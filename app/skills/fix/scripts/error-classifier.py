#!/usr/bin/env python3
"""Parse lint/test error output from stdin and classify as auto-fixable or manual.

Reads multi-tool error output (ruff, mypy, ESLint, tsc, phpstan) from
stdin, parses each line into structured records, and classifies every
error as either auto-fixable or requiring manual intervention. The
output is a JSON object with error counts, a prioritised file order
(auto-fixable first), and a suggested fix strategy.

Usage::

    ruff check . 2>&1 | python3 error-classifier.py
    mypy src/ 2>&1 | python3 error-classifier.py
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any


# Patterns to parse error formats: (file, line, col_or_none, code_or_none, message)
ERROR_PARSERS: dict[str, re.Pattern[str]] = {
    "ruff": re.compile(r"^(.+?):(\d+):(\d+):\s+([A-Z]\d+)\s+(.+)$"),
    "mypy": re.compile(r"^(.+?):(\d+):\s+error:\s+(.+?)(?:\s+\[(.+)\])?$"),
    "eslint": re.compile(r"^\s*(\d+):(\d+)\s+(error|warning)\s+(.+?)\s+(\S+)$"),
    "tsc": re.compile(r"^(.+?)\((\d+),(\d+)\):\s+error\s+(TS\d+):\s+(.+)$"),
    "phpstan": re.compile(r"^(.+?):(\d+)\s+(.+)$"),
}

# Auto-fixable error codes/patterns
AUTO_FIXABLE: dict[str, str] = {
    # Ruff
    "F401": "unused import",
    "F841": "unused variable",
    "W291": "trailing whitespace",
    "W292": "no newline at end of file",
    "W293": "whitespace before ':'",
    "E301": "expected blank lines",
    "E302": "expected 2 blank lines",
    "E303": "too many blank lines",
    "E501": "line too long",
    "I001": "import sort order",
    "C408": "unnecessary dict/list call",
    "UP": "pyupgrade",
    # ESLint
    "no-unused-vars": "unused variable",
    "semi": "missing semicolon",
    "indent": "indentation",
    "quotes": "quote style",
    "comma-dangle": "trailing comma",
    "eol-last": "newline at end",
}


def is_auto_fixable(code: str | None) -> bool:
    """Check if an error code is auto-fixable.

    Matches exact codes and short prefix patterns (e.g. ``"UP"`` matches
    ``"UP006"``).

    Args:
        code: The error code string, or ``None``.

    Returns:
        ``True`` if the error can be fixed automatically.
    """
    if not code:
        return False
    if code in AUTO_FIXABLE:
        return True
    # Check prefix matches (e.g., UP006 matches "UP")
    for prefix in AUTO_FIXABLE:
        if len(prefix) <= 3 and code.startswith(prefix):
            return True
    return False


def _err(
    tool: str,
    file: str,
    line: str | int,
    col: str | int,
    code: str | None,
    msg: str,
) -> dict[str, Any]:
    """Build a structured error dictionary.

    Args:
        tool: Name of the tool that produced the error.
        file: Source file path.
        line: Line number (converted to int).
        col: Column number (converted to int).
        code: Error code or rule identifier.
        msg: Human-readable error message.

    Returns:
        Dictionary with tool, file, line, column, code, message, and
        auto_fixable flag.
    """
    return {"tool": tool, "file": file, "line": int(line), "column": int(col),
            "code": code, "message": msg, "auto_fixable": is_auto_fixable(code)}


def parse_errors(text: str) -> list[dict[str, Any]]:
    """Parse multi-tool error output and return structured error records.

    Supports ruff, mypy, tsc, and ESLint output formats. ESLint is
    detected via a file-header line followed by indented error lines.

    Args:
        text: Raw error output text, typically from stdout/stderr.

    Returns:
        List of structured error dictionaries.
    """
    errors: list[dict[str, Any]] = []
    eslint_file: str | None = None
    for line in text.strip().split("\n"):
        line = line.rstrip()
        if not line:
            continue
        m = ERROR_PARSERS["ruff"].match(line)
        if m:
            errors.append(_err("ruff", m[1], m[2], m[3], m[4], m[5]))
            continue
        m = ERROR_PARSERS["mypy"].match(line)
        if m:
            errors.append(_err("mypy", m[1], m[2], 0, m[4] or "mypy", m[3]))
            continue
        m = ERROR_PARSERS["tsc"].match(line)
        if m:
            errors.append(_err("tsc", m[1], m[2], m[3], m[4], m[5]))
            continue
        # ESLint: file header then indented errors
        if re.match(r"^[/.]", line) and not re.search(r":\d+", line):
            eslint_file = line.strip()
            continue
        m = ERROR_PARSERS["eslint"].match(line)
        if m and eslint_file:
            errors.append(_err("eslint", eslint_file, m[1], m[2], m[5], m[4]))
    return errors


def main() -> None:
    """Entry point: read stdin, classify errors, and print JSON to stdout."""
    text = sys.stdin.read()
    if not text.strip():
        print(json.dumps({"error": "No input provided. Pipe lint/test output to stdin."}))
        return

    errors = parse_errors(text)
    auto_fixable = [e for e in errors if e["auto_fixable"]]
    manual = [e for e in errors if not e["auto_fixable"]]

    # Group by file for suggested order
    file_order: list[str] = []
    seen: set[str] = set()
    # Auto-fixable files first
    for e in auto_fixable:
        if e["file"] not in seen:
            seen.add(e["file"])
            file_order.append(e["file"])
    # Then manual files
    for e in manual:
        if e["file"] not in seen:
            seen.add(e["file"])
            file_order.append(e["file"])

    # Tool summary
    tools_detected = list(set(e["tool"] for e in errors))

    result: dict[str, Any] = {
        "total_errors": len(errors),
        "auto_fixable_count": len(auto_fixable),
        "manual_count": len(manual),
        "tools_detected": tools_detected,
        "errors": errors,
        "suggested_order": file_order,
        "fix_strategy": (
            "Run auto-fix first (e.g., ruff check --fix .), then address manual errors."
            if auto_fixable
            else "All errors require manual intervention."
        ),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
