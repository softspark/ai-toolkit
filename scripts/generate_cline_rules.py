#!/usr/bin/env python3
"""Generate .cline/rules/*.md files for Cline.

Cline reads directory-based rules from .cline/rules/*.md (since Q1 2025).
The legacy .clinerules single-file format is still generated separately
by generate_cline.py for backwards compatibility.

Usage:
  python3 scripts/generate_cline_rules.py [target-dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dir_rules_shared import (
    STANDARD_RULES,
    build_language_rules,
    build_registered_rules,
    write_rules,
)


def generate(target_dir: Path, *,
             language_modules: list[str] | None = None,
             rules_dir: Path | None = None) -> None:
    """Write .cline/rules/*.md files to target_dir."""
    rules = dict(STANDARD_RULES)
    rules.update(build_language_rules(language_modules))
    rules.update(build_registered_rules(rules_dir))
    write_rules(target_dir, rules, ".cline/rules")


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    generate(target)


if __name__ == "__main__":
    main()
