# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Centralized path constants for ai-toolkit.

All scripts MUST import paths from here — never hardcode ~/.ai-toolkit or
~/.softspark/ai-toolkit directly.

Supports override via AI_TOOLKIT_HOME env var for testing and custom setups.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Canonical paths
# ---------------------------------------------------------------------------

SOFTSPARK_DIR = Path(os.environ.get("SOFTSPARK_HOME", Path.home() / ".softspark"))

TOOLKIT_DATA_DIR = Path(
    os.environ.get("AI_TOOLKIT_HOME", SOFTSPARK_DIR / "ai-toolkit")
)

# Legacy path (pre-v2.0) — used only by migration detection
LEGACY_DATA_DIR = Path.home() / ".ai-toolkit"

# Sub-directories under TOOLKIT_DATA_DIR
HOOKS_DIR = TOOLKIT_DATA_DIR / "hooks"
EXTERNAL_HOOKS_DIR = HOOKS_DIR / "external"
MCP_TEMPLATES_DIR = TOOLKIT_DATA_DIR / "mcp-templates"
EXTERNAL_MCP_DIR = MCP_TEMPLATES_DIR / "external"
RULES_DIR = TOOLKIT_DATA_DIR / "rules"
SESSIONS_DIR = TOOLKIT_DATA_DIR / "sessions"
COMPACTIONS_DIR = TOOLKIT_DATA_DIR / "compactions"
CONFIG_CACHE_DIR = TOOLKIT_DATA_DIR / "config-cache"
COMPILED_DIR = TOOLKIT_DATA_DIR / "compiled"

# Files under TOOLKIT_DATA_DIR
STATE_FILE = TOOLKIT_DATA_DIR / "state.json"
PROJECTS_FILE = TOOLKIT_DATA_DIR / "projects.json"
STATS_FILE = TOOLKIT_DATA_DIR / "stats.json"
GOVERNANCE_LOG = TOOLKIT_DATA_DIR / "governance.log"
VERSION_CHECK_FILE = TOOLKIT_DATA_DIR / "version-check.json"

# Per-project config filenames
PROJECT_CONFIG_FILENAME = ".softspark-toolkit.json"
PROJECT_LOCK_FILENAME = ".softspark-toolkit.lock.json"

# Legacy per-project config filenames (for migration)
LEGACY_PROJECT_CONFIG = ".ai-toolkit.json"
LEGACY_PROJECT_LOCK = ".ai-toolkit.lock.json"

# Base config filename (published in npm packages — unchanged)
BASE_CONFIG_FILENAME = "ai-toolkit.config.json"


def user_path(raw: "str | os.PathLike[str]") -> Path:
    """Resolve a user-supplied path against the directory the user ran the CLI in.

    ``bin/ai-toolkit.js`` runs some commands (``claude-app``, ``codex-plugin``,
    ``antigravity-plugin``) with ``cwd`` inside the installed package so their
    relative asset paths resolve, and passes the shell's own directory as
    ``AI_TOOLKIT_USER_CWD``. Before v4.32.2 a relative ``--output`` (including
    every default) was written next to ``node_modules/@softspark/ai-toolkit``.
    Absolute paths pass through; direct ``python3 scripts/...`` runs, where the
    variable is unset, resolve against the real cwd as before.
    """
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    base = os.environ.get("AI_TOOLKIT_USER_CWD", "").strip()
    return (Path(base) if base else Path.cwd()) / path
