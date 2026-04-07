#!/usr/bin/env python3
"""Inject external hooks into ~/.claude/settings.json.

Allows external tools (MCP servers, plugins, etc.) to register their own
hooks alongside ai-toolkit's hooks.  Each injected file is tagged with a
``_source`` derived from the filename stem so that re-running is idempotent
and removal is safe.

Usage:
    inject_hook_cli.py <hooks-file.json> [target-dir]
    inject_hook_cli.py --remove <hook-source-name> [target-dir]

Arguments:
    hooks-file    Path to a JSON file with ``{"hooks": {"EventName": [...]}}``
    target-dir    Directory containing ``.claude/settings.json`` (default: $HOME)

Flags:
    --remove      Remove all hook entries tagged with the given source name

The source name is derived from the filename stem (e.g.,
``rag-mcp-hooks.json`` becomes ``"rag-mcp-hooks"``).  All entries are tagged
with ``"_source": "<source-name>"`` for idempotent updates.  Re-running
replaces old entries with the same source name.

Entries tagged with ``_source: "ai-toolkit"`` are **never** modified -- those
are managed exclusively by the toolkit itself.

Exit codes:
    0  success
    1  usage / argument error
    2  JSON parse error
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Protected source tag -- this CLI must never touch ai-toolkit's own entries.
PROTECTED_SOURCE = "ai-toolkit"


# ---------------------------------------------------------------------------
# JSON helpers (same style as merge-hooks.py)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _entry_source(entry: dict) -> str | None:
    """Return the ``_source`` tag of a hook entry, checking nested hooks too.

    Args:
        entry: A single hook entry dict.

    Returns:
        The source string, or ``None`` if untagged.
    """
    if "_source" in entry:
        return entry["_source"]
    for hook in entry.get("hooks", []):
        if isinstance(hook, dict) and "_source" in hook:
            return hook["_source"]
    return None


def strip_source(hooks: dict, source: str) -> dict:
    """Remove all entries whose ``_source`` matches *source*.

    Args:
        hooks: Existing hooks dict (event-name -> list of entries).
        source: Source tag to strip.

    Returns:
        New hooks dict with matching entries removed.  Empty event lists
        are omitted.
    """
    result: dict = {}
    for event, entries in hooks.items():
        filtered = [e for e in entries if _entry_source(e) != source]
        if filtered:
            result[event] = filtered
    return result


def tag_entries(hooks: dict, source: str) -> dict:
    """Tag every entry in *hooks* with ``"_source": source``.

    Operates on top-level entries only (not nested ``hooks`` arrays) to
    match the convention used in ``app/hooks.json``.

    Args:
        hooks: Hook entries to tag (event-name -> list of entries).
        source: Source tag to apply.

    Returns:
        New hooks dict with all entries tagged.
    """
    result: dict = {}
    for event, entries in hooks.items():
        tagged = []
        for entry in entries:
            entry_copy = dict(entry)
            entry_copy["_source"] = source
            tagged.append(entry_copy)
        result[event] = tagged
    return result


def merge_hooks(new_hooks: dict, existing_hooks: dict, source: str) -> dict:
    """Strip old entries for *source*, then append *new_hooks*.

    Args:
        new_hooks: Tagged hook entries to inject.
        existing_hooks: Current hooks from the settings file.
        source: Source tag being injected.

    Returns:
        Merged hooks dict.
    """
    merged = strip_source(existing_hooks, source)
    for event, entries in new_hooks.items():
        if event not in merged:
            merged[event] = []
        merged[event].extend(entries)
    return merged


# ---------------------------------------------------------------------------
# CLI actions
# ---------------------------------------------------------------------------

def inject(hooks_file: str, target_dir: str) -> None:
    """Inject hooks from *hooks_file* into the target settings.json.

    Args:
        hooks_file: Path to the external hooks JSON file.
        target_dir: Directory containing ``.claude/settings.json``.
    """
    # Derive source name from filename stem
    source = Path(hooks_file).stem
    if source == PROTECTED_SOURCE:
        print(
            f"Error: source name '{PROTECTED_SOURCE}' is reserved. "
            "Rename your hooks file.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load the hooks file
    try:
        hooks_data = load_json(hooks_file)
    except json.JSONDecodeError as exc:
        print(f"Error: malformed JSON in {hooks_file}: {exc}", file=sys.stderr)
        sys.exit(2)
    except OSError as exc:
        print(f"Error reading hooks file: {exc}", file=sys.stderr)
        sys.exit(1)

    new_hooks = hooks_data.get("hooks", {})
    if not new_hooks:
        print(f"Warning: no 'hooks' key found in {hooks_file}", file=sys.stderr)
        return

    # Tag entries with source
    tagged = tag_entries(new_hooks, source)

    # Load existing settings
    settings_dir = Path(target_dir) / ".claude"
    settings_path = settings_dir / "settings.json"

    settings: dict = {}
    if settings_path.is_file():
        try:
            settings = load_json(str(settings_path))
        except json.JSONDecodeError as exc:
            print(
                f"Error: malformed JSON in {settings_path}: {exc}",
                file=sys.stderr,
            )
            sys.exit(2)
    else:
        settings_dir.mkdir(parents=True, exist_ok=True)

    existing_hooks = settings.get("hooks", {})
    settings["hooks"] = merge_hooks(tagged, existing_hooks, source)
    save_json(str(settings_path), settings)
    print(f"Injected hooks from '{source}' into {settings_path}")


def remove(source_name: str, target_dir: str) -> None:
    """Remove all hook entries tagged with *source_name*.

    Args:
        source_name: The ``_source`` tag to remove.
        target_dir: Directory containing ``.claude/settings.json``.
    """
    if source_name == PROTECTED_SOURCE:
        print(
            f"Error: cannot remove '{PROTECTED_SOURCE}' entries. "
            "Use 'ai-toolkit uninstall' instead.",
            file=sys.stderr,
        )
        sys.exit(1)

    settings_path = Path(target_dir) / ".claude" / "settings.json"

    if not settings_path.is_file():
        print(f"No settings.json found at {settings_path}")
        return

    try:
        settings = load_json(str(settings_path))
    except json.JSONDecodeError as exc:
        print(
            f"Error: malformed JSON in {settings_path}: {exc}",
            file=sys.stderr,
        )
        sys.exit(2)

    existing_hooks = settings.get("hooks", {})
    cleaned = strip_source(existing_hooks, source_name)

    if cleaned:
        settings["hooks"] = cleaned
    else:
        settings.pop("hooks", None)

    save_json(str(settings_path), settings)
    print(f"Removed hooks with source '{source_name}' from {settings_path}")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str]) -> dict:
    """Parse CLI arguments.

    Returns:
        Dict with keys: remove_mode, remove_name, source_file, target_dir.
    """
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
                print("--remove requires a hook source name", file=sys.stderr)
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
    """Inject or remove external hooks in settings.json."""
    args = _parse_args(sys.argv[1:])

    # -- remove mode ---------------------------------------------------------
    if args["remove_mode"]:
        remove(args["remove_name"], args["target_dir"])
        return

    # -- inject mode ---------------------------------------------------------
    source_file = args["source_file"]
    if not source_file:
        print(
            "Usage: inject_hook_cli.py <hooks-file.json> [target-dir]",
            file=sys.stderr,
        )
        print(
            "       inject_hook_cli.py --remove <hook-source-name> [target-dir]",
            file=sys.stderr,
        )
        sys.exit(1)

    source_path = Path(source_file)
    if not source_path.is_file():
        print(f"Hooks file not found: {source_path}", file=sys.stderr)
        sys.exit(1)

    inject(source_file, args["target_dir"])


if __name__ == "__main__":
    main()
