#!/usr/bin/env python3
"""Generate .windsurf/hooks.json for Windsurf Cascade.

Writes `<target>/.windsurf/hooks.json`. Existing user hook entries are
preserved; only entries tagged `_source: ai-toolkit` are replaced on
regeneration. Windsurf merges system / user / workspace hooks at runtime, so
this file is safe to live alongside `~/.codeium/windsurf/hooks.json`.

Windsurf Cascade events (per docs.windsurf.com/windsurf/cascade/hooks.md):
    pre_read_code, post_read_code, pre_write_code, post_write_code,
    pre_run_command, post_run_command, pre_mcp_tool_use, post_mcp_tool_use,
    pre_user_prompt, post_cascade_response,
    post_cascade_response_with_transcript, post_setup_worktree
    (12 total).

Pre-hooks can block via exit code 2 (see `guard-destructive.sh`). Each entry
takes `command` (macOS/Linux) + optional `powershell` (Windows). We only emit
`command` because our hook scripts are bash-only.

Usage:
    python3 scripts/generate_windsurf_hooks.py [target-dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HOOKS_PREFIX = '"$HOME/.softspark/ai-toolkit/hooks/'
SOURCE_TAG = "ai-toolkit"

# Event -> list of script names.
WINDSURF_HOOKS: dict[str, list[str]] = {
    "pre_read_code": [
        "guard-path.sh",
    ],
    "pre_write_code": [
        "guard-path.sh",
        "guard-config.sh",
    ],
    "post_write_code": [
        "post-tool-use.sh",
        "governance-capture.sh",
    ],
    "pre_run_command": [
        "guard-destructive.sh",
        "commit-quality.sh",
    ],
    "post_run_command": [
        "governance-capture.sh",
    ],
    "pre_mcp_tool_use": [
        "guard-config.sh",
    ],
    "pre_user_prompt": [
        "user-prompt-submit.sh",
        "track-usage.sh",
    ],
    "post_cascade_response": [
        "quality-check.sh",
        "save-session.sh",
    ],
    "post_setup_worktree": [
        "session-context.sh",
    ],
}


def build_hook_entry(script: str) -> dict:
    """Build a single Windsurf hook entry.

    Uses `bash -c` semantics via the raw command (Windsurf already runs the
    macOS/Linux `command` via `bash -c`).
    """
    return {
        "_source": SOURCE_TAG,
        "command": f"{HOOKS_PREFIX}{script}\"",
        "show_output": False,
    }


def build_toolkit_hooks() -> dict[str, list[dict]]:
    return {event: [build_hook_entry(s) for s in scripts]
            for event, scripts in WINDSURF_HOOKS.items()}


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
    ws_dir = target_dir / ".windsurf"
    ws_dir.mkdir(parents=True, exist_ok=True)
    path = ws_dir / "hooks.json"

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
    doc["hooks"] = merge_hooks(existing_hooks or {}, build_toolkit_hooks())

    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=4, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    return path


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    path = generate(target)
    total = sum(len(v) for v in WINDSURF_HOOKS.values())
    print(f"Generated: {path.relative_to(target) if path.is_relative_to(target) else path} "
          f"({total} hooks across {len(WINDSURF_HOOKS)} events)")


if __name__ == "__main__":
    main()
