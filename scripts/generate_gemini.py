#!/usr/bin/env python3
"""Generate GEMINI.md from app/agents/*.md and app/skills/*/SKILL.md.

Usage: ./scripts/generate_gemini.py > GEMINI.md
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generator_base import render_generator

if __name__ == "__main__":
    render_generator({
        "title": "# AI Toolkit — Gemini CLI Configuration",
        "intro_template": (
            "Shared AI development toolkit with {agents} specialized agents,"
            " {skills} skills, quality hooks, and a safety constitution."
        ),
        "agents_section": "## Available Agents ({agents})",
        "agents_intro": "Specialized agent personas — apply their expertise for relevant tasks:",
        "agents_format": "bullets",
        "skills_section": "## Available Skills ({skills})",
        "skills_intro": "Skills are invocable slash commands or auto-loaded knowledge sources:",
        "skills_format": "bullets",
        "guidelines": ["quality_standards", "workflow"],
    })
