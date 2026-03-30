#!/usr/bin/env python3
"""Generate .roomodes JSON from app/agents/*.md.

Usage: ./scripts/generate_roo_modes.py > .roomodes
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import agents_dir, frontmatter_field


def _json_escape(s: str) -> str:
    """Escape a string for safe JSON embedding (no stdlib json dependency needed)."""
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", "\\n")
    s = s.replace("\t", "\\t")
    s = s.replace("\r", "")
    return s


def _read_body(filepath: Path) -> str:
    """Read file content after YAML frontmatter (after second --- delimiter).

    Trailing blank lines are stripped to match bash ``$(...)`` behaviour.
    """
    lines: list[str] = []
    fence_count = 0
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if stripped == "---":
                fence_count += 1
                continue
            if fence_count >= 2:
                lines.append(line.rstrip("\n"))
    # Strip trailing empty lines (bash command substitution strips trailing newlines)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def main() -> None:
    first = True
    sys.stdout.write('{\n  "customModes": [\n')

    for agent_file in sorted(agents_dir.glob("*.md")):
        if not agent_file.is_file():
            continue

        slug = agent_file.stem
        name = frontmatter_field(agent_file, "name")
        description = frontmatter_field(agent_file, "description")

        if not name or not description:
            continue

        role_def = _read_body(agent_file)
        role_text = f"{description}\n\n{role_def}"

        if first:
            first = False
        else:
            sys.stdout.write(",\n")

        sys.stdout.write("    {\n")
        sys.stdout.write(f'      "slug": "{_json_escape(slug)}",\n')
        sys.stdout.write(f'      "name": "{_json_escape(name)}",\n')
        sys.stdout.write(f'      "roleDefinition": "{_json_escape(role_text)}",\n')
        sys.stdout.write('      "groups": ["read", "edit", "command", "mcp"]\n')
        sys.stdout.write("    }")

    sys.stdout.write("\n  ]\n}\n")


if __name__ == "__main__":
    main()
