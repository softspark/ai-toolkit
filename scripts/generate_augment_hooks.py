#!/usr/bin/env python3
"""Generate Augment settings.json hooks block.

Augment stores hooks in `~/.augment/settings.json` (user scope) — there is no
per-workspace hooks file. `/etc/augment/settings.json` exists for system-wide
policy and we never write there. The generator accepts an optional target
directory; when omitted it defaults to the user's `$HOME` and writes
`~/.augment/settings.json`.

Augment hook events (per docs.augmentcode.com/cli/hooks.md):
    PreToolUse, PostToolUse, SessionStart, SessionEnd, Stop
Schema mirrors Claude Code — each event holds an array of groups, each group
holds `{matcher?, hooks: [{type, command, timeout?}]}`. We tag the outer group
with `_source: ai-toolkit` so we can strip and rewrite idempotently without
clobbering user hook groups.

Common Augment tool names relevant to our hooks:
    launch-process (shell), view (read), str-replace-editor (edit),
    save-file (write), remove-files (delete), web-fetch, web-search,
    codebase-retrieval, github-api, linear.

Usage:
    python3 scripts/generate_augment_hooks.py [target-dir]

`target-dir` is the HOME-equivalent directory (default: `$HOME`). The
settings file is written to `<target-dir>/.augment/settings.json`.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HOOKS_PREFIX = '"$HOME/.softspark/ai-toolkit/hooks/'
SOURCE_TAG = "ai-toolkit"

# Event -> list of (matcher, script). Matcher is a regex over tool_name.
AUGMENT_HOOKS: dict[str, list[tuple[str, str]]] = {
    "SessionStart": [
        ("", "session-start.sh"),
        ("", "mcp-health.sh"),
        ("", "session-context.sh"),
    ],
    "PreToolUse": [
        ("launch-process", "guard-destructive.sh"),
        ("launch-process", "commit-quality.sh"),
        ("view|str-replace-editor|save-file|remove-files", "guard-path.sh"),
        ("str-replace-editor|save-file", "guard-config.sh"),
    ],
    "PostToolUse": [
        ("str-replace-editor|save-file", "post-tool-use.sh"),
        ("launch-process|str-replace-editor|save-file", "governance-capture.sh"),
    ],
    "Stop": [
        ("", "quality-check.sh"),
        ("", "save-session.sh"),
    ],
    "SessionEnd": [
        ("", "session-end.sh"),
    ],
}


def build_hook_group(matcher: str, script: str) -> dict:
    """Build a single Augment hook group (merge-safe shape)."""
    group: dict = {
        "_source": SOURCE_TAG,
        "hooks": [
            {
                "type": "command",
                "command": f"{HOOKS_PREFIX}{script}\"",
            }
        ],
    }
    # Augment ignores `matcher` on session events; omit cleanly so it doesn't
    # show up as a spurious regex-against-nothing in their logs.
    if matcher:
        group["matcher"] = matcher
    return group


def build_toolkit_hooks() -> dict[str, list[dict]]:
    return {event: [build_hook_group(m, s) for m, s in entries]
            for event, entries in AUGMENT_HOOKS.items()}


def _is_toolkit_entry(entry: dict) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get("_source") == SOURCE_TAG:
        return True
    # Pre-2.13 layout tagged the inner hook dict instead of the outer group.
    for h in entry.get("hooks", []) or []:
        if isinstance(h, dict) and h.get("_source") == SOURCE_TAG:
            return True
    return False


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


def _resolve_target_dir(argv: list[str]) -> Path:
    """Accept an explicit target dir or fall back to $HOME."""
    if len(argv) > 1 and argv[1]:
        return Path(argv[1])
    home = os.environ.get("HOME")
    if not home:
        raise SystemExit("HOME is not set and no target directory was provided.")
    return Path(home)


def generate(target_dir: Path) -> Path:
    """Write `<target_dir>/.augment/settings.json` and return its path."""
    aug_dir = target_dir / ".augment"
    aug_dir.mkdir(parents=True, exist_ok=True)
    path = aug_dir / "settings.json"

    settings: dict = {}
    if path.is_file():
        try:
            with open(path, encoding="utf-8") as f:
                settings = json.load(f)
            if not isinstance(settings, dict):
                settings = {}
        except (json.JSONDecodeError, OSError):
            settings = {}

    existing_hooks = settings.get("hooks") if isinstance(settings.get("hooks"), dict) else {}
    settings["hooks"] = merge_hooks(existing_hooks or {}, build_toolkit_hooks())

    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    return path


def main() -> None:
    target = _resolve_target_dir(sys.argv)
    path = generate(target)
    total = sum(len(v) for v in AUGMENT_HOOKS.values())
    print(f"Generated: {path} ({total} hooks across {len(AUGMENT_HOOKS)} events)")


if __name__ == "__main__":
    main()
