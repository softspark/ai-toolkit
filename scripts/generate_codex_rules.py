#!/usr/bin/env python3
"""Generate Codex CLI .agents/rules/ files.

Codex discovers rules in .agents/rules/ at the project root.
This generator follows the same pattern as generate_antigravity.py.

Usage:
  python3 scripts/generate_codex_rules.py [target-dir]

Writes files directly to target-dir/.agents/rules/.
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
    """Write .agents/rules/ files to target_dir."""
    rules = dict(STANDARD_RULES)
    rules.update(build_language_rules(language_modules))
    rules.update(build_registered_rules(rules_dir))
    write_rules(target_dir, rules, ".agents/rules")


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    generate(target)


if __name__ == "__main__":
    main()
