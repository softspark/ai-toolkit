#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate native Google Antigravity hooks and their portable adapter.

Project installs use ``.agents/hooks.json`` and a workspace-relative runtime.
Global installs use ``~/.gemini/config/hooks.json`` and an adjacent runtime.
Only the top-level ``ai-toolkit`` namespace is owned by this generator.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from secure_fs import (
    SecureDestination,
    SecureTransaction,
    lexical_absolute,
    nearest_existing_root,
    run_secure_transaction,
)


MANAGED_NAMESPACE = "ai-toolkit"
HOOK_EVENTS = (
    "PreToolUse",
    "PostToolUse",
    "PreInvocation",
    "PostInvocation",
    "Stop",
)
TOOL_EVENTS = frozenset({"PreToolUse", "PostToolUse"})
HOOK_TIMEOUT_SECONDS = 5
RUNTIME_NAME = "ai-toolkit-antigravity-hook.py"
RUNTIME_MARKER = "# ai-toolkit-managed: antigravity-hook-runtime"
TOOL_MATCHER = (
    "run_command|write_to_file|replace_file_content|"
    "multi_replace_file_content|view_file"
)


RUNTIME_SOURCE = '''#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# ai-toolkit-managed: antigravity-hook-runtime
"""Translate Antigravity hook input to bounded ai-toolkit safety decisions."""

from __future__ import annotations

import json
import re
import signal
import sys
from typing import Any

MAX_INPUT_BYTES = 1024 * 1024
MAX_RUNTIME_SECONDS = 4
EVENTS = {"PreToolUse", "PostToolUse", "PreInvocation", "PostInvocation", "Stop"}
DESTRUCTIVE = (
    re.compile(r"(?:^|[;&|]\\s*)rm\\s+(?:-[^\\s]*r[^\\s]*f|-[^\\s]*f[^\\s]*r)\\b"),
    re.compile(r"\\bgit\\s+reset\\s+--hard\\b"),
    re.compile(r"\\bgit\\s+clean\\s+-[^\\s]*f"),
    re.compile(r"\\b(?:mkfs|format)\\b", re.IGNORECASE),
    re.compile(r"\\bDROP\\s+(?:DATABASE|SCHEMA|TABLE)\\b", re.IGNORECASE),
)


def _timeout(_signum: int, _frame: object) -> None:
    raise TimeoutError("Antigravity hook runtime exceeded its deadline")


def _read_payload() -> dict[str, Any]:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("Antigravity hook payload exceeds 1 MiB")
    if not raw.strip():
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Antigravity hook payload must be an object")
    return value


def _tool(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    tool_call = payload.get("toolCall", {})
    if not isinstance(tool_call, dict):
        return "", {}
    name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    return (
        name if isinstance(name, str) else "",
        args if isinstance(args, dict) else {},
    )


def _pre_tool(payload: dict[str, Any]) -> dict[str, str]:
    name, args = _tool(payload)
    if name != "run_command":
        return {"decision": "allow"}
    command = args.get("CommandLine", "")
    if not isinstance(command, str):
        return {"decision": "ask"}
    if any(pattern.search(command) for pattern in DESTRUCTIVE):
        return {"decision": "deny"}
    return {"decision": "allow"}


def respond(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event == "PreToolUse":
        return _pre_tool(payload)
    if event == "PostToolUse":
        return {}
    if event == "PreInvocation":
        return {
            "injectSteps": [
                {
                    "ephemeralMessage": (
                        "Follow repository instructions and verify before "
                        "claiming completion."
                    )
                }
            ]
        }
    if event == "PostInvocation":
        return {"injectSteps": [], "terminationBehavior": ""}
    if event == "Stop":
        # Never reawaken a Stop hook that Antigravity already re-entered.
        factual_block = payload.get("factualBlock") is True
        loop_active = payload.get("stopHookActive") is True
        execution_num = payload.get("executionNum", 0)
        repeated = isinstance(execution_num, int) and execution_num > 1
        if factual_block and not loop_active and not repeated:
            return {
                "decision": "continue",
                "reason": "A factual completion block still requires resolution.",
            }
        return {"decision": "stop"}
    raise ValueError(f"unsupported Antigravity hook event: {event}")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in EVENTS:
        print("usage: ai-toolkit-antigravity-hook.py <event>", file=sys.stderr)
        return 2
    signal.signal(signal.SIGALRM, _timeout)
    signal.alarm(MAX_RUNTIME_SECONDS)
    try:
        result = respond(sys.argv[1], _read_payload())
        print(json.dumps(result, separators=(",", ":"), sort_keys=True))
        return 0
    except (ValueError, json.JSONDecodeError, TimeoutError) as error:
        print(str(error), file=sys.stderr)
        return 1
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _hook(command: str) -> dict[str, Any]:
    return {"command": command, "timeout": HOOK_TIMEOUT_SECONDS}


def build_managed_hooks(command_prefix: str) -> dict[str, list[dict[str, Any]]]:
    """Return the exact managed namespace using Antigravity's native schema."""
    managed: dict[str, list[dict[str, Any]]] = {}
    for event in HOOK_EVENTS:
        command = f"{command_prefix} {event}"
        if event in TOOL_EVENTS:
            managed[event] = [{"matcher": TOOL_MATCHER, "hooks": [_hook(command)]}]
        else:
            managed[event] = [_hook(command)]
    return managed


def build_document(command_prefix: str) -> dict[str, Any]:
    return {MANAGED_NAMESPACE: build_managed_hooks(command_prefix)}


def validate_document(document: Any, command_prefix: str | None = None) -> None:
    """Reject schema drift before any config is written or packaged."""
    if not isinstance(document, dict):
        raise ValueError("Antigravity hooks.json must contain an object")
    managed = document.get(MANAGED_NAMESPACE)
    if not isinstance(managed, dict) or set(managed) != set(HOOK_EVENTS):
        raise ValueError("Antigravity managed hooks must contain the exact event set")
    for event in HOOK_EVENTS:
        entries = managed[event]
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"Antigravity {event} must contain hook entries")
        handlers: list[Any]
        if event in TOOL_EVENTS:
            handlers = []
            for group in entries:
                if not isinstance(group, dict) or set(group) != {"matcher", "hooks"}:
                    raise ValueError(f"Antigravity {event} has invalid matcher group")
                if not isinstance(group["matcher"], str) or not group["matcher"]:
                    raise ValueError(f"Antigravity {event} matcher must be non-empty")
                if not isinstance(group["hooks"], list) or not group["hooks"]:
                    raise ValueError(f"Antigravity {event} hooks must be non-empty")
                handlers.extend(group["hooks"])
        else:
            handlers = entries
        for handler in handlers:
            if not isinstance(handler, dict) or set(handler) != {"command", "timeout"}:
                raise ValueError(f"Antigravity {event} handler must be command-only")
            if not isinstance(handler["command"], str) or not handler["command"]:
                raise ValueError(f"Antigravity {event} command must be non-empty")
            if not isinstance(handler["timeout"], int) or not 1 <= handler["timeout"] <= 10:
                raise ValueError(f"Antigravity {event} timeout must be bounded")
            expected_command = f"{command_prefix} {event}"
            if command_prefix is not None and handler["command"] != expected_command:
                raise ValueError(f"Antigravity {event} command was tampered")


def _load_existing(content: bytes | None, path: Path) -> dict[str, Any]:
    if content is None:
        return {}
    try:
        value = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid Antigravity hooks JSON at {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _paths(target_dir: Path, global_install: bool) -> tuple[Path, Path, str]:
    if global_install:
        config_root = target_dir / ".gemini" / "config"
        runtime = config_root / "hooks" / RUNTIME_NAME
        command = f'python3 "$HOME/.gemini/config/hooks/{RUNTIME_NAME}"'
        return config_root / "hooks.json", runtime, command
    config_root = target_dir / ".agents"
    runtime = config_root / "hooks" / RUNTIME_NAME
    command = f"python3 .agents/hooks/{RUNTIME_NAME}"
    return config_root / "hooks.json", runtime, command


def generate(target_dir: Path, *, global_install: bool = False) -> Path:
    """Merge hooks and write their adjacent runtime transactionally."""
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Antigravity target directory: {target}")
    hooks_path, runtime_path, command_prefix = _paths(target, global_install)
    root = nearest_existing_root(target)
    hooks_destination = SecureDestination(hooks_path, root, "Antigravity hooks.json")
    runtime_destination = SecureDestination(
        runtime_path, root, "Antigravity hook runtime"
    )
    destinations = [hooks_destination, runtime_destination]

    managed = build_managed_hooks(command_prefix)
    validate_document({MANAGED_NAMESPACE: managed}, command_prefix)

    def apply(transaction: SecureTransaction) -> None:
        existing = _load_existing(
            transaction.initial_content(hooks_destination), hooks_path
        )
        existing[MANAGED_NAMESPACE] = managed
        validate_document(existing, command_prefix)
        current_runtime = transaction.initial_content(runtime_destination)
        if (
            current_runtime is not None
            and RUNTIME_MARKER.encode() not in current_runtime[:256]
        ):
            raise RuntimeError(f"Refusing user-owned Antigravity runtime: {runtime_path}")
        transaction.atomic_write(runtime_destination, RUNTIME_SOURCE.encode(), 0o755)
        content = (
            json.dumps(existing, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n"
        ).encode()
        transaction.atomic_write(hooks_destination, content, 0o600)

    run_secure_transaction(destinations, apply)
    return hooks_path


def generate_global(home_dir: Path) -> Path:
    return generate(home_dir, global_install=True)


def cleanup(target_dir: Path, *, global_install: bool = False) -> None:
    """Remove only ai-toolkit's namespace and managed adjacent runtime."""
    target = lexical_absolute(target_dir)
    hooks_path, runtime_path, _ = _paths(target, global_install)
    if not hooks_path.is_file() or hooks_path.is_symlink():
        return
    root = nearest_existing_root(target)
    hooks_destination = SecureDestination(hooks_path, root, "Antigravity hooks.json")
    destinations = [hooks_destination]
    runtime_destination: SecureDestination | None = None
    if runtime_path.is_file() and not runtime_path.is_symlink():
        runtime_destination = SecureDestination(
            runtime_path, root, "Antigravity hook runtime"
        )
        destinations.append(runtime_destination)

    def apply(transaction: SecureTransaction) -> None:
        document = _load_existing(
            transaction.initial_content(hooks_destination), hooks_path
        )
        if MANAGED_NAMESPACE not in document:
            return
        document.pop(MANAGED_NAMESPACE)
        if document:
            transaction.atomic_write(
                hooks_destination,
                (
                    json.dumps(
                        document, indent=2, ensure_ascii=False, sort_keys=True
                    )
                    + "\n"
                ).encode(),
            )
        else:
            transaction.unlink(hooks_destination)
        if runtime_destination is not None:
            runtime = transaction.initial_content(runtime_destination)
            if runtime is not None and RUNTIME_MARKER.encode() in runtime[:256]:
                transaction.unlink(runtime_destination)

    run_secure_transaction(destinations, apply)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    path = generate(target)
    relative_path = path.relative_to(lexical_absolute(target))
    print(f"Generated: {relative_path} ({len(HOOK_EVENTS)} events)")


if __name__ == "__main__":
    main()
