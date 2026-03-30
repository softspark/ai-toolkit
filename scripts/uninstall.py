#!/usr/bin/env python3
"""AI Toolkit Uninstaller.

Removes toolkit symlinks from ~/.claude/ (global install).

Handles both old-style (whole-directory symlinks) and new-style
(per-file symlinks inside agents/ and skills/ directories).
User-owned files are never removed.

Usage:
    python3 scripts/uninstall.py [--yes] [target-dir]
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir, app_dir


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_toolkit_link(link_target: str) -> bool:
    """Check if a symlink target points into the ai-toolkit app directory."""
    return str(app_dir) in link_target or "/ai-toolkit/app/" in link_target


def _strip_all_toolkit_markers(filepath: Path) -> str | None:
    """Remove all TOOLKIT marker sections from a file.

    Returns the remaining content, or None if file doesn't exist.
    """
    if not filepath.is_file():
        return None

    content = filepath.read_text(encoding="utf-8")
    if "<!-- TOOLKIT:" not in content:
        return content

    lines: list[str] = []
    skip = False
    for line in content.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        if re.match(r"^<!-- TOOLKIT:\S+ START -->$", stripped):
            skip = True
            continue
        if re.match(r"^<!-- TOOLKIT:\S+ END -->$", stripped):
            skip = False
            continue
        if not skip:
            lines.append(line)

    result = "".join(lines).strip()
    return result


# ---------------------------------------------------------------------------
# Discovery: count what would be removed
# ---------------------------------------------------------------------------

def discover_components(claude_dir: Path) -> list[tuple[str, str]]:
    """Find all toolkit components installed in claude_dir.

    Returns a list of (description, type) tuples.
    """
    found: list[tuple[str, str]] = []

    # Check old-style directory symlinks (backward compat)
    for item in ("agents", "skills"):
        target = claude_dir / item
        if target.is_symlink():
            link_target = str(target.resolve())
            found.append((f"Symlink: {item} -> {link_target} (directory)", "old-dir"))

    # Check per-file agent symlinks (new-style)
    agents_dir = claude_dir / "agents"
    if agents_dir.is_dir() and not agents_dir.is_symlink():
        for agent in sorted(agents_dir.glob("*.md")):
            if not agent.is_symlink():
                continue
            link_target = str(agent.readlink())
            if _is_toolkit_link(link_target):
                found.append(
                    (f"Symlink: agents/{agent.name} -> {link_target}", "agent-link")
                )

    # Check per-directory skill symlinks (new-style)
    skills_dir = claude_dir / "skills"
    if skills_dir.is_dir() and not skills_dir.is_symlink():
        for skill in sorted(skills_dir.iterdir()):
            if not skill.is_symlink():
                continue
            link_target = str(skill.readlink())
            if _is_toolkit_link(link_target):
                found.append(
                    (f"Symlink: skills/{skill.name}/ -> {link_target}", "skill-link")
                )

    # Check hooks.json for toolkit entries (merged, not symlinked)
    hooks_file = claude_dir / "hooks.json"
    if hooks_file.is_symlink():
        found.append(
            (f"Symlink: hooks.json -> {hooks_file.readlink()} (legacy)", "hooks-link")
        )
    elif hooks_file.is_file():
        content = hooks_file.read_text(encoding="utf-8")
        if '"_source"' in content and '"ai-toolkit"' in content:
            count = content.count('"ai-toolkit"')
            found.append(
                (f"Merged: hooks.json ({count} toolkit entries)", "hooks-merged")
            )

    # Check marker-injected files (constitution.md, ARCHITECTURE.md)
    for item in ("constitution.md", "ARCHITECTURE.md"):
        target = claude_dir / item
        if target.is_symlink():
            found.append(
                (f"Symlink: {item} -> {target.readlink()} (legacy)", "marker-link")
            )
        elif target.is_file():
            content = target.read_text(encoding="utf-8")
            if "<!-- TOOLKIT:" in content:
                found.append((f"Injected: {item} (marker-based)", "marker-inject"))

    # Check legacy commands symlink
    commands = claude_dir / "commands"
    if commands.is_symlink():
        found.append(
            (f"Symlink: commands -> {commands.readlink()} (legacy)", "old-dir")
        )

    return found


# ---------------------------------------------------------------------------
# Removal
# ---------------------------------------------------------------------------

def remove_components(claude_dir: Path) -> None:
    """Remove all toolkit components from claude_dir."""

    # Remove old-style directory symlinks (backward compat)
    for item in ("agents", "skills", "commands"):
        target = claude_dir / item
        if target.is_symlink():
            target.unlink()
            print(f"  Removed: {item} (directory symlink)")

    # Remove per-file agent symlinks (only those pointing into toolkit)
    agents_dir = claude_dir / "agents"
    if agents_dir.is_dir() and not agents_dir.is_symlink():
        removed = 0
        for agent in sorted(agents_dir.glob("*.md")):
            if not agent.is_symlink():
                continue
            link_target = str(agent.readlink())
            if _is_toolkit_link(link_target):
                agent.unlink()
                removed += 1
        if removed > 0:
            print(f"  Removed: {removed} agent symlink(s)")
        # Remove the agents dir if it is now empty
        try:
            agents_dir.rmdir()
            print("  Removed: agents/ (empty)")
        except OSError:
            pass  # Not empty -- user has custom agents

    # Remove per-directory skill symlinks (only those pointing into toolkit)
    skills_dir = claude_dir / "skills"
    if skills_dir.is_dir() and not skills_dir.is_symlink():
        removed = 0
        for skill in sorted(skills_dir.iterdir()):
            if not skill.is_symlink():
                continue
            link_target = str(skill.readlink())
            if _is_toolkit_link(link_target):
                skill.unlink()
                removed += 1
        if removed > 0:
            print(f"  Removed: {removed} skill symlink(s)")
        # Remove the skills dir if it is now empty
        try:
            skills_dir.rmdir()
            print("  Removed: skills/ (empty)")
        except OSError:
            pass  # Not empty -- user has custom skills

    # Remove toolkit hooks from hooks.json (or remove legacy symlink)
    hooks_file = claude_dir / "hooks.json"
    if hooks_file.is_symlink():
        hooks_file.unlink()
        print("  Removed: hooks.json (legacy symlink)")
    elif hooks_file.is_file():
        content = hooks_file.read_text(encoding="utf-8")
        if '"_source"' in content and '"ai-toolkit"' in content:
            merge_hooks = toolkit_dir / "scripts" / "merge-hooks.py"
            subprocess.run(
                ["python3", str(merge_hooks), "strip", str(hooks_file)],
                check=True,
            )
            if hooks_file.is_file():
                print("  Stripped: hooks.json (toolkit entries removed, user hooks preserved)")
            else:
                print("  Removed: hooks.json (no user hooks remaining)")

    # Remove marker-injected content from constitution.md, ARCHITECTURE.md
    for item in ("constitution.md", "ARCHITECTURE.md"):
        target = claude_dir / item
        if target.is_symlink():
            target.unlink()
            print(f"  Removed: {item} (legacy symlink)")
        elif target.is_file():
            content = target.read_text(encoding="utf-8")
            if "<!-- TOOLKIT:" in content:
                remaining = _strip_all_toolkit_markers(target)
                if remaining and remaining.strip():
                    target.write_text(remaining + "\n", encoding="utf-8")
                    print(f"  Stripped: {item} (toolkit content removed, user content preserved)")
                else:
                    target.unlink()
                    print(f"  Removed: {item} (no user content remaining)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    force = False
    target_dir = Path.home()

    for arg in sys.argv[1:]:
        if arg in ("--yes", "-y"):
            force = True
        else:
            target_dir = Path(arg)

    claude_dir = target_dir / ".claude"

    if not claude_dir.is_dir():
        print(f"Error: No .claude/ directory found in {target_dir}")
        sys.exit(1)

    print("AI Toolkit Uninstaller")
    print("==========================")
    print(f"Target: {claude_dir}")
    print()

    # -- Count components to remove ---
    components = discover_components(claude_dir)

    for desc, _ in components:
        print(f"  {desc}")

    if not components:
        print("No toolkit components found. Nothing to remove.")
        sys.exit(0)

    print()
    print(f"Found {len(components)} toolkit component(s).")
    print("Note: ~/.claude/CLAUDE.md and settings.local.json are NOT removed.")
    print()

    # -- Confirm ---
    if not force:
        try:
            response = input("Remove these components? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            sys.exit(0)
        if response not in ("y", "yes"):
            print("Cancelled.")
            sys.exit(0)

    # -- Remove ---
    remove_components(claude_dir)

    print()
    print("Toolkit components removed from ~/.claude/ successfully.")
    print(f"{Path.home()}/.claude/CLAUDE.md preserved (contains your global rules).")
    print()
    print("To reinstall: npm install -g @softspark/ai-toolkit && ai-toolkit install")


if __name__ == "__main__":
    main()
