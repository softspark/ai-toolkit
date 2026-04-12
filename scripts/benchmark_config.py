#!/usr/bin/env python3
"""ai-toolkit benchmark --my-config — Compare user config vs toolkit vs ecosystem."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir

from paths import HOOKS_DIR as _HOOKS_DIR

CLAUDE_DIR = Path.home() / ".claude"
HOOKS_DIR = _HOOKS_DIR
DASHBOARD = toolkit_dir / "benchmarks" / "ecosystem-dashboard.json"


def count_files(directory: Path, pattern: str, min_depth: int = 0) -> int:
    """Count files matching pattern in directory."""
    if not directory.is_dir():
        return 0
    count = 0
    for p in directory.iterdir():
        if min_depth > 0 and not p.is_dir():
            continue
        if p.name.endswith(pattern.lstrip("*")) if "*" in pattern else p.name == pattern:
            count += 1
        if min_depth > 0 and p.is_dir():
            count += 1
    return count


def main() -> None:
    tk_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else toolkit_dir

    print("AI Toolkit Config Benchmark")
    print("========================")
    print()

    # --- User's installed components ---
    print("## Your Configuration (~/.claude/)")

    user_agents = sum(1 for f in (CLAUDE_DIR / "agents").glob("*.md")) if (CLAUDE_DIR / "agents").is_dir() else 0
    user_skills = sum(1 for d in (CLAUDE_DIR / "skills").iterdir() if d.is_dir() or d.is_symlink()) if (CLAUDE_DIR / "skills").is_dir() else 0
    user_hooks = sum(1 for f in HOOKS_DIR.glob("*.sh")) if HOOKS_DIR.is_dir() else 0

    print(f"  Agents:  {user_agents}")
    print(f"  Skills:  {user_skills}")
    print(f"  Hooks:   {user_hooks}")
    print()

    # --- Toolkit totals ---
    print("## Toolkit Totals")

    tk_agents = sum(1 for f in (tk_dir / "app" / "agents").glob("*.md"))
    tk_skills = sum(1 for d in (tk_dir / "app" / "skills").iterdir() if d.is_dir())
    tk_hooks = sum(1 for f in (tk_dir / "app" / "hooks").glob("*.sh"))

    print(f"  Agents:  {tk_agents}")
    print(f"  Skills:  {tk_skills}")
    print(f"  Hooks:   {tk_hooks}")
    print()

    # --- Coverage ---
    print("## Coverage")

    agent_pct = (user_agents * 100 // tk_agents) if tk_agents > 0 else 0
    skill_pct = (user_skills * 100 // tk_skills) if tk_skills > 0 else 0
    hook_pct = (user_hooks * 100 // tk_hooks) if tk_hooks > 0 else 0

    print(f"  Agents:  {agent_pct}%  ({user_agents} / {tk_agents})")
    print(f"  Skills:  {skill_pct}%  ({user_skills} / {tk_skills})")
    print(f"  Hooks:   {hook_pct}%  ({user_hooks} / {tk_hooks})")
    print()

    # --- Missing components ---
    if user_agents < tk_agents or user_skills < tk_skills:
        print("## Missing Components")
        shown = 0
        if (tk_dir / "app" / "agents").is_dir() and (CLAUDE_DIR / "agents").is_dir():
            for agent in sorted((tk_dir / "app" / "agents").glob("*.md")):
                if not (CLAUDE_DIR / "agents" / agent.name).exists():
                    print(f"  Agent: {agent.name}")
                    shown += 1
                    if shown >= 10:
                        break
            missing = tk_agents - user_agents
            if missing > 10:
                print(f"  ... and {missing - 10} more agents")

        if (tk_dir / "app" / "skills").is_dir() and (CLAUDE_DIR / "skills").is_dir():
            for skill_dir in sorted((tk_dir / "app" / "skills").iterdir()):
                if not skill_dir.is_dir():
                    continue
                if not (CLAUDE_DIR / "skills" / skill_dir.name).exists():
                    print(f"  Skill: {skill_dir.name}")
                    shown += 1
                    if shown >= 20:
                        break
            missing = tk_skills - user_skills
            if missing > 10:
                print(f"  ... and {missing - 10} more skills")
        print()

    # --- Ecosystem comparison ---
    if DASHBOARD.is_file():
        print("## Ecosystem Comparison")
        with open(DASHBOARD) as f:
            data = json.load(f)

        header = f"{'Repo':<40} {'Agents':>7} {'Skills':>7} {'Hooks':>6}"
        print(header)
        print("-" * 62)
        print(f"{'Your config':<40} {user_agents:>7} {user_skills:>7} {user_hooks:>6}")
        print("-" * 62)
        for repo in data.get("repos", []):
            name = repo.get("repo", "unknown")
            agents = repo.get("agents_md", 0)
            skills = repo.get("skills", 0) + repo.get("commands_md", 0)
            hooks = repo.get("hook_settings_files", 0)
            print(f"{name:<40} {agents:>7} {skills:>7} {hooks:>6}")

    print()
    print("Run 'ai-toolkit install' to sync missing components.")


if __name__ == "__main__":
    main()
