#!/usr/bin/env python3
"""ai-toolkit plugin — install, remove, update, clean, and list plugin packs.

Usage:
    plugin.py install <pack-name> [<pack-name> ...]
    plugin.py install --all
    plugin.py remove <pack-name> [<pack-name> ...]
    plugin.py remove --all
    plugin.py update <pack-name> [<pack-name> ...]
    plugin.py update --all
    plugin.py clean <pack-name> [--days N]
    plugin.py list
    plugin.py status

Actions:
    install   Copy plugin hooks/scripts, verify agents+skills are linked
    remove    Remove plugin hooks/scripts, leave core agents+skills intact
    update    Re-install plugin (remove + install), --all updates all installed
    clean     Prune old data (e.g. memory-pack observations older than --days N, default 90)
    list      Show available plugin packs with status
    status    Show what's currently installed
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3 as sqlite
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir, app_dir
from plugin_schema import resolve_hook_event, validate_manifest, validate_references


PLUGINS_DIR = app_dir / "plugins"
CLAUDE_DIR = Path.home() / ".claude"
HOOKS_DIR = Path.home() / ".ai-toolkit" / "hooks"
PLUGINS_STATE_FILE = Path.home() / ".ai-toolkit" / "plugins.json"


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    """Load installed plugins state."""
    if PLUGINS_STATE_FILE.is_file():
        try:
            with open(PLUGINS_STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"installed": []}


def save_state(state: dict) -> None:
    """Save installed plugins state."""
    PLUGINS_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PLUGINS_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


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
            with open(manifest) as f:
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


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

def _link_agents(includes: dict, pack_dir: Path, installed_items: list[str]) -> None:
    """Verify and link referenced agents from a plugin pack."""
    for agent in includes.get("agents", []):
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


def _link_skills(includes: dict, pack_dir: Path, installed_items: list[str]) -> None:
    """Verify and link referenced skills from a plugin pack."""
    for skill in includes.get("skills", []):
        skill_dir = CLAUDE_DIR / "skills" / skill
        source_dir = app_dir / "skills" / skill
        if skill_dir.exists() or skill_dir.is_symlink():
            print(f"    OK skill: {skill}")
        elif source_dir.is_dir():
            skill_dir.parent.mkdir(parents=True, exist_ok=True)
            skill_dir.symlink_to(source_dir)
            print(f"    Linked skill: {skill}")
            installed_items.append(f"skill:{skill}")
        else:
            plugin_skill = pack_dir / "skills" / skill / "SKILL.md"
            if plugin_skill.is_file():
                skill_dir.parent.mkdir(parents=True, exist_ok=True)
                skill_dir.symlink_to(pack_dir / "skills" / skill)
                print(f"    Linked skill (from plugin): {skill}")
                installed_items.append(f"skill:{skill}")
            else:
                print(f"    WARN skill not found: {skill}")


def _copy_hooks(name: str, pack_dir: Path, installed_items: list[str]) -> None:
    """Copy plugin-specific hook scripts."""
    plugin_hooks_dir = pack_dir / "hooks"
    if not plugin_hooks_dir.is_dir():
        return
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    for hook_file in sorted(plugin_hooks_dir.glob("*.sh")):
        dest = HOOKS_DIR / f"plugin-{name}-{hook_file.name}"
        shutil.copy2(hook_file, dest)
        dest.chmod(dest.stat().st_mode | 0o111)
        print(f"    Copied hook: {hook_file.name} -> {dest.name}")
        installed_items.append(f"hook:{dest.name}")


def _copy_scripts(name: str, pack_dir: Path, installed_items: list[str]) -> None:
    """Copy plugin-specific scripts and run init if present."""
    plugin_scripts_dir = pack_dir / "scripts"
    if not plugin_scripts_dir.is_dir():
        return
    scripts_dest = Path.home() / ".ai-toolkit" / "plugin-scripts" / name
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
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"    Init: {result.stdout.strip()}")
        else:
            print(f"    WARN init failed: {result.stderr.strip()}")


def install_pack(name: str) -> bool:
    """Install a single plugin pack. Returns True if successful."""
    pack = find_pack(name)
    if not pack:
        print(f"  ERROR: plugin pack '{name}' not found")
        print(f"  Available: {', '.join(p['name'] for p in list_available())}")
        return False

    pack_dir = Path(pack["_dir"])
    includes = pack.get("includes", {})
    installed_items: list[str] = []

    print(f"  Installing: {name} ({pack.get('description', '')})")

    _link_agents(includes, pack_dir, installed_items)
    _link_skills(includes, pack_dir, installed_items)
    _copy_hooks(name, pack_dir, installed_items)
    _copy_scripts(name, pack_dir, installed_items)

    plugin_hooks_dir = pack_dir / "hooks"
    if plugin_hooks_dir.is_dir() and any(plugin_hooks_dir.glob("*.sh")):
        _inject_plugin_hooks(name, pack_dir)

    state = load_state()
    if name not in state["installed"]:
        state["installed"].append(name)
    save_state(state)

    print(f"  Done: {name} ({len(installed_items)} items)")
    return True


def _inject_plugin_hooks(name: str, pack_dir: Path) -> None:
    """Register plugin hooks in settings.json via manual JSON merge."""
    settings_path = CLAUDE_DIR / "settings.json"
    if not settings_path.is_file():
        return

    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    hooks = settings.setdefault("hooks", {})
    plugin_hooks_dir = pack_dir / "hooks"

    for hook_file in sorted(plugin_hooks_dir.glob("*.sh")):
        # Determine event from hook filename or manifest
        event = _guess_event(hook_file.name, name)
        if not event:
            continue

        dest_path = HOOKS_DIR / f"plugin-{name}-{hook_file.name}"
        entry = {
            "_source": f"ai-toolkit-plugin-{name}",
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": str(dest_path),
                }
            ],
        }

        event_hooks = hooks.setdefault(event, [])
        # Remove old entries from this plugin
        event_hooks = [h for h in event_hooks if h.get("_source") != f"ai-toolkit-plugin-{name}"]
        event_hooks.append(entry)
        hooks[event] = event_hooks

    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=4)
    print(f"    Merged hooks into settings.json")


def _guess_event(hook_filename: str, pack_name: str) -> str:
    """Map hook filename to Claude Code event.

    Uses hook_events from the plugin manifest if available,
    falls back to filename-based guessing.
    """
    pack = find_pack(pack_name)
    if pack:
        return resolve_hook_event(hook_filename, pack)
    # Fallback for unknown packs
    return resolve_hook_event(hook_filename, {})


# ---------------------------------------------------------------------------
# Remove
# ---------------------------------------------------------------------------

def remove_pack(name: str) -> bool:
    """Remove a plugin pack. Returns True if successful."""
    state = load_state()
    if name not in state["installed"]:
        print(f"  Plugin '{name}' is not installed")
        return False

    print(f"  Removing: {name}")

    # 1. Remove plugin hooks from ~/.ai-toolkit/hooks/
    removed = 0
    for hook in HOOKS_DIR.glob(f"plugin-{name}-*.sh"):
        hook.unlink()
        print(f"    Removed hook: {hook.name}")
        removed += 1

    # 2. Remove plugin scripts
    scripts_dir = Path.home() / ".ai-toolkit" / "plugin-scripts" / name
    if scripts_dir.is_dir():
        shutil.rmtree(scripts_dir)
        print(f"    Removed scripts: {scripts_dir}")
        removed += 1

    # 3. Strip plugin hooks from settings.json
    _strip_plugin_hooks(name)

    # 4. Update state
    state["installed"] = [p for p in state["installed"] if p != name]
    save_state(state)

    print(f"  Done: removed {name}")
    return True


def _strip_plugin_hooks(name: str) -> None:
    """Remove plugin hooks from settings.json."""
    settings_path = CLAUDE_DIR / "settings.json"
    if not settings_path.is_file():
        return

    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    source_tag = f"ai-toolkit-plugin-{name}"
    hooks = settings.get("hooks", {})
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
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=4)
        print(f"    Stripped hooks from settings.json")


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

def update_pack(name: str) -> bool:
    """Update a single plugin pack (remove + install). Returns True if successful."""
    state = load_state()
    if name not in state["installed"]:
        print(f"  Plugin '{name}' is not installed — use 'install' instead")
        return False

    print(f"  Updating: {name}")
    remove_pack(name)
    return install_pack(name)


# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

MEMORY_DB = Path.home() / ".ai-toolkit" / "memory.db"

# Map plugin names to their clean logic
CLEANABLE_PLUGINS = {"memory-pack"}


def clean_pack(name: str, days: int = 90) -> bool:
    """Prune old data for a plugin. Returns True if successful."""
    state = load_state()
    if name not in state["installed"]:
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

        # Count before
        before = cur.execute("SELECT COUNT(*) FROM observations").fetchone()[0]

        # Delete old observations
        cur.execute(
            "DELETE FROM observations WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        pruned_obs = cur.rowcount

        # Delete orphan sessions
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

def cmd_list() -> None:
    """List available plugin packs."""
    packs = list_available()
    state = load_state()

    print("Available plugin packs:")
    print()
    print(f"  {'Name':<20} {'Domain':<12} {'Status':<14} {'Agents':>7} {'Skills':>7} {'Hooks':>6}  Installed")
    print(f"  {'-'*20} {'-'*12} {'-'*14} {'-'*7} {'-'*7} {'-'*6}  {'-'*9}")

    for pack in packs:
        inc = pack.get("includes", {})
        installed = "YES" if pack["name"] in state["installed"] else ""
        print(
            f"  {pack['name']:<20} {pack.get('domain',''):<12} {pack.get('status',''):<14}"
            f" {len(inc.get('agents',[])):>7} {len(inc.get('skills',[])):>7} {len(inc.get('hooks',[])):>6}"
            f"  {installed}"
        )

    print()
    print(f"  Total: {len(packs)} packs, {len(state['installed'])} installed")
    print()
    print("  Install:    ai-toolkit plugin install <name>")
    print("  Install all: ai-toolkit plugin install --all")
    print("  Update:     ai-toolkit plugin update <name>")
    print("  Update all: ai-toolkit plugin update --all")
    print("  Clean:      ai-toolkit plugin clean <name> [--days N]")
    print("  Remove:     ai-toolkit plugin remove <name>")


def cmd_status() -> None:
    """Show installed plugins with details."""
    state = load_state()
    if not state["installed"]:
        print("No plugins installed.")
        print("Run: ai-toolkit plugin list")
        return

    print("Installed plugins:")
    for name in state["installed"]:
        pack = find_pack(name)
        if pack:
            print(f"  {name}: {pack.get('description', '')}")
            # Check hooks
            hooks = list(HOOKS_DIR.glob(f"plugin-{name}-*.sh"))
            if hooks:
                print(f"    Hooks: {', '.join(h.name for h in hooks)}")
            # Show memory-pack DB stats
            if name == "memory-pack":
                _show_memory_stats()
        else:
            print(f"  {name}: (manifest not found — orphaned?)")


def _show_memory_stats() -> None:
    """Show memory-pack database statistics."""
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _cmd_install(args: list[str]) -> None:
    if not args:
        print("Usage: ai-toolkit plugin install <pack-name> [...]")
        print("       ai-toolkit plugin install --all")
        sys.exit(1)
    if "--all" in args:
        packs = list_available()
        print(f"Installing all {len(packs)} plugin packs...\n")
        ok = 0
        for pack in packs:
            if install_pack(pack["name"]):
                ok += 1
            print()
        print(f"Installed: {ok}/{len(packs)} packs")
    else:
        for name in args:
            install_pack(name)
            print()


def _cmd_remove(args: list[str]) -> None:
    if not args:
        print("Usage: ai-toolkit plugin remove <pack-name> [...]")
        print("       ai-toolkit plugin remove --all")
        sys.exit(1)
    if "--all" in args:
        state = load_state()
        names = list(state["installed"])
        if not names:
            print("No plugins installed.")
            return
        for name in names:
            remove_pack(name)
            print()
    else:
        for name in args:
            remove_pack(name)
            print()


def _cmd_update(args: list[str]) -> None:
    if not args:
        print("Usage: ai-toolkit plugin update <pack-name> [...]")
        print("       ai-toolkit plugin update --all")
        sys.exit(1)
    if "--all" in args:
        state = load_state()
        names = list(state["installed"])
        if not names:
            print("No plugins installed.")
            return
        print(f"Updating {len(names)} installed plugin(s)...\n")
        ok = 0
        for name in names:
            if update_pack(name):
                ok += 1
            print()
        print(f"Updated: {ok}/{len(names)} packs")
    else:
        for name in args:
            update_pack(name)
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
                    print(f"  ERROR: --days must be positive, got {days}")
                    sys.exit(1)
            except ValueError:
                print(f"  ERROR: --days requires a number, got '{args[i + 1]}'")
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
    args = sys.argv[2:]

    dispatch = {
        "list": lambda: cmd_list(),
        "status": lambda: cmd_status(),
        "install": lambda: _cmd_install(args),
        "remove": lambda: _cmd_remove(args),
        "update": lambda: _cmd_update(args),
        "clean": lambda: _cmd_clean(args),
    }

    handler = dispatch.get(action)
    if handler:
        handler()
    else:
        print(f"Unknown action: {action}")
        print("Actions: install, remove, update, clean, list, status")
        sys.exit(1)


if __name__ == "__main__":
    main()
