#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate AGENTS.md content for opencode (https://opencode.ai).

opencode reads AGENTS.md using the same convention as OpenAI Codex CLI.
The generated file is safe for both editors to consume from the same
project root — each injects into its own marker-wrapped block.

Usage: ./scripts/generate_opencode.py > AGENTS.md
"""
from __future__ import annotations

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
from injection import strip_owned_sections
from paths import RULES_DIR
from secure_fs import OwnedEdit, apply_owned_edits, lexical_absolute


def _emit_agents() -> str:
    """Emit agents as opencode subagent bullets."""
    lines: list[str] = []
    for agent_file in sorted(agents_dir.glob("*.md")):
        name = frontmatter_field(agent_file, "name")
        description = frontmatter_field(agent_file, "description")
        if not name or not description:
            continue
        lines.append(f"- **{name}**: {description}")
    return "\n".join(lines)


def _emit_skills() -> str:
    """Emit user-invocable skills as opencode command bullets.

    Adapts Claude orchestration-only descriptions via the Codex adapter —
    opencode, like Codex, lacks Claude's Agent/Team/Task primitives so the
    same translation layer applies.
    """
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


def _cleanup_plan(
    target_dir: Path, config_root: Path | None
) -> tuple[Path, dict[Path, OwnedEdit], tuple[Path, ...]]:
    target = lexical_absolute(target_dir)
    base = lexical_absolute(config_root) if config_root is not None else target
    if base.is_symlink():
        raise RuntimeError(f"Refusing symlinked OpenCode path: {base}")
    path = base / "AGENTS.md"
    edits = {path: strip_owned_sections} if path.is_file() else {}
    return target, edits, () if base == target else (base,)


def cleanup(target_dir: Path, config_root: Path | None = None) -> int:
    """Strip TOOLKIT sections from ``AGENTS.md``; delete it when nothing remains.

    ``config_root`` selects the global ``~/.config/opencode/AGENTS.md``;
    otherwise ``target_dir/AGENTS.md`` (shared with Codex) is used. Returns 1
    when the file was rewritten or removed, else 0.
    """
    target, edits, prune = _cleanup_plan(target_dir, config_root)
    return apply_owned_edits(edits, target, label="OpenCode AGENTS.md", prune=prune)


def discover(target_dir: Path, config_root: Path | None = None) -> int:
    """Return 1 when :func:`cleanup` would change ``AGENTS.md``, without side effects."""
    target, edits, _ = _cleanup_plan(target_dir, config_root)
    return apply_owned_edits(edits, target, label="OpenCode AGENTS.md", dry_run=True)


def main() -> None:
    print_toolkit_start()

    print("# AI Toolkit — opencode Configuration")
    print()
    print(
        "Shared AI development toolkit with specialized subagents,"
        " opencode-compatible commands, quality hooks, and a safety constitution."
    )
    print()
    print(
        "opencode reads this file at session start. Subagents are also"
        " installed under `.opencode/agents/` and slash commands under"
        " `.opencode/commands/` for native `@` and `/` autocomplete."
    )

    # Agents
    print()
    print("## Available Subagents")
    print()
    print("Invoke with `@<name>` in opencode, or delegate via `spawn_agent`:")
    print()
    print(_emit_agents())

    # Skills / slash commands
    print()
    print("## Available Commands")
    print()
    print("Invoke with `/<name>` in opencode. Knowledge-only skills load automatically:")
    print()
    print(_emit_skills())

    # Guidelines
    print()
    print(generate_quality_standards())
    print()
    print(generate_workflow_guidelines())

    print_toolkit_end()

    # Registered custom rules from ~/.softspark/ai-toolkit/rules/
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
