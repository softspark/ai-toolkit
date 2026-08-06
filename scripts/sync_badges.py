#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Sync the README count badges to ground truth.

`validate.py` errors when a README badge disagrees with the tree. The badges were
maintained by hand, so every change that added a test or a skill turned the build
red until someone edited a number — a tax paid per change, with a diagnosis cycle
each time it was forgotten.

This derives the three counts the same way `validate.py` does and rewrites them.
It runs inside `npm run generate:all`, which `prepublishOnly` executes before
`validate.py --strict`, so the badges are correct by the time anything checks them.

Counting rules, matched to validate.py so the two cannot disagree:
  agents  — *.md under app/agents/
  skills  — directories under app/skills/ with a SKILL.md, excluding _-prefixed
  tests   — `@test ` declarations across tests/*.bats

Stdlib-only.

Usage:
    python3 scripts/sync_badges.py            # rewrite README.md badges
    python3 scripts/sync_badges.py --check    # report drift, change nothing
    python3 scripts/sync_badges.py --toolkit-dir /path

Exit codes:
    0  badges are correct (or were rewritten)
    1  --check found drift
    2  usage error
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir as default_toolkit_dir

TEST_RE = re.compile(r"^@test ", re.MULTILINE)


def counts(tk_dir: Path) -> dict[str, int]:
    agents_dir = tk_dir / "app" / "agents"
    skills_dir = tk_dir / "app" / "skills"
    tests_dir = tk_dir / "tests"

    agents = len(list(agents_dir.glob("*.md"))) if agents_dir.is_dir() else 0
    skills = sum(
        1 for d in skills_dir.iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "SKILL.md").is_file()
    ) if skills_dir.is_dir() else 0
    tests = sum(
        len(TEST_RE.findall(f.read_text(encoding="utf-8")))
        for f in tests_dir.glob("*.bats")
    ) if tests_dir.is_dir() else 0

    return {"agents": agents, "skills": skills, "tests": tests}


def sync(tk_dir: Path, check_only: bool) -> int:
    readme = tk_dir / "README.md"
    if not readme.is_file():
        print("ERROR: README.md not found", file=sys.stderr)
        return 2

    text = readme.read_text(encoding="utf-8")
    actual = counts(tk_dir)
    drift: list[str] = []
    updated = text

    for label, value in actual.items():
        pattern = re.compile(rf"({label}-)(\d+)")
        match = pattern.search(updated)
        if not match:
            continue
        if match.group(2) != str(value):
            drift.append(f"{label}: badge {match.group(2)} != actual {value}")
            updated = pattern.sub(rf"\g<1>{value}", updated, count=1)

    if check_only:
        for line in drift:
            print(f"  DRIFT: {line}")
        if drift:
            print("BADGE CHECK FAILED — run `python3 scripts/sync_badges.py`")
            return 1
        print(f"  OK: badges match ({actual['agents']} agents, "
              f"{actual['skills']} skills, {actual['tests']} tests)")
        return 0

    if drift:
        readme.write_text(updated, encoding="utf-8")
        for line in drift:
            print(f"  synced {line}")
    else:
        print(f"  OK: badges already match ({actual['agents']} agents, "
              f"{actual['skills']} skills, {actual['tests']} tests)")
    return 0


def main(argv: list[str]) -> int:
    check_only = False
    tk_dir = default_toolkit_dir

    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--check":
            check_only = True
        elif arg in ("-h", "--help"):
            print(__doc__)
            return 0
        elif arg == "--toolkit-dir":
            idx += 1
            if idx >= len(argv):
                print("ERROR: --toolkit-dir requires a value", file=sys.stderr)
                return 2
            tk_dir = Path(argv[idx])
        elif arg.startswith("-"):
            print(f"ERROR: unknown option: {arg}", file=sys.stderr)
            return 2
        else:
            tk_dir = Path(arg)
        idx += 1

    return sync(tk_dir.resolve(), check_only)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
