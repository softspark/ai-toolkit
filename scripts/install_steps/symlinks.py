"""Agent and skill symlink management."""
from __future__ import annotations

from pathlib import Path

from _common import app_dir, should_install


def install_agents(claude_dir: Path, only: str, skip: str, dry_run: bool) -> None:
    """Create per-file symlinks for agents."""
    if not should_install("agents", only, skip):
        print("  Skipped: .claude/agents")
        return

    agents_src = app_dir / "agents"
    if not agents_src.is_dir():
        return

    if dry_run:
        print("  Would link: .claude/agents/*.md (per-file merge)")
        return

    agents_dst = claude_dir / "agents"
    if agents_dst.is_symlink():
        agents_dst.unlink()
        print("  Upgraded: .claude/agents (directory symlink -> per-file)")
    agents_dst.mkdir(parents=True, exist_ok=True)
    linked = 0
    skipped = 0
    for agent_file in sorted(agents_src.glob("*.md")):
        target = agents_dst / agent_file.name
        if target.is_symlink():
            target.unlink()
        if target.is_file():
            skipped += 1
            continue
        target.symlink_to(agent_file)
        linked += 1
    print(f"  Linked: .claude/agents/ ({linked} files)")
    if skipped > 0:
        print(f"  Kept: {skipped} user agent(s) (name conflict)")


def install_skills(claude_dir: Path, only: str, skip: str, dry_run: bool) -> None:
    """Create per-directory symlinks for skills."""
    if not should_install("skills", only, skip):
        print("  Skipped: .claude/skills")
        return

    skills_src = app_dir / "skills"
    if not skills_src.is_dir():
        return

    if dry_run:
        print("  Would link: .claude/skills/*/ (per-directory merge)")
        return

    skills_dst = claude_dir / "skills"
    if skills_dst.is_symlink():
        skills_dst.unlink()
        print("  Upgraded: .claude/skills (directory symlink -> per-directory)")
    skills_dst.mkdir(parents=True, exist_ok=True)
    linked = 0
    skipped = 0
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
            continue
        target = skills_dst / skill_dir.name
        if target.is_symlink():
            target.unlink()
        if target.is_dir():
            skipped += 1
            continue
        target.symlink_to(skill_dir)
        linked += 1
    print(f"  Linked: .claude/skills/ ({linked} directories)")
    if skipped > 0:
        print(f"  Kept: {skipped} user skill(s) (name conflict)")


def clean_legacy_commands(claude_dir: Path, dry_run: bool) -> None:
    """Remove legacy commands symlink."""
    legacy_commands = claude_dir / "commands"
    if legacy_commands.is_symlink():
        if not dry_run:
            legacy_commands.unlink()
        print("  Removed: .claude/commands (legacy)")
