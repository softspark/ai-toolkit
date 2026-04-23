#!/usr/bin/env python3
"""Generate ``.gemini/commands/ai-toolkit-*.toml`` files for Gemini CLI.

User-invocable skills become Gemini custom slash commands. Knowledge skills
(``user-invocable: false``) are excluded — they load automatically via
``GEMINI.md`` context instead of ``/`` invocation.

Per github.com/google-gemini/gemini-cli, Gemini custom commands are TOML
files with at minimum:

    description = "<one-line summary shown in the palette>"
    prompt = \"\"\"
    <multi-line prompt body>
    \"\"\"

Argument substitution uses the ``{{args}}`` placeholder. We translate the
Claude Code ``$ARGUMENTS`` token that appears in some skill bodies into
``{{args}}`` so the same skill works across both runtimes.

Files are prefixed ``ai-toolkit-`` so install/uninstall can identify ours
without touching user-authored Gemini commands.

Usage:
  python3 scripts/generate_gemini_commands.py [target-dir]

Writes files to ``target-dir/.gemini/commands/``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emission import skills_dir
from frontmatter import frontmatter_field

COMMAND_PREFIX = "ai-toolkit-"


def _skill_body(skill_file: Path) -> str:
    """Return the markdown body of a skill (content after frontmatter)."""
    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    return parts[2].lstrip("\n") if len(parts) >= 3 else text


def _translate_placeholders(body: str) -> str:
    """Rewrite Claude-style ``$ARGUMENTS`` placeholders to Gemini ``{{args}}``."""
    return body.replace("$ARGUMENTS", "{{args}}")


def _render_gemini_command(skill_file: Path) -> str:
    """Render a single Gemini TOML command file from a user-invocable skill.

    Bodies are emitted as TOML multi-line **literal** strings (``'''...'''``)
    so embedded regex such as ``\\s``, ``\\d``, ``\\n`` are passed through
    verbatim. Literal strings accept no escape sequences, which is exactly
    what we want for prompt fidelity.
    """
    description = frontmatter_field(skill_file, "description")
    body = _skill_body(skill_file).rstrip()
    body = _translate_placeholders(body)

    if "'''" in body:
        raise ValueError(
            f"{skill_file}: body contains ''' which would terminate a TOML "
            f"multi-line literal string. Rewrite the skill to avoid that "
            f"sequence or switch this generator to basic strings for it."
        )

    safe_desc = (description or "").replace('"', '\\"')

    lines: list[str] = []
    lines.append(f'description = "{safe_desc}"')
    lines.append("prompt = '''")
    if body:
        lines.append(body)
    lines.append("'''")
    lines.append("")
    return "\n".join(lines)


def _is_user_invocable(skill_file: Path) -> bool:
    """Return True if the skill should be exposed as a ``/`` command."""
    invocable = frontmatter_field(skill_file, "user-invocable")
    if invocable:
        return invocable.lower() not in ("false", "0", "no")
    disable_model = frontmatter_field(skill_file, "disable-model-invocation")
    if disable_model and disable_model.lower() in ("true", "1", "yes"):
        return True
    return False


def _cleanup_stale(commands_out: Path) -> int:
    """Remove stale ai-toolkit-* command files whose source no longer exists.

    Also removes commands whose source skill is no longer user-invocable.
    Only touches files prefixed ``ai-toolkit-`` so user-authored commands
    are preserved.
    """
    if not commands_out.is_dir():
        return 0
    removed = 0
    for f in sorted(commands_out.glob(f"{COMMAND_PREFIX}*.toml")):
        source_name = f.stem[len(COMMAND_PREFIX):]
        source = skills_dir / source_name / "SKILL.md"
        if not source.is_file() or not _is_user_invocable(source):
            f.unlink()
            removed += 1
    return removed


def generate(
    target_dir: Path, config_root: Path | None = None
) -> tuple[int, int]:
    """Write Gemini TOML command files and return (written, removed_stale).

    By default writes to ``target_dir/.gemini/commands/`` (project-local).
    Pass ``config_root=~/.gemini`` for the global layout.
    """
    base = config_root if config_root is not None else target_dir / ".gemini"
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
        out_path = commands_out / f"{COMMAND_PREFIX}{name}.toml"
        out_path.write_text(_render_gemini_command(skill_file), encoding="utf-8")
        written += 1

    removed = _cleanup_stale(commands_out)
    return written, removed


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    written, removed = generate(target)
    msg = f"Generated: .gemini/commands/ ({written} commands"
    if removed:
        msg += f", {removed} stale removed"
    msg += ")"
    print(msg)


if __name__ == "__main__":
    main()
