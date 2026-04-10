#!/usr/bin/env python3
"""Generate .roo/rules/*.md shared rules for Roo Code.

Roo Code reads shared rules from .roo/rules/*.md (applied to all modes).
The .roomodes JSON is still generated separately by generate_roo_modes.py.

Usage:
  python3 scripts/generate_roo_rules.py [target-dir]
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
    """Write .roo/rules/*.md files to target_dir."""
    rules = dict(STANDARD_RULES)
    rules.update(build_language_rules(language_modules))
    rules.update(build_registered_rules(rules_dir))
    write_rules(target_dir, rules, ".roo/rules")


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    generate(target)


if __name__ == "__main__":
    main()
