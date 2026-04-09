#!/usr/bin/env python3
"""Generate .windsurf/rules/*.md files for Windsurf IDE.

Windsurf reads directory-based rules from .windsurf/rules/*.md (since mid-2025).
The legacy .windsurfrules single-file format is still generated separately
by generate_windsurf.py for backwards compatibility.

Usage:
  python3 scripts/generate_windsurf_rules.py [target-dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dir_rules_shared import STANDARD_RULES, write_rules


def generate(target_dir: Path) -> None:
    """Write .windsurf/rules/*.md files to target_dir."""
    write_rules(target_dir, STANDARD_RULES, ".windsurf/rules")


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    generate(target)


if __name__ == "__main__":
    main()
