#!/usr/bin/env python3
"""URL source registry for remotely-sourced rules.

Tracks which rules were registered from a URL so that `ai-toolkit update`
can re-fetch the latest version before injection.

Metadata stored in ~/.softspark/ai-toolkit/rules/sources.json.

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import RULES_DIR
from url_fetch import fetch_url as fetch_url  # noqa: F811 — re-export

_SOURCES_FILENAME = "sources.json"


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

def register_url_source(
    rules_dir: Path | None,
    rule_name: str,
    url: str,
    content: bytes | None = None,
) -> None:
    """Add or update a URL source entry.

    When ``content`` is supplied, its sha256 is persisted. If a previous
    sha256 exists and differs from the new one, a warning is printed
    (and the process fails with exit 2 when ``AI_TOOLKIT_STRICT_PIN=1``).
    """
    import re
    if not rule_name or not re.fullmatch(r"[a-zA-Z0-9_-]+", rule_name):
        raise ValueError(f"Invalid rule name: {rule_name!r}")
    rules_dir = rules_dir or RULES_DIR
    sources = load_sources(rules_dir)
    entry: dict[str, Any] = {
        "url": url,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if content is not None:
        new_hash = hashlib.sha256(content).hexdigest()
        prev = sources.get(rule_name) or {}
        prev_hash = prev.get("sha256")
        if prev_hash and prev_hash != new_hash:
            msg = (
                f"  CHECKSUM CHANGED: rule '{rule_name}' sha256 "
                f"{prev_hash[:12]}... -> {new_hash[:12]}..."
            )
            print(msg)
            if os.environ.get("AI_TOOLKIT_STRICT_PIN") == "1":
                raise SystemExit(
                    f"Refusing to update '{rule_name}' under AI_TOOLKIT_STRICT_PIN=1."
                )
        entry["sha256"] = new_hash
    sources[rule_name] = entry
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
# Fetch — delegated to shared url_fetch module (re-exported above)
# ---------------------------------------------------------------------------
