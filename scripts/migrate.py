#!/usr/bin/env python3
"""Migrate ai-toolkit data from ~/.ai-toolkit to ~/.softspark/ai-toolkit.

Called automatically by install.py and ai-toolkit.js on first run.
Can also be invoked directly: python3 scripts/migrate.py [--dry-run]

Migration steps:
  1. Detect legacy ~/.ai-toolkit directory
  2. Create ~/.softspark/ai-toolkit/
  3. Move all contents (state, hooks, rules, sessions, etc.)
  4. Leave ~/.ai-toolkit/.migrated marker with pointer to new location
  5. Migrate per-project .ai-toolkit.json → .softspark-toolkit.json (via registry)

Exit codes:
  0  Migration succeeded or nothing to migrate
  1  Migration failed
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import (
    LEGACY_DATA_DIR,
    LEGACY_PROJECT_CONFIG,
    LEGACY_PROJECT_LOCK,
    PROJECT_CONFIG_FILENAME,
    PROJECT_LOCK_FILENAME,
    SOFTSPARK_DIR,
    TOOLKIT_DATA_DIR,
)


def needs_migration() -> bool:
    """Check if legacy directory exists and needs migration.

    Returns True only when ~/.ai-toolkit/ exists AND contains real data
    (not just an empty dir). After migration the directory is removed entirely.
    """
    if not LEGACY_DATA_DIR.is_dir():
        return False
    # Empty dir (or only hidden files) — nothing to migrate
    if not any(LEGACY_DATA_DIR.iterdir()):
        return False
    # Don't migrate if AI_TOOLKIT_HOME is set (custom setup)
    if os.environ.get("AI_TOOLKIT_HOME"):
        return False
    return True


def migrate_home_directory(dry_run: bool = False) -> bool:
    """Migrate ~/.ai-toolkit → ~/.softspark/ai-toolkit.

    Returns True if migration was performed, False if skipped.
    """
    if not needs_migration():
        return False

    print()
    print("## Migrating to new directory structure")
    print(f"   {LEGACY_DATA_DIR} → {TOOLKIT_DATA_DIR}")
    print()

    if dry_run:
        print("   (dry-run: no changes made)")
        return False

    # Create parent ~/.softspark/
    SOFTSPARK_DIR.mkdir(parents=True, exist_ok=True)

    if TOOLKIT_DATA_DIR.exists():
        # New dir already exists (partial migration?) — merge carefully
        _merge_directories(LEGACY_DATA_DIR, TOOLKIT_DATA_DIR)
    else:
        # Clean move
        shutil.move(str(LEGACY_DATA_DIR), str(TOOLKIT_DATA_DIR))

    # Remove legacy directory entirely
    if LEGACY_DATA_DIR.exists():
        shutil.rmtree(str(LEGACY_DATA_DIR), ignore_errors=True)

    print(f"   Migrated: {TOOLKIT_DATA_DIR}")
    return True


def _merge_directories(src: Path, dst: Path) -> None:
    """Merge src into dst, preferring src files (newer)."""
    for item in src.iterdir():
        if item.name == ".migrated":
            continue
        dest_item = dst / item.name
        if item.is_dir():
            if dest_item.is_dir():
                _merge_directories(item, dest_item)
            else:
                shutil.move(str(item), str(dest_item))
        else:
            # Overwrite with source (legacy has the latest data)
            shutil.move(str(item), str(dest_item))


def migrate_project_configs(dry_run: bool = False) -> int:
    """Rename .ai-toolkit.json → .softspark-toolkit.json in registered projects.

    Returns the number of projects migrated.
    """
    registry_file = TOOLKIT_DATA_DIR / "projects.json"
    if not registry_file.is_file():
        return 0

    try:
        with open(registry_file, encoding="utf-8") as f:
            data = json.load(f)
        projects = data.get("projects", [])
    except (json.JSONDecodeError, OSError):
        return 0

    count = 0
    for project in projects:
        project_path = Path(project.get("path", ""))
        if not project_path.is_dir():
            continue

        # Migrate .ai-toolkit.json → .softspark-toolkit.json
        old_config = project_path / LEGACY_PROJECT_CONFIG
        new_config = project_path / PROJECT_CONFIG_FILENAME
        if old_config.is_file() and not new_config.is_file():
            if dry_run:
                print(f"   Would rename: {old_config} → {new_config}")
            else:
                old_config.rename(new_config)
                print(f"   Renamed: {old_config.name} → {new_config.name} in {project_path}")
            count += 1

        # Migrate .ai-toolkit.lock.json → .softspark-toolkit.lock.json
        old_lock = project_path / LEGACY_PROJECT_LOCK
        new_lock = project_path / PROJECT_LOCK_FILENAME
        if old_lock.is_file() and not new_lock.is_file():
            if dry_run:
                print(f"   Would rename: {old_lock} → {new_lock}")
            else:
                old_lock.rename(new_lock)

    return count


def migrate_settings_json(dry_run: bool = False) -> int:
    """Rewrite hook commands in ~/.claude/settings.json from old to new path.

    Replaces ALL occurrences of .ai-toolkit/hooks/ with .softspark/ai-toolkit/hooks/
    in hook command strings, regardless of _source tag. This catches plugin hooks
    (memory-pack, enterprise-pack, etc.) that merge-hooks.py doesn't strip.

    Returns the number of commands rewritten.
    """
    settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.is_file():
        return 0

    try:
        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return 0

    hooks = data.get("hooks", {})
    old_prefix = ".ai-toolkit/hooks/"
    new_prefix = ".softspark/ai-toolkit/hooks/"
    count = 0

    for entries in hooks.values():
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                if old_prefix in cmd and new_prefix not in cmd:
                    hook["command"] = cmd.replace(old_prefix, new_prefix)
                    count += 1

    if count > 0 and not dry_run:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.write("\n")
        print(f"   Rewritten: {count} hook path(s) in settings.json")

    return count


def run_full_migration(dry_run: bool = False) -> bool:
    """Run complete migration: home directory + project configs + settings.json.

    Returns True if any migration was performed.
    """
    migrated = migrate_home_directory(dry_run=dry_run)

    if migrated and not dry_run:
        count = migrate_project_configs(dry_run=dry_run)
        if count > 0:
            print(f"   Migrated {count} project config(s)")
        migrate_settings_json(dry_run=dry_run)

    return migrated


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    if not needs_migration():
        print("Nothing to migrate (no legacy ~/.ai-toolkit found or already migrated).")
        sys.exit(0)

    success = run_full_migration(dry_run=dry_run)

    if success:
        print()
        print("Migration complete. ~/.ai-toolkit/ has been removed.")
    elif not dry_run:
        print("Migration skipped.")


if __name__ == "__main__":
    main()
