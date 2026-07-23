#!/usr/bin/env python3
"""Generate native, self-contained Codex hooks without bypassing trust.

Project installs write ``.codex/hooks.json`` and executable assets under
``.codex/hooks/``. Global installs write the same JSON under ``$CODEX_HOME``
(default ``~/.codex``) and assets under its ``ai-toolkit-hooks/`` directory.
Existing user command hooks are preserved; only handlers carrying ai-toolkit's
command marker (or its legacy shared-hook path) are replaced.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from secure_fs import (
    SECURE_DIR_FD,
    SecureDestination,
    SecureTransaction,
    lexical_absolute,
    nearest_existing_root,
    run_secure_transaction,
)


TOOLKIT_COMMAND_MARKER = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit"
SCRIPT_MARKER = "# ai-toolkit-managed: codex-hook-script"
LEGACY_COMMAND_MARKER = ".softspark/ai-toolkit/hooks/"
PLUGIN_OWNER_PATTERN = re.compile(r"ai-toolkit-plugin-[a-z0-9][a-z0-9-]*")
COMMAND_OWNER_PATTERN = re.compile(
    r"(?:^|\s)AI_TOOLKIT_HOOK_OWNER=(?P<owner>[a-z0-9][a-z0-9-]*)(?=\s|$)"
)
_SECURE_DIR_FD = SECURE_DIR_FD
_UNSAFE_MUTATION_PLATFORM_ERROR = (
    "Safe Codex hook mutations require POSIX dir_fd and O_NOFOLLOW support, "
    "which this Python runtime does not provide. No files were changed. "
    "On Windows, generate or update Codex hooks from WSL."
)


def _require_secure_mutation_support() -> None:
    if not _SECURE_DIR_FD:
        raise RuntimeError(_UNSAFE_MUTATION_PLATFORM_ERROR)


SUPPORTED_EVENTS = frozenset(
    {
        "PreToolUse",
        "PostToolUse",
        "PermissionRequest",
        "PreCompact",
        "PostCompact",
        "SessionStart",
        "UserPromptSubmit",
        "SubagentStart",
        "SubagentStop",
        "Stop",
    }
)

GROUP_KEYS = frozenset({"matcher", "hooks"})
HANDLER_KEYS = frozenset(
    {
        "type",
        "command",
        "commandWindows",
        "timeout",
        "statusMessage",
        "async",
    }
)

# Format: event -> (matcher, executable asset). Empty matchers are omitted.
CODEX_HOOKS: dict[str, list[tuple[str, str]]] = {
    "SessionStart": [
        ("startup|resume", "codex-session-start.sh"),
        ("startup|resume", "codex-mcp-health.sh"),
    ],
    "PreToolUse": [
        ("Bash", "guard-destructive.sh"),
        ("Bash", "guard-path.sh"),
        ("Bash", "commit-quality.sh"),
        ("Bash", "revert-guard.sh"),
    ],
    "PostToolUse": [
        ("Bash", "governance-capture.sh"),
        ("Bash", "loop-guard.sh"),
    ],
    "PermissionRequest": [
        ("Bash", "guard-destructive.sh"),
        ("Bash", "guard-path.sh"),
    ],
    "UserPromptSubmit": [
        ("", "user-prompt-submit.sh"),
        ("", "track-usage.sh"),
    ],
    "SubagentStart": [
        ("", "subagent-start.sh"),
    ],
    "SubagentStop": [
        ("", "subagent-stop.sh"),
    ],
    "PreCompact": [
        ("", "codex-pre-compact.sh"),
    ],
    "Stop": [
        ("", "quality-check.sh"),
        ("", "save-session.sh"),
        ("", "codex-stop-search-check.sh"),
    ],
}

HELPER_ASSETS = frozenset(
    {
        "_hook-io.sh",
        "_locate-toolkit.sh",
        "_profile-check.sh",
        "_search-capability.sh",
        "_session-paths.sh",
    }
)

CODEX_STOP_SEARCH_ADAPTER = r"""#!/usr/bin/env bash
# Convert the shared Stop search guard's legacy decision object into Codex's
# documented Stop output fields.
INPUT=$(cat)
OUTPUT=$(printf '%s' "$INPUT" | "$(dirname "$0")/stop-search-check.sh")
STATUS=$?
[ "$STATUS" -eq 0 ] || exit "$STATUS"
[ -n "$OUTPUT" ] || exit 0
if printf '%s' "$OUTPUT" | jq -e '.decision == "block"' >/dev/null 2>&1; then
    REASON=$(printf '%s' "$OUTPUT" | jq -r '.reason // "Hook requested another turn."')
    jq -nc --arg reason "$REASON" \
        '{"continue":false,"stopReason":$reason,"systemMessage":$reason}'
else
    printf '%s\n' "$OUTPUT"
fi
"""

CODEX_SESSION_START_ADAPTER = r"""#!/usr/bin/env bash
# Native Codex SessionStart context. Plain stdout becomes developer context.
cat >/dev/null || true
cat <<'EOF'
AI Toolkit: apply the active AGENTS.md instruction chain and repository rules before technical work. Use current Codex skills when their descriptions match. For changes, keep tests and affected documentation aligned, and verify before claiming completion.
EOF
"""

CODEX_PRE_COMPACT_ADAPTER = r"""#!/usr/bin/env bash
# Native Codex PreCompact reminder. Plain stdout is retained as hook context.
cat >/dev/null || true
printf '%s\n' 'AI Toolkit: context is being compacted. Re-read the active AGENTS.md instruction chain, the current plan, and git status before continuing.'
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf 'Branch: %s; uncommitted paths: %s\n' \
        "$(git branch --show-current 2>/dev/null || printf detached)" \
        "$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
fi
"""

CODEX_MCP_HEALTH_ADAPTER = r"""#!/usr/bin/env bash
# Check documented Codex MCP config layers without starting any MCP server.
cat >/dev/null || true
command -v python3 >/dev/null 2>&1 || exit 0
PROJECT_CONFIG=""
if command -v git >/dev/null 2>&1; then
    PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
    [ -n "$PROJECT_ROOT" ] && PROJECT_CONFIG="$PROJECT_ROOT/.codex/config.toml"
fi
python3 - "${CODEX_HOME:-$HOME/.codex}/config.toml" "$PROJECT_CONFIG" <<'PY'
import shutil
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    raise SystemExit(0)

for raw_path in sys.argv[1:]:
    if not raw_path:
        continue
    path = Path(raw_path)
    if not path.is_file() or path.is_symlink():
        continue
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        continue
    servers = data.get("mcp_servers", {})
    if not isinstance(servers, dict):
        continue
    for name, config in servers.items():
        if not isinstance(config, dict) or config.get("enabled") is False:
            continue
        command = config.get("command")
        if isinstance(command, str) and command and shutil.which(command) is None:
            print(f"MCP health: {name} command not found ({command}).")
PY
"""

GENERATED_ADAPTERS = {
    "codex-stop-search-check.sh": CODEX_STOP_SEARCH_ADAPTER,
    "codex-session-start.sh": CODEX_SESSION_START_ADAPTER,
    "codex-pre-compact.sh": CODEX_PRE_COMPACT_ADAPTER,
    "codex-mcp-health.sh": CODEX_MCP_HEALTH_ADAPTER,
}


def _source_hooks_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "app" / "hooks"


def _asset_names() -> set[str]:
    names = {
        script
        for entries in CODEX_HOOKS.values()
        for _, script in entries
        if script not in GENERATED_ADAPTERS
    }
    names.update(HELPER_ASSETS)
    names.add("stop-search-check.sh")
    names.update(GENERATED_ADAPTERS)
    return names


def _command_for(script: str, global_install: bool) -> str:
    if global_install:
        executable = f'"${{CODEX_HOME:-$HOME/.codex}}/ai-toolkit-hooks/{script}"'
    else:
        executable = (
            f'"$(git rev-parse --show-toplevel 2>/dev/null)/.codex/hooks/{script}"'
        )
    return f"AI_TOOLKIT_HOOK_QUIET=1 {TOOLKIT_COMMAND_MARKER} {executable}"


def build_hooks_json(*, global_install: bool = False) -> dict[str, Any]:
    """Build only ai-toolkit's schema-valid native command handlers."""
    hooks: dict[str, list[dict[str, Any]]] = {}
    for event, entries in CODEX_HOOKS.items():
        groups: list[dict[str, Any]] = []
        for matcher, script in entries:
            group: dict[str, Any] = {
                "hooks": [
                    {
                        "type": "command",
                        "command": _command_for(script, global_install),
                    }
                ]
            }
            if matcher:
                group["matcher"] = matcher
            groups.append(group)
        hooks[event] = groups
    result = {"hooks": hooks}
    _validate_hooks_document(result)
    return result


def _validate_hooks_document(data: Any) -> None:
    if not isinstance(data, dict) or set(data) - {"hooks"}:
        raise ValueError("Codex hooks.json must contain only the top-level hooks key")
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("Codex hooks.json hooks must be an object")
    unsupported = set(hooks) - SUPPORTED_EVENTS
    if unsupported:
        raise ValueError(f"Unsupported Codex hook events: {sorted(unsupported)}")

    for event, groups in hooks.items():
        if not isinstance(groups, list):
            raise ValueError(f"Codex hook event {event} must contain a list")
        for group in groups:
            _validate_matcher_group(event, group)


def _validate_matcher_group(event: str, group: Any) -> None:
    if not isinstance(group, dict) or "hooks" not in group:
        raise ValueError(f"Codex {event} matcher group must contain hooks")
    unknown = set(group) - GROUP_KEYS
    if unknown:
        raise ValueError(f"Unknown Codex {event} matcher keys: {sorted(unknown)}")
    matcher = group.get("matcher")
    if matcher is not None:
        if not isinstance(matcher, str):
            raise ValueError(f"Codex {event} matcher must be a string")
        re.compile(matcher)
    if event in {"UserPromptSubmit", "Stop"} and "matcher" in group:
        raise ValueError(f"Codex {event} does not support matchers")

    handlers = group["hooks"]
    if not isinstance(handlers, list) or not handlers:
        raise ValueError(f"Codex {event} matcher group must have command handlers")
    for handler in handlers:
        _validate_handler(event, handler)


def _validate_handler(event: str, handler: Any) -> None:
    if not isinstance(handler, dict):
        raise ValueError(f"Codex {event} handler must be an object")
    unknown = set(handler) - HANDLER_KEYS
    if unknown:
        raise ValueError(f"Unknown Codex {event} handler keys: {sorted(unknown)}")
    command = handler.get("command")
    if (
        handler.get("type") != "command"
        or not isinstance(command, str)
        or not command.strip()
    ):
        raise ValueError(f"Codex {event} supports executable command handlers only")
    if "timeout" in handler:
        timeout = handler["timeout"]
        if type(timeout) is not int or timeout <= 0:
            raise ValueError(f"Codex {event} timeout must be a positive integer")
    for key in ("commandWindows", "statusMessage"):
        if key in handler and not isinstance(handler[key], str):
            raise ValueError(f"Codex {event} {key} must be a string")
    if "async" in handler and not isinstance(handler["async"], bool):
        raise ValueError(f"Codex {event} async must be boolean")


def _normalize_legacy_plugin_groups(data: Any) -> Any:
    """Remove the retired ``_source`` key from known toolkit plugin groups.

    Older ai-toolkit releases used Claude's private ownership key in Codex
    ``hooks.json``. Keep those handlers usable during upgrade by moving their
    ownership into the command marker that the native schema accepts.
    """
    if not isinstance(data, dict) or not isinstance(data.get("hooks", {}), dict):
        return data
    for groups in data.get("hooks", {}).values():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict) or "_source" not in group:
                continue
            owner = group.get("_source")
            if (
                not isinstance(owner, str)
                or PLUGIN_OWNER_PATTERN.fullmatch(owner) is None
            ):
                continue
            if set(group) - GROUP_KEYS - {"_source"}:
                continue
            handlers = group.get("hooks")
            if not isinstance(handlers, list):
                continue
            for handler in handlers:
                if not isinstance(handler, dict):
                    continue
                command = handler.get("command")
                if not isinstance(command, str) or not command.strip():
                    continue
                match = COMMAND_OWNER_PATTERN.search(command)
                if match is not None and match.group("owner") != owner:
                    raise ValueError(
                        "Legacy Codex plugin hook owner conflicts with its command marker"
                    )
                if match is None:
                    handler["command"] = f"AI_TOOLKIT_HOOK_OWNER={owner} {command}"
            del group["_source"]
    return data


def _load_existing_hooks_bytes(
    content: bytes | None,
    hooks_path: Path,
) -> dict[str, Any]:
    if content is None:
        return {"hooks": {}}
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Cannot read existing Codex hooks: {hooks_path}: {error}"
        ) from error
    data = _normalize_legacy_plugin_groups(data)
    _validate_hooks_document(data)
    data.setdefault("hooks", {})
    return data


def _load_existing_hooks(hooks_path: Path) -> dict[str, Any]:
    if not hooks_path.exists():
        return {"hooks": {}}
    try:
        content = hooks_path.read_bytes()
    except OSError as error:
        raise ValueError(
            f"Cannot read existing Codex hooks: {hooks_path}: {error}"
        ) from error
    return _load_existing_hooks_bytes(content, hooks_path)


def _is_managed_handler(handler: dict[str, Any]) -> bool:
    command = handler.get("command", "")
    owner_match = COMMAND_OWNER_PATTERN.search(command)
    if owner_match is not None:
        owner = owner_match.group("owner")
        if PLUGIN_OWNER_PATTERN.fullmatch(owner) is not None:
            return False
        if owner == "ai-toolkit":
            return True
    return LEGACY_COMMAND_MARKER in command


def _merge_hooks(existing: dict[str, Any], generated: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {"hooks": {}}
    for event, groups in existing.get("hooks", {}).items():
        retained_groups: list[dict[str, Any]] = []
        for group in groups:
            retained = [
                handler
                for handler in group["hooks"]
                if not _is_managed_handler(handler)
            ]
            if retained:
                retained_group = dict(group)
                retained_group["hooks"] = retained
                retained_groups.append(retained_group)
        if retained_groups:
            merged["hooks"][event] = retained_groups

    for event, groups in generated["hooks"].items():
        merged["hooks"].setdefault(event, []).extend(groups)
    _validate_hooks_document(merged)
    return merged


def _managed_asset_content(name: str) -> bytes:
    if name in GENERATED_ADAPTERS:
        text = GENERATED_ADAPTERS[name]
    else:
        source = _source_hooks_dir() / name
        if source.is_symlink() or not source.is_file():
            raise RuntimeError(f"Missing safe Codex hook source asset: {source}")
        text = source.read_text(encoding="utf-8")

    lines = text.splitlines(keepends=True)
    marker_line = f"{SCRIPT_MARKER}\n"
    if lines and lines[0].startswith("#!"):
        text = "".join((lines[0], marker_line, *lines[1:]))
    else:
        text = marker_line + text
    return text.encode("utf-8")


def _is_managed_asset(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        prefix = path.read_text(encoding="utf-8")[:256]
    except (OSError, UnicodeError):
        return False
    return SCRIPT_MARKER in prefix


def _assert_safe_paths(
    target_dir: Path, codex_dir: Path, assets_dir: Path, hooks_path: Path
) -> None:
    for path, label in (
        (target_dir, "target"),
        (codex_dir, ".codex"),
        (assets_dir, "hook assets"),
        (hooks_path, "hooks.json"),
    ):
        if path.is_symlink():
            raise RuntimeError(f"Refusing symlinked Codex {label}: {path}")


def _assert_no_asset_collisions(assets_dir: Path, names: set[str]) -> None:
    if not assets_dir.exists():
        return
    if not assets_dir.is_dir():
        raise RuntimeError(f"Codex hook assets path is not a directory: {assets_dir}")
    for name in names:
        destination = assets_dir / name
        if destination.is_symlink():
            raise RuntimeError(f"Refusing symlinked Codex hook asset: {destination}")
        if destination.exists() and not _is_managed_asset(destination):
            raise RuntimeError(
                f"Refusing user-owned Codex hook asset collision: {destination}"
            )


def _write_outputs(
    hooks_path: Path,
    assets_dir: Path,
    generated_hooks: dict[str, Any],
    assets: dict[str, bytes],
    trusted_root: Path,
    stale: list[SecureDestination],
) -> None:
    _require_secure_mutation_support()
    asset_outputs: list[tuple[SecureDestination, bytes]] = []
    for name in sorted(assets):
        asset_outputs.append(
            (
                SecureDestination(
                    assets_dir / name,
                    trusted_root,
                    f"Codex hook asset {name}",
                ),
                assets[name],
            )
        )
    hooks_destination = SecureDestination(
        hooks_path,
        trusted_root,
        "Codex hooks.json",
    )

    def apply(transaction: SecureTransaction) -> None:
        marker = SCRIPT_MARKER.encode()
        existing_hooks = _load_existing_hooks_bytes(
            transaction.initial_content(hooks_destination),
            hooks_path,
        )
        merged_hooks = _merge_hooks(existing_hooks, generated_hooks)
        hooks_content = (
            json.dumps(merged_hooks, indent=4, ensure_ascii=False) + "\n"
        ).encode()

        for destination, _ in asset_outputs:
            existing = transaction.initial_content(destination)
            if existing is not None and marker not in existing[:256]:
                raise RuntimeError(
                    f"Refusing user-owned Codex hook asset collision: "
                    f"{destination.path}"
                )
        for destination, content in asset_outputs:
            transaction.atomic_write(destination, content, 0o755)
        transaction.atomic_write(hooks_destination, hooks_content)

        for destination in stale:
            existing = transaction.initial_content(destination)
            if existing is not None and marker in existing[:256]:
                transaction.unlink(destination)

    destinations = [item[0] for item in asset_outputs]
    destinations.append(hooks_destination)
    destinations.extend(stale)
    run_secure_transaction(destinations, apply)


def _stale_asset_destinations(
    assets_dir: Path,
    expected_names: set[str],
    trusted_root: Path,
) -> list[SecureDestination]:
    if not assets_dir.is_dir():
        return []
    stale: list[SecureDestination] = []
    for path in assets_dir.iterdir():
        if path.name in expected_names or path.is_symlink() or not path.is_file():
            continue
        stale.append(
            SecureDestination(
                path,
                trusted_root,
                f"stale Codex hook asset {path.name}",
            )
        )
    return stale


def write_hooks_json(
    hooks_path: Path,
    data: dict[str, Any],
    *,
    transaction: SecureTransaction | None = None,
    trusted_root: Path | None = None,
) -> None:
    """Validate and atomically replace a Codex hooks document."""
    _require_secure_mutation_support()
    _validate_hooks_document(data)
    hooks_path = lexical_absolute(hooks_path)
    root = (
        lexical_absolute(trusted_root)
        if trusted_root is not None
        else nearest_existing_root(hooks_path.parent)
    )
    destination = SecureDestination(hooks_path, root, "Codex hooks.json")
    content = (json.dumps(data, indent=4, ensure_ascii=False) + "\n").encode()
    if transaction is not None:
        transaction.atomic_write(destination, content)
        return
    run_secure_transaction(
        [destination],
        lambda secure_transaction: secure_transaction.atomic_write(
            destination, content
        ),
    )


def load_hooks_json(hooks_path: Path) -> dict[str, Any]:
    """Load, migrate, and validate a native Codex hooks document safely."""
    hooks_path = Path(hooks_path)
    codex_dir = hooks_path.parent
    if (
        hooks_path.is_symlink()
        or codex_dir.is_symlink()
        or codex_dir.parent.is_symlink()
    ):
        raise RuntimeError(f"Refusing symlinked Codex hooks path: {hooks_path}")
    return _load_existing_hooks(hooks_path)


def parse_hooks_json_bytes(
    content: bytes | None,
    hooks_path: Path,
) -> dict[str, Any]:
    """Parse a hooks snapshot already captured by a secure transaction."""
    return _load_existing_hooks_bytes(content, hooks_path)


def validate_hooks_document(data: Any) -> None:
    """Validate a Codex hooks document without writing it."""
    _validate_hooks_document(data)


def _infer_global_install(target_dir: Path) -> bool:
    return os.path.abspath(target_dir) == os.path.abspath(Path.home())


def _global_codex_home(target_dir: Path, explicit_home: Path | None) -> Path:
    if explicit_home is not None:
        return Path(explicit_home).expanduser()
    configured = os.environ.get("CODEX_HOME")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            raise RuntimeError("CODEX_HOME must be an absolute path")
        if not path.is_dir():
            raise RuntimeError("Configured CODEX_HOME must already exist")
        return path
    return target_dir / ".codex"


def generate(
    target_dir: Path,
    *,
    global_install: bool | None = None,
    codex_home: Path | None = None,
) -> None:
    """Merge native Codex hooks and install their self-contained assets."""
    _require_secure_mutation_support()
    target_dir = lexical_absolute(target_dir)
    if global_install is None:
        global_install = _infer_global_install(target_dir)

    codex_dir = (
        _global_codex_home(target_dir, codex_home)
        if global_install
        else target_dir / ".codex"
    )
    codex_dir = lexical_absolute(codex_dir)
    hooks_path = codex_dir / "hooks.json"
    assets_dir = codex_dir / ("ai-toolkit-hooks" if global_install else "hooks")
    _assert_safe_paths(target_dir, codex_dir, assets_dir, hooks_path)

    generated = build_hooks_json(global_install=global_install)
    names = _asset_names()
    assets = {name: _managed_asset_content(name) for name in names}
    _assert_no_asset_collisions(assets_dir, names)

    trusted_root = (
        codex_dir if codex_dir.is_dir() else nearest_existing_root(codex_dir.parent)
    )
    stale = _stale_asset_destinations(assets_dir, names, trusted_root)
    _write_outputs(
        hooks_path,
        assets_dir,
        generated,
        assets,
        trusted_root,
        stale,
    )

    if global_install:
        print(
            "Codex global hooks changed. Review and trust them with /hooks before use."
        )
    else:
        print(
            "Codex project hooks require a trusted .codex project layer. "
            "Review and trust the exact definitions with /hooks before use."
        )


def main() -> None:
    args = sys.argv[1:]
    global_install = "--global" in args
    positional = [arg for arg in args if not arg.startswith("--")]
    target = Path(positional[0]) if positional else Path.cwd()
    generate(target, global_install=True if global_install else None)
    hook_count = sum(len(entries) for entries in CODEX_HOOKS.values())
    print(f"Generated: .codex/hooks.json ({hook_count} hooks)")


if __name__ == "__main__":
    main()
