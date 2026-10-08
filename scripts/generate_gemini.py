#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate GEMINI.md from app/agents/*.md and app/skills/*/SKILL.md.

Usage: ./scripts/generate_gemini.py > GEMINI.md
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generator_base import render_generator
from injection import strip_owned_sections
from secure_fs import apply_owned_edits, lexical_absolute


def _apply(target_dir: Path, global_install: bool, *, dry_run: bool) -> int:
    """Strip ai-toolkit sections from GEMINI.md through the secure edit path.

    Global installs inject ``~/.gemini/GEMINI.md``; local installs inject
    ``<project>/GEMINI.md``. A symlinked GEMINI.md is skipped and a symlinked
    ``.gemini`` directory is refused.
    """
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Gemini target directory: {target}")
    parent = target / ".gemini" if global_install else target
    path = parent / "GEMINI.md"
    return apply_owned_edits(
        {path: strip_owned_sections} if path.is_file() else {},
        target,
        label="Gemini GEMINI.md",
        prune=(parent,) if global_install else (),
        dry_run=dry_run,
    )


def discover(target_dir: Path, *, global_install: bool = False) -> int:
    """Return 1 when GEMINI.md holds ai-toolkit marker sections, else 0."""
    return _apply(target_dir, global_install, dry_run=True)


def cleanup(target_dir: Path, *, global_install: bool = False) -> int:
    """Strip ai-toolkit sections from GEMINI.md; delete it only when empty."""
    return _apply(target_dir, global_install, dry_run=False)


if __name__ == "__main__":
    # GEMINI.md is also Antigravity's always-on global rule, truncated above
    # 24,000 bytes, so the agent and skill catalogues are not inlined: both
    # clients discover them from their native directories.
    render_generator({
        "title": "# AI Toolkit — Gemini CLI Configuration",
        "intro_template": (
            "Shared AI development toolkit with {agents} specialized agents,"
            " {skills} skills, quality hooks, and a safety constitution."
            " The catalogues are not repeated here: skills and agents are"
            " discovered from their native directories (`~/.gemini/skills/`,"
            " `~/.gemini/agents/`, `~/.gemini/config/skills/`, or"
            " `.gemini/` and `.agents/` in a project), and every skill is"
            " installed under `~/.claude/skills/<name>/SKILL.md`."
        ),
        "guidelines": ["quality_standards", "workflow"],
    })
