#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Project a bounded set of checkpoint fields into the private session summary."""

from collections import deque
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import stat
import sys
import tempfile


HEADER = "# Session Context (structured v1)"
MAX_CHECKPOINTS = 5
MAX_VALUE = 400
FIELDS = {
    "objective": "Objective", "current objective": "Objective",
    "completed": "Completed", "completed steps": "Completed",
    "pending": "Next action", "pending steps": "Next action", "next action": "Next action",
    "decision": "Decision", "decisions": "Decision", "key decisions": "Decision",
    "artifacts": "Artifacts", "artifact": "Artifacts", "files modified": "Files modified",
}
# Omit the entire field rather than trying to extract the value of a secret.
# This covers common formats. Authors still need to omit private personal data.
SENSITIVE = re.compile(
    r"password|passwd|passphrase|secret|credential|token|api[ _-]?key|private[ _-]?key|"
    r"authorization|cookie|\bbearer\b|\bbasic\s+[\w+/=]+|-----BEGIN |"
    r"\b(?:gh[oprsu]_|github_pat_|npm_|glpat-|sk[-_]|xox[baprs]-|AKIA|ASIA|AIza|eyJ)[\w.-]{6,}|"
    r"\S+@\S+|\w+://\S*[?#]|(?:/Users/|/home/|[A-Za-z]:\\Users\\)\S+|"
    r"[A-Za-z0-9_/+=-]{48,}", re.IGNORECASE,
)


def keep_value(value: str) -> bool:
    return bool(value) and len(value) <= MAX_VALUE and value.isprintable() and not SENSITIVE.search(value)


def checkpoint_fields(lines):
    recent = deque(maxlen=MAX_CHECKPOINTS)
    current = None
    fence = ""
    for line in lines:
        text = line.strip()
        marker = re.match(r"^(`{3,}|~{3,})(.*)$", text)
        if marker:
            run, suffix = marker.groups()
            if not fence:
                fence = run
            elif run.startswith(fence) and not suffix.strip():
                fence = ""
            continue
        if fence:
            continue
        if text.startswith("#"):
            current = None
            if re.fullmatch(r"## Checkpoint(?:\s+.*)?", text):
                current = {}
                recent.append(current)
            continue
        if current is not None:
            key, colon, value = text.partition(":")
            field = FIELDS.get(key.strip("-* ").lower())
            value = value.removeprefix("**").strip()
            if field and colon:
                if keep_value(value):
                    current[field] = value
                else:
                    current.pop(field, None)
    for checkpoint in recent:
        if checkpoint:
            yield "\n## Checkpoint"
            yield from (f"- {key}: {value}" for key, value in checkpoint.items())


def read_checkpoints(path: Path) -> list[str]:
    try:
        expected = path.lstat()
        if not stat.S_ISREG(expected.st_mode):
            return []
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
    except OSError:
        # Optional checkpoints must not prevent replacement of an older summary.
        return []
    if not expected.st_ino or not os.path.samestat(expected, os.fstat(fd)):
        os.close(fd)
        return []
    with os.fdopen(fd, encoding="utf-8", errors="replace") as source:
        return list(checkpoint_fields(source))


def write_summary(directory: Path, session: str, commit: str, dirty: str) -> None:
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink():
        raise ValueError("session directory is a symlink")
    lines = [HEADER, f"Updated: {datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}"]
    lines.append(f"Session fingerprint: {hashlib.sha256(session.encode()).hexdigest()[:16]}")
    if re.fullmatch(r"[0-9a-f]{7,40}", commit):
        lines.append(f"Commit: {commit}")
    if dirty.isascii() and dirty.isdigit():
        lines.append(f"Uncommitted paths: {dirty}")
    lines.extend(read_checkpoints(directory / "session-context.md.checkpoints"))
    fd, name = tempfile.mkstemp(dir=directory)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        os.replace(temporary, directory / "session-context.md")
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    write_summary(Path(sys.argv[1]), *sys.argv[2:])
