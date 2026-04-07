"""Track installed modules and versions in ~/.ai-toolkit/state.json."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILENAME = "state.json"


def _state_path() -> Path:
    """Return the canonical path to state.json."""
    return Path.home() / ".ai-toolkit" / STATE_FILENAME


def load_state() -> dict:
    """Load state from ~/.ai-toolkit/state.json.

    Returns an empty dict if the file does not exist or is malformed.
    """
    path = _state_path()
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict) -> None:
    """Save state to ~/.ai-toolkit/state.json.

    Creates the parent directory if it does not exist.
    """
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def get_installed_modules() -> list[str]:
    """Return list of installed module names from state, or empty list."""
    state = load_state()
    modules = state.get("installed_modules", [])
    if isinstance(modules, list):
        return modules
    return []


def get_installed_profile() -> str:
    """Return the profile name from state, or empty string."""
    state = load_state()
    return state.get("profile", "")


def _now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_install(
    version: str,
    modules: list[str],
    profile: str,
    auto_detected: list[str] | None = None,
) -> None:
    """Record a successful install in state.json.

    If state already exists, preserves ``installed_at`` and updates
    ``last_updated``. Otherwise sets both timestamps.
    """
    state = load_state()
    now = _now_iso()

    state["installed_version"] = version
    if "installed_at" not in state:
        state["installed_at"] = now
    state["last_updated"] = now
    state["installed_modules"] = sorted(set(modules))
    state["profile"] = profile
    if auto_detected is not None:
        state["auto_detected_languages"] = sorted(auto_detected)

    save_state(state)

    # Clear version check cache (version may have changed)
    cache_file = _state_path().parent / "version-check.json"
    if cache_file.is_file():
        cache_file.unlink()


def print_status() -> None:
    """Print a human-readable summary of the install state."""
    state = load_state()
    if not state:
        print("No install state found (~/.ai-toolkit/state.json missing).")
        print("Run 'ai-toolkit install' to set up the toolkit.")
        return

    print("AI Toolkit Install Status")
    print("=========================")
    print(f"  Version:    {state.get('installed_version', 'unknown')}")
    print(f"  Installed:  {state.get('installed_at', 'unknown')}")
    print(f"  Updated:    {state.get('last_updated', 'unknown')}")
    print(f"  Profile:    {state.get('profile', 'unknown')}")

    modules = state.get("installed_modules", [])
    if modules:
        print(f"  Modules:    {', '.join(modules)}")
    else:
        print("  Modules:    (none recorded)")

    detected = state.get("auto_detected_languages", [])
    if detected:
        # Strip "rules-" prefix for readability
        langs = [m.replace("rules-", "") for m in detected]
        print(f"  Detected:   {', '.join(langs)}")

    # Check for updates
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from version_check import check
        result = check()
        if result["update_available"]:
            print()
            print(f"  Update available: {result['installed']} -> {result['latest']}")
            print(f"  Run: npm install -g @softspark/ai-toolkit@latest && ai-toolkit update")
        else:
            print(f"  Latest:     {result['latest']} (up to date)")
    except Exception:
        pass  # version check is optional
