"""YAML frontmatter parsing for agent and skill markdown files.

Stdlib-only. Extracts fields from ``---`` delimited frontmatter blocks.

Usage::

    from frontmatter import frontmatter_field, frontmatter_block
"""
from __future__ import annotations

from pathlib import Path


def frontmatter_field(filepath: str | Path, field: str) -> str:
    """Extract a YAML frontmatter field value from a file.

    Reads lines between the first pair of ``---`` delimiters and returns
    the value for the given field. Strips surrounding quotes.
    """
    filepath = Path(filepath)
    if not filepath.is_file():
        return ""
    in_frontmatter = False
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if stripped == "---":
                if in_frontmatter:
                    break
                in_frontmatter = True
                continue
            if in_frontmatter and stripped.startswith(f"{field}:"):
                value = stripped[len(field) + 1:].strip()
                # Strip surrounding quotes
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                return value
    return ""


def frontmatter_block(filepath: str | Path) -> str:
    """Return the raw frontmatter text (excluding --- delimiters)."""
    filepath = Path(filepath)
    if not filepath.is_file():
        return ""
    lines: list[str] = []
    in_fm = False
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if stripped == "---":
                if in_fm:
                    break
                in_fm = True
                continue
            if in_fm:
                lines.append(stripped)
    return "\n".join(lines)
