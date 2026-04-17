#!/usr/bin/env python3
"""ai-toolkit eject -- Export standalone toolkit config.

Creates a self-contained copy of the toolkit configuration in the
target directory with no symlinks and no dependency on ai-toolkit.

What it exports:
  - .claude/agents/*.md (real files, not symlinks)
  - .claude/skills/*/   (real directories, not symlinks)
  - .claude/output-styles/*.md (system-prompt styles)
  - .claude/CLAUDE.md   (inlined rules)
  - .claude/constitution.md (full content)
  - .claude/ARCHITECTURE.md (full content)

Usage:
  ai-toolkit eject [target-dir]
  target-dir defaults to current working directory
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import app_dir, inject_rule


def main() -> None:
    """Eject toolkit into a standalone directory."""
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    print("ai-toolkit eject")
    print("========================")
    print(f"Source:  {app_dir.parent}")
    print(f"Target:  {target_dir.resolve()}")
    print()

    claude_dir = target_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # -- Agents: copy as real files ------------------------------------------
    print("## Agents")
    agents_out = claude_dir / "agents"
    agents_out.mkdir(parents=True, exist_ok=True)
    agent_count = 0
    agents_src = app_dir / "agents"
    if agents_src.is_dir():
        for agent in sorted(agents_src.glob("*.md")):
            dest = agents_out / agent.name
            if dest.is_symlink():
                dest.unlink()
            shutil.copy2(agent, dest)
            agent_count += 1
    print(f"  Copied: {agent_count} agents")

    # -- Skills: copy as real directories ------------------------------------
    print("## Skills")
    skills_out = claude_dir / "skills"
    skills_out.mkdir(parents=True, exist_ok=True)
    skill_count = 0
    skills_src = app_dir / "skills"
    if skills_src.is_dir():
        for skill in sorted(skills_src.iterdir()):
            if not skill.is_dir():
                continue
            dest = skills_out / skill.name
            if dest.is_symlink():
                dest.unlink()
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(skill, dest)
            # Count only real skills. Underscore-prefixed dirs (e.g. `_lib/`)
            # are shared helpers that must be copied so dependent skills keep
            # working, but are not skills themselves — matches validate.py.
            if not skill.name.startswith("_") and (skill / "SKILL.md").is_file():
                skill_count += 1
    print(f"  Copied: {skill_count} skills")

    # -- CLAUDE.md: inline all rules -----------------------------------------
    print("## Rules")
    claude_md = claude_dir / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.touch()

    rule_count = 0
    rules_src = app_dir / "rules"
    if rules_src.is_dir():
        for rule in sorted(rules_src.glob("*.md")):
            inject_rule(rule, target_dir)
            rule_count += 1
    print(f"  Inlined: {rule_count} rules into CLAUDE.md")

    # -- Output styles: copy as real files -----------------------------------
    print("## Output Styles")
    style_count = 0
    styles_src = app_dir / "output-styles"
    if styles_src.is_dir():
        styles_out = claude_dir / "output-styles"
        styles_out.mkdir(parents=True, exist_ok=True)
        for style in sorted(styles_src.glob("*.md")):
            dest = styles_out / style.name
            if dest.is_symlink():
                dest.unlink()
            shutil.copy2(style, dest)
            style_count += 1
    print(f"  Copied: {style_count} output style(s)")

    # -- Constitution and Architecture ---------------------------------------
    print("## Config Files")
    for filename in ("constitution.md", "ARCHITECTURE.md"):
        src = app_dir / filename
        if src.is_file():
            dest = claude_dir / filename
            if dest.is_symlink():
                dest.unlink()
            shutil.copy2(src, dest)
            print(f"  Copied: {filename}")

    # -- Summary -------------------------------------------------------------
    print()
    print("========================")
    print(f"Ejected: {agent_count} agents, {skill_count} skills, {rule_count} rules, {style_count} output style(s)")
    print()
    print(f"The toolkit is now standalone in {target_dir.resolve()}/.claude/")
    print("You can safely run: npm uninstall -g @softspark/ai-toolkit")
    print()
    print("Note: hooks are NOT ejected (they require settings.json merge).")
    print("To keep hooks working, keep ai-toolkit installed globally.")


if __name__ == "__main__":
    main()
