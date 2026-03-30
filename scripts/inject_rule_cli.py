#!/usr/bin/env python3
"""CLI wrapper around inject_rule() and remove_rule_section() from _common.

Injects a rule file into CLAUDE.md using idempotent marker-based injection.
Re-running updates only the marked section. Content outside markers is
never touched.

Usage:
  inject_rule_cli.py <rule-file> [target-dir]
  inject_rule_cli.py --remove <rule-name> [target-dir]

Arguments:
  rule-file   Path to a .md file with the rule content
  target-dir  Directory containing .claude/CLAUDE.md (default: $HOME)

Flags:
  --remove    Remove a rule section instead of injecting
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import inject_rule, remove_rule_section


def _parse_args(argv: list[str]) -> dict:
    """Parse CLI arguments."""
    result: dict = {
        "remove_mode": False,
        "remove_name": "",
        "source_file": "",
        "target_dir": str(Path.home()),
    }

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--remove":
            result["remove_mode"] = True
            i += 1
            if i >= len(argv):
                print("--remove requires a rule name", file=sys.stderr)
                sys.exit(1)
            result["remove_name"] = argv[i]
        elif arg.startswith("-"):
            print(f"Unknown option: {arg}", file=sys.stderr)
            sys.exit(1)
        elif not result["source_file"] and not result["remove_mode"]:
            result["source_file"] = arg
        else:
            result["target_dir"] = arg
        i += 1

    return result


def main() -> None:
    """Inject or remove a rule in CLAUDE.md."""
    args = _parse_args(sys.argv[1:])
    target_dir = Path(args["target_dir"])
    claude_md = target_dir / ".claude" / "CLAUDE.md"

    # -- remove mode ---------------------------------------------------------
    if args["remove_mode"]:
        rule_name = args["remove_name"]
        if not claude_md.is_file():
            print(f"No CLAUDE.md found at {target_dir}", file=sys.stderr)
            sys.exit(1)

        found = remove_rule_section(rule_name, target_dir)
        if found:
            print(f"Removed rule '{rule_name}' from {claude_md}")
        else:
            print(f"Rule '{rule_name}' not found in {claude_md}")
        return

    # -- inject mode ---------------------------------------------------------
    source_file = args["source_file"]
    if not source_file:
        print("Usage: inject_rule_cli.py <rule-file> [target-dir]", file=sys.stderr)
        print("       inject_rule_cli.py --remove <rule-name> [target-dir]", file=sys.stderr)
        sys.exit(1)

    source_path = Path(source_file)
    if not source_path.is_file():
        print(f"Rule file not found: {source_path}", file=sys.stderr)
        sys.exit(1)

    # Ensure .claude/ directory and CLAUDE.md exist
    claude_md.parent.mkdir(parents=True, exist_ok=True)
    if not claude_md.is_file():
        print(f"Created: {claude_md}")

    action = inject_rule(source_path, target_dir)
    print(f"  {action}: {claude_md}")


if __name__ == "__main__":
    main()
