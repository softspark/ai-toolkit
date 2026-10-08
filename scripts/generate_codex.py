#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate the compact shared AGENTS.md policy for OpenAI Codex CLI.

Agent and skill discovery is installed separately in native directories, so
the always-on instruction file contains policy rather than duplicated catalogs.

Usage: ./scripts/generate_codex.py > AGENTS.md
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emission import (
    print_toolkit_end,
    print_toolkit_start,
)
from instruction_core import render_instruction_core
from paths import RULES_DIR
from registered_rules import print_rule_blocks


def main() -> None:
    print_toolkit_start()
    print(render_instruction_core().rstrip())
    print()
    print_toolkit_end()

    # Registered custom rules from ~/.softspark/ai-toolkit/rules/.
    print_rule_blocks(RULES_DIR)


if __name__ == "__main__":
    main()
