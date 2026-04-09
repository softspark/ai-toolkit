"""Detect project language from file markers and source file extensions."""
from __future__ import annotations

import json
from pathlib import Path


# Map file extensions to manifest module names.
# Only extensions that unambiguously identify a language are listed.
_EXT_TO_MODULE: dict[str, str] = {
    ".py": "rules-python",
    ".ts": "rules-typescript",
    ".tsx": "rules-typescript",
    ".go": "rules-golang",
    ".rs": "rules-rust",
    ".java": "rules-java",
    ".kt": "rules-kotlin",
    ".kts": "rules-kotlin",
    ".swift": "rules-swift",
    ".dart": "rules-dart",
    ".cs": "rules-csharp",
    ".php": "rules-php",
    ".cpp": "rules-cpp",
    ".cc": "rules-cpp",
    ".cxx": "rules-cpp",
    ".hpp": "rules-cpp",
    ".rb": "rules-ruby",
}

# Directories that should never be scanned (dependency dirs, build output, etc.)
_SKIP_DIRS = frozenset({
    "node_modules", ".git", "__pycache__", "venv", ".venv", "env",
    "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
    "vendor", "target", ".next", ".nuxt", "coverage",
})


def _load_manifest_modules(toolkit_dir: Path) -> dict:
    """Load the modules section from manifest.json."""
    manifest_path = toolkit_dir / "manifest.json"
    if not manifest_path.is_file():
        return {}
    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("modules", {})


def _glob_matches(project_dir: Path, pattern: str) -> bool:
    """Check if a glob pattern matches any file in the project directory.

    Only checks the top-level directory (no recursive descent)
    to keep detection fast and predictable.
    """
    return any(project_dir.glob(pattern))


def _detect_by_extensions(project_dir: Path) -> set[str]:
    """Scan source files (top-level + 1 level deep) and return detected modules.

    Skips dependency/build directories for speed. Stops scanning for a
    given extension once one match is found.
    """
    found: set[str] = set()
    seen_exts: set[str] = set()

    for child in project_dir.iterdir():
        if child.is_file():
            ext = child.suffix
            if ext in _EXT_TO_MODULE and ext not in seen_exts:
                seen_exts.add(ext)
                found.add(_EXT_TO_MODULE[ext])
        elif child.is_dir() and child.name not in _SKIP_DIRS:
            for grandchild in child.iterdir():
                if grandchild.is_file():
                    ext = grandchild.suffix
                    if ext in _EXT_TO_MODULE and ext not in seen_exts:
                        seen_exts.add(ext)
                        found.add(_EXT_TO_MODULE[ext])

    return found


def detect_languages(project_dir: Path, toolkit_dir: Path) -> list[str]:
    """Return list of detected language module names.

    Two-phase detection:
    1. Marker files (``auto_detect`` in manifest.json) — config-level signals.
    2. Source file extensions (top-level + 1 deep) — actual code presence.

    Both phases contribute; duplicates are merged.

    Returns:
        Sorted list of matching module names, e.g.
        ``["rules-python", "rules-typescript"]``.
    """
    modules = _load_manifest_modules(toolkit_dir)
    detected: set[str] = set()

    # Phase 1: marker files from manifest
    for module_name, module_cfg in modules.items():
        markers = module_cfg.get("auto_detect")
        if not markers:
            continue

        for pattern in markers:
            if _glob_matches(project_dir, pattern):
                detected.add(module_name)
                break  # one match is enough for this module

    # Phase 2: source file extensions
    detected |= _detect_by_extensions(project_dir)

    return sorted(detected)
