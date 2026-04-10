#!/usr/bin/env python3
"""Generate .clinerules/*.md files for Cline.

Cline reads rules from the .clinerules/ directory (since Cline 3.7).
Each .md file inside .clinerules/ is automatically loaded.
The legacy .clinerules single-file format is replaced by this directory.

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
    """Write .clinerules/*.md files to target_dir."""
    # Migrate: if .clinerules exists as a single file, remove it
    # so the directory can be created (Cline 3.7+ uses directory format)
    clinerules = target_dir / ".clinerules"
    if clinerules.is_file():
        clinerules.unlink()
    rules = dict(STANDARD_RULES)
    rules.update(build_language_rules(language_modules))
    rules.update(build_registered_rules(rules_dir))
    write_rules(target_dir, rules, ".clinerules")


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    generate(target)


if __name__ == "__main__":
    main()
