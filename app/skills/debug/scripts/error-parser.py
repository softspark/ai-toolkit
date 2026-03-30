#!/usr/bin/env python3
"""Parse error messages and stack traces from stdin for structured diagnosis.

Reads raw error output piped from a failing command or log file,
detects the programming language (Python, Node.js, Go, PHP), extracts
the error type, message, and stack frames, classifies the error into a
category, and outputs a JSON object with common causes and files to
investigate.

Usage::

    your_command 2>&1 | python3 error-parser.py
    cat /var/log/app/error.log | python3 error-parser.py
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any


LANGUAGE_SIGNATURES: dict[str, list[str]] = {
    "python": [r"Traceback \(most recent call last\)", r"File \".*\", line \d+"],
    "node": [r"at Object\.<anonymous>", r"at Module\.", r"node:internal", r"at .*\(.*\.js:\d+:\d+\)"],
    "go": [r"goroutine \d+", r"panic:", r"\.go:\d+"],
    "php": [r"Fatal error:", r"PHP (?:Warning|Notice|Fatal)", r"Stack trace:", r"\.php:\d+"],
}

ERROR_CATEGORIES: dict[str, list[str]] = {
    "import": [r"ModuleNotFoundError", r"ImportError", r"Cannot find module", r"no required module", r"undefined: "],
    "reference": [r"NameError", r"ReferenceError", r"undefined variable", r"Undefined variable"],
    "type": [r"TypeError", r"type mismatch", r"cannot use .* as type"],
    "connection": [r"ConnectionRefusedError", r"ECONNREFUSED", r"connection refused", r"dial tcp"],
    "timeout": [r"TimeoutError", r"ETIMEDOUT", r"context deadline exceeded", r"Maximum execution time"],
    "memory": [r"MemoryError", r"heap out of memory", r"out of memory", r"Allowed memory size"],
    "permission": [r"PermissionError", r"EACCES", r"permission denied", r"Access denied"],
    "syntax": [r"SyntaxError", r"Unexpected token", r"syntax error", r"Parse error"],
}

COMMON_CAUSES: dict[str, list[str]] = {
    "import": ["Missing dependency (run pip install / npm install)", "Typo in module name", "Virtual environment not activated"],
    "reference": ["Variable used before assignment", "Typo in variable/function name", "Missing import"],
    "type": ["Wrong argument type passed", "None/null not handled", "API response shape changed"],
    "connection": ["Service not running", "Wrong host/port", "Firewall blocking connection"],
    "timeout": ["Service overloaded", "Network latency", "Query too slow - add index"],
    "memory": ["Large dataset loaded into memory", "Memory leak in loop", "Increase memory limit"],
    "permission": ["File ownership issue", "Missing sudo/elevation", "SELinux/AppArmor policy"],
    "syntax": ["Missing bracket/parenthesis", "Invalid JSON/YAML", "Wrong language version"],
}


def detect_language(text: str) -> str:
    """Detect the programming language from characteristic error patterns.

    Scores each supported language by counting how many of its
    signature patterns match the input text and returns the language
    with the highest score.

    Args:
        text: Raw error output text.

    Returns:
        Detected language name or ``"unknown"``.
    """
    scores: dict[str, int] = {}
    for lang, patterns in LANGUAGE_SIGNATURES.items():
        score = sum(1 for p in patterns if re.search(p, text))
        if score > 0:
            scores[lang] = score
    if not scores:
        return "unknown"
    return max(scores, key=scores.get)


def categorize_error(text: str) -> str:
    """Categorize error text into a high-level domain.

    Args:
        text: Raw error output text.

    Returns:
        Category string (e.g. ``"import"``, ``"connection"``) or
        ``"unknown"``.
    """
    for category, patterns in ERROR_CATEGORIES.items():
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return category
    return "unknown"


def extract_frames(text: str, language: str) -> list[dict[str, Any]]:
    """Extract stack trace frames based on the detected language.

    Args:
        text: Raw error output text.
        language: Detected language (``"python"``, ``"node"``, ``"go"``,
            ``"php"``).

    Returns:
        List of frame dictionaries with ``file``, ``line``, and
        ``function`` keys.
    """
    frames: list[dict[str, Any]] = []
    if language == "python":
        for m in re.finditer(r'File "([^"]+)", line (\d+)(?:, in (.+))?', text):
            frames.append({"file": m.group(1), "line": int(m.group(2)), "function": m.group(3) or ""})
    elif language == "node":
        for m in re.finditer(r"at (?:(.+?) \()?(.+?):(\d+):(\d+)\)?", text):
            frames.append({"file": m.group(2), "line": int(m.group(3)), "function": m.group(1) or ""})
    elif language == "go":
        for m in re.finditer(r"(\S+\.go):(\d+)", text):
            frames.append({"file": m.group(1), "line": int(m.group(2)), "function": ""})
    elif language == "php":
        for m in re.finditer(r"(?:#\d+\s+)?(\S+\.php)(?:\((\d+)\))?(?::\s*(.+))?", text):
            frames.append({"file": m.group(1), "line": int(m.group(2)) if m.group(2) else 0, "function": m.group(3) or ""})
    return frames


def extract_error_message(text: str, language: str) -> tuple[str, str]:
    """Extract the primary error type and message from error output.

    Uses language-specific regex patterns to find the error class and
    description. Falls back to searching for lines containing common
    error keywords.

    Args:
        text: Raw error output text.
        language: Detected language identifier.

    Returns:
        A ``(error_type, message)`` tuple.
    """
    patterns: dict[str, str] = {
        "python": r"(\w+Error|\w+Exception|\w+Warning):\s*(.+)",
        "node": r"(\w+Error|\w+Exception):\s*(.+)",
        "go": r"(?:panic:\s*(.+)|fatal error:\s*(.+))",
        "php": r"(?:Fatal error|PHP \w+):\s*(.+?)(?:\s+in\s+|$)",
    }
    pattern = patterns.get(language, r"(\w+Error|\w+Exception):\s*(.+)")
    m = re.search(pattern, text)
    if m:
        groups = [g for g in m.groups() if g]
        if len(groups) >= 2:
            return groups[0], groups[1].strip()
        elif groups:
            return "Error", groups[0].strip()
    # Fallback: first non-empty line that looks like an error
    for line in text.split("\n"):
        line = line.strip()
        if line and any(kw in line.lower() for kw in ["error", "exception", "fatal", "panic"]):
            return "Error", line[:200]
    return "Unknown", "Could not parse error message"


def main() -> None:
    """Entry point: read stdin, parse errors, and print JSON to stdout."""
    text = sys.stdin.read()
    if not text.strip():
        print(json.dumps({"error": "No input provided. Pipe error output to stdin."}))
        return

    language = detect_language(text)
    error_type, message = extract_error_message(text, language)
    category = categorize_error(text)
    frames = extract_frames(text, language)
    causes = COMMON_CAUSES.get(category, ["Unknown error category - manual investigation required"])

    # Files to check - unique files from stack frames
    files_to_check = list(dict.fromkeys(f["file"] for f in frames if f["file"]))[:10]

    result: dict[str, Any] = {
        "language": language,
        "error_type": error_type,
        "message": message,
        "category": category,
        "stack_frames": frames[:20],
        "files_to_check": files_to_check,
        "common_causes": causes,
        "raw_lines": len(text.split("\n")),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
