"""Detect project language from file markers in the manifest."""
from __future__ import annotations

import json
from pathlib import Path


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


def detect_languages(project_dir: Path, toolkit_dir: Path) -> list[str]:
    """Return list of detected language module names.

    Scans ``project_dir`` for marker files defined in each module's
    ``auto_detect`` list inside ``manifest.json``.

    Returns:
        Sorted list of matching module names, e.g.
        ``["rules-python", "rules-typescript"]``.
    """
    modules = _load_manifest_modules(toolkit_dir)
    detected: list[str] = []

    for module_name, module_cfg in modules.items():
        markers = module_cfg.get("auto_detect")
        if not markers:
            continue

        for pattern in markers:
            if _glob_matches(project_dir, pattern):
                detected.append(module_name)
                break  # one match is enough for this module

    return sorted(detected)
