#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate the shared AGENTS.md instruction core.

Output is compatible with the Codex and GitHub Copilot AGENTS.md format.
Usage: ./scripts/generate_agents_md.py > AGENTS.md
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from instruction_core import render_instruction_core


def main() -> None:
    print(render_instruction_core(), end="")


if __name__ == "__main__":
    main()
