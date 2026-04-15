#!/usr/bin/env python3
"""Inject external hooks into ~/.claude/settings.json.

Allows external tools (MCP servers, plugins, etc.) to register their own
hooks alongside ai-toolkit's hooks.  Each injected file is tagged with a
``_source`` derived from the filename stem so that re-running is idempotent
and removal is safe.

Usage:
    inject_hook_cli.py <hooks-file-or-url> [hook-name] [target-dir]
    inject_hook_cli.py --remove <hook-source-name> [target-dir]

Arguments:
    hooks-file-or-url  Path to a JSON file or HTTPS URL with
                       ``{"hooks": {"EventName": [...]}}``
    hook-name          Override the source name (default: filename stem or
                       URL last segment)
    target-dir         Directory containing ``.claude/settings.json``
                       (default: $HOME)

Flags:
    --remove      Remove all hook entries tagged with the given source name
                  (also unregisters URL source if present)

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
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

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
# URL helpers
# ---------------------------------------------------------------------------

def _is_url(source: str) -> bool:
    """Check if source looks like an HTTP(S) URL."""
    return source.startswith("https://") or source.startswith("http://")


def _name_from_url(url: str) -> str:
    """Derive a hook source name from a URL's last path segment."""
    parsed = urllib.parse.urlparse(url)
    filename = parsed.path.rstrip("/").split("/")[-1]
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    return re.sub(r"[^a-zA-Z0-9_-]", "", stem)


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

def _fetch_and_cache(url: str, source: str) -> str:
    """Fetch hooks JSON from URL, cache locally, register source.

    Args:
        url: HTTPS URL to fetch.
        source: Source name for caching and registry.

    Returns:
        Path to the cached hooks JSON file.
    """
    from url_fetch import fetch_url
    from hook_sources import register_url_source
    from paths import EXTERNAL_HOOKS_DIR

    EXTERNAL_HOOKS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        data = fetch_url(url)
    except Exception as exc:
        print(f"Error fetching URL: {exc}", file=sys.stderr)
        sys.exit(1)

    # Validate JSON before caching
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as exc:
        print(f"Error: URL returned invalid JSON: {exc}", file=sys.stderr)
        sys.exit(2)

    if "hooks" not in parsed:
        print(f"Warning: no 'hooks' key found in URL response", file=sys.stderr)

    cached_path = EXTERNAL_HOOKS_DIR / f"{source}.json"
    cached_path.write_bytes(data)
    register_url_source(None, source, url)

    return str(cached_path)


def inject(hooks_file: str, target_dir: str, source_override: str = "") -> None:
    """Inject hooks from *hooks_file* (or URL) into the target settings.json.

    Args:
        hooks_file: Path to the external hooks JSON file, or an HTTPS URL.
        target_dir: Directory containing ``.claude/settings.json``.
        source_override: Explicit source name (overrides filename-derived name).
    """
    is_url = _is_url(hooks_file)

    if is_url:
        if hooks_file.startswith("http://"):
            print(
                "Error: only HTTPS URLs are supported. Use https:// for security.",
                file=sys.stderr,
            )
            sys.exit(1)

        source = source_override or _name_from_url(hooks_file)
        source = re.sub(r"[^a-zA-Z0-9_-]", "", source)
        if not source:
            print(
                "Error: could not derive hook name from URL. "
                "Provide one explicitly.",
                file=sys.stderr,
            )
            sys.exit(1)

        if source == PROTECTED_SOURCE:
            print(
                f"Error: source name '{PROTECTED_SOURCE}' is reserved.",
                file=sys.stderr,
            )
            sys.exit(1)

        hooks_file = _fetch_and_cache(hooks_file, source)
        print(f"Fetched hooks from URL (source: '{source}')")
    else:
        # Derive source name from filename stem
        source = source_override or Path(hooks_file).stem
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

    Also unregisters the URL source if it was URL-sourced.

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

    # Unregister URL source if present
    try:
        from hook_sources import unregister_source
        from paths import EXTERNAL_HOOKS_DIR

        if unregister_source(None, source_name):
            print(f"Unregistered URL source '{source_name}'")

        # Remove cached file if exists
        cached = EXTERNAL_HOOKS_DIR / f"{source_name}.json"
        if cached.is_file():
            cached.unlink()
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str]) -> dict:
    """Parse CLI arguments.

    Returns:
        Dict with keys: remove_mode, remove_name, source_file, hook_name,
        target_dir.
    """
    result: dict = {
        "remove_mode": False,
        "remove_name": "",
        "source_file": "",
        "hook_name": "",
        "target_dir": str(Path.home()),
    }

    i = 0
    positional = 0
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
        else:
            if positional == 0:
                if not result["remove_mode"]:
                    result["source_file"] = arg
                else:
                    result["target_dir"] = arg
            elif positional == 1:
                if _is_url(result["source_file"]):
                    # Second positional after URL could be hook-name or target-dir
                    # If it looks like a path (starts with / or ~ or .), it's target-dir
                    if arg.startswith(("/", "~", ".")):
                        result["target_dir"] = arg
                    else:
                        result["hook_name"] = arg
                else:
                    result["target_dir"] = arg
            elif positional == 2:
                result["target_dir"] = arg
            positional += 1
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
            "Usage: inject_hook_cli.py <hooks-file-or-url> [hook-name] [target-dir]",
            file=sys.stderr,
        )
        print(
            "       inject_hook_cli.py --remove <hook-source-name> [target-dir]",
            file=sys.stderr,
        )
        sys.exit(1)

    if not _is_url(source_file):
        source_path = Path(source_file)
        if not source_path.is_file():
            print(f"Hooks file not found: {source_path}", file=sys.stderr)
            sys.exit(1)

    inject(source_file, args["target_dir"], source_override=args["hook_name"])


if __name__ == "__main__":
    main()
