#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Find secret-looking database columns that an edit stores in plaintext.

Backs the advisory ``secret-column-check.sh`` PostToolUse hook (secrets-at-rest
rule in ``app/rules/common/security.md``). Reads the edited text on stdin and
the edited file's path as the only argument, and prints one finding per line
as ``<column>\\t<declaration kind>``. Prints nothing when the text declares no
such column, when the declaration carries an encryption or hashing marker, or
when the file is not a schema, model or migration file.

Detection is by name and by declaration shape, so it is a reminder, not a
proof: a credential under a neutral name is not found, and a column that only
looks like one is reported once and can be ignored.

Usage:
    printf '%s' "$NEW_TEXT" | secret_column_check.py path/to/Entity/User.php

Always exits 0: a hook helper must never break the edit it follows.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import PurePath

SECRET_NAME = re.compile(
    r"token|secret|password|passwd|apikey|privatekey|licensekey|licencekey"
    r"|credential|signingkey|accesskey|clientkey"
)
"""Name fragments (lower case, ``_`` removed) that mark a credential."""

NOT_A_SECRET = re.compile(
    r"hash|digest|hmac|fingerprint|expires|expiry|expiration|ttl|length|policy"
    r"|count|changed|lease|enabled|configured|required|type|url|uri|endpoint"
    r"|prefix|last4|hint|mask|encrypted|cipher|sealed"
)
"""Fragments that make a matching name a derived or descriptive column."""

PROTECTED = re.compile(
    r"encrypt|cipher|hashedtoken|blindindex|hashed|sealed|transformer|@convert|secretfield",
    re.IGNORECASE,
)
"""Markers on or just above a declaration that say the value is protected."""

FRAMEWORK_PASSWORD = frozenset({"password", "passwd"})
"""Bare ``password`` columns are framework password hashes (Laravel, Django, Symfony)."""

MAX_FINDINGS = 20


@dataclass(frozen=True)
class Pattern:
    kind: str
    regex: re.Pattern[str]
    look_back: int = 0
    """Lines above the match also searched for a protection marker (attributes, decorators)."""
    requires: str = ""
    """Content that must appear somewhere in the text for the pattern to apply."""


SQL_TYPES = r"(?:VARCHAR|CHARACTER\s+VARYING|NVARCHAR|CHAR|TEXT|CLOB|BYTEA|BLOB|STRING)\b"

SQL = Pattern(
    "SQL column",
    re.compile(
        r"(?:ADD\s+(?:COLUMN\s+)?|[(,]\s*|^\s*)[\"`\[]?(?P<name>\w+)[\"`\]]?\s+" + SQL_TYPES,
        re.IGNORECASE | re.MULTILINE,
    ),
)

PATTERNS_BY_SUFFIX: dict[str, tuple[Pattern, ...]] = {
    ".php": (
        Pattern(
            "Doctrine column",
            re.compile(
                r"^\s*(?:private|protected|public)\s+(?:readonly\s+)?\??[\w\\|]*\s*\$(?P<name>\w+)",
                re.MULTILINE,
            ),
            look_back=8,
            requires="Column",
        ),
        Pattern(
            "Laravel column",
            re.compile(r"\$table->(?:string|text|char|longText|mediumText)\(\s*['\"](?P<name>\w+)['\"]"),
        ),
    ),
    ".py": (
        Pattern(
            "SQLAlchemy column",
            re.compile(
                r"^\s*(?P<name>\w+)\s*(?::\s*Mapped\[[^\]]*\])?\s*=\s*(?:\w+\.)?(?:mapped_column|Column)\(.*$",
                re.MULTILINE,
            ),
        ),
        Pattern(
            "SQLAlchemy column",
            re.compile(r"^\s*(?P<name>\w+)\s*:\s*Mapped\[(?:str|Optional\[str\]|str\s*\|\s*None)\]\s*$", re.MULTILINE),
            requires="Mapped[",
        ),
        Pattern(
            "Django field",
            re.compile(r"^\s*(?P<name>\w+)\s*=\s*models\.(?:Char|Text|Binary)Field\(.*$", re.MULTILINE),
        ),
    ),
    ".prisma": (
        Pattern("Prisma field", re.compile(r"^\s*(?P<name>\w+)\s+String\b.*$", re.MULTILINE)),
    ),
    ".rb": (
        Pattern("Rails column", re.compile(r"t\.(?:string|text)\s+:(?P<name>\w+).*$", re.MULTILINE)),
        Pattern("Rails column", re.compile(r"add_column\s+:\w+,\s*:(?P<name>\w+),\s*:(?:string|text).*$", re.MULTILINE)),
    ),
    ".ts": (
        Pattern(
            "TypeORM column",
            re.compile(r"^\s*(?:public\s+|private\s+|protected\s+|readonly\s+)*(?P<name>\w+)[?!]?\s*:\s*string\b", re.MULTILINE),
            look_back=3,
            requires="@Column",
        ),
        Pattern("Drizzle column", re.compile(r"^\s*(?P<name>\w+)\s*:\s*(?:varchar|text|char)\(.*$", re.MULTILINE)),
        Pattern(
            "Sequelize column",
            re.compile(r"^\s*(?P<name>\w+)\s*:\s*\{\s*type:\s*DataTypes\.(?:STRING|TEXT)\b.*$", re.MULTILINE),
        ),
    ),
    ".java": (
        Pattern(
            "JPA column",
            re.compile(r"^\s*(?:private|protected|public)\s+String\s+(?P<name>\w+)\s*[;=]", re.MULTILINE),
            look_back=3,
            requires="@Column",
        ),
    ),
    ".kt": (
        Pattern(
            "JPA column",
            re.compile(r"^\s*(?:\w+\s+)*va[lr]\s+(?P<name>\w+)\s*:\s*String\b", re.MULTILINE),
            look_back=3,
            requires="@Column",
        ),
    ),
}
PATTERNS_BY_SUFFIX[".js"] = PATTERNS_BY_SUFFIX[".ts"]

MIGRATION_HINT = re.compile(r"migrat|alembic|/versions/|(?:^|/)Version\d+\.php$|/db/", re.IGNORECASE)
"""Paths whose text may carry raw SQL DDL (``addSql``, ``op.execute``, ``.sql`` files)."""


def looks_secret(name: str) -> bool:
    """Whether a column or field name looks like it holds a credential."""
    if name.lower() in FRAMEWORK_PASSWORD or re.search(r"(?:_at|At)$", name):
        return False
    normalized = name.replace("_", "").lower()
    return bool(SECRET_NAME.search(normalized)) and not NOT_A_SECRET.search(normalized)


def patterns_for(path: str) -> tuple[Pattern, ...]:
    """The declaration shapes worth scanning in this file, by suffix and location."""
    pure = PurePath(path)
    suffix = pure.suffix.lower()
    found = PATTERNS_BY_SUFFIX.get(suffix, ())
    if suffix == ".sql" or MIGRATION_HINT.search(pure.as_posix()):
        found = (*found, SQL)
    return found


def _declaration(lines: list[str], line_index: int, look_back: int) -> list[str]:
    """The matched line plus the attribute/decorator/doc lines that belong to it.

    Walks up at most ``look_back`` lines and stops at the end of the previous
    statement, so a mapping attribute or an encryption marker on the property
    above is never credited to this one.
    """
    block = [lines[line_index]]
    for index in range(line_index - 1, max(-1, line_index - look_back - 1), -1):
        line = lines[index].rstrip()
        if line.endswith((";", "}")) and not line.lstrip().startswith(("#[", "@", "*", "/*", "//")):
            break
        block.append(line)
    return block


def _mapped_and_protected(lines: list[str], line_index: int, pattern: Pattern) -> tuple[bool, bool]:
    block = _declaration(lines, line_index, pattern.look_back)
    mapped = not pattern.requires or pattern.look_back == 0 or any(pattern.requires in line for line in block[1:])
    return mapped, any(PROTECTED.search(line) for line in block)


def find(path: str, text: str) -> list[tuple[str, str]]:
    """Secret-looking, unprotected column declarations in ``text``, as ``(name, kind)``."""
    lines = text.splitlines()
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line) + 1)

    findings: list[tuple[str, str]] = []
    seen: set[str] = set()
    for pattern in patterns_for(path):
        if pattern.requires and pattern.requires not in text:
            continue
        for match in pattern.regex.finditer(text):
            name = match.group("name")
            if name in seen or not looks_secret(name):
                continue
            line_index = _line_of(offsets, match.start("name"))
            mapped, protected = _mapped_and_protected(lines, line_index, pattern)
            if not mapped or protected:
                continue
            seen.add(name)
            findings.append((name, pattern.kind))
            if len(findings) >= MAX_FINDINGS:
                return findings
    return findings


def _line_of(offsets: list[int], position: int) -> int:
    low, high = 0, len(offsets) - 1
    while low < high:
        middle = (low + high + 1) // 2
        if offsets[middle] <= position:
            low = middle
        else:
            high = middle - 1
    return low


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return 0
    try:
        text = sys.stdin.read()
        for name, kind in find(argv[1], text):
            print(f"{name}\t{kind}")
    except Exception:  # noqa: BLE001 - advisory helper, never break the caller
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
