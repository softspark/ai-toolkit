"""Project registry — tracks which directories have ai-toolkit installed locally.

Stores registry in ~/.softspark/ai-toolkit/projects.json.
Used by `ai-toolkit update` to propagate updates to all registered projects,
and by `ai-toolkit projects` to list/manage them.

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import PROJECTS_FILE

# Max retries when reading a partially-written file
_LOAD_RETRIES = 3
_LOAD_RETRY_DELAY = 0.05  # 50ms


@contextlib.contextmanager
def _registry_lock() -> Generator[None, None, None]:
    """Exclusive file lock for read-modify-write on projects.json.

    Prevents concurrent processes from interleaving loads and saves,
    which can silently drop entries.
    """
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _registry_path() -> Path:
    """Return the canonical path to projects.json."""
    return PROJECTS_FILE


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------

def load_registry() -> list[dict[str, Any]]:
    """Load project registry with retry for partially-written files.

    Retries on JSONDecodeError (another process mid-write).
    Returns empty list only if the file genuinely doesn't exist.
    """
    path = _registry_path()
    if not path.is_file():
        return []

    last_err: Exception | None = None
    for attempt in range(_LOAD_RETRIES):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                projects = data.get("projects", [])
                return projects if isinstance(projects, list) else []
            return []
        except json.JSONDecodeError as exc:
            last_err = exc
            if attempt < _LOAD_RETRIES - 1:
                time.sleep(_LOAD_RETRY_DELAY)
        except OSError:
            return []

    # All retries exhausted — file is genuinely corrupt, not mid-write
    import sys as _sys
    print(
        f"Warning: {path} is corrupt after {_LOAD_RETRIES} retries: {last_err}",
        file=_sys.stderr,
    )
    return []


def save_registry(projects: list[dict[str, Any]]) -> None:
    """Save project registry atomically (write-to-temp + rename).

    Uses os.rename which is atomic on POSIX, preventing other processes
    from reading a partially-written file.
    """
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), prefix=".projects_", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"projects": projects}, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp_path, str(path))
    except BaseException:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


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
    Uses file lock to prevent concurrent read-modify-write races.
    """
    project_path = str(Path(project_path).resolve())

    with _registry_lock():
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

    with _registry_lock():
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
    with _registry_lock():
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
