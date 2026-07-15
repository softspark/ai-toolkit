#!/usr/bin/env python3
"""ai-toolkit plugin — install, remove, update, clean, and list plugin packs.

Usage:
    plugin.py list [--editor claude|codex|all]
    plugin.py status [--editor claude|codex|all]
    plugin.py install [--editor claude|codex|all] <pack-name> [<pack-name> ...]
    plugin.py install [--editor claude|codex|all] --all
    plugin.py remove [--editor claude|codex|all] <pack-name> [<pack-name> ...]
    plugin.py remove [--editor claude|codex|all] --all
    plugin.py update [--editor claude|codex|all] <pack-name> [<pack-name> ...]
    plugin.py update [--editor claude|codex|all] --all
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
import os
import re
import shutil
import sqlite3 as sqlite
import subprocess
import sys
import tempfile
from pathlib import Path

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
from plugin_schema import resolve_hook_event


PLUGINS_DIR = app_dir / "plugins"
CLAUDE_DIR = Path.home() / ".claude"
CODEX_ROOT = Path.home()
CODEX_HOME = Path(os.environ.get("CODEX_HOME", CODEX_ROOT / ".codex")).expanduser()
CODEX_HOOKS_DIR = CODEX_HOME / "ai-toolkit-hooks"
HOOKS_DIR = _HOOKS_DIR
PLUGINS_STATE_FILE = TOOLKIT_DATA_DIR / "plugins.json"
MEMORY_DB = TOOLKIT_DATA_DIR / "memory.db"

VALID_EDITORS = ("claude", "codex")
CODEX_PLUGIN_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
CODEX_PLUGIN_ASSET_MARKER = "# ai-toolkit-managed: codex-plugin-hook"


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def _empty_state() -> dict:
    return {
        "targets": {
            "claude": {"installed": []},
            "codex": {"installed": []},
        }
    }


def load_state() -> dict:
    """Load installed plugins state with backwards compatibility."""
    state = _empty_state()
    if PLUGINS_STATE_FILE.is_file():
        try:
            with open(PLUGINS_STATE_FILE, encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError):
            raw = {}

        if isinstance(raw, dict):
            if isinstance(raw.get("installed"), list):
                # Legacy format: Claude-only installs.
                state["targets"]["claude"]["installed"] = sorted(set(raw["installed"]))

            targets = raw.get("targets", {})
            if isinstance(targets, dict):
                for editor in VALID_EDITORS:
                    installed = targets.get(editor, {}).get("installed", [])
                    if isinstance(installed, list):
                        state["targets"][editor]["installed"] = sorted(set(installed))
    return state


def save_state(state: dict) -> None:
    """Save installed plugins state."""
    PLUGINS_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PLUGINS_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def _installed_for(state: dict, editor: str) -> list[str]:
    return list(state.get("targets", {}).get(editor, {}).get("installed", []))


def _set_installed(state: dict, editor: str, names: list[str]) -> None:
    state.setdefault("targets", {}).setdefault(editor, {})
    state["targets"][editor]["installed"] = sorted(set(names))


# ---------------------------------------------------------------------------
# Plugin discovery
# ---------------------------------------------------------------------------

def list_available() -> list[dict]:
    """List all available plugin packs."""
    packs: list[dict] = []
    if not PLUGINS_DIR.is_dir():
        return packs
    for d in sorted(PLUGINS_DIR.iterdir()):
        manifest = d / "plugin.json"
        if not manifest.is_file():
            continue
        try:
            with open(manifest, encoding="utf-8") as f:
                data = json.load(f)
            data["_dir"] = str(d)
            packs.append(data)
        except (json.JSONDecodeError, OSError):
            continue
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
        specs.append({
            "ref": hook_ref,
            "name": hook_name,
            "event": event,
            "source": source,
            "is_core": is_core,
        })
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
        specs.append({
            "name": source.stem,
            "source": source,
            "is_core": is_core,
        })
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
        dest = scripts_dest / script_file.name
        shutil.copy2(script_file, dest)
        if script_file.suffix in (".py", ".sh"):
            dest.chmod(dest.stat().st_mode | 0o111)
        print(f"    Copied script: {script_file.name}")
        installed_items.append(f"script:{dest}")

    init_script = plugin_scripts_dir / "init_db.py"
    if init_script.is_file():
        result = subprocess.run(
            ["python3", str(init_script)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            print(f"    Init: {result.stdout.strip()}")
        elif result.returncode != 0 and result.stderr.strip():
            print(f"    WARN init failed: {result.stderr.strip()}")


def _copy_plugin_hook_scripts(name: str, hook_specs: list[dict], installed_items: list[str]) -> None:
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
        return f"\"$HOME/.softspark/ai-toolkit/hooks/{spec['name']}\""
    return f"\"$HOME/.softspark/ai-toolkit/hooks/plugin-{name}-{spec['name']}\""


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
                base = Path(command.replace("\"", "")).name
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


def _install_claude_skills(pack: dict, pack_dir: Path, installed_items: list[str]) -> None:
    for skill in pack.get("includes", {}).get("skills", []):
        skill_dir = CLAUDE_DIR / "skills" / skill
        source_dir = _resolve_skill_source(pack_dir, skill)
        if skill_dir.exists() or skill_dir.is_symlink():
            print(f"    OK skill: {skill}")
        elif source_dir:
            skill_dir.parent.mkdir(parents=True, exist_ok=True)
            skill_dir.symlink_to(source_dir)
            print(f"    Linked skill: {skill}")
            installed_items.append(f"skill:{skill}")
        else:
            print(f"    WARN skill not found: {skill}")


def _install_claude_agents(pack: dict, installed_items: list[str]) -> None:
    for agent in pack.get("includes", {}).get("agents", []):
        agent_file = CLAUDE_DIR / "agents" / f"{agent}.md"
        source_file = app_dir / "agents" / f"{agent}.md"
        if agent_file.exists() or agent_file.is_symlink():
            print(f"    OK agent: {agent}")
        elif source_file.is_file():
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
        event_hooks = hooks.setdefault(spec["event"], [])
        event_hooks = [h for h in event_hooks if h.get("_source") != source_tag]
        event_hooks.append(entry)
        hooks[spec["event"]] = event_hooks

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
    _install_claude_agents(pack, installed_items)
    _install_claude_skills(pack, pack_dir, installed_items)
    _copy_plugin_hook_scripts(name, hook_specs, installed_items)
    _copy_plugin_scripts(name, pack_dir, installed_items)
    _install_claude_rules(name, rule_specs)
    if any(not spec["is_core"] for spec in hook_specs):
        _merge_claude_hooks(name, hook_specs)

    print(f"  Done: {name} for claude ({len(installed_items)} file items)")
    return True


def remove_pack_claude(name: str, pack: dict, pack_dir: Path, *, keep_shared_assets: bool) -> bool:
    hook_specs = _resolve_pack_hooks(pack, pack_dir)
    rule_specs = _resolve_pack_rules(pack, pack_dir)

    if not keep_shared_assets:
        for hook in HOOKS_DIR.glob(f"plugin-{name}-*.sh"):
            hook.unlink()
            print(f"    Removed hook: {hook.name}")

        scripts_dir = TOOLKIT_DATA_DIR / "plugin-scripts" / name
        if scripts_dir.is_dir():
            shutil.rmtree(scripts_dir)
            print(f"    Removed scripts: {scripts_dir}")

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
                if not _codex_command_has_owner(command, TOOLKIT_COMMAND_MARKER.split("=", 1)[1]):
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


def _write_codex_plugin_asset(destination: Path, content: bytes, mode: int = 0o755) -> None:
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
            raise RuntimeError(f"Refusing user-owned Codex hook collision: {destination}")
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
        f'AI_TOOLKIT_HOOK_OWNER={owner} '
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
            "hooks": [{
                "type": "command",
                "command": _codex_plugin_command(name, spec),
            }]
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
        for match in re.findall(r"<!-- TOOLKIT:(plugin-" + re.escape(name) + r"-[^ ]+) START -->", content):
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


def remove_pack_codex(name: str, pack: dict, pack_dir: Path, *, keep_shared_assets: bool) -> bool:
    _assert_safe_codex_surface()
    _strip_codex_hooks(name)

    if CODEX_HOOKS_DIR.is_dir():
        for hook in CODEX_HOOKS_DIR.glob(f"plugin-{name}-*.sh"):
            if hook.is_symlink():
                raise RuntimeError(f"Refusing symlinked Codex plugin hook: {hook}")
            if _is_owned_codex_plugin_asset(hook, name):
                hook.unlink()
                print(f"    Removed Codex hook: {hook.name}")
            else:
                print(f"    WARN preserved user-owned Codex hook: {hook.name}")

    if not keep_shared_assets:
        # Clean paths used by releases before native Codex plugin assets moved
        # under $CODEX_HOME. Claude still owns these when installed for both.
        for hook in HOOKS_DIR.glob(f"plugin-{name}-*.sh"):
            hook.unlink()
            print(f"    Removed hook: {hook.name}")

        scripts_dir = TOOLKIT_DATA_DIR / "plugin-scripts" / name
        if scripts_dir.is_dir():
            shutil.rmtree(scripts_dir)
            print(f"    Removed scripts: {scripts_dir}")

    _remove_codex_rules(name)
    print(f"  Done: removed {name} from codex")
    return True


# ---------------------------------------------------------------------------
# Common actions
# ---------------------------------------------------------------------------

def install_pack(name: str, editor: str) -> bool:
    pack = find_pack(name)
    if not pack:
        print(f"  ERROR: plugin pack '{name}' not found")
        print(f"  Available: {', '.join(p['name'] for p in list_available())}")
        return False

    pack_dir = Path(pack["_dir"])
    print(f"  Installing: {name} for {editor} ({pack.get('description', '')})")

    ok = install_pack_claude(name, pack, pack_dir) if editor == "claude" else install_pack_codex(name, pack, pack_dir)
    if not ok:
        return False

    state = load_state()
    installed = _installed_for(state, editor)
    if name not in installed:
        installed.append(name)
    _set_installed(state, editor, installed)
    save_state(state)
    return True


def remove_pack(name: str, editor: str) -> bool:
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
    keep_shared_assets = any(
        name in _installed_for(state, other)
        for other in VALID_EDITORS
        if other != editor
    )
    ok = (
        remove_pack_claude(name, pack, pack_dir, keep_shared_assets=keep_shared_assets)
        if editor == "claude"
        else remove_pack_codex(name, pack, pack_dir, keep_shared_assets=keep_shared_assets)
    )
    if not ok:
        return False

    installed = [p for p in installed if p != name]
    _set_installed(state, editor, installed)
    save_state(state)
    return True


def update_pack(name: str, editor: str) -> bool:
    state = load_state()
    if name not in _installed_for(state, editor):
        print(f"  Plugin '{name}' is not installed for {editor} — use 'install' instead")
        return False

    print(f"  Updating: {name} for {editor}")
    remove_pack(name, editor)
    return install_pack(name, editor)


# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

CLEANABLE_PLUGINS = {"memory-pack"}


def clean_pack(name: str, days: int = 90) -> bool:
    """Prune old data for a plugin. Returns True if successful."""
    state = load_state()
    installed_anywhere = any(name in _installed_for(state, editor) for editor in VALID_EDITORS)
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
    print(
        f"  {'Name':<20} {'Domain':<12} {'Status':<14} {'Agents':>7} {'Skills':>7} {'Hooks':>6}"
        f"  {'Claude':>6} {'Codex':>6}"
    )
    print(
        f"  {'-'*20} {'-'*12} {'-'*14} {'-'*7} {'-'*7} {'-'*6}"
        f"  {'-'*6} {'-'*6}"
    )

    for pack in packs:
        inc = pack.get("includes", {})
        claude = "YES" if pack["name"] in _installed_for(state, "claude") else ""
        codex = "YES" if pack["name"] in _installed_for(state, "codex") else ""
        print(
            f"  {pack['name']:<20} {pack.get('domain',''):<12} {pack.get('status',''):<14}"
            f" {len(inc.get('agents',[])):>7} {len(inc.get('skills',[])):>7} {len(inc.get('hooks',[])):>6}"
            f"  {claude:>6} {codex:>6}"
        )

    print()
    print(
        f"  Total: {len(packs)} packs | Claude: {len(_installed_for(state, 'claude'))}"
        f" | Codex: {len(_installed_for(state, 'codex'))}"
    )
    print()
    print("  Install:     ai-toolkit plugin install --editor claude|codex|all <name>")
    print("  Install all: ai-toolkit plugin install --editor claude|codex|all --all")
    print("  Update:      ai-toolkit plugin update --editor claude|codex|all <name>")
    print("  Remove:      ai-toolkit plugin remove --editor claude|codex|all <name>")
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
                hooks = list(HOOKS_DIR.glob(f"plugin-{name}-*.sh"))
                if hooks:
                    print(f"    Hooks: {', '.join(h.name for h in hooks)}")
            elif editor == "codex":
                hooks = sorted(CODEX_HOOKS_DIR.glob(f"plugin-{name}-*.sh"))
                if hooks:
                    print(f"    Hooks: {', '.join(h.name for h in hooks)}")
            if name == "memory-pack":
                _show_memory_stats()
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
                print("Valid values: claude, codex, all")
                sys.exit(1)
            editors = parsed or ["claude"]
        i += 1
    return editors, remainder


def _cmd_install(args: list[str], editors: list[str]) -> None:
    if not args:
        print("Usage: ai-toolkit plugin install [--editor claude|codex|all] <pack-name> [...]")
        print("       ai-toolkit plugin install [--editor claude|codex|all] --all")
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
        print("Usage: ai-toolkit plugin remove [--editor claude|codex|all] <pack-name> [...]")
        print("       ai-toolkit plugin remove [--editor claude|codex|all] --all")
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
        print("Usage: ai-toolkit plugin update [--editor claude|codex|all] <pack-name> [...]")
        print("       ai-toolkit plugin update [--editor claude|codex|all] --all")
        sys.exit(1)
    state = load_state()
    for editor in editors:
        names = list(_installed_for(state, editor)) if "--all" in args else args
        if not names:
            print(f"No plugins installed for {editor}.")
            print()
            continue
        if "--all" in args:
            print(f"Updating {len(names)} installed plugin(s) for {editor}...\n")
        ok = 0
        for name in names:
            if update_pack(name, editor):
                ok += 1
            print()
        if "--all" in args:
            print(f"Updated: {ok}/{len(names)} packs for {editor}")
            print()


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
