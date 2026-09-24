#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate ``.roomodes`` JSON from ``app/agents/*.md``.

Roo Code's custom mode format supports these top-level properties:

  * ``slug`` — internal identifier, used for mode-specific rule dirs
  * ``name`` — display name shown in the UI
  * ``description`` — short one-line summary shown below the name in the
    mode selector (required for the redesigned selector)
  * ``roleDefinition`` — detailed expertise text placed at the start of
    the system prompt
  * ``whenToUse`` — optional guidance consumed by the Orchestrator mode
    and mode-switch tool to pick the right mode for a given task
  * ``groups`` — list of allowed tool groups

Previously this script emitted only ``slug``, ``name``, ``roleDefinition``,
and ``groups``. Per the Roo Code docs (features/custom-modes), both
``description`` and ``whenToUse`` are now first-class fields: the
description field is what the UI renders under the mode name, while
``roleDefinition`` should carry the deeper persona text.

Usage: ./scripts/generate_roo_modes.py > .roomodes
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import agents_dir, frontmatter_field
from secure_fs import OwnedEdit, apply_owned_edits, lexical_absolute

MODE_GROUPS = ["read", "edit", "command", "mcp"]
_MODE_REQUIRED = frozenset({"slug", "name", "roleDefinition", "groups"})
_MODE_OPTIONAL = frozenset({"description", "whenToUse"})


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


def _first_sentence(description: str, *, limit: int = 140) -> str:
    """Extract a short summary for the ``whenToUse`` hint.

    Roo's orchestrator uses ``whenToUse`` to pick between modes, so a
    terse action-oriented sentence is more useful than the full agent
    description. Falls back to the first ~140 chars if no period is
    found before the limit.
    """
    if not description:
        return ""
    text = description.strip().replace("\n", " ")
    dot = text.find(". ")
    if 0 < dot <= limit:
        return text[:dot + 1]
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def _toolkit_slugs(source_dir: Path) -> set[str]:
    return {
        agent_file.stem
        for agent_file in source_dir.glob("*.md")
        if frontmatter_field(agent_file, "name")
        and frontmatter_field(agent_file, "description")
    }


def _is_toolkit_mode(mode: object, slugs: set[str]) -> bool:
    """Match the exact shape this generator emits (current and pre-description).

    ``.roomodes`` carries no ownership marker, so a mode counts as toolkit-owned
    only when its slug is a toolkit agent, its keys and ``groups`` are exactly
    what the generator writes, and ``roleDefinition`` opens with the description.
    """
    if not isinstance(mode, dict):
        return False
    keys = set(mode)
    if not _MODE_REQUIRED <= keys <= _MODE_REQUIRED | _MODE_OPTIONAL:
        return False
    if mode["slug"] not in slugs or mode["groups"] != MODE_GROUPS:
        return False
    role = mode["roleDefinition"]
    description = mode.get("description")
    if not isinstance(role, str):
        return False
    if description is None:
        return "\n\n" in role
    return isinstance(description, str) and role.startswith(f"{description}\n\n")


def _modes_edit(slugs: set[str]) -> OwnedEdit:
    def strip_toolkit_modes(content: bytes) -> bytes | None:
        try:
            data = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return content
        if not isinstance(data, dict) or not isinstance(data.get("customModes"), list):
            return content
        modes = data["customModes"]
        kept = [mode for mode in modes if not _is_toolkit_mode(mode, slugs)]
        if len(kept) == len(modes):
            return content
        if not kept and set(data) == {"customModes"}:
            return None
        data["customModes"] = kept
        return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")

    return strip_toolkit_modes


def _cleanup_plan(
    target_dir: Path, source_dir: Path | None
) -> tuple[Path, dict[Path, OwnedEdit]]:
    target = lexical_absolute(target_dir)
    path = target / ".roomodes"
    if not path.is_file():
        return target, {}
    return target, {path: _modes_edit(_toolkit_slugs(source_dir or agents_dir))}


def cleanup(target_dir: Path, *, source_dir: Path | None = None) -> int:
    """Remove toolkit modes from ``target_dir/.roomodes``.

    User modes and other top-level keys are kept (the file is re-serialized
    as indented JSON); the file is deleted only when nothing else remains.
    Returns 1 when the file was rewritten or removed, else 0.
    """
    target, edits = _cleanup_plan(target_dir, source_dir)
    return apply_owned_edits(edits, target, label="Roo modes")


def discover(target_dir: Path, *, source_dir: Path | None = None) -> int:
    """Return 1 when :func:`cleanup` would change ``.roomodes``, without side effects."""
    target, edits = _cleanup_plan(target_dir, source_dir)
    return apply_owned_edits(edits, target, label="Roo modes", dry_run=True)


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
        when_to_use = _first_sentence(description)

        if first:
            first = False
        else:
            sys.stdout.write(",\n")

        sys.stdout.write("    {\n")
        sys.stdout.write(f'      "slug": "{_json_escape(slug)}",\n')
        sys.stdout.write(f'      "name": "{_json_escape(name)}",\n')
        sys.stdout.write(f'      "description": "{_json_escape(description)}",\n')
        sys.stdout.write(f'      "roleDefinition": "{_json_escape(role_text)}",\n')
        if when_to_use:
            sys.stdout.write(f'      "whenToUse": "{_json_escape(when_to_use)}",\n')
        sys.stdout.write(f'      "groups": {json.dumps(MODE_GROUPS)}\n')
        sys.stdout.write("    }")

    sys.stdout.write("\n  ]\n}\n")


if __name__ == "__main__":
    main()
