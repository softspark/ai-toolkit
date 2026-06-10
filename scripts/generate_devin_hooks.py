#!/usr/bin/env python3
"""Generate ``.devin/hooks.v1.json`` for the Devin CLI (formerly Windsurf).

Devin CLI uses a hook format **compatible with Claude Code hooks**
(docs.devin.ai/cli/extensibility/hooks/overview). This generator is the
replacement for the deprecated Cascade ``.windsurf/hooks.json`` surface,
which stops working when Cascade sunsets on 2026-07-01. Devin Local / Devin
CLI do NOT read ``.windsurf/hooks.json`` as a fallback, so the hooks must be
regenerated onto this new file.

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
    # Cascade's post_setup_worktree has no Devin equivalent; session-context
    # moves to SessionStart (Devin fires SessionStart when a session begins).
    "SessionStart": [
        ("", ["session-context.sh"]),
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


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    path = generate(target)
    total = sum(len(scripts) for groups in DEVIN_HOOKS.values()
                for _, scripts in groups)
    rel = path.relative_to(target) if path.is_relative_to(target) else path
    print(f"Generated: {rel} ({total} hooks across {len(DEVIN_HOOKS)} events)")


if __name__ == "__main__":
    main()
