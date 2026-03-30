#!/usr/bin/env python3
"""Code complexity analysis script.

Scans a project directory and reports file counts by extension, largest
files by line count, TODO/FIXME/HACK/XXX markers, and a summary with
total file and line counts.

Usage::

    python3 complexity.py [directory]
"""
from __future__ import annotations

import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

IGNORE_DIRS: set[str] = {
    ".git", "node_modules", "__pycache__", ".venv",
    "vendor", "dist", "build",
}

IGNORE_DIRS_LARGEST: set[str] = IGNORE_DIRS  # same exclusions for largest-file scan

IGNORE_LOCK_NAMES: set[str] = {
    "package-lock.json",
}

IGNORE_LOCK_EXTENSIONS: set[str] = {
    ".lock",
}

CODE_EXTENSIONS: set[str] = {
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".go", ".php", ".dart", ".rs", ".rb",
}


def _is_ignored(path: Path, ignored: set[str]) -> bool:
    """Return True if any component of *path* matches the ignored set."""
    return bool(set(path.parts) & ignored)


def _walk_files(root: Path, ignored: set[str]) -> list[Path]:
    """Collect all regular files under *root*, skipping ignored dirs."""
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignored]
        dp = Path(dirpath)
        for fn in filenames:
            files.append(dp / fn)
    return files


def _count_lines(path: Path) -> int:
    """Count lines in a file, returning 0 on read errors."""
    try:
        with open(path, "rb") as fh:
            return sum(1 for _ in fh)
    except (OSError, PermissionError):
        return 0


def _file_counts(files: list[Path]) -> list[tuple[int, str]]:
    """Return (count, extension) pairs sorted descending, top 15."""
    ext_counter: Counter[str] = Counter()
    for f in files:
        ext = f.suffix.lstrip(".") if f.suffix else f.name
        ext_counter[ext] += 1
    return ext_counter.most_common(15)


def _largest_files(root: Path) -> list[tuple[int, str]]:
    """Return (line_count, path) for the 10 largest files."""
    all_files = _walk_files(root, IGNORE_DIRS_LARGEST)
    eligible = [
        f for f in all_files
        if f.suffix not in IGNORE_LOCK_EXTENSIONS
        and f.name not in IGNORE_LOCK_NAMES
    ]
    counted: list[tuple[int, str]] = []
    for f in eligible:
        lines = _count_lines(f)
        if lines > 0:
            counted.append((lines, str(f)))
    counted.sort(reverse=True)
    return counted[:10]


def _debt_markers(root: Path, files: list[Path]) -> dict[str, int]:
    """Count files containing each debt marker in code files."""
    code_files = [f for f in files if f.suffix in CODE_EXTENSIONS]
    markers = ["TODO", "FIXME", "HACK", "XXX"]
    results: dict[str, int] = {}
    for marker in markers:
        count = 0
        for cf in code_files:
            try:
                with open(cf, "r", errors="replace") as fh:
                    for line in fh:
                        if marker in line:
                            count += 1
                            break
            except (OSError, PermissionError):
                continue
        results[marker] = count
    return results


def _summary(root: Path, all_files: list[Path]) -> tuple[int, int]:
    """Return (total_files, total_code_lines) for the summary."""
    total_files = len(all_files)

    code_files = _walk_files(root, IGNORE_DIRS)
    code_only = [f for f in code_files if f.suffix in CODE_EXTENSIONS]
    total_lines = sum(_count_lines(f) for f in code_only)
    return total_files, total_lines


def main() -> None:
    """Entry point: analyse directory and print text report to stdout."""
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    all_files = _walk_files(root, IGNORE_DIRS)

    print("=== Code Complexity Report ===")
    print(f"Directory: {root}")
    print(f"Date: {now}")
    print()

    # File counts by extension
    print("## File Counts")
    for count, ext in _file_counts(all_files):
        print(f"   {count} {ext}")
    print()

    # Largest files
    print("## Largest Files (top 10)")
    largest = _largest_files(root)
    for lines, path in largest:
        print(f"  {lines} {path}")
    # Include total line if there are entries (mirrors wc behavior)
    if len(largest) > 1:
        total = sum(lc for lc, _ in largest)
        print(f"  {total} total")
    print()

    # Debt markers
    print("## Code Debt Markers")
    for marker, count in _debt_markers(root, all_files).items():
        print(f"  {marker}: {count} files")
    print()

    # Summary
    print("## Summary")
    total_files, total_lines = _summary(root, all_files)
    print(f"  Total files: {total_files}")
    print(f"  Total code lines: {total_lines}")


if __name__ == "__main__":
    main()
