#!/usr/bin/env python3
"""Mirror the ai-toolkit skill catalogue into Codex ``.agents/skills/``.

OpenAI Codex CLI discovers Agent Skills from ``.agents/skills/`` in the
repository tree, plus user/admin/system skill locations. Unlike the Augment
and Gemini pointer pattern, Codex benefits from having the full skill catalog
on disk, so this generator syncs every skill in ``app/skills/`` into
``<target-dir>/.agents/skills/<name>/``.

The mirror is **opt-in**: ``enable_codex_skills=False`` is the default.
Bucket 4 wires a ``--codex-skills`` CLI flag that toggles this on.

Implementation:
  * Native Codex-compatible skills are symlinked to canonical ``app/skills``.
  * Skills that use Claude-only delegation tools are rendered as Codex
    wrappers through ``codex_skill_adapter.sync_codex_skill``.
  * Skip ``_lib`` and any dotfile directories under ``app/skills/``.
  * Remove stale generated wrappers and broken managed symlinks.
  * Preserve user-authored entries in ``.agents/skills/`` that are not managed
    by ai-toolkit.

Idempotent on rerun.

Usage:
  python3 scripts/generate_codex_skills.py [target-dir]

By default the CLI entrypoint also requires ``--enable`` to write anything,
keeping the opt-in default enforced even when invoked directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_skill_adapter import cleanup_codex_skills, sync_codex_skill
from emission import skills_dir


# ---------------------------------------------------------------------------
# Source skill discovery
# ---------------------------------------------------------------------------

def _iter_source_skills() -> list[Path]:
    """Return sorted list of source skill directories in ``app/skills/``.

    Skills starting with ``_`` (library internals) or ``.`` are skipped.
    Only directories containing a top-level ``SKILL.md`` are returned.
    """
    if not skills_dir.is_dir():
        return []
    entries: list[Path] = []
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("_") or entry.name.startswith("."):
            continue
        if not (entry / "SKILL.md").is_file():
            continue
        entries.append(entry)
    return entries


# ---------------------------------------------------------------------------
# Mirror operations
# ---------------------------------------------------------------------------

def _count_entries(codex_skills_dir: Path) -> int:
    """Count top-level skill entries after sync."""
    if not codex_skills_dir.is_dir():
        return 0
    return sum(1 for entry in codex_skills_dir.iterdir() if entry.is_dir() or entry.is_symlink())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate(target_dir: Path, enable_codex_skills: bool = False) -> None:
    """Mirror ``app/skills/`` into ``<target_dir>/.agents/skills/``.

    Args:
      target_dir: Project root where ``.agents/skills/`` is written.
      enable_codex_skills: Opt-in flag. Defaults to ``False`` (no-op).

    Contract for Bucket 4 wiring::

        from scripts.generate_codex_skills import generate as gen_codex_skills
        gen_codex_skills(target_dir, enable_codex_skills=cli_flag)

    The ``--codex-skills`` CLI flag should propagate straight into
    ``enable_codex_skills``.
    """
    if not enable_codex_skills:
        return

    codex_skills_dir = target_dir / ".agents" / "skills"
    codex_skills_dir.mkdir(parents=True, exist_ok=True)

    sources = _iter_source_skills()

    linked = 0
    adapted = 0
    skipped = 0
    for skill in sources:
        mode = sync_codex_skill(skill, codex_skills_dir)
        if mode == "linked":
            linked += 1
        elif mode == "adapted":
            adapted += 1
        else:
            skipped += 1

    cleanup_codex_skills(codex_skills_dir, skills_dir)

    print(
        f"  Codex skill mirror: {_count_entries(codex_skills_dir)} skills "
        f"to .agents/skills/ ({linked} linked, {adapted} adapted, "
        f"{skipped} skipped)"
    )


def main() -> None:
    args = sys.argv[1:]
    enable = "--enable" in args
    positional = [a for a in args if not a.startswith("--")]
    target = Path(positional[0]) if positional else Path.cwd()
    generate(target, enable_codex_skills=enable)


if __name__ == "__main__":
    main()
