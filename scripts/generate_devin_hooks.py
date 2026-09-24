#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate ``.devin/hooks.v1.json`` for the Devin CLI (formerly Windsurf).

Devin CLI uses a hook format **compatible with Claude Code hooks**
(docs.devin.ai/cli/extensibility/hooks/overview). This generator is the
replacement for the removed Cascade ``.windsurf/hooks.json`` surface, which
stopped working on 2026-07-01. Devin Local and the standalone Devin CLI do not
read that legacy file as a fallback, so hooks are emitted here.

Output file: ``<target>/.devin/hooks.v1.json``. Per the Devin docs the
standalone ``hooks.v1.json`` file's entire contents ARE the hooks object —
there is **no** top-level ``"hooks"`` wrapper key (unlike
``.claude/settings.json`` or ``.devin/config.json``).

Events use Claude-style PascalCase names. Matchers are regexes against the
Devin **tool name** (``read``, ``edit``, ``exec``, ``grep``, ``glob``,
``mcp__<server>__<tool>``) — NOT Claude's ``Bash``/``Edit`` names — so the
shared guard scripts reliably fire under Devin.

Blocking contract: the shared guard scripts emit ``{"decision":"block",
"reason":...}`` on stdout (plain mode) AND exit 2 — Devin honors both (docs:
exit 2 = deny; JSON ``{"decision":"block"}`` = deny). Hooks therefore run
WITHOUT ``AI_TOOLKIT_HOOK_FORMAT=json`` because Devin expects the flat
``{"decision","reason"}`` shape, not Claude's ``hookSpecificOutput`` envelope.

Existing user hook entries are preserved; only entries tagged
``_source: ai-toolkit`` are replaced on regeneration.

Usage:
    python3 scripts/generate_devin_hooks.py [target-dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from secure_fs import apply_owned_edits, lexical_absolute

HOOKS_PREFIX = '"$HOME/.softspark/ai-toolkit/hooks/'
SOURCE_TAG = "ai-toolkit"

# event -> list of (matcher_regex, [script names]).
# Matchers target Devin tool names: read, edit, exec, mcp__<server>__<tool>.
# An empty matcher fires for every tool name (Devin: omitted/empty = match all).
DEVIN_HOOKS: dict[str, list[tuple[str, list[str]]]] = {
    "PreToolUse": [
        ("^(read|edit)$", ["guard-path.sh"]),
        ("^edit$", ["guard-config.sh"]),
        ("^exec$", ["guard-destructive.sh", "commit-quality.sh", "revert-guard.sh"]),
        ("^mcp__", ["guard-config.sh"]),
    ],
    "PostToolUse": [
        ("^edit$", ["post-tool-use.sh", "governance-capture.sh", "test-cohesion.sh"]),
        ("^exec$", ["governance-capture.sh"]),
        ("^mcp__.*__(smart_query|hybrid_search_kb|crag_search|multi_hop_search|verify_answer)$",
         ["search-tracker.sh"]),
    ],
    "UserPromptSubmit": [
        ("", ["user-prompt-submit.sh", "track-usage.sh"]),
    ],
    "Stop": [
        ("", ["quality-check.sh", "save-session.sh", "stop-search-check.sh"]),
    ],
}


def build_hook_entry(matcher: str, scripts: list[str]) -> dict:
    """Build one Devin matcher-group: ``{matcher, hooks:[{type,command}]}``."""
    return {
        "_source": SOURCE_TAG,
        "matcher": matcher,
        "hooks": [
            {"type": "command", "command": f'{HOOKS_PREFIX}{s}"'}
            for s in scripts
        ],
    }


def build_toolkit_hooks() -> dict[str, list[dict]]:
    return {
        event: [build_hook_entry(matcher, scripts) for matcher, scripts in groups]
        for event, groups in DEVIN_HOOKS.items()
    }


def _is_toolkit_entry(entry: dict) -> bool:
    return isinstance(entry, dict) and entry.get("_source") == SOURCE_TAG


def strip_toolkit_hooks(hooks: dict) -> dict:
    """Drop ai-toolkit matcher-groups; keep user-authored entries."""
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
    devin_dir = target_dir / ".devin"
    devin_dir.mkdir(parents=True, exist_ok=True)
    path = devin_dir / "hooks.v1.json"

    # The standalone hooks.v1.json file IS the hooks object (no wrapper key).
    existing: dict = {}
    if path.is_file():
        try:
            with open(path, encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, dict):
                existing = {}
        except (json.JSONDecodeError, OSError):
            existing = {}

    merged = merge_hooks(existing, build_toolkit_hooks())

    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=4, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    return path


HOOKS_FILE = ".devin/hooks.v1.json"
# Cascade hooks retired on 2026-07-01; older installs wrote them here.
RETIRED_HOOKS_FILE = ".windsurf/hooks.json"
# Every toolkit handler runs a script from this directory, which uninstall
# deletes. A handler whose ``_source`` tag an editor dropped still names it.
TOOLKIT_HOOKS_PATH = ".softspark/ai-toolkit/hooks/"


def _is_toolkit_handler(handler: object) -> bool:
    return isinstance(handler, dict) and (
        handler.get("_source") == SOURCE_TAG
        or TOOLKIT_HOOKS_PATH in str(handler.get("command", ""))
    )


def _strip_for_uninstall(hooks: dict) -> dict:
    """Drop toolkit matcher-groups and toolkit handlers inside user groups."""
    kept: dict = {}
    for event, entries in strip_toolkit_hooks(hooks).items():
        if not isinstance(entries, list):
            kept[event] = entries
            continue
        survivors = []
        for entry in entries:
            handlers = entry.get("hooks") if isinstance(entry, dict) else None
            if not isinstance(handlers, list):
                survivors.append(entry)
                continue
            remaining = [h for h in handlers if not _is_toolkit_handler(h)]
            if remaining:
                survivors.append({**entry, "hooks": remaining})
        if survivors:
            kept[event] = survivors
    return kept


def _load_json(content: bytes, label: str) -> object:
    try:
        return json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Refusing to rewrite invalid {label}: {error}") from error


def _dump(document: dict) -> bytes:
    return (
        json.dumps(document, indent=4, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")


def _strip_hooks_file(content: bytes) -> bytes | None:
    """Owned edit for hooks.v1.json, whose whole document is the hooks object."""
    document = _load_json(content, HOOKS_FILE)
    if not isinstance(document, dict):
        return content
    survivors = _strip_for_uninstall(document)
    if survivors == document:
        return content
    return _dump(survivors) if survivors else None


def _strip_retired_hooks_file(content: bytes) -> bytes | None:
    """Owned edit for the retired Cascade file, which wraps hooks in a key."""
    document = _load_json(content, RETIRED_HOOKS_FILE)
    if not isinstance(document, dict) or not isinstance(document.get("hooks"), dict):
        return content
    survivors = _strip_for_uninstall(document["hooks"])
    if survivors == document["hooks"]:
        return content
    remaining = {key: value for key, value in document.items() if key != "hooks"}
    if survivors:
        remaining["hooks"] = survivors
    return _dump(remaining) if remaining else None


def _apply(target_dir: Path, *, dry_run: bool) -> int:
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Devin target directory: {target}")
    return apply_owned_edits(
        {
            target / HOOKS_FILE: _strip_hooks_file,
            target / RETIRED_HOOKS_FILE: _strip_retired_hooks_file,
        },
        target,
        label="Devin hooks",
        prune=(target / ".devin", target / ".windsurf"),
        dry_run=dry_run,
    )


def discover(target_dir: Path) -> int:
    """Count Devin/Cascade hook files that hold ai-toolkit hook entries."""
    return _apply(target_dir, dry_run=True)


def cleanup(target_dir: Path) -> int:
    """Strip ai-toolkit hooks from ``.devin/hooks.v1.json`` and ``.windsurf/hooks.json``.

    User matcher-groups and handlers are kept; a file left empty is deleted.
    Invalid JSON raises ``ValueError`` instead of being overwritten. Returns
    the number of files rewritten or removed.
    """
    return _apply(target_dir, dry_run=False)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    path = generate(target)
    total = sum(len(scripts) for groups in DEVIN_HOOKS.values()
                for _, scripts in groups)
    rel = path.relative_to(target) if path.is_relative_to(target) else path
    print(f"Generated: {rel} ({total} hooks across {len(DEVIN_HOOKS)} events)")


if __name__ == "__main__":
    main()
