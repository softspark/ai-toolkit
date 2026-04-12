"""Project registry — tracks which directories have ai-toolkit installed locally.

Stores registry in ~/.softspark/ai-toolkit/projects.json.
Used by `ai-toolkit update` to propagate updates to all registered projects,
and by `ai-toolkit projects` to list/manage them.

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import PROJECTS_FILE


def _registry_path() -> Path:
    """Return the canonical path to projects.json."""
    return PROJECTS_FILE


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------

def load_registry() -> list[dict[str, Any]]:
    """Load project registry. Returns empty list if missing/corrupt."""
    path = _registry_path()
    if not path.is_file():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            projects = data.get("projects", [])
            return projects if isinstance(projects, list) else []
        return []
    except (json.JSONDecodeError, OSError):
        return []


def save_registry(projects: list[dict[str, Any]]) -> None:
    """Save project registry."""
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"projects": projects}, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def register_project(
    project_path: str | Path,
    profile: str = "",
    extends: str = "",
) -> bool:
    """Register a project directory. Returns True if newly added, False if updated.

    Idempotent — updates existing entry if path already registered.
    """
    project_path = str(Path(project_path).resolve())
    projects = load_registry()
    now = _now_iso()

    for p in projects:
        if p.get("path") == project_path:
            # Update existing
            p["last_updated"] = now
            if profile:
                p["profile"] = profile
            if extends:
                p["extends"] = extends
            elif "extends" in p and not extends:
                # Clear extends if project no longer uses it
                pass
            save_registry(projects)
            return False

    # New registration
    projects.append({
        "path": project_path,
        "registered_at": now,
        "last_updated": now,
        "profile": profile or "standard",
        "extends": extends or "",
    })
    save_registry(projects)
    return True


def unregister_project(project_path: str | Path) -> bool:
    """Unregister a project. Returns True if found and removed."""
    project_path = str(Path(project_path).resolve())
    projects = load_registry()
    original_len = len(projects)
    projects = [p for p in projects if p.get("path") != project_path]
    if len(projects) < original_len:
        save_registry(projects)
        return True
    return False


def list_projects() -> list[dict[str, Any]]:
    """List all registered projects with existence status."""
    projects = load_registry()
    for p in projects:
        p["exists"] = Path(p["path"]).is_dir()
    return projects


def prune_stale() -> list[str]:
    """Remove projects whose directories no longer exist. Returns pruned paths."""
    projects = load_registry()
    pruned: list[str] = []
    kept: list[dict[str, Any]] = []

    for p in projects:
        if Path(p["path"]).is_dir():
            kept.append(p)
        else:
            pruned.append(p["path"])

    if pruned:
        save_registry(kept)

    return pruned


def get_active_projects() -> list[dict[str, Any]]:
    """Get registered projects that still exist on disk."""
    return [p for p in load_registry() if Path(p["path"]).is_dir()]
