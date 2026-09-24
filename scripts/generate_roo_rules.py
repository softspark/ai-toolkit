#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate .roo/rules/*.md shared rules for Roo Code.

Roo Code reads shared rules from .roo/rules/*.md (applied to all modes).
The .roomodes JSON is still generated separately by generate_roo_modes.py.

Usage:
  python3 scripts/generate_roo_rules.py [target-dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dir_rules_shared import (
    STANDARD_RULES,
    build_language_rules,
    build_registered_rules,
    rule_scope,
    write_rules,
)
from secure_fs import OwnedEdit, apply_owned_edits, lexical_absolute


def generate(target_dir: Path, *,
             language_modules: list[str] | None = None,
             rules_dir: Path | None = None,
             output_root: Path | None = None) -> None:
    """Write Roo Code rule files.

    By default writes project-local ``target_dir/.roo/rules/*.md``. When
    ``output_root`` is provided, writes directly into that directory for
    documented global rules such as ``~/.roo/rules``.
    """
    rules = dict(STANDARD_RULES)
    rules.update(build_language_rules(language_modules))
    rules.update(build_registered_rules(rules_dir))
    root = output_root.parent if output_root is not None else target_dir
    subdir = output_root.name if output_root is not None else ".roo/rules"
    write_rules(root, rules, subdir)


def _cleanup_plan(
    target_dir: Path, output_root: Path | None
) -> tuple[Path, dict[Path, OwnedEdit], tuple[Path, ...]]:
    target = lexical_absolute(target_dir)
    rules_root = (
        lexical_absolute(output_root)
        if output_root is not None
        else target / ".roo" / "rules"
    )
    for path in (rules_root.parent, rules_root):
        if path.is_symlink():
            raise RuntimeError(f"Refusing symlinked Roo rules path: {path}")
    if not rules_root.is_dir():
        return target, {}, ()
    edits: dict[Path, OwnedEdit] = {
        path: lambda _content: None
        for path in sorted(rules_root.iterdir())
        if rule_scope(path.name) is not None
        and path.suffix == ".md"
        and path.is_file()
    }
    prune = tuple(p for p in (rules_root, rules_root.parent) if p != target)
    return target, edits, prune


def cleanup(target_dir: Path, *, output_root: Path | None = None) -> int:
    """Remove ``ai-toolkit-*`` Roo rule files and return how many were removed.

    Defaults to ``target_dir/.roo/rules``; pass the same ``output_root`` as
    :func:`generate` for the global ``~/.roo/rules``. User rules are untouched.
    """
    target, edits, prune = _cleanup_plan(target_dir, output_root)
    return apply_owned_edits(edits, target, label="Roo rule", prune=prune)


def discover(target_dir: Path, *, output_root: Path | None = None) -> int:
    """Count the files :func:`cleanup` would remove, without side effects."""
    target, edits, _ = _cleanup_plan(target_dir, output_root)
    return apply_owned_edits(edits, target, label="Roo rule", dry_run=True)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    from paths import RULES_DIR
    generate(target, rules_dir=RULES_DIR)


if __name__ == "__main__":
    main()
