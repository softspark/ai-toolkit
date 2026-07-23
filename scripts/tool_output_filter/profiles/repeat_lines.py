"""Compact adjacent identical output lines."""

from __future__ import annotations

PROFILE_ID = "repeat-lines"
PROFILE_VERSION = 1

_DIAGNOSTIC_PREFIXES = (
    "error",
    "warning",
    "warn:",
    "fatal",
    "fail",
    "not ok",
    "npm err!",
    "critical",
    "segmentation fault",
    "traceback",
    "exception",
    "panic",
    "assert",
    "e   ",
    "✕",
    "✗",
    "security",
    "vulnerab",
    "cve-",
    "denied",
    "unauthor",
    "permission",
)


def _is_diagnostic(line: str) -> bool:
    if not line.strip():
        return True
    stripped = line.lstrip().lower()
    return (
        stripped.startswith(_DIAGNOSTIC_PREFIXES)
        or stripped.startswith("#")
        or stripped.startswith("[ai-toolkit-output-filter ")
        or "\x1b" in line
        or "\x00" in line
    )


def transform(output: str) -> str:
    """Collapse adjacent identical lines while preserving their first copy."""

    lines = output.splitlines(keepends=True)
    if not lines:
        return output

    transformed: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        run_end = index + 1
        while run_end < len(lines) and lines[run_end] == line:
            run_end += 1
        run_length = run_end - index
        transformed.append(line)
        if run_length > 1 and not _is_diagnostic(line):
            transformed.append(
                "[ai-toolkit-output-filter repeat-lines/v1: "
                f"{run_length - 1} adjacent copies omitted]\n"
            )
        elif run_length > 1:
            transformed.extend(lines[index + 1 : run_end])
        index = run_end
    return "".join(transformed)
