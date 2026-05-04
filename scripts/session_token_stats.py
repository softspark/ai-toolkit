#!/usr/bin/env python3
"""Read Claude Code session JSONL files and report real token usage.

Claude Code writes one JSONL line per message to:
    ~/.claude/projects/<sanitized-cwd>/<session-id>.jsonl

Each message contains a `usage` block with input_tokens, output_tokens,
cache_creation_input_tokens, and cache_read_input_tokens. This script
parses those blocks and emits aggregate or per-session reports.

Usage:
    python3 scripts/session_token_stats.py [options]

Options:
    --session PATH         Path to a single session JSONL (default: latest)
    --project-dir PATH     Look only in this project's session dir
    --claude-dir PATH      Override ~/.claude (for testing)
    --since DURATION       Filter to messages newer than 7d|24h|30m
    --json                 Emit JSON instead of human-readable text
    --statusline           One-line statusline-friendly output
    --baseline FILE        Compare current session vs a baseline JSON file

Exit codes:
    0  success
    1  no sessions found
    2  invalid arguments or filesystem error

Stdlib-only. Designed to run in the statusline hot path (<50ms target).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator


DEFAULT_CLAUDE_DIR = Path.home() / ".claude"
DURATION_RE = re.compile(r"^(\d+)([smhd])$")


def parse_duration(value: str) -> timedelta:
    """Parse 7d, 24h, 30m, 90s into a timedelta. Raises ValueError on bad input."""
    match = DURATION_RE.match(value)
    if not match:
        raise ValueError(f"invalid duration: {value!r}; expected e.g. 7d, 24h, 30m")
    n = int(match.group(1))
    unit = match.group(2)
    if unit == "s":
        return timedelta(seconds=n)
    if unit == "m":
        return timedelta(minutes=n)
    if unit == "h":
        return timedelta(hours=n)
    return timedelta(days=n)


def sanitize_cwd(cwd: str) -> str:
    """Claude Code mangles `/` to `-` and prefixes with `-` for project dir name."""
    return "-" + cwd.replace("/", "-").lstrip("-")


def find_project_dir(claude_dir: Path, cwd: str | None = None) -> Path | None:
    """Locate the project sessions directory for cwd, or None if missing."""
    projects_root = claude_dir / "projects"
    if not projects_root.is_dir():
        return None
    if cwd:
        candidate = projects_root / sanitize_cwd(cwd)
        return candidate if candidate.is_dir() else None
    return projects_root


def find_latest_session(search_dir: Path) -> Path | None:
    """Return the most-recently-modified .jsonl under search_dir, or None."""
    if not search_dir.is_dir():
        return None
    candidates = list(search_dir.rglob("*.jsonl"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def iter_messages(session_file: Path) -> Iterator[dict[str, Any]]:
    """Yield parsed JSON messages from a session file. Skips malformed lines.

    Lines without a `usage` field are skipped without parsing — most lines in a
    Claude Code session JSONL are user inputs, tool results, etc. that have no
    token cost. Filtering at the substring level avoids json.loads on ~80% of
    the file and cuts parse time roughly in half on long sessions.
    """
    try:
        with open(session_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or '"usage"' not in line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def extract_usage(message: dict[str, Any]) -> dict[str, int] | None:
    """Pull usage block from a message, normalizing field names. Returns None if absent."""
    usage = None
    if isinstance(message.get("message"), dict):
        usage = message["message"].get("usage")
    if usage is None:
        usage = message.get("usage")
    if not isinstance(usage, dict):
        return None
    return {
        "input": int(usage.get("input_tokens") or 0),
        "output": int(usage.get("output_tokens") or 0),
        "cache_create": int(usage.get("cache_creation_input_tokens") or 0),
        "cache_read": int(usage.get("cache_read_input_tokens") or 0),
    }


def message_timestamp(message: dict[str, Any]) -> datetime | None:
    """Extract message timestamp. Tries common field names."""
    for key in ("timestamp", "created_at", "time"):
        value = message.get(key)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def aggregate(
    session_file: Path,
    since: timedelta | None = None,
) -> dict[str, Any]:
    """Sum token usage across a session, optionally filtered by recency."""
    cutoff = datetime.now(timezone.utc) - since if since else None
    totals = {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0}
    message_count = 0
    counted = 0

    for message in iter_messages(session_file):
        message_count += 1
        if cutoff is not None:
            ts = message_timestamp(message)
            if ts is None or ts < cutoff:
                continue
        usage = extract_usage(message)
        if usage is None:
            continue
        for key, value in usage.items():
            totals[key] += value
        counted += 1

    totals["total"] = totals["input"] + totals["output"]
    totals["total_with_cache"] = (
        totals["total"] + totals["cache_create"] + totals["cache_read"]
    )
    totals["messages_total"] = message_count
    totals["messages_counted"] = counted
    return totals


def format_human(totals: dict[str, Any], session_file: Path) -> str:
    lines = [
        f"session: {session_file.name}",
        f"  input        {totals['input']:>10,}",
        f"  output       {totals['output']:>10,}",
        f"  cache_create {totals['cache_create']:>10,}",
        f"  cache_read   {totals['cache_read']:>10,}",
        f"  total        {totals['total']:>10,}",
        f"  with cache   {totals['total_with_cache']:>10,}",
        f"  messages     {totals['messages_counted']}/{totals['messages_total']}",
    ]
    return "\n".join(lines)


def format_statusline(totals: dict[str, Any], baseline: dict[str, Any] | None) -> str:
    total = totals["total"]
    if total >= 1000:
        rendered = f"{total / 1000:.1f}k"
    else:
        rendered = str(total)
    output = f"[ai-toolkit] session: {rendered}"
    if baseline:
        baseline_total = baseline.get("total")
        if isinstance(baseline_total, int) and baseline_total > 0:
            delta = (total - baseline_total) / baseline_total
            arrow = "↓" if delta < 0 else "↑" if delta > 0 else "·"
            output += f" · trend: {arrow}{abs(delta) * 100:.0f}%"
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, help="Path to a session JSONL")
    parser.add_argument("--project-dir", type=Path, help="Look only in this project's session dir")
    parser.add_argument("--claude-dir", type=Path, default=DEFAULT_CLAUDE_DIR)
    parser.add_argument("--cwd", type=str, default=os.getcwd())
    parser.add_argument("--since", type=str)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--statusline", action="store_true")
    parser.add_argument("--baseline", type=Path, help="JSON baseline for trend comparison")
    args = parser.parse_args()

    try:
        since = parse_duration(args.since) if args.since else None
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.session:
        session_file: Path | None = args.session
    elif args.project_dir:
        session_file = find_latest_session(args.project_dir)
    else:
        project_dir = find_project_dir(args.claude_dir, args.cwd)
        if project_dir is None:
            print("error: no Claude Code project directory found", file=sys.stderr)
            return 1
        session_file = find_latest_session(project_dir)

    if not session_file or not session_file.is_file():
        print("error: no session file found", file=sys.stderr)
        return 1

    totals = aggregate(session_file, since=since)

    baseline = None
    if args.baseline and args.baseline.is_file():
        try:
            baseline = json.loads(args.baseline.read_text())
        except (json.JSONDecodeError, OSError):
            baseline = None

    if args.statusline:
        print(format_statusline(totals, baseline))
        return 0

    if args.json:
        payload = {"session": str(session_file), "totals": totals}
        if baseline:
            payload["baseline"] = baseline
        print(json.dumps(payload, indent=2))
        return 0

    print(format_human(totals, session_file))
    return 0


if __name__ == "__main__":
    sys.exit(main())
