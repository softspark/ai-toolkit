#!/usr/bin/env python3
"""Test cohesion resolver for ai-toolkit hooks.

Reads a project-local or toolkit-default test-cohesion-map and answers:
"given these changed paths, what tests should run?"

Map format (JSON array of rules):
    [
        {
            "match": "app/hooks/*.sh",           # glob, repo-rooted
            "tests": ["tests/test_hooks.bats"],
            "runner": "bats",                    # bats|pytest|vitest|jest|custom
            "command": null                      # optional: full command override
        }
    ]

Lookup order:
    1. $PWD/.claude/test-cohesion-map.json (project override)
    2. $TOOLKIT_DIR/app/hooks/test-cohesion-map.json (toolkit default)

Usage:
    test_cohesion.py resolve --changed-paths PATH [PATH ...] [--repo-root DIR]
        Prints one shell command per line. Exit 0 if any test commands resolved,
        1 if no rules matched (so hook can skip silently).
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from pathlib import Path

DEFAULT_RUNNERS: dict[str, str] = {
    "bats": "bats --no-parallelize-within-files",
    "pytest": "pytest -x",
    "vitest": "npx vitest run",
    "jest": "npx jest --bail",
}


def _toolkit_dir() -> Path | None:
    env = os.environ.get("AI_TOOLKIT_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    # Walk up from this script: scripts/ -> repo root
    here = Path(__file__).resolve()
    candidate = here.parent.parent
    if (candidate / "app" / "hooks.json").is_file():
        return candidate
    return None


def _load_map(repo_root: Path) -> list[dict]:
    candidates = [repo_root / ".claude" / "test-cohesion-map.json"]
    tk = _toolkit_dir()
    if tk:
        candidates.append(tk / "hooks" / "test-cohesion-map.json")
        candidates.append(tk / "app" / "hooks" / "test-cohesion-map.json")
    for path in candidates:
        if not path.is_file():
            continue
        try:
            with path.open() as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, list):
            return data
    return []


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(
        os.path.basename(path), pattern
    )


def _relpath(repo_root: Path, abs_path: str) -> str:
    try:
        return str(Path(abs_path).resolve().relative_to(repo_root.resolve()))
    except (ValueError, OSError):
        return abs_path


def resolve(repo_root: Path, changed: list[str]) -> list[str]:
    rules = _load_map(repo_root)
    if not rules:
        return []
    # First-match-wins per changed path. List specific rules before broad
    # globs in the map to control scope.
    buckets: dict[tuple[str, str | None], set[str]] = {}
    for raw in changed:
        rel = _relpath(repo_root, raw)
        for rule in rules:
            pattern = rule.get("match")
            if not pattern or not _matches(rel, pattern):
                continue
            runner = rule.get("runner", "bats")
            command_override = rule.get("command")
            key = (runner, command_override)
            buckets.setdefault(key, set()).update(rule.get("tests", []))
            break  # first match wins for this path
    if not buckets:
        return []
    commands: list[str] = []
    for (runner, override), tests in buckets.items():
        if override:
            commands.append(override)
            continue
        base = DEFAULT_RUNNERS.get(runner, runner)
        commands.append(f"{base} {' '.join(sorted(tests))}".strip())
    return commands


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve cohesion test commands")
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("resolve")
    r.add_argument("--changed-paths", nargs="+", required=True)
    r.add_argument("--repo-root", default=os.getcwd())
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    commands = resolve(repo_root, args.changed_paths)
    for c in commands:
        print(c)
    return 0 if commands else 1


if __name__ == "__main__":
    sys.exit(main())
