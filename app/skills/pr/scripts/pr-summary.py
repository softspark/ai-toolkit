#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate a structured PR summary from the git log.

Parses commits between a base branch and HEAD using the Conventional
Commits format, groups them by type, detects breaking changes, counts
file and test statistics, and suggests a PR title. Outputs a JSON
object suitable for populating a PR template.

Usage::

    python3 pr-summary.py [base_branch]
    # Default base: cached origin/HEAD, then local main (no network access)

An empty commit range returns a normal summary with zero counts and an empty
title. Invalid refs and Git failures return an error object and exit nonzero.
"""

from __future__ import annotations

import argparse
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


def run_git(*args: str) -> str:
    """Run Git with literal arguments, preserving delimiters and failures."""
    result = subprocess.run(
        ["git", "--no-pager", *args], capture_output=True, text=True, check=True
    )
    return result.stdout


def resolve_commit(ref: str) -> str | None:
    """Resolve one literal commit ref, returning None only when it is absent."""
    try:
        return run_git(
            "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}"
        ).strip()
    except subprocess.CalledProcessError as error:
        if error.returncode == 1:
            return None
        raise


def resolve_base(base: str | None) -> tuple[str, str]:
    """Select a locally available base and pin its commit for this summary."""
    if base is not None:
        commit = resolve_commit(base)
        if commit is None:
            raise ValueError(
                f"Base {base!r} is not a commit ref available locally. "
                "Pass an existing branch, tag, or commit."
            )
        return base, commit
    for label, ref in (
        ("origin/HEAD", "refs/remotes/origin/HEAD"),
        ("main", "refs/heads/main"),
    ):
        commit = resolve_commit(ref)
        if commit is not None:
            return label, commit
    raise ValueError(
        "Cannot determine a base: cached origin/HEAD and local main are unavailable. "
        "Pass the PR target branch explicitly, for example: pr-summary.py develop."
    )


def parse_conventional_commit(message: str) -> dict[str, Any]:
    """Parse a conventional commit message into type, scope, and description.

    Args:
        message: Single-line commit message.

    Returns:
        Dictionary with ``type``, ``scope``, ``breaking``, and
        ``description`` keys.
    """
    m = re.match(r"^(\w+)(?:\(([^)]+)\))?(!)?:\s*(.+)$", message)
    if m:
        return {
            "type": m.group(1),
            "scope": m.group(2) or "",
            "breaking": bool(m.group(3)),
            "description": m.group(4),
        }
    return {"type": "other", "scope": "", "breaking": False, "description": message}


def read_commits(commit_range: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Read subjects and bodies without line or user-controlled separators."""
    log_output = run_git(
        "log",
        "--no-show-signature",
        "--no-color",
        "--no-decorate",
        "--format=%h%x00%s%x00%b",
        "-z",
        commit_range,
        "--",
    )
    fields = log_output.split("\0")[:-1]
    commits: list[dict[str, Any]] = []
    breaking_changes: list[str] = []
    for index in range(0, len(fields), 3):
        sha, message, body = fields[index : index + 3]
        parsed = parse_conventional_commit(message)
        commits.append({"sha": sha, "message": message, **parsed})
        for bline in f"{message}\n{body}".splitlines():
            if bline.startswith(("BREAKING CHANGE:", "BREAKING-CHANGE:")):
                breaking_changes.append(bline.split(":", 1)[1].strip())
    # Also check for ! in commit type
    for c in commits:
        if c["breaking"] and c["description"] not in breaking_changes:
            breaking_changes.append(c["description"])
    return commits, breaking_changes


def summarize_groups(
    commits: list[dict[str, Any]],
) -> tuple[dict[str, list[str]], list[str]]:
    """Group commit descriptions and construct the existing summary bullets."""
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

    return groups, summary_bullets


def suggest_title(commits: list[dict[str, Any]]) -> str:
    """Suggest a title using the most common commit type and scope."""
    if not commits:
        return ""
    type_counts: dict[str, int] = {}
    scope_counts: dict[str, int] = {}
    for c in commits:
        type_counts[c["type"]] = type_counts.get(c["type"], 0) + 1
        if c["scope"]:
            scope_counts[c["scope"]] = scope_counts.get(c["scope"], 0) + 1

    dominant_type = max(type_counts, key=lambda item: type_counts[item])
    dominant_scope = (
        max(scope_counts, key=lambda item: scope_counts[item]) if scope_counts else ""
    )

    if len(commits) == 1:
        title_suggestion: str = commits[0]["message"]
    else:
        scope_part = f"({dominant_scope})" if dominant_scope else ""
        # Use the description of the first commit of dominant type as hint
        dominant_descs = [
            c["description"] for c in commits if c["type"] == dominant_type
        ]
        brief = dominant_descs[0]
        if len(brief) > 50:
            brief = brief[:47] + "..."
        title_suggestion = f"{dominant_type}{scope_part}: {brief}"
    return title_suggestion


def generate_summary(base: str | None) -> dict[str, Any]:
    """Generate the JSON summary from checked, locally resolved Git refs."""
    run_git("rev-parse", "--git-dir")
    base, base_commit = resolve_base(base)
    head = resolve_commit("HEAD")
    if head is None:
        raise ValueError(
            "HEAD has no commit. Create a commit before generating a PR summary."
        )
    commits, breaking_changes = read_commits(f"{base_commit}..{head}")
    groups, summary_bullets = summarize_groups(commits)
    names = run_git("diff", "--name-only", "-z", f"{base_commit}...{head}", "--")
    changed_files = names.split("\0")[:-1]
    test_files = sum(
        bool(
            re.search(r"(test_|_test\.|\.test\.|spec\.|__tests__)", name, re.IGNORECASE)
        )
        for name in changed_files
    )
    return {
        "base": base,
        "total_commits": len(commits),
        "title_suggestion": suggest_title(commits),
        "commits": commits,
        "groups": groups,
        "summary_bullets": summary_bullets,
        "has_breaking": len(breaking_changes) > 0,
        "breaking_changes": breaking_changes,
        "files_changed": len(changed_files),
        "test_files_changed": test_files,
        "has_tests": test_files > 0,
    }


def main() -> int:
    """Print a summary or an actionable error, using a failing exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "base_branch", nargs="?", help="PR target ref (default: origin/HEAD, then main)"
    )
    args = parser.parse_args()
    try:
        result = generate_summary(args.base_branch)
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or f"exit status {error.returncode}"
        print(json.dumps({"error": f"Git command failed: {detail}"}))
        return 1
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
