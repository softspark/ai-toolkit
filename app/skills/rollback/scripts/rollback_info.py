#!/usr/bin/env python3
"""Gather rollback context: git state, migrations, docker services.

Detects the current git state, identifies the migration tool in use,
and lists running Docker Compose services. Returns a JSON object with
``git``, ``migrations``, and ``docker`` sections.

Usage::

    python3 rollback_info.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command, capturing output as text. Never raises."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )


def _git(args: list[str], default: str = "unknown") -> str:
    """Run a git sub-command and return stripped stdout, or *default*."""
    result = _run(["git"] + args)
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else default


def _git_info() -> dict[str, Any]:
    """Collect git state information."""
    current_commit = _git(["rev-parse", "HEAD"])
    previous_commit = _git(["rev-parse", "HEAD~1"])
    last_msg = _git(["log", "-1", "--pretty=%s"])
    branch = _git(["branch", "--show-current"])

    porcelain = _run(["git", "status", "--porcelain"])
    uncommitted = bool(porcelain.stdout.strip()) if porcelain.returncode == 0 else False

    # Determine main branch name
    main_branch = "main"
    verify = _run(["git", "rev-parse", "--verify", "origin/main"])
    if verify.returncode != 0:
        main_branch = "master"

    ahead_result = _run(["git", "rev-list", "--count", f"origin/{main_branch}..HEAD"])
    try:
        ahead = int(ahead_result.stdout.strip())
    except (ValueError, TypeError):
        ahead = 0

    return {
        "branch": branch,
        "current_commit": current_commit,
        "previous_commit": previous_commit,
        "last_commit_message": last_msg,
        f"commits_ahead_of_{main_branch}": ahead,
        "uncommitted_changes": uncommitted,
    }


def _migration_info() -> dict[str, Any]:
    """Detect migration tool and build rollback command."""
    tool = "none"
    pending: str = "unknown"
    rollback_cmd: str | None = None

    if Path("alembic.ini").exists():
        tool = "alembic"
        rollback_cmd = "alembic downgrade -1"
        if shutil.which("alembic") is not None:
            result = _run(["alembic", "heads"])
            if result.returncode == 0:
                head_count = len(
                    [line for line in result.stdout.strip().splitlines() if line.strip()]
                )
                pending = f"{head_count} pending head(s)"
    elif Path("prisma/schema.prisma").exists():
        tool = "prisma"
        rollback_cmd = "npx prisma migrate resolve --rolled-back <name>"
    elif Path("database/migrations").is_dir() and Path("artisan").exists():
        tool = "laravel"
        rollback_cmd = "php artisan migrate:rollback --step=1"
    elif Path("manage.py").exists():
        tool = "django"
        rollback_cmd = "python manage.py migrate <app> <previous_migration>"
    elif Path("drizzle.config.ts").exists() or Path("drizzle.config.js").exists():
        tool = "drizzle"
        rollback_cmd = "manual rollback required"

    return {
        "tool": tool,
        "pending": pending,
        "rollback_command": rollback_cmd,
    }


def _docker_info() -> dict[str, Any]:
    """Detect Docker Compose services."""
    services: list[dict[str, str]] = []
    running = False

    has_compose = (
        Path("docker-compose.yml").exists()
        or Path("compose.yml").exists()
    )
    if not (shutil.which("docker") and has_compose):
        return {"running": running, "services": services}

    result = _run([
        "docker", "compose", "ps",
        "--format", "{{.Service}}:{{.Image}}:{{.Status}}",
    ])
    if result.returncode == 0 and result.stdout.strip():
        running = True
        for line in result.stdout.strip().splitlines():
            parts = line.split(":", 2)
            if len(parts) >= 2:
                services.append({
                    "service": parts[0],
                    "image": parts[1],
                })

    return {"running": running, "services": services}


def main() -> None:
    """Entry point: gather rollback context and print JSON to stdout."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    output: dict[str, Any] = {
        "timestamp": now,
        "git": _git_info(),
        "migrations": _migration_info(),
        "docker": _docker_info(),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
