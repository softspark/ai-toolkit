#!/usr/bin/env python3
"""Generate native, self-contained Cursor hooks.

Repository installs write ``.cursor/hooks.json`` and a managed Python runtime
below ``.cursor/hooks/ai-toolkit/``. The same manifest also works for Cursor
user hooks: project hooks run from the repository root, while user hooks run
from ``~/.cursor`` and use the colocated runtime fallback.

Cursor Cloud Agents load only repository hooks and cannot access user-level
``~/.cursor`` configuration. Keeping every project command repository-relative
makes the generated hook set portable to Cursor's isolated cloud VMs.
"""
from __future__ import annotations

import json
import os
import shlex
import sys
import tempfile
from pathlib import Path
from typing import Any


SOURCE_TAG = "ai-toolkit"
SCHEMA_VERSION = 1
SCRIPT_MARKER = "# ai-toolkit-managed: cursor-hook"
SCRIPT_NAME = "cursor_hook.py"
PROJECT_RUNTIME = ".cursor/hooks/ai-toolkit/cursor_hook.py"
USER_RUNTIME = "./hooks/ai-toolkit/cursor_hook.py"

# Cursor 3.11 hook events documented at https://cursor.com/docs/hooks.
HOOK_DEFINITIONS: tuple[tuple[str, str, int], ...] = (
    ("sessionStart", "session-start", 10),
    ("sessionEnd", "observe", 10),
    ("preToolUse", "pre-tool-use", 10),
    ("postToolUse", "post-tool-use", 10),
    ("postToolUseFailure", "post-tool-use-failure", 10),
    ("subagentStart", "subagent-start", 10),
    ("subagentStop", "subagent-stop", 10),
    ("beforeShellExecution", "before-shell", 10),
    ("afterShellExecution", "observe", 10),
    ("beforeMCPExecution", "before-mcp", 10),
    ("afterMCPExecution", "observe", 10),
    ("beforeReadFile", "before-read", 10),
    ("afterFileEdit", "post-file-edit", 10),
    ("beforeSubmitPrompt", "before-submit-prompt", 10),
    ("preCompact", "observe", 10),
    ("stop", "stop", 120),
    ("afterAgentResponse", "observe", 10),
    ("afterAgentThought", "observe", 10),
    ("beforeTabFileRead", "before-read", 10),
    ("afterTabFileEdit", "post-file-edit", 10),
    ("workspaceOpen", "workspace-open", 10),
)


HOOK_RUNTIME = r'''#!/usr/bin/env python3
# ai-toolkit-managed: cursor-hook
"""Self-contained runtime for native Cursor hooks."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


MAX_OUTPUT_CHARS = 2_000
DESTRUCTIVE_PATTERNS = tuple(re.compile(pattern, re.IGNORECASE) for pattern in (
    r"\brm\s+(?:-[rRf]{2,}|-r\s+-f|-f\s+-r|--recursive|--force)\b",
    r"\bsudo\s+rm\b",
    r"\b(?:xargs\s+rm|find\s+.+(?:-delete|-exec\s+rm))\b",
    r"\bDROP\s+(?:TABLE|DATABASE|SCHEMA|INDEX)\b",
    r"\bTRUNCATE\s+",
    r"\bDELETE\s+FROM\s+\S+\s*(?:;|$|WHERE\s+1)\b",
    r"\b(?:mkfs|shred)\b",
    r"\bdd\s+if=",
    r"\bgit\s+push\s+.*(?:--force(?:\s|$)|-f(?:\s|$))",
    r"\bgit\s+(?:reset\s+--hard|clean\s+-[a-z]*f|branch\s+-D)\b",
    r"\bchmod\s+(?:-R\s+)?(?:777|000)\b",
    r"\bdocker\s+(?:system\s+prune|rm\s+-f|rmi\s+-f)\b",
    r"\bkubectl\s+delete\s+(?:namespace|ns|all|node)\b",
    r"\bterraform\s+destroy\b",
    r"\bsystemctl\s+(?:stop|disable)\s+",
    r">\s*/dev/sd[a-z]",
))


def _payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        print(f"ai-toolkit Cursor hook skipped invalid JSON: {error}", file=sys.stderr)
        return {}
    return value if isinstance(value, dict) else {}


def _emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def _all_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(_all_strings(item))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_all_strings(item))
        return result
    return []


def _command_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    for key in ("command", "commandLine", "command_line", "script", "code"):
        command = value.get(key)
        if isinstance(command, str):
            return command
    return ""


def _destructive_reason(command: str) -> str | None:
    normalized = " ".join(command.replace("\\", "").split())
    if not normalized:
        return None
    if not re.search(r"&&|\|\||;|\|", normalized):
        if re.match(r"\s*(?:echo|printf|git\s+(?:commit|tag))(?:\s|$)", normalized):
            return None
    normalized = re.sub(r"--force-with-lease(?:=\S+)?|--force-if-includes", "", normalized)
    if any(pattern.search(normalized) for pattern in DESTRUCTIVE_PATTERNS):
        return "Potentially destructive command requires explicit user review."
    return None


def _wrong_home_reason(value: Any) -> str | None:
    actual_user = Path.home().name
    if not actual_user:
        return None
    pattern = re.compile(r"/(?:Users|home)/([^/\s'\"]+)")
    for text in _all_strings(value):
        for match in pattern.finditer(text):
            if match.group(1) != actual_user:
                return (
                    f"Absolute path names user '{match.group(1)}', but the active "
                    f"home belongs to '{actual_user}'. Use $HOME or the correct path."
                )
    return None


def _deny(reason: str) -> None:
    _emit({
        "permission": "deny",
        "user_message": reason,
        "agent_message": reason,
    })
    raise SystemExit(2)


def _before_shell(payload: dict[str, Any]) -> None:
    reason = _destructive_reason(_command_text(payload))
    if reason:
        _deny(reason)


def _pre_tool_use(payload: dict[str, Any]) -> None:
    arguments = payload.get("tool_input", payload.get("toolInput", {}))
    reason = _wrong_home_reason(arguments)
    tool_name = str(payload.get("tool_name") or payload.get("toolName") or "")
    if reason is None and tool_name.lower() in {
        "bash", "shell", "terminal", "run_terminal_command",
    }:
        reason = _destructive_reason(_command_text(arguments))
    if reason:
        _deny(reason)


def _before_read(payload: dict[str, Any]) -> None:
    reason = _wrong_home_reason(payload.get("file_path", payload))
    if reason:
        _deny(reason)


def _quality_command(cwd: Path) -> tuple[str, list[str]] | None:
    if (cwd / "pyproject.toml").is_file() or (cwd / "setup.py").is_file():
        if shutil.which("ruff"):
            return "ruff check", ["ruff", "check", "."]
    if (cwd / "package.json").is_file() and (cwd / "tsconfig.json").is_file():
        local_tsc = cwd / "node_modules" / ".bin" / "tsc"
        if local_tsc.is_file():
            return "TypeScript typecheck", [str(local_tsc), "--noEmit"]
        if shutil.which("tsc"):
            return "TypeScript typecheck", ["tsc", "--noEmit"]
    if (cwd / "pubspec.yaml").is_file() and shutil.which("dart"):
        return "Dart analysis", ["dart", "analyze"]
    if (cwd / "go.mod").is_file() and shutil.which("go"):
        return "Go vet", ["go", "vet", "./..."]
    phpstan = cwd / "vendor" / "bin" / "phpstan"
    if (cwd / "composer.json").is_file() and phpstan.is_file():
        return "PHPStan", [str(phpstan), "analyse"]
    return None


def _stop(payload: dict[str, Any]) -> None:
    try:
        loop_count = int(payload.get("loop_count", 0))
    except (TypeError, ValueError):
        loop_count = 0
    if loop_count >= 2:
        print(
            "ai-toolkit Cursor quality circuit breaker reached after three "
            "failed completion attempts",
            file=sys.stderr,
        )
        return

    cwd_value = payload.get("cwd") or os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd()
    cwd = Path(str(cwd_value))
    if not cwd.is_dir():
        return
    selected = _quality_command(cwd)
    if selected is None:
        return
    label, command = selected
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=110,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"ai-toolkit Cursor quality hook skipped {label}: {error}", file=sys.stderr)
        return
    if result.returncode == 0:
        return
    detail = (result.stdout + "\n" + result.stderr).strip()[-MAX_OUTPUT_CHARS:]
    message = f"{label} failed. Fix the errors and verify again before finishing."
    if detail:
        message += f"\n\n{detail}"
    _emit({"followup_message": message})


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else "observe"
    payload = _payload()
    if action == "session-start":
        _emit({
            "additional_context": (
                "AI Toolkit: follow repository instructions and relevant skills, "
                "keep tests and docs aligned, and verify evidence before completion."
            )
        })
    elif action == "before-shell":
        _before_shell(payload)
    elif action == "pre-tool-use":
        _pre_tool_use(payload)
    elif action == "before-read":
        _before_read(payload)
    elif action == "stop":
        _stop(payload)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:  # Adapter failures must not create agent loops.
        print(f"ai-toolkit Cursor hook failed safely: {error}", file=sys.stderr)
'''


def _runtime_command(action: str) -> str:
    action_arg = shlex.quote(action)
    return (
        f'if [ -f "{PROJECT_RUNTIME}" ]; then '
        f'exec python3 "{PROJECT_RUNTIME}" {action_arg}; '
        f'else exec python3 "{USER_RUNTIME}" {action_arg}; fi'
    )


def build_toolkit_hooks() -> dict[str, list[dict[str, Any]]]:
    hooks: dict[str, list[dict[str, Any]]] = {}
    for event, action, timeout in HOOK_DEFINITIONS:
        entry: dict[str, Any] = {
            "command": _runtime_command(action),
            "timeout": timeout,
        }
        if event in {"stop", "subagentStop"}:
            entry["loop_limit"] = 5
        hooks[event] = [entry]
    return hooks


def _is_toolkit_entry(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get("_source") == SOURCE_TAG:  # Migrate legacy generator output.
        return True
    command = entry.get("command")
    return isinstance(command, str) and (
        PROJECT_RUNTIME in command or USER_RUNTIME in command
    )


def strip_toolkit_hooks(hooks: dict[str, Any]) -> dict[str, Any]:
    kept: dict[str, Any] = {}
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            kept[event] = entries
            continue
        survivors = [entry for entry in entries if not _is_toolkit_entry(entry)]
        if survivors:
            kept[event] = survivors
    return kept


def merge_hooks(
    existing: dict[str, Any],
    toolkit: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    merged = strip_toolkit_hooks(existing)
    for event, entries in toolkit.items():
        merged.setdefault(event, []).extend(entries)
    return merged


def _load_document(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Refusing to overwrite invalid Cursor hooks JSON: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"Cursor hooks file must contain a JSON object: {path}")
    version = value.get("version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported Cursor hooks version {version!r}: {path}")
    hooks = value.get("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"Cursor hooks field must contain an object: {path}")
    return value


def _assert_not_symlink(path: Path, label: str) -> None:
    if path.is_symlink():
        raise RuntimeError(f"Refusing symlinked Cursor {label}: {path}")


def _is_managed_runtime(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        return SCRIPT_MARKER in path.read_text(encoding="utf-8")[:256]
    except (OSError, UnicodeError):
        return False


def _stage_file(destination: Path, content: bytes, mode: int) -> Path:
    fd, temp_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            fd = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, mode)
        return temp_path
    except Exception:
        if fd >= 0:
            os.close(fd)
        temp_path.unlink(missing_ok=True)
        raise


def _write_transaction(outputs: list[tuple[Path, bytes, int]]) -> None:
    staged: list[tuple[Path, Path]] = []
    backups: dict[Path, Path] = {}
    applied: list[Path] = []
    try:
        for destination, content, mode in outputs:
            staged.append((_stage_file(destination, content, mode), destination))
        for _, destination in staged:
            if destination.exists():
                current_mode = destination.stat().st_mode & 0o777
                backups[destination] = _stage_file(
                    destination,
                    destination.read_bytes(),
                    current_mode,
                )
        for temp_path, destination in staged:
            _assert_not_symlink(destination, "hook output")
            os.replace(temp_path, destination)
            applied.append(destination)
    except Exception as error:
        rollback_errors: list[Exception] = []
        for destination in reversed(applied):
            backup = backups.get(destination)
            try:
                if backup is None:
                    destination.unlink(missing_ok=True)
                else:
                    os.replace(backup, destination)
            except Exception as rollback_error:  # pragma: no cover
                rollback_errors.append(rollback_error)
        if rollback_errors:
            raise RuntimeError(
                "Cursor hook update failed and rollback was incomplete: "
                f"{rollback_errors}"
            ) from error
        raise
    finally:
        for temp_path, _ in staged:
            temp_path.unlink(missing_ok=True)
        for backup in backups.values():
            backup.unlink(missing_ok=True)


def generate(target_dir: Path) -> Path:
    target_dir = Path(target_dir).expanduser().absolute()
    cursor_dir = target_dir / ".cursor"
    hooks_dir = cursor_dir / "hooks"
    assets_dir = hooks_dir / "ai-toolkit"
    config_path = cursor_dir / "hooks.json"
    runtime_path = assets_dir / SCRIPT_NAME

    safe_paths = (
        (target_dir, "target root"),
        (cursor_dir, "config directory"),
        (hooks_dir, "hooks directory"),
        (assets_dir, "assets directory"),
        (config_path, "hooks config"),
        (runtime_path, "hook runtime"),
    )
    for path, label in safe_paths:
        _assert_not_symlink(path, label)
    for directory in (cursor_dir, hooks_dir, assets_dir):
        if directory.exists() and not directory.is_dir():
            raise RuntimeError(f"Cursor hook path is not a directory: {directory}")
        directory.mkdir(parents=True, exist_ok=True)
    for path, label in safe_paths:
        _assert_not_symlink(path, label)
    if runtime_path.exists() and not _is_managed_runtime(runtime_path):
        raise RuntimeError(f"Refusing user-owned Cursor hook runtime: {runtime_path}")

    document = _load_document(config_path)
    existing_hooks = document.get("hooks", {})
    document["version"] = SCHEMA_VERSION
    document["hooks"] = merge_hooks(existing_hooks, build_toolkit_hooks())
    config_bytes = (
        json.dumps(document, indent=4, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")
    _write_transaction([
        (runtime_path, HOOK_RUNTIME.encode("utf-8"), 0o755),
        (config_path, config_bytes, 0o644),
    ])
    return config_path


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    path = generate(target)
    total = len(HOOK_DEFINITIONS)
    relative = path.relative_to(target) if path.is_relative_to(target) else path
    print(f"Generated: {relative} ({total} hooks across {total} events)")


if __name__ == "__main__":
    main()
