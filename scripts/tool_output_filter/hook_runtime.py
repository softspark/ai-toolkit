"""Lean Claude PostToolUse runtime for native tool-output filtering."""

from __future__ import annotations

import json
import os
import re
import shlex
import sys

from .contracts import FilterMode, FilterRequest
from .engine import filter_output
from .input import JSON_ENVELOPE_ALLOWANCE_BYTES, load_bounded_json
from .invariants import SessionCircuitBreaker
from .policy import OutputFilterPolicy, load_policy
from .recovery import EphemeralRecoveryStore

_UNSAFE_SHELL_FRAGMENTS = ("|", ">", "<", ";", "&&", "||", "`", "$(", "\n")
# Claude Code's Bash tool_response has no guaranteed exit-status field; when a
# runtime does provide one, a non-zero value must veto filtering outright.
_EXIT_STATUS_KEYS = ("exitCode", "exit_code", "returncode")
_FAILURE_LINE_PREFIXES = (
    "not ok",
    "npm err!",
    "fail",
    "--- fail",
    "error",
    "fatal",
    "panic",
    "traceback",
    "critical",
    "segmentation fault",
    "assert",
    "exception",
    "✕",
    "✗",
    "e   ",
)
_FAILURE_SUMMARY_PATTERN = re.compile(
    r"\b[1-9][0-9]* (?:failed|failures|errors)\b"
)
_DANGEROUS_FRAGMENTS = (
    "audit",
    "deploy",
    "destroy",
    "migrat",
    "publish",
    "release",
    "semgrep",
    "snyk",
    "terraform",
    "trivy",
)
_SAFE_TASK_TOKENS = frozenset(
    {
        "analyze",
        "analysis",
        "check",
        "checks",
        "clippy",
        "lint",
        "qa",
        "test",
        "tests",
        "typecheck",
        "validate",
        "validation",
        "vet",
    }
)
_TASK_TOKEN_SEPARATORS = "-_:./"
_SAFE_SESSION_ID_CHARACTERS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)
_MAX_SESSION_ID_LENGTH = 160


def _is_safe_task(value: str) -> bool:
    normalized = value.lower()
    for separator in _TASK_TOKEN_SEPARATORS:
        normalized = normalized.replace(separator, " ")
    return any(token in _SAFE_TASK_TOKENS for token in normalized.split())


def _matches_supported_shape(arguments: list[str]) -> bool:
    executable = os.path.basename(arguments[0]).lower()
    remaining = arguments[1:]
    if executable in {"bats", "jest", "pytest", "vitest"}:
        return True
    if executable in {"python", "python3"}:
        return len(remaining) >= 2 and remaining[:2] in (
            ["-m", "pytest"],
            ["-m", "unittest"],
        )
    if executable in {"cargo", "dart", "flutter", "go"}:
        return bool(remaining) and _is_safe_task(remaining[0])
    if executable == "npm":
        if not remaining:
            return False
        if remaining[0] == "test":
            return True
        return len(remaining) >= 2 and remaining[0] == "run" and _is_safe_task(
            remaining[1]
        )
    if executable == "npx":
        return bool(remaining) and os.path.basename(remaining[0]).lower() in {
            "eslint",
            "jest",
            "tsc",
            "vitest",
        }
    if executable == "make":
        return bool(remaining) and all(_is_safe_task(target) for target in remaining)
    if executable == "composer":
        if len(remaining) == 1:
            return _is_safe_task(remaining[0])
        return (
            len(remaining) == 2
            and remaining[0] in {"run", "run-script"}
            and _is_safe_task(remaining[1])
        )
    return False


def _is_supported_command(command: str) -> bool:
    if any(fragment in command for fragment in _UNSAFE_SHELL_FRAGMENTS):
        return False
    try:
        arguments = shlex.split(command, posix=True)
    except ValueError:
        return False
    if not arguments:
        return False
    lowered_arguments = [argument.lower() for argument in arguments]
    if any(
        fragment in argument
        for argument in lowered_arguments
        for fragment in _DANGEROUS_FRAGMENTS
    ):
        return False
    return _matches_supported_shape(arguments)


def _reports_failed_execution(response: dict[str, object]) -> bool:
    for key in _EXIT_STATUS_KEYS:
        value = response.get(key)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value != 0:
            return True
    return False


def _looks_like_failure_output(stdout: str) -> bool:
    for line in stdout.splitlines():
        content = line.lstrip().lower()
        if not content:
            continue
        if content.startswith(_FAILURE_LINE_PREFIXES):
            return True
        if _FAILURE_SUMMARY_PATTERN.search(content) is not None:
            return True
    return False


def _infer_repo_root(start: str) -> str | None:
    # realpath keeps the repo key aligned with the bash hooks, which resolve
    # symlinks via `git rev-parse --show-toplevel`.
    candidate_path = os.path.realpath(os.path.expanduser(start))
    if not os.path.isdir(candidate_path):
        return None
    candidate = candidate_path
    while True:
        git_marker = os.path.join(candidate, ".git")
        if os.path.isdir(git_marker) or os.path.isfile(git_marker):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent
    return candidate_path


def _session_base_for_repo(repo_root: str) -> str:
    repo_key = "-" + str(repo_root).replace("/", "-").lstrip("-")
    return os.path.join(
        os.path.expanduser("~"),
        ".softspark",
        "ai-toolkit",
        "sessions",
        repo_key,
    )


def _normalize_payload(payload: object) -> tuple[dict[str, object], str] | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("hook_event_name") != "PostToolUse":
        return None
    if payload.get("tool_name") != "Bash":
        return None
    response = payload.get("tool_response")
    tool_input = payload.get("tool_input")
    if not isinstance(response, dict) or not isinstance(tool_input, dict):
        return None
    stdout = response.get("stdout")
    command = tool_input.get("command")
    if not isinstance(stdout, str) or not isinstance(command, str):
        return None
    if response.get("stderr") != "" or response.get("interrupted") is not False:
        return None
    if response.get("isImage") is not False:
        return None
    if _reports_failed_execution(response):
        return None
    if _looks_like_failure_output(stdout):
        return None
    if not _is_supported_command(command):
        return None
    return response, stdout


def _repo_session_root(payload: dict[str, object]) -> tuple[str, str] | None:
    cwd = payload.get("cwd")
    session_identifier = payload.get("session_id")
    if not isinstance(cwd, str) or not isinstance(session_identifier, str):
        return None
    if not cwd or not session_identifier:
        return None
    if (
        len(session_identifier) > _MAX_SESSION_ID_LENGTH
        or any(
            character not in _SAFE_SESSION_ID_CHARACTERS
            for character in session_identifier
        )
    ):
        return None
    repo_root = _infer_repo_root(cwd)
    if repo_root is None:
        return None
    return _session_base_for_repo(repo_root), session_identifier


def _request(
    policy: OutputFilterPolicy,
    response: dict[str, object],
    stdout: str,
    profile_id: str,
) -> FilterRequest:
    return FilterRequest(
        output=stdout,
        raw_response=response,
        mode=policy.mode,
        profile_id=profile_id,
        max_input_bytes=policy.max_input_bytes,
        min_savings_bytes=policy.min_savings_bytes,
        min_savings_ratio=policy.min_savings_ratio,
    )


def _emit_replacement(
    response: dict[str, object],
    replacement: str,
) -> None:
    updated_response = dict(response)
    updated_response["stdout"] = replacement
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedToolOutput": updated_response,
        }
    }
    sys.stdout.write(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    sys.stdout.write("\n")


def _emit_system_message(message: str) -> None:
    sys.stdout.write(
        json.dumps(
            {"systemMessage": message},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    sys.stdout.write("\n")


def _filter_profiles(
    policy: OutputFilterPolicy,
    response: dict[str, object],
    stdout: str,
    recovery: EphemeralRecoveryStore,
    circuit_breaker: SessionCircuitBreaker,
) -> None:
    for profile_id in policy.profiles:
        result = filter_output(
            _request(policy, response, stdout, profile_id),
            recovery=recovery,
            telemetry=recovery,
            circuit_breaker=circuit_breaker,
        )
        recovery.save_failure_count(
            min(
                circuit_breaker.consecutive_failures,
                circuit_breaker.failure_limit,
            )
        )
        if result.changed:
            _emit_replacement(response, result.output)
            return
        if result.outcome == "observed":
            return


def run_hook(policy_path: str | os.PathLike[str]) -> int:
    """Run one bounded, fail-open Claude PostToolUse decision."""

    if os.environ.get("AI_TOOLKIT_OUTPUT_FILTER_DISABLE") == "1":
        return 0
    try:
        policy = load_policy(policy_path)
    except (OSError, TypeError, ValueError, KeyError):
        return 0
    if policy.mode is FilterMode.OFF:
        return 0
    payload_limit = policy.max_input_bytes + JSON_ENVELOPE_ALLOWANCE_BYTES
    try:
        payload = load_bounded_json(sys.stdin.buffer, max_bytes=payload_limit)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0
    normalized = _normalize_payload(payload)
    if normalized is None:
        return 0
    response, stdout = normalized
    recovery_location = _repo_session_root(payload)
    if recovery_location is None:
        return 0
    base_directory, session_identifier = recovery_location
    try:
        with EphemeralRecoveryStore(
            base_directory,
            session_identifier=session_identifier,
            max_session_bytes=policy.max_session_bytes,
            ttl_minutes=policy.ttl_minutes,
        ) as recovery:
            circuit_breaker = SessionCircuitBreaker(
                consecutive_failures=recovery.load_failure_count()
            )
            if circuit_breaker.is_open and not recovery.load_warning_emitted():
                _emit_system_message(
                    "ai-toolkit: output filtering disabled for this session "
                    "after 3 safety failures"
                )
                recovery.mark_warning_emitted()
            _filter_profiles(
                policy,
                response,
                stdout,
                recovery,
                circuit_breaker,
            )
    except (OSError, RuntimeError, TypeError, ValueError):
        return 0
    return 0


__all__ = ["run_hook"]
