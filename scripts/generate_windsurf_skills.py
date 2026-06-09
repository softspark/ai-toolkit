#!/usr/bin/env python3
"""Generate a Devin Desktop (formerly Windsurf) skill pointer.

Dual-emits under ``.devin/skills/`` (primary since the 2026-06-02 rebrand)
and ``.windsurf/skills/`` (legacy fallback). Pass an explicit ``skill_root``
to emit a single location instead (used for the ``~/.codeium/windsurf/``
global install path).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skill_pointer import POINTER_SKILL_NAME, write_pointer_skill

DEFAULT_SKILL_ROOTS: tuple[str, ...] = (".devin/skills", ".windsurf/skills")


def generate(target_dir: Path, *, emit_skill_pointer: bool = True,
             skill_root: str | None = None) -> None:
    if not emit_skill_pointer:
        return
    roots = (skill_root,) if skill_root else DEFAULT_SKILL_ROOTS
    for root in roots:
        write_pointer_skill(target_dir, root, "Windsurf")
        print(f"  Generated: {root}/{POINTER_SKILL_NAME}/SKILL.md")


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    generate(target)


if __name__ == "__main__":
    main()
