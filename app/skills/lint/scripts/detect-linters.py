#!/usr/bin/env python3
"""Detect available linters and build combined lint/format commands for a project.

Scans a project directory for Python, Node.js, PHP, Go, and Dart
configuration files, checks which linters are installed or configured,
and returns a JSON object with individual linter entries, a combined
check command, and available format commands.

Usage::

    python3 detect-linters.py [project_directory]
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from _lib.detect_utils import is_installed, read_json, read_text, run_detector


def detect(project_dir: Path) -> dict[str, Any]:
    """Detect linters configured or installed for the project."""
    linters: list[dict[str, Any]] = []
    format_commands: list[str] = []

    # Python: pyproject.toml
    pyproject = read_text(project_dir / "pyproject.toml")
    if pyproject or (project_dir / "setup.py").exists():
        py_linters: dict[str, dict[str, str | None]] = {
            "ruff": {"check": "ruff check .", "fix": "ruff check --fix .", "format": "ruff format ."},
            "flake8": {"check": "flake8 .", "fix": None, "format": None},
            "pylint": {"check": "pylint src/", "fix": None, "format": None},
            "mypy": {"check": "mypy .", "fix": None, "format": None},
            "black": {"check": "black --check .", "fix": None, "format": "black ."},
        }
        for name, cmds in py_linters.items():
            configured = pyproject and name in pyproject if pyproject else False
            installed = is_installed(name)
            if configured or installed:
                linters.append({"name": name, "language": "python", "installed": installed,
                                "configured": configured, "check_command": cmds["check"],
                                "fix_command": cmds["fix"]})
                if cmds.get("format"):
                    format_commands.append(cmds["format"])  # type: ignore[arg-type]

    # Node.js: package.json
    pkg = read_json(project_dir / "package.json")
    if pkg:
        dev_deps = {**pkg.get("devDependencies", {}), **pkg.get("dependencies", {})}
        node_linters: dict[str, dict[str, str | None]] = {
            "eslint": {"check": "npx eslint .", "fix": "npx eslint --fix ."},
            "prettier": {"check": "npx prettier --check .", "format": "npx prettier --write ."},
            "tsc": {"check": "npx tsc --noEmit", "fix": None},
        }
        for name, cmds in node_linters.items():
            in_deps = name in dev_deps or (name == "tsc" and "typescript" in dev_deps)
            installed = is_installed(f"npx {name}") if name != "tsc" else is_installed("npx tsc")
            if in_deps:
                linters.append({"name": name, "language": "javascript/typescript",
                                "installed": True, "configured": in_deps,
                                "check_command": cmds["check"], "fix_command": cmds.get("fix")})
                if cmds.get("format"):
                    format_commands.append(cmds["format"])  # type: ignore[arg-type]

    # PHP: composer.json
    composer = read_json(project_dir / "composer.json")
    if composer:
        require_dev: dict[str, str] = composer.get("require-dev", {})
        php_linters: dict[str, dict[str, str]] = {
            "phpstan": {"check": "./vendor/bin/phpstan analyse", "pkg": "phpstan/phpstan"},
            "psalm": {"check": "./vendor/bin/psalm", "pkg": "vimeo/psalm"},
            "phpcs": {"check": "./vendor/bin/phpcs", "pkg": "squizlabs/php_codesniffer"},
        }
        for name, info in php_linters.items():
            in_deps = any(info["pkg"] in k for k in require_dev)
            if in_deps:
                linters.append({"name": name, "language": "php", "installed": True,
                                "configured": True, "check_command": info["check"], "fix_command": None})

    # Go: .golangci.yml
    if (project_dir / "go.mod").exists():
        go_lint: dict[str, str | None] = {"check": "golangci-lint run", "fix": None}
        configured = (project_dir / ".golangci.yml").exists() or (project_dir / ".golangci.yaml").exists()
        installed = is_installed("golangci-lint")
        if configured or installed:
            linters.append({"name": "golangci-lint", "language": "go", "installed": installed,
                            "configured": configured, "check_command": go_lint["check"], "fix_command": None})
        linters.append({"name": "go-vet", "language": "go", "installed": True,
                        "configured": True, "check_command": "go vet ./...", "fix_command": None})

    # Dart: pubspec.yaml
    if (project_dir / "pubspec.yaml").exists():
        linters.append({"name": "dart-analyze", "language": "dart", "installed": is_installed("dart"),
                        "configured": True, "check_command": "dart analyze", "fix_command": "dart fix --apply"})

    # Build combined command
    check_parts = [l["check_command"] for l in linters if l.get("installed") and l.get("check_command")]
    combined = " && ".join(check_parts) if check_parts else None

    return {
        "linters": linters,
        "combined_command": combined,
        "format_commands": format_commands,
        "linter_count": len(linters),
        "installed_count": sum(1 for l in linters if l.get("installed")),
    }


if __name__ == "__main__":
    run_detector(detect)
