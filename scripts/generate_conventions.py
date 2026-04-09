#!/usr/bin/env python3
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
