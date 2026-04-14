#!/usr/bin/env python3
"""URL source registry for remotely-sourced rules.

Tracks which rules were registered from a URL so that `ai-toolkit update`
can re-fetch the latest version before injection.

Metadata stored in ~/.softspark/ai-toolkit/rules/sources.json.

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import tempfile
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import RULES_DIR

_SOURCES_FILENAME = "sources.json"
_FETCH_TIMEOUT = 30  # seconds
_FETCH_MAX_BYTES = 10 * 1024 * 1024  # 10MB


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------

def _sources_path(rules_dir: Path | None = None) -> Path:
    return (rules_dir or RULES_DIR) / _SOURCES_FILENAME


def load_sources(rules_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load sources.json. Returns {} if missing or corrupt."""
    path = _sources_path(rules_dir)
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data.get("rules", {})
        return {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_sources(rules_dir: Path | None = None,
                 sources: dict[str, dict[str, Any]] | None = None) -> None:
    """Write sources.json atomically."""
    rules_dir = rules_dir or RULES_DIR
    path = _sources_path(rules_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps({"schema_version": 1, "rules": sources or {}}, indent=2)

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

def register_url_source(rules_dir: Path | None, rule_name: str, url: str) -> None:
    """Add or update a URL source entry."""
    rules_dir = rules_dir or RULES_DIR
    sources = load_sources(rules_dir)
    sources[rule_name] = {
        "url": url,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    save_sources(rules_dir, sources)


def unregister_source(rules_dir: Path | None, rule_name: str) -> bool:
    """Remove a source entry. Returns True if found and removed."""
    rules_dir = rules_dir or RULES_DIR
    sources = load_sources(rules_dir)
    if rule_name in sources:
        del sources[rule_name]
        save_sources(rules_dir, sources)
        return True
    return False


def get_url_rules(rules_dir: Path | None = None) -> dict[str, str]:
    """Return {rule_name: url} for all URL-sourced rules."""
    sources = load_sources(rules_dir)
    return {name: entry["url"] for name, entry in sources.items() if "url" in entry}


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_url(url: str) -> bytes:
    """Fetch URL content. HTTPS only, 30s timeout, 10MB cap.

    Raises:
        ValueError: if URL is not HTTPS
        urllib.error.URLError: on network failure
    """
    if not url.startswith("https://"):
        raise ValueError(
            f"Only HTTPS URLs are supported (got: {url.split('://')[0]}://)"
        )

    ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, timeout=_FETCH_TIMEOUT, context=ctx) as resp:
        data = resp.read(_FETCH_MAX_BYTES)

    # Basic binary detection — reject if null bytes present
    if b"\x00" in data:
        raise ValueError(f"URL returned binary content, expected markdown: {url}")

    return data
