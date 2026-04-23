#!/usr/bin/env python3
"""Mirror the full ai-toolkit skill catalogue into ``.codex/skills/``.

OpenAI Codex CLI supports the Agent Skills standard at
``.codex/skills/<skill-name>/SKILL.md`` with optional supporting files
(scripts, references, assets) in the skill directory. Unlike the Augment
and Gemini pointer pattern, Codex benefits from having the full skill
content on disk, so this generator performs a **full mirror** of every
skill in ``app/skills/`` into ``<target-dir>/.codex/skills/<name>/``.

The mirror is **opt-in**: ``enable_codex_skills=False`` is the default.
Bucket 4 wires a ``--codex-skills`` CLI flag that toggles this on.

Implementation:
  * Prefer symlinks from ``.codex/skills/<name>`` to the canonical
    ``app/skills/<name>`` directory (atomic and cheap).
  * Fall back to a recursive copy when symlinks are unavailable (Windows
    without developer mode, hostile filesystems, etc.).
  * Skip ``_lib`` and any dotfile directories under ``app/skills/``.
  * Remove stale entries under ``.codex/skills/`` that no longer
    correspond to a source skill (cleanup on rerun).
  * Never touch user-authored entries in ``.codex/skills/`` that do not
    match a source skill name and are not our managed targets.

Idempotent on rerun.

Usage:
  python3 scripts/generate_codex_skills.py [target-dir]

By default the CLI entrypoint also requires ``--enable`` to write anything,
keeping the opt-in default enforced even when invoked directly.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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

def _remove_existing(target: Path) -> None:
    """Remove an existing file, symlink, or directory at ``target``.

    Uses ``lstat`` so symlinks are unlinked without following them.
    """
    if not target.exists() and not target.is_symlink():
        return
    if target.is_symlink() or target.is_file():
        target.unlink()
        return
    shutil.rmtree(target)


def _symlink_or_copy(source: Path, target: Path) -> str:
    """Create ``target`` as a symlink to ``source``; fall back to a copy.

    Returns ``"symlink"`` or ``"copy"`` indicating which strategy was used.
    """
    _remove_existing(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(source, target, target_is_directory=True)
        return "symlink"
    except (OSError, NotImplementedError):
        shutil.copytree(source, target, symlinks=False)
        return "copy"


def _cleanup_stale(codex_skills_dir: Path, live_names: set[str]) -> list[str]:
    """Remove managed entries under ``.codex/skills/`` that no longer map
    to a source skill. Returns the names removed.

    A managed entry is one whose directory name matches a historical
    source skill name pattern: it contains a ``SKILL.md`` either directly
    (copy) or via a symlink back into ``app/skills/``. User-authored
    entries that do not look managed are left alone.
    """
    if not codex_skills_dir.is_dir():
        return []
    removed: list[str] = []
    for entry in sorted(codex_skills_dir.iterdir()):
        if not entry.is_dir() and not entry.is_symlink():
            continue
        if entry.name in live_names:
            continue
        if entry.is_symlink():
            # Only remove symlinks that point inside our app/skills/ tree.
            try:
                resolved = entry.resolve()
            except OSError:
                continue
            try:
                resolved.relative_to(skills_dir.resolve())
            except ValueError:
                continue
            entry.unlink()
            removed.append(entry.name)
            continue
        # Copy mode: treat as managed only if a SKILL.md is present.
        if (entry / "SKILL.md").is_file():
            shutil.rmtree(entry)
            removed.append(entry.name)
    return removed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate(target_dir: Path, enable_codex_skills: bool = False) -> None:
    """Mirror ``app/skills/`` into ``<target_dir>/.codex/skills/``.

    Args:
      target_dir: Project root where ``.codex/skills/`` is written.
      enable_codex_skills: Opt-in flag. Defaults to ``False`` (no-op).

    Contract for Bucket 4 wiring::

        from scripts.generate_codex_skills import generate as gen_codex_skills
        gen_codex_skills(target_dir, enable_codex_skills=cli_flag)

    The ``--codex-skills`` CLI flag should propagate straight into
    ``enable_codex_skills``.
    """
    if not enable_codex_skills:
        return

    codex_skills_dir = target_dir / ".codex" / "skills"
    codex_skills_dir.mkdir(parents=True, exist_ok=True)

    sources = _iter_source_skills()
    live_names: set[str] = {s.name for s in sources}

    symlink_count = 0
    copy_count = 0
    for skill in sources:
        target = codex_skills_dir / skill.name
        mode = _symlink_or_copy(skill, target)
        if mode == "symlink":
            symlink_count += 1
        else:
            copy_count += 1

    removed = _cleanup_stale(codex_skills_dir, live_names)

    total = symlink_count + copy_count
    print(
        f"  Codex skill mirror: {total} skills "
        f"({symlink_count} symlink, {copy_count} copy)"
    )
    if removed:
        print(f"  Codex skill mirror: removed {len(removed)} stale entries")


def main() -> None:
    args = sys.argv[1:]
    enable = "--enable" in args
    positional = [a for a in args if not a.startswith("--")]
    target = Path(positional[0]) if positional else Path.cwd()
    generate(target, enable_codex_skills=enable)


if __name__ == "__main__":
    main()
