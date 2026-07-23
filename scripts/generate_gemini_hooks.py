#!/usr/bin/env python3
"""Generate .gemini/settings.json hooks block for Gemini CLI.

Merges ai-toolkit hook entries into `<target>/.gemini/settings.json`. User
settings (everything outside the `hooks` key or any hook entry not tagged
`_source: ai-toolkit`) are preserved byte-for-byte.

Gemini CLI hook events (per docs/hooks/reference.md, google-gemini/gemini-cli):
    BeforeTool, AfterTool, BeforeAgent, AfterAgent, BeforeModel,
    BeforeToolSelection, AfterModel, SessionStart, SessionEnd,
    Notification, PreCompress

The ai-toolkit registry nominally includes `Stop`, but the upstream Gemini CLI
does not implement it; `AfterAgent` is the closest equivalent (fires once per
turn after the model's final response) and we wire our `save-session.sh` /
`quality-check.sh` there.

Hook scripts are shared with Claude Code / Codex and live under
`~/.softspark/ai-toolkit/hooks/`. This generator does NOT duplicate shell code.

Usage:
    python3 scripts/generate_gemini_hooks.py [target-dir]

Writes `<target-dir>/.gemini/settings.json` (merge-safe, idempotent).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

HOOKS_PREFIX = 'AI_TOOLKIT_HOOK_FORMAT=json "$HOME/.softspark/ai-toolkit/hooks/'
SOURCE_TAG = "ai-toolkit"

# Event -> list of (matcher, script) pairs. Matcher semantics:
#   - Tool events (BeforeTool/AfterTool): regex over tool_name
#     (built-in tools: run_shell_command, write_file, edit, replace, read_file...)
#   - Agent/Model/Session events: matcher is ignored upstream but harmless to omit
GEMINI_HOOKS: dict[str, list[tuple[str, str]]] = {
    "SessionStart": [
        ("", "session-start.sh"),
        ("", "mcp-health.sh"),
    ],
    "BeforeTool": [
        # run_shell_command covers Bash-equivalent destructive patterns
        ("run_shell_command", "guard-destructive.sh"),
        ("run_shell_command", "commit-quality.sh"),
        ("run_shell_command", "revert-guard.sh"),
        # File-touching tools — guard paths + config
        ("write_file|edit|replace|read_file", "guard-path.sh"),
        ("write_file|edit|replace", "guard-config.sh"),
    ],
    "AfterTool": [
        ("write_file|edit|replace", "post-tool-use.sh"),
        ("write_file|edit|replace", "test-cohesion.sh"),
        ("run_shell_command|write_file|edit|replace", "governance-capture.sh"),
        ("google_web_search|web_fetch", "search-tracker.sh"),
    ],
    "BeforeAgent": [
        ("", "user-prompt-submit.sh"),
        ("", "track-usage.sh"),
    ],
    "AfterAgent": [
        # Closest equivalent to Claude's Stop event. Gemini has no native Stop.
        ("", "quality-check.sh"),
        ("", "save-session.sh"),
        ("", "stop-search-check.sh"),
    ],
    "SessionEnd": [
        ("", "session-end.sh"),
    ],
}


def build_hook_entry(matcher: str, script: str) -> dict:
    """Build a single Gemini hook entry (merge-safe shape)."""
    entry: dict = {
        "_source": SOURCE_TAG,
        "hooks": [
            {
                "type": "command",
                "command": f"{HOOKS_PREFIX}{script}\"",
            }
        ],
    }
    if matcher:
        entry["matcher"] = matcher
    return entry


def build_toolkit_hooks() -> dict[str, list[dict]]:
    """Build the toolkit's hook entries grouped by event."""
    result: dict[str, list[dict]] = {}
    for event, entries in GEMINI_HOOKS.items():
        result[event] = [build_hook_entry(m, s) for m, s in entries]
    return result


def _is_toolkit_entry(entry: dict) -> bool:
    return isinstance(entry, dict) and entry.get("_source") == SOURCE_TAG


def strip_toolkit_hooks(hooks: dict) -> dict:
    """Drop any existing ai-toolkit-tagged entries, keep everything else."""
    kept: dict = {}
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            kept[event] = entries
            continue
        survivors = [e for e in entries if not _is_toolkit_entry(e)]
        if survivors:
            kept[event] = survivors
    return kept


def merge_hooks(existing_hooks: dict, toolkit_hooks: dict) -> dict:
    """Strip old toolkit entries, then append the current batch."""
    merged = strip_toolkit_hooks(existing_hooks)
    for event, entries in toolkit_hooks.items():
        merged.setdefault(event, []).extend(entries)
    return merged


def _write_settings_atomic(settings_path: Path, settings: dict) -> None:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=settings_path.parent,
            prefix=f".{settings_path.name}.",
            encoding="utf-8",
            delete=False,
        ) as temp_file:
            json.dump(settings, temp_file, indent=4, ensure_ascii=False, sort_keys=True)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = Path(temp_file.name)
        os.replace(temp_path, settings_path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def generate(target_dir: Path) -> Path:
    """Write `<target_dir>/.gemini/settings.json` and return its path."""
    gemini_dir = target_dir / ".gemini"
    if gemini_dir.is_symlink():
        raise RuntimeError(f"Refusing symlinked Gemini directory: {gemini_dir}")
    gemini_dir.mkdir(parents=True, exist_ok=True)
    settings_path = gemini_dir / "settings.json"
    if settings_path.is_symlink():
        raise RuntimeError(f"Refusing symlinked Gemini settings: {settings_path}")

    settings: dict = {}
    if settings_path.is_file():
        with open(settings_path, encoding="utf-8") as f:
            settings = json.load(f)
        if not isinstance(settings, dict):
            raise ValueError(f"{settings_path} must contain a JSON object")

    existing_hooks = settings.get("hooks") if isinstance(settings.get("hooks"), dict) else {}
    settings["hooks"] = merge_hooks(existing_hooks or {}, build_toolkit_hooks())

    _write_settings_atomic(settings_path, settings)
    return settings_path


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    path = generate(target)
    total = sum(len(v) for v in GEMINI_HOOKS.values())
    print(f"Generated: {path.relative_to(target) if path.is_relative_to(target) else path} "
          f"({total} hooks across {len(GEMINI_HOOKS)} events)")


if __name__ == "__main__":
    main()
