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
from dir_rules_shared import (
    STANDARD_RULES,
    build_language_rules,
    build_registered_rules,
    write_rules,
)


def generate(target_dir: Path, *,
             language_modules: list[str] | None = None,
             rules_dir: Path | None = None) -> None:
    """Write .windsurf/rules/*.md files to target_dir."""
    rules = dict(STANDARD_RULES)
    rules.update(build_language_rules(language_modules))
    rules.update(build_registered_rules(rules_dir))
    write_rules(target_dir, rules, ".windsurf/rules")


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    from paths import RULES_DIR
    generate(target, rules_dir=RULES_DIR)


if __name__ == "__main__":
    main()
