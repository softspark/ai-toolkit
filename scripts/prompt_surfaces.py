# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Keep explicitly scoped Claude instructions out of other client exports."""

from __future__ import annotations

import re

CLAUDE_CODE_ONLY_START = "<!-- CLAUDE_CODE_ONLY_START -->"
CLAUDE_CODE_ONLY_END = "<!-- CLAUDE_CODE_ONLY_END -->"


def strip_claude_code_only(text: str) -> str:
    """Remove top-level blocks, preserving fenced examples and indented YAML."""
    rendered: list[str] = []
    inside = False
    fence: str | None = None
    for line in text.splitlines(keepends=True):
        marker = line.rstrip("\r\n")
        boundary = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", marker)
        if boundary:
            delimiter, suffix = boundary.groups()
            if fence is None:
                fence = delimiter
            elif delimiter[0] == fence[0] and len(delimiter) >= len(fence) and not suffix.strip():
                fence = None
            if not inside:
                rendered.append(line)
            continue
        if fence is not None:
            if not inside:
                rendered.append(line)
            continue
        if marker == CLAUDE_CODE_ONLY_START:
            if inside:
                raise ValueError("Nested CLAUDE_CODE_ONLY block")
            inside = True
        elif marker == CLAUDE_CODE_ONLY_END:
            if not inside:
                raise ValueError("Unmatched CLAUDE_CODE_ONLY end marker")
            inside = False
        elif not inside:
            rendered.append(line)
    if inside:
        raise ValueError("Unterminated CLAUDE_CODE_ONLY block")
    return "".join(rendered)
