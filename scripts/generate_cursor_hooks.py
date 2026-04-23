#!/usr/bin/env python3
"""Generate .cursor/hooks.json for Cursor Agent / Tab.

Writes `<target>/.cursor/hooks.json`. Existing user-authored hook entries are
preserved; entries tagged `_source: ai-toolkit` are the only ones replaced on
regeneration. Top-level `version` is set to 1 (current Cursor schema).

Cursor hook events (per cursor.com/docs/hooks.md):
    Agent:    sessionStart, sessionEnd, preToolUse, postToolUse,
              postToolUseFailure, subagentStart, subagentStop,
              beforeShellExecution, afterShellExecution,
              beforeMCPExecution, afterMCPExecution,
              beforeReadFile, afterFileEdit, beforeSubmitPrompt,
              preCompact, stop, afterAgentResponse, afterAgentThought
    Tab:      beforeTabFileRead, afterTabFileEdit
Entry schema: {"command": "...", "matcher"?: "...", "timeout"?: number}
Exit code 2 blocks the action, so `guard-destructive.sh` continues to work.

Hook scripts are shared with Claude Code and live under
`~/.softspark/ai-toolkit/hooks/`. Cursor runs commands via the shell so the
`"$HOME/..."` expansion works identically.

Usage:
    python3 scripts/generate_cursor_hooks.py [target-dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HOOKS_PREFIX = '"$HOME/.softspark/ai-toolkit/hooks/'
SOURCE_TAG = "ai-toolkit"
SCHEMA_VERSION = 1

# Event -> list of (matcher, script). Empty matcher = omit the field.
CURSOR_HOOKS: dict[str, list[tuple[str, str]]] = {
    "sessionStart": [
        ("", "session-start.sh"),
        ("", "mcp-health.sh"),
        ("", "session-context.sh"),
    ],
    "beforeShellExecution": [
        ("", "guard-destructive.sh"),
        ("", "commit-quality.sh"),
    ],
    "beforeReadFile": [
        ("", "guard-path.sh"),
    ],
    "afterFileEdit": [
        ("", "post-tool-use.sh"),
        ("", "governance-capture.sh"),
    ],
    "beforeSubmitPrompt": [
        ("", "user-prompt-submit.sh"),
        ("", "track-usage.sh"),
    ],
    "beforeMCPExecution": [
        ("", "guard-config.sh"),
    ],
    "preCompact": [
        ("", "pre-compact.sh"),
        ("", "pre-compact-save.sh"),
    ],
    "subagentStart": [
        ("", "subagent-start.sh"),
    ],
    "subagentStop": [
        ("", "subagent-stop.sh"),
    ],
    "stop": [
        ("", "quality-check.sh"),
        ("", "save-session.sh"),
    ],
    "sessionEnd": [
        ("", "session-end.sh"),
    ],
}


def build_hook_entry(matcher: str, script: str) -> dict:
    entry: dict = {
        "_source": SOURCE_TAG,
        "command": f"{HOOKS_PREFIX}{script}\"",
    }
    if matcher:
        entry["matcher"] = matcher
    return entry


def build_toolkit_hooks() -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for event, entries in CURSOR_HOOKS.items():
        result[event] = [build_hook_entry(m, s) for m, s in entries]
    return result


def _is_toolkit_entry(entry: dict) -> bool:
    return isinstance(entry, dict) and entry.get("_source") == SOURCE_TAG


def strip_toolkit_hooks(hooks: dict) -> dict:
    kept: dict = {}
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            kept[event] = entries
            continue
        survivors = [e for e in entries if not _is_toolkit_entry(e)]
        if survivors:
            kept[event] = survivors
    return kept


def merge_hooks(existing: dict, toolkit: dict) -> dict:
    merged = strip_toolkit_hooks(existing)
    for event, entries in toolkit.items():
        merged.setdefault(event, []).extend(entries)
    return merged


def generate(target_dir: Path) -> Path:
    cursor_dir = target_dir / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    path = cursor_dir / "hooks.json"

    doc: dict = {}
    if path.is_file():
        try:
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
            if not isinstance(doc, dict):
                doc = {}
        except (json.JSONDecodeError, OSError):
            doc = {}

    existing_hooks = doc.get("hooks") if isinstance(doc.get("hooks"), dict) else {}
    doc["version"] = SCHEMA_VERSION
    doc["hooks"] = merge_hooks(existing_hooks or {}, build_toolkit_hooks())

    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=4, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    return path


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    path = generate(target)
    total = sum(len(v) for v in CURSOR_HOOKS.values())
    print(f"Generated: {path.relative_to(target) if path.is_relative_to(target) else path} "
          f"({total} hooks across {len(CURSOR_HOOKS)} events)")


if __name__ == "__main__":
    main()
