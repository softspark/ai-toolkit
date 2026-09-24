#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate a Cursor skill pointer under ``.cursor/skills/``."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from secure_fs import apply_owned_edits, lexical_absolute
from skill_pointer import POINTER_SKILL_NAME, owned_pointer_edit, write_pointer_skill

SKILL_ROOT = ".cursor/skills"


def generate(target_dir: Path, *, emit_skill_pointer: bool = True) -> None:
    if not emit_skill_pointer:
        return
    write_pointer_skill(target_dir, SKILL_ROOT, "Cursor")
    print(f"  Generated: {SKILL_ROOT}/{POINTER_SKILL_NAME}/SKILL.md")


def _apply(target_dir: Path, *, dry_run: bool) -> int:
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Cursor target directory: {target}")
    pointer_dir = target / SKILL_ROOT / POINTER_SKILL_NAME
    return apply_owned_edits(
        {pointer_dir / "SKILL.md": owned_pointer_edit},
        target,
        label="Cursor skill pointer",
        prune=(pointer_dir, pointer_dir.parent, target / ".cursor"),
        dry_run=dry_run,
    )


def discover(target_dir: Path) -> int:
    """Return 1 when the managed Cursor skill catalogue pointer is present."""
    return _apply(target_dir, dry_run=True)


def cleanup(target_dir: Path) -> int:
    """Remove only the managed Cursor catalogue pointer; returns 1 or 0."""
    return _apply(target_dir, dry_run=False)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    generate(target)


if __name__ == "__main__":
    main()
