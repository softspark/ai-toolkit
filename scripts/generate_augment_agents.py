#!/usr/bin/env python3
"""Generate ``.augment/agents/ai-toolkit-*.md`` files for Augment Code.

Each ai-toolkit agent in ``app/agents/`` is mirrored as an Augment native
subagent. Augment's subagent frontmatter (per docs.augmentcode.com) supports:

    ---
    name: <slug>
    description: "<single-line description>"
    model: inherit            # or explicit model id
    color: <color-name>       # optional UI hint
    tools: [Read, Write, ...]
    disabled_tools: []
    ---

    <body from agent file>

Design choices:

* ``model: inherit`` is used unconditionally. ai-toolkit stores short aliases
  (``opus``/``sonnet``/``haiku``) that do not map to Augment's full model ids
  without assuming a provider, so we defer to the user's default model.
* ``tools`` are passed through verbatim from the source file, normalized into
  YAML flow-list form (``[Read, Write, ...]``) so Augment parses them as a
  native list.
* ``disabled_tools: []`` is emitted as an explicit empty list to match the
  shape Augment's UI expects when reading back the file.
* Files are prefixed ``ai-toolkit-`` so uninstall can identify ours without
  touching user-authored agents.
* Regeneration removes stale ``ai-toolkit-*.md`` files whose source agent
  no longer exists.

Usage:
  python3 scripts/generate_augment_agents.py [target-dir]

Writes files to ``target-dir/.augment/agents/``.
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


def _render_augment_agent(agent_file: Path) -> str:
    """Render a single Augment subagent .md file from an ai-toolkit agent."""
    name = frontmatter_field(agent_file, "name")
    description = frontmatter_field(agent_file, "description")
    color = frontmatter_field(agent_file, "color")
    tools_raw = frontmatter_field(agent_file, "tools")
    tools = _parse_tools(tools_raw)

    # Escape description for YAML quoted string
    safe_desc = description.replace('"', "'")

    lines: list[str] = ["---"]
    lines.append(f"name: {name}")
    lines.append(f'description: "{safe_desc}"')
    # Augment recommends ``model: inherit`` for plugins that want to follow
    # the user's active model selection. ai-toolkit agents are authored with
    # short aliases that do not map to Augment's provider-qualified ids, so
    # we deliberately emit ``inherit`` instead of translating.
    lines.append("model: inherit")
    if color:
        lines.append(f"color: {color}")
    if tools:
        tools_flow = ", ".join(tools)
        lines.append(f"tools: [{tools_flow}]")
    else:
        lines.append("tools: []")
    # Explicit empty disabled_tools for shape parity with Augment UI exports
    lines.append("disabled_tools: []")
    lines.append("---")
    lines.append("")
    body = _agent_body(agent_file).rstrip()
    if body:
        lines.append(body)
    lines.append("")
    return "\n".join(lines)


def _cleanup_stale(agents_out: Path) -> int:
    """Remove stale ai-toolkit-* agent files whose source no longer exists.

    Only touches files with the ``ai-toolkit-`` prefix so user-authored
    Augment agents are preserved.
    """
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
    """Write Augment agent files and return (written, removed_stale).

    By default writes to ``target_dir/.augment/agents/`` (project-local).
    Pass ``config_root=~/.augment`` for the global layout, which writes
    directly under ``agents/`` without the ``.augment/`` prefix.
    """
    base = config_root if config_root is not None else target_dir / ".augment"
    agents_out = base / "agents"
    agents_out.mkdir(parents=True, exist_ok=True)

    written = 0
    for agent_file in sorted(agents_dir.glob("*.md")):
        name = frontmatter_field(agent_file, "name")
        description = frontmatter_field(agent_file, "description")
        if not name or not description:
            continue
        out_path = agents_out / f"{AGENT_PREFIX}{name}.md"
        out_path.write_text(_render_augment_agent(agent_file), encoding="utf-8")
        written += 1

    removed = _cleanup_stale(agents_out)
    return written, removed


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    written, removed = generate(target)
    msg = f"Generated: .augment/agents/ ({written} agents"
    if removed:
        msg += f", {removed} stale removed"
    msg += ")"
    print(msg)


if __name__ == "__main__":
    main()
