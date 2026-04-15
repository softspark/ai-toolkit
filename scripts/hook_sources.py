#!/usr/bin/env python3
"""URL source registry for remotely-sourced hooks.

Tracks which hooks were registered from a URL so that `ai-toolkit update`
can re-fetch the latest version before injection.

Metadata stored in ~/.softspark/ai-toolkit/hooks/external/sources.json.

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import EXTERNAL_HOOKS_DIR

_SOURCES_FILENAME = "sources.json"


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------

def _sources_path(hooks_dir: Path | None = None) -> Path:
    return (hooks_dir or EXTERNAL_HOOKS_DIR) / _SOURCES_FILENAME


def load_sources(hooks_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load sources.json. Returns {} if missing or corrupt."""
    path = _sources_path(hooks_dir)
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data.get("hooks", {})
        return {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_sources(hooks_dir: Path | None = None,
                 sources: dict[str, dict[str, Any]] | None = None) -> None:
    """Write sources.json atomically."""
    hooks_dir = hooks_dir or EXTERNAL_HOOKS_DIR
    path = _sources_path(hooks_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps({"schema_version": 1, "hooks": sources or {}}, indent=2)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), prefix=".sources_", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp_path, str(path))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def register_url_source(hooks_dir: Path | None, hook_name: str, url: str) -> None:
    """Add or update a URL source entry."""
    hooks_dir = hooks_dir or EXTERNAL_HOOKS_DIR
    sources = load_sources(hooks_dir)
    sources[hook_name] = {
        "url": url,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    save_sources(hooks_dir, sources)


def unregister_source(hooks_dir: Path | None, hook_name: str) -> bool:
    """Remove a source entry. Returns True if found and removed."""
    hooks_dir = hooks_dir or EXTERNAL_HOOKS_DIR
    sources = load_sources(hooks_dir)
    if hook_name in sources:
        del sources[hook_name]
        save_sources(hooks_dir, sources)
        return True
    return False


def get_url_hooks(hooks_dir: Path | None = None) -> dict[str, str]:
    """Return {hook_name: url} for all URL-sourced hooks."""
    sources = load_sources(hooks_dir)
    return {name: entry["url"] for name, entry in sources.items() if "url" in entry}
