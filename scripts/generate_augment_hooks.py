#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate Augment settings.json hooks block.

Augment reads hooks from several settings.json layers (per
docs.augmentcode.com/cli/v0/hooks): `<workspace>/.augment/settings.local.json`,
`<workspace>/.augment/settings.json`, `~/.augment/settings.json` (user scope),
and `/etc/augment/settings.json` (system policy). This generator writes the
user-scope file: it accepts an optional target directory and defaults to the
user's `$HOME`, writing `~/.augment/settings.json`. Project-local hook emission
for `--local` installs is a possible future extension.

The same user settings can serve Auggie 1.x and 0.x. Match both generations
of native tool names with one hook per action.
Augment hook events (per docs.augmentcode.com/cli/hooks.md):
    PreToolUse, PostToolUse, SessionStart, SessionEnd, Stop
Schema mirrors Claude Code — each event holds an array of groups, each group
holds `{matcher?, hooks: [{type, command, timeout?}]}`. We tag the outer group
with `_source: ai-toolkit` so we can strip and rewrite idempotently without
clobbering user hook groups.

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcp_editors import ConfigUpdate, apply_config_updates
from secure_fs import apply_owned_edits, lexical_absolute

HOOKS_PREFIX = 'AI_TOOLKIT_HOOK_FORMAT=json "$HOME/.softspark/ai-toolkit/hooks/'
SOURCE_TAG = "ai-toolkit"
SHELL = "^(bash|launch-process)$"
FILE_ACCESS = "^(read|grep|find|ls|edit|write|view|str-replace-editor|save-file|remove-files)$"
FILE_EDIT = "^(edit|write|str-replace-editor|save-file)$"

# Event -> list of (matcher, script). Matcher is a regex over tool_name.
AUGMENT_HOOKS: dict[str, list[tuple[str, str]]] = {
    "SessionStart": [
        ("", "session-start.sh"),
        ("", "mcp-health.sh"),
    ],
    "PreToolUse": [
        (SHELL, "guard-destructive.sh"),
        (SHELL, "commit-quality.sh"),
        (SHELL, "revert-guard.sh"),
        (FILE_ACCESS, "guard-path.sh"),
        (FILE_EDIT, "guard-config.sh"),
    ],
    "PostToolUse": [
        (FILE_EDIT, "post-tool-use.sh"),
        (FILE_EDIT, "test-cohesion.sh"),
        (f"{SHELL}|{FILE_EDIT}", "governance-capture.sh"),
        ("^(web-fetch|web-search|codebase-retrieval)$", "search-tracker.sh"),
    ],
    "Stop": [
        ("", "quality-check.sh"),
        ("", "save-session.sh"),
        ("", "stop-search-check.sh"),
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
        survivors = []
        for entry in entries:
            if not _is_toolkit_entry(entry):
                survivors.append(entry)
            elif entry.get("_source") != SOURCE_TAG:
                # Before 2.13 each handler carried its own ownership tag.
                handlers = [h for h in entry["hooks"] if not isinstance(h, dict) or h.get("_source") != SOURCE_TAG]
                if handlers:
                    survivors.append({**entry, "hooks": handlers})
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
    path = aug_dir / "settings.json"
    if target_dir.is_symlink() or aug_dir.is_symlink() or path.is_symlink():
        raise RuntimeError(f"Refusing symlinked Augment settings path: {path}")
    settings: dict = {}
    original = path.read_bytes() if path.exists() else None
    if original is not None:
        settings = json.loads(original.decode("utf-8"))
        if not isinstance(settings, dict):
            raise ValueError(f"Expected an Augment settings object in {path}")

    existing_hooks = settings.get("hooks", {})
    if not isinstance(existing_hooks, dict):
        raise ValueError(f"Expected an Augment hooks object in {path}")
    settings["hooks"] = merge_hooks(existing_hooks, build_toolkit_hooks())

    content = (json.dumps(settings, indent=4, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    apply_config_updates([ConfigUpdate(path, original, content)])
    return path


def _strip_settings(content: bytes) -> tuple[bytes | None, int]:
    """Strip ai-toolkit hook groups; ``None`` when nothing else remains."""
    try:
        settings = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return content, 0
    if not isinstance(settings, dict) or not isinstance(settings.get("hooks"), dict):
        return content, 0
    hooks = settings["hooks"]
    count = sum(
        1
        for entries in hooks.values()
        if isinstance(entries, list)
        for entry in entries
        if _is_toolkit_entry(entry)
    )
    if not count:
        return content, 0
    survivors = strip_toolkit_hooks(hooks)
    if survivors:
        settings["hooks"] = survivors
    else:
        settings.pop("hooks")
    if not settings:
        return None, count
    rendered = json.dumps(settings, indent=4, ensure_ascii=False, sort_keys=True)
    return (rendered + "\n").encode("utf-8"), count


def _apply(target_dir: Path, *, dry_run: bool) -> int:
    """Run the settings edit and return the hook groups it strips.

    The count is taken from the same pinned bytes the edit rewrites.
    """
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Augment target directory: {target}")
    aug_dir = target / ".augment"
    if aug_dir.is_symlink():
        raise RuntimeError(f"Refusing symlinked Augment settings directory: {aug_dir}")
    path = aug_dir / "settings.json"
    stripped: list[int] = []

    def edit(content: bytes) -> bytes | None:
        updated, count = _strip_settings(content)
        stripped.append(count)
        return updated

    apply_owned_edits(
        {path: edit} if path.is_file() else {},
        target,
        label="Augment settings.json",
        prune=(aug_dir,),
        dry_run=dry_run,
    )
    return sum(stripped)


def discover(target_dir: Path) -> int:
    """Count ai-toolkit hook groups in ``<target_dir>/.augment/settings.json``."""
    return _apply(target_dir, dry_run=True)


def cleanup(target_dir: Path) -> int:
    """Strip ai-toolkit hook groups and return how many were removed.

    ``target_dir`` is HOME for both install scopes. User hook groups and
    other settings are preserved; the file is deleted only when empty.
    """
    return _apply(target_dir, dry_run=False)


def main() -> None:
    target = _resolve_target_dir(sys.argv)
    path = generate(target)
    total = sum(len(v) for v in AUGMENT_HOOKS.values())
    print(f"Generated: {path} ({total} hooks across {len(AUGMENT_HOOKS)} events)")


if __name__ == "__main__":
    main()
