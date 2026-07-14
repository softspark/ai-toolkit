"""Marker-based section injection and rule management.

Handles idempotent injection of content between TOOLKIT markers
into target files. Also manages rule injection into CLAUDE.md.

Stdlib-only.

Usage::

    from injection import inject_section, inject_rule, remove_rule_section
"""
from __future__ import annotations

import re
from pathlib import Path


_MARKER_RE = re.compile(
    r"^<!-- TOOLKIT:([a-zA-Z0-9._-]+) (START|END) -->$"
)


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

def markers_start(section: str = "ai-toolkit") -> str:
    """Return the TOOLKIT start marker block."""
    return (
        f"<!-- TOOLKIT:{section} START -->\n"
        f"<!-- Auto-injected by ai-toolkit. Re-run to update. -->\n"
    )


def markers_end(section: str = "ai-toolkit") -> str:
    """Return the TOOLKIT end marker."""
    return f"\n<!-- TOOLKIT:{section} END -->"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def strip_section(content: str, section: str) -> str:
    """Remove a TOOLKIT marker section from content."""
    return _strip_sections(content, {section})


def strip_all_sections(content: str) -> str:
    """Remove every balanced TOOLKIT section and any orphan marker lines.

    Balanced spans are discovered before content is removed, so nested legacy
    sections are handled without leaving an outer END marker behind. An
    unmatched START marker does not consume unrelated user content after it.
    """
    return _strip_sections(content, None)


def _strip_sections(content: str, sections: set[str] | None) -> str:
    lines = content.splitlines(keepends=True)
    stacks: dict[str, list[int]] = {}
    marker_lines: set[int] = set()
    intervals: list[tuple[int, int]] = []

    for index, line in enumerate(lines):
        match = _MARKER_RE.fullmatch(line.rstrip("\r\n"))
        if not match:
            continue
        name, kind = match.groups()
        if sections is not None and name not in sections:
            continue
        marker_lines.add(index)
        stack = stacks.setdefault(name, [])
        if kind == "START":
            stack.append(index)
        elif stack:
            intervals.append((stack.pop(), index))

    def is_managed(index: int) -> bool:
        if index in marker_lines:
            return True
        return any(start < index < end for start, end in intervals)

    return "".join(
        line for index, line in enumerate(lines) if not is_managed(index)
    )


def trim_trailing_blanks(text: str) -> str:
    """Remove trailing blank lines from text."""
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def collapse_blank_runs(text: str, max_blanks: int = 2) -> str:
    """Collapse runs of more than max_blanks consecutive blank lines."""
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    blanks = 0
    for line in lines:
        if not line.strip():
            blanks += 1
            if blanks <= max_blanks:
                result.append(line)
        else:
            blanks = 0
            result.append(line)
    return "".join(result)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def inject_section(
    content_file: str | Path,
    target_file: str | Path,
    section: str = "ai-toolkit",
) -> str:
    """Inject content between TOOLKIT markers into target file.

    Existing content outside markers is preserved. Re-running updates
    only the marked section (idempotent).

    Returns action taken: "Created" or "Updated".
    """
    content_file = Path(content_file)
    target_file = Path(target_file)

    # Sanitize section name
    section = re.sub(r"[^a-zA-Z0-9_-]", "", section)

    # Create parent dir and target if missing
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if not target_file.exists():
        target_file.touch()
        action = "Created"
    else:
        action = "Updated"

    # Read existing content
    existing = target_file.read_text(encoding="utf-8")

    # Strip existing section
    existing = strip_section(existing, section)
    existing = trim_trailing_blanks(existing)

    # Read content to inject
    new_content = content_file.read_text(encoding="utf-8")

    # Build output
    parts: list[str] = []
    if existing.strip():
        parts.append(existing)
        parts.append("")

    parts.append(f"<!-- TOOLKIT:{section} START -->")
    parts.append("<!-- Auto-injected by ai-toolkit. Re-run to update. -->")
    parts.append("")
    parts.append(new_content.rstrip("\n"))
    parts.append("")
    parts.append(f"<!-- TOOLKIT:{section} END -->")

    output = "\n".join(parts) + "\n"
    output = collapse_blank_runs(output)
    output = output.lstrip("\n")  # no leading blank lines

    target_file.write_text(output, encoding="utf-8")
    return action


def inject_rule(rule_file: str | Path, target_dir: str | Path) -> str:
    """Inject a rule file into target_dir/.claude/CLAUDE.md.

    Returns action taken.
    """
    rule_file = Path(rule_file)
    target_dir = Path(target_dir)

    if not rule_file.is_file():
        raise FileNotFoundError(f"Rule file not found: {rule_file}")

    rule_name = re.sub(r"[^a-zA-Z0-9_-]", "", rule_file.stem)
    claude_md = target_dir / ".claude" / "CLAUDE.md"
    claude_md.parent.mkdir(parents=True, exist_ok=True)

    return inject_section(rule_file, claude_md, rule_name)


def remove_rule_section(rule_name: str, target_dir: str | Path) -> bool:
    """Remove a rule section from target_dir/.claude/CLAUDE.md.

    Returns True if section was found and removed.
    """
    target_dir = Path(target_dir)
    claude_md = target_dir / ".claude" / "CLAUDE.md"

    if not claude_md.is_file():
        return False

    content = claude_md.read_text(encoding="utf-8")
    start_marker = f"<!-- TOOLKIT:{rule_name} START -->"

    if start_marker not in content:
        return False

    content = strip_section(content, rule_name)
    content = trim_trailing_blanks(content) + "\n"
    claude_md.write_text(content, encoding="utf-8")
    return True
