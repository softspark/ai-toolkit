#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate CONVENTIONS.md for Aider.

Aider automatically loads CONVENTIONS.md from the project root as
read-only context. This file contains coding standards, guidelines,
and the agent/skill catalog — same content other platforms get.

Output is plain markdown suitable for marker injection into an
existing CONVENTIONS.md (preserves user content outside markers).

Usage:
  python3 scripts/generate_conventions.py > CONVENTIONS.md
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generator_base import render_generator
from injection import strip_owned_sections
from secure_fs import apply_owned_edits, lexical_absolute

LOCAL_FILE = "CONVENTIONS.md"
# Global install writes a toolkit-named file into HOME (ai_tools._install_aider_global).
GLOBAL_FILE = ".aider-ai-toolkit-CONVENTIONS.md"


def _conventions_path(target_dir: Path, global_install: bool) -> tuple[Path, Path]:
    target = lexical_absolute(target_dir)
    return target, target / (GLOBAL_FILE if global_install else LOCAL_FILE)


def cleanup(target_dir: Path, *, global_install: bool = False) -> int:
    """Strip TOOLKIT sections from the Aider conventions file.

    Local: ``target_dir/CONVENTIONS.md``; global: ``~/.aider-ai-toolkit-CONVENTIONS.md``.
    The file is deleted only when nothing but toolkit sections remained.
    Returns 1 when the file was rewritten or removed, else 0.
    """
    target, path = _conventions_path(target_dir, global_install)
    edits = {path: strip_owned_sections} if path.is_file() else {}
    return apply_owned_edits(edits, target, label="Aider conventions")


def discover(target_dir: Path, *, global_install: bool = False) -> int:
    """Return 1 when :func:`cleanup` would change the file, without side effects."""
    target, path = _conventions_path(target_dir, global_install)
    edits = {path: strip_owned_sections} if path.is_file() else {}
    return apply_owned_edits(edits, target, label="Aider conventions", dry_run=True)


if __name__ == "__main__":
    render_generator({
        "title": "# AI Toolkit — Coding Conventions",
        "intro_template": (
            "Shared AI development toolkit with specialized agents,"
            " skills, quality hooks, and a safety constitution."
            " Aider loads this file automatically as read-only context."
        ),
        "agents_section": "## Available Agents",
        "agents_intro": "Specialized agent personas — apply their expertise for relevant tasks:",
        "agents_format": "bullets",
        "skills_section": "## Available Skills",
        "skills_intro": "Skills are invocable slash commands or auto-loaded knowledge sources:",
        "skills_format": "bullets",
        "guidelines": ["general", "quality_standards", "workflow"],
    })
