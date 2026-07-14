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
    r"^<!-- TOOLKIT:(?P<section>.+) (?P<kind>START|END) -->$"
)
_EMPTY_LEGACY_MARKER_RE = re.compile(
    r"^<!-- TOOLKIT: (?P<kind>START|END) -->$"
)


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

def _validate_section_name(section: str) -> str:
    """Validate a section name that can be represented by one marker line."""
    if not section or "\n" in section or "\r" in section:
        raise ValueError("section name must be non-empty and single-line")
    return section


def _section_names_for_update(section: str) -> set[str]:
    """Return current and pre-Unicode marker names for update migration."""
    section = _validate_section_name(section)
    legacy_section = re.sub(r"[^a-zA-Z0-9_-]", "", section)
    return {section, legacy_section}


def markers_start(section: str = "ai-toolkit") -> str:
    """Return the TOOLKIT start marker block."""
    section = _validate_section_name(section)
    return (
        f"<!-- TOOLKIT:{section} START -->\n"
        f"<!-- Auto-injected by ai-toolkit. Re-run to update. -->\n"
    )


def markers_end(section: str = "ai-toolkit") -> str:
    """Return the TOOLKIT end marker."""
    section = _validate_section_name(section)
    return f"\n<!-- TOOLKIT:{section} END -->"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def strip_section(content: str, section: str) -> str:
    """Remove a TOOLKIT marker section from content."""
    return _strip_sections(content, {_validate_section_name(section)})


def strip_all_sections(content: str) -> str:
    """Remove every balanced TOOLKIT section and any orphan marker lines.

    Balanced spans are discovered before content is removed, so nested legacy
    sections are handled without leaving an outer END marker behind. An
    unmatched START marker does not consume unrelated user content after it.
    """
    return _strip_sections(content, None)


def _strip_sections(
    content: str,
    sections: set[str] | None,
    *,
    migrate_empty_legacy: bool = False,
) -> str:
    lines = content.splitlines(keepends=True)
    stack: list[tuple[str, int]] = []
    marker_names: dict[int, str] = {}
    intervals: list[tuple[int, int, str]] = []

    for index, line in enumerate(lines):
        marker_line = line.rstrip("\r\n")
        match = _MARKER_RE.fullmatch(marker_line)
        if match:
            name = _validate_section_name(match.group("section"))
            kind = match.group("kind")
        elif migrate_empty_legacy:
            empty_match = _EMPTY_LEGACY_MARKER_RE.fullmatch(marker_line)
            if not empty_match:
                continue
            name = ""
            kind = empty_match.group("kind")
        else:
            continue
        marker_names[index] = name
        if kind == "START":
            stack.append((name, index))
        elif stack and stack[-1][0] == name:
            _, start = stack.pop()
            intervals.append((start, index, name))
        elif stack:
            # Crossed or otherwise mismatched markers make every open span
            # ambiguous. Keep their non-marker content instead of guessing.
            stack.clear()

    coverage_delta = [0] * (len(lines) + 1)
    for start, end, name in intervals:
        if sections is None or name in sections:
            coverage_delta[start] += 1
            coverage_delta[end + 1] -= 1

    result: list[str] = []
    coverage = 0
    for index, line in enumerate(lines):
        coverage += coverage_delta[index]
        marker_name = marker_names.get(index)
        remove_marker = marker_name is not None and (
            sections is None or marker_name in sections
        )
        if coverage == 0 and not remove_marker:
            result.append(line)
    return "".join(result)


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

    section = _validate_section_name(section)

    # Create parent dir and target if missing
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if not target_file.exists():
        target_file.touch()
        action = "Created"
    else:
        action = "Updated"

    # Read existing content
    existing = target_file.read_text(encoding="utf-8")

    # Strip both the current marker and the legacy ASCII-sanitized marker.
    section_names = _section_names_for_update(section)
    existing = _strip_sections(
        existing,
        section_names,
        migrate_empty_legacy="" in section_names,
    )
    existing = trim_trailing_blanks(existing)

    # Read content to inject
    new_content = content_file.read_text(encoding="utf-8")

    # Build output
    parts: list[str] = []
    if existing.strip():
        parts.append(existing)
        parts.append("")

    parts.append(markers_start(section).rstrip("\n"))
    parts.append("")
    parts.append(new_content.rstrip("\n"))
    parts.append("")
    parts.append(markers_end(section).lstrip("\n"))

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

    rule_name = _validate_section_name(rule_file.stem)
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
    rule_name = _validate_section_name(rule_name)
    start_marker = markers_start(rule_name).splitlines()[0]

    if start_marker not in content:
        return False

    content = strip_section(content, rule_name)
    content = trim_trailing_blanks(content) + "\n"
    claude_md.write_text(content, encoding="utf-8")
    return True
