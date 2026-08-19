#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate a Cline skill pointer under ``.cline/skills/``."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from secure_fs import (
    SecureDestination,
    SecureTransaction,
    lexical_absolute,
    nearest_existing_root,
    run_secure_transaction,
)
from skill_pointer import POINTER_SKILL_NAME, build_pointer_skill


def _is_managed(content: bytes | None) -> bool:
    if content is None:
        return False
    return (
        f"name: {POINTER_SKILL_NAME}".encode() in content
        and b"This workspace uses ai-toolkit with Cline." in content
    )


def _destination(target_dir: Path, skill_root: str) -> SecureDestination:
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Cline target directory: {target}")
    path = target / skill_root / POINTER_SKILL_NAME / "SKILL.md"
    return SecureDestination(path, nearest_existing_root(target), "Cline skill pointer")


def generate(target_dir: Path, *, emit_skill_pointer: bool = True,
             skill_root: str = ".cline/skills") -> None:
    if not emit_skill_pointer:
        return
    destination = _destination(target_dir, skill_root)

    def apply(transaction: SecureTransaction) -> None:
        current = transaction.initial_content(destination)
        if current is not None and not _is_managed(current):
            raise RuntimeError(f"Refusing user-owned Cline skill: {destination.path}")
        transaction.atomic_write(
            destination,
            build_pointer_skill("Cline").encode("utf-8"),
            0o644,
        )

    run_secure_transaction([destination], apply)
    print(f"  Generated: {skill_root}/{POINTER_SKILL_NAME}/SKILL.md")


def discover(target_dir: Path, *, skill_root: str = ".cline/skills") -> int:
    """Return one when the managed Cline catalogue pointer is present."""
    destination = _destination(target_dir, skill_root)
    transaction = SecureTransaction([destination])
    try:
        return int(_is_managed(transaction.initial_content(destination)))
    finally:
        transaction.close()


def cleanup(target_dir: Path, *, skill_root: str = ".cline/skills") -> int:
    """Remove only the managed Cline catalogue pointer."""
    destination = _destination(target_dir, skill_root)
    transaction = SecureTransaction([destination])
    try:
        if not _is_managed(transaction.initial_content(destination)):
            return 0
        transaction.materialize_parents()
        transaction.unlink(destination)
        return 1
    except BaseException:
        transaction.rollback()
        raise
    finally:
        transaction.close()


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    generate(target)


if __name__ == "__main__":
    main()
