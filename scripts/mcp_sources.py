#!/usr/bin/env python3
"""URL source registry for externally-injected MCP templates.

Tracks which MCP templates were registered from a URL or local file so that
`ai-toolkit update` can re-fetch the latest version and re-inject. Mirrors
the design of hook_sources.py for parity between inject-hook and inject-mcp.

Metadata stored in ~/.softspark/ai-toolkit/mcp-templates/external/sources.json.

Stdlib-only -- no external dependencies.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import EXTERNAL_MCP_DIR

_SOURCES_FILENAME = "sources.json"


def _sources_path(mcp_dir: Path | None = None) -> Path:
    return (mcp_dir or EXTERNAL_MCP_DIR) / _SOURCES_FILENAME


def load_sources(mcp_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load sources.json. Returns {} if missing or corrupt."""
    path = _sources_path(mcp_dir)
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data.get("templates", {})
        return {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_sources(mcp_dir: Path | None = None,
                 sources: dict[str, dict[str, Any]] | None = None) -> None:
    """Write sources.json atomically."""
    mcp_dir = mcp_dir or EXTERNAL_MCP_DIR
    path = _sources_path(mcp_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(
        {"schema_version": 1, "templates": sources or {}}, indent=2
    )

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


def register_url_source(
    mcp_dir: Path | None,
    template_name: str,
    url: str,
    content: bytes | None = None,
) -> None:
    """Add or update a URL source entry for an MCP template.

    When ``content`` is supplied, its sha256 is persisted. If a previous
    sha256 exists and differs from the new one, a warning is printed
    (and the process fails with exit 2 when ``AI_TOOLKIT_STRICT_PIN=1``).
    """
    if not template_name or not re.fullmatch(r"[a-zA-Z0-9_-]+", template_name):
        raise ValueError(f"Invalid MCP template name: {template_name!r}")
    mcp_dir = mcp_dir or EXTERNAL_MCP_DIR
    sources = load_sources(mcp_dir)
    entry: dict[str, Any] = {
        "url": url,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if content is not None:
        new_hash = hashlib.sha256(content).hexdigest()
        prev = sources.get(template_name) or {}
        prev_hash = prev.get("sha256")
        if prev_hash and prev_hash != new_hash:
            msg = (
                f"  CHECKSUM CHANGED: mcp '{template_name}' sha256 "
                f"{prev_hash[:12]}... -> {new_hash[:12]}..."
            )
            print(msg)
            if os.environ.get("AI_TOOLKIT_STRICT_PIN") == "1":
                raise SystemExit(
                    f"Refusing to update '{template_name}' under AI_TOOLKIT_STRICT_PIN=1."
                )
        entry["sha256"] = new_hash
    sources[template_name] = entry
    save_sources(mcp_dir, sources)


def register_path_source(
    mcp_dir: Path | None,
    template_name: str,
    path: Path,
    content: bytes | None = None,
) -> None:
    """Add or update a local-file source entry for an MCP template.

    Stores the absolute origin path so subsequent ``ai-toolkit update`` runs
    can detect drift, plus a sha256 of the injected content.
    """
    if not template_name or not re.fullmatch(r"[a-zA-Z0-9_-]+", template_name):
        raise ValueError(f"Invalid MCP template name: {template_name!r}")
    mcp_dir = mcp_dir or EXTERNAL_MCP_DIR
    sources = load_sources(mcp_dir)
    existing = sources.get(template_name) or {}
    # Never demote a URL-tracked entry to a local-path entry. update() flows
    # call inject() with the cached file path after URL fetch, which would
    # otherwise overwrite the URL.
    if "url" in existing:
        return
    entry: dict[str, Any] = {
        "path": str(Path(path).resolve()),
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if content is not None:
        entry["sha256"] = hashlib.sha256(content).hexdigest()
    sources[template_name] = entry
    save_sources(mcp_dir, sources)


def unregister_source(mcp_dir: Path | None, template_name: str) -> bool:
    """Remove a source entry. Returns True if found and removed."""
    mcp_dir = mcp_dir or EXTERNAL_MCP_DIR
    sources = load_sources(mcp_dir)
    if template_name in sources:
        del sources[template_name]
        save_sources(mcp_dir, sources)
        return True
    return False


def get_url_templates(mcp_dir: Path | None = None) -> dict[str, str]:
    """Return {template_name: url} for all URL-sourced MCP templates."""
    sources = load_sources(mcp_dir)
    return {name: entry["url"] for name, entry in sources.items() if "url" in entry}
