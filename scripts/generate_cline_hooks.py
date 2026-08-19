#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate Cline CLI and extension-compatible hook executables."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from secure_fs import (
    SecureDestination,
    SecureTransaction,
    lexical_absolute,
    nearest_existing_root,
    run_secure_transaction,
)


HOOK_EVENTS = (
    "TaskStart",
    "TaskResume",
    "TaskCancel",
    "TaskComplete",
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "PreCompact",
)
MANAGED_MARKER = "# ai-toolkit-managed: cline-hook"


HOOK_SOURCE = '''#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# ai-toolkit-managed: cline-hook
"""Self-contained ai-toolkit adapter for one native Cline hook event."""

from __future__ import annotations

import json
import re
import signal
import sys
from pathlib import Path
from typing import Any


MAX_INPUT_BYTES = 1024 * 1024
MAX_RUNTIME_SECONDS = 4
EVENTS = {
    "TaskStart",
    "TaskResume",
    "TaskCancel",
    "TaskComplete",
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "PreCompact",
}
COMMAND_TOOLS = {
    "execute_command",
    "run_command",
    "run_commands",
    "bash",
    "shell",
}
DESTRUCTIVE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"(?:^|[;&|]\\s*)rm\\s+(?:-[rRf]+|--recursive|--force)\\b",
        r"\\bsudo\\s+rm\\b",
        r"\\bgit\\s+reset\\s+--hard\\b",
        r"\\bgit\\s+clean\\s+-[^\\s]*f",
        r"\\bgit\\s+push\\s+.*(?:--force(?:\\s|$)|-f(?:\\s|$))",
        r"\\b(?:mkfs|shred)\\b",
        r"\\bdd\\s+if=.+\\s+of=/dev/",
        r"\\bDROP\\s+(?:DATABASE|SCHEMA|TABLE)\\b",
        r"\\bTRUNCATE\\s+(?:TABLE\\s+)?\\S+",
        r"\\bterraform\\s+destroy\\b",
        r"\\bkubectl\\s+delete\\s+(?:namespace|ns|all|node)\\b",
    )
)
CONTEXT_BY_EVENT = {
    "TaskStart": (
        "Follow repository instructions, keep changes scoped, and verify before "
        "claiming completion."
    ),
    "TaskResume": (
        "Reconfirm the current objective, pending work, and repository state "
        "before continuing."
    ),
    "UserPromptSubmit": (
        "For technical work, search the project knowledge base first and cite "
        "the source paths used."
    ),
    "PreCompact": (
        "Preserve the objective, completed and pending work, modified files, "
        "decisions, and verification evidence during compaction."
    ),
}


def _timeout(_signum: int, _frame: object) -> None:
    raise TimeoutError("Cline hook exceeded its deadline")


def _read_payload() -> dict[str, Any]:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("Cline hook payload exceeds 1 MiB")
    if not raw.strip():
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Cline hook payload must be an object")
    return value


def _pre_tool_use(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("preToolUse")
    if not isinstance(data, dict):
        return {"cancel": True, "errorMessage": "Invalid preToolUse payload."}
    tool = data.get("toolName")
    parameters = data.get("parameters")
    if not isinstance(tool, str) or not tool:
        return {"cancel": True, "errorMessage": "Invalid toolName value."}
    if not isinstance(parameters, dict):
        return {"cancel": True, "errorMessage": "Invalid command parameters."}
    if tool.lower() not in COMMAND_TOOLS:
        return {"cancel": False}
    commands = parameters.get("commands") if tool.lower() == "run_commands" else None
    if commands is None:
        commands = [parameters.get("command")]
    if (
        not isinstance(commands, list)
        or not commands
        or any(
            not isinstance(command, str) or not command.strip()
            for command in commands
        )
    ):
        return {"cancel": True, "errorMessage": "Invalid command value."}
    if any(
        pattern.search(command)
        for command in commands
        for pattern in DESTRUCTIVE_PATTERNS
    ):
        return {
            "cancel": True,
            "errorMessage": "Potentially destructive command requires explicit user approval.",
        }
    return {"cancel": False}


def respond(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event == "PreToolUse":
        return _pre_tool_use(payload)
    if event in CONTEXT_BY_EVENT:
        return {
            "cancel": False,
            "contextModification": CONTEXT_BY_EVENT[event],
            "errorMessage": "",
        }
    return {"cancel": False}


def main() -> int:
    event = Path(sys.argv[0]).name
    if event not in EVENTS:
        print("Unsupported Cline hook event", file=sys.stderr)
        return 2
    signal.signal(signal.SIGALRM, _timeout)
    signal.alarm(MAX_RUNTIME_SECONDS)
    try:
        result = respond(event, _read_payload())
        print(json.dumps(result, separators=(",", ":"), sort_keys=True))
        return 0
    except (json.JSONDecodeError, TimeoutError, ValueError) as error:
        print(
            json.dumps(
                {
                    "cancel": True,
                    "errorMessage": f"Cline hook input rejected: {error}",
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _hook_paths(target_dir: Path, hooks_root: Path | None = None) -> list[Path]:
    hooks_dir = hooks_root or target_dir / ".cline" / "hooks"
    return [hooks_dir / event for event in HOOK_EVENTS]


def _default_hook_roots(target: Path) -> list[Path]:
    roots = [target / ".cline" / "hooks"]
    compatibility_root = target / ".clinerules"
    if compatibility_root.is_symlink():
        raise RuntimeError(
            f"Unsafe symlinked Cline hooks ancestor: {compatibility_root}"
        )
    if not compatibility_root.is_file():
        roots.append(compatibility_root / "hooks")
    return roots


def _stale_candidates(hooks_dir: Path) -> list[Path]:
    if not hooks_dir.exists():
        return []
    if hooks_dir.is_symlink() or not hooks_dir.is_dir():
        raise RuntimeError(f"Unsafe Cline hooks directory: {hooks_dir}")
    active_names = set(HOOK_EVENTS)
    return sorted(
        (
            path
            for path in hooks_dir.iterdir()
            if path.name not in active_names
            and not path.is_symlink()
            and path.is_file()
        ),
        key=lambda path: path.name,
    )


def _reject_symlink_ancestors(target: Path, output_root: Path) -> None:
    try:
        relative = output_root.relative_to(target)
    except ValueError as error:
        raise RuntimeError(
            f"Cline hooks root escapes target directory: {output_root}"
        ) from error
    current = target
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise RuntimeError(f"Unsafe symlinked Cline hooks ancestor: {current}")
        if not current.exists():
            break
        if not current.is_dir():
            raise RuntimeError(f"Unsafe non-directory Cline hooks ancestor: {current}")


def generate(target_dir: Path, *, hooks_root: Path | None = None) -> Path:
    """Write all eight Cline hook executables atomically.

    ``hooks_root`` selects a documented compatibility root while keeping
    ``target_dir`` as the trusted filesystem boundary. Without an override,
    project hooks are dual-emitted to ``.cline/hooks`` and
    ``.clinerules/hooks`` unless a legacy ``.clinerules`` file occupies the
    compatibility path.
    """
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Cline target directory: {target}")
    output_roots = (
        [lexical_absolute(hooks_root)]
        if hooks_root is not None
        else _default_hook_roots(target)
    )
    for output_root in output_roots:
        _reject_symlink_ancestors(target, output_root)
    root = nearest_existing_root(target)
    active_destinations = [
        SecureDestination(path, root, f"Cline {path.name} hook")
        for output_root in output_roots
        for path in _hook_paths(target, output_root)
    ]
    stale_destinations = [
        SecureDestination(path, root, f"Cline stale {path.name} hook")
        for output_root in output_roots
        for path in _stale_candidates(output_root)
    ]
    destinations = active_destinations + stale_destinations

    def apply(transaction: SecureTransaction) -> None:
        for destination in active_destinations:
            content = transaction.initial_content(destination)
            if content is not None and MANAGED_MARKER.encode() not in content[:256]:
                raise RuntimeError(
                    f"Refusing user-owned Cline hook: {destination.path}"
                )
        for destination in active_destinations:
            transaction.atomic_write(destination, HOOK_SOURCE.encode(), 0o755)
        for destination in stale_destinations:
            content = transaction.initial_content(destination)
            if content is not None and MANAGED_MARKER.encode() in content[:256]:
                transaction.unlink(destination)

    run_secure_transaction(destinations, apply)
    return output_roots[0]


def generate_global(home_dir: Path) -> Path:
    """Write hooks below Cline CLI's global ``~/.cline/hooks`` root."""
    home = lexical_absolute(home_dir)
    return generate(home, hooks_root=home / ".cline" / "hooks")


def generate_extension_global(home_dir: Path) -> Path:
    """Write extension-compatible hooks below ``~/Documents/Cline/Hooks``."""
    home = lexical_absolute(home_dir)
    return generate(home, hooks_root=home / "Documents" / "Cline" / "Hooks")


def cleanup(target_dir: Path, *, hooks_root: Path | None = None) -> None:
    """Remove only ai-toolkit-managed hook files from a Cline target."""
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        return
    hook_roots = (
        [lexical_absolute(hooks_root)]
        if hooks_root is not None
        else _default_hook_roots(target)
    )
    for hooks_dir in hook_roots:
        _reject_symlink_ancestors(target, hooks_dir)
    root = nearest_existing_root(target)
    candidates = [
        path
        for hooks_dir in hook_roots
        if hooks_dir.is_dir()
        for path in _hook_paths(target, hooks_dir) + _stale_candidates(hooks_dir)
    ]
    destinations = [
        SecureDestination(path, root, f"Cline {path.name} hook")
        for path in candidates
        if path.is_file() and not path.is_symlink()
    ]
    if not destinations:
        return

    def apply(transaction: SecureTransaction) -> None:
        for destination in destinations:
            content = transaction.initial_content(destination)
            if content is not None and MANAGED_MARKER.encode() in content[:256]:
                transaction.unlink(destination)

    run_secure_transaction(destinations, apply)


def discover(target_dir: Path, *, hooks_root: Path | None = None) -> int:
    """Return the number of ai-toolkit-managed Cline hook files."""
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Cline target directory: {target}")
    roots = (
        [lexical_absolute(hooks_root)]
        if hooks_root is not None
        else _default_hook_roots(target)
    )
    for root in roots:
        _reject_symlink_ancestors(target, root)
    count = 0
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.iterdir():
            if path.is_symlink() or not path.is_file():
                continue
            try:
                with path.open("rb") as handle:
                    content = handle.read(256)
            except OSError:
                continue
            if MANAGED_MARKER.encode() in content:
                count += 1
    return count


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    generate(target)
    roots = _default_hook_roots(lexical_absolute(target))
    print(f"Generated: {', '.join(map(str, roots))} ({len(HOOK_EVENTS)} hooks each)")


if __name__ == "__main__":
    main()
