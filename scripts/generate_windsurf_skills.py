#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate a Devin/Windsurf skill pointer.

Current Devin docs support both ``.devin/skills/`` and ``.windsurf/skills/``.
Keep one pointer under the latter so older Windsurf clients discover it too,
without registering duplicate skills. Pass an explicit ``skill_root`` for a
single alternate location (used by the HOME-scoped Windsurf install).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from secure_fs import OwnedEdit, apply_owned_edits, lexical_absolute
from skill_pointer import POINTER_SKILL_NAME, owned_pointer_edit, write_pointer_skill

DEFAULT_SKILL_ROOTS: tuple[str, ...] = (".windsurf/skills",)
GLOBAL_SKILL_ROOT = ".codeium/windsurf/skills"
# Pre-migration project pointer; install removes it, uninstall must too.
RETIRED_SKILL_ROOTS: tuple[str, ...] = (".devin/skills",)
# Editor directories pruned (only when empty) after a pointer is removed.
_EDITOR_ROOTS: dict[str, tuple[str, ...]] = {
    ".windsurf/skills": (".windsurf",),
    ".devin/skills": (".devin",),
    GLOBAL_SKILL_ROOT: (".codeium/windsurf", ".codeium"),
}


def generate(target_dir: Path, *, emit_skill_pointer: bool = True,
             skill_root: str | None = None) -> None:
    if not emit_skill_pointer:
        return
    roots = (skill_root,) if skill_root else DEFAULT_SKILL_ROOTS
    for root in roots:
        write_pointer_skill(target_dir, root, "Windsurf")
        print(f"  Generated: {root}/{POINTER_SKILL_NAME}/SKILL.md")


def _skill_roots(scope: str) -> tuple[str, ...]:
    local = DEFAULT_SKILL_ROOTS + RETIRED_SKILL_ROOTS
    if scope == "local":
        return local
    if scope == "global":
        return (GLOBAL_SKILL_ROOT,)
    if scope == "both":
        return local + (GLOBAL_SKILL_ROOT,)
    raise ValueError(f"Unknown Windsurf cleanup scope: {scope!r}")


def _apply(target_dir: Path, scope: str, *, dry_run: bool) -> int:
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Windsurf target directory: {target}")
    edits: dict[Path, OwnedEdit] = {}
    prune: list[Path] = []
    for root in _skill_roots(scope):
        pointer_dir = target / root / POINTER_SKILL_NAME
        edits[pointer_dir / "SKILL.md"] = owned_pointer_edit
        prune.extend((pointer_dir, pointer_dir.parent))
        prune.extend(target / editor for editor in _EDITOR_ROOTS[root])
    return apply_owned_edits(
        edits,
        target,
        label="Windsurf skill pointer",
        prune=tuple(prune),
        dry_run=dry_run,
    )


def discover(target_dir: Path, *, scope: str = "both") -> int:
    """Count managed Windsurf/Devin skill catalogue pointers."""
    return _apply(target_dir, scope, dry_run=True)


def cleanup(target_dir: Path, *, scope: str = "both") -> int:
    """Remove managed Windsurf/Devin skill catalogue pointers.

    ``scope`` selects ``local`` (``.windsurf/skills`` plus the retired
    ``.devin/skills``), ``global`` (``.codeium/windsurf/skills``), or ``both``.
    Only a SKILL.md carrying the catalogue name and the ai-toolkit sentence is
    removed; directories are pruned only when empty. Returns the count removed.
    """
    return _apply(target_dir, scope, dry_run=False)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    generate(target)


if __name__ == "__main__":
    main()
