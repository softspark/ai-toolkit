#!/usr/bin/env python3
"""Generate .github/copilot-instructions.md from app/agents/*.md and app/skills/*/SKILL.md.

Usage: ./scripts/generate_copilot.py > .github/copilot-instructions.md
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generator_base import render_generator

if __name__ == "__main__":
    render_generator({
        "title": "# GitHub Copilot Instructions",
        "intro_template": (
            "This repository uses the ai-toolkit — a shared AI development toolkit"
            " with {agents} specialized agent personas and {skills} skills."
        ),
        "agents_section": "## Available Agent Personas",
        "agents_intro": "Apply the expertise of these agents when working on relevant tasks:",
        "agents_format": "headings",
        "agents_level": "###",
        "skills_section": "## Available Skills",
        "skills_intro": "The following skills are available as slash commands or knowledge sources:",
        "skills_format": "headings",
        "skills_level": "###",
        "guidelines": ["quality"],
    })
