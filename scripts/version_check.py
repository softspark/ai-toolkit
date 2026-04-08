#!/usr/bin/env python3
"""Check if a newer version of ai-toolkit is available on npm.

Caches the result for 24 hours to avoid hitting npm on every session.

Usage:
  version_check.py              # Print update notice if available (for hooks)
  version_check.py --status     # Print detailed version info (for ai-toolkit status)
  version_check.py --force      # Force re-check (ignore cache)

Exit codes:
  0  Up to date (or check skipped/failed)
  1  Update available
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

CACHE_FILE = Path.home() / ".ai-toolkit" / "version-check.json"
CACHE_TTL = 86400  # 24 hours
PACKAGE_NAME = "@softspark/ai-toolkit"


def _get_installed_version() -> str:
    """Read version from state.json (what user actually has configured).

    Falls back to package.json if state.json is missing (e.g. fresh install).
    state.json is the source of truth because it reflects what was last
    installed/updated, while package.json may be newer if the npm package
    was upgraded but `ai-toolkit update` was not run yet.
    """
    state_file = Path.home() / ".ai-toolkit" / "state.json"
    if state_file.is_file():
        try:
            with open(state_file, encoding="utf-8") as f:
                version = json.load(f).get("installed_version")
                if version:
                    return version
        except (json.JSONDecodeError, OSError):
            pass
    # Fallback: package.json
    pkg = Path(__file__).resolve().parent.parent / "package.json"
    if pkg.is_file():
        with open(pkg, encoding="utf-8") as f:
            return json.load(f).get("version", "unknown")
    return "unknown"


def _get_cached() -> dict | None:
    """Read cached version check result."""
    if not CACHE_FILE.is_file():
        return None
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        checked_at = data.get("checked_at", 0)
        if time.time() - checked_at > CACHE_TTL:
            return None  # expired
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _save_cache(installed: str, latest: str) -> None:
    """Save version check result to cache."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "installed": installed,
        "latest": latest,
        "checked_at": time.time(),
    }
    tmp = str(CACHE_FILE) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, str(CACHE_FILE))


def _fetch_latest_version() -> str | None:
    """Fetch latest version from npm registry (2s timeout)."""
    try:
        result = subprocess.run(
            ["npm", "view", PACKAGE_NAME, "version"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _parse_semver(version: str) -> tuple[int, ...]:
    """Parse version string to comparable tuple."""
    try:
        return tuple(int(x) for x in version.split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _is_newer(latest: str, installed: str) -> bool:
    """Check if latest is newer than installed."""
    return _parse_semver(latest) > _parse_semver(installed)


def check(force: bool = False) -> dict:
    """Check for updates. Returns {installed, latest, update_available}."""
    installed = _get_installed_version()

    if not force:
        cached = _get_cached()
        if cached:
            return {
                "installed": installed,
                "latest": cached.get("latest", installed),
                "update_available": _is_newer(cached.get("latest", ""), installed),
                "cached": True,
            }

    latest = _fetch_latest_version()
    if latest:
        _save_cache(installed, latest)
        return {
            "installed": installed,
            "latest": latest,
            "update_available": _is_newer(latest, installed),
            "cached": False,
        }

    return {
        "installed": installed,
        "latest": "unknown",
        "update_available": False,
        "cached": False,
    }


def main() -> None:
    force = "--force" in sys.argv
    status_mode = "--status" in sys.argv

    result = check(force=force)

    if status_mode:
        print(f"  Installed:  {result['installed']}")
        print(f"  Latest:     {result['latest']}")
        if result["update_available"]:
            print(f"  Update:     {result['installed']} -> {result['latest']}")
            print(f"  Run:        npm install -g {PACKAGE_NAME}@latest && ai-toolkit update")
        else:
            print("  Update:     up to date")
        sys.exit(1 if result["update_available"] else 0)

    # Hook mode: only print if update available
    if result["update_available"]:
        print(
            f"ai-toolkit update available: {result['installed']} -> {result['latest']} "
            f"(npm install -g {PACKAGE_NAME}@latest)"
        )
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
