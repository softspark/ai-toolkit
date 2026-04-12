#!/usr/bin/env python3
"""Lock file management for ai-toolkit config inheritance.

Generates and consumes .softspark-toolkit.lock.json for reproducible
extends resolution across team members and CI.

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOCK_FILENAME = ".softspark-toolkit.lock.json"
LOCK_VERSION = 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

LEGACY_LOCK_FILENAME = ".ai-toolkit.lock.json"


def load_lock_file(project_dir: Path) -> dict[str, Any] | None:
    """Load lock file from project directory.

    Falls back to legacy .ai-toolkit.lock.json if the new file doesn't exist.
    Returns None if neither file exists.
    """
    lock_path = project_dir / LOCK_FILENAME
    if not lock_path.is_file():
        legacy_path = project_dir / LEGACY_LOCK_FILENAME
        if legacy_path.is_file():
            lock_path = legacy_path
        else:
            return None
    try:
        with open(lock_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_lock_file(
    project_dir: Path,
    resolved_configs: list[dict[str, Any]],
    ai_toolkit_version: str = "",
) -> Path:
    """Save lock file after successful extends resolution.

    Args:
        project_dir: Project root directory.
        resolved_configs: List of resolved config metadata dicts
            (each with source, name, version, integrity, root).
        ai_toolkit_version: Current ai-toolkit version.

    Returns:
        Path to the created lock file.
    """
    lock_data: dict[str, Any] = {
        "lockfileVersion": LOCK_VERSION,
        "resolved": {},
        "generated_at": _now_iso(),
        "ai_toolkit_version": ai_toolkit_version,
    }

    for config in resolved_configs:
        name = config.get("name", config.get("source", "unknown"))
        lock_data["resolved"][name] = {
            "version": config.get("version", ""),
            "source": config.get("source", ""),
            "integrity": config.get("integrity", ""),
            "cached": config.get("root", ""),
        }

    lock_path = project_dir / LOCK_FILENAME
    with open(lock_path, "w", encoding="utf-8") as f:
        json.dump(lock_data, f, indent=2)
        f.write("\n")

    return lock_path


def check_lock_staleness(project_dir: Path) -> str:
    """Check if lock file exists and is up-to-date.

    Returns:
        - "ok" if lock file exists and is current
        - "missing" if no lock file
        - "stale: <reason>" if lock file is outdated
        - "" if no extends in config (lock not applicable)
    """
    from config_resolver import load_project_config

    config = load_project_config(project_dir)
    if config is None or not config.get("extends"):
        return ""  # No extends, lock file not applicable

    lock = load_lock_file(project_dir)
    if lock is None:
        return "missing"

    # Check lock version
    if lock.get("lockfileVersion") != LOCK_VERSION:
        return f"stale: lock version {lock.get('lockfileVersion')} != {LOCK_VERSION}"

    # Check if resolved entries exist
    resolved = lock.get("resolved", {})
    if not resolved:
        return "stale: no resolved entries"

    return "ok"


def get_locked_version(project_dir: Path, config_name: str) -> str | None:
    """Get the locked version for a specific config.

    Returns None if not locked.
    """
    lock = load_lock_file(project_dir)
    if lock is None:
        return None
    resolved = lock.get("resolved", {})
    entry = resolved.get(config_name, {})
    return entry.get("version") or None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# CLI entry point (for testing)
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI: inspect lock file."""
    if len(sys.argv) < 2:
        print("Usage: config_lock.py <project-dir>", file=sys.stderr)
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    lock = load_lock_file(project_dir)

    if lock is None:
        print(json.dumps({"status": "no lock file"}))
    else:
        print(json.dumps(lock, indent=2))


if __name__ == "__main__":
    main()
