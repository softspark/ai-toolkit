#!/usr/bin/env python3
"""CLI wrapper around inject_section() from _common.

Injects content between TOOLKIT markers into any file.
Existing content outside the markers is preserved -- never overwritten.
Re-running updates only the marked section (idempotent).

Usage:
  inject_section_cli.py <content-file> <target-file> [section-name]

Arguments:
  content-file  Path to file with content to inject
  target-file   Path to target file (created if missing)
  section-name  Marker label (default: ai-toolkit)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import inject_section


def main() -> None:
    """Inject a content file into a target file between TOOLKIT markers."""
    if len(sys.argv) < 3:
        print(
            "Usage: inject_section_cli.py <content-file> <target-file> [section-name]",
            file=sys.stderr,
        )
        sys.exit(1)

    content_file = Path(sys.argv[1])
    target_file = Path(sys.argv[2])
    section = sys.argv[3] if len(sys.argv) > 3 else "ai-toolkit"

    if not content_file.is_file():
        print(f"Content file not found: {content_file}", file=sys.stderr)
        sys.exit(1)

    action = inject_section(content_file, target_file, section)
    print(f"  {action}: {target_file}")


if __name__ == "__main__":
    main()
