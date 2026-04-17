#!/usr/bin/env python3
"""Analyze a git diff for risk assessment, file categorization, and secrets detection.

Compares the current branch against a base branch (default ``main``),
categorises each changed file (security, test, config, migration,
infra, docs, logic), scans added lines for potential secrets, computes
a composite risk score, and outputs a JSON report suitable for
pre-review triage.

Usage::

    python3 diff-analyzer.py [base_branch]
    # Default base branch: main
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import Any


# Order matters: earlier patterns win. `docs` and `test` come first so a
# README under docs/ or a test file named e.g. `role_test.py` is not miscategorised
# as `security`. Patterns use word boundaries or path anchors to avoid matching
# substrings in unrelated filenames.
CATEGORY_PATTERNS: dict[str, str] = {
    "docs": r"(^|/)(readme|changelog|license)\b|(^|/)docs/|\.md$",
    "test": r"(^|/)tests?/|__tests__|(^|/)test_|_test\.|\.test\.|\.spec\.",
    "migration": r"(^|/)(migrations?|alembic)(/|$)|\bschema_migrate\b|\b(migrate|migration)\.[a-z]+$",
    "infra": r"(^|/)(docker|kubernetes|k8s|terraform|ansible|\.github)(/|$)|\.(dockerfile|tf)$|(^|/)ci(/|$)|(^|/)deploy(/|_|-|$)",
    "security": r"\b\w*(auth|login|password|passwd|token|secret|crypto|session|permission|role|access|oauth|jwt|mfa|totp)\w*\b",
    "config": r"(^|/)(config|settings)(/|\.[a-z]+$)|\.(yml|yaml|json|toml|env|ini|cfg)$|\.lock$",
}

# Secret detection patterns. Combines quoted and unquoted env-style assignments,
# common cloud provider prefixes, JWTs, and PEM private key headers.
SECRET_PATTERNS: list[str] = [
    # Quoted secret assignments: API_KEY = "..." / secret: '...'
    # Allow prefix/suffix word chars so `some_password`, `MY_API_KEY`, `accessToken` match.
    r'(?i)\b\w*(?:api[_-]?key|secret[_-]?key|password|passwd|token|bearer|access[_-]?key)\w*\s*[=:]\s*["\'][^"\']{8,}["\']',
    # Unquoted env-style: API_KEY=abcdef12345678 or API_KEY=SECRET_VALUE_XYZ.
    # The RHS must look like a secret (no snake_case identifiers) — either a
    # dotted/hyphenated/alphanumeric blob without underscores, or an ALL_CAPS
    # constant. This excludes ``request_token = generate_token_v2_legacy`` style
    # function refs.
    r'(?i)\b\w*(?:api[_-]?key|secret[_-]?key|password|passwd|token|bearer|access[_-]?key)\w*\s*=\s*(?:[A-Za-z0-9\-\.]{12,}|(?-i:[A-Z][A-Z0-9_]{11,}))\b',
    # AWS access key ID
    r"\bAKIA[0-9A-Z]{16}\b",
    # OpenAI / Anthropic-style keys
    r"\bsk-[a-zA-Z0-9]{20,}\b",
    # GitHub PAT
    r"\bghp_[a-zA-Z0-9]{36}\b",
    # GitHub fine-grained PAT
    r"\bgithub_pat_[A-Za-z0-9_]{82}\b",
    # Google API key
    r"\bAIza[0-9A-Za-z_\-]{35}\b",
    # Slack tokens (bot, app, user, refresh, config)
    r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b",
    # JWT
    r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b",
    # PEM private key header
    r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----",
]


def categorize(path: str) -> str:
    """Categorize a file path into a review domain.

    Args:
        path: Relative file path from the diff.

    Returns:
        Category name (``"security"``, ``"test"``, ``"config"``,
        ``"migration"``, ``"infra"``, ``"docs"``, or ``"logic"``).
    """
    for cat, pattern in CATEGORY_PATTERNS.items():
        if re.search(pattern, path, re.IGNORECASE):
            return cat
    return "logic"


def _base_ref_exists(base: str) -> bool:
    """Return True if ``base`` resolves to a valid git ref."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _run_diff(args: list[str]) -> tuple[str, int]:
    """Run a git diff command and return (stdout, returncode)."""
    result = subprocess.run(
        ["git", "diff", *args],
        capture_output=True,
        text=True,
    )
    return result.stdout, result.returncode


def _parse_numstat_z(raw: str) -> list[tuple[int, int, str]]:
    """Parse ``git diff --numstat -z`` output into ``(adds, dels, path)`` triples.

    With ``-z`` each record is NUL-terminated. Rename entries are emitted
    as three NUL-separated tokens: ``additions\\tdeletions\\t`` then
    ``old_path`` NUL ``new_path`` NUL. The new path is reported.
    """
    records: list[tuple[int, int, str]] = []
    tokens = raw.split("\0")
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if not token:
            i += 1
            continue
        parts = token.split("\t")
        if len(parts) < 2:
            i += 1
            continue
        add_str, del_str = parts[0], parts[1]
        try:
            add = int(add_str) if add_str != "-" else 0
            delete = int(del_str) if del_str != "-" else 0
        except ValueError:
            i += 1
            continue
        if len(parts) >= 3 and parts[2]:
            # Normal entry: "adds\tdels\tpath"
            records.append((add, delete, parts[2]))
            i += 1
        else:
            # Rename entry: "adds\tdels\t" then old\0new
            if i + 2 < len(tokens):
                new_path = tokens[i + 2]
                if new_path:
                    records.append((add, delete, new_path))
                i += 3
            else:
                i += 1
    return records


def _scan_secrets(diff_content: str) -> list[dict[str, Any]]:
    """Walk a unified diff, tracking current file path and line number for each
    added line, and report any lines matching a secret pattern.

    Returns a list of ``{"file": path, "line": file_line, "preview": snippet}``.
    """
    findings: list[dict[str, Any]] = []
    current_file: str | None = None
    new_line_no: int | None = None
    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    for raw_line in diff_content.split("\n"):
        if raw_line.startswith("+++ "):
            # Format: "+++ b/path/to/file" or "+++ /dev/null"
            target = raw_line[4:].strip()
            if target == "/dev/null":
                current_file = None
            elif target.startswith("b/"):
                current_file = target[2:]
            else:
                current_file = target
            new_line_no = None
            continue
        if raw_line.startswith("--- "):
            continue
        if raw_line.startswith("@@"):
            match = hunk_re.match(raw_line)
            if match:
                new_line_no = int(match.group(1))
            continue
        if new_line_no is None:
            continue
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            for pattern in SECRET_PATTERNS:
                if re.search(pattern, raw_line):
                    findings.append(
                        {
                            "file": current_file,
                            "line": new_line_no,
                            "preview": raw_line[:80],
                        }
                    )
                    break
            new_line_no += 1
        elif raw_line.startswith("-"):
            # Deletion does not advance the new-file line counter
            continue
        else:
            # Context line advances the new-file line counter
            new_line_no += 1
    return findings


def main() -> None:
    """Entry point: analyze diff and print JSON risk report to stdout."""
    base = sys.argv[1] if len(sys.argv) > 1 else "main"

    warnings: list[str] = []

    # Determine scope: branch diff if base exists, otherwise staged-only.
    if _base_ref_exists(base):
        scope = f"{base}...HEAD"
        numstat_raw, rc1 = _run_diff(["--numstat", "-z", f"{base}...HEAD"])
        diff_raw, rc2 = _run_diff([f"{base}...HEAD"])
        if rc1 != 0 or rc2 != 0:
            scope = "staged"
            warnings.append(
                f"branch diff against {base!r} failed; fell back to staged changes"
            )
            numstat_raw, _ = _run_diff(["--numstat", "-z", "--cached"])
            diff_raw, _ = _run_diff(["--cached"])
    else:
        scope = "staged"
        warnings.append(
            f"base ref {base!r} not found; reporting staged changes only"
        )
        print(
            f"[diff-analyzer] base ref {base!r} not found; using --cached",
            file=sys.stderr,
        )
        numstat_raw, _ = _run_diff(["--numstat", "-z", "--cached"])
        diff_raw, _ = _run_diff(["--cached"])

    files: list[dict[str, Any]] = []
    total_add, total_del = 0, 0

    for add, delete, path in _parse_numstat_z(numstat_raw):
        cat = categorize(path)
        if cat in ("security", "migration") or add > 100:
            risk = "high"
        elif add > 30:
            risk = "medium"
        else:
            risk = "low"
        files.append(
            {
                "path": path,
                "additions": add,
                "deletions": delete,
                "category": cat,
                "risk": risk,
            }
        )
        total_add += add
        total_del += delete

    # Category summary
    categories: dict[str, int] = {}
    for f in files:
        categories[f["category"]] = categories.get(f["category"], 0) + 1

    # Hotspots - files with most additions
    hotspots: list[str] = [
        f"{f['path']} - {f['additions']} lines added ({f['category']})"
        for f in sorted(files, key=lambda x: x["additions"], reverse=True)[:5]
        if f["additions"] > 20
    ]

    # Secrets scan on added lines with accurate file + file-line tracking
    secrets = _scan_secrets(diff_raw)

    # Risk score
    has_security = any(f["category"] == "security" for f in files)
    has_migration = any(f["category"] == "migration" for f in files)
    if has_security or has_migration or secrets or len(files) > 20:
        risk_score = "high"
    elif len(files) > 10 or total_add > 500:
        risk_score = "medium"
    else:
        risk_score = "low"

    # Test coverage estimate
    test_file_count = sum(1 for f in files if f["category"] == "test")
    logic_files = sum(1 for f in files if f["category"] == "logic")
    if test_file_count >= logic_files and logic_files > 0:
        coverage = "good"
    elif test_file_count > 0:
        coverage = "partial"
    else:
        coverage = "none"

    if not files:
        warnings.append("no changes detected")

    result: dict[str, Any] = {
        "base": base,
        "scope": scope,
        "files_changed": len(files),
        "additions": total_add,
        "deletions": total_del,
        "files": files,
        "categories": categories,
        "risk_score": risk_score,
        "hotspots": hotspots,
        "test_coverage_estimate": coverage,
        "secrets_scan": secrets,
        "parallel_review_recommended": risk_score == "high" or len(files) > 10,
        "warnings": warnings,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
