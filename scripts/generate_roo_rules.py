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
             rules_dir: Path | None = None,
             output_root: Path | None = None) -> None:
    """Write Roo Code rule files.

    By default writes project-local ``target_dir/.roo/rules/*.md``. When
    ``output_root`` is provided, writes directly into that directory for
    documented global rules such as ``~/.roo/rules``.
    """
    rules = dict(STANDARD_RULES)
    rules.update(build_language_rules(language_modules))
    rules.update(build_registered_rules(rules_dir))
    root = output_root.parent if output_root is not None else target_dir
    subdir = output_root.name if output_root is not None else ".roo/rules"
    write_rules(root, rules, subdir)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    from paths import RULES_DIR
    generate(target, rules_dir=RULES_DIR)


if __name__ == "__main__":
    main()
