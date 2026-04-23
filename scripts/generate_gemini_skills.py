#!/usr/bin/env python3
"""Generate a Gemini CLI skill pointer under ``.gemini/skills/``.

Gemini supports the Agent Skills standard via
``.gemini/skills/<skill-name>/SKILL.md``. Rather than duplicating the full
ai-toolkit skill catalogue into Gemini's skills directory (which would
produce 99 near-duplicate files on every install), we emit a single
**pointer skill** that teaches Gemini to resolve real skills from the
canonical Claude Code locations:

  * ``.claude/skills/<name>/SKILL.md`` (project-local install)
  * ``~/.claude/skills/<name>/SKILL.md`` (global install)

This mirrors the pattern used by ``generate_antigravity.py``.

Usage:
  python3 scripts/generate_gemini_skills.py [target-dir]

Writes ``<target-dir>/.gemini/skills/ai-toolkit-skill-catalogue/SKILL.md``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emission import emit_skills_bullets


# ---------------------------------------------------------------------------
# Skill pointer — a single SKILL.md that directs Gemini to our catalogue
# ---------------------------------------------------------------------------

POINTER_SKILL_NAME = "ai-toolkit-skill-catalogue"


def _pointer_skill_md() -> str:
    """Build the SKILL.md body for the Gemini pointer skill."""
    body = (
        "# AI Toolkit Skill Catalogue\n\n"
        "This workspace uses the ai-toolkit. Real skills are installed "
        "alongside Claude Code at `.claude/skills/` (project install) or "
        "`~/.claude/skills/` (global install). If the ai-toolkit installer "
        "has run, every skill below already exists as an agent-invocable "
        "SKILL.md on disk.\n\n"
        "## When to use this skill\n\n"
        "- You are asked to run a task that maps to one of the catalogued "
        "skills below.\n"
        "- You want to discover which skills the user has installed before "
        "reinventing the wheel.\n\n"
        "## How to invoke a catalogue entry\n\n"
        "1. Match the user's task to a skill name in the catalogue.\n"
        "2. Read the skill's SKILL.md from `.claude/skills/<name>/SKILL.md` "
        "or `~/.claude/skills/<name>/SKILL.md` (whichever exists).\n"
        "3. Follow its Rules, Gotchas, and When NOT to Use sections.\n\n"
        "## Catalogue (installed skills)\n\n"
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


def _write_skill_pointer(target_dir: Path) -> None:
    """Write the pointer SKILL.md under .gemini/skills/<name>/."""
    skill_dir = target_dir / ".gemini" / "skills" / POINTER_SKILL_NAME
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(_pointer_skill_md(), encoding="utf-8")
    print(f"  Generated: .gemini/skills/{POINTER_SKILL_NAME}/SKILL.md")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate(target_dir: Path, *, emit_skill_pointer: bool = True) -> None:
    """Write ``.gemini/skills/ai-toolkit-skill-catalogue/SKILL.md``.

    ``emit_skill_pointer`` controls whether the pointer SKILL.md is written.
    Set to ``False`` to leave Gemini's skills directory untouched.
    """
    if emit_skill_pointer:
        _write_skill_pointer(target_dir)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    generate(target)


if __name__ == "__main__":
    main()
