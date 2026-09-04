#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""ai-toolkit plugin — install, remove, update, clean, and list plugin packs.

Usage:
    plugin.py list [--editor claude|codex|cursor|gemini|all]
    plugin.py status [--editor claude|codex|cursor|gemini|all]
    plugin.py install [--editor claude|codex|cursor|gemini|all] <pack-name> [<pack-name> ...]
    plugin.py install [--editor claude|codex|cursor|gemini|all] --all
    plugin.py remove [--editor claude|codex|cursor|gemini|all] <pack-name> [<pack-name> ...]
    plugin.py remove [--editor claude|codex|cursor|gemini|all] --all
    plugin.py update [--editor claude|codex|cursor|gemini|all] <pack-name> [<pack-name> ...]
    plugin.py update [--editor claude|codex|cursor|gemini|all] --all
    plugin.py clean <pack-name> [--days N]

Actions:
    install   Install a plugin pack for one or more runtimes
    remove    Remove plugin hooks/rules/scripts for one or more runtimes
    update    Re-install plugin pack (remove + install)
    clean     Prune old data (e.g. memory-pack observations older than --days N)
    list      Show available plugin packs with install status by runtime
    status    Show installed packs with runtime-specific details
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import secrets
import signal
import shutil
import sqlite3 as sqlite
import stat
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None
    import msvcrt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import app_dir, inject_section, remove_rule_section
from injection import strip_section, trim_trailing_blanks
from codex_skill_adapter import (
    cleanup_codex_skills,
    prepare_codex_skills_dir,
    sync_codex_skill,
    unmanaged_codex_skill_names,
)
from generate_codex_hooks import (
    SUPPORTED_EVENTS as SUPPORTED_CODEX_HOOK_EVENTS,
    TOOLKIT_COMMAND_MARKER,
    generate as generate_codex_hooks,
    load_hooks_json,
    validate_hooks_document,
    write_hooks_json,
)
from install_steps.ai_tools import inject_with_rules
from paths import HOOKS_DIR as _HOOKS_DIR
from paths import RULES_DIR, TOOLKIT_DATA_DIR
from mcp_editors import ConfigUpdate, apply_config_updates
from plugin_mcp import (
    PluginMcpInstallPlan,
    PluginMcpRemovalPlan,
    apply_plugin_mcp_install,
    apply_plugin_mcp_removal,
    prepare_plugin_mcp_install,
    prepare_plugin_mcp_removal,
)
from plugin_rules import (
    PluginRulePlan,
    prepare_plugin_rule_install,
    prepare_plugin_rule_removal,
)
from plugin_schema import resolve_hook_event


PLUGINS_DIR = app_dir / "plugins"
# External packs live outside the npm package so a toolkit upgrade cannot delete
# them: `npm install -g @softspark/ai-toolkit` replaces app/ wholesale, taking any
# third-party pack dropped in there with it. TOOLKIT_DATA_DIR is user-owned and
# survives. The entry may be a directory or a symlink (e.g. to an npm-installed
# pack), which is how an external pack gets a versioned update path.
USER_PLUGINS_DIR = TOOLKIT_DATA_DIR / "plugins"
CLAUDE_DIR = Path.home() / ".claude"
CODEX_ROOT = Path.home()
CODEX_HOME = Path(os.environ.get("CODEX_HOME", CODEX_ROOT / ".codex")).expanduser()
CODEX_HOOKS_DIR = CODEX_HOME / "ai-toolkit-hooks"
HOOKS_DIR = _HOOKS_DIR
PLUGINS_STATE_FILE = TOOLKIT_DATA_DIR / "plugins.json"
MEMORY_DB = TOOLKIT_DATA_DIR / "memory.db"
PLUGIN_LIFECYCLE_LOCK = TOOLKIT_DATA_DIR / "plugin-lifecycle.lock"
PLUGIN_INIT_LOCK = TOOLKIT_DATA_DIR / "plugin-init.lock"
PLUGIN_INIT_TIMEOUT_SECONDS = 30
PLUGIN_INIT_TERMINATE_GRACE_SECONDS = 1.0
PLUGIN_INIT_KILL_GRACE_SECONDS = 1.0
_PLUGIN_THREAD_LOCK = threading.RLock()
_PLUGIN_LOCK_DEPTH = 0

VALID_EDITORS = ("claude", "codex", "cursor", "gemini")
PLUGIN_EDITOR_LABELS = {
    "claude": "Claude",
    "codex": "Codex",
    "cursor": "Cursor",
    "gemini": "Gemini",
}

# Runtimes whose hook config is a JSON document we merge a single pack entry
# into, rather than a surface with its own installer. Everything below is read
# from the matching scripts/generate_<runtime>_hooks.py.
#
# `source_tag` deliberately differs from those generators' own `SOURCE_TAG`
# ("ai-toolkit"): their strip predicates match that value exactly, so a pack
# entry tagged `ai-toolkit-plugin-<pack>` survives a core regeneration instead
# of being deleted as legacy output.
#
# Pack hooks are user-scope only. Cursor's project manifest is deliberately
# self-contained so cloud agents can read it (tests/test_cursor.bats), and a
# `$HOME/.softspark` command would break that; `~/.cursor/hooks.json` is a local
# file where a home-relative command is correct.
JSON_HOOK_RUNTIMES: dict[str, dict] = {
    "cursor": {
        "config": Path.home() / ".cursor" / "hooks.json",
        # Claude event name -> this runtime's event name. An event with no
        # mapping is skipped loudly rather than guessed at.
        "events": {"PreToolUse": "beforeShellExecution"},
        "shape": "flat",  # entry is the command record itself
        "timeout": 10,
    },
    "gemini": {
        "config": Path.home() / ".gemini" / "settings.json",
        "events": {"PreToolUse": "BeforeTool", "PostToolUse": "AfterTool"},
        "shape": "nested",  # entry wraps a hooks[] list, optional matcher
        "matcher": "run_shell_command",
        "root_key": "hooks",  # hooks live under a key inside a larger document
    },
}
CODEX_PLUGIN_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
CODEX_PLUGIN_ASSET_MARKER = "# ai-toolkit-managed: codex-plugin-hook"


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


def _empty_state() -> dict:
    # Built from VALID_EDITORS so adding a runtime cannot leave load_state()
    # indexing a key that was never created.
    return {
        "shared_asset_ownership": {},
        "targets": {
            editor: {
                "installed": [],
                "versions": {},
                "mcp_ownership": {},
                "rule_ownership": {},
            }
            for editor in VALID_EDITORS
        },
    }


def _normalize_shared_asset_consumers(state: dict) -> None:
    """Migrate legacy shared ownership to explicit per-editor consumers."""
    ownerships = state.get("shared_asset_ownership", {})
    if not isinstance(ownerships, dict):
        return
    for name, ownership in ownerships.items():
        if not isinstance(ownership, dict):
            continue
        entries = ownership.get("entries", {})
        if not isinstance(entries, dict):
            entries = {}
        raw_consumers = ownership.get("consumers")
        consumers: dict[str, list[str]] = {}
        if isinstance(raw_consumers, dict):
            for editor, keys in raw_consumers.items():
                if editor in VALID_EDITORS and isinstance(keys, list):
                    consumers[editor] = sorted(
                        key
                        for key in set(keys)
                        if isinstance(key, str) and key in entries
                    )
        if not consumers and entries:
            for editor in VALID_EDITORS:
                installed = (
                    state.get("targets", {}).get(editor, {}).get("installed", [])
                )
                if name in installed:
                    consumers[editor] = sorted(entries)
        ownership["consumers"] = consumers


def load_state() -> dict:
    """Load installed plugins state with backwards compatibility."""
    state = _empty_state()
    if PLUGINS_STATE_FILE.exists() or PLUGINS_STATE_FILE.is_symlink():
        try:
            version = _read_file_version(PLUGINS_STATE_FILE)
            raw = (
                json.loads(version.content.decode("utf-8"))
                if version is not None
                else {}
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            raw = {}

        if isinstance(raw, dict):
            shared_asset_ownership = raw.get("shared_asset_ownership", {})
            if isinstance(shared_asset_ownership, dict):
                state["shared_asset_ownership"] = {
                    name: ownership
                    for name, ownership in shared_asset_ownership.items()
                    if isinstance(name, str) and isinstance(ownership, dict)
                }
            if isinstance(raw.get("installed"), list):
                # Legacy format: Claude-only installs.
                state["targets"]["claude"]["installed"] = sorted(set(raw["installed"]))

            targets = raw.get("targets", {})
            if isinstance(targets, dict):
                for editor in VALID_EDITORS:
                    installed = targets.get(editor, {}).get("installed", [])
                    if isinstance(installed, list):
                        state["targets"][editor]["installed"] = sorted(set(installed))
                    # Absent in state written before versions were tracked, so
                    # every pack looks stale once and is updated exactly once.
                    versions = targets.get(editor, {}).get("versions", {})
                    if isinstance(versions, dict):
                        state["targets"][editor]["versions"] = {
                            k: v for k, v in versions.items() if isinstance(v, str)
                        }
                    mcp_ownership = targets.get(editor, {}).get("mcp_ownership", {})
                    if isinstance(mcp_ownership, dict):
                        state["targets"][editor]["mcp_ownership"] = {
                            name: ownership
                            for name, ownership in mcp_ownership.items()
                            if isinstance(name, str) and isinstance(ownership, dict)
                        }
                    rule_ownership = targets.get(editor, {}).get("rule_ownership", {})
                    if isinstance(rule_ownership, dict):
                        state["targets"][editor]["rule_ownership"] = {
                            name: ownership
                            for name, ownership in rule_ownership.items()
                            if isinstance(name, str) and isinstance(ownership, dict)
                        }
    _normalize_shared_asset_consumers(state)
    return state


def save_state(state: dict) -> FileVersion:
    """Save installed plugins state."""
    _validate_ancestor_chain(PLUGINS_STATE_FILE)
    _secure_create_parent(PLUGINS_STATE_FILE)
    pins = _pin_ancestors(PLUGINS_STATE_FILE)
    current = _read_file_version(PLUGINS_STATE_FILE)
    mode = current.mode if current is not None else 0o600
    return _secure_atomic_write(
        PLUGINS_STATE_FILE,
        _state_content(state),
        mode,
        pins,
        current,
    )


def _installed_for(state: dict, editor: str) -> list[str]:
    return list(state.get("targets", {}).get(editor, {}).get("installed", []))


def _installed_version(state: dict, editor: str, name: str) -> str:
    return state.get("targets", {}).get(editor, {}).get("versions", {}).get(name, "")


def _record_version(state: dict, editor: str, name: str, version: str) -> None:
    state.setdefault("targets", {}).setdefault(editor, {}).setdefault("versions", {})[
        name
    ] = version


def _forget_version(state: dict, editor: str, name: str) -> None:
    state.get("targets", {}).get(editor, {}).get("versions", {}).pop(name, None)


def _set_installed(state: dict, editor: str, names: list[str]) -> None:
    state.setdefault("targets", {}).setdefault(editor, {})
    state["targets"][editor]["installed"] = sorted(set(names))


def _mcp_ownership_for(state: dict, editor: str, name: str) -> dict | None:
    ownership = (
        state.get("targets", {}).get(editor, {}).get("mcp_ownership", {}).get(name)
    )
    return ownership if isinstance(ownership, dict) else None


def _record_mcp_ownership(state: dict, editor: str, name: str, ownership: dict) -> None:
    target = state.setdefault("targets", {}).setdefault(editor, {})
    target.setdefault("mcp_ownership", {})[name] = ownership


def _forget_mcp_ownership(state: dict, editor: str, name: str) -> None:
    target = state.get("targets", {}).get(editor, {})
    ownership = target.get("mcp_ownership", {})
    if isinstance(ownership, dict):
        ownership.pop(name, None)


def _rule_ownership_for(state: dict, editor: str, name: str) -> dict | None:
    ownership = (
        state.get("targets", {}).get(editor, {}).get("rule_ownership", {}).get(name)
    )
    return ownership if isinstance(ownership, dict) else None


def _record_rule_ownership(
    state: dict, editor: str, name: str, ownership: dict
) -> None:
    target = state.setdefault("targets", {}).setdefault(editor, {})
    target.setdefault("rule_ownership", {})[name] = ownership


def _forget_rule_ownership(state: dict, editor: str, name: str) -> None:
    target = state.get("targets", {}).get(editor, {})
    ownership = target.get("rule_ownership", {})
    if isinstance(ownership, dict):
        ownership.pop(name, None)


def _shared_asset_ownership_for(state: dict, name: str) -> dict | None:
    ownership = state.get("shared_asset_ownership", {}).get(name)
    return ownership if isinstance(ownership, dict) else None


def _record_shared_asset_ownership(state: dict, name: str, ownership: dict) -> None:
    state.setdefault("shared_asset_ownership", {})[name] = ownership


def _forget_shared_asset_ownership(state: dict, name: str) -> None:
    ownership = state.get("shared_asset_ownership", {})
    if isinstance(ownership, dict):
        ownership.pop(name, None)


def _shared_asset_consumers(ownership: object, name: str) -> dict[str, list[str]]:
    if not isinstance(ownership, dict):
        return {}
    if ownership.get("source") != f"ai-toolkit-plugin-{name}":
        return {}
    entries = _asset_entries(ownership, name)
    raw = ownership.get("consumers", {})
    if not isinstance(raw, dict):
        return {}
    consumers: dict[str, list[str]] = {}
    for editor, keys in raw.items():
        if editor not in VALID_EDITORS or not isinstance(keys, list):
            continue
        consumers[editor] = sorted(
            key for key in set(keys) if isinstance(key, str) and key in entries
        )
    return consumers


def _release_shared_asset_consumer(state: dict, name: str, editor: str) -> None:
    """Drop one editor and ownership entries no remaining editor consumes."""
    ownership = _shared_asset_ownership_for(state, name)
    if ownership is None:
        return
    consumers = _shared_asset_consumers(ownership, name)
    consumers.pop(editor, None)
    consumers = {key: value for key, value in consumers.items() if value}
    retained_keys = {key for keys in consumers.values() for key in keys}
    entries = {
        key: entry
        for key, entry in _asset_entries(ownership, name).items()
        if key in retained_keys
    }
    if not entries:
        _forget_shared_asset_ownership(state, name)
        return
    _record_shared_asset_ownership(
        state,
        name,
        {
            "source": f"ai-toolkit-plugin-{name}",
            "entries": entries,
            "consumers": consumers,
        },
    )


# ---------------------------------------------------------------------------
# Plugin discovery
# ---------------------------------------------------------------------------


def plugin_roots() -> list[Path]:
    """Directories scanned for packs, in precedence order.

    Core packs ship inside the npm package; user packs live under
    TOOLKIT_DATA_DIR and outlive every toolkit upgrade. A core pack wins a name
    collision so a stray external directory cannot shadow shipped behaviour.
    """
    return [PLUGINS_DIR, USER_PLUGINS_DIR]


def list_available() -> list[dict]:
    """List all available plugin packs, core first, then user-installed."""
    packs: list[dict] = []
    seen: set[str] = set()
    for root in plugin_roots():
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            manifest = d / "plugin.json"
            if not manifest.is_file():
                continue
            try:
                with open(manifest, encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            name = data.get("name")
            if not name or name in seen:
                continue
            seen.add(name)
            data["_dir"] = str(d)
            # "_source" is taken: hook entries use it as an ownership marker.
            data["_root"] = "core" if root == PLUGINS_DIR else "user"
            packs.append(data)
    return packs


def find_pack(name: str) -> dict | None:
    """Find a plugin pack by name."""
    for pack in list_available():
        if pack["name"] == name:
            return pack
    return None


def _resolve_skill_source(pack_dir: Path, skill: str) -> Path | None:
    core = app_dir / "skills" / skill / "SKILL.md"
    plugin = pack_dir / "skills" / skill / "SKILL.md"
    if core.is_file():
        return core.parent
    if plugin.is_file():
        return plugin.parent
    return None


def _resolve_agent_source(pack_dir: Path, agent: str) -> Path | None:
    """Locate the agent file a pack references.

    Mirrors _resolve_skill_source: a core agent in app/agents wins, otherwise the
    pack may ship its own under <pack>/agents/. Resolving only against app/agents
    is what made every pack-shipped agent print "WARN agent not found" while
    _remove_claude_pack_links already knew how to unlink one.
    """
    core = app_dir / "agents" / f"{agent}.md"
    plugin = pack_dir / "agents" / f"{agent}.md"
    if core.is_file():
        return core
    if plugin.is_file():
        return plugin
    return None


def _resolve_rule_source(pack_dir: Path, rule_name: str) -> tuple[Path, bool] | None:
    candidates = [
        (pack_dir / f"{rule_name}.md", False),
        (pack_dir / "rules" / f"{rule_name}.md", False),
        (pack_dir / rule_name, False),
        (app_dir / "rules" / f"{rule_name}.md", True),
        (app_dir / "rules" / rule_name, True),
    ]
    for path, is_core in candidates:
        if path.is_file():
            return path, is_core
    return None


def _resolve_hook_source(pack_dir: Path, hook_ref: str) -> tuple[Path, bool] | None:
    base = Path(hook_ref).name
    candidates = [
        (pack_dir / hook_ref, False),
        (pack_dir / "hooks" / base, False),
        (app_dir / "hooks" / base, True),
    ]
    for path, is_core in candidates:
        if path.is_file():
            return path, is_core
    return None


def _resolve_pack_hooks(pack: dict, pack_dir: Path) -> list[dict]:
    specs: list[dict] = []
    seen: set[str] = set()
    for hook_ref in pack.get("includes", {}).get("hooks", []):
        resolved = _resolve_hook_source(pack_dir, hook_ref)
        if not resolved:
            print(f"    WARN hook not found: {hook_ref}")
            continue
        source, is_core = resolved
        hook_name = source.name
        if hook_name in seen:
            continue
        event = resolve_hook_event(hook_name, pack)
        if not event:
            print(f"    WARN could not infer hook event for: {hook_name}")
            continue
        specs.append(
            {
                "ref": hook_ref,
                "name": hook_name,
                "event": event,
                "source": source,
                "is_core": is_core,
            }
        )
        seen.add(hook_name)
    return specs


def _resolve_pack_rules(pack: dict, pack_dir: Path) -> list[dict]:
    specs: list[dict] = []
    for rule_name in pack.get("includes", {}).get("rules", []):
        resolved = _resolve_rule_source(pack_dir, rule_name)
        if not resolved:
            print(f"    WARN rule not found: {rule_name}")
            continue
        source, is_core = resolved
        specs.append(
            {
                "name": source.stem,
                "source": source,
                "is_core": is_core,
            }
        )
    return specs


def _has_core_claude_rule(rule_name: str) -> bool:
    return (app_dir / "rules" / f"{rule_name}.md").is_file()


# ---------------------------------------------------------------------------
# Shared installers
# ---------------------------------------------------------------------------


def _ensure_core_hook_scripts() -> None:
    """Ensure canonical hook scripts exist in ~/.softspark/ai-toolkit/hooks/."""
    hooks_src = app_dir / "hooks"
    if not hooks_src.is_dir():
        return
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    for hook_file in sorted(hooks_src.glob("*.sh")):
        dst = HOOKS_DIR / hook_file.name
        shutil.copy2(hook_file, dst)
        dst.chmod(dst.stat().st_mode | 0o111)


def _copy_plugin_scripts(name: str, pack_dir: Path, installed_items: list[str]) -> None:
    """Copy plugin-specific scripts and run init if present."""
    plugin_scripts_dir = pack_dir / "scripts"
    if not plugin_scripts_dir.is_dir():
        return
    scripts_dest = TOOLKIT_DATA_DIR / "plugin-scripts" / name
    scripts_dest.mkdir(parents=True, exist_ok=True)
    for script_file in sorted(plugin_scripts_dir.iterdir()):
        if script_file.name.startswith("__"):
            continue
        # copy2 on a directory raises IsADirectoryError and aborts the install
        # halfway with nothing rolled back, so a pack that ships scripts/bin/
        # or a stray __pycache__ would break it.
        if not script_file.is_file():
            continue
        dest = scripts_dest / script_file.name
        shutil.copy2(script_file, dest)
        if script_file.suffix in (".py", ".sh"):
            dest.chmod(dest.stat().st_mode | 0o111)
        print(f"    Copied script: {script_file.name}")
        installed_items.append(f"script:{dest}")

    # `init.py` is the generic name; `init_db.py` predates it and is what
    # memory-pack ships. A pack whose init script is named anything else is
    # silently never run, and the install still reports success.
    for candidate in ("init.py", "init_db.py"):
        init_script = plugin_scripts_dir / candidate
        if not init_script.is_file():
            continue
        result = subprocess.run(
            ["python3", str(init_script)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            print(f"    Init: {result.stdout.strip()}")
        elif result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "no output"
            print(f"    WARN init failed: {detail}")
        break


def _copy_plugin_hook_scripts(
    name: str, hook_specs: list[dict], installed_items: list[str]
) -> None:
    """Copy plugin-provided hook scripts into shared toolkit storage."""
    if not hook_specs:
        return
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    for spec in hook_specs:
        if spec["is_core"]:
            continue
        dest = HOOKS_DIR / f"plugin-{name}-{spec['name']}"
        shutil.copy2(spec["source"], dest)
        dest.chmod(dest.stat().st_mode | 0o111)
        print(f"    Copied hook: {spec['name']} -> {dest.name}")
        installed_items.append(f"hook:{dest.name}")


def _plugin_hook_command(name: str, spec: dict) -> str:
    if spec["is_core"]:
        return f'"$HOME/.softspark/ai-toolkit/hooks/{spec["name"]}"'
    return f'"$HOME/.softspark/ai-toolkit/hooks/plugin-{name}-{spec["name"]}"'


def _json_runtime_entry(runtime: str, name: str, spec: dict) -> dict:
    """One hook entry in this runtime's schema, tagged as owned by the pack."""
    cfg = JSON_HOOK_RUNTIMES[runtime]
    command = _plugin_hook_command(name, spec)
    # The hook is one script for every runtime; the target is its first
    # argument, so a pack can branch on which host is calling rather than
    # always assuming Claude.
    command = f"{command} {runtime}"
    source_tag = f"ai-toolkit-plugin-{name}"

    if cfg["shape"] == "flat":
        entry = {"_source": source_tag, "command": command}
        if cfg.get("timeout"):
            entry["timeout"] = cfg["timeout"]
        return entry

    entry = {"_source": source_tag, "hooks": [{"type": "command", "command": command}]}
    if cfg.get("matcher"):
        entry["matcher"] = cfg["matcher"]
    return entry


def _json_runtime_hooks_block(runtime: str, document: dict) -> dict:
    cfg = JSON_HOOK_RUNTIMES[runtime]
    root = cfg.get("root_key")
    if root:
        block = document.get(root)
        return block if isinstance(block, dict) else {}
    block = document.get("hooks")
    return block if isinstance(block, dict) else {}


def _json_runtime_set_hooks(runtime: str, document: dict, hooks: dict) -> None:
    cfg = JSON_HOOK_RUNTIMES[runtime]
    document[cfg.get("root_key") or "hooks"] = hooks


def _merge_json_runtime_hooks_document(
    runtime: str,
    name: str,
    hook_specs: list[dict],
    document: dict,
) -> int:
    """Merge one pack's hooks into an already loaded runtime document."""
    cfg = JSON_HOOK_RUNTIMES[runtime]
    source_tag = f"ai-toolkit-plugin-{name}"
    hooks = _json_runtime_hooks_block(runtime, document)

    # Drop this pack's previous entries everywhere before appending, so a
    # re-install cannot duplicate and two hooks on one event both survive.
    hooks = {
        event: [
            e
            for e in entries
            if not (isinstance(e, dict) and e.get("_source") == source_tag)
        ]
        if isinstance(entries, list)
        else entries
        for event, entries in hooks.items()
    }

    landed = 0
    for spec in hook_specs:
        if spec["is_core"]:
            continue
        target_event = cfg["events"].get(spec["event"])
        if not target_event:
            print(
                f"    WARN {runtime} has no equivalent of {spec['event']} "
                f"for {spec['name']}, hook not registered"
            )
            continue
        hooks.setdefault(target_event, []).append(
            _json_runtime_entry(runtime, name, spec)
        )
        landed += 1

    hooks = {event: entries for event, entries in hooks.items() if entries}
    _json_runtime_set_hooks(runtime, document, hooks)
    return landed


def _strip_json_runtime_hooks_document(
    runtime: str,
    name: str,
    document: dict,
) -> int:
    """Strip one pack's hooks from an already loaded runtime document."""
    source_tag = f"ai-toolkit-plugin-{name}"
    hooks = _json_runtime_hooks_block(runtime, document)
    kept = {}
    removed = 0
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            kept[event] = entries
            continue
        survivors = [
            e
            for e in entries
            if not (isinstance(e, dict) and e.get("_source") == source_tag)
        ]
        removed += len(entries) - len(survivors)
        if survivors:
            kept[event] = survivors
    _json_runtime_set_hooks(runtime, document, kept)
    return removed


def _load_json_runtime_document(path: Path) -> tuple[bytes | None, dict]:
    version = _read_file_version(path)
    if version is None:
        return None, {}
    try:
        document = json.loads(version.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid JSON runtime config at {path}: {error}") from error
    if not isinstance(document, dict):
        raise ValueError(f"JSON runtime config must be an object: {path}")
    return version.content, document


def _prepare_json_runtime_hook_install(
    runtime: str,
    name: str,
    hook_specs: list[dict],
) -> ConfigUpdate | None:
    path: Path = JSON_HOOK_RUNTIMES[runtime]["config"]
    original, document = _load_json_runtime_document(path)
    if not _merge_json_runtime_hooks_document(runtime, name, hook_specs, document):
        return None
    content = (json.dumps(document, indent=4) + "\n").encode("utf-8")
    return ConfigUpdate(path=path, original=original, content=content)


def _prepare_json_runtime_hook_removal(
    runtime: str,
    name: str,
) -> ConfigUpdate | None:
    path: Path = JSON_HOOK_RUNTIMES[runtime]["config"]
    original, document = _load_json_runtime_document(path)
    if original is None:
        return None
    if not _strip_json_runtime_hooks_document(runtime, name, document):
        return None
    content = (json.dumps(document, indent=4) + "\n").encode("utf-8")
    return ConfigUpdate(path=path, original=original, content=content)


def _gemini_mcp_update(
    updates: tuple[ConfigUpdate, ...],
) -> ConfigUpdate:
    """Return the single Gemini settings update owned by an MCP plan."""
    if len(updates) != 1:
        raise RuntimeError("Gemini MCP plan must target exactly one settings file")
    update = updates[0]
    expected = JSON_HOOK_RUNTIMES["gemini"]["config"]
    if update.path != expected or update.content is None:
        raise RuntimeError("Gemini MCP plan does not target the shared settings file")
    return update


def _prepare_gemini_combined_install(
    name: str,
    hook_specs: list[dict],
    mcp_plan: PluginMcpInstallPlan | None,
) -> ConfigUpdate | None:
    """Combine Gemini MCP and hook changes against one settings snapshot."""
    if mcp_plan is None or not hook_specs:
        return None
    update = _gemini_mcp_update(mcp_plan.updates)
    document = json.loads(update.content.decode("utf-8"))
    if not _merge_json_runtime_hooks_document("gemini", name, hook_specs, document):
        return None
    content = (json.dumps(document, indent=4) + "\n").encode("utf-8")
    return ConfigUpdate(path=update.path, original=update.original, content=content)


def _prepare_gemini_combined_removal(
    name: str,
    mcp_plan: PluginMcpRemovalPlan | None,
) -> ConfigUpdate | None:
    """Combine Gemini MCP and hook removal against one settings snapshot."""
    if mcp_plan is None or not mcp_plan.updates:
        return None
    update = _gemini_mcp_update(mcp_plan.updates)
    document = json.loads(update.content.decode("utf-8"))
    if not _strip_json_runtime_hooks_document("gemini", name, document):
        return None
    content = (json.dumps(document, indent=4) + "\n").encode("utf-8")
    return ConfigUpdate(path=update.path, original=update.original, content=content)


def _print_mcp_install_result(plan: PluginMcpInstallPlan) -> None:
    for server_name in plan.ownership["servers"]:
        print(f"    Installed MCP server: {server_name}")
    for hint in plan.hints:
        print(f"    MCP note: {hint}")


def _print_mcp_removal_result(plan: PluginMcpRemovalPlan) -> None:
    for server_name in plan.removed:
        print(f"    Removed MCP server: {server_name}")
    for server_name in plan.preserved:
        print(f"    WARN preserved changed or user-owned MCP server: {server_name}")


@dataclass(frozen=True, slots=True)
class FileVersion:
    """Exact no-follow identity and bytes for one regular file."""

    content: bytes
    mode: int
    device: int
    inode: int


@dataclass(frozen=True, slots=True)
class AncestorPin:
    """Pinned directory identity from HOME to one destination parent."""

    path: Path
    device: int
    inode: int


@dataclass(slots=True)
class FileMutation:
    """Before/expected/produced states for CAS rollback."""

    path: Path
    ancestors: tuple[AncestorPin, ...]
    before: FileVersion | None
    expected_content: bytes | None = None
    expected_mode: int | None = None
    expected_is_set: bool = False
    produced_is_recorded: bool = False
    produced_history: list[FileVersion | None] = field(default_factory=list)
    backup_path: Path | None = None


@dataclass(frozen=True, slots=True)
class AssetSpec:
    """One explicit plugin-owned hook or script file installation."""

    key: str
    path: Path
    content: bytes
    mode: int
    kind: str


@dataclass(frozen=True, slots=True)
class AssetRemovalPlan:
    """Identity-checked shared asset removals and preserved entries."""

    removable: tuple[tuple[str, Path, FileVersion], ...]
    preserved: tuple[tuple[str, Path], ...]


_UNSPECIFIED_FILE_VERSION = object()


def _home_relative(path: Path) -> Path:
    absolute = path.expanduser().absolute()
    home = Path.home().absolute()
    try:
        return absolute.relative_to(home)
    except ValueError as error:
        raise RuntimeError(f"Plugin path escapes expected HOME: {absolute}") from error


def _lstat_directory(path: Path) -> os.stat_result:
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode):
        raise RuntimeError(f"Refusing symlinked plugin path ancestor: {path}")
    if not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"Plugin path ancestor is not a directory: {path}")
    return info


def _validate_ancestor_chain(path: Path) -> None:
    relative = _home_relative(path)
    current = Path.home().absolute()
    _lstat_directory(current)
    for part in relative.parts[:-1]:
        current /= part
        try:
            _lstat_directory(current)
        except FileNotFoundError:
            continue


def _secure_create_parent(path: Path) -> None:
    relative = _home_relative(path)
    current_path = Path.home().absolute()
    _lstat_directory(current_path)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    current = os.open(current_path, flags)
    try:
        for part in relative.parts[:-1]:
            current_path /= part
            try:
                child = os.open(part, flags, dir_fd=current)
            except FileNotFoundError:
                try:
                    os.mkdir(part, 0o700, dir_fd=current)
                except FileExistsError:
                    pass
                try:
                    child = os.open(part, flags, dir_fd=current)
                except OSError as error:
                    raise RuntimeError(
                        f"Unsafe plugin path ancestor: {current_path}"
                    ) from error
            except OSError as error:
                raise RuntimeError(
                    f"Unsafe plugin path ancestor: {current_path}"
                ) from error
            os.close(current)
            current = child
    finally:
        os.close(current)


def _pin_ancestors(path: Path) -> tuple[AncestorPin, ...]:
    relative = _home_relative(path)
    current_path = Path.home().absolute()
    pins: list[AncestorPin] = []
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    current = os.open(current_path, flags)
    try:
        info = os.fstat(current)
        pins.append(AncestorPin(current_path, info.st_dev, info.st_ino))
        for part in relative.parts[:-1]:
            current_path /= part
            child = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = child
            info = os.fstat(current)
            pins.append(AncestorPin(current_path, info.st_dev, info.st_ino))
    finally:
        os.close(current)
    return tuple(pins)


def _verify_ancestor_pins(pins: tuple[AncestorPin, ...]) -> None:
    if not pins:
        raise RuntimeError("Plugin path has no ancestor pins")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    current = os.open(pins[0].path, flags)
    try:
        for index, pin in enumerate(pins):
            if index:
                child = os.open(pin.path.name, flags, dir_fd=current)
                os.close(current)
                current = child
            info = os.fstat(current)
            if (info.st_dev, info.st_ino) != (pin.device, pin.inode):
                raise RuntimeError(f"Plugin path identity changed: {pin.path}")
    except OSError as error:
        raise RuntimeError(f"Plugin path identity changed: {pin.path}") from error
    finally:
        os.close(current)


def _read_file_version(path: Path) -> FileVersion | None:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError(f"Plugin destination is not a regular file: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return FileVersion(
            content=b"".join(chunks),
            mode=info.st_mode & 0o777,
            device=info.st_dev,
            inode=info.st_ino,
        )
    finally:
        os.close(descriptor)


def _read_file_version_at(directory: int, name: str) -> FileVersion | None:
    """Read one regular file relative to an already pinned directory."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError(f"Plugin destination is not a regular file: {name}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return FileVersion(
            content=b"".join(chunks),
            mode=info.st_mode & 0o777,
            device=info.st_dev,
            inode=info.st_ino,
        )
    finally:
        os.close(descriptor)


def _open_pinned_parent(path: Path, pins: tuple[AncestorPin, ...]) -> int:
    """Open and verify the destination parent represented by ancestor pins."""
    _verify_ancestor_pins(pins)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    directory = os.open(path.parent, flags)
    info = os.fstat(directory)
    parent_pin = pins[-1]
    if (info.st_dev, info.st_ino) != (parent_pin.device, parent_pin.inode):
        os.close(directory)
        raise RuntimeError(f"Plugin path identity changed: {parent_pin.path}")
    return directory


def _restore_quarantined_file(
    directory: int,
    quarantine_name: str,
    destination_name: str,
    moved: FileVersion,
) -> None:
    """Restore a quarantined inode without replacing a concurrent destination."""
    if _read_file_version_at(directory, quarantine_name) != moved:
        raise RuntimeError(
            f"Quarantined plugin file changed; retained as {quarantine_name}"
        )
    try:
        os.link(
            quarantine_name,
            destination_name,
            src_dir_fd=directory,
            dst_dir_fd=directory,
            follow_symlinks=False,
        )
    except FileExistsError as error:
        raise RuntimeError(
            "Concurrent plugin replacement preserved; original retained as "
            f"{quarantine_name}"
        ) from error
    restored = _read_file_version_at(directory, destination_name)
    if restored != moved:
        raise RuntimeError(
            f"Plugin quarantine restore identity mismatch: {destination_name}"
        )
    if _read_file_version_at(directory, quarantine_name) != moved:
        raise RuntimeError(
            f"Quarantined plugin file changed; retained as {quarantine_name}"
        )
    os.unlink(quarantine_name, dir_fd=directory)


def _before_restore_backup_exchange(
    mutation: FileMutation,
    expected_current: FileVersion | None,
) -> None:
    """Test seam immediately before the rollback restore CAS boundary."""


def _secure_atomic_write(
    path: Path,
    content: bytes,
    mode: int,
    pins: tuple[AncestorPin, ...],
    expected_before: FileVersion | None | object = _UNSPECIFIED_FILE_VERSION,
) -> FileVersion:
    directory = _open_pinned_parent(path, pins)
    temp_name = f".{path.name}.{secrets.token_hex(8)}.tmp"
    quarantine_name: str | None = None
    descriptor = -1
    try:
        current_before = _read_file_version_at(directory, path.name)
        expected = (
            current_before
            if expected_before is _UNSPECIFIED_FILE_VERSION
            else expected_before
        )
        if current_before != expected:
            raise RuntimeError(f"Plugin file changed before write: {path}")
        descriptor = os.open(
            temp_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            mode,
            dir_fd=directory,
        )
        os.fchmod(descriptor, mode)
        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
        temp_info = os.fstat(descriptor)
        temp_version = FileVersion(
            content=content,
            mode=temp_info.st_mode & 0o777,
            device=temp_info.st_dev,
            inode=temp_info.st_ino,
        )
        os.close(descriptor)
        descriptor = -1
        if expected is None:
            os.link(
                temp_name,
                path.name,
                src_dir_fd=directory,
                dst_dir_fd=directory,
                follow_symlinks=False,
            )
            os.unlink(temp_name, dir_fd=directory)
        else:
            quarantine_name = f".{path.name}.{secrets.token_hex(8)}.quarantine"
            os.rename(
                path.name,
                quarantine_name,
                src_dir_fd=directory,
                dst_dir_fd=directory,
            )
            moved = _read_file_version_at(directory, quarantine_name)
            if moved != expected:
                if moved is not None:
                    _restore_quarantined_file(
                        directory,
                        quarantine_name,
                        path.name,
                        moved,
                    )
                    quarantine_name = None
                raise RuntimeError(f"Plugin file changed before replace: {path}")
            try:
                os.link(
                    temp_name,
                    path.name,
                    src_dir_fd=directory,
                    dst_dir_fd=directory,
                    follow_symlinks=False,
                )
            except FileExistsError as error:
                raise RuntimeError(
                    "Concurrent plugin replacement preserved; original retained as "
                    f"{path.parent / quarantine_name}"
                ) from error
            installed = _read_file_version_at(directory, path.name)
            if installed != temp_version:
                raise RuntimeError(f"Plugin write identity mismatch: {path}")
            os.unlink(temp_name, dir_fd=directory)
            if _read_file_version_at(directory, quarantine_name) != moved:
                raise RuntimeError(
                    "Plugin quarantine changed; original retained as "
                    f"{path.parent / quarantine_name}"
                )
            os.unlink(quarantine_name, dir_fd=directory)
            quarantine_name = None
        os.fsync(directory)
        version = _read_file_version_at(directory, path.name)
        if version is None:  # pragma: no cover - link succeeded above
            raise RuntimeError(f"Plugin write disappeared: {path}")
        return version
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temp_name, dir_fd=directory)
        except FileNotFoundError:
            pass
        os.close(directory)


def _secure_unlink(
    path: Path,
    expected: FileVersion,
    pins: tuple[AncestorPin, ...],
) -> None:
    directory = _open_pinned_parent(path, pins)
    quarantine_name = f".{path.name}.{secrets.token_hex(8)}.quarantine"
    try:
        if _read_file_version_at(directory, path.name) != expected:
            raise RuntimeError(f"Plugin file changed before delete: {path}")
        os.rename(
            path.name,
            quarantine_name,
            src_dir_fd=directory,
            dst_dir_fd=directory,
        )
        moved = _read_file_version_at(directory, quarantine_name)
        if moved != expected:
            if moved is not None:
                _restore_quarantined_file(
                    directory,
                    quarantine_name,
                    path.name,
                    moved,
                )
            raise RuntimeError(f"Plugin file changed before delete: {path}")
        if _read_file_version_at(directory, quarantine_name) != expected:
            raise RuntimeError(
                "Plugin quarantine changed; file retained as "
                f"{path.parent / quarantine_name}"
            )
        os.unlink(quarantine_name, dir_fd=directory)
        os.fsync(directory)
    finally:
        os.close(directory)


@contextmanager
def _exclusive_plugin_lock(path: Path, label: str):
    """Hold one no-follow, pinned advisory lock for the current process."""
    _validate_ancestor_chain(path)
    _secure_create_parent(path)
    pins = _pin_ancestors(path)
    _verify_ancestor_pins(pins)
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    create_flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | no_follow
    open_flags = os.O_RDWR | no_follow
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_flags |= getattr(os, "O_NOFOLLOW", 0)
    directory = os.open(path.parent, directory_flags)
    try:
        directory_info = os.fstat(directory)
        parent_pin = pins[-1]
        if (directory_info.st_dev, directory_info.st_ino) != (
            parent_pin.device,
            parent_pin.inode,
        ):
            raise RuntimeError(f"Plugin {label} lock parent changed: {parent_pin.path}")
        for attempt in range(3):
            try:
                descriptor = os.open(
                    path.name,
                    create_flags,
                    0o600,
                    dir_fd=directory,
                )
                break
            except FileExistsError:
                try:
                    descriptor = os.open(
                        path.name,
                        open_flags,
                        dir_fd=directory,
                    )
                    break
                except FileNotFoundError:
                    if attempt == 2:
                        raise
        else:  # pragma: no cover - loop always breaks or raises
            raise RuntimeError(f"Unable to open plugin {label} lock: {path}")
    finally:
        os.close(directory)
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode):
        os.close(descriptor)
        raise RuntimeError(f"Plugin {label} lock is not a regular file: {path}")
    if fcntl is not None:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
    else:  # pragma: no cover - Windows only
        msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
    try:
        yield descriptor
    finally:
        if fcntl is not None:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        else:  # pragma: no cover - Windows only
            msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
        os.close(descriptor)


@contextmanager
def _plugin_lifecycle_lock():
    """Serialize plugin lifecycle commands across processes and nested calls."""
    global _PLUGIN_LOCK_DEPTH
    with _PLUGIN_THREAD_LOCK:
        if _PLUGIN_LOCK_DEPTH:
            _PLUGIN_LOCK_DEPTH += 1
            try:
                yield
            finally:
                _PLUGIN_LOCK_DEPTH -= 1
            return

        with _exclusive_plugin_lock(PLUGIN_LIFECYCLE_LOCK, "lifecycle"):
            _PLUGIN_LOCK_DEPTH = 1
            try:
                yield
            finally:
                _PLUGIN_LOCK_DEPTH = 0


@contextmanager
def _plugin_operation_gate():
    """Serialize normal lifecycle plus init while letting marked init children reenter."""
    if os.environ.get("AI_TOOLKIT_PLUGIN_INIT_ACTIVE") == "1":
        yield
        return
    with _exclusive_plugin_lock(PLUGIN_INIT_LOCK, "init"):
        yield


class PluginFileTransaction:
    """CAS rollback boundary for one plugin lifecycle operation."""

    def __init__(self, paths: tuple[Path, ...]) -> None:
        unique_paths = tuple(sorted(set(paths), key=str))
        for path in unique_paths:
            _validate_ancestor_chain(path)
        for path in unique_paths:
            _secure_create_parent(path)
        self.mutations = {
            path: FileMutation(
                path=path,
                ancestors=_pin_ancestors(path),
                before=_read_file_version(path),
            )
            for path in unique_paths
        }

    def expect_file(self, path: Path, content: bytes, mode: int | None = None) -> None:
        mutation = self.mutations[path]
        mutation.expected_content = content
        mutation.expected_mode = (
            mode
            if mode is not None
            else (mutation.before.mode if mutation.before is not None else 0o600)
        )
        mutation.expected_is_set = True

    def expect_absent(self, path: Path) -> None:
        mutation = self.mutations[path]
        mutation.expected_content = None
        mutation.expected_mode = None
        mutation.expected_is_set = True

    def backup(self, path: Path) -> None:
        mutation = self.mutations[path]
        if mutation.backup_path is not None:
            return
        if mutation.before is None:
            if _read_file_version(path) is not None:
                raise RuntimeError(
                    f"Concurrent create at plugin destination preserved: {path}"
                )
            return
        _verify_ancestor_pins(mutation.ancestors)
        current = _read_file_version(path)
        if current != mutation.before:
            raise RuntimeError(f"Plugin file changed before backup: {path}")
        directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        directory_flags |= getattr(os, "O_NOFOLLOW", 0)
        directory = os.open(path.parent, directory_flags)
        backup_name = f".{path.name}.{secrets.token_hex(8)}.rollback"
        try:
            directory_info = os.fstat(directory)
            parent_pin = mutation.ancestors[-1]
            if (directory_info.st_dev, directory_info.st_ino) != (
                parent_pin.device,
                parent_pin.inode,
            ):
                raise RuntimeError(f"Plugin path identity changed: {parent_pin.path}")
            os.link(
                path.name,
                backup_name,
                src_dir_fd=directory,
                dst_dir_fd=directory,
                follow_symlinks=False,
            )
            os.fsync(directory)
        finally:
            os.close(directory)
        backup_path = path.parent / backup_name
        backup = _read_file_version(backup_path)
        if backup != mutation.before:
            raise RuntimeError(f"Plugin rollback backup identity mismatch: {path}")
        mutation.backup_path = backup_path

    def record(self, path: Path) -> None:
        mutation = self.mutations[path]
        _verify_ancestor_pins(mutation.ancestors)
        current = _read_file_version(path)
        if mutation.expected_content is None:
            if current is not None:
                raise RuntimeError(
                    f"Expected plugin file removal did not occur: {path}"
                )
        elif (
            current is None
            or current.content != mutation.expected_content
            or current.mode != mutation.expected_mode
        ):
            raise RuntimeError(f"Plugin mutation produced unexpected state: {path}")
        mutation.produced_is_recorded = True
        mutation.produced_history.append(current)

    def record_version(self, path: Path, version: FileVersion) -> None:
        mutation = self.mutations[path]
        _verify_ancestor_pins(mutation.ancestors)
        current = _read_file_version(path)
        if current != version:
            raise RuntimeError(f"Plugin file changed immediately after write: {path}")
        if (
            mutation.expected_content != version.content
            or mutation.expected_mode != version.mode
        ):
            raise RuntimeError(f"Plugin mutation produced unexpected state: {path}")
        mutation.produced_is_recorded = True
        mutation.produced_history.append(version)

    def final_exact_states(self) -> dict[Path, FileVersion | None]:
        """Return only final states proven by this transaction."""
        states: dict[Path, FileVersion | None] = {}
        for mutation in self.mutations.values():
            _verify_ancestor_pins(mutation.ancestors)
            current = _read_file_version(mutation.path)
            if current == mutation.before or any(
                current == produced for produced in mutation.produced_history
            ):
                states[mutation.path] = current
        return states

    def accept_nested_states(
        self,
        states: dict[Path, FileVersion | None],
    ) -> None:
        """Adopt exact inode states proven by a nested lifecycle transaction."""
        for path, state in states.items():
            mutation = self.mutations.get(path)
            if mutation is None or not mutation.expected_is_set:
                continue
            if mutation.expected_content is None:
                if state is None:
                    mutation.produced_history.append(None)
                    mutation.produced_is_recorded = True
                continue
            if (
                state is not None
                and state.content == mutation.expected_content
                and state.mode == mutation.expected_mode
            ):
                mutation.produced_history.append(state)
                mutation.produced_is_recorded = True

    def rollback(self) -> None:
        conflicts: list[str] = []
        for mutation in reversed(tuple(self.mutations.values())):
            if not mutation.expected_is_set:
                continue
            try:
                _verify_ancestor_pins(mutation.ancestors)
                current = _read_file_version(mutation.path)
            except Exception as error:
                conflicts.append(f"{mutation.path}: {error}")
                continue
            if current == mutation.before:
                mutation.produced_history.append(current)
                self._discard_backup(mutation, conflicts)
                continue
            if not self._matches_produced(mutation, current):
                recovery = (
                    f"; original retained at {mutation.backup_path}"
                    if mutation.backup_path is not None
                    else ""
                )
                conflicts.append(
                    f"{mutation.path}: concurrent edit/create/mode/path swap preserved"
                    f"{recovery}"
                )
                continue
            try:
                if mutation.before is None:
                    if current is not None:
                        _secure_unlink(
                            mutation.path,
                            current,
                            mutation.ancestors,
                        )
                    mutation.produced_history.append(None)
                else:
                    if mutation.backup_path is not None:
                        self._restore_backup(mutation, current)
                        mutation.produced_history.append(mutation.before)
                    else:
                        restored = _secure_atomic_write(
                            mutation.path,
                            mutation.before.content,
                            mutation.before.mode,
                            mutation.ancestors,
                            current,
                        )
                        mutation.produced_history.append(restored)
            except Exception as error:
                conflicts.append(f"{mutation.path}: {error}")
        if conflicts:
            raise RuntimeError("Rollback conflict(s): " + "; ".join(conflicts))

    def commit(self) -> None:
        conflicts: list[str] = []
        for mutation in self.mutations.values():
            self._discard_backup(mutation, conflicts)
        if conflicts:
            raise RuntimeError(
                "Plugin backup cleanup conflict(s): " + "; ".join(conflicts)
            )

    @staticmethod
    def _restore_backup(
        mutation: FileMutation,
        expected_current: FileVersion | None,
    ) -> None:
        backup_path = mutation.backup_path
        if backup_path is None or mutation.before is None:
            raise RuntimeError(f"Missing plugin rollback backup: {mutation.path}")
        backup = _read_file_version(backup_path)
        if backup != mutation.before:
            raise RuntimeError(f"Plugin rollback backup changed: {backup_path}")
        directory = _open_pinned_parent(mutation.path, mutation.ancestors)
        quarantine_name: str | None = None
        try:
            if _read_file_version_at(directory, backup_path.name) != mutation.before:
                raise RuntimeError(f"Plugin rollback backup changed: {backup_path}")
            if _read_file_version_at(directory, mutation.path.name) != expected_current:
                raise RuntimeError(
                    f"Plugin file changed before rollback restore: {mutation.path}"
                )
            _before_restore_backup_exchange(mutation, expected_current)
            if expected_current is not None:
                quarantine_name = (
                    f".{mutation.path.name}.{secrets.token_hex(8)}.rollback-current"
                )
                os.rename(
                    mutation.path.name,
                    quarantine_name,
                    src_dir_fd=directory,
                    dst_dir_fd=directory,
                )
                moved = _read_file_version_at(directory, quarantine_name)
                if moved != expected_current:
                    if moved is not None:
                        _restore_quarantined_file(
                            directory,
                            quarantine_name,
                            mutation.path.name,
                            moved,
                        )
                        quarantine_name = None
                    raise RuntimeError(
                        "Concurrent rollback replacement preserved; original retained at "
                        f"{backup_path}"
                    )
            elif _read_file_version_at(directory, mutation.path.name) is not None:
                raise RuntimeError(
                    "Concurrent rollback create preserved; original retained at "
                    f"{backup_path}"
                )
            try:
                os.link(
                    backup_path.name,
                    mutation.path.name,
                    src_dir_fd=directory,
                    dst_dir_fd=directory,
                    follow_symlinks=False,
                )
            except FileExistsError as error:
                raise RuntimeError(
                    "Concurrent rollback replacement preserved; original retained at "
                    f"{backup_path}"
                ) from error
            if _read_file_version_at(directory, mutation.path.name) != mutation.before:
                raise RuntimeError(
                    f"Plugin rollback identity was not restored: {mutation.path}"
                )
            if _read_file_version_at(directory, backup_path.name) != mutation.before:
                raise RuntimeError(f"Plugin rollback backup changed: {backup_path}")
            os.unlink(backup_path.name, dir_fd=directory)
            if quarantine_name is not None:
                if (
                    _read_file_version_at(directory, quarantine_name)
                    != expected_current
                ):
                    raise RuntimeError(
                        "Rollback quarantine changed; retained as "
                        f"{mutation.path.parent / quarantine_name}"
                    )
                os.unlink(quarantine_name, dir_fd=directory)
                quarantine_name = None
            os.fsync(directory)
        finally:
            os.close(directory)
        restored = _read_file_version(mutation.path)
        if restored != mutation.before:
            raise RuntimeError(
                f"Plugin rollback identity was not restored: {mutation.path}"
            )
        mutation.backup_path = None

    @staticmethod
    def _discard_backup(mutation: FileMutation, conflicts: list[str]) -> None:
        backup_path = mutation.backup_path
        if backup_path is None or mutation.before is None:
            return
        try:
            backup = _read_file_version(backup_path)
            if backup != mutation.before:
                raise RuntimeError(f"Plugin rollback backup changed: {backup_path}")
            _secure_unlink(backup_path, backup, mutation.ancestors)
            mutation.backup_path = None
        except Exception as error:
            conflicts.append(f"{backup_path}: {error}")

    @staticmethod
    def _matches_produced(
        mutation: FileMutation,
        current: FileVersion | None,
    ) -> bool:
        if mutation.produced_is_recorded:
            return any(current == produced for produced in mutation.produced_history)
        return False


def _snapshot_files(paths: tuple[Path, ...]) -> PluginFileTransaction:
    """Preflight and pin one explicit plugin file transaction."""
    return PluginFileTransaction(paths)


def _restore_file_snapshots(transaction: PluginFileTransaction) -> None:
    transaction.rollback()


def _expected_replacement_mode(
    transaction: PluginFileTransaction,
    path: Path,
    *,
    default: int = 0o600,
) -> int:
    before = transaction.mutations[path].before
    return before.mode if before is not None else default


def _expect_config_updates(
    transaction: PluginFileTransaction,
    updates: tuple[ConfigUpdate, ...] | list[ConfigUpdate],
) -> None:
    for update in updates:
        if update.content is None:
            transaction.expect_absent(update.path)
        else:
            transaction.expect_file(
                update.path,
                update.content,
                _expected_replacement_mode(transaction, update.path),
            )


def _apply_config_updates_owned(
    transaction: PluginFileTransaction,
    updates: tuple[ConfigUpdate, ...] | list[ConfigUpdate],
) -> None:
    """Apply plugin config updates with pinned ancestors and exact snapshots."""
    pending = [
        update
        for update in updates
        if update.content is not None and update.content != update.original
    ]
    for update in pending:
        mutation = transaction.mutations[update.path]
        current = _read_file_version(update.path)
        current_content = current.content if current is not None else None
        if current != mutation.before or current_content != update.original:
            raise RuntimeError(
                f"Plugin config changed after preflight; refusing overwrite: {update.path}"
            )
    for update in pending:
        mutation = transaction.mutations[update.path]
        transaction.backup(update.path)
        version = _secure_atomic_write(
            update.path,
            update.content,
            mutation.expected_mode or 0o600,
            mutation.ancestors,
            mutation.before,
        )
        transaction.record_version(update.path, version)


def _expect_rule_plan(
    transaction: PluginFileTransaction,
    plan: PluginRulePlan | None,
) -> None:
    if plan is None:
        return
    for update in plan.updates:
        if update.content is None:
            transaction.expect_absent(update.path)
        else:
            transaction.expect_file(
                update.path,
                update.content,
                _expected_replacement_mode(transaction, update.path),
            )


def _apply_rule_plan_owned(
    transaction: PluginFileTransaction,
    plan: PluginRulePlan | None,
) -> None:
    """Apply native rule updates with exact CAS identity tracking."""
    if plan is None:
        return
    for update in plan.updates:
        mutation = transaction.mutations[update.path]
        current_content = (
            mutation.before.content if mutation.before is not None else None
        )
        if _read_file_version(update.path) != mutation.before:
            raise RuntimeError(f"Plugin rule changed after preflight: {update.path}")
        if current_content != update.original:
            raise RuntimeError(f"Plugin rule snapshot mismatch: {update.path}")
    for update in plan.updates:
        mutation = transaction.mutations[update.path]
        if update.content == update.original:
            transaction.record(update.path)
            continue
        transaction.backup(update.path)
        if update.content is None:
            if mutation.before is not None:
                _secure_unlink(update.path, mutation.before, mutation.ancestors)
            transaction.record(update.path)
        else:
            version = _secure_atomic_write(
                update.path,
                update.content,
                mutation.expected_mode or 0o600,
                mutation.ancestors,
                mutation.before,
            )
            transaction.record_version(update.path, version)
    for rule_name in plan.installed:
        print(f"    Installed {rule_name} rule")
    for rule_name in plan.removed:
        print(f"    Removed {rule_name} rule")
    for rule_name in plan.preserved:
        print(f"    WARN preserved changed or user-owned plugin rule: {rule_name}")


def _state_content(state: dict) -> bytes:
    return (json.dumps(state, indent=2) + "\n").encode("utf-8")


def _write_plugin_state(
    state: dict,
    transaction: PluginFileTransaction | None,
) -> None:
    """Write state through the active lifecycle transaction when one exists."""
    if transaction is None:
        save_state(state)
        return
    mutation = transaction.mutations[PLUGINS_STATE_FILE]
    content = _state_content(state)
    transaction.backup(PLUGINS_STATE_FILE)
    version = _secure_atomic_write(
        PLUGINS_STATE_FILE,
        content,
        mutation.expected_mode or 0o600,
        mutation.ancestors,
        mutation.before,
    )
    transaction.record_version(PLUGINS_STATE_FILE, version)


def _after_plugin_state_write(
    state: dict,
    editor: str,
    name: str,
    action: str,
) -> None:
    """Test seam after state identity is pinned inside the transaction."""


def _prepare_asset_specs(
    name: str,
    pack_dir: Path,
    hook_specs: list[dict],
) -> tuple[AssetSpec, ...]:
    specs: list[AssetSpec] = []
    for hook in hook_specs:
        if hook["is_core"]:
            continue
        source = Path(hook["source"])
        version = _read_file_version(source)
        if version is None:
            raise RuntimeError(f"Plugin hook source disappeared: {source}")
        specs.append(
            AssetSpec(
                key=f"hook:{hook['name']}",
                path=HOOKS_DIR / f"plugin-{name}-{hook['name']}",
                content=version.content,
                mode=version.mode | 0o111,
                kind="hook",
            )
        )
    scripts_source = pack_dir / "scripts"
    if scripts_source.is_dir():
        for source in sorted(scripts_source.iterdir()):
            if source.name.startswith("__") or not source.is_file():
                continue
            version = _read_file_version(source)
            if version is None:
                raise RuntimeError(f"Plugin script source disappeared: {source}")
            mode = (
                version.mode | 0o111
                if source.suffix in (".py", ".sh")
                else version.mode
            )
            specs.append(
                AssetSpec(
                    key=f"script:{source.name}",
                    path=TOOLKIT_DATA_DIR / "plugin-scripts" / name / source.name,
                    content=version.content,
                    mode=mode,
                    kind="script",
                )
            )
    return tuple(specs)


def _asset_entries(ownership: object, name: str) -> dict[str, dict]:
    if not isinstance(ownership, dict):
        return {}
    if ownership.get("source") != f"ai-toolkit-plugin-{name}":
        return {}
    entries = ownership.get("entries")
    if not isinstance(entries, dict):
        return {}
    return {
        key: entry
        for key, entry in entries.items()
        if isinstance(key, str) and isinstance(entry, dict)
    }


def _asset_entry_matches(path: Path, version: FileVersion, entry: object) -> bool:
    if not isinstance(entry, dict) or entry.get("path") != str(path):
        return False
    return (
        entry.get("sha256") == hashlib.sha256(version.content).hexdigest()
        and entry.get("mode") == version.mode
        and entry.get("device") == version.device
        and entry.get("inode") == version.inode
    )


def _owned_asset_paths(
    state: dict,
    name: str,
    editor: str,
    retained_keys: frozenset[str] = frozenset(),
) -> tuple[Path, ...]:
    ownership = _shared_asset_ownership_for(state, name)
    entries = _asset_entries(ownership, name)
    consumers = _shared_asset_consumers(ownership, name)
    editor_keys = set(consumers.get(editor, ()))
    other_keys = {
        key
        for consumer, keys in consumers.items()
        if consumer != editor
        for key in keys
    }
    paths: list[Path] = []
    hook_prefix = f"plugin-{name}-"
    scripts_root = TOOLKIT_DATA_DIR / "plugin-scripts" / name
    for key, entry in entries.items():
        if key not in editor_keys or key in other_keys or key in retained_keys:
            continue
        raw_path = entry.get("path")
        kind = entry.get("kind")
        if not isinstance(raw_path, str):
            continue
        path = Path(raw_path).expanduser().absolute()
        if kind == "hook":
            if path.parent != HOOKS_DIR.absolute() or not path.name.startswith(
                hook_prefix
            ):
                raise RuntimeError(f"Unsafe owned plugin hook path: {path}")
        elif kind == "script":
            if path.parent != scripts_root.absolute():
                raise RuntimeError(f"Unsafe owned plugin script path: {path}")
        else:
            raise RuntimeError(f"Unknown plugin asset kind for {path}: {kind!r}")
        paths.append(path)
    return tuple(sorted(set(paths), key=str))


def _preflight_asset_install(
    transaction: PluginFileTransaction,
    specs: tuple[AssetSpec, ...],
    previous_ownership: dict | None,
    name: str,
    *,
    allow_matching_adoption: bool = False,
) -> None:
    previous_entries = _asset_entries(previous_ownership, name)
    for spec in specs:
        before = transaction.mutations[spec.path].before
        if before is not None:
            is_owned = _asset_entry_matches(
                spec.path,
                before,
                previous_entries.get(spec.key),
            )
            is_adoptable = (
                allow_matching_adoption
                and before.content == spec.content
                and before.mode == spec.mode
            )
            if not is_owned and not is_adoptable:
                raise RuntimeError(
                    f"Refusing user-owned plugin asset collision: {spec.path}"
                )
        transaction.expect_file(spec.path, spec.content, spec.mode)


def _apply_asset_install(
    transaction: PluginFileTransaction,
    specs: tuple[AssetSpec, ...],
    name: str,
    editor: str,
    previous_ownership: dict | None,
) -> dict:
    produced_entries: dict[str, dict] = {}
    for spec in specs:
        mutation = transaction.mutations[spec.path]
        transaction.backup(spec.path)
        version = _secure_atomic_write(
            spec.path,
            spec.content,
            spec.mode,
            mutation.ancestors,
            mutation.before,
        )
        transaction.record_version(spec.path, version)
        produced_entries[spec.key] = {
            "path": str(spec.path),
            "kind": spec.kind,
            "sha256": hashlib.sha256(version.content).hexdigest(),
            "mode": version.mode,
            "device": version.device,
            "inode": version.inode,
        }
        print(f"    Installed plugin {spec.kind}: {spec.path.name}")
    return _merge_asset_ownership(previous_ownership, name, editor, produced_entries)


def _merge_asset_ownership(
    previous_ownership: dict | None,
    name: str,
    editor: str,
    produced_entries: dict[str, dict],
) -> dict:
    """Fold one editor's freshly written assets into the pack's ownership record."""
    entries = _asset_entries(previous_ownership, name)
    entries.update(produced_entries)
    consumers = _shared_asset_consumers(previous_ownership, name)
    if produced_entries:
        consumers[editor] = sorted(produced_entries)
    else:
        consumers.pop(editor, None)
    retained_keys = {key for keys in consumers.values() for key in keys}
    entries = {key: entry for key, entry in entries.items() if key in retained_keys}
    return {
        "source": f"ai-toolkit-plugin-{name}",
        "entries": entries,
        "consumers": consumers,
    }


def _ownership_from_copied_assets(
    name: str,
    editor: str,
    pack_dir: Path,
    hook_specs: list[dict],
    previous_ownership: dict | None,
) -> dict:
    """Record what the non-transactional Claude/Codex install just copied.

    ``_copy_plugin_hook_scripts`` and ``_copy_plugin_scripts`` write the same
    paths ``_prepare_asset_specs`` describes but never recorded them, so
    removal had nothing to verify against and preserved every file as
    "untracked" (v4.32.1). Reading the versions back from disk after the copy
    gives removal the same sha256/mode/inode contract the JSON runtimes get.
    """
    produced: dict[str, dict] = {}
    for spec in _prepare_asset_specs(name, pack_dir, hook_specs):
        version = _read_file_version(spec.path)
        if version is None:
            continue
        produced[spec.key] = {
            "path": str(spec.path),
            "kind": spec.kind,
            "sha256": hashlib.sha256(version.content).hexdigest(),
            "mode": version.mode,
            "device": version.device,
            "inode": version.inode,
        }
    return _merge_asset_ownership(previous_ownership, name, editor, produced)


def _preflight_asset_removal(
    transaction: PluginFileTransaction,
    ownership: dict | None,
    name: str,
    editor: str,
    retained_keys: frozenset[str] = frozenset(),
) -> AssetRemovalPlan:
    entries = _asset_entries(ownership, name)
    consumers = _shared_asset_consumers(ownership, name)
    editor_keys = set(consumers.get(editor, ()))
    other_keys = {
        key
        for consumer, keys in consumers.items()
        if consumer != editor
        for key in keys
    }
    removable: list[tuple[str, Path, FileVersion]] = []
    preserved: list[tuple[str, Path]] = []
    for key, entry in entries.items():
        if key not in editor_keys or key in other_keys or key in retained_keys:
            continue
        raw_path = entry.get("path")
        if not isinstance(raw_path, str):
            continue
        path = Path(raw_path).expanduser().absolute()
        mutation = transaction.mutations.get(path)
        if mutation is None:
            raise RuntimeError(f"Owned plugin asset was not preflighted: {path}")
        before = mutation.before
        if before is None:
            continue
        if _asset_entry_matches(path, before, entry):
            transaction.expect_absent(path)
            removable.append((key, path, before))
        else:
            preserved.append((key, path))
    return AssetRemovalPlan(tuple(removable), tuple(preserved))


def _apply_asset_removal(
    transaction: PluginFileTransaction,
    plan: AssetRemovalPlan,
) -> None:
    for _key, path, before in plan.removable:
        mutation = transaction.mutations[path]
        transaction.backup(path)
        _secure_unlink(path, before, mutation.ancestors)
        transaction.record(path)
        print(f"    Removed plugin asset: {path.name}")
    for _key, path in plan.preserved:
        print(f"    WARN preserved changed or user-owned plugin asset: {path}")


def _remove_owned_plugin_assets(state: dict | None, name: str, editor: str) -> None:
    """Delete the hook and script files this pack installed for ``editor``.

    Claude and Codex removal never consulted ``shared_asset_ownership``: the
    files were written on install, recorded, and then reported as "untracked"
    on remove because nothing looked the record up. Every pack left its hooks
    and ``plugin-scripts/<name>/`` behind (v4.32.1).

    Same rules as the transactional runtimes: an entry is deleted only when
    this editor consumes it, no other editor still does, and the file on disk
    is byte- and inode-identical to what install recorded. Anything else
    (user edits, a file install never wrote, a symlink) is preserved and named.
    """
    ownership = _shared_asset_ownership_for(state or {}, name)
    entries = _asset_entries(ownership, name)
    consumers = _shared_asset_consumers(ownership, name)
    editor_keys = set(consumers.get(editor, ()))
    other_keys = {
        key
        for consumer, keys in consumers.items()
        if consumer != editor
        for key in keys
    }
    scripts_root = TOOLKIT_DATA_DIR / "plugin-scripts" / name
    hook_prefix = f"plugin-{name}-"
    handled: set[Path] = set()

    for key, entry in entries.items():
        raw_path = entry.get("path")
        if not isinstance(raw_path, str):
            continue
        path = Path(raw_path)
        handled.add(path.absolute())
        if key not in editor_keys or key in other_keys:
            continue
        kind = entry.get("kind")
        if kind == "hook":
            safe = path.parent.absolute() == HOOKS_DIR.absolute() and path.name.startswith(hook_prefix)
        elif kind == "script":
            safe = path.parent.absolute() == scripts_root.absolute()
        else:
            safe = False
        if not safe:
            print(f"    WARN refused to remove plugin asset outside its owned root: {path}")
            continue
        if path.is_symlink():
            print(f"    WARN preserved symlinked plugin asset: {path}")
            continue
        version = _read_file_version(path)
        if version is None:
            continue
        if not _asset_entry_matches(path, version, entry):
            print(f"    WARN preserved changed plugin asset: {path}")
            continue
        path.unlink()
        print(f"    Removed plugin asset: {path.name}")

    for hook in sorted(HOOKS_DIR.glob(f"{hook_prefix}*")):
        if hook.absolute() not in handled:
            print(f"    WARN preserved untracked plugin hook: {hook}")
    if scripts_root.is_dir():
        for leftover in sorted(scripts_root.iterdir()):
            if leftover.absolute() not in handled:
                print(f"    WARN preserved untracked plugin script: {leftover}")
        if not any(scripts_root.iterdir()):
            scripts_root.rmdir()


def _state_after_removal(
    state: dict,
    editor: str,
    name: str,
) -> dict:
    result = json.loads(json.dumps(state))
    _set_installed(
        result,
        editor,
        [
            installed
            for installed in _installed_for(result, editor)
            if installed != name
        ],
    )
    _forget_version(result, editor, name)
    _forget_mcp_ownership(result, editor, name)
    _forget_rule_ownership(result, editor, name)
    _release_shared_asset_consumer(result, name, editor)
    return result


def _is_process_group_alive(process_group: int) -> bool:
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # pragma: no cover - same-user child groups are expected
        return True
    return True


def _wait_for_init_tree_exit(
    process: subprocess.Popen[str],
    process_group: int,
    timeout: float,
) -> tuple[bool, KeyboardInterrupt | None]:
    deadline = time.monotonic() + timeout
    interrupted: KeyboardInterrupt | None = None
    while True:
        try:
            process.poll()
        except KeyboardInterrupt as error:
            interrupted = interrupted or error
        try:
            is_alive = _is_process_group_alive(process_group)
        except KeyboardInterrupt as error:
            interrupted = interrupted or error
            continue
        if not is_alive:
            return True, interrupted
        if time.monotonic() >= deadline:
            return False, interrupted
        try:
            time.sleep(0.02)
        except KeyboardInterrupt as error:
            interrupted = interrupted or error


def _signal_plugin_init_group(
    process_group: int,
    signal_number: int,
) -> KeyboardInterrupt | None:
    """Deliver one group signal despite a bounded burst of user interrupts."""
    interrupted: KeyboardInterrupt | None = None
    for _attempt in range(5):
        try:
            os.killpg(process_group, signal_number)
            return interrupted
        except ProcessLookupError:
            return interrupted
        except KeyboardInterrupt as error:
            interrupted = interrupted or error
    return interrupted


def _terminate_plugin_init_tree(
    process: subprocess.Popen[str],
) -> None:
    process_group = process.pid
    interrupted = _signal_plugin_init_group(process_group, signal.SIGTERM)
    exited, wait_interrupt = _wait_for_init_tree_exit(
        process,
        process_group,
        PLUGIN_INIT_TERMINATE_GRACE_SECONDS,
    )
    interrupted = interrupted or wait_interrupt
    if not exited:
        kill_interrupt = _signal_plugin_init_group(process_group, signal.SIGKILL)
        interrupted = interrupted or kill_interrupt
        exited, wait_interrupt = _wait_for_init_tree_exit(
            process,
            process_group,
            PLUGIN_INIT_KILL_GRACE_SECONDS,
        )
        interrupted = interrupted or wait_interrupt
    try:
        process.wait(timeout=PLUGIN_INIT_KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("Plugin init supervisor could not be reaped") from error
    except KeyboardInterrupt as error:
        interrupted = interrupted or error
        while process.poll() is None:
            try:
                process.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                continue
            except KeyboardInterrupt as repeated:
                interrupted = interrupted or repeated
    if not exited or _is_process_group_alive(process_group):
        raise RuntimeError("Plugin init process group exit could not be confirmed")
    if interrupted is not None:
        raise interrupted


def _run_plugin_init_posix(
    init_script: Path,
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str] | None:
    process = subprocess.Popen(
        ["python3", str(init_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=PLUGIN_INIT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        _terminate_plugin_init_tree(process)
        print(f"    WARN init timed out after {PLUGIN_INIT_TIMEOUT_SECONDS} seconds")
        return None
    except BaseException:
        _terminate_plugin_init_tree(process)
        raise
    return subprocess.CompletedProcess(
        process.args,
        process.returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _run_plugin_init(pack_dir: Path) -> None:
    scripts_source = pack_dir / "scripts"
    for candidate in ("init.py", "init_db.py"):
        init_script = scripts_source / candidate
        if not init_script.is_file() or init_script.is_symlink():
            continue
        if os.name != "posix":
            raise RuntimeError(
                "Plugin init process-tree isolation is unsupported on this platform"
            )
        environment = dict(os.environ)
        environment["AI_TOOLKIT_PLUGIN_INIT_ACTIVE"] = "1"
        result = _run_plugin_init_posix(init_script, environment)
        if result is None:
            break
        if result.returncode == 0 and result.stdout.strip():
            print(f"    Init: {result.stdout.strip()}")
        elif result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "no output"
            print(f"    WARN init failed: {detail}")
        break


def _run_plugin_init_requests(pack_dirs: list[Path]) -> None:
    """Run successful install initializers after releasing the lifecycle lock."""
    if os.environ.get("AI_TOOLKIT_PLUGIN_INIT_ACTIVE") == "1":
        return
    for pack_dir in dict.fromkeys(pack_dirs):
        _run_plugin_init(pack_dir)


def _plugin_install_transaction_paths(
    name: str,
    pack_dir: Path,
    editor: str,
    hook_specs: list[dict],
    mcp_plan: PluginMcpInstallPlan | None,
    rule_plan: PluginRulePlan | None,
    asset_specs: tuple[AssetSpec, ...],
    retiring_asset_paths: tuple[Path, ...] = (),
) -> tuple[Path, ...]:
    """Return every file a Cursor/Gemini install may mutate."""
    paths = {
        PLUGINS_STATE_FILE,
        JSON_HOOK_RUNTIMES[editor]["config"],
    }
    if mcp_plan is not None:
        paths.update(update.path for update in mcp_plan.updates)
    if rule_plan is not None:
        paths.update(update.path for update in rule_plan.updates)
    paths.update(spec.path for spec in asset_specs)
    paths.update(retiring_asset_paths)
    return tuple(sorted(paths, key=str))


def _plugin_update_transaction_paths(
    name: str,
    pack_dir: Path,
    editor: str,
    hook_specs: list[dict],
    mcp_install_plan: PluginMcpInstallPlan | None,
    rule_install_plan: PluginRulePlan | None,
    mcp_removal_plan: PluginMcpRemovalPlan | None,
    rule_removal_plan: PluginRulePlan | None,
    asset_specs: tuple[AssetSpec, ...],
    owned_asset_paths: tuple[Path, ...],
) -> tuple[Path, ...]:
    """Return old and new files participating in one JSON-runtime update."""
    paths = set(
        _plugin_install_transaction_paths(
            name,
            pack_dir,
            editor,
            hook_specs,
            mcp_install_plan,
            rule_install_plan,
            asset_specs,
            (),
        )
    )
    if mcp_removal_plan is not None:
        paths.update(update.path for update in mcp_removal_plan.updates)
    if rule_removal_plan is not None:
        paths.update(update.path for update in rule_removal_plan.updates)
    paths.update(owned_asset_paths)
    return tuple(sorted(paths, key=str))


def _plugin_remove_transaction_paths(
    name: str,
    editor: str,
    mcp_plan: PluginMcpRemovalPlan | None,
    rule_plan: PluginRulePlan | None,
    owned_asset_paths: tuple[Path, ...],
) -> tuple[Path, ...]:
    """Return every owned file a JSON-runtime removal may mutate."""
    paths = {
        PLUGINS_STATE_FILE,
        JSON_HOOK_RUNTIMES[editor]["config"],
    }
    if mcp_plan is not None:
        paths.update(update.path for update in mcp_plan.updates)
    if rule_plan is not None:
        paths.update(update.path for update in rule_plan.updates)
    paths.update(owned_asset_paths)
    return tuple(sorted(paths, key=str))


def _rollback_plugin_transaction(
    snapshots: PluginFileTransaction | None,
    error: Exception,
) -> None:
    """Restore one failed plugin transaction or raise a combined error."""
    if snapshots is None:
        return
    try:
        _restore_file_snapshots(snapshots)
    except Exception as rollback_error:
        raise RuntimeError(
            f"Plugin transaction failed ({error}); rollback also failed: "
            f"{rollback_error}"
        ) from error


def install_pack_json_runtime(
    runtime: str,
    name: str,
    *,
    mcp_planned: bool = False,
    native_rules_planned: bool = False,
    hooks_planned: bool = False,
    installed_asset_count: int = 0,
) -> bool:
    hooks_registered = hooks_planned
    if not hooks_registered and not mcp_planned and not native_rules_planned:
        print(
            f"    WARN nothing registered for {runtime}; pack files are installed but inert"
        )
    print(f"  Done: {name} for {runtime} ({installed_asset_count} file items)")
    return True


def remove_pack_json_runtime(
    runtime: str,
    name: str,
) -> bool:
    print(f"  Done: removed {name} from {runtime}")
    return True


def _load_json(path: Path, default: dict) -> dict:
    if not path.is_file():
        return json.loads(json.dumps(default))
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return json.loads(json.dumps(default))
    if isinstance(data, dict):
        return data
    return json.loads(json.dumps(default))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        f.write("\n")


def _load_core_hook_matchers() -> dict[str, str]:
    hooks_json = app_dir / "hooks.json"
    if not hooks_json.is_file():
        return {}
    data = _load_json(hooks_json, {"hooks": {}})
    mapping: dict[str, str] = {}
    for entries in data.get("hooks", {}).values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            matcher = entry.get("matcher", "")
            for hook in entry.get("hooks", []):
                if not isinstance(hook, dict):
                    continue
                command = hook.get("command", "")
                base = Path(command.replace('"', "")).name
                if base and base not in mapping:
                    mapping[base] = matcher
    return mapping


CORE_HOOK_MATCHERS = _load_core_hook_matchers()


# ---------------------------------------------------------------------------
# Claude runtime
# ---------------------------------------------------------------------------


def _ensure_claude_settings() -> Path:
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    settings_path = CLAUDE_DIR / "settings.json"
    if not settings_path.is_file():
        _write_json(settings_path, {"hooks": {}, "env": {}})
    return settings_path


def _clear_dangling_link(path: Path, label: str) -> bool:
    """Drop a symlink whose target no longer exists, so install can relink it.

    A toolkit upgrade replaces app/ wholesale, which leaves every ~/.claude link
    into the old package pointing at nothing. The install guard treated such a
    link as installed (`exists() or is_symlink()`), reported OK and repaired
    nothing — the user was left with a dead link and a green log. Only dangling
    links are removed: a live link or a real file is user content and stays.
    """
    if path.is_symlink() and not path.exists():
        try:
            path.unlink()
        except OSError:
            return False
        print(f"    Dangling {label} link removed: {path.name}")
        return True
    return False


def _install_claude_skills(
    pack: dict, pack_dir: Path, installed_items: list[str]
) -> None:
    for skill in pack.get("includes", {}).get("skills", []):
        skill_dir = CLAUDE_DIR / "skills" / skill
        source_dir = _resolve_skill_source(pack_dir, skill)
        _clear_dangling_link(skill_dir, "skill")
        if skill_dir.exists() or skill_dir.is_symlink():
            print(f"    OK skill: {skill}")
        elif source_dir:
            skill_dir.parent.mkdir(parents=True, exist_ok=True)
            skill_dir.symlink_to(source_dir)
            print(f"    Linked skill: {skill}")
            installed_items.append(f"skill:{skill}")
        else:
            print(f"    WARN skill not found: {skill}")


def _install_claude_agents(
    pack: dict, pack_dir: Path, installed_items: list[str]
) -> None:
    for agent in pack.get("includes", {}).get("agents", []):
        agent_file = CLAUDE_DIR / "agents" / f"{agent}.md"
        source_file = _resolve_agent_source(pack_dir, agent)
        _clear_dangling_link(agent_file, "agent")
        if agent_file.exists() or agent_file.is_symlink():
            print(f"    OK agent: {agent}")
        elif source_file is not None:
            agent_file.parent.mkdir(parents=True, exist_ok=True)
            agent_file.symlink_to(source_file)
            print(f"    Linked agent: {agent}")
            installed_items.append(f"agent:{agent}")
        else:
            print(f"    WARN agent not found: {agent}")


def _merge_claude_hooks(name: str, hook_specs: list[dict]) -> None:
    settings_path = _ensure_claude_settings()
    settings = _load_json(settings_path, {"hooks": {}, "env": {}})
    hooks = settings.setdefault("hooks", {})
    source_tag = f"ai-toolkit-plugin-{name}"

    # Drop this pack's previous entries once per event, before appending any.
    # Stripping inside the loop also removed the entry appended by an earlier
    # iteration, so a pack shipping two non-core hooks on the same event kept
    # only the last one. memory-pack does not hit this because its two hooks
    # sit on different events.
    events = {spec["event"] for spec in hook_specs if not spec["is_core"]}
    for event in events:
        existing = hooks.get(event, [])
        hooks[event] = [h for h in existing if h.get("_source") != source_tag]

    for spec in hook_specs:
        if spec["is_core"]:
            # Base Claude install already owns core hooks.
            continue
        entry = {
            "_source": source_tag,
            "matcher": CORE_HOOK_MATCHERS.get(spec["name"], ""),
            "hooks": [
                {
                    "type": "command",
                    "command": _plugin_hook_command(name, spec),
                }
            ],
        }
        hooks.setdefault(spec["event"], []).append(entry)

    _write_json(settings_path, settings)
    print("    Merged hooks into ~/.claude/settings.json")


def _strip_claude_hooks(name: str) -> None:
    settings_path = CLAUDE_DIR / "settings.json"
    if not settings_path.is_file():
        return

    settings = _load_json(settings_path, {"hooks": {}})
    hooks = settings.get("hooks", {})
    source_tag = f"ai-toolkit-plugin-{name}"
    changed = False

    for event in list(hooks.keys()):
        original = hooks[event]
        filtered = [h for h in original if h.get("_source") != source_tag]
        if len(filtered) != len(original):
            hooks[event] = filtered
            changed = True
        if not hooks[event]:
            del hooks[event]

    if changed:
        _write_json(settings_path, settings)
        print("    Stripped hooks from ~/.claude/settings.json")


def _install_claude_rules(name: str, rule_specs: list[dict]) -> None:
    for spec in rule_specs:
        if spec["is_core"] and _has_core_claude_rule(spec["name"]):
            print(f"    OK rule (core install): {spec['name']}")
            continue
        section = f"plugin-{name}-{spec['name']}"
        inject_section(spec["source"], CLAUDE_DIR / "CLAUDE.md", section)
        print(f"    Injected rule: {spec['name']} -> ~/.claude/CLAUDE.md")


def _remove_claude_rules(name: str, rule_specs: list[dict]) -> None:
    for spec in rule_specs:
        if spec["is_core"] and _has_core_claude_rule(spec["name"]):
            continue
        section = f"plugin-{name}-{spec['name']}"
        remove_rule_section(section, Path.home())


def install_pack_claude(name: str, pack: dict, pack_dir: Path) -> bool:
    installed_items: list[str] = []
    hook_specs = _resolve_pack_hooks(pack, pack_dir)
    rule_specs = _resolve_pack_rules(pack, pack_dir)

    _ensure_core_hook_scripts()
    _install_claude_agents(pack, pack_dir, installed_items)
    _install_claude_skills(pack, pack_dir, installed_items)
    _copy_plugin_hook_scripts(name, hook_specs, installed_items)
    _copy_plugin_scripts(name, pack_dir, installed_items)
    _install_claude_rules(name, rule_specs)
    if any(not spec["is_core"] for spec in hook_specs):
        _merge_claude_hooks(name, hook_specs)

    print(f"  Done: {name} for claude ({len(installed_items)} file items)")
    return True


def _remove_claude_pack_links(pack: dict, pack_dir: Path) -> None:
    """Drop skill/agent symlinks this pack owns.

    Install symlinks both into ~/.claude but removal never did, so every pack
    left them behind. Ownership is decided by where the link resolves: only a
    link into the pack's own directory is removed. A link into app/skills or
    app/agents is a core asset the pack merely referenced, and the base install
    would have created it anyway, so it stays.
    """
    pack_dir = pack_dir.resolve()

    for skill in pack.get("includes", {}).get("skills", []):
        link = CLAUDE_DIR / "skills" / skill
        if not link.is_symlink():
            continue
        try:
            target = link.resolve()
        except OSError:
            continue
        if target.is_relative_to(pack_dir):
            link.unlink()
            print(f"    Removed skill link: {skill}")

    for agent in pack.get("includes", {}).get("agents", []):
        link = CLAUDE_DIR / "agents" / f"{agent}.md"
        if not link.is_symlink():
            continue
        try:
            target = link.resolve()
        except OSError:
            continue
        if target.is_relative_to(pack_dir):
            link.unlink()
            print(f"    Removed agent link: {agent}")


def remove_pack_claude(
    name: str, pack: dict, pack_dir: Path, *, keep_shared_assets: bool,
    state: dict | None = None,
) -> bool:
    hook_specs = _resolve_pack_hooks(pack, pack_dir)
    rule_specs = _resolve_pack_rules(pack, pack_dir)
    _remove_claude_pack_links(pack, pack_dir)

    if not keep_shared_assets:
        _remove_owned_plugin_assets(state, name, "claude")

    if any(not spec["is_core"] for spec in hook_specs):
        _strip_claude_hooks(name)
    _remove_claude_rules(name, rule_specs)

    print(f"  Done: removed {name} from claude")
    return True


# ---------------------------------------------------------------------------
# Codex runtime
# ---------------------------------------------------------------------------


def _install_all_codex_skills(target_root: Path) -> None:
    skills_src = app_dir / "skills"
    skills_dst = prepare_codex_skills_dir(target_root)
    user_names = unmanaged_codex_skill_names(skills_dst, skills_src)
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        if skill_dir.name in user_names:
            continue
        sync_codex_skill(skill_dir, skills_dst)
    cleanup_codex_skills(skills_dst, skills_src, user_names)


def _install_codex_extra_skills(pack: dict, pack_dir: Path) -> None:
    skills_src = app_dir / "skills"
    skills_dst = prepare_codex_skills_dir(CODEX_ROOT)
    user_names = unmanaged_codex_skill_names(skills_dst, skills_src)
    for skill in pack.get("includes", {}).get("skills", []):
        source_dir = _resolve_skill_source(pack_dir, skill)
        if not source_dir:
            print(f"    WARN skill not found: {skill}")
            continue
        if source_dir.name in user_names:
            print(f"    Preserved user Codex skill: {skill}")
            continue
        sync_codex_skill(source_dir, skills_dst)
        print(f"    Ensured Codex skill: {skill}")
    cleanup_codex_skills(skills_dst, skills_src, user_names)


def _codex_plugin_owner(name: str) -> str:
    if CODEX_PLUGIN_NAME_PATTERN.fullmatch(name) is None:
        raise ValueError(f"Unsafe Codex plugin name: {name}")
    return f"ai-toolkit-plugin-{name}"


def _codex_command_has_owner(command: str, owner: str) -> bool:
    pattern = rf"(?:^|\s)AI_TOOLKIT_HOOK_OWNER={re.escape(owner)}(?=\s|$)"
    return re.search(pattern, command) is not None


def _assert_safe_codex_surface() -> None:
    configured_home = os.environ.get("CODEX_HOME")
    if not CODEX_HOME.is_absolute():
        raise RuntimeError("CODEX_HOME must be an absolute path")
    if configured_home and not CODEX_HOME.is_dir():
        raise RuntimeError("Configured CODEX_HOME must already exist")
    paths = (
        (CODEX_HOME, "home"),
        (CODEX_HOME / "AGENTS.md", "AGENTS.md"),
        (CODEX_HOME / "hooks.json", "hooks.json"),
        (CODEX_HOOKS_DIR, "hook assets"),
    )
    for path, label in paths:
        if path.is_symlink():
            raise RuntimeError(f"Refusing symlinked Codex {label}: {path}")


def _install_codex_base() -> None:
    _assert_safe_codex_surface()
    generate_codex_hooks(
        CODEX_ROOT,
        global_install=True,
        codex_home=CODEX_HOME,
    )
    # Universal coding rules are inlined into AGENTS.md by generate_codex.py;
    # Codex does not read a .agents/rules/ directory.
    inject_with_rules("generate_codex.py", CODEX_HOME / "AGENTS.md", RULES_DIR)
    _install_all_codex_skills(CODEX_ROOT)


def _codex_matcher(spec: dict) -> str:
    if spec["event"] in {"PreToolUse", "PostToolUse", "PermissionRequest"}:
        return "Bash"
    if spec["event"] == "SessionStart":
        return "startup|resume"
    if spec["event"] in {"UserPromptSubmit", "Stop"}:
        return ""
    return CORE_HOOK_MATCHERS.get(spec["name"], "")


def _codex_base_hook_present(data: dict, hook_name: str) -> bool:
    for groups in data.get("hooks", {}).values():
        for group in groups:
            for handler in group.get("hooks", []):
                command = handler.get("command", "")
                if not _codex_command_has_owner(
                    command, TOOLKIT_COMMAND_MARKER.split("=", 1)[1]
                ):
                    continue
                if re.search(rf"/{re.escape(hook_name)}(?=[\"'\s]|$)", command):
                    return True
    return False


def _select_codex_hook_specs(data: dict, hook_specs: list[dict]) -> list[dict]:
    selected: list[dict] = []
    for spec in hook_specs:
        if spec["event"] not in SUPPORTED_CODEX_HOOK_EVENTS:
            print(
                "    Skipped Codex hook (unsupported event): "
                f"{spec['name']} -> {spec['event']}"
            )
            continue
        if spec["is_core"] and _codex_base_hook_present(data, spec["name"]):
            print(f"    OK Codex hook (base install): {spec['name']}")
            continue
        selected.append(spec)
    return selected


def _remove_codex_handlers(data: dict, name: str) -> bool:
    owner = _codex_plugin_owner(name)
    changed = False
    bucket = data.get("hooks", {})
    for event in list(bucket):
        retained_groups: list[dict] = []
        for group in bucket[event]:
            handlers = group.get("hooks", [])
            retained = [
                handler
                for handler in handlers
                if not _codex_command_has_owner(handler.get("command", ""), owner)
            ]
            if len(retained) != len(handlers):
                changed = True
            if retained:
                retained_group = dict(group)
                retained_group["hooks"] = retained
                retained_groups.append(retained_group)
        if retained_groups:
            bucket[event] = retained_groups
        else:
            del bucket[event]
    return changed


def _codex_plugin_asset_name(name: str, spec: dict) -> str:
    return f"plugin-{name}-{Path(spec['name']).name}"


def _codex_plugin_asset_marker(name: str) -> str:
    return f"{CODEX_PLUGIN_ASSET_MARKER} owner={_codex_plugin_owner(name)}"


def _codex_plugin_asset_content(name: str, spec: dict) -> bytes:
    source = Path(spec["source"])
    if source.is_symlink() or not source.is_file():
        raise RuntimeError(f"Refusing unsafe Codex plugin hook source: {source}")
    text = source.read_text(encoding="utf-8")
    marker = _codex_plugin_asset_marker(name) + "\n"
    lines = text.splitlines(keepends=True)
    if lines and lines[0].startswith("#!"):
        text = "".join((lines[0], marker, *lines[1:]))
    else:
        text = marker + text
    return text.encode("utf-8")


def _is_owned_codex_plugin_asset(path: Path, name: str) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        prefix = path.read_text(encoding="utf-8")[:512]
    except (OSError, UnicodeError):
        return False
    return _codex_plugin_asset_marker(name) in prefix


def _stage_codex_plugin_asset(destination: Path, content: bytes, mode: int) -> Path:
    fd, temp_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            fd = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, mode)
        return temp_path
    except Exception:
        if fd >= 0:
            os.close(fd)
        temp_path.unlink(missing_ok=True)
        raise


def _write_codex_plugin_asset(
    destination: Path, content: bytes, mode: int = 0o755
) -> None:
    staged = _stage_codex_plugin_asset(destination, content, mode)
    try:
        if destination.is_symlink():
            raise RuntimeError(f"Refusing symlinked Codex plugin hook: {destination}")
        os.replace(staged, destination)
    finally:
        staged.unlink(missing_ok=True)


def _prepare_codex_plugin_assets(name: str, specs: list[dict]) -> dict[Path, bytes]:
    _assert_safe_codex_surface()
    CODEX_HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    _assert_safe_codex_surface()
    assets: dict[Path, bytes] = {}
    for spec in specs:
        destination = CODEX_HOOKS_DIR / _codex_plugin_asset_name(name, spec)
        if destination.is_symlink():
            raise RuntimeError(f"Refusing symlinked Codex plugin hook: {destination}")
        if destination.exists() and not _is_owned_codex_plugin_asset(destination, name):
            raise RuntimeError(
                f"Refusing user-owned Codex hook collision: {destination}"
            )
        assets[destination] = _codex_plugin_asset_content(name, spec)
    return assets


def _restore_codex_plugin_assets(
    snapshots: dict[Path, tuple[bytes, int] | None],
) -> None:
    for destination, snapshot in snapshots.items():
        if snapshot is None:
            destination.unlink(missing_ok=True)
        else:
            content, mode = snapshot
            _write_codex_plugin_asset(destination, content, mode)


def _codex_plugin_command(name: str, spec: dict) -> str:
    owner = _codex_plugin_owner(name)
    asset_name = _codex_plugin_asset_name(name, spec)
    return (
        f"AI_TOOLKIT_HOOK_OWNER={owner} "
        f'"${{CODEX_HOME:-$HOME/.codex}}/ai-toolkit-hooks/{asset_name}"'
    )


def _install_codex_hooks(
    name: str,
    hook_specs: list[dict],
    installed_items: list[str],
) -> None:
    hooks_path = CODEX_HOME / "hooks.json"
    data = load_hooks_json(hooks_path)
    specs = _select_codex_hook_specs(data, hook_specs)
    _remove_codex_handlers(data, name)
    bucket = data.setdefault("hooks", {})
    for spec in specs:
        group = {
            "hooks": [
                {
                    "type": "command",
                    "command": _codex_plugin_command(name, spec),
                }
            ]
        }
        matcher = _codex_matcher(spec)
        if matcher:
            group["matcher"] = matcher
        bucket.setdefault(spec["event"], []).append(group)
    validate_hooks_document(data)

    assets = _prepare_codex_plugin_assets(name, specs)
    snapshots = {
        path: (path.read_bytes(), path.stat().st_mode & 0o777)
        if path.exists()
        else None
        for path in assets
    }
    try:
        for path, content in assets.items():
            _write_codex_plugin_asset(path, content)
        write_hooks_json(hooks_path, data)
    except Exception:
        _restore_codex_plugin_assets(snapshots)
        raise

    for path in assets:
        installed_items.append(f"hook:{path.name}")
        print(f"    Copied Codex hook: {path.name}")
    print("    Merged hooks into $CODEX_HOME/hooks.json")


def _strip_codex_hooks(name: str) -> None:
    hooks_path = CODEX_HOME / "hooks.json"
    if not hooks_path.is_file():
        return
    data = load_hooks_json(hooks_path)
    if _remove_codex_handlers(data, name):
        write_hooks_json(hooks_path, data)
        print("    Stripped hooks from $CODEX_HOME/hooks.json")


def _install_codex_rules(name: str, rule_specs: list[dict]) -> None:
    # Codex reads instructions only from AGENTS.md, never from a .agents/rules/
    # directory, so pack rules are marker-injected into $CODEX_HOME/AGENTS.md.
    agents_md = CODEX_HOME / "AGENTS.md"
    for spec in rule_specs:
        section = f"plugin-{name}-{spec['name']}"
        inject_section(spec["source"], agents_md, section)
        print(f"    Injected Codex rule: {spec['name']} -> $CODEX_HOME/AGENTS.md")
    _clean_legacy_codex_rule_files(name)


def _remove_codex_rules(name: str) -> None:
    agents_md = CODEX_HOME / "AGENTS.md"
    if agents_md.is_file():
        content = agents_md.read_text(encoding="utf-8")
        changed = False
        for match in re.findall(
            r"<!-- TOOLKIT:(plugin-" + re.escape(name) + r"-[^ ]+) START -->", content
        ):
            content = strip_section(content, match)
            changed = True
        if changed:
            agents_md.write_text(trim_trailing_blanks(content) + "\n", encoding="utf-8")
            print(f"    Removed Codex rules for {name} from $CODEX_HOME/AGENTS.md")
    _clean_legacy_codex_rule_files(name)


def _clean_legacy_codex_rule_files(name: str) -> None:
    """Remove dead ~/.agents/rules/plugin-<name>-*.md files written by earlier
    versions. Codex never read them; Antigravity's .agents/rules/ is a separate,
    project-local surface, so this only touches our own plugin-prefixed files."""
    agents_dir = CODEX_ROOT / ".agents"
    rules_dir = agents_dir / "rules"
    if agents_dir.is_symlink() or rules_dir.is_symlink():
        raise RuntimeError(f"Refusing symlinked legacy Codex rules path: {rules_dir}")
    if not rules_dir.is_dir():
        return
    for rule_file in sorted(rules_dir.glob(f"plugin-{name}-*.md")):
        rule_file.unlink()
        print(f"    Removed legacy Codex rule file: {rule_file.name}")


def install_pack_codex(name: str, pack: dict, pack_dir: Path) -> bool:
    installed_items: list[str] = []
    hook_specs = _resolve_pack_hooks(pack, pack_dir)
    rule_specs = _resolve_pack_rules(pack, pack_dir)

    _install_codex_base()
    _install_codex_extra_skills(pack, pack_dir)
    _install_codex_hooks(name, hook_specs, installed_items)
    _copy_plugin_scripts(name, pack_dir, installed_items)
    _install_codex_rules(name, rule_specs)

    print(f"  Done: {name} for codex ({len(installed_items)} file items)")
    return True


def remove_pack_codex(
    name: str, pack: dict, pack_dir: Path, *, keep_shared_assets: bool,
    state: dict | None = None,
) -> bool:
    _assert_safe_codex_surface()
    _strip_codex_hooks(name)

    if CODEX_HOOKS_DIR.is_dir():
        for hook in CODEX_HOOKS_DIR.glob(f"plugin-{name}-*"):
            if hook.is_symlink():
                raise RuntimeError(f"Refusing symlinked Codex plugin hook: {hook}")
            if _is_owned_codex_plugin_asset(hook, name):
                hook.unlink()
                print(f"    Removed Codex hook: {hook.name}")
            else:
                print(f"    WARN preserved user-owned Codex hook: {hook.name}")

    if not keep_shared_assets:
        # Paths used by releases before native Codex plugin assets moved under
        # $CODEX_HOME. Claude still owns these when installed for both, which
        # the ownership consumers encode; only Codex-consumed entries go.
        _remove_owned_plugin_assets(state, name, "codex")

    _remove_codex_rules(name)
    print(f"  Done: removed {name} from codex")
    return True


# ---------------------------------------------------------------------------
# Common actions
# ---------------------------------------------------------------------------


def install_pack(name: str, editor: str) -> bool:
    init_requests: list[Path] = []
    with _plugin_operation_gate():
        with _plugin_lifecycle_lock():
            installed = _install_pack_locked(
                name,
                editor,
                init_requests=init_requests,
            )
        if installed:
            _run_plugin_init_requests(init_requests)
    return installed


def _install_pack_locked(
    name: str,
    editor: str,
    *,
    transaction_reports: list[PluginFileTransaction] | None = None,
    init_requests: list[Path] | None = None,
) -> bool:
    pack = find_pack(name)
    if not pack:
        print(f"  ERROR: plugin pack '{name}' not found")
        print(f"  Available: {', '.join(p['name'] for p in list_available())}")
        return False

    # A pack may declare which runtimes it actually works on. Without this a
    # pack installs everywhere and silently does nothing on the runtimes it was
    # never built for: a hook that speaks Claude Code's payload format would be
    # wired into Codex and never fire.
    supported = pack.get("supported_editors")
    if isinstance(supported, list) and supported and editor not in supported:
        print(
            f"  Skipping: {name} does not support {editor} "
            f"(supported: {', '.join(supported)})"
        )
        return False

    pack_dir = Path(pack["_dir"])
    if CODEX_PLUGIN_NAME_PATTERN.fullmatch(name) is None:
        raise ValueError(f"Unsafe plugin name: {name!r}")
    print(f"  Installing: {name} for {editor} ({pack.get('description', '')})")

    state = load_state()
    mcp_plan = prepare_plugin_mcp_install(
        name,
        editor,
        pack,
        pack_dir,
        _mcp_ownership_for(state, editor, name),
    )
    json_hook_specs = (
        _resolve_pack_hooks(pack, pack_dir) if editor in JSON_HOOK_RUNTIMES else []
    )
    json_rule_specs = (
        _resolve_pack_rules(pack, pack_dir) if editor in JSON_HOOK_RUNTIMES else []
    )
    asset_specs = (
        _prepare_asset_specs(name, pack_dir, json_hook_specs)
        if editor in JSON_HOOK_RUNTIMES
        else ()
    )
    retained_asset_keys = frozenset(spec.key for spec in asset_specs)
    retiring_asset_paths = (
        _owned_asset_paths(state, name, editor, retained_asset_keys)
        if editor in JSON_HOOK_RUNTIMES
        else ()
    )
    rule_plan = prepare_plugin_rule_install(
        name,
        editor,
        json_rule_specs,
        _rule_ownership_for(state, editor, name),
    )
    gemini_config_update = (
        _prepare_gemini_combined_install(name, json_hook_specs, mcp_plan)
        if editor == "gemini"
        else None
    )
    hook_config_update = (
        gemini_config_update
        if gemini_config_update is not None
        else (
            _prepare_json_runtime_hook_install(editor, name, json_hook_specs)
            if editor in JSON_HOOK_RUNTIMES
            else None
        )
    )
    transaction_snapshots = (
        _snapshot_files(
            _plugin_install_transaction_paths(
                name,
                pack_dir,
                editor,
                json_hook_specs,
                mcp_plan,
                rule_plan,
                asset_specs,
                retiring_asset_paths,
            )
        )
        if editor in JSON_HOOK_RUNTIMES
        else None
    )
    if transaction_snapshots is not None and transaction_reports is not None:
        transaction_reports.append(transaction_snapshots)
    asset_retirement_plan = (
        _preflight_asset_removal(
            transaction_snapshots,
            _shared_asset_ownership_for(state, name),
            name,
            editor,
            retained_asset_keys,
        )
        if transaction_snapshots is not None
        else AssetRemovalPlan((), ())
    )
    if transaction_snapshots is not None:
        _preflight_asset_install(
            transaction_snapshots,
            asset_specs,
            _shared_asset_ownership_for(state, name),
            name,
            allow_matching_adoption=any(
                name in _installed_for(state, other)
                for other in VALID_EDITORS
                if other != editor
            ),
        )
        if hook_config_update is not None:
            _expect_config_updates(transaction_snapshots, [hook_config_update])
        if gemini_config_update is None and mcp_plan is not None:
            _expect_config_updates(transaction_snapshots, mcp_plan.updates)
        _expect_rule_plan(transaction_snapshots, rule_plan)

    try:
        asset_ownership: dict | None = None
        if transaction_snapshots is not None:
            _apply_asset_removal(transaction_snapshots, asset_retirement_plan)
            asset_ownership = _apply_asset_install(
                transaction_snapshots,
                asset_specs,
                name,
                editor,
                _shared_asset_ownership_for(state, name),
            )
        if editor == "claude":
            ok = install_pack_claude(name, pack, pack_dir)
        elif editor == "codex":
            ok = install_pack_codex(name, pack, pack_dir)
        elif editor in JSON_HOOK_RUNTIMES:
            ok = install_pack_json_runtime(
                editor,
                name,
                mcp_planned=mcp_plan is not None,
                native_rules_planned=rule_plan is not None,
                hooks_planned=hook_config_update is not None,
                installed_asset_count=len(asset_specs),
            )
        else:
            print(f"  ERROR: no installer for runtime '{editor}'")
            return False
        if not ok:
            if transaction_snapshots is not None:
                _restore_file_snapshots(transaction_snapshots)
            return False
        if editor in ("claude", "codex"):
            asset_ownership = _ownership_from_copied_assets(
                name,
                editor,
                pack_dir,
                _resolve_pack_hooks(pack, pack_dir),
                _shared_asset_ownership_for(state, name),
            )

        if hook_config_update is not None:
            if transaction_snapshots is not None:
                _apply_config_updates_owned(
                    transaction_snapshots,
                    [hook_config_update],
                )
            else:  # pragma: no cover - hook plans are JSON-runtime only
                apply_config_updates([hook_config_update])
            print(f"    Merged hooks into {hook_config_update.path}")
        if gemini_config_update is not None and mcp_plan is not None:
            _print_mcp_install_result(mcp_plan)
        else:
            if transaction_snapshots is not None and mcp_plan is not None:
                _apply_config_updates_owned(
                    transaction_snapshots,
                    mcp_plan.updates,
                )
                _print_mcp_install_result(mcp_plan)
            else:
                apply_plugin_mcp_install(mcp_plan)
        if transaction_snapshots is not None:
            _apply_rule_plan_owned(transaction_snapshots, rule_plan)
        installed = _installed_for(state, editor)
        if name not in installed:
            installed.append(name)
        _set_installed(state, editor, installed)
        # Recorded so update --all can skip an unchanged plugin manifest.
        _record_version(state, editor, name, str(pack.get("version", "")))
        if mcp_plan is not None:
            _record_mcp_ownership(state, editor, name, mcp_plan.ownership)
        if rule_plan is not None and rule_plan.ownership is not None:
            _record_rule_ownership(state, editor, name, rule_plan.ownership)
        if asset_ownership is not None:
            _record_shared_asset_ownership(state, name, asset_ownership)
        if transaction_snapshots is not None:
            transaction_snapshots.expect_file(
                PLUGINS_STATE_FILE,
                _state_content(state),
                _expected_replacement_mode(
                    transaction_snapshots,
                    PLUGINS_STATE_FILE,
                ),
            )
        _write_plugin_state(state, transaction_snapshots)
        if transaction_snapshots is not None:
            _after_plugin_state_write(state, editor, name, "install")
            transaction_snapshots.commit()
            if init_requests is not None:
                init_requests.append(pack_dir)
        return True
    except Exception as error:
        _rollback_plugin_transaction(transaction_snapshots, error)
        raise


def remove_pack(name: str, editor: str) -> bool:
    with _plugin_operation_gate():
        with _plugin_lifecycle_lock():
            return _remove_pack_locked(name, editor)


def _remove_pack_locked(
    name: str,
    editor: str,
    *,
    transaction_reports: list[PluginFileTransaction] | None = None,
) -> bool:
    state = load_state()
    installed = _installed_for(state, editor)
    if name not in installed:
        print(f"  Plugin '{name}' is not installed for {editor}")
        return False

    pack = find_pack(name)
    if not pack:
        print(f"  Plugin '{name}' manifest not found")
        return False

    pack_dir = Path(pack["_dir"])
    print(f"  Removing: {name} from {editor}")
    mcp_plan = prepare_plugin_mcp_removal(
        name,
        editor,
        _mcp_ownership_for(state, editor, name),
    )
    rule_plan = prepare_plugin_rule_removal(
        name,
        editor,
        _rule_ownership_for(state, editor, name),
    )
    gemini_config_update = (
        _prepare_gemini_combined_removal(name, mcp_plan) if editor == "gemini" else None
    )
    hook_config_update = (
        gemini_config_update
        if gemini_config_update is not None
        else (
            _prepare_json_runtime_hook_removal(editor, name)
            if editor in JSON_HOOK_RUNTIMES
            else None
        )
    )
    keep_shared_assets = any(
        name in _installed_for(state, other)
        for other in VALID_EDITORS
        if other != editor
    )
    owned_asset_paths = (
        _owned_asset_paths(state, name, editor) if editor in JSON_HOOK_RUNTIMES else ()
    )
    transaction_snapshots = (
        _snapshot_files(
            _plugin_remove_transaction_paths(
                name,
                editor,
                mcp_plan,
                rule_plan,
                owned_asset_paths,
            )
        )
        if editor in JSON_HOOK_RUNTIMES
        else None
    )
    if transaction_snapshots is not None and transaction_reports is not None:
        transaction_reports.append(transaction_snapshots)
    asset_removal_plan = (
        _preflight_asset_removal(
            transaction_snapshots,
            _shared_asset_ownership_for(state, name),
            name,
            editor,
        )
        if transaction_snapshots is not None
        else AssetRemovalPlan((), ())
    )
    if transaction_snapshots is not None:
        if hook_config_update is not None:
            _expect_config_updates(transaction_snapshots, [hook_config_update])
        if gemini_config_update is None and mcp_plan is not None:
            _expect_config_updates(transaction_snapshots, mcp_plan.updates)
        _expect_rule_plan(transaction_snapshots, rule_plan)
    try:
        if hook_config_update is not None:
            if transaction_snapshots is not None:
                _apply_config_updates_owned(
                    transaction_snapshots,
                    [hook_config_update],
                )
            else:  # pragma: no cover - hook plans are JSON-runtime only
                apply_config_updates([hook_config_update])
            print(f"    Stripped hooks from {hook_config_update.path}")
        if gemini_config_update is not None and mcp_plan is not None:
            _print_mcp_removal_result(mcp_plan)
        if editor == "claude":
            ok = remove_pack_claude(
                name,
                pack,
                pack_dir,
                keep_shared_assets=keep_shared_assets,
                state=state,
            )
        elif editor == "codex":
            ok = remove_pack_codex(
                name,
                pack,
                pack_dir,
                keep_shared_assets=keep_shared_assets,
                state=state,
            )
        elif editor in JSON_HOOK_RUNTIMES:
            ok = remove_pack_json_runtime(
                editor,
                name,
            )
        else:
            print(f"  ERROR: no remover for runtime '{editor}'")
            return False
        if not ok:
            if transaction_snapshots is not None:
                _restore_file_snapshots(transaction_snapshots)
            return False

        if gemini_config_update is None:
            if transaction_snapshots is not None and mcp_plan is not None:
                _apply_config_updates_owned(
                    transaction_snapshots,
                    mcp_plan.updates,
                )
                _print_mcp_removal_result(mcp_plan)
            else:
                apply_plugin_mcp_removal(mcp_plan)
        if transaction_snapshots is not None:
            _apply_rule_plan_owned(transaction_snapshots, rule_plan)
            _apply_asset_removal(transaction_snapshots, asset_removal_plan)
        installed = [p for p in installed if p != name]
        _set_installed(state, editor, installed)
        _forget_version(state, editor, name)
        _forget_mcp_ownership(state, editor, name)
        _forget_rule_ownership(state, editor, name)
        _release_shared_asset_consumer(state, name, editor)
        if transaction_snapshots is not None:
            transaction_snapshots.expect_file(
                PLUGINS_STATE_FILE,
                _state_content(state),
                _expected_replacement_mode(
                    transaction_snapshots,
                    PLUGINS_STATE_FILE,
                ),
            )
        _write_plugin_state(state, transaction_snapshots)
        if transaction_snapshots is not None:
            _after_plugin_state_write(state, editor, name, "remove")
            transaction_snapshots.commit()
        return True
    except Exception as error:
        _rollback_plugin_transaction(transaction_snapshots, error)
        raise


def pack_update_pending(name: str, editor: str) -> tuple[bool, str, str]:
    """(needs_update, installed_version, available_version) for one pack."""
    state = load_state()
    if name not in _installed_for(state, editor):
        return False, "", ""
    pack = find_pack(name)
    if not pack:
        return False, _installed_version(state, editor, name), ""
    available = str(pack.get("version", ""))
    current = _installed_version(state, editor, name)
    return current != available, current, available


def update_pack(name: str, editor: str, *, force: bool = False) -> bool:
    init_requests: list[Path] = []
    with _plugin_operation_gate():
        with _plugin_lifecycle_lock():
            updated = _update_pack_locked(
                name,
                editor,
                force=force,
                init_requests=init_requests,
            )
        if updated:
            _run_plugin_init_requests(init_requests)
    return updated


def _update_pack_locked(
    name: str,
    editor: str,
    *,
    force: bool = False,
    init_requests: list[Path] | None = None,
) -> bool:
    state = load_state()
    if name not in _installed_for(state, editor):
        print(
            f"  Plugin '{name}' is not installed for {editor} — use 'install' instead"
        )
        return False

    pending, current, available = pack_update_pending(name, editor)
    if not pending and not force:
        # Silent no-op by design: `ai-toolkit update` runs this for every
        # installed pack on every invocation.
        return True

    pack = find_pack(name)
    if not pack:
        print(f"  Plugin '{name}' manifest not found")
        return False
    pack_dir = Path(pack["_dir"])
    # Update is remove + install, so validate every MCP collision against the
    # current ownership record before remove_pack can touch state or assets.
    mcp_install_plan = prepare_plugin_mcp_install(
        name,
        editor,
        pack,
        pack_dir,
        _mcp_ownership_for(state, editor, name),
    )
    hook_specs: list[dict] = []
    rule_install_plan: PluginRulePlan | None = None
    mcp_removal_plan: PluginMcpRemovalPlan | None = None
    rule_removal_plan: PluginRulePlan | None = None
    if editor in JSON_HOOK_RUNTIMES:
        hook_specs = _resolve_pack_hooks(pack, pack_dir)
        rule_specs = _resolve_pack_rules(pack, pack_dir)
        rule_install_plan = prepare_plugin_rule_install(
            name,
            editor,
            rule_specs,
            _rule_ownership_for(state, editor, name),
        )
        mcp_removal_plan = prepare_plugin_mcp_removal(
            name,
            editor,
            _mcp_ownership_for(state, editor, name),
        )
        rule_removal_plan = prepare_plugin_rule_removal(
            name,
            editor,
            _rule_ownership_for(state, editor, name),
        )
    asset_specs = (
        _prepare_asset_specs(name, pack_dir, hook_specs)
        if editor in JSON_HOOK_RUNTIMES
        else ()
    )
    owned_asset_paths = (
        _owned_asset_paths(state, name, editor) if editor in JSON_HOOK_RUNTIMES else ()
    )

    if current and available:
        print(f"  Updating: {name} for {editor} ({current} -> {available})")
    else:
        print(f"  Updating: {name} for {editor}")
    rollback_snapshots = (
        _snapshot_files(
            _plugin_update_transaction_paths(
                name,
                pack_dir,
                editor,
                hook_specs,
                mcp_install_plan,
                rule_install_plan,
                mcp_removal_plan,
                rule_removal_plan,
                asset_specs,
                owned_asset_paths,
            )
        )
        if editor in JSON_HOOK_RUNTIMES
        else None
    )
    outer_asset_removal = (
        _preflight_asset_removal(
            rollback_snapshots,
            _shared_asset_ownership_for(state, name),
            name,
            editor,
        )
        if rollback_snapshots is not None
        else AssetRemovalPlan((), ())
    )
    hook_removal_update: ConfigUpdate | None = None
    gemini_removal_update: ConfigUpdate | None = None
    if editor in JSON_HOOK_RUNTIMES:
        gemini_removal_update = (
            _prepare_gemini_combined_removal(name, mcp_removal_plan)
            if editor == "gemini"
            else None
        )
        hook_removal_update = (
            gemini_removal_update
            if gemini_removal_update is not None
            else _prepare_json_runtime_hook_removal(editor, name)
        )
    if rollback_snapshots is not None:
        if hook_removal_update is not None:
            _expect_config_updates(rollback_snapshots, [hook_removal_update])
        if gemini_removal_update is None and mcp_removal_plan is not None:
            _expect_config_updates(rollback_snapshots, mcp_removal_plan.updates)
        _expect_rule_plan(rollback_snapshots, rule_removal_plan)
        for _key, path, _before in outer_asset_removal.removable:
            rollback_snapshots.expect_absent(path)
            rollback_snapshots.backup(path)
        removal_state = _state_after_removal(
            state,
            editor,
            name,
        )
        rollback_snapshots.expect_file(
            PLUGINS_STATE_FILE,
            _state_content(removal_state),
            _expected_replacement_mode(
                rollback_snapshots,
                PLUGINS_STATE_FILE,
            ),
        )
    transaction_reports: list[PluginFileTransaction] = []
    try:
        if not _remove_pack_locked(
            name,
            editor,
            transaction_reports=transaction_reports,
        ):
            if rollback_snapshots is not None:
                _restore_file_snapshots(rollback_snapshots)
            return False
        if rollback_snapshots is not None:
            for report in transaction_reports:
                rollback_snapshots.accept_nested_states(report.final_exact_states())
        installed = _install_pack_locked(
            name,
            editor,
            transaction_reports=transaction_reports,
            init_requests=init_requests,
        )
        if not installed and rollback_snapshots is not None:
            for report in transaction_reports:
                rollback_snapshots.accept_nested_states(report.final_exact_states())
            _restore_file_snapshots(rollback_snapshots)
        elif installed and rollback_snapshots is not None:
            rollback_snapshots.commit()
        return installed
    except Exception as error:
        if rollback_snapshots is not None:
            for report in transaction_reports:
                rollback_snapshots.accept_nested_states(report.final_exact_states())
        _rollback_plugin_transaction(rollback_snapshots, error)
        raise


# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

CLEANABLE_PLUGINS = {"memory-pack"}


def clean_pack(name: str, days: int = 90) -> bool:
    """Prune old data for a plugin. Returns True if successful."""
    state = load_state()
    installed_anywhere = any(
        name in _installed_for(state, editor) for editor in VALID_EDITORS
    )
    if not installed_anywhere:
        print(f"  Plugin '{name}' is not installed")
        return False

    if name not in CLEANABLE_PLUGINS:
        print(f"  Plugin '{name}' has no data to clean")
        return False

    if name == "memory-pack":
        return _clean_memory_pack(days)

    return False


def _clean_memory_pack(days: int) -> bool:
    """Prune memory-pack observations older than N days."""
    if not MEMORY_DB.is_file():
        print("  No memory database found")
        return False

    try:
        conn = sqlite.connect(str(MEMORY_DB))
        cur = conn.cursor()

        before = cur.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        cur.execute(
            "DELETE FROM observations WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        pruned_obs = cur.rowcount
        cur.execute(
            "DELETE FROM sessions WHERE session_id NOT IN "
            "(SELECT DISTINCT session_id FROM observations) "
            "AND ended_at IS NOT NULL"
        )
        pruned_sessions = cur.rowcount

        conn.commit()
        conn.execute("VACUUM")
        conn.close()

        after = before - pruned_obs
        print(f"  Cleaned memory-pack (older than {days} days):")
        print(f"    Observations: {before} -> {after} (pruned {pruned_obs})")
        print(f"    Sessions pruned: {pruned_sessions}")
        print(f"    DB size: {_human_size(MEMORY_DB.stat().st_size)}")
        return True
    except sqlite.Error as e:
        print(f"  ERROR: {e}")
        return False


def _human_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} B"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ---------------------------------------------------------------------------
# List / Status
# ---------------------------------------------------------------------------


def cmd_list(editors: list[str]) -> None:
    packs = list_available()
    state = load_state()

    print("Available plugin packs:")
    print()
    runtime_header = "".join(
        f" {PLUGIN_EDITOR_LABELS[editor]:>7}" for editor in VALID_EDITORS
    )
    print(
        f"  {'Name':<20} {'Domain':<12} {'Status':<14} {'Agents':>7} "
        f"{'Skills':>7} {'Hooks':>6}{runtime_header}"
    )
    runtime_divider = "".join(f" {'-' * 7}" for _editor in VALID_EDITORS)
    print(
        f"  {'-' * 20} {'-' * 12} {'-' * 14} {'-' * 7} "
        f"{'-' * 7} {'-' * 6}{runtime_divider}"
    )

    for pack in packs:
        inc = pack.get("includes", {})
        runtime_status = "".join(
            f" {('YES' if pack['name'] in _installed_for(state, editor) else ''):>7}"
            for editor in VALID_EDITORS
        )
        print(
            f"  {pack['name']:<20} {pack.get('domain', ''):<12} {pack.get('status', ''):<14}"
            f" {len(inc.get('agents', [])):>7} {len(inc.get('skills', [])):>7} {len(inc.get('hooks', [])):>6}"
            f"{runtime_status}"
        )

    print()
    totals = " | ".join(
        f"{PLUGIN_EDITOR_LABELS[editor]}: {len(_installed_for(state, editor))}"
        for editor in VALID_EDITORS
    )
    print(f"  Total: {len(packs)} packs | {totals}")
    print()
    editor_values = "|".join((*VALID_EDITORS, "all"))
    print(f"  Install:     ai-toolkit plugin install --editor {editor_values} <name>")
    print(f"  Install all: ai-toolkit plugin install --editor {editor_values} --all")
    print(f"  Update:      ai-toolkit plugin update --editor {editor_values} <name>")
    print(f"  Remove:      ai-toolkit plugin remove --editor {editor_values} <name>")
    print("  Clean:       ai-toolkit plugin clean <name> [--days N]")


def _show_memory_stats() -> None:
    if not MEMORY_DB.is_file():
        print("    DB: not initialized")
        return
    try:
        conn = sqlite.connect(str(MEMORY_DB))
        cur = conn.cursor()
        obs_count = cur.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        sess_count = cur.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        oldest = cur.execute("SELECT MIN(created_at) FROM observations").fetchone()[0]
        newest = cur.execute("SELECT MAX(created_at) FROM observations").fetchone()[0]
        conn.close()
        db_size = _human_size(MEMORY_DB.stat().st_size)
        print(f"    DB: {db_size} | {obs_count} observations | {sess_count} sessions")
        if oldest:
            print(f"    Range: {oldest} — {newest}")
    except sqlite.Error:
        print(f"    DB: {_human_size(MEMORY_DB.stat().st_size)} (error reading stats)")


def _show_pack_status(name: str, pack_dir: Path) -> None:
    """Let a pack report its own state via scripts/status.py.

    Generic counterpart to the install-time init.py hook. Before this, anything
    beyond a hook listing meant another hardcoded `if name == ...` branch, which
    is why memory-pack is the only pack that ever reported anything.

    The script owns its output format; it is indented and shown verbatim.
    Failure is not an error: status must never be the thing that breaks.
    """
    status_script = pack_dir / "scripts" / "status.py"
    if not status_script.is_file():
        return
    try:
        result = subprocess.run(
            ["python3", str(status_script)],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"    (status unavailable: {exc})")
        return
    stream = result.stdout if result.stdout.strip() else result.stderr
    for line in stream.strip().splitlines():
        print(f"    {line}")


def cmd_status(editors: list[str]) -> None:
    state = load_state()
    shown = False
    for editor in editors:
        installed = _installed_for(state, editor)
        print(f"Installed plugins for {editor}:")
        if not installed:
            print("  (none)")
            print()
            continue
        shown = True
        for name in installed:
            pack = find_pack(name)
            if not pack:
                print(f"  {name}: (manifest not found — orphaned?)")
                continue
            print(f"  {name}: {pack.get('description', '')}")
            if editor == "claude":
                hooks = list(HOOKS_DIR.glob(f"plugin-{name}-*"))
                if hooks:
                    print(f"    Hooks: {', '.join(h.name for h in hooks)}")
            elif editor == "codex":
                hooks = sorted(CODEX_HOOKS_DIR.glob(f"plugin-{name}-*"))
                if hooks:
                    print(f"    Hooks: {', '.join(h.name for h in hooks)}")
            if name == "memory-pack":
                _show_memory_stats()
            else:
                _show_pack_status(name, Path(pack["_dir"]))
        print()

    if not shown and all(not _installed_for(state, editor) for editor in editors):
        print("Run: ai-toolkit plugin list")


# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------


def _parse_editors(args: list[str]) -> tuple[list[str], list[str]]:
    editors = ["claude"]
    remainder: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--editor="):
            value = arg.split("=", 1)[1]
        elif arg == "--editor":
            if i + 1 >= len(args):
                print("ERROR: --editor requires a value")
                sys.exit(1)
            i += 1
            value = args[i]
        else:
            remainder.append(arg)
            i += 1
            continue

        if value == "all":
            editors = list(VALID_EDITORS)
        else:
            parsed = [item.strip() for item in value.split(",") if item.strip()]
            invalid = [item for item in parsed if item not in VALID_EDITORS]
            if invalid:
                print(f"ERROR: unsupported editor(s): {', '.join(invalid)}")
                print(f"Valid values: {', '.join((*VALID_EDITORS, 'all'))}")
                sys.exit(1)
            editors = parsed or ["claude"]
        i += 1
    return editors, remainder


def _cmd_install(args: list[str], editors: list[str]) -> None:
    if not args:
        print(
            "Usage: ai-toolkit plugin install [--editor claude|codex|cursor|gemini|all] <pack-name> [...]"
        )
        print(
            "       ai-toolkit plugin install [--editor claude|codex|cursor|gemini|all] --all"
        )
        sys.exit(1)
    names = [pack["name"] for pack in list_available()] if "--all" in args else args
    for editor in editors:
        if "--all" in args:
            print(f"Installing all {len(names)} plugin packs for {editor}...\n")
        ok = 0
        for name in names:
            if install_pack(name, editor):
                ok += 1
            print()
        if "--all" in args:
            print(f"Installed: {ok}/{len(names)} packs for {editor}")
            print()


def _cmd_remove(args: list[str], editors: list[str]) -> None:
    if not args:
        print(
            "Usage: ai-toolkit plugin remove [--editor claude|codex|cursor|gemini|all] <pack-name> [...]"
        )
        print(
            "       ai-toolkit plugin remove [--editor claude|codex|cursor|gemini|all] --all"
        )
        sys.exit(1)
    state = load_state()
    for editor in editors:
        names = list(_installed_for(state, editor)) if "--all" in args else args
        if not names:
            print(f"No plugins installed for {editor}.")
            print()
            continue
        for name in names:
            remove_pack(name, editor)
            print()


def _cmd_update(args: list[str], editors: list[str]) -> None:
    if not args:
        print(
            "Usage: ai-toolkit plugin update [--editor claude|codex|cursor|gemini|all] <pack-name> [...]"
        )
        print(
            "       ai-toolkit plugin update [--editor claude|codex|cursor|gemini|all] --all [--dry-run]"
        )
        sys.exit(1)

    dry_run = "--dry-run" in args or "--list" in args
    force = "--force" in args
    everything = "--all" in args
    explicit = [a for a in args if not a.startswith("--")]

    state = load_state()
    had_failures = False
    for editor in editors:
        names = list(_installed_for(state, editor)) if everything else explicit
        if not names:
            if everything:
                # Nothing installed is the common case; do not make the core
                # update noisy about it.
                continue
            print(f"No plugins installed for {editor}.")
            print()
            continue

        if dry_run:
            pending = []
            for name in names:
                needs, current, available = pack_update_pending(name, editor)
                if needs or force:
                    pending.append(
                        f"{name} ({current or 'unrecorded'} -> {available or 'unknown'})"
                    )
            if pending:
                print(f"Would update for {editor}: {', '.join(pending)}")
            else:
                print(f"All {len(names)} pack(s) up to date for {editor}")
            print()
            continue

        ok = 0
        failed: list[str] = []
        for name in names:
            try:
                if update_pack(name, editor, force=force):
                    ok += 1
                else:
                    failed.append(name)
                    had_failures = True
            except Exception as exc:  # noqa: BLE001
                # A pack failure must never abort the run: `ai-toolkit update`
                # calls this after the core update has already succeeded.
                print(f"  WARN update failed for {name}: {exc}")
                failed.append(name)
                had_failures = True
        if everything and (failed or force):
            print(f"Updated: {ok}/{len(names)} packs for {editor}")
            if failed:
                print(f"  Failed: {', '.join(failed)}")
            print()
    if had_failures:
        sys.exit(1)


def _parse_clean_args(args: list[str]) -> tuple[list[str], int]:
    days = 90
    pack_names: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--days" and i + 1 < len(args):
            try:
                days = int(args[i + 1])
                if days <= 0:
                    print(f"ERROR: --days must be positive, got {days}")
                    sys.exit(1)
            except ValueError:
                print(f"ERROR: --days requires a number, got '{args[i + 1]}'")
                sys.exit(1)
            i += 2
        else:
            pack_names.append(args[i])
            i += 1
    return pack_names, days


def _cmd_clean(args: list[str]) -> None:
    if not args:
        print("Usage: ai-toolkit plugin clean <pack-name> [--days N]")
        print("       Default: prune data older than 90 days")
        sys.exit(1)
    pack_names, days = _parse_clean_args(args)
    if not pack_names:
        print("Usage: ai-toolkit plugin clean <pack-name> [--days N]")
        sys.exit(1)
    for name in pack_names:
        clean_pack(name, days)
        print()


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]
    editors, args = _parse_editors(sys.argv[2:])

    if action == "list":
        cmd_list(editors)
        return
    if action == "status":
        cmd_status(editors)
        return
    if action == "install":
        _cmd_install(args, editors)
        return
    if action == "remove":
        _cmd_remove(args, editors)
        return
    if action == "update":
        _cmd_update(args, editors)
        return
    if action == "clean":
        _cmd_clean(args)
        return

    print(f"Unknown action: {action}")
    print("Actions: install, remove, update, clean, list, status")
    sys.exit(1)


if __name__ == "__main__":
    main()
