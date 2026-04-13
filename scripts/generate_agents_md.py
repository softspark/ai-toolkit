#!/usr/bin/env python3
"""Generate AGENTS.md from app/agents/*.md frontmatter.

Output is compatible with Codex, OpenCode, and Gemini CLI AGENTS.md format.
Usage: ./scripts/generate_agents_md.py > AGENTS.md
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import subprocess

from _common import agents_dir, frontmatter_field


def main() -> None:
    print("# AGENTS.md")
    print()
    print(
        "This file describes the specialized AI agents bundled with ai-toolkit."
    )
    print(
        "It is auto-generated from `app/agents/*.md` frontmatter"
        " — do not edit manually."
    )
    print()
    print("To regenerate: `python3 scripts/generate_agents_md.py > AGENTS.md`")
    print()
    print("Compatible with: Claude Code, Codex, OpenCode, Gemini CLI.")
    print()
    print("---")
    print()
    print("## Usage")
    print()
    print("### Claude Code")
    print(
        "Agents are loaded automatically from `.claude/agents/`"
        " after running `install.sh`."
    )
    print("Invoke via the Agent tool:")
    print("```")
    print(
        'Use subagent_type: "backend-specialist" to implement the API endpoint.'
    )
    print("```")
    print()
    print("### Codex / OpenCode")
    print("Reference agents by name in your prompts:")
    print("```")
    print("@backend-specialist implement the payment API")
    print("```")
    print()
    print("### Gemini CLI")
    print("Use agent descriptions as system context:")
    print("```")
    print(
        'gemini --system "$(cat .claude/agents/backend-specialist.md)"'
        ' "implement the API"'
    )
    print("```")
    print()
    print("---")
    print()
    print("## Agents")
    print()

    for agent_file in sorted(agents_dir.glob("*.md")):
        if not agent_file.is_file():
            continue

        name = frontmatter_field(agent_file, "name")
        description = frontmatter_field(agent_file, "description")
        tools = frontmatter_field(agent_file, "tools")

        if not name:
            continue

        print(f"### `{name}`")
        print()
        if description:
            print(description)
            print()
        if tools:
            print(f"**Tools:** `{tools}`")
            print()
        print("---")
        print()

    # Codex CLI configuration block (agents, skills, guidelines)
    codex_script = Path(__file__).resolve().parent / "generate_codex.py"
    result = subprocess.run(
        ["python3", str(codex_script)],
        capture_output=True, text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        print(result.stdout.rstrip())

    # Note: custom rules are included via generate_codex.py output above


if __name__ == "__main__":
    main()
