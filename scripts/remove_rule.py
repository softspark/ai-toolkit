#!/usr/bin/env python3
"""remove-rule -- Unregister a rule (opposite of add-rule).

Removes the rule file from ~/.ai-toolkit/rules/ (so it is no longer
re-applied on future 'ai-toolkit install' runs) AND strips its injected
block from the target CLAUDE.md.

Usage:
  remove_rule.py <rule-name> [target-dir]

Arguments:
  rule-name   Name of the rule (filename without .md)
  target-dir  Directory containing .claude/CLAUDE.md (default: $HOME)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import remove_rule_section


def main() -> None:
    """Unregister a rule and strip its injected block."""
    if len(sys.argv) < 2:
        print("Usage: remove_rule.py <rule-name> [target-dir]", file=sys.stderr)
        sys.exit(1)

    rule_name = sys.argv[1]
    target_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home()
    rules_dir = Path.home() / ".ai-toolkit" / "rules"

    removed = 0

    # 1. Unregister from ~/.ai-toolkit/rules/
    rule_file = rules_dir / f"{rule_name}.md"
    if rule_file.is_file():
        rule_file.unlink()
        print(f"Unregistered: '{rule_name}' (removed from {rules_dir})")
        removed += 1
    else:
        print(f"Not registered: '{rule_name}' not found in {rules_dir}")

    # 2. Strip injected block from .claude/CLAUDE.md
    found = remove_rule_section(rule_name, target_dir)
    if found:
        print(f"Removed rule '{rule_name}' from {target_dir / '.claude' / 'CLAUDE.md'}")
        removed += 1

    if removed == 0:
        print()
        print("Nothing to unregister. To list registered rules:")
        print("  ls ~/.ai-toolkit/rules/")


if __name__ == "__main__":
    main()
