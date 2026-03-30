"""Shared utilities for skill detection scripts.

Provides common constants, file helpers, and a standard main() wrapper
used by detect-linters.py, detect-build.py, detect-runner.py, ci-detect.py,
and other project-scanning scripts under app/skills/*/scripts/.

All functions are stdlib-only.

Usage::

    from _lib.detect_utils import read_json, read_text, IGNORE_DIRS, run_detector
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

# Directories to skip during project walks
IGNORE_DIRS: frozenset[str] = frozenset({
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", "vendor",
})

# Common project markers → project type
PROJECT_MARKERS: dict[str, list[str]] = {
    "python": ["pyproject.toml", "setup.py", "requirements.txt"],
    "node": ["package.json"],
    "flutter": ["pubspec.yaml"],
    "go": ["go.mod"],
    "rust": ["Cargo.toml"],
    "php": ["composer.json"],
    "docker": ["Dockerfile"],
}


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

def read_json(path: Path) -> dict[str, Any] | None:
    """Read and parse a JSON file, returning None on failure."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def read_text(path: Path) -> str | None:
    """Read a text file, returning None when it does not exist."""
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return None


def is_installed(binary: str) -> bool:
    """Check whether a binary is available on PATH."""
    return shutil.which(binary) is not None


# ---------------------------------------------------------------------------
# Project detection
# ---------------------------------------------------------------------------

def detect_project_type(project_dir: Path) -> str | None:
    """Detect project type from well-known marker files."""
    for ptype, markers in PROJECT_MARKERS.items():
        for marker in markers:
            if (project_dir / marker).exists():
                return ptype
    return None


def count_files(root: Path, patterns: list[str]) -> int:
    """Walk root and count files matching any regex pattern.

    Directories in IGNORE_DIRS are pruned.
    """
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            for pat in patterns:
                if re.search(pat, f):
                    count += 1
                    break
    return count


def parse_makefile_targets(project_dir: Path) -> list[str]:
    """Extract non-hidden target names from a Makefile."""
    content = read_text(project_dir / "Makefile")
    if not content:
        return []
    targets: list[str] = []
    for line in content.split("\n"):
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:", line)
        if m and not m.group(1).startswith("."):
            targets.append(m.group(1))
    return targets


# ---------------------------------------------------------------------------
# Standard main() wrapper
# ---------------------------------------------------------------------------

def run_detector(
    detect_fn: Any,
    *,
    extra_args: bool = False,
) -> None:
    """Standard entry point wrapper for detection scripts.

    Parses argv for project directory, calls detect_fn(project_dir, ...),
    and prints JSON result to stdout. Handles errors uniformly.

    Args:
        detect_fn: Callable(project_dir: Path, ...) -> dict
        extra_args: If True, passes remaining argv items to detect_fn
    """
    project_dir = Path.cwd()
    extra: list[str] = []

    for arg in sys.argv[1:]:
        if os.path.isdir(arg):
            project_dir = Path(arg).resolve()
        else:
            extra.append(arg)

    if not project_dir.is_dir():
        print(json.dumps({"error": f"Not a directory: {project_dir}"}))
        sys.exit(1)

    try:
        if extra_args and extra:
            result = detect_fn(project_dir, *extra)
        else:
            result = detect_fn(project_dir)
        result["project_dir"] = str(project_dir)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
