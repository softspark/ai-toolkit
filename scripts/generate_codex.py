#!/usr/bin/env python3
"""Generate the compact shared AGENTS.md policy for OpenAI Codex CLI.

Agent and skill discovery is installed separately in native directories, so
the always-on instruction file contains policy rather than duplicated catalogs.

Usage: ./scripts/generate_codex.py > AGENTS.md
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emission import (
    print_toolkit_end,
    print_toolkit_start,
)
from instruction_core import render_instruction_core
from paths import RULES_DIR


def main() -> None:
    print_toolkit_start()
    print(render_instruction_core().rstrip())
    print()
    print_toolkit_end()

    # Registered custom rules from ~/.softspark/ai-toolkit/rules/.
    # Skipped when AI_TOOLKIT_NO_CUSTOM_RULES=1 so a maintainer's personal
    # registered rules never leak into the toolkit's own canonical files.
    if RULES_DIR.is_dir() and os.environ.get("AI_TOOLKIT_NO_CUSTOM_RULES") != "1":
        for rule_file in sorted(RULES_DIR.glob("*.md")):
            rule_name = rule_file.stem
            print()
            print(f"<!-- TOOLKIT:{rule_name} START -->")
            print("<!-- Auto-injected by ai-toolkit. Re-run to update. -->")
            print()
            print(rule_file.read_text(encoding="utf-8").rstrip())
            print()
            print(f"<!-- TOOLKIT:{rule_name} END -->")


if __name__ == "__main__":
    main()
