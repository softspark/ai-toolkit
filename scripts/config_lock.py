#!/usr/bin/env python3
"""Lock file management for ai-toolkit config inheritance.

Generates and consumes .softspark-toolkit.lock.json for reproducible
extends resolution across team members and CI.

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import hashlib
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
            lock = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    return lock if isinstance(lock, dict) else None


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
        "ai_toolkit_version": ai_toolkit_version or _current_toolkit_version(),
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

    header_error = _check_lock_header(lock)
    if header_error:
        return header_error
    resolved = lock["resolved"]
    return _check_resolved_chain(config["extends"], resolved)


def get_locked_version(project_dir: Path, config_name: str) -> str | None:
    """Get the locked version for a specific config.

    Returns None if not locked.
    """
    lock = load_lock_file(project_dir)
    if lock is None:
        return None
    resolved = lock.get("resolved", {})
    if not isinstance(resolved, dict):
        return None
    entry = resolved.get(config_name, {})
    if not isinstance(entry, dict):
        return None
    version = entry.get("version")
    return version if isinstance(version, str) and version else None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check_lock_header(lock: dict[str, Any]) -> str:
    """Validate lock format and toolkit version."""
    if lock.get("lockfileVersion") != LOCK_VERSION:
        return f"stale: lock version {lock.get('lockfileVersion')} != {LOCK_VERSION}"
    locked_version = lock.get("ai_toolkit_version")
    current_version = _current_toolkit_version()
    if current_version and (
        not isinstance(locked_version, str)
        or not locked_version
    ):
        return "stale: ai-toolkit version metadata is missing or invalid"
    if current_version and locked_version != current_version:
        return (
            f"stale: ai-toolkit version '{locked_version}' "
            f"!= current '{current_version}'"
        )
    resolved = lock.get("resolved")
    if not isinstance(resolved, dict) or not resolved:
        return "stale: no resolved entries"
    if not all(isinstance(entry, dict) for entry in resolved.values()):
        return "stale: invalid resolved entries"
    return ""


def _check_resolved_chain(
    current_source: str,
    resolved: dict[str, dict[str, Any]],
) -> str:
    """Compare every locked config against its current cached snapshot."""
    if not isinstance(current_source, str) or not current_source:
        return "stale: invalid project extends source"
    for name, entry in reversed(list(resolved.items())):
        locked_source = entry.get("source", "")
        if current_source != locked_source:
            return (
                f"stale: extends source '{current_source}' "
                f"!= locked '{locked_source}'"
            )
        error, current_config = _check_resolved_entry(name, entry)
        if error:
            return error
        assert current_config is not None
        current_source = current_config.get("extends", "")
        if not isinstance(current_source, str):
            return f"stale: invalid extends source in resolved config {name}"
    if current_source:
        return f"stale: unresolved extends source '{current_source}'"
    return "ok"


def _check_resolved_entry(
    name: str,
    entry: dict[str, Any],
) -> tuple[str, dict[str, Any] | None]:
    """Compare version and integrity for one locked config."""
    cached = entry.get("cached")
    locked_source = entry.get("source")
    locked_version = entry.get("version")
    locked_integrity = entry.get("integrity")
    if (
        not isinstance(cached, str)
        or not cached
        or not isinstance(locked_source, str)
        or not locked_source
        or not isinstance(locked_version, str)
        or not isinstance(locked_integrity, str)
        or not locked_integrity.startswith("sha256:")
    ):
        return f"stale: invalid resolved config metadata for {name}", None
    config_path = Path(cached).expanduser() / "ai-toolkit.config.json"
    try:
        raw_config = config_path.read_bytes()
        current_config = json.loads(raw_config.decode("utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return f"stale: cannot read resolved config for {name}", None
    if not isinstance(current_config, dict):
        return f"stale: invalid resolved config content for {name}", None
    current_version = current_config.get("version", "")
    if current_version != locked_version:
        return (
            f"stale: {name} version '{current_version}' "
            f"!= locked '{locked_version}'"
        ), None
    current_integrity = f"sha256:{hashlib.sha256(raw_config).hexdigest()}"
    if current_integrity != locked_integrity:
        return (
            f"stale: {name} integrity '{current_integrity}' "
            f"!= locked '{locked_integrity}'"
        ), None
    return "", current_config


def _current_toolkit_version() -> str:
    """Read the version of the toolkit owning this lock implementation."""
    package_path = Path(__file__).resolve().parent.parent / "package.json"
    try:
        with open(package_path, encoding="utf-8") as handle:
            package = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return ""
    version = package.get("version", "")
    return version if isinstance(version, str) else ""


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
