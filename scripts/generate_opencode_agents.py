#!/usr/bin/env python3
"""Generate .opencode/agents/*.md files for opencode (https://opencode.ai).

Each ai-toolkit agent becomes an opencode subagent with frontmatter:

    ---
    description: "..."
    mode: subagent
    ---

    <body from agent file>

Generated files are prefixed ``ai-toolkit-`` so they never collide with
user-authored opencode agents and can be cleanly removed on uninstall.

Usage:
  python3 scripts/generate_opencode_agents.py [target-dir]

Writes files to target-dir/.opencode/agents/.
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
    # Skip first frontmatter block
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text.strip() + "\n"
    return parts[2].lstrip("\n")


def _render_opencode_agent(agent_file: Path) -> str:
    """Render a single opencode subagent .md file from an ai-toolkit agent."""
    name = frontmatter_field(agent_file, "name")
    description = frontmatter_field(agent_file, "description")
    model = frontmatter_field(agent_file, "model")
    color = frontmatter_field(agent_file, "color")

    # Escape description for YAML quoted string
    safe_desc = description.replace('"', "'")

    lines: list[str] = ["---"]
    lines.append(f'description: "{safe_desc}"')
    lines.append("mode: subagent")
    if model:
        # opencode expects `provider/model` — pass the Claude value through as a hint
        lines.append(f"# source model hint from ai-toolkit: {model}")
    if color:
        lines.append(f"color: {color}")
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


def generate(target_dir: Path) -> tuple[int, int]:
    """Write .opencode/agents/ai-toolkit-*.md files to target_dir.

    Returns (written, removed_stale).
    """
    agents_out = target_dir / ".opencode" / "agents"
    agents_out.mkdir(parents=True, exist_ok=True)

    written = 0
    for agent_file in sorted(agents_dir.glob("*.md")):
        name = frontmatter_field(agent_file, "name")
        description = frontmatter_field(agent_file, "description")
        if not name or not description:
            continue
        out_path = agents_out / f"{AGENT_PREFIX}{name}.md"
        out_path.write_text(_render_opencode_agent(agent_file), encoding="utf-8")
        written += 1

    removed = _cleanup_stale(agents_out)
    return written, removed


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    written, removed = generate(target)
    msg = f"Generated: .opencode/agents/ ({written} agents"
    if removed:
        msg += f", {removed} stale removed"
    msg += ")"
    print(msg)


if __name__ == "__main__":
    main()
