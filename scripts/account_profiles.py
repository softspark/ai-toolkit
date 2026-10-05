# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Shared account registry and directory-routing helpers."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

PROFILE_NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}\Z")


@dataclass
class Registry:
    default: str
    accounts: dict[str, str | None]
    projects: dict[str, str]

    def account(self, name: str) -> str | None:
        if name not in self.accounts:
            raise ValueError(f"Unknown account: {name}")
        return self.accounts[name]


def match_project(registry: Registry, directory: Path) -> tuple[str, str] | None:
    matches = [
        (Path(project).resolve(), account, project)
        for project, account in registry.projects.items()
        if directory.is_relative_to(Path(project).resolve())
    ]
    if not matches:
        return None
    _, account, project = max(matches, key=lambda match: len(match[0].parts))
    return account, project


def worktree_origin(directory: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=5, check=False,
            env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode:
        return None
    common = Path(result.stdout.strip())
    return common.parent.resolve() if common.is_absolute() and common.name == ".git" else None


def parse_run(args: list[str]) -> tuple[str | None, list[str]]:
    account = None
    if args and args[0] == "--account":
        if len(args) < 2 or not PROFILE_NAME.fullmatch(args[1]):
            raise ValueError("--account requires an account name")
        account, args = args[1], args[2:]
    elif args and args[0].startswith("--account="):
        account, args = args[0].split("=", 1)[1], args[1:]
    if args and args[0] == "--":
        args = args[1:]
    return account, args
