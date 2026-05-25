#!/usr/bin/env python3
"""Generate a Windsurf skill pointer under ``.windsurf/skills/``."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skill_pointer import POINTER_SKILL_NAME, write_pointer_skill


def generate(target_dir: Path, *, emit_skill_pointer: bool = True,
             skill_root: str = ".windsurf/skills") -> None:
    if not emit_skill_pointer:
        return
    write_pointer_skill(target_dir, skill_root, "Windsurf")
    print(f"  Generated: {skill_root}/{POINTER_SKILL_NAME}/SKILL.md")


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    generate(target)


if __name__ == "__main__":
    main()
