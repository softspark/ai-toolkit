#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Container-side half of the rtk replay. Stdlib only, no package imports.

Usage (inside the replay container):
    python3 runner.py RECORDS_JSONL RESULTS_JSONL

Each record is ``{"key", "command", "output"}``: a Bash command an agent ran and
the output the model saw. For each one this asks rtk's own Claude hook — the
entry point an agent actually hits — whether it would rewrite the command, and,
when the rewrite is a single rtk call with a stdin filter, pipes the recorded
output through that filter.

Results carry sizes and rtk family names only. No command text and no output
leaves this script, so the results file holds nothing the transcripts were
trusted with.

Known limit, reported rather than hidden: ``rtk pipe`` runs the same filter code
as the live command but with its own result caps (grep keeps 10 matches per file
where live ``rtk grep`` keeps 25 and shortens lines), so per-family figures are
a proxy for what the live path would produce.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Any

RTK = "/opt/rtk/rtk"
WHITESPACE = frozenset(b" \t\r\n")

# rtk subcommand (and second word, where the filter depends on it) -> `rtk pipe -f` name.
PIPE_FILTERS: dict[tuple[str, ...], str] = {
    ("git", "status"): "git-status",
    ("git", "log"): "git-log",
    ("git", "diff"): "git-diff",
    ("grep",): "grep",
    ("rg",): "rg",
    ("find",): "find",
    ("fd",): "fd",
    ("cargo", "test"): "cargo-test",
    ("pytest",): "pytest",
    ("go", "test"): "go-test",
    ("go", "build"): "go-build",
    ("tsc",): "tsc",
    ("vitest",): "vitest",
    ("mypy",): "mypy",
    ("ruff", "check"): "ruff-check",
    ("ruff", "format"): "ruff-format",
    ("prettier",): "prettier",
    ("ctest",): "ctest",
    ("log",): "log",
}
TWO_WORD_FAMILIES = frozenset({"git", "go", "cargo", "ruff", "gh", "glab", "docker", "kubectl", "npm", "pnpm"})
INVOCATION = re.compile(r"(?:^|[\s;&|(])rtk\s+([A-Za-z][\w.-]*)(?:\s+([A-Za-z][\w.-]*))?")


def invocations(command: str) -> list[tuple[str, str | None]]:
    return [(m.group(1), m.group(2)) for m in INVOCATION.finditer(command)]


def family(sub: str, nxt: str | None) -> str:
    return f"{sub} {nxt}" if sub in TWO_WORD_FAMILIES and nxt else sub


def pipe_filter(sub: str, nxt: str | None) -> str | None:
    return PIPE_FILTERS.get((sub, nxt or "")) or PIPE_FILTERS.get((sub,))


def rewritten_command(hook_stdout: str) -> str | None:
    """The command rtk's Claude hook substitutes, or None when it leaves the call alone."""
    if not hook_stdout.strip():
        return None
    try:
        payload = json.loads(hook_stdout)
    except json.JSONDecodeError:
        return None
    output = payload.get("hookSpecificOutput") if isinstance(payload, dict) else None
    updated = output.get("updatedInput") if isinstance(output, dict) else None
    command = updated.get("command") if isinstance(updated, dict) else None
    return command if isinstance(command, str) else None


def whitespace_bytes(data: bytes) -> int:
    return sum(1 for b in data if b in WHITESPACE)


def replay(record: dict[str, Any], rtk: str = RTK) -> dict[str, Any]:
    command = str(record.get("command", ""))
    output = str(record.get("output", "")).encode("utf-8")
    hook_input = json.dumps({
        "hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command},
        "session_id": "replay", "cwd": "/tmp", "transcript_path": "/tmp/replay.jsonl",
    })
    hook = subprocess.run([rtk, "hook", "claude"], input=hook_input, capture_output=True, text=True, timeout=30)
    rewritten = rewritten_command(hook.stdout) if hook.returncode == 0 else None
    calls = invocations(rewritten) if rewritten else []
    result: dict[str, Any] = {
        "key": record.get("key"),
        "hook_rc": hook.returncode,
        "rewritten": rewritten is not None,
        "rtk_calls": len(calls),
        "families": sorted({family(sub, nxt) for sub, nxt in calls}),
        "pipeline_after_rtk": bool(rewritten and re.search(r"rtk\s[^|]*\|", rewritten)),
        "raw_bytes": len(output),
        "raw_whitespace": whitespace_bytes(output),
        "filter": None,
        "filtered_bytes": None,
        "filtered_whitespace": None,
        "pipe_rc": None,
    }
    if len(calls) == 1 and output:
        name = pipe_filter(*calls[0])
        if name:
            piped = subprocess.run([rtk, "pipe", "-f", name], input=output, capture_output=True, timeout=60)
            result.update(filter=name, pipe_rc=piped.returncode)
            if piped.returncode == 0:
                result.update(filtered_bytes=len(piped.stdout), filtered_whitespace=whitespace_bytes(piped.stdout))
    return result


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    os.makedirs(os.environ.get("HOME", "/tmp/h"), exist_ok=True)
    with open(argv[1], encoding="utf-8") as source, open(argv[2], "w", encoding="utf-8") as sink:
        for line in source:
            if line.strip():
                sink.write(json.dumps(replay(json.loads(line))) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
