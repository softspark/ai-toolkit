#!/usr/bin/env python3
"""Generate a structured PR summary from the git log.

Parses commits between a base branch and HEAD using the Conventional
Commits format, groups them by type, detects breaking changes, counts
file and test statistics, and suggests a PR title. Outputs a JSON
object suitable for populating a PR template.

Usage::

    python3 pr-summary.py [base_branch]
    # Default base branch: main
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import Any


CONVENTIONAL_TYPES: dict[str, str] = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "docs": "Documentation",
    "style": "Style",
    "refactor": "Refactoring",
    "perf": "Performance",
    "test": "Tests",
    "build": "Build",
    "ci": "CI/CD",
    "chore": "Chores",
    "revert": "Reverts",
}


def run(cmd: str) -> str:
    """Run a command and return stripped stdout.

    Args:
        cmd: Command string (split via shlex, no shell).

    Returns:
        Stripped standard output of the command.
    """
    import shlex
    # Strip shell redirects (2>/dev/null) — subprocess captures stderr anyway
    clean = re.sub(r'\s*2>/dev/null\s*', '', cmd)
    r = subprocess.run(shlex.split(clean), capture_output=True, text=True)
    return r.stdout.strip()


def parse_conventional_commit(message: str) -> dict[str, Any]:
    """Parse a conventional commit message into type, scope, and description.

    Args:
        message: Single-line commit message.

    Returns:
        Dictionary with ``type``, ``scope``, ``breaking``, and
        ``description`` keys.
    """
    m = re.match(
        r"^(\w+)(?:\(([^)]+)\))?(!)?:\s*(.+)$", message
    )
    if m:
        return {
            "type": m.group(1),
            "scope": m.group(2) or "",
            "breaking": bool(m.group(3)),
            "description": m.group(4),
        }
    return {"type": "other", "scope": "", "breaking": False, "description": message}


def main() -> None:
    """Entry point: generate PR summary and print JSON to stdout."""
    base = sys.argv[1] if len(sys.argv) > 1 else "main"

    # Get oneline log
    log_output = run(f"git log --oneline {base}..HEAD 2>/dev/null")
    if not log_output:
        print(json.dumps({"error": f"No commits found between {base} and HEAD."}))
        return

    # Parse commits
    commits: list[dict[str, Any]] = []
    for line in log_output.split("\n"):
        if not line.strip():
            continue
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        sha = parts[0]
        message = parts[1]
        parsed = parse_conventional_commit(message)
        commits.append({"sha": sha, "message": message, **parsed})

    # Check full commit bodies for BREAKING CHANGE
    body_output = run(f"git log --format='%B---COMMIT_SEP---' {base}..HEAD 2>/dev/null")
    breaking_changes: list[str] = []
    for block in (body_output or "").split("---COMMIT_SEP---"):
        for bline in block.strip().split("\n"):
            if bline.startswith("BREAKING CHANGE:") or bline.startswith("BREAKING-CHANGE:"):
                breaking_changes.append(bline.split(":", 1)[1].strip())
    # Also check for ! in commit type
    for c in commits:
        if c["breaking"] and c["description"] not in breaking_changes:
            breaking_changes.append(c["description"])

    # Group by type
    groups: dict[str, list[str]] = {}
    for c in commits:
        label = CONVENTIONAL_TYPES.get(c["type"], "Other")
        groups.setdefault(label, []).append(c["description"])

    # Summary bullets
    summary_bullets: list[str] = []
    for label, descriptions in groups.items():
        if len(descriptions) == 1:
            summary_bullets.append(f"{label}: {descriptions[0]}")
        else:
            summary_bullets.append(f"{label}: {len(descriptions)} changes")

    # File stats
    diff_stat = run(f"git diff --stat {base}...HEAD 2>/dev/null")
    files_changed = 0
    test_files = 0
    stat_lines = diff_stat.split("\n") if diff_stat else []
    for sl in stat_lines:
        sl = sl.strip()
        if "|" in sl:
            files_changed += 1
            fname = sl.split("|")[0].strip()
            if re.search(r"(test_|_test\.|\.test\.|spec\.|__tests__)", fname, re.IGNORECASE):
                test_files += 1

    # Suggest title from most common type + scope
    type_counts: dict[str, int] = {}
    scope_counts: dict[str, int] = {}
    for c in commits:
        type_counts[c["type"]] = type_counts.get(c["type"], 0) + 1
        if c["scope"]:
            scope_counts[c["scope"]] = scope_counts.get(c["scope"], 0) + 1

    dominant_type = max(type_counts, key=type_counts.get) if type_counts else "feat"
    dominant_scope = max(scope_counts, key=scope_counts.get) if scope_counts else ""

    if len(commits) == 1:
        title_suggestion = commits[0]["message"]
    else:
        scope_part = f"({dominant_scope})" if dominant_scope else ""
        # Use the description of the first commit of dominant type as hint
        dominant_descs = [c["description"] for c in commits if c["type"] == dominant_type]
        brief = dominant_descs[0] if dominant_descs else "multiple changes"
        if len(brief) > 50:
            brief = brief[:47] + "..."
        title_suggestion = f"{dominant_type}{scope_part}: {brief}"

    result: dict[str, Any] = {
        "base": base,
        "total_commits": len(commits),
        "title_suggestion": title_suggestion,
        "commits": commits,
        "groups": groups,
        "summary_bullets": summary_bullets,
        "has_breaking": len(breaking_changes) > 0,
        "breaking_changes": breaking_changes,
        "files_changed": files_changed,
        "test_files_changed": test_files,
        "has_tests": test_files > 0,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
