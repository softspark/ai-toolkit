#!/usr/bin/env python3
"""Generate .opencode/commands/*.md files for opencode (https://opencode.ai).

User-invocable skills become opencode slash commands. Knowledge skills
(``user-invocable: false``) are excluded — they load automatically via
AGENTS.md context instead of `/` invocation.

Generated commands use the required ``template`` frontmatter field.
Files are prefixed ``ai-toolkit-`` for clean uninstall.

opencode commands: https://opencode.ai/docs/commands/
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_skill_adapter import build_codex_skill_text, is_codex_adapted_skill
from emission import skills_dir
from frontmatter import frontmatter_field

COMMAND_PREFIX = "ai-toolkit-"


def _skill_body(skill_file: Path) -> str:
    """Return the markdown body of a skill (content after frontmatter).

    For skills that rely on Claude-only orchestration primitives, route
    through the Codex adapter so `Agent`/`TeamCreate`/`TaskCreate` get
    rewritten to opencode-compatible delegation guidance. The adapter's
    output is compatible with opencode's subagent model (``spawn_agent``
    conventions, plan tracking) because both lack Claude primitives.
    """
    if is_codex_adapted_skill(skill_file):
        adapted = build_codex_skill_text(skill_file)
        # Strip the adapted frontmatter — we emit our own below
        parts = adapted.split("---", 2)
        return parts[2].lstrip("\n") if len(parts) >= 3 else adapted

    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    return parts[2].lstrip("\n") if len(parts) >= 3 else text


def _render_opencode_command(skill_file: Path) -> str:
    """Render a single opencode command .md file from a user-invocable skill."""
    name = frontmatter_field(skill_file, "name")
    description = frontmatter_field(skill_file, "description")
    agent_field = frontmatter_field(skill_file, "agent")
    # opencode does NOT read "body" — the prompt is entirely in the `template`
    # frontmatter field. We embed the SKILL.md body as the template using a
    # YAML block scalar (``|``) which preserves newlines without escaping.
    body = _skill_body(skill_file).rstrip()

    lines: list[str] = ["---"]
    if description:
        safe_desc = description.replace('"', "'")
        lines.append(f'description: "{safe_desc}"')
    if agent_field:
        # opencode accepts an `agent` frontmatter field pointing at a subagent
        lines.append(f"agent: {_map_agent_name(agent_field)}")
    lines.append("template: |")
    for tpl_line in body.splitlines() or [""]:
        lines.append(f"  {tpl_line}" if tpl_line else "  ")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _map_agent_name(value: str) -> str:
    """Map ai-toolkit agent names to opencode subagent names.

    Our opencode agents are installed with the ``ai-toolkit-`` prefix by
    ``generate_opencode_agents.py``, so rewrite here for consistency.
    """
    value = value.strip()
    if not value:
        return value
    if value.startswith(COMMAND_PREFIX):
        return value
    return f"{COMMAND_PREFIX}{value}"


def _is_user_invocable(skill_file: Path) -> bool:
    """Return True if the skill should be exposed as a `/` command."""
    invocable = frontmatter_field(skill_file, "user-invocable")
    if invocable:
        return invocable.lower() not in ("false", "0", "no")
    # Absence + `disable-model-invocation: true` = task skill (user-invocable)
    disable_model = frontmatter_field(skill_file, "disable-model-invocation")
    if disable_model and disable_model.lower() in ("true", "1", "yes"):
        return True
    # Default: NOT invocable — avoids exposing knowledge skills as commands
    return False


def _cleanup_stale(commands_out: Path) -> int:
    """Remove stale ai-toolkit-* command files whose source no longer exists or is no longer invocable."""
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


def generate(target_dir: Path) -> tuple[int, int]:
    """Write .opencode/commands/ai-toolkit-*.md files to target_dir.

    Returns (written, removed_stale).
    """
    commands_out = target_dir / ".opencode" / "commands"
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
        out_path.write_text(_render_opencode_command(skill_file), encoding="utf-8")
        written += 1

    removed = _cleanup_stale(commands_out)
    return written, removed


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    written, removed = generate(target)
    msg = f"Generated: .opencode/commands/ ({written} commands"
    if removed:
        msg += f", {removed} stale removed"
    msg += ")"
    print(msg)


if __name__ == "__main__":
    main()
