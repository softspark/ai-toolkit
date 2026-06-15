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
from dir_rules_shared import (
    rule_code_style,
    rule_output_mode,
    rule_security,
    rule_testing,
)
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


def _emit_coding_rules() -> str:
    """Inline the universal coding-rule bodies so Codex receives them.

    Codex reads project instructions only from AGENTS.md (and AGENTS.override.md);
    it does not read a ``.agents/rules/`` directory. Workflow + quality standards
    are already emitted above, so this adds code-style, testing, security, and
    output-mode under a single ``## Coding Rules`` section (H1 demoted to H3).
    """
    sections: list[str] = []
    for rule_fn in (rule_code_style, rule_testing, rule_security, rule_output_mode):
        body = rule_fn().rstrip()
        if body.startswith("# "):
            body = "### " + body[2:]
        sections.append(body)
    return "## Coding Rules\n\n" + "\n\n".join(sections)


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

    # Universal coding rules — Codex reads instructions only from AGENTS.md,
    # so inline them here (previously emitted to the unread .agents/rules/).
    print()
    print(_emit_coding_rules())

    print_toolkit_end()

    # Registered custom rules from ~/.softspark/ai-toolkit/rules/.
    # Skipped when AI_TOOLKIT_NO_CUSTOM_RULES=1 so a maintainer's personal
    # registered rules never leak into the toolkit's own canonical files.
    if RULES_DIR.is_dir() and os.environ.get("AI_TOOLKIT_NO_CUSTOM_RULES") != "1":
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
