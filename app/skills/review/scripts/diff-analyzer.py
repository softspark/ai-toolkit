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


CATEGORY_PATTERNS: dict[str, str] = {
    "security": r"(auth|login|password|token|secret|crypto|session|permission|role|access)",
    "test": r"(test_|_test\.|spec\.|\.test\.|__tests__|tests/)",
    "config": r"(\.(yml|yaml|json|toml|env|ini|cfg)$|config|settings|\.lock$)",
    "migration": r"(migration|alembic|schema|migrate)",
    "infra": r"(docker|kubernetes|k8s|terraform|ansible|ci|deploy|\.github)",
    "docs": r"(readme|changelog|docs/|\.md$|license)",
}

SECRET_PATTERNS: list[str] = [
    r'(?i)(api[_-]?key|secret[_-]?key|password|token|bearer)\s*[=:]\s*["\'][^"\']{8,}',
    r"AKIA[0-9A-Z]{16}",
    r"sk-[a-zA-Z0-9]{20,}",
    r"ghp_[a-zA-Z0-9]{36}",
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


def main() -> None:
    """Entry point: analyze diff and print JSON risk report to stdout."""
    base = sys.argv[1] if len(sys.argv) > 1 else "main"

    # Get diff stats (try base...HEAD first, fall back to --cached)
    r = subprocess.run(
        ["git", "diff", "--numstat", f"{base}...HEAD"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    )
    if r.returncode != 0:
        r = subprocess.run(
            ["git", "diff", "--numstat", "--cached"],
            capture_output=True, text=True,
        )
    diff_stat = r.stdout.strip()
    files: list[dict[str, Any]] = []
    total_add, total_del = 0, 0

    for line in diff_stat.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        add = int(parts[0]) if parts[0] != "-" else 0
        delete = int(parts[1]) if parts[1] != "-" else 0
        path = parts[2]
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

    # Secrets scan on added lines (try base...HEAD first, fall back to --cached)
    r = subprocess.run(
        ["git", "diff", f"{base}...HEAD"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    )
    if r.returncode != 0:
        r = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True, text=True,
        )
    diff_content = r.stdout.strip()
    secrets: list[dict[str, Any]] = []
    for i, line in enumerate(diff_content.split("\n")):
        if line.startswith("+") and not line.startswith("+++"):
            for p in SECRET_PATTERNS:
                if re.search(p, line):
                    secrets.append({"line": i, "preview": line[:80]})

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

    result: dict[str, Any] = {
        "base": base,
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
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
