"""Shared generator for editor-native ai-toolkit skill catalogue pointers."""
from __future__ import annotations

from pathlib import Path

from emission import emit_skills_bullets


POINTER_SKILL_NAME = "ai-toolkit-skill-catalogue"


def build_pointer_skill(editor_name: str) -> str:
    """Build a SKILL.md pointer to the canonical ai-toolkit skill catalogue."""
    body = (
        "# AI Toolkit Skill Catalogue\n\n"
        f"This workspace uses ai-toolkit with {editor_name}. Real skills are "
        "installed alongside Claude Code at `.claude/skills/` (project "
        "install) or `~/.claude/skills/` (global install). If those paths are "
        "not present, use the catalogue below to identify the matching "
        "ai-toolkit skill before recreating its workflow manually.\n\n"
        "## When to use this skill\n\n"
        "- The user's request maps to one of the catalogued skills below.\n"
        "- You need to discover which ai-toolkit skill should guide the task.\n\n"
        "## How to use a catalogue entry\n\n"
        "1. Match the user's task to a skill name in the catalogue.\n"
        "2. Read the skill's SKILL.md from `.claude/skills/<name>/SKILL.md` "
        "or `~/.claude/skills/<name>/SKILL.md` when available.\n"
        "3. Follow that skill's workflow, rules, gotchas, and exclusions.\n\n"
        "## Catalogue\n\n"
        f"{emit_skills_bullets()}\n"
    )
    return (
        "---\n"
        f"name: {POINTER_SKILL_NAME}\n"
        "description: Index of ai-toolkit skills installed at .claude/skills/"
        " or ~/.claude/skills/. Read this first when the user's request "
        "matches a named skill.\n"
        "---\n"
        f"{body}"
    )


def write_pointer_skill(target_dir: Path, skill_root: str, editor_name: str) -> Path:
    """Write a pointer skill under ``skill_root/<pointer>/SKILL.md``."""
    skill_dir = target_dir / skill_root / POINTER_SKILL_NAME
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(build_pointer_skill(editor_name), encoding="utf-8")
    return skill_file
