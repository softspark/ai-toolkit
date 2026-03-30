"""Shared generator pipeline for producing AI tool configs.

Each generator declares its output format via a config dict.
This module handles the shared pipeline: count → emit → wrap.

Stdlib-only.

Usage::

    from generator_base import render_generator

    render_generator({
        "title": "# Cursor Rules",
        "header_lines": ["# Auto-generated..."],
        "intro_template": "This repo uses ai-toolkit with {agents} agents and {skills} skills.",
        "agents_section": "## Available Agent Personas",
        "agents_format": "headings",    # "headings" or "bullets"
        "agents_level": "##",           # heading level (for "headings" format)
        "skills_section": "## Available Skills",
        "skills_format": "headings",    # "headings" or "bullets"
        "skills_level": "##",           # heading level (for "headings" format)
        "guidelines_fn": "general",     # "general"|"quality"|"quality_standards"|"workflow"|None
        "use_markers": True,            # wrap in TOOLKIT markers
        "trailing_newline_after_skills": True,  # extra blank line after skills
    })
"""
from __future__ import annotations

import sys

from emission import (
    count_agents_and_skills,
    emit_agents_bullets,
    emit_agents_headings,
    emit_skills_bullets,
    emit_skills_headings,
    generate_general_guidelines,
    generate_quality_guidelines,
    generate_quality_standards,
    generate_workflow_guidelines,
    print_toolkit_end,
    print_toolkit_start,
)

# Map guideline names to functions
_GUIDELINES = {
    "general": generate_general_guidelines,
    "quality": generate_quality_guidelines,
    "quality_standards": generate_quality_standards,
    "workflow": generate_workflow_guidelines,
}


def render_generator(config: dict) -> None:
    """Render a generator output based on a declarative config.

    Config keys:
        title: str — main heading line
        header_lines: list[str] — additional header lines (comments etc)
        intro_template: str — format string with {agents} and {skills}
        agents_section: str — heading for agents section
        agents_format: "headings" | "bullets"
        agents_level: str — heading level for headings format (default "##")
        skills_section: str — heading for skills section
        skills_format: "headings" | "bullets"
        skills_level: str — heading level for headings format (default "##")
        guidelines: list[str] — list of guideline block names to include
        use_markers: bool — wrap in TOOLKIT markers (default True)
        trailing_newline_after_skills: bool — extra blank line after skills emit
    """
    agents, skills = count_agents_and_skills()

    if config.get("use_markers", True):
        print_toolkit_start()

    # Title
    if "title" in config:
        print(config["title"])

    # Header lines
    for line in config.get("header_lines", []):
        print(line)

    # Intro
    if "intro_template" in config:
        if config.get("header_lines") or "title" in config:
            print()
        print(config["intro_template"].format(agents=agents, skills=skills))

    # Agents section
    if "agents_section" in config:
        print()
        print(config["agents_section"].format(agents=agents, skills=skills))
        print()
        agents_intro = config.get("agents_intro")
        if agents_intro:
            print(agents_intro)
            print()

        fmt = config.get("agents_format", "headings")
        level = config.get("agents_level", "##")
        if fmt == "bullets":
            print(emit_agents_bullets())
        else:
            print(emit_agents_headings(level))

    # Skills section
    if "skills_section" in config:
        # Bullets format needs a separator; headings already end with blank line
        if config.get("agents_format") == "bullets":
            print()
        print(config["skills_section"].format(agents=agents, skills=skills))
        print()
        skills_intro = config.get("skills_intro")
        if skills_intro:
            print(skills_intro)
            print()

        fmt = config.get("skills_format", "headings")
        level = config.get("skills_level", "##")
        if fmt == "bullets":
            print(emit_skills_bullets())
        else:
            # Use sys.stdout.write to match original output (no trailing newline)
            sys.stdout.write(emit_skills_headings(level))

        if config.get("trailing_newline_after_skills", False):
            print()

    # Guidelines
    for guideline_name in config.get("guidelines", []):
        print()
        fn = _GUIDELINES.get(guideline_name)
        if fn:
            print(fn())

    # End marker
    if config.get("use_markers", True):
        print()
        print_toolkit_end()
