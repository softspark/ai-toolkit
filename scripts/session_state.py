#!/usr/bin/env python3
"""Session edit state tracker for ai-toolkit hooks.

Stores per-session file edits so hooks can:
- Know which paths were touched (revert-guard, test-cohesion).
- Run only related tests (quality-gate ai-toolkit branch).

State file: ``~/.softspark/ai-toolkit/state/session-edits.json``

Usage:
    session_state.py reset [--session-id ID]
    session_state.py append --tool Edit --path /abs/path [--session-id ID]
    session_state.py was-edited /abs/path
    session_state.py list
    session_state.py session-id

Exit codes:
    0  success / true
    1  false / not found (for boolean queries)
    2  usage error
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import uuid
from pathlib import Path

STATE_DIR = Path(os.path.expanduser("~/.softspark/ai-toolkit/state"))
STATE_FILE = STATE_DIR / "session-edits.json"
MAX_EDITS = 5000  # cap to avoid unbounded growth


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _load() -> dict:
    if not STATE_FILE.is_file():
        return {"session_id": "", "started_at": "", "edits": []}
    try:
        with STATE_FILE.open() as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"session_id": "", "started_at": "", "edits": []}
    data.setdefault("session_id", "")
    data.setdefault("started_at", "")
    data.setdefault("edits", [])
    return data


def _save(data: dict) -> None:
    _ensure_dir()
    tmp = STATE_FILE.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, STATE_FILE)


def cmd_reset(session_id: str | None) -> int:
    sid = session_id or str(uuid.uuid4())
    _save({"session_id": sid, "started_at": _now(), "edits": []})
    return 0


def cmd_append(tool: str, path: str, session_id: str | None) -> int:
    if not path:
        return 0  # silently ignore tools without file_path (e.g., bash)
    data = _load()
    if session_id and data["session_id"] != session_id:
        # New session detected mid-stream — auto-reset.
        cmd_reset(session_id)
        data = _load()
    abs_path = os.path.abspath(path)
    data["edits"].append({"ts": _now(), "tool": tool, "path": abs_path})
    if len(data["edits"]) > MAX_EDITS:
        data["edits"] = data["edits"][-MAX_EDITS:]
    _save(data)
    return 0


def cmd_was_edited(path: str) -> int:
    abs_path = os.path.abspath(path)
    data = _load()
    for edit in data["edits"]:
        if edit.get("path") == abs_path:
            return 0
    return 1


def cmd_list() -> int:
    data = _load()
    seen: set[str] = set()
    for edit in data["edits"]:
        p = edit.get("path", "")
        if p and p not in seen:
            seen.add(p)
            print(p)
    return 0


def cmd_session_id() -> int:
    data = _load()
    print(data.get("session_id", ""))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Session edit state tracker")
    sub = parser.add_subparsers(dest="cmd", required=True)

    reset = sub.add_parser("reset", help="Clear state, start fresh session")
    reset.add_argument("--session-id", default=None)

    append = sub.add_parser("append", help="Record an edit")
    append.add_argument("--tool", required=True)
    append.add_argument("--path", required=True)
    append.add_argument("--session-id", default=None)

    was = sub.add_parser("was-edited", help="Exit 0 if path was edited this session")
    was.add_argument("path")

    sub.add_parser("list", help="Print unique edited paths, one per line")
    sub.add_parser("session-id", help="Print current session id")

    args = parser.parse_args(argv)

    if args.cmd == "reset":
        return cmd_reset(args.session_id)
    if args.cmd == "append":
        return cmd_append(args.tool, args.path, args.session_id)
    if args.cmd == "was-edited":
        return cmd_was_edited(args.path)
    if args.cmd == "list":
        return cmd_list()
    if args.cmd == "session-id":
        return cmd_session_id()
    return 2


if __name__ == "__main__":
    sys.exit(main())
