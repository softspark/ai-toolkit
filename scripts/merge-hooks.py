#!/usr/bin/env python3
"""Merge ai-toolkit hooks into a settings.json file (or strip them).

Usage:
    merge-hooks.py inject <toolkit-hooks.json> <target-settings.json>
    merge-hooks.py strip  <target-settings.json>

inject: Reads toolkit hooks (tagged with "_source": "ai-toolkit"),
        removes any previous toolkit entries from target's "hooks" key,
        appends current toolkit entries, and writes the result.
        Preserves all other keys in the target settings file.
        Creates target with just {"hooks": ...} if missing.

strip:  Removes all entries with "_source": "ai-toolkit" from target's
        "hooks" key. Removes the "hooks" key if empty. Never deletes
        the target file (it may contain other settings).

Exit codes:
    0  success
    1  usage error
    2  JSON parse error
"""
from __future__ import annotations

import json
import os
import sys

SOURCE_TAG = "ai-toolkit"


def load_json(path: str) -> dict:
    """Load and parse a JSON file.

    Args:
        path: Filesystem path to the JSON file.

    Returns:
        Parsed JSON content as a dictionary.
    """
    with open(path) as f:
        return json.load(f)


def save_json(path: str, data: dict) -> None:
    """Write a dictionary to a JSON file with 4-space indent and trailing newline.

    Args:
        path: Filesystem path for the output JSON file.
        data: Dictionary to serialize.
    """
    with open(path, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")


def _is_toolkit_entry(entry: dict) -> bool:
    """Check if a hook entry (at any nesting level) is from ai-toolkit."""
    if entry.get("_source") == SOURCE_TAG:
        return True
    # Check nested hooks array for _source tag
    for hook in entry.get("hooks", []):
        if isinstance(hook, dict) and hook.get("_source") == SOURCE_TAG:
            return True
    return False


def strip_toolkit(hooks: dict) -> dict:
    """Remove all entries tagged with _source == SOURCE_TAG."""
    result = {}
    for event, entries in hooks.items():
        filtered = [e for e in entries if not _is_toolkit_entry(e)]
        if filtered:
            result[event] = filtered
    return result


def merge(toolkit_hooks: dict, target_hooks: dict) -> dict:
    """Strip old toolkit entries, then append current toolkit entries.

    Args:
        toolkit_hooks: Hook entries from the toolkit source file.
        target_hooks: Existing hook entries in the target settings.

    Returns:
        Merged hooks dictionary with old toolkit entries replaced by new ones.
    """
    merged = strip_toolkit(target_hooks)
    for event, entries in toolkit_hooks.items():
        if event not in merged:
            merged[event] = []
        merged[event].extend(entries)
    return merged


def cmd_inject(toolkit_path: str, target_path: str) -> None:
    """Inject toolkit hooks into a target settings file.

    Reads toolkit hooks, strips previous toolkit entries from the target,
    appends the current toolkit entries, and writes the result. Creates
    the target file if it does not exist.

    Args:
        toolkit_path: Path to the toolkit hooks JSON file.
        target_path: Path to the target settings JSON file.
    """
    try:
        toolkit_data = load_json(toolkit_path)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error reading toolkit hooks: {e}", file=sys.stderr)
        sys.exit(2)

    toolkit_hooks = toolkit_data.get("hooks", {})
    toolkit_statusline = toolkit_data.get("statusLine")

    # Load existing target settings (preserving all non-hooks keys)
    target_settings: dict = {}
    if os.path.islink(target_path):
        # Old-style symlink — remove it, start fresh
        os.remove(target_path)
    elif os.path.isfile(target_path):
        try:
            target_settings = load_json(target_path)
        except json.JSONDecodeError as e:
            print(f"Error parsing target settings: {e}", file=sys.stderr)
            sys.exit(2)

    target_hooks = target_settings.get("hooks", {})
    result = merge(toolkit_hooks, target_hooks)

    target_settings["hooks"] = result

    # statusLine: only set if absent OR previously installed by ai-toolkit.
    # User-customized statusLine (no _source tag) is preserved.
    if toolkit_statusline is not None:
        existing_sl = target_settings.get("statusLine")
        if existing_sl is None or (
            isinstance(existing_sl, dict) and existing_sl.get("_source") == SOURCE_TAG
        ):
            target_settings["statusLine"] = toolkit_statusline
        # else: user has a custom statusLine, leave it alone

    save_json(target_path, target_settings)


def cmd_strip(target_path: str) -> None:
    """Remove all ai-toolkit hook entries from a target settings file.

    Removes entries tagged with the ai-toolkit source marker. If no hooks
    remain, the ``hooks`` key is removed from the settings. Handles
    legacy symlink targets by deleting the symlink.

    Args:
        target_path: Path to the target settings JSON file.
    """
    if os.path.islink(target_path):
        os.remove(target_path)
        return

    if not os.path.isfile(target_path):
        return

    try:
        target_settings = load_json(target_path)
    except json.JSONDecodeError as e:
        print(f"Error parsing target settings: {e}", file=sys.stderr)
        sys.exit(2)

    result = strip_toolkit(target_settings.get("hooks", {}))
    if result:
        target_settings["hooks"] = result
    else:
        target_settings.pop("hooks", None)

    # Strip toolkit-installed statusLine (user-customized one is preserved).
    sl = target_settings.get("statusLine")
    if isinstance(sl, dict) and sl.get("_source") == SOURCE_TAG:
        target_settings.pop("statusLine", None)

    save_json(target_path, target_settings)


def main() -> None:
    """Parse CLI arguments and dispatch to inject or strip sub-commands."""
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "inject":
        if len(sys.argv) != 4:
            print("Usage: merge-hooks.py inject <toolkit-hooks> <target-settings>", file=sys.stderr)
            sys.exit(1)
        cmd_inject(sys.argv[2], sys.argv[3])

    elif cmd == "strip":
        if len(sys.argv) != 3:
            print("Usage: merge-hooks.py strip <target-settings>", file=sys.stderr)
            sys.exit(1)
        cmd_strip(sys.argv[2])

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
