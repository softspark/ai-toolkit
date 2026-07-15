#!/usr/bin/env python3
"""Generate native, self-contained GitHub Copilot hooks.

Repository installs write ``.github/hooks/ai-toolkit.json`` plus a managed
runtime below ``.github/hooks/ai-toolkit/``. User installs write the same
artifacts below the active Copilot configuration root (``COPILOT_HOME`` or
``~/.copilot``). The generated commands do not depend on the ai-toolkit
checkout after installation.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path
from typing import Any

import secure_fs
from secure_fs import SecureDestination, run_secure_transaction


OWNER_KEY = "AI_TOOLKIT_HOOK_OWNER"
OWNER_VALUE = "ai-toolkit"
SCRIPT_MARKER = "# ai-toolkit-managed: github-copilot-hook"
CONFIG_NAME = "ai-toolkit.json"
SCRIPT_NAME = "copilot_hook.py"

SUPPORTED_EVENTS = frozenset({
    "agentStop",
    "errorOccurred",
    "notification",
    "permissionRequest",
    "postToolUse",
    "postToolUseFailure",
    "preCompact",
    "preToolUse",
    "sessionEnd",
    "sessionStart",
    "subagentStart",
    "subagentStop",
    "userPromptSubmitted",
})
MATCHER_EVENTS = frozenset({
    "notification",
    "permissionRequest",
    "postToolUse",
    "preCompact",
    "preToolUse",
    "subagentStart",
})
COMMAND_KEYS = frozenset({
    "type",
    "bash",
    "command",
    "powershell",
    "cwd",
    "env",
    "timeout",
    "timeoutSec",
    "matcher",
})


HOOK_RUNTIME = r'''#!/usr/bin/env python3
# ai-toolkit-managed: github-copilot-hook
"""Self-contained runtime for native GitHub Copilot hooks."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


MAX_QUALITY_BLOCKS = 3
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
        print(f"ai-toolkit Copilot hook skipped invalid JSON: {error}", file=sys.stderr)
        return {}
    return value if isinstance(value, dict) else {}


def _emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def _session_id(payload: dict[str, Any]) -> str:
    raw = str(payload.get("sessionId") or payload.get("session_id") or "default")
    return re.sub(r"[^A-Za-z0-9_.-]", "_", raw)[:160] or "default"


def _state_path(payload: dict[str, Any]) -> Path:
    configured = os.environ.get("AI_TOOLKIT_COPILOT_STATE_DIR")
    root = Path(configured) if configured else (
        Path(tempfile.gettempdir()) / "ai-toolkit-copilot-hooks"
    )
    root.mkdir(parents=True, exist_ok=True)
    return root / f"quality-{_session_id(payload)}.count"


def _clear_quality_state(payload: dict[str, Any]) -> None:
    try:
        _state_path(payload).unlink(missing_ok=True)
    except OSError:
        pass


def _increment_quality_failures(payload: dict[str, Any]) -> int:
    path = _state_path(payload)
    try:
        current = int(path.read_text(encoding="utf-8").strip()) if path.is_file() else 0
    except (OSError, ValueError):
        current = 0
    current += 1
    try:
        fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=".quality-", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"{current}\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except OSError:
        try:
            Path(temp_name).unlink(missing_ok=True)
        except (OSError, UnboundLocalError):
            pass
    return current


def _tool_args(payload: dict[str, Any]) -> Any:
    return payload.get("toolArgs", payload.get("tool_input", {}))


def _command_text(arguments: Any) -> str:
    if isinstance(arguments, str):
        return arguments
    if not isinstance(arguments, dict):
        return ""
    for key in ("command", "commandLine", "command_line", "script", "code"):
        value = arguments.get(key)
        if isinstance(value, str):
            return value
    return ""


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


def _wrong_home_reason(arguments: Any) -> str | None:
    home = Path.home()
    actual_user = home.name
    if not actual_user:
        return None
    path_pattern = re.compile(r"/(?:Users|home)/([^/\s'\"]+)")
    for text in _all_strings(arguments):
        for match in path_pattern.finditer(text):
            if match.group(1) != actual_user:
                return (
                    f"Absolute path names user '{match.group(1)}', but the active "
                    f"home belongs to '{actual_user}'. Use $HOME or the correct path."
                )
    return None


def _pre_tool_use(payload: dict[str, Any]) -> None:
    arguments = _tool_args(payload)
    reason = _wrong_home_reason(arguments)
    tool_name = str(payload.get("toolName") or payload.get("tool_name") or "")
    if reason is None and tool_name.lower() in {"bash", "powershell"}:
        reason = _destructive_reason(_command_text(arguments))
    if reason:
        _emit({"permissionDecision": "deny", "permissionDecisionReason": reason})


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


def _agent_stop(payload: dict[str, Any]) -> None:
    cwd_value = payload.get("cwd") or os.getcwd()
    cwd = Path(str(cwd_value))
    if not cwd.is_dir():
        return
    selected = _quality_command(cwd)
    if selected is None:
        _clear_quality_state(payload)
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
        print(f"ai-toolkit Copilot quality hook skipped {label}: {error}", file=sys.stderr)
        return
    if result.returncode == 0:
        _clear_quality_state(payload)
        return
    failures = _increment_quality_failures(payload)
    detail = (result.stdout + "\n" + result.stderr).strip()[-MAX_OUTPUT_CHARS:]
    if failures >= MAX_QUALITY_BLOCKS:
        print(
            f"ai-toolkit circuit breaker: {label} failed {failures} times; "
            "allowing stop so the agent can report the blocker.",
            file=sys.stderr,
        )
        _clear_quality_state(payload)
        return
    reason = f"{label} failed. Fix the errors and verify again before finishing."
    if detail:
        reason += f"\n\n{detail}"
    _emit({"decision": "block", "reason": reason})


def main() -> None:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    payload = _payload()
    if event == "session-start":
        _clear_quality_state(payload)
        _emit({
            "additionalContext": (
                "AI Toolkit: follow the repository and personal Copilot "
                "instructions, use relevant skills, keep tests and docs aligned, "
                "and verify evidence before claiming completion."
            )
        })
    elif event == "pre-tool-use":
        _pre_tool_use(payload)
    elif event == "post-tool-use":
        _emit({
            "additionalContext": (
                "A file-changing tool completed. Run the relevant validation and "
                "tests, and update affected documentation before finishing."
            )
        })
    elif event == "post-tool-use-failure":
        print(
            "The tool failed. Inspect the concrete error, gather evidence, and "
            "apply the smallest safe correction before retrying."
        )
        raise SystemExit(2)
    elif event == "subagent-start":
        _emit({
            "additionalContext": (
                "Stay within the delegated scope, cite concrete evidence, and return "
                "explicit validation notes with any edits."
            )
        })
    elif event == "agent-stop":
        _agent_stop(payload)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # Never turn an adapter bug into an agent loop.
        print(f"ai-toolkit Copilot hook failed safely: {error}", file=sys.stderr)
'''


HOOK_DEFINITIONS: tuple[tuple[str, str, str | None, int], ...] = (
    ("sessionStart", "session-start", None, 10),
    ("preToolUse", "pre-tool-use", None, 10),
    ("postToolUse", "post-tool-use", "create|edit", 10),
    ("postToolUseFailure", "post-tool-use-failure", None, 10),
    ("subagentStart", "subagent-start", None, 10),
    ("agentStop", "agent-stop", None, 120),
)


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _commands(script_path: Path, *, project_install: bool, action: str) -> tuple[str, str]:
    if project_install:
        relative = ".github/hooks/ai-toolkit/copilot_hook.py"
        return (
            f"python3 {shlex.quote(relative)} {shlex.quote(action)}",
            f"python {_powershell_quote(relative)} {_powershell_quote(action)}",
        )
    absolute = str(script_path.absolute())
    return (
        f"python3 {shlex.quote(absolute)} {shlex.quote(action)}",
        f"python {_powershell_quote(absolute)} {_powershell_quote(action)}",
    )


def build_hooks_json(script_path: Path, *, project_install: bool) -> dict[str, Any]:
    hooks: dict[str, list[dict[str, Any]]] = {}
    for event, action, matcher, timeout in HOOK_DEFINITIONS:
        bash, powershell = _commands(
            script_path,
            project_install=project_install,
            action=action,
        )
        entry: dict[str, Any] = {
            "type": "command",
            "bash": bash,
            "powershell": powershell,
            "cwd": ".",
            "env": {OWNER_KEY: OWNER_VALUE},
            "timeoutSec": timeout,
        }
        if matcher is not None:
            entry["matcher"] = matcher
        hooks.setdefault(event, []).append(entry)
    data = {"version": 1, "hooks": hooks}
    _validate_document(data)
    return data


def _validate_document(data: Any) -> None:
    if not isinstance(data, dict) or set(data) - {"version", "hooks", "disableAllHooks"}:
        raise ValueError("Copilot hooks file has unsupported top-level fields")
    if data.get("version") != 1 or not isinstance(data.get("hooks"), dict):
        raise ValueError("Copilot hooks file must contain version 1 and a hooks object")
    unsupported = set(data["hooks"]) - SUPPORTED_EVENTS
    if unsupported:
        raise ValueError(f"Unsupported Copilot hook events: {sorted(unsupported)}")
    for event, entries in data["hooks"].items():
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"Copilot hook event {event} must contain entries")
        for entry in entries:
            _validate_entry(event, entry)


def _validate_entry(event: str, entry: Any) -> None:
    if not isinstance(entry, dict) or set(entry) - COMMAND_KEYS:
        raise ValueError(f"Invalid Copilot command hook for {event}")
    if entry.get("type", "command") != "command":
        raise ValueError(f"Copilot {event} hook must use type=command")
    if not any(isinstance(entry.get(key), str) and entry[key] for key in (
        "bash", "powershell", "command"
    )):
        raise ValueError(f"Copilot {event} hook needs a shell command")
    if "matcher" in entry:
        if event not in MATCHER_EVENTS or not isinstance(entry["matcher"], str):
            raise ValueError(f"Copilot event {event} does not accept this matcher")
        re.compile(entry["matcher"])
    if "cwd" in entry and not isinstance(entry["cwd"], str):
        raise ValueError(f"Copilot {event} cwd must be a string")
    env = entry.get("env", {})
    if not isinstance(env, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in env.items()
    ):
        raise ValueError(f"Copilot {event} env must contain strings")
    for key in ("timeout", "timeoutSec"):
        if key in entry and (
            not isinstance(entry[key], (int, float)) or isinstance(entry[key], bool)
            or entry[key] <= 0
        ):
            raise ValueError(f"Copilot {event} {key} must be positive")


def _is_managed_config_content(content: bytes) -> bool:
    try:
        data = json.loads(content.decode("utf-8"))
        _validate_document(data)
    except (UnicodeError, json.JSONDecodeError, ValueError):
        return False
    entries = [entry for values in data["hooks"].values() for entry in values]
    return bool(entries) and all(
        entry.get("env", {}).get(OWNER_KEY) == OWNER_VALUE
        for entry in entries
    )


def _is_managed_config(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        return _is_managed_config_content(path.read_bytes())
    except OSError:
        return False


def _is_managed_script_content(content: bytes) -> bool:
    try:
        return SCRIPT_MARKER in content[:256].decode("utf-8")
    except UnicodeError:
        return False


def _is_managed_script(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        return _is_managed_script_content(path.read_bytes())
    except OSError:
        return False


def _assert_safe_paths(paths: list[tuple[Path, str]]) -> None:
    for path, label in paths:
        if path.is_symlink():
            raise RuntimeError(f"Refusing symlinked Copilot {label}: {path}")


def _assert_collisions(config_path: Path, script_path: Path) -> None:
    if config_path.exists() and not _is_managed_config(config_path):
        raise RuntimeError(f"Refusing user-owned Copilot hook config collision: {config_path}")
    if script_path.exists() and not _is_managed_script(script_path):
        raise RuntimeError(f"Refusing user-owned Copilot hook runtime collision: {script_path}")


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
                mode = destination.stat().st_mode & 0o777
                backups[destination] = _stage_file(
                    destination,
                    destination.read_bytes(),
                    mode,
                )
        for temp_path, destination in staged:
            if destination.is_symlink():
                raise RuntimeError(f"Copilot hook path became a symlink: {destination}")
            os.replace(temp_path, destination)
            applied.append(destination)
        for directory in {destination.parent for _, destination in staged}:
            try:
                descriptor = os.open(directory, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            except OSError:
                pass
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
                f"Copilot hook update failed and rollback was incomplete: {rollback_errors}"
            ) from error
        raise
    finally:
        for temp_path, _ in staged:
            temp_path.unlink(missing_ok=True)
        for backup in backups.values():
            backup.unlink(missing_ok=True)


def copilot_home(home: Path | None = None) -> Path:
    """Return the active user configuration root, honoring ``COPILOT_HOME``."""
    configured = os.environ.get("COPILOT_HOME")
    if configured:
        return Path(configured).expanduser().absolute()
    base = Path.home() if home is None else Path(home).expanduser().absolute()
    return base / ".copilot"


def _cleanup_targets(
    target_dir: Path,
    config_root: Path | None,
) -> tuple[Path, Path, Path, list[SecureDestination]]:
    """Resolve and validate every hook-cleanup destination without mutation."""
    target_dir = Path(target_dir).expanduser().absolute()
    project_install = config_root is None
    customization_root = (
        target_dir / ".github"
        if project_install
        else Path(config_root).expanduser().absolute()
    )
    hooks_dir = customization_root / "hooks"
    assets_dir = hooks_dir / "ai-toolkit"
    config_path = hooks_dir / CONFIG_NAME
    script_path = assets_dir / SCRIPT_NAME
    _assert_safe_paths([
        (customization_root, "customization root"),
        (hooks_dir, "hooks directory"),
        (assets_dir, "hook assets directory"),
        (config_path, "hook config"),
        (script_path, "hook runtime"),
    ])
    existing_paths: list[tuple[Path, str]] = []
    if config_path.exists():
        existing_paths.append((config_path, "hook config"))
    if script_path.exists():
        existing_paths.append((script_path, "hook runtime"))
    trusted_root = target_dir if project_install else customization_root
    destinations = [
        SecureDestination(path, trusted_root, f"Copilot {label}")
        for path, label in existing_paths
    ]
    return hooks_dir, config_path, script_path, destinations


def _require_secure_cleanup() -> None:
    if secure_fs.SECURE_DIR_FD:
        return
    raise RuntimeError(
        "Copilot hook cleanup requires POSIX dir_fd and O_NOFOLLOW; "
        "No files were changed"
    )


def preflight_cleanup(
    target_dir: Path,
    *,
    config_root: Path | None = None,
) -> None:
    """Fail before installer mutations when hook cleanup cannot run safely."""
    _, _, _, destinations = _cleanup_targets(target_dir, config_root)
    if not destinations:
        return
    _require_secure_cleanup()
    run_secure_transaction(destinations, lambda _transaction: None)


def cleanup(target_dir: Path, *, config_root: Path | None = None) -> None:
    """Remove only the managed Copilot hook bundle for a profile downgrade."""
    hooks_dir, config_path, script_path, destinations = _cleanup_targets(
        target_dir,
        config_root,
    )
    if not destinations:
        return
    _require_secure_cleanup()

    def remove_managed(transaction) -> bool:
        contents = {
            destination.path: transaction.initial_content(destination)
            for destination in destinations
        }
        config_content = contents.get(config_path)
        script_content = contents.get(script_path)
        config_owned = (
            config_content is None or _is_managed_config_content(config_content)
        )
        script_owned = (
            script_content is None or _is_managed_script_content(script_content)
        )
        if not config_owned or not script_owned:
            print(
                f"Warning: preserving user-owned Copilot hook bundle at '{hooks_dir}'",
                file=sys.stderr,
            )
            return False
        for destination in destinations:
            transaction.unlink(destination)
        return True

    if run_secure_transaction(destinations, remove_managed):
        label = (
            ".github/hooks"
            if config_root is None
            else str(hooks_dir)
        )
        print(f"  Removed managed: {label}/{CONFIG_NAME}")


def generate(target_dir: Path, *, config_root: Path | None = None) -> None:
    """Generate repository hooks, or user hooks when ``config_root`` is set."""
    target_dir = Path(target_dir).expanduser().absolute()
    project_install = config_root is None
    customization_root = (
        target_dir / ".github" if project_install
        else Path(config_root).expanduser().absolute()
    )
    hooks_dir = customization_root / "hooks"
    assets_dir = hooks_dir / "ai-toolkit"
    config_path = hooks_dir / CONFIG_NAME
    script_path = assets_dir / SCRIPT_NAME
    safe_paths = [
        (target_dir, "target root"),
        (customization_root, "customization root"),
        (hooks_dir, "hooks directory"),
        (assets_dir, "hook assets directory"),
        (config_path, "hook config"),
        (script_path, "hook runtime"),
    ]
    _assert_safe_paths(safe_paths)
    for directory in (customization_root, hooks_dir, assets_dir):
        if directory.exists() and not directory.is_dir():
            raise RuntimeError(f"Copilot hook path is not a directory: {directory}")
        directory.mkdir(parents=True, exist_ok=True)
    _assert_safe_paths(safe_paths)
    _assert_collisions(config_path, script_path)

    data = build_hooks_json(script_path, project_install=project_install)
    config_bytes = (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode()
    _write_transaction([
        (script_path, HOOK_RUNTIME.encode(), 0o755),
        (config_path, config_bytes, 0o644),
    ])
    label = ".github/hooks" if project_install else str(hooks_dir)
    print(f"  Generated: {label}/{CONFIG_NAME} (native Copilot hooks)")


def main() -> None:
    args = sys.argv[1:]
    user_install = "--global" in args or "--user" in args
    positional = [arg for arg in args if not arg.startswith("--")]
    target = Path(positional[0]) if positional else Path.cwd()
    if user_install:
        generate(target, config_root=copilot_home(target))
    else:
        generate(target)


if __name__ == "__main__":
    main()
