#!/usr/bin/env python3
"""Session edit state tracker for ai-toolkit hooks.

Stores per-session file edits so hooks can:
- Know which paths were touched (revert-guard, test-cohesion).
- Run only related tests (quality-gate ai-toolkit branch).

State files: ``~/.softspark/ai-toolkit/state/session-edits-<hash>.json``.
The legacy ``session-edits.json`` alias tracks the most recently active session.

Usage:
    session_state.py reset [--session-id ID]
    session_state.py append --tool Edit --path /abs/path [--session-id ID]
    session_state.py was-edited /abs/path [--session-id ID]
    session_state.py list [--session-id ID]
    session_state.py session-id [--session-id ID]
    session_state.py clean --session-id ID

Exit codes:
    0  success / true
    1  false / not found (for boolean queries)
    2  usage error
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import stat
import sys
import tempfile
import uuid
from pathlib import Path

STATE_DIR = Path(os.path.expanduser("~/.softspark/ai-toolkit/state"))
STATE_FILE = STATE_DIR / "session-edits.json"
MAX_EDITS = 5000  # cap to avoid unbounded growth


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _state_file(session_id: str | None) -> Path:
    if not session_id:
        return STATE_FILE
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    return STATE_DIR / f"session-edits-{digest}.json"


def _empty_state(session_id: str = "") -> dict:
    return {"session_id": session_id, "started_at": "", "edits": []}


def _validated_state(data: object, session_id: str | None) -> dict:
    fallback = _empty_state(session_id or "")
    if not isinstance(data, dict):
        return fallback
    stored_session = data.get("session_id", session_id or "")
    started_at = data.get("started_at", "")
    edits = data.get("edits", [])
    if not isinstance(stored_session, str) or not isinstance(started_at, str):
        return fallback
    if not isinstance(edits, list) or any(
        not isinstance(edit, dict)
        or not isinstance(edit.get("path", ""), str)
        for edit in edits
    ):
        return fallback
    return {
        "session_id": stored_session,
        "started_at": started_at,
        "edits": edits,
    }


def _load(session_id: str | None = None) -> dict:
    state_file = _state_file(session_id)
    if not state_file.is_file():
        return _empty_state(session_id or "")
    try:
        with state_file.open(encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeError):
        return _empty_state(session_id or "")
    return _validated_state(data, session_id)


def _atomic_save(state_file: Path, data: dict) -> None:
    _ensure_dir()
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=STATE_DIR,
            prefix=f".{state_file.name}.",
            encoding="utf-8",
            delete=False,
        ) as temp_file:
            json.dump(data, temp_file, indent=2)
            temp_file.write("\n")
            temp_path = Path(temp_file.name)
        os.replace(temp_path, state_file)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _save(data: dict, session_id: str | None = None) -> None:
    _atomic_save(_state_file(session_id), data)
    if session_id:
        # Preserve no-ID CLI behavior without making it the source of truth.
        _atomic_save(STATE_FILE, data)


def cmd_reset(session_id: str | None) -> int:
    sid = session_id or str(uuid.uuid4())
    _save({"session_id": sid, "started_at": _now(), "edits": []}, session_id)
    return 0


def cmd_append(tool: str, path: str, session_id: str | None) -> int:
    if not path:
        return 0  # silently ignore tools without file_path (e.g., bash)
    data = _load(session_id)
    if session_id and data["session_id"] != session_id:
        data = _empty_state(session_id)
    if not data["started_at"]:
        data["started_at"] = _now()
    abs_path = os.path.abspath(path)
    data["edits"].append({"ts": _now(), "tool": tool, "path": abs_path})
    if len(data["edits"]) > MAX_EDITS:
        data["edits"] = data["edits"][-MAX_EDITS:]
    _save(data, session_id)
    return 0


def cmd_was_edited(path: str, session_id: str | None) -> int:
    abs_path = os.path.abspath(path)
    data = _load(session_id)
    for edit in data["edits"]:
        if edit.get("path") == abs_path:
            return 0
    return 1


def cmd_list(session_id: str | None) -> int:
    data = _load(session_id)
    seen: set[str] = set()
    for edit in data["edits"]:
        path = edit.get("path", "")
        if path and path not in seen:
            seen.add(path)
            print(path)
    return 0


def cmd_session_id(session_id: str | None) -> int:
    data = _load(session_id)
    print(data.get("session_id", ""))
    return 0


def cmd_clean(session_id: str) -> int:
    """Remove the selected hashed state and its matching legacy alias."""
    state_file = _state_file(session_id)
    try:
        metadata = state_file.lstat()
    except FileNotFoundError:
        _clean_matching_legacy_alias(session_id)
        return 0
    if not stat.S_ISREG(metadata.st_mode):
        return 2
    try:
        state_file.unlink()
    except FileNotFoundError:
        pass
    _clean_matching_legacy_alias(session_id)
    return 0


def _clean_matching_legacy_alias(session_id: str) -> None:
    """Remove the compatibility alias only when it names this session."""
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(
        os,
        "O_NOFOLLOW",
        0,
    )
    try:
        descriptor = os.open(STATE_FILE, flags)
    except OSError:
        return
    opened_metadata = os.fstat(descriptor)
    try:
        with os.fdopen(descriptor, encoding="utf-8") as state_handle:
            data = json.load(state_handle)
    except (json.JSONDecodeError, OSError, UnicodeError):
        return
    if isinstance(data, dict) and data.get("session_id") == session_id:
        try:
            current_metadata = STATE_FILE.lstat()
            if (
                not stat.S_ISREG(current_metadata.st_mode)
                or current_metadata.st_dev != opened_metadata.st_dev
                or current_metadata.st_ino != opened_metadata.st_ino
            ):
                return
            STATE_FILE.unlink()
        except FileNotFoundError:
            pass


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
    was.add_argument("--session-id", default=None)

    list_parser = sub.add_parser("list", help="Print unique edited paths, one per line")
    list_parser.add_argument("--session-id", default=None)
    session_parser = sub.add_parser("session-id", help="Print current session id")
    session_parser.add_argument("--session-id", default=None)
    clean_parser = sub.add_parser(
        "clean",
        help="Remove one session-scoped edit state file",
    )
    clean_parser.add_argument("--session-id", required=True)

    args = parser.parse_args(argv)

    if args.cmd == "reset":
        return cmd_reset(args.session_id)
    if args.cmd == "append":
        return cmd_append(args.tool, args.path, args.session_id)
    if args.cmd == "was-edited":
        return cmd_was_edited(args.path, args.session_id)
    if args.cmd == "list":
        return cmd_list(args.session_id)
    if args.cmd == "session-id":
        return cmd_session_id(args.session_id)
    if args.cmd == "clean":
        return cmd_clean(args.session_id)
    return 2


if __name__ == "__main__":
    sys.exit(main())
