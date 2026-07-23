#!/usr/bin/env python3
"""Lean process entry point for the Claude output-filter hook."""

from __future__ import annotations

import sys

from tool_output_filter.hook_runtime import run_hook


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if (
        len(arguments) != 3
        or arguments[0] != "hook"
        or arguments[1] != "--policy"
    ):
        return 2
    return run_hook(arguments[2])


if __name__ == "__main__":
    sys.exit(main())
