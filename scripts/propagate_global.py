#!/usr/bin/env python3
"""Propagate rules, hooks, and MCP configs to all globally installed editors.

Called automatically after inject-rule, inject-hook, add-rule, remove-rule,
and mcp add to keep global editor configs in sync.

Usage:
    propagate_global.py [--rules] [--hooks] [--mcp]

Flags (can combine):
    --rules   Re-inject registered rules into global editor configs
    --hooks   Re-inject external hooks into Codex global hooks.json
    --mcp     Sync MCP templates to global editor MCP configs

With no flags, propagates rules (the most common case).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def propagate_rules() -> None:
    """Re-inject registered rules into all global editors from state."""
    from paths import RULES_DIR
    from install_steps.install_state import get_global_editors

    editors = get_global_editors()
    if not editors:
        return

    target_dir = Path.home()
    rules_dir = RULES_DIR

    from install_steps.ai_tools import install_ai_tools
    print("Propagating rules to global editors...")
    install_ai_tools(target_dir, rules_dir, dry_run=False, editors=editors)


def propagate_hooks() -> None:
    """Re-inject URL-sourced hooks into Codex global hooks.json."""
    from install_steps.install_state import get_global_editors

    editors = get_global_editors()
    if "codex" not in editors:
        return

    # Hooks are already propagated to Codex by inject_hook_cli.py
    # This is a no-op — kept for completeness and future editors with hooks
    pass


def propagate_mcp() -> None:
    """Sync globally tracked MCP templates to global editor MCP configs."""
    from install_steps.install_state import get_global_editors, get_mcp_templates

    editors = get_global_editors()
    templates = get_mcp_templates()
    if not editors or not templates:
        return

    # MCP editor sync is handled by mcp_manager.py install --editor --scope global
    import subprocess
    scripts_dir = Path(__file__).resolve().parent

    for editor in editors:
        try:
            subprocess.run(
                ["python3", str(scripts_dir / "mcp_manager.py"),
                 "install", "--editor", editor, "--scope", "global"] + templates,
                capture_output=True, text=True, timeout=30,
            )
            print(f"  MCP synced to {editor} (global)")
        except Exception as exc:
            print(f"  Warning: MCP sync to {editor} failed: {exc}")


def main() -> None:
    args = set(sys.argv[1:])

    if not args or "--rules" in args:
        propagate_rules()
    if "--hooks" in args:
        propagate_hooks()
    if "--mcp" in args:
        propagate_mcp()


if __name__ == "__main__":
    main()
