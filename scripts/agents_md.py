#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Make AGENTS.md a project's single source of instructions.

Usage:
  ai-toolkit adopt-agents-md [project-dir] [--dry-run]

It moves the project's own instructions out of CLAUDE.md into
AGENTS.md, which Claude Code, Codex, Copilot, OpenCode and Antigravity all
read, and leaves CLAUDE.md importing it (``@AGENTS.md``) next to the sections
the toolkit manages there. ai-toolkit sections an older release injected into
AGENTS.md are dropped, since each agent now gets them from its own surface.
A ``/AGENTS.md`` or ``AGENTS.md`` line in .gitignore is removed so the file can
be committed. Every file is backed up to ``~/.softspark/ai-toolkit/backups/``
before it changes. Running it again is a no-op.

Stdlib only.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from injection import collapse_blank_runs, strip_all_sections, trim_trailing_blanks
from install_steps.ai_tools import (
    AGENTS_MD_IMPORT,
    AGENTS_MD_SECTION,
    _CONSTITUTION_HEADING as CONSTITUTION_HEADING,
    _CONSTITUTION_IMPORT as CONSTITUTION_IMPORT,
    _backup_file,
    _create_local_claude_md,
    project_instructions,
)
from registered_rules import ANTIGRAVITY_RULE_LIMIT_BYTES

GITIGNORE_ENTRIES = frozenset({"AGENTS.md", "/AGENTS.md"})
USAGE = "usage: ai-toolkit adopt-agents-md [project-dir] [--dry-run]"
_MARKER = re.compile(r"^<!-- TOOLKIT:(?P<name>.+) (?P<kind>START|END) -->$")


def _toolkit_parts(text: str) -> str:
    """Only what the toolkit manages in CLAUDE.md: marker sections and the
    project constitution import, in their original order."""
    kept: list[str] = []
    open_section: str | None = None
    for line in text.splitlines():
        match = _MARKER.match(line.strip())
        if open_section is None and match and match["kind"] == "START":
            open_section = match["name"]
        if open_section is not None:
            kept.append(line)
            if match and match["kind"] == "END" and match["name"] == open_section:
                open_section = None
                kept.append("")
        elif line.strip() in (CONSTITUTION_HEADING, CONSTITUTION_IMPORT):
            kept.append(line)
    return collapse_blank_runs(trim_trailing_blanks("\n".join(kept).strip("\n"))) + "\n"


def adopt(project: Path, *, dry_run: bool = False) -> list[str]:
    """Move CLAUDE.md instructions into AGENTS.md; return what changed."""
    claude_md, agents_md = project / "CLAUDE.md", project / "AGENTS.md"
    gitignore = project / ".gitignore"
    for path in (claude_md, agents_md, gitignore):
        if path.is_symlink():
            raise RuntimeError(f"Refusing to edit symlinked {path}")
    changes: list[str] = []

    claude_text = claude_md.read_text(encoding="utf-8") if claude_md.is_file() else ""
    # Removed toolkit sections leave blank-line gaps behind.
    instructions = collapse_blank_runs(project_instructions(claude_text), max_blanks=1).strip()
    agents_text = agents_md.read_text(encoding="utf-8") if agents_md.is_file() else ""
    agents_own = strip_all_sections(agents_text).strip()
    if instructions and instructions not in agents_own:
        merged = "\n\n".join(part for part in (instructions, agents_own) if part) + "\n"
        changes.append(f"AGENTS.md: project instructions from CLAUDE.md ({len(merged.encode())} bytes)")
        if not dry_run:
            if agents_text:
                _backup_file(agents_md, agents_text)
            agents_md.write_text(merged, encoding="utf-8")
        if len(merged.encode()) > ANTIGRAVITY_RULE_LIMIT_BYTES:
            changes.append(
                f"WARNING: AGENTS.md exceeds {ANTIGRAVITY_RULE_LIMIT_BYTES} bytes; "
                "Antigravity truncates it, split detail into kb/ or skills"
            )
    if instructions:
        changes.append("CLAUDE.md: instructions moved out; it imports @AGENTS.md")
        if not dry_run:
            _backup_file(claude_md, claude_text)
            claude_md.write_text(_toolkit_parts(claude_text), encoding="utf-8")

    if gitignore.is_file():
        lines = gitignore.read_text(encoding="utf-8").splitlines(keepends=True)
        kept = [line for line in lines if line.strip() not in GITIGNORE_ENTRIES]
        if kept != lines:
            changes.append(".gitignore: AGENTS.md is no longer ignored (commit it)")
            if not dry_run:
                _backup_file(gitignore, "".join(lines))
                gitignore.write_text("".join(kept), encoding="utf-8")

    if not dry_run and (instructions or agents_md.is_file()):
        # Adds the import block and drops toolkit sections left in AGENTS.md.
        _create_local_claude_md(project, reset=False)
    elif not instructions and agents_md.is_file() and AGENTS_MD_IMPORT not in claude_text:
        changes.append(f"CLAUDE.md: add the {AGENTS_MD_SECTION} import")
    return changes


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--dry-run"]
    dry_run = "--dry-run" in argv
    if len(args) > 1 or any(a.startswith("-") for a in args):
        print(USAGE, file=sys.stderr)
        return 2
    # The CLI runs this in the caller's directory. AI_TOOLKIT_USER_CWD is not
    # consulted: an inherited, stale value must never redirect file edits.
    project = Path(args[0] if args else ".").expanduser().resolve()
    if not project.is_dir():
        print(f"Not a directory: {project}", file=sys.stderr)
        return 1
    try:
        changes = adopt(project, dry_run=dry_run)
    except (OSError, RuntimeError) as error:
        print(f"ai-toolkit agents-md: {error}", file=sys.stderr)
        return 1
    prefix = "Would change" if dry_run else "Changed"
    for change in changes or ["nothing: AGENTS.md already holds the project instructions"]:
        print(f"  {prefix}: {change}" if changes else f"  No change: {change}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
