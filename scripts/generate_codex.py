#!/usr/bin/env python3
"""Generate AGENTS.md content for OpenAI Codex CLI.

Adapts Claude-oriented skills to Codex-native delegation guidance so the full
skill catalog can be surfaced in Codex installs.

Usage: ./scripts/generate_codex.py > AGENTS.md
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_skill_adapter import codex_skill_description
from emission import (
    agents_dir,
    skills_dir,
    generate_quality_standards,
    generate_workflow_guidelines,
    print_toolkit_end,
    print_toolkit_start,
)
from frontmatter import frontmatter_field
from paths import RULES_DIR


def _emit_agents() -> str:
    """Emit agents as bullets."""
    lines: list[str] = []
    for agent_file in sorted(agents_dir.glob("*.md")):
        name = frontmatter_field(agent_file, "name")
        description = frontmatter_field(agent_file, "description")
        if not name or not description:
            continue
        lines.append(f"- **{name}**: {description}")
    return "\n".join(lines)


def _emit_skills() -> str:
    """Emit skills as bullets, adapting Claude-native descriptions for Codex."""
    lines: list[str] = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if skill_dir.name.startswith("_"):
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        name = frontmatter_field(skill_file, "name")
        description = codex_skill_description(skill_file)
        if not name or not description:
            continue
        lines.append(f"- **{name}**: {description}")
    return "\n".join(lines)


def main() -> None:
    print_toolkit_start()

    print("# AI Toolkit — Codex CLI Configuration")
    print()
    print(
        "Shared AI development toolkit with specialized agents,"
        " Codex-compatible skills, quality hooks, and a safety constitution."
    )

    # Agents (all agents are informational — safe to list)
    print()
    print("## Available Agents")
    print()
    print("Specialized agent personas — apply their expertise for relevant tasks:")
    print()
    print(_emit_agents())

    # Skills
    print()
    print("## Available Skills")
    print()
    print("Skills are invocable commands or auto-loaded knowledge sources:")
    print()
    print(_emit_skills())

    # Guidelines
    print()
    print(generate_quality_standards())
    print()
    print(generate_workflow_guidelines())

    print_toolkit_end()

    # Registered custom rules — skip when called by inject_with_rules()
    # (which handles injection separately via inject_section)
    if not os.environ.get("_TOOLKIT_INJECT_MODE"):
        if RULES_DIR.is_dir():
            for rule_file in sorted(RULES_DIR.glob("*.md")):
                rule_name = rule_file.stem
                print()
                print(f"<!-- TOOLKIT:{rule_name} START -->")
                print("<!-- Auto-injected by ai-toolkit. Re-run to update. -->")
                print()
                print(rule_file.read_text(encoding="utf-8").rstrip())
                print()
                print(f"<!-- TOOLKIT:{rule_name} END -->")


if __name__ == "__main__":
    main()
