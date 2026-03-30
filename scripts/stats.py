#!/usr/bin/env python3
"""ai-toolkit stats -- Show skill usage statistics.

Reads ~/.ai-toolkit/stats.json (populated by track-usage.sh hook)
and displays a sorted table of skill invocations.

Options:
  --reset   Clear all stats
  --json    Output raw JSON
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

STATS_FILE = Path.home() / ".ai-toolkit" / "stats.json"


def main() -> None:
    """Display, export, or reset usage statistics."""
    flag = sys.argv[1] if len(sys.argv) > 1 else ""

    # --reset
    if flag == "--reset":
        if STATS_FILE.is_file():
            STATS_FILE.unlink()
            print("Stats reset.")
        else:
            print("No stats file found.")
        return

    # --json
    if flag == "--json":
        if STATS_FILE.is_file():
            print(STATS_FILE.read_text(encoding="utf-8"), end="")
        else:
            print("{}")
        return

    # Default: pretty-print table
    if not STATS_FILE.is_file():
        print("No usage stats recorded yet.")
        print("Stats are collected when skills are invoked via slash commands.")
        print()
        print(f"File: {STATS_FILE}")
        return

    print("AI Toolkit Usage Stats")
    print("========================")
    print()

    with open(STATS_FILE, encoding="utf-8") as f:
        data: dict = json.load(f)

    if not data:
        print("No invocations recorded.")
        return

    rows = sorted(data.items(), key=lambda x: x[1].get("count", 0), reverse=True)

    print(f"{'Skill':<30} {'Count':>6}  {'Last Used':<20}")
    print("-" * 60)
    for name, info in rows:
        count = info.get("count", 0)
        last = info.get("last_used", "unknown")
        print(f"{name:<30} {count:>6}  {last:<20}")

    total = sum(v.get("count", 0) for v in data.values())
    print()
    print(f"Total invocations: {total}")
    print(f"Unique skills: {len(data)}")
    print()
    print(f"File: {STATS_FILE}")
    print("Reset: ai-toolkit stats --reset")


if __name__ == "__main__":
    main()
