#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate ``.augment/commands/ai-toolkit-*.md`` files for Augment Code.

User-invocable skills become Augment custom slash commands. Knowledge skills
(``user-invocable: false``) are excluded — they load automatically via
AGENTS.md/rules context instead of ``/`` invocation.

Per docs.augmentcode.com/cli/custom-commands, Augment custom commands are plain
markdown files with an optional YAML frontmatter header. The body of the file IS
the prompt (no ``template:`` field, no TOML). The documented frontmatter fields
are ``description``, ``argument-hint``, and ``model`` (no ``agent`` field):

    ---
    description: "<short one-liner shown in the palette>"
    argument-hint: "<optional hint shown after the command name>"
    ---

    <prompt body — supports $ARGUMENTS placeholder>

Files are prefixed ``ai-toolkit-`` so install/uninstall can identify ours
without touching user files.

Usage:
  python3 scripts/generate_augment_commands.py [target-dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emission import skills_dir
from frontmatter import frontmatter_field
from secure_fs import apply_owned_edits, lexical_absolute

COMMAND_PREFIX = "ai-toolkit-"


def _skill_body(skill_file: Path) -> str:
    """Return the markdown body of a skill (content after frontmatter)."""
    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    return parts[2].lstrip("\n") if len(parts) >= 3 else text


def _render_augment_command(skill_file: Path) -> str:
    """Render a single Augment command .md file from a user-invocable skill."""
    description = frontmatter_field(skill_file, "description")
    argument_hint = frontmatter_field(skill_file, "argument-hint")
    body = _skill_body(skill_file).rstrip()

    lines: list[str] = ["---"]
    if description:
        safe_desc = description.replace('"', "'")
        lines.append(f'description: "{safe_desc}"')
    if argument_hint:
        safe_hint = argument_hint.replace('"', "'")
        lines.append(f'argument-hint: "{safe_hint}"')
    lines.append("---")
    lines.append("")
    if body:
        lines.append(body)
    lines.append("")
    return "\n".join(lines)


def _is_user_invocable(skill_file: Path) -> bool:
    """Return True if the skill should be exposed as a ``/`` command.

    Matches the opencode generator's logic:
    * explicit ``user-invocable: true`` -> yes
    * implicit: ``disable-model-invocation: true`` -> yes (task skill)
    * default -> no (keeps knowledge skills out of the command palette)
    """
    invocable = frontmatter_field(skill_file, "user-invocable")
    if invocable:
        return invocable.lower() not in ("false", "0", "no")
    disable_model = frontmatter_field(skill_file, "disable-model-invocation")
    if disable_model and disable_model.lower() in ("true", "1", "yes"):
        return True
    return False


def _cleanup_stale(commands_out: Path) -> int:
    """Remove stale ai-toolkit-* command files whose source no longer exists.

    Also removes commands whose source skill is no longer user-invocable so
    flipping a skill's ``user-invocable`` flag back to ``false`` cleanly
    retracts the command.
    """
    if not commands_out.is_dir():
        return 0
    removed = 0
    for f in sorted(commands_out.glob(f"{COMMAND_PREFIX}*.md")):
        source_name = f.stem[len(COMMAND_PREFIX):]
        source = skills_dir / source_name / "SKILL.md"
        if not source.is_file() or not _is_user_invocable(source):
            f.unlink()
            removed += 1
    return removed


def generate(
    target_dir: Path, config_root: Path | None = None
) -> tuple[int, int]:
    """Write Augment command files and return (written, removed_stale).

    By default writes to ``target_dir/.augment/commands/`` (project-local).
    Pass ``config_root=~/.augment`` for the global layout.
    """
    base = config_root if config_root is not None else target_dir / ".augment"
    commands_out = base / "commands"
    commands_out.mkdir(parents=True, exist_ok=True)

    written = 0
    for skill_dir in sorted(skills_dir.iterdir()):
        if skill_dir.name.startswith("_"):
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        if not _is_user_invocable(skill_file):
            continue
        name = frontmatter_field(skill_file, "name")
        if not name:
            continue
        out_path = commands_out / f"{COMMAND_PREFIX}{name}.md"
        out_path.write_text(_render_augment_command(skill_file), encoding="utf-8")
        written += 1

    removed = _cleanup_stale(commands_out)
    return written, removed


_COMMAND_FRONTMATTER_KEYS = (b"description: ", b"argument-hint: ")


def _is_managed_command(content: bytes) -> bool:
    """Match the frontmatter ``_render_augment_command`` emits: only the
    ``description`` and ``argument-hint`` keys, then a blank line."""
    if not content.startswith(b"---\n"):
        return False
    end = content.find(b"\n---\n", 3)
    if end < 0:
        return False
    keys = content[4:end].split(b"\n") if end > 3 else []
    return all(line.startswith(_COMMAND_FRONTMATTER_KEYS) for line in keys if line)


def _owned_command_edit(content: bytes) -> bytes | None:
    return None if _is_managed_command(content) else content


def _apply(target_dir: Path, config_root: Path | None, *, dry_run: bool) -> int:
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Augment target directory: {target}")
    base = lexical_absolute(config_root) if config_root is not None else target / ".augment"
    commands_out = base / "commands"
    for directory in (base, commands_out):
        if directory.is_symlink():
            raise RuntimeError(f"Refusing symlinked Augment commands directory: {directory}")
    files = sorted(
        path for path in commands_out.glob(f"{COMMAND_PREFIX}*.md")
        if path.is_file() and not path.is_symlink()
    ) if commands_out.is_dir() else []
    return apply_owned_edits(
        {path: _owned_command_edit for path in files},
        target,
        label="Augment command",
        prune=(commands_out, base) if base != target else (commands_out,),
        dry_run=dry_run,
    )


def discover(target_dir: Path, *, config_root: Path | None = None) -> int:
    """Count managed ``ai-toolkit-*.md`` commands ``cleanup`` would remove."""
    return _apply(target_dir, config_root, dry_run=True)


def cleanup(target_dir: Path, *, config_root: Path | None = None) -> int:
    """Remove every managed Augment command; user commands are preserved."""
    return _apply(target_dir, config_root, dry_run=False)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    written, removed = generate(target)
    msg = f"Generated: .augment/commands/ ({written} commands"
    if removed:
        msg += f", {removed} stale removed"
    msg += ")"
    print(msg)


if __name__ == "__main__":
    main()
