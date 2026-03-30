#!/usr/bin/env python3
"""Detect build system, package manager, and available build/dev/docker commands.

Scans a project directory for Node.js, Python, Flutter/Dart, Go, Rust,
PHP, and Makefile-based projects. Returns a JSON object describing the
project type, package manager, suggested build and dev commands, Docker
build command (if applicable), available Makefile targets, and the
configuration file used for detection.

Usage::

    python3 detect-build.py [project_directory] [dev|prod|docker]
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from _lib.detect_utils import parse_makefile_targets, read_json, read_text, run_detector


def detect_package_manager(project_dir: Path) -> str | None:
    """Detect the Node.js package manager from lock files."""
    checks: list[tuple[str, str]] = [
        ("bun.lockb", "bun"),
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("package-lock.json", "npm"),
    ]
    for lockfile, manager in checks:
        if (project_dir / lockfile).exists():
            return manager
    if (project_dir / "package.json").exists():
        return "npm"
    return None


def detect(project_dir: Path, target: str | None = None) -> dict[str, Any]:
    """Detect the build system for the given project directory."""
    result: dict[str, Any] = {
        "project_type": None, "package_manager": None,
        "build_command": None, "dev_command": None,
        "docker_build": None, "makefile_targets": [],
        "scripts": {}, "detected_from": None,
    }

    result["makefile_targets"] = parse_makefile_targets(project_dir)

    # Docker detection
    has_dockerfile = (project_dir / "Dockerfile").exists()
    has_compose = (project_dir / "docker-compose.yml").exists() or (project_dir / "docker-compose.yaml").exists() or (project_dir / "compose.yml").exists()
    if has_dockerfile or has_compose:
        if has_compose:
            result["docker_build"] = "docker compose build"
        elif has_dockerfile:
            result["docker_build"] = "docker build -t app ."

    # Node.js
    pkg = read_json(project_dir / "package.json")
    if pkg:
        pm = detect_package_manager(project_dir)
        result["project_type"] = "node"
        result["package_manager"] = pm
        result["detected_from"] = "package.json"
        scripts = pkg.get("scripts", {})
        result["scripts"] = {k: v for k, v in scripts.items() if k in
                             {"build", "dev", "start", "preview", "lint", "test", "typecheck"}}
        run_pfx = f"{pm} run" if pm in ("npm", "pnpm") else (f"{pm} run" if pm == "yarn" else f"{pm} run")
        if pm == "bun":
            run_pfx = "bun run"
        result["build_command"] = f"{run_pfx} build" if "build" in scripts else None
        result["dev_command"] = f"{run_pfx} dev" if "dev" in scripts else (f"{run_pfx} start" if "start" in scripts else None)
        if target == "docker" and result["docker_build"]:
            result["build_command"] = result["docker_build"]
        return result

    # Python
    pyproject = read_text(project_dir / "pyproject.toml")
    if pyproject or (project_dir / "setup.py").exists():
        result["project_type"] = "python"
        result["detected_from"] = "pyproject.toml" if pyproject else "setup.py"
        if pyproject and "poetry" in pyproject:
            result["package_manager"] = "poetry"
            result["build_command"] = "poetry build"
            result["dev_command"] = "poetry run python -m app"
        elif pyproject and "hatchling" in pyproject:
            result["package_manager"] = "hatch"
            result["build_command"] = "hatch build"
        else:
            result["package_manager"] = "pip"
            result["build_command"] = "pip install -e ."
        if target == "docker" and result["docker_build"]:
            result["build_command"] = result["docker_build"]
        return result

    # Flutter/Dart
    if (project_dir / "pubspec.yaml").exists():
        result.update(project_type="flutter", package_manager="pub",
                      detected_from="pubspec.yaml",
                      build_command="flutter build", dev_command="flutter run")
        return result

    # Go
    if (project_dir / "go.mod").exists():
        result.update(project_type="go", package_manager="go",
                      detected_from="go.mod",
                      build_command="go build ./...", dev_command="go run .")
        return result

    # Rust
    if (project_dir / "Cargo.toml").exists():
        result.update(project_type="rust", package_manager="cargo",
                      detected_from="Cargo.toml",
                      build_command="cargo build --release", dev_command="cargo run")
        return result

    # PHP
    if (project_dir / "composer.json").exists():
        result.update(project_type="php", package_manager="composer",
                      detected_from="composer.json",
                      build_command="composer install --no-dev --optimize-autoloader",
                      dev_command="composer install && php -S localhost:8000 -t public/")
        return result

    # Fallback: Makefile-only project
    if result["makefile_targets"]:
        result["project_type"] = "makefile"
        result["detected_from"] = "Makefile"
        if "build" in result["makefile_targets"]:
            result["build_command"] = "make build"
        if "dev" in result["makefile_targets"]:
            result["dev_command"] = "make dev"
        return result

    result["project_type"] = "unknown"
    return result


if __name__ == "__main__":
    # Handle target arg (dev/prod/docker) specially
    target: str | None = None
    clean_argv = [sys.argv[0]]
    for arg in sys.argv[1:]:
        if arg in ("dev", "prod", "docker"):
            target = arg
        else:
            clean_argv.append(arg)
    sys.argv = clean_argv
    run_detector(lambda d: detect(d, target))
