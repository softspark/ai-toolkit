"""Render shared editor instructions from canonical ai-toolkit sources."""
from __future__ import annotations

import re
from pathlib import Path


CONSTITUTION_PATH = (
    Path(__file__).resolve().parent.parent / "app" / "constitution.md"
)


def _strip_frontmatter(text: str) -> str:
    """Return Markdown after an optional leading YAML frontmatter block."""
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return text.strip()
    try:
        closing = lines.index("---", 1)
    except ValueError:
        return text.strip()
    return "\n".join(lines[closing + 1:]).strip()


def read_constitution(path: Path = CONSTITUTION_PATH) -> str:
    """Read the canonical constitution body without YAML frontmatter."""
    return _strip_frontmatter(path.read_text(encoding="utf-8"))


def render_constitution_policy(
    heading_level: int = 2,
    path: Path = CONSTITUTION_PATH,
) -> str:
    """Render the canonical constitution below a caller-selected heading."""
    if not 1 <= heading_level <= 5:
        raise ValueError("heading_level must be between 1 and 5")

    body_lines = read_constitution(path).splitlines()
    if body_lines and body_lines[0].startswith("# "):
        body_lines = body_lines[1:]
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)

    heading_shift = heading_level - 1
    rebased: list[str] = []
    for line in body_lines:
        match = re.match(r"^(#{1,6})(\s+.*)$", line)
        if not match:
            rebased.append(line)
            continue
        level = min(6, len(match.group(1)) + heading_shift)
        rebased.append("#" * level + match.group(2))

    title = "#" * heading_level + " Constitution"
    source = "Generated from `app/constitution.md`, the single policy source."
    return f"{title}\n\n{source}\n\n" + "\n".join(rebased).rstrip()


def _demote_rule_heading(body: str) -> str:
    if body.startswith("# "):
        return "### " + body[2:]
    return body


def render_instruction_core() -> str:
    """Render the compact root AGENTS.md body shared by Codex and Copilot."""
    from dir_rules_shared import (
        rule_code_style,
        rule_output_mode,
        rule_security,
        rule_testing,
    )
    from emission import generate_workflow_guidelines

    coding_rules = "\n\n".join(
        _demote_rule_heading(rule_fn().rstrip())
        for rule_fn in (
            rule_code_style,
            rule_testing,
            rule_security,
            rule_output_mode,
        )
    )
    sections = [
        "# AI Toolkit Instructions",
        (
            "Shared, always-on policy for ai-toolkit projects. Agent and skill"
            " catalogs are discovered from their native directories instead of"
            " being duplicated here."
        ),
        render_constitution_policy(heading_level=2),
        generate_workflow_guidelines(),
        "## Coding Rules\n\n" + coding_rules,
    ]
    return "\n\n".join(sections).rstrip() + "\n"
