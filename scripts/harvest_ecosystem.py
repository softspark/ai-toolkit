#!/usr/bin/env python3
"""harvest-ecosystem — Refresh machine-readable ecosystem snapshot.

Usage:
    harvest_ecosystem.py [--offline] [--out FILE]
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir

OUTFILE = toolkit_dir / "benchmarks" / "ecosystem-harvest.json"


def main() -> None:
    outfile = str(OUTFILE)
    passthrough: list[str] = []

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--out":
            i += 1
            if i < len(args):
                outfile = args[i]
        else:
            passthrough.append(args[i])
        i += 1

    Path(outfile).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(toolkit_dir / "scripts" / "benchmark_ecosystem.py"),
        "--dashboard-json",
        *passthrough,
        "--out", outfile,
    ]
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print(f"Harvested ecosystem snapshot: {outfile}")
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
