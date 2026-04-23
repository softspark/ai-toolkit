#!/usr/bin/env python3
"""Generate ``.cursor/agents/ai-toolkit-*.md`` files for Cursor IDE.

Each ai-toolkit agent is mirrored as a Cursor custom agent. Per Cursor's
docs (docs.cursor.com -> custom agents), agent files use YAML frontmatter:

    ---
    name: <slug>
    description: "<one-line summary shown in the picker>"
    model: <model-id>     # optional, inherits user default if absent
    color: <color-name>   # optional UI hint
    tools: [Read, Write, ...]  # list of allowed tool names
    ---

    <system prompt body>

Design choices:

* ``model`` is omitted. Our agents store short aliases (``opus``, ``sonnet``,
  ``haiku``) that do not map to Cursor's provider-qualified model ids.
  Omitting the field makes Cursor fall back to the user's default model,
  which is the same behaviour our opencode generator uses.
* ``tools`` is emitted as a YAML flow-list parsed verbatim from the source.
* Files are prefixed ``ai-toolkit-`` so install/uninstall can identify ours.
* Regeneration removes stale ``ai-toolkit-*.md`` files whose source agent
  no longer exists, but leaves user-authored agents untouched.

Usage:
  python3 scripts/generate_cursor_agents.py [target-dir]

Writes files to ``target-dir/.cursor/agents/``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emission import agents_dir
from frontmatter import frontmatter_field

AGENT_PREFIX = "ai-toolkit-"


def _agent_body(agent_file: Path) -> str:
    """Return the markdown body of an agent file (content after frontmatter)."""
    text = agent_file.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return text.strip() + "\n"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text.strip() + "\n"
    return parts[2].lstrip("\n")


def _parse_tools(tools_raw: str) -> list[str]:
    """Parse the comma-separated ``tools:`` frontmatter value into a list."""
    if not tools_raw:
        return []
    return [t.strip() for t in tools_raw.split(",") if t.strip()]


def _render_cursor_agent(agent_file: Path) -> str:
    """Render a single Cursor custom agent .md file."""
    name = frontmatter_field(agent_file, "name")
    description = frontmatter_field(agent_file, "description")
    color = frontmatter_field(agent_file, "color")
    tools_raw = frontmatter_field(agent_file, "tools")
    tools = _parse_tools(tools_raw)

    safe_desc = description.replace('"', "'")

    lines: list[str] = ["---"]
    lines.append(f"name: {name}")
    lines.append(f'description: "{safe_desc}"')
    # model intentionally omitted — Cursor falls back to the user default.
    if color:
        lines.append(f"color: {color}")
    if tools:
        tools_flow = ", ".join(tools)
        lines.append(f"tools: [{tools_flow}]")
    else:
        lines.append("tools: []")
    lines.append("---")
    lines.append("")
    body = _agent_body(agent_file).rstrip()
    if body:
        lines.append(body)
    lines.append("")
    return "\n".join(lines)


def _cleanup_stale(agents_out: Path) -> int:
    """Remove stale ai-toolkit-* agent files whose source no longer exists."""
    if not agents_out.is_dir():
        return 0
    removed = 0
    for f in sorted(agents_out.glob(f"{AGENT_PREFIX}*.md")):
        source_name = f.stem[len(AGENT_PREFIX):]
        source = agents_dir / f"{source_name}.md"
        if not source.is_file():
            f.unlink()
            removed += 1
    return removed


def generate(
    target_dir: Path, config_root: Path | None = None
) -> tuple[int, int]:
    """Write Cursor agent files and return (written, removed_stale).

    By default writes to ``target_dir/.cursor/agents/`` (project-local).
    Pass ``config_root=~/.cursor`` for the global layout.
    """
    base = config_root if config_root is not None else target_dir / ".cursor"
    agents_out = base / "agents"
    agents_out.mkdir(parents=True, exist_ok=True)

    written = 0
    for agent_file in sorted(agents_dir.glob("*.md")):
        name = frontmatter_field(agent_file, "name")
        description = frontmatter_field(agent_file, "description")
        if not name or not description:
            continue
        out_path = agents_out / f"{AGENT_PREFIX}{name}.md"
        out_path.write_text(_render_cursor_agent(agent_file), encoding="utf-8")
        written += 1

    removed = _cleanup_stale(agents_out)
    return written, removed


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    written, removed = generate(target)
    msg = f"Generated: .cursor/agents/ ({written} agents"
    if removed:
        msg += f", {removed} stale removed"
    msg += ")"
    print(msg)


if __name__ == "__main__":
    main()
