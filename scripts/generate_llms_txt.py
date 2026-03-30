#!/usr/bin/env python3
"""Generate llms.txt and llms-full.txt from kb/ docs.

Usage:
  ./scripts/generate_llms_txt.py          -> llms.txt (index only)
  ./scripts/generate_llms_txt.py --full   -> llms-full.txt (full content)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import agents_dir, frontmatter_field, skill_count, skills_dir, toolkit_dir


def _relative(path: Path) -> str:
    """Return path relative to toolkit_dir."""
    return str(path.relative_to(toolkit_dir))


def _title_from_md(filepath: Path) -> str:
    """Extract the first ``# `` heading from a markdown file, or fallback to stem."""
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            if line.startswith("# "):
                return line[2:].strip()
    return filepath.stem


def _find_kb_files() -> list[Path]:
    """Find all .md files under kb/, sorted."""
    kb_dir = toolkit_dir / "kb"
    if not kb_dir.is_dir():
        return []
    return sorted(kb_dir.rglob("*.md"))


def _find_skill_files() -> list[Path]:
    """Find all SKILL.md files, sorted."""
    return sorted(skills_dir.rglob("SKILL.md"))


def _find_agent_files() -> list[Path]:
    """Find all agent .md files, sorted."""
    return sorted(agents_dir.glob("*.md"))


def _count_skills() -> int:
    """Count skill directories containing SKILL.md."""
    return skill_count()


def _count_agents() -> int:
    """Count agent .md files."""
    return sum(1 for f in agents_dir.glob("*.md") if f.is_file())


def generate_index() -> None:
    """Print the llms.txt index."""
    skills = _count_skills()
    agents = _count_agents()

    print("# ai-toolkit")
    print()
    print(
        f"> Professional-grade Claude Code toolkit: {skills} skills,"
        f" {agents} agents, machine-enforced constitution, quality hooks."
    )
    print()
    print("## Documentation")
    print()

    readme = toolkit_dir / "README.md"
    if readme.is_file():
        print("- [README](README.md): Installation, usage, and feature overview")
    changelog = toolkit_dir / "CHANGELOG.md"
    if changelog.is_file():
        print("- [CHANGELOG](CHANGELOG.md): Version history")
    contributing = toolkit_dir / "CONTRIBUTING.md"
    if contributing.is_file():
        print("- [CONTRIBUTING](CONTRIBUTING.md): How to add agents and skills")
    architecture = toolkit_dir / "app" / "ARCHITECTURE.md"
    if architecture.is_file():
        print("- [ARCHITECTURE](app/ARCHITECTURE.md): System design")
    constitution = toolkit_dir / "app" / "constitution.md"
    if constitution.is_file():
        print("- [CONSTITUTION](app/constitution.md): Safety rules")

    kb_files = _find_kb_files()
    if kb_files:
        print()
        print("## Knowledge Base")
        print()
        for f in kb_files:
            rel = _relative(f)
            title = _title_from_md(f)
            print(f"- [{title}]({rel})")


def generate_skills_listing() -> None:
    """Print the skills listing section."""
    print()
    print("## Skills")
    print()

    for skill_file in _find_skill_files():
        skill_name = frontmatter_field(skill_file, "name")
        if not skill_name:
            skill_name = skill_file.parent.name
        skill_desc = frontmatter_field(skill_file, "description")
        print(f"- **{skill_name}**: {skill_desc}")


def generate_agents_listing() -> None:
    """Print the agents listing section."""
    print()
    print("## Agents")
    print()

    for agent_file in _find_agent_files():
        if not agent_file.is_file():
            continue
        agent_name = frontmatter_field(agent_file, "name")
        if not agent_name:
            agent_name = agent_file.stem
        agent_desc = frontmatter_field(agent_file, "description")
        print(f"- **{agent_name}**: {agent_desc}")


def generate_full() -> None:
    """Print full llms-full.txt with all KB content inlined."""
    generate_index()
    generate_skills_listing()
    generate_agents_listing()

    kb_files = _find_kb_files()
    if kb_files:
        print()
        print("---")
        print()

        for f in kb_files:
            rel = _relative(f)
            print(f"## {rel}")
            print()
            sys.stdout.write(f.read_text(encoding="utf-8"))
            print()
            print("---")
            print()


def main() -> None:
    full_mode = "--full" in sys.argv[1:]

    if full_mode:
        generate_full()
    else:
        generate_index()


if __name__ == "__main__":
    main()
