#!/usr/bin/env python3
"""CLI for managing the ai-toolkit project registry.

Usage:
    ai-toolkit projects                — List all registered projects
    ai-toolkit projects --prune        — Remove stale (deleted) projects
    ai-toolkit projects remove <path>  — Unregister a specific project

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from install_steps.project_registry import (
    list_projects,
    prune_stale,
    unregister_project,
)


def main() -> None:
    args = sys.argv[1:]

    if not args or args == []:
        cmd_list()
    elif args[0] == "--prune":
        cmd_prune()
    elif args[0] == "remove" and len(args) >= 2:
        cmd_remove(args[1])
    elif args[0] in ("--help", "-h", "help"):
        cmd_help()
    else:
        print(f"Unknown: {' '.join(args)}", file=sys.stderr)
        cmd_help()
        sys.exit(1)


def cmd_list() -> None:
    """List all registered projects."""
    projects = list_projects()

    if not projects:
        print("  No registered projects.")
        print("  Run 'ai-toolkit install --local' in a project to register it.")
        return

    print(f"  Registered projects ({len(projects)}):")
    print()

    for p in projects:
        path_short = p["path"].replace(str(Path.home()), "~")
        status = "✓" if p["exists"] else "✗ MISSING"
        profile = p.get("profile", "")
        extends = p.get("extends", "")
        updated = p.get("last_updated", "")

        print(f"  {status}  {path_short}")
        details = []
        if profile:
            details.append(f"profile: {profile}")
        if extends:
            details.append(f"extends: {extends}")
        if updated:
            details.append(f"updated: {updated}")
        if details:
            print(f"        {' | '.join(details)}")

    stale = [p for p in projects if not p["exists"]]
    if stale:
        print()
        print(f"  {len(stale)} stale project(s). Run 'ai-toolkit projects --prune' to clean up.")


def cmd_prune() -> None:
    """Remove stale projects."""
    pruned = prune_stale()
    if pruned:
        for p in pruned:
            path_short = p.replace(str(Path.home()), "~")
            print(f"  Pruned: {path_short}")
        print(f"  Removed {len(pruned)} stale project(s).")
    else:
        print("  No stale projects found.")


def cmd_remove(project_path: str) -> None:
    """Unregister a specific project."""
    resolved = Path(project_path).resolve()
    if unregister_project(resolved):
        path_short = str(resolved).replace(str(Path.home()), "~")
        print(f"  Removed: {path_short}")
    else:
        print(f"  Not found in registry: {project_path}")
        sys.exit(1)


def cmd_help() -> None:
    print("Usage: ai-toolkit projects [command]")
    print()
    print("Commands:")
    print("  (none)          List all registered projects")
    print("  --prune         Remove projects whose directories no longer exist")
    print("  remove <path>   Unregister a specific project")


if __name__ == "__main__":
    main()
