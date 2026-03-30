#!/usr/bin/env python3
"""Health check script for common services.

Probes Docker services, an HTTP health endpoint, disk usage, and
available memory. Returns a JSON object with status information for
each detected subsystem.

Usage::

    python3 health_check.py [service-url]
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command, capturing output as text. Never raises."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )


def _command_exists(name: str) -> bool:
    """Return True if *name* is found on PATH."""
    return shutil.which(name) is not None


def _check_docker() -> dict[str, Any] | None:
    """Return Docker service info, or None if Docker is unavailable."""
    if not _command_exists("docker"):
        return None
    result = _run(["docker", "compose", "ps", "--format", "json"])
    if result.returncode != 0:
        return None
    services: list[dict[str, str]] = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            svc = json.loads(line)
            services.append({
                "name": svc.get("Service", ""),
                "state": svc.get("State", ""),
            })
        except json.JSONDecodeError:
            continue
    if not services:
        return None
    return {"status": "running", "services": services}


def _check_http(url: str) -> dict[str, Any] | None:
    """Probe *url*/health via curl and return status info."""
    if not _command_exists("curl"):
        return None
    health_url = f"{url}/health"

    # Status code
    code_result = _run([
        "curl", "-sf", "-o", "/dev/null", "-w", "%{http_code}", health_url,
    ])
    status_code = int(code_result.stdout.strip()) if code_result.stdout.strip().isdigit() else 0

    # Response time
    time_result = _run([
        "curl", "-sf", "-o", "/dev/null", "-w", "%{time_total}", health_url,
    ])
    try:
        response_time_s = float(time_result.stdout.strip())
    except (ValueError, TypeError):
        response_time_s = 0.0
    response_time_ms = round(response_time_s * 1000, 2)

    return {
        "url": health_url,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
    }


def _check_disk() -> dict[str, Any]:
    """Return disk usage percentage for the current working directory."""
    try:
        usage = shutil.disk_usage(os.getcwd())
        percent = round(usage.used / usage.total * 100) if usage.total else 0
    except OSError:
        percent = 0
    return {"usage_percent": percent}


def _check_memory() -> dict[str, Any]:
    """Return available memory info, platform-aware."""
    system = platform.system()
    if system == "Darwin":
        result = _run(["vm_stat"])
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "Pages free" in line:
                    parts = line.split()
                    # Last token is the number, possibly with a trailing period
                    raw = parts[-1].rstrip(".")
                    try:
                        return {"free_pages": int(raw)}
                    except ValueError:
                        pass
        return {"free_pages": 0}

    if system == "Linux":
        try:
            with open("/proc/meminfo", "r") as fh:
                for line in fh:
                    if line.startswith("MemAvailable"):
                        parts = line.split()
                        try:
                            return {"available_kb": int(parts[1])}
                        except (IndexError, ValueError):
                            pass
        except OSError:
            pass
        return {"available_kb": 0}

    return {}


def main() -> None:
    """Entry point: run all checks and print JSON to stdout."""
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    checks: dict[str, Any] = {}

    docker_info = _check_docker()
    if docker_info is not None:
        checks["docker"] = docker_info

    http_info = _check_http(url)
    if http_info is not None:
        checks["http"] = http_info

    checks["disk"] = _check_disk()
    checks["memory"] = _check_memory()

    output = {
        "timestamp": now,
        "checks": checks,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
