#!/usr/bin/env python3
"""Manual and hook entry points for native tool-output filtering."""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from tool_output_filter.contracts import FilterMode, FilterRequest
from tool_output_filter.contracts import (
    DEFAULT_MAX_INPUT_BYTES,
    DEFAULT_MIN_SAVINGS_BYTES,
    DEFAULT_MIN_SAVINGS_RATIO,
)
from tool_output_filter.engine import filter_output
from tool_output_filter.hook_runtime import run_hook
from tool_output_filter.input import read_bounded_text
from tool_output_filter.policy import OutputFilterPolicy, load_policy
from tool_output_filter.recovery import (
    EphemeralRecoveryStore,
    clean_owned_repo_recovery,
    clean_session,
    recover_by_handle,
)

if TYPE_CHECKING:
    import argparse

_OWNER_MARKER = "ai-toolkit-output-filter-policy-v1"
_INSPECT_PROFILES = frozenset({"repeat-lines", "tap-success"})


def _infer_repo_root(start: Path) -> Path | None:
    # realpath keeps the repo key aligned with the bash hooks, which resolve
    # symlinks via `git rev-parse --show-toplevel`.
    candidate_path = Path(
        os.path.realpath(os.path.expanduser(str(start)))
    )
    if not candidate_path.is_dir():
        return None
    for candidate in (candidate_path, *candidate_path.parents):
        git_marker = candidate / ".git"
        if git_marker.is_dir() or git_marker.is_file():
            return candidate
    return candidate_path


def _session_base_for_repo(repo_root: Path) -> Path:
    repo_key = "-" + str(repo_root).replace("/", "-").lstrip("-")
    return (
        Path.home()
        / ".softspark"
        / "ai-toolkit"
        / "sessions"
        / repo_key
    )


def _manual_session_base() -> Path | None:
    project_directory = os.environ.get("CLAUDE_PROJECT_DIR")
    repo_root = _infer_repo_root(
        Path(project_directory) if project_directory else Path.cwd()
    )
    return _session_base_for_repo(repo_root) if repo_root is not None else None


def _is_regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _is_registered_project(project_root: Path) -> bool:
    """Trust only projects registered via `ai-toolkit install --local`.

    The owner marker is a public constant, so a cloned repo must never be
    able to self-enable filtering with it. Mirrors filter-tool-output.sh.
    """
    registry = (
        Path.home() / ".softspark" / "ai-toolkit" / "projects.json"
    )
    if not _is_regular_file(registry):
        return False
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    projects = data.get("projects") if isinstance(data, dict) else None
    if not isinstance(projects, list):
        return False
    root_text = str(project_root)
    return any(
        isinstance(entry, dict) and entry.get("path") == root_text
        for entry in projects
    )


def _trusted_project_policy(project_root: Path) -> Path | None:
    managed_directory = project_root / ".claude"
    if project_root.is_symlink() or managed_directory.is_symlink():
        return None
    if not _is_registered_project(project_root):
        return None
    policy_path = managed_directory / "ai-toolkit-output-filter.json"
    owner_path = managed_directory / ".ai-toolkit-output-filter.owner"
    if not _is_regular_file(policy_path) or not _is_regular_file(owner_path):
        return None
    try:
        owner_text = owner_path.read_text(encoding="utf-8")
    except OSError:
        return None
    # The bash hook's $(<file) strips trailing newlines; accept the same.
    if owner_text.rstrip("\n") != _OWNER_MARKER:
        return None
    return policy_path


def _resolve_policy_path(explicit_path: Path | None) -> Path | None:
    if explicit_path is not None:
        return explicit_path
    # Same resolution as filter-tool-output.sh: the project directory only,
    # never its parents, so `status` reports what the hook will actually do.
    project_directory = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    project_policy = _trusted_project_policy(Path(project_directory))
    if project_policy is not None:
        return project_policy
    global_policy = (
        Path.home()
        / ".softspark"
        / "ai-toolkit"
        / "hooks"
        / "output-filter-policy.json"
    )
    return global_policy if _is_regular_file(global_policy) else None


def _default_policy() -> OutputFilterPolicy:
    return OutputFilterPolicy(
        mode=FilterMode.OFF,
        profiles=("repeat-lines", "tap-success"),
    )


def _run_status(policy_path: Path | None) -> int:
    resolved_path = _resolve_policy_path(policy_path)
    if resolved_path is None:
        policy = _default_policy()
    else:
        try:
            policy = load_policy(resolved_path)
        except (OSError, TypeError, ValueError, KeyError):
            return 2
    output = {
        "mode": policy.mode.value,
        "profiles": list(policy.profiles),
        "maxInputBytes": policy.max_input_bytes,
        "minSavingsBytes": policy.min_savings_bytes,
        "minSavingsRatio": policy.min_savings_ratio,
        "recovery": {
            "mode": "ephemeral",
            "ttlMinutes": policy.ttl_minutes,
            "maxSessionBytes": policy.max_session_bytes,
        },
    }
    print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    return 0


def _run_inspect(args: argparse.Namespace) -> int:
    if not _valid_inspect_arguments(args):
        return 2
    try:
        raw_output = read_bounded_text(
            sys.stdin.buffer,
            max_bytes=args.max_input_bytes,
        )
    except (TypeError, UnicodeDecodeError, ValueError):
        return 2
    if raw_output is None:
        report = {
            "profile": args.profile,
            "eligible": False,
            "outcome": "passthrough",
            "fallbackReason": "input-too-large",
            "inputBytesAtLeast": args.max_input_bytes + 1,
            "maxInputBytes": args.max_input_bytes,
        }
        print(json.dumps(report, separators=(",", ":")))
        return 0
    request = FilterRequest(
        output=raw_output,
        mode=FilterMode.OBSERVE,
        profile_id=args.profile,
        max_input_bytes=args.max_input_bytes,
        min_savings_bytes=args.min_savings_bytes,
        min_savings_ratio=args.min_savings_ratio,
    )
    result = filter_output(request)
    telemetry = result.telemetry
    input_bytes = len(raw_output.encode("utf-8"))
    report = {
        "profile": args.profile,
        "eligible": result.outcome == "observed",
        "outcome": result.outcome,
        "fallbackReason": result.fallback_reason,
        "inputBytes": input_bytes,
        "candidateBytes": (
            telemetry.output_bytes if telemetry is not None else input_bytes
        ),
        "inputLines": len(raw_output.splitlines()),
        "candidateLines": (
            telemetry.output_lines
            if telemetry is not None
            else len(raw_output.splitlines())
        ),
    }
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return 0


def _valid_inspect_arguments(args: argparse.Namespace) -> bool:
    """Reject unsafe manual limits before consuming stdin."""
    return (
        args.profile in _INSPECT_PROFILES
        and 1 <= args.max_input_bytes <= DEFAULT_MAX_INPUT_BYTES
        and 0 <= args.min_savings_bytes <= DEFAULT_MAX_INPUT_BYTES
        and math.isfinite(args.min_savings_ratio)
        and 0.0 <= args.min_savings_ratio <= 1.0
    )


def _run_recover(args: argparse.Namespace) -> int:
    base_directory = args.base_directory or _manual_session_base()
    if base_directory is None:
        return 2
    try:
        if args.session_id:
            with EphemeralRecoveryStore(
                base_directory,
                session_identifier=args.session_id,
            ) as recovery:
                response = recovery.load(args.handle)
        else:
            response = recover_by_handle(base_directory, args.handle)
    except (OSError, RuntimeError, TypeError, ValueError):
        return 2
    if response is None:
        return 1
    print(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
    return 0


def _run_clean(args: argparse.Namespace) -> int:
    base_directory = args.base_directory or _manual_session_base()
    if base_directory is None:
        return 2
    try:
        if args.session_id:
            if args.expired:
                with EphemeralRecoveryStore(
                    base_directory,
                    session_identifier=args.session_id,
                ) as recovery:
                    removed = recovery.clean_expired()
                scope = "expired"
            else:
                removed = clean_session(
                    base_directory,
                    args.session_id,
                )
                scope = "all"
        elif args.expired:
            return 2
        else:
            removed = clean_owned_repo_recovery(base_directory)
            scope = "all"
    except (OSError, RuntimeError, TypeError, ValueError):
        return 2
    print(json.dumps({"removed": removed, "scope": scope}, separators=(",", ":")))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    import argparse

    parser = argparse.ArgumentParser(
        description="Inspect and safely filter supported tool output"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    hook = subparsers.add_parser("hook")
    hook.add_argument("--policy", type=Path, required=True)
    status = subparsers.add_parser("status")
    status.add_argument("--policy", type=Path)
    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("--profile", required=True)
    inspect.add_argument(
        "--max-input-bytes",
        type=int,
        default=DEFAULT_MAX_INPUT_BYTES,
    )
    inspect.add_argument(
        "--min-savings-bytes",
        type=int,
        default=DEFAULT_MIN_SAVINGS_BYTES,
    )
    inspect.add_argument(
        "--min-savings-ratio",
        type=float,
        default=DEFAULT_MIN_SAVINGS_RATIO,
    )
    recover = subparsers.add_parser("recover")
    recover.add_argument("handle")
    recover.add_argument("--base-directory", type=Path)
    recover.add_argument("--session-id")
    clean = subparsers.add_parser("clean")
    clean.add_argument("--base-directory", type=Path)
    clean.add_argument("--session-id")
    clean.add_argument("--expired", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if (
        len(arguments) == 3
        and arguments[0] == "hook"
        and arguments[1] == "--policy"
    ):
        return run_hook(Path(arguments[2]))
    args = _build_parser().parse_args(arguments)
    if args.command == "hook":
        return run_hook(args.policy)
    if args.command == "status":
        return _run_status(args.policy)
    if args.command == "inspect":
        return _run_inspect(args)
    if args.command == "recover":
        return _run_recover(args)
    if args.command == "clean":
        return _run_clean(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
