#!/usr/bin/env python3
"""Generate .codex/hooks.json for OpenAI Codex CLI.

Maps compatible ai-toolkit hooks to Codex lifecycle events.
Hook scripts are shared with Claude Code (stored in ~/.softspark/ai-toolkit/hooks/).

Codex supports 5 events: SessionStart, PreToolUse, PostToolUse,
UserPromptSubmit, Stop. PreToolUse/PostToolUse only support Bash matcher.

Usage:
  python3 scripts/generate_codex_hooks.py [target-dir]

Writes .codex/hooks.json to target-dir.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


HOOKS_PREFIX = '"$HOME/.softspark/ai-toolkit/hooks/'

# Hooks compatible with Codex, grouped by event.
# Format: (matcher, script_name)
CODEX_HOOKS: dict[str, list[tuple[str, str]]] = {
    "SessionStart": [
        ("startup|resume", "session-start.sh"),
        ("startup|resume", "mcp-health.sh"),
        ("startup|resume", "session-context.sh"),
    ],
    "PreToolUse": [
        ("Bash", "guard-destructive.sh"),
        ("Bash", "commit-quality.sh"),
    ],
    "UserPromptSubmit": [
        ("", "user-prompt-submit.sh"),
        ("", "track-usage.sh"),
    ],
    "Stop": [
        ("", "quality-check.sh"),
        ("", "save-session.sh"),
    ],
}


def build_hooks_json() -> dict:
    """Build the hooks.json structure for Codex."""
    hooks: dict[str, list] = {}
    for event, entries in CODEX_HOOKS.items():
        hooks[event] = []
        for matcher, script in entries:
            entry: dict = {"hooks": [{"type": "command", "command": f"{HOOKS_PREFIX}{script}\""}]}
            if matcher:
                entry["matcher"] = matcher
            hooks[event].append(entry)
    return {"hooks": hooks}


def generate(target_dir: Path) -> None:
    """Write .codex/hooks.json to target_dir."""
    codex_dir = target_dir / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    hooks_path = codex_dir / "hooks.json"
    data = build_hooks_json()
    with open(hooks_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    generate(target)
    print(f"Generated: .codex/hooks.json ({sum(len(v) for v in CODEX_HOOKS.values())} hooks)")


if __name__ == "__main__":
    main()
