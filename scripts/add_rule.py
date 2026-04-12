#!/usr/bin/env python3
"""add-rule -- Register a rule file in ~/.softspark/ai-toolkit/rules/.

Registered rules are automatically injected into all AI tool configs
on next 'ai-toolkit install' or 'ai-toolkit update':
  Global: Claude, Cursor, Windsurf, Gemini, Augment
  Local (--local): all of the above + Copilot, Cline, Roo, Aider, Antigravity

Usage:
  add_rule.py <rule-file> [rule-name]

Arguments:
  rule-file   Path to .md file with the rule content
  rule-name   Override the rule name (default: filename without .md)
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    """Register a rule file in the global rules directory."""
    if len(sys.argv) < 2:
        print("Usage: add_rule.py <rule-file> [rule-name]", file=sys.stderr)
        sys.exit(1)

    rule_file = Path(sys.argv[1])
    if not rule_file.is_file():
        print(f"Rule file not found: {rule_file}", file=sys.stderr)
        sys.exit(1)

    rule_name = sys.argv[2] if len(sys.argv) > 2 else rule_file.stem
    rule_name = re.sub(r"[^a-zA-Z0-9_-]", "", rule_name)
    if not rule_name:
        print("Error: rule name is empty after sanitization", file=sys.stderr)
        sys.exit(1)
    from paths import RULES_DIR
    rules_dir = RULES_DIR
    rules_dir.mkdir(parents=True, exist_ok=True)

    dest = rules_dir / f"{rule_name}.md"
    shutil.copy2(rule_file, dest)

    print(f"Registered: '{rule_name}' -> {dest}")
    print()
    print("Apply now:")
    print("  ai-toolkit update            # global (Claude, Cursor, Windsurf, Gemini, Augment)")
    print("  ai-toolkit update --local    # project-local (all editors)")


if __name__ == "__main__":
    main()
