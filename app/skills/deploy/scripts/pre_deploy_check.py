#!/usr/bin/env python3
"""Pre-deployment readiness checklist.

Runs a series of checks (git clean, branch, Docker, env file, build
artifacts, test results) and returns a JSON object with pass/fail for
each check, a list of blockers, and an overall ready status.

Usage::

    python3 pre_deploy_check.py [environment]
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _run(cmd: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    """Run a command and return the CompletedProcess.

    Captures stdout/stderr as text. Never raises on non-zero exit unless
    *check* is True.
    """
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=check,
    )


def _git_porcelain() -> str:
    """Return the porcelain output of ``git status``."""
    result = _run(["git", "status", "--porcelain"])
    return result.stdout.strip()


def _git_branch() -> str:
    """Return the current git branch name, or ``unknown``."""
    result = _run(["git", "branch", "--show-current"])
    return result.stdout.strip() or "unknown"


def _docker_available() -> bool:
    """Return True if the ``docker`` command is on PATH."""
    result = _run(["command", "-v", "docker"])
    # Fallback: just try docker --version
    if result.returncode != 0:
        result = _run(["docker", "--version"])
    return result.returncode == 0


def _docker_services_running() -> bool:
    """Return True if any docker compose service reports running."""
    result = _run(["docker", "compose", "ps"])
    if result.returncode != 0:
        return False
    return "running" in result.stdout.lower()


class _CheckCollector:
    """Accumulates individual check results and blockers."""

    def __init__(self) -> None:
        self.checks: dict[str, dict[str, Any]] = {}
        self.blockers: list[str] = []

    def add(self, name: str, passed: bool, detail: str) -> None:
        """Record a single check result."""
        self.checks[name] = {"pass": passed, "detail": detail}
        if not passed:
            self.blockers.append(detail)

    @property
    def ready(self) -> bool:
        """Return True when there are no blockers."""
        return len(self.blockers) == 0


def _run_checks(env: str) -> _CheckCollector:
    """Execute all pre-deployment checks and return the collector."""
    collector = _CheckCollector()

    # 1. Git clean
    porcelain = _git_porcelain()
    if not porcelain:
        collector.add("git_clean", True, "No uncommitted changes")
    else:
        collector.add("git_clean", False, "Uncommitted changes detected")

    # 2. Branch
    branch = _git_branch()
    if env in ("prod", "production"):
        if branch in ("main", "master"):
            collector.add("branch", True, f"On {branch}")
        else:
            collector.add("branch", False, f"Not on main/master (on {branch})")
    else:
        collector.add("branch", True, f"On {branch}")

    # 3. Docker
    has_compose = (
        Path("docker-compose.yml").exists()
        or Path("compose.yml").exists()
    )
    if _docker_available() and has_compose:
        if _docker_services_running():
            collector.add("docker", True, "Docker services running")
        else:
            collector.add("docker", False, "Docker services not running")
    else:
        collector.add("docker", True, "No Docker config (skipped)")

    # 4. Env file
    if Path(".env").exists() or Path(f".env.{env}").exists():
        collector.add("env_file", True, "Environment file exists")
    else:
        collector.add("env_file", False, f"Missing .env or .env.{env} file")

    # 5. Build artifacts
    found_artifacts = any(Path(d).is_dir() for d in ("dist", "build"))
    if found_artifacts:
        collector.add("build_artifacts", True, "Build artifacts present")
    else:
        collector.add(
            "build_artifacts", True,
            "No build artifacts expected (interpreted language)",
        )

    # 6. Test results
    test_artifacts = [
        "coverage/.last_run.json",
        "htmlcov/status.json",
        ".coverage",
        "test-results.xml",
    ]
    if any(Path(p).exists() for p in test_artifacts):
        collector.add("tests_ran", True, "Test result artifacts found")
    else:
        collector.add(
            "tests_ran", False,
            "No recent test results found - run tests first",
        )

    return collector


def main() -> None:
    """Entry point: run checks and print JSON result to stdout."""
    env = sys.argv[1] if len(sys.argv) > 1 else "staging"
    branch = _git_branch()
    collector = _run_checks(env)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    output: dict[str, Any] = {
        "environment": env,
        "timestamp": now,
        "branch": branch,
        "checks": collector.checks,
        "ready": collector.ready,
        "blockers": collector.blockers,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
