#!/usr/bin/env python3
"""Editor-specific MCP config adapters for ai-toolkit."""

from __future__ import annotations

import copy
import errno
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.11+ should have tomllib
    tomllib = None


EDITOR_SPECS: dict[str, dict[str, str | None]] = {
    "claude": {
        "label": "Claude Code",
        "project_path": ".mcp.json",
        "global_path": ".claude.json",
        "format": "json",
        "doc_scope": "project + global",
    },
    "cursor": {
        "label": "Cursor",
        "project_path": ".cursor/mcp.json",
        "global_path": ".cursor/mcp.json",
        "format": "json",
        "doc_scope": "project + global",
    },
    "copilot": {
        "label": "GitHub Copilot",
        "project_path": ".github/mcp.json",
        "global_path": ".copilot/mcp-config.json",
        "format": "json",
        "doc_scope": "project + global",
    },
    "gemini": {
        "label": "Gemini CLI",
        "project_path": ".gemini/settings.json",
        "global_path": ".gemini/settings.json",
        "format": "json",
        "doc_scope": "project + global",
    },
    "antigravity": {
        "label": "Google Antigravity",
        "project_path": ".agents/mcp_config.json",
        "global_path": ".gemini/config/mcp_config.json",
        "format": "json",
        "doc_scope": "project + global",
    },
    "roo": {
        "label": "Roo Code",
        "project_path": ".roo/mcp.json",
        "global_path": None,
        "format": "json",
        "doc_scope": "project",
    },
    "windsurf": {
        "label": "Windsurf",
        "project_path": None,
        "global_path": ".codeium/windsurf/mcp_config.json",
        "format": "json",
        "doc_scope": "global",
    },
    "cline": {
        "label": "Cline",
        "project_path": None,
        "global_path": ".cline/data/settings/cline_mcp_settings.json",
        "format": "json",
        "doc_scope": "global",
    },
    "augment": {
        "label": "Augment",
        "project_path": None,
        "global_path": ".augment/settings.json",
        "format": "json",
        "doc_scope": "global",
    },
    "codex": {
        "label": "Codex CLI",
        "project_path": ".codex/config.toml",
        "global_path": ".codex/config.toml",
        "format": "toml",
        "doc_scope": "project + global",
    },
}


CODEX_MCP_BLOCK_START = "# >>> ai-toolkit managed Codex MCP servers >>>"
CODEX_MCP_BLOCK_END = "# <<< ai-toolkit managed Codex MCP servers <<<"

_TOML_BARE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_CODEX_SHARED_SERVER_KEYS = frozenset(
    {
        "startup_timeout_sec",
        "startup_timeout_ms",
        "tool_timeout_sec",
        "enabled",
        "required",
        "enabled_tools",
        "disabled_tools",
        "scopes",
        "oauth_resource",
        "default_tools_approval_mode",
        "tools",
    }
)
_CODEX_STDIO_SERVER_KEYS = frozenset(
    {
        "command",
        "args",
        "env",
        "env_vars",
        "cwd",
        "experimental_environment",
    }
)
_CODEX_HTTP_SERVER_KEYS = frozenset(
    {
        "url",
        "auth",
        "bearer_token_env_var",
        "http_headers",
        "env_http_headers",
    }
)
_CODEX_PORTABLE_TRANSPORT_KEYS = {
    "http": "url",
    "local": "command",
    "stdio": "command",
}
_CODEX_APPROVAL_MODES = frozenset({"auto", "prompt", "writes", "approve"})
_UNSUPPORTED_DIRECTORY_FSYNC_ERRNOS = frozenset(
    {
        errno.EBADF,
        errno.EINVAL,
        getattr(errno, "ENOTSUP", errno.EINVAL),
        getattr(errno, "EOPNOTSUPP", errno.EINVAL),
    }
)


PROJECT_SCOPED_EDITORS = {
    name for name, spec in EDITOR_SPECS.items() if spec.get("project_path")
}


@dataclass(frozen=True, slots=True)
class ConfigUpdate:
    """A preflighted config-file replacement used by an MCP transaction."""

    path: Path
    original: bytes | None
    content: bytes | None


def supported_editors() -> list[str]:
    """Return all editor ids with native MCP adapters."""
    return sorted(EDITOR_SPECS)


def editor_rows() -> list[dict[str, str]]:
    """Return display metadata for `ai-toolkit mcp editors`."""
    rows: list[dict[str, str]] = []
    for name in supported_editors():
        spec = EDITOR_SPECS[name]
        rows.append(
            {
                "name": name,
                "label": str(spec["label"]),
                "scope": str(spec["doc_scope"]),
                "project_path": str(spec.get("project_path") or "—"),
                "global_path": str(spec.get("global_path") or "—"),
                "format": str(spec["format"]),
            }
        )
    return rows


def _resolve_global_config_root(
    *,
    home: Path | None,
    env_name: str,
    default_dir: str,
) -> Path:
    """Resolve an editor config root without following an environment symlink."""
    if home is not None:
        return (home / default_dir).expanduser().absolute()

    configured = os.environ.get(env_name, "").strip()
    if not configured:
        return (Path.home() / default_dir).absolute()

    config_root = Path(configured).expanduser()
    if not config_root.is_absolute():
        raise ValueError(f"Configured {env_name} must be absolute: {configured}")
    config_root = config_root.absolute()
    if config_root.is_symlink():
        raise RuntimeError(
            f"Configured {env_name} must not be a symlink: {config_root}"
        )
    if not config_root.exists():
        raise FileNotFoundError(f"Configured {env_name} does not exist: {config_root}")
    if not config_root.is_dir():
        raise NotADirectoryError(
            f"Configured {env_name} is not a directory: {config_root}"
        )
    return config_root


def resolve_editor_path(
    editor: str,
    scope: str,
    *,
    project_dir: Path | None = None,
    home: Path | None = None,
) -> Path:
    """Resolve the native config path for an editor + scope."""
    if editor not in EDITOR_SPECS:
        raise ValueError(f"Unsupported editor: {editor}")
    spec = EDITOR_SPECS[editor]
    if scope == "project":
        rel = spec.get("project_path")
        if not rel:
            raise ValueError(
                f"Editor '{editor}' does not support project-scoped MCP config"
            )
        base = project_dir or Path.cwd()
        return base / str(rel)
    if scope == "global":
        rel = spec.get("global_path")
        if not rel:
            raise ValueError(f"Editor '{editor}' does not support global MCP config")
        if editor == "copilot":
            copilot_home = _resolve_global_config_root(
                home=home,
                env_name="COPILOT_HOME",
                default_dir=".copilot",
            )
            return copilot_home / "mcp-config.json"
        if editor == "codex":
            codex_home = _resolve_global_config_root(
                home=home,
                env_name="CODEX_HOME",
                default_dir=".codex",
            )
            return codex_home / "config.toml"
        return (home or Path.home()) / str(rel)
    raise ValueError(f"Unsupported scope: {scope}")


def load_project_mcp_servers(project_dir: Path) -> dict:
    """Load `.mcp.json` servers from a project directory."""
    config_path = project_dir / ".mcp.json"
    _assert_safe_config_path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"{config_path} not found")
    data = load_json_config(config_path)
    servers = data.get("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError(f"{config_path} has invalid mcpServers data")
    return servers


def install_servers(
    editors: list[str],
    servers: dict,
    *,
    scope: str,
    project_dir: Path | None = None,
    home: Path | None = None,
) -> list[Path]:
    """Merge servers into native editor config files."""
    updates = prepare_install_servers(
        editors,
        servers,
        scope=scope,
        project_dir=project_dir,
        home=home,
    )
    apply_config_updates(updates)
    return [update.path for update in updates]


def prepare_install_servers(
    editors: list[str],
    servers: dict,
    *,
    scope: str,
    project_dir: Path | None = None,
    home: Path | None = None,
) -> list[ConfigUpdate]:
    """Preflight all native editor merges without mutating any destination."""
    updates: list[ConfigUpdate] = []
    seen_paths: set[Path] = set()
    for editor in editors:
        path = resolve_editor_path(
            editor,
            scope,
            project_dir=project_dir,
            home=home,
        )
        identity = path.absolute()
        if identity in seen_paths:
            continue
        seen_paths.add(identity)
        if EDITOR_SPECS[editor]["format"] == "toml":
            updates.append(_prepare_merge_toml_servers(path, servers))
        else:
            updates.append(_prepare_merge_json_servers(path, editor, servers))
    return updates


def remove_servers(
    editors: list[str],
    server_names: list[str],
    *,
    scope: str,
    project_dir: Path | None = None,
    home: Path | None = None,
) -> list[Path]:
    """Remove servers from native editor config files."""
    updates = prepare_remove_servers(
        editors,
        server_names,
        scope=scope,
        project_dir=project_dir,
        home=home,
    )
    apply_config_updates(updates)
    return [update.path for update in updates]


def prepare_remove_servers(
    editors: list[str],
    server_names: list[str],
    *,
    scope: str,
    project_dir: Path | None = None,
    home: Path | None = None,
) -> list[ConfigUpdate]:
    """Preflight all native editor removals without mutating any destination."""
    updates: list[ConfigUpdate] = []
    seen_paths: set[Path] = set()
    for editor in editors:
        path = resolve_editor_path(
            editor,
            scope,
            project_dir=project_dir,
            home=home,
        )
        identity = path.absolute()
        if identity in seen_paths:
            continue
        seen_paths.add(identity)
        if EDITOR_SPECS[editor]["format"] == "toml":
            updates.append(_prepare_remove_toml_servers(path, server_names))
        else:
            updates.append(_prepare_remove_json_servers(path, server_names))
    return updates


def sync_project_mcp_to_editors(project_dir: Path, editors: list[str]) -> list[Path]:
    """Mirror `.mcp.json` into project-scoped editor configs.

    Claude project settings are always synced when `.mcp.json` exists.
    """
    config_path = project_dir / ".mcp.json"
    _assert_safe_config_path(config_path)
    if not config_path.exists():
        return []

    servers = load_project_mcp_servers(project_dir)
    selected = {"claude"}
    selected.update(e for e in editors if e in PROJECT_SCOPED_EDITORS)
    return install_servers(
        sorted(selected),
        servers,
        scope="project",
        project_dir=project_dir,
    )


def _load_json_file(path: Path) -> dict:
    _original, data = _load_json_document(path)
    return data


def _load_json_document(path: Path) -> tuple[bytes | None, dict]:
    original = _read_optional_file(path)
    if original is None:
        return None, {}
    try:
        text = original.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"{path} is not valid UTF-8 JSON: {error}") from error
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"{path} contains invalid JSON: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return original, data


def load_json_config(path: Path) -> dict:
    """Load a native JSON config after validating its destination path."""
    return _load_json_file(path)


def prepare_json_config(path: Path, data: dict) -> ConfigUpdate:
    """Build a validated JSON replacement without writing it."""
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    original, _existing = _load_json_document(path)
    content = (json.dumps(data, indent=2) + "\n").encode("utf-8")
    return ConfigUpdate(path=path, original=original, content=content)


def write_json_config(path: Path, data: dict) -> None:
    """Atomically write a native JSON MCP document without following symlinks."""
    apply_config_updates([prepare_json_config(path, data)])


def apply_config_updates(updates: list[ConfigUpdate]) -> None:
    """Apply preflighted file updates atomically, rolling back on any failure."""
    unique_updates = _coalesce_config_updates(updates)
    pending = [
        update
        for update in unique_updates
        if update.content is not None and update.content != update.original
    ]

    # Validate every snapshot before the first write. This catches symlinks,
    # concurrent changes, invalid destination types, and stale plans without
    # leaving a partially updated editor set.
    for update in pending:
        _verify_config_snapshot(update)

    attempted: list[ConfigUpdate] = []
    try:
        for update in pending:
            _verify_config_snapshot(update)
            attempted.append(update)
            _atomic_write_bytes(update.path, update.content)
    except Exception as error:
        rollback_errors: list[str] = []
        for update in reversed(attempted):
            try:
                _rollback_config_update(update)
            except Exception as rollback_error:  # pragma: no cover - catastrophic I/O
                rollback_errors.append(f"{update.path}: {rollback_error}")
        if rollback_errors:
            details = "; ".join(rollback_errors)
            raise RuntimeError(
                f"MCP config update failed ({error}); rollback also failed: {details}"
            ) from error
        raise


def _coalesce_config_updates(updates: list[ConfigUpdate]) -> list[ConfigUpdate]:
    unique: dict[Path, ConfigUpdate] = {}
    for update in updates:
        identity = update.path.absolute()
        previous = unique.get(identity)
        if previous is None:
            unique[identity] = update
            continue
        if previous.original != update.original or previous.content != update.content:
            raise ValueError(f"Conflicting MCP config updates for {update.path}")
    return list(unique.values())


def _verify_config_snapshot(update: ConfigUpdate) -> None:
    current = _read_optional_file(update.path)
    if current != update.original:
        raise RuntimeError(
            f"MCP config changed after preflight; refusing to overwrite: {update.path}"
        )


def _rollback_config_update(update: ConfigUpdate) -> None:
    current = _read_optional_file(update.path)
    if current == update.original:
        return
    if current != update.content:
        raise RuntimeError(
            f"MCP config changed during rollback; refusing to overwrite: {update.path}"
        )
    if update.original is None:
        _assert_safe_config_path(update.path)
        update.path.unlink()
        _fsync_directory(update.path.parent)
        return
    _atomic_write_bytes(update.path, update.original)


def _normalize_server(editor: str, server: dict) -> dict:
    if editor == "antigravity":
        return _normalize_antigravity_server(server)
    data = copy.deepcopy(server)
    if editor == "copilot":
        if "url" in data:
            data.setdefault("type", "http")
        elif "command" in data:
            data.setdefault("type", "local")
        data.setdefault("tools", ["*"])
    return data


def _normalize_antigravity_server(server: dict) -> dict:
    """Validate Antigravity's native MCP schema without rewriting transports."""
    if not isinstance(server, dict):
        raise ValueError("Antigravity MCP server configuration must be an object")

    data = copy.deepcopy(server)
    data.pop("_source", None)
    if "httpUrl" in data:
        raise ValueError("Antigravity MCP does not support the legacy 'httpUrl' field")

    transport_keys = [key for key in ("command", "serverUrl", "url") if key in data]
    if len(transport_keys) != 1:
        raise ValueError(
            "Antigravity MCP server requires exactly one of "
            "'command', 'serverUrl', or 'url'"
        )
    transport_key = transport_keys[0]
    _require_antigravity_string(data, transport_key)

    if transport_key == "command":
        _validate_antigravity_stdio(data)
    else:
        _validate_antigravity_remote(data)
    if "disabled" in data and not isinstance(data["disabled"], bool):
        raise ValueError("Antigravity MCP 'disabled' must be a boolean")
    _validate_antigravity_string_list(data, "disabledTools")
    return data


def _validate_antigravity_stdio(data: dict) -> None:
    incompatible = {"headers", "authProviderType", "oauth"} & set(data)
    if incompatible:
        fields = ", ".join(sorted(incompatible))
        raise ValueError(f"Incompatible Antigravity STDIO MCP field(s): {fields}")
    _validate_antigravity_string_list(data, "args")
    _validate_antigravity_string_map(data, "env")
    if "cwd" in data:
        _require_antigravity_string(data, "cwd")


def _validate_antigravity_remote(data: dict) -> None:
    incompatible = {"args", "env", "cwd"} & set(data)
    if incompatible:
        fields = ", ".join(sorted(incompatible))
        raise ValueError(f"Incompatible Antigravity remote MCP field(s): {fields}")
    _validate_antigravity_string_map(data, "headers")
    if "authProviderType" in data:
        _require_antigravity_string(data, "authProviderType")
    if "oauth" in data and not isinstance(data["oauth"], dict):
        raise ValueError("Antigravity MCP 'oauth' must be an object")


def _require_antigravity_string(data: dict, key: str) -> None:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Antigravity MCP '{key}' must be a non-empty string")


def _validate_antigravity_string_list(data: dict, key: str) -> None:
    if key not in data:
        return
    value = data[key]
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"Antigravity MCP '{key}' must be a list of non-empty strings")


def _validate_antigravity_string_map(data: dict, key: str) -> None:
    if key not in data:
        return
    value = data[key]
    if not isinstance(value, dict) or not all(
        isinstance(item_key, str) and item_key and isinstance(item_value, str)
        for item_key, item_value in value.items()
    ):
        raise ValueError(
            f"Antigravity MCP '{key}' must map non-empty strings to strings"
        )


def _prepare_merge_json_servers(
    path: Path,
    editor: str,
    servers: dict,
) -> ConfigUpdate:
    original, data = _load_json_document(path)
    bucket = data.setdefault("mcpServers", {})
    if not isinstance(bucket, dict):
        raise ValueError(f"{path} has invalid mcpServers data")
    for key, value in servers.items():
        bucket[key] = _normalize_server(editor, value)
    content = (json.dumps(data, indent=2) + "\n").encode("utf-8")
    return ConfigUpdate(path=path, original=original, content=content)


def _prepare_remove_json_servers(
    path: Path,
    server_names: list[str],
) -> ConfigUpdate:
    original, data = _load_json_document(path)
    if original is None:
        return ConfigUpdate(path=path, original=None, content=None)
    bucket = data.get("mcpServers", {})
    if not isinstance(bucket, dict):
        raise ValueError(f"{path} has invalid mcpServers data")
    changed = False
    for name in server_names:
        if name in bucket:
            del bucket[name]
            changed = True
    if not changed:
        return ConfigUpdate(path=path, original=original, content=original)
    data["mcpServers"] = bucket
    content = (json.dumps(data, indent=2) + "\n").encode("utf-8")
    return ConfigUpdate(path=path, original=original, content=content)


def _prepare_merge_toml_servers(path: Path, servers: dict) -> ConfigUpdate:
    original_bytes, original = _load_toml_document(path)
    base, managed = _split_codex_managed_block(original, path)
    normalized = {
        _validate_server_name(name): _normalize_toml_server(value)
        for name, value in servers.items()
    }
    base = _remove_selected_toml_server_tables(base, set(normalized), path)
    managed.update(normalized)
    rendered = _compose_codex_toml(base, managed)
    _parse_toml(rendered, path)
    return ConfigUpdate(
        path=path,
        original=original_bytes,
        content=rendered.encode("utf-8"),
    )


def _prepare_remove_toml_servers(
    path: Path,
    server_names: list[str],
) -> ConfigUpdate:
    original_bytes, original = _load_toml_document(path)
    if original_bytes is None:
        return ConfigUpdate(path=path, original=None, content=None)
    base, managed = _split_codex_managed_block(original, path)
    normalized_names = {_validate_server_name(name) for name in server_names}
    base = _remove_selected_toml_server_tables(base, normalized_names, path)
    for name in normalized_names:
        managed.pop(name, None)
    rendered = _compose_codex_toml(base, managed)
    _parse_toml(rendered, path)
    return ConfigUpdate(
        path=path,
        original=original_bytes,
        content=rendered.encode("utf-8"),
    )


def _normalize_toml_server(server: dict) -> dict:
    if not isinstance(server, dict):
        raise ValueError("Codex MCP server configuration must be an object")

    source = copy.deepcopy(server)
    source.pop("_source", None)
    _strip_compatible_codex_transport_type(source)
    if "tools" in source and not isinstance(source["tools"], dict):
        raise ValueError(
            "Codex MCP 'tools' must be a per-tool policy object, not a Copilot tool list"
        )

    data = {key: value for key, value in source.items() if value not in (None, {}, [])}
    has_command = "command" in data
    has_url = "url" in data
    if has_command == has_url:
        raise ValueError("Codex MCP server requires exactly one of 'command' or 'url'")

    transport_keys = (
        _CODEX_STDIO_SERVER_KEYS if has_command else _CODEX_HTTP_SERVER_KEYS
    )
    unknown = set(data) - transport_keys - _CODEX_SHARED_SERVER_KEYS
    if unknown:
        raise ValueError(
            "Unsupported Codex MCP field(s): " + ", ".join(sorted(unknown))
        )

    incompatible = set(data) & (
        _CODEX_HTTP_SERVER_KEYS if has_command else _CODEX_STDIO_SERVER_KEYS
    )
    if incompatible:
        transport = "STDIO" if has_command else "HTTP"
        raise ValueError(
            f"Incompatible {transport} Codex MCP field(s): "
            + ", ".join(sorted(incompatible))
        )

    if has_command:
        _require_nonempty_string(data, "command")
        _validate_optional_string_list(data, "args")
        _validate_optional_string_map(data, "env")
        _validate_env_vars(data)
        _validate_optional_string(data, "cwd")
        if "experimental_environment" in data:
            _require_choice(data, "experimental_environment", {"remote"})
    else:
        _require_nonempty_string(data, "url")
        _validate_optional_string(data, "bearer_token_env_var")
        _validate_optional_string_map(data, "http_headers")
        _validate_optional_string_map(data, "env_http_headers")
        if "auth" in data:
            _require_choice(data, "auth", {"oauth", "chatgpt"})

    for key in ("startup_timeout_sec", "tool_timeout_sec"):
        if key in data:
            value = data[key]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError(f"Codex MCP '{key}' must be a positive number")
    if "startup_timeout_ms" in data:
        value = data["startup_timeout_ms"]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(
                "Codex MCP 'startup_timeout_ms' must be a positive integer"
            )
    for key in ("enabled", "required"):
        if key in data and not isinstance(data[key], bool):
            raise ValueError(f"Codex MCP '{key}' must be a boolean")
    for key in ("enabled_tools", "disabled_tools"):
        _validate_optional_string_list(data, key)
    _validate_optional_string_list(data, "scopes")
    _validate_optional_string(data, "oauth_resource")
    if "default_tools_approval_mode" in data:
        _require_choice(data, "default_tools_approval_mode", _CODEX_APPROVAL_MODES)
    _validate_tool_policies(data)

    key_order = (
        "command",
        "args",
        "env_vars",
        "cwd",
        "experimental_environment",
        "url",
        "auth",
        "bearer_token_env_var",
        "startup_timeout_sec",
        "startup_timeout_ms",
        "tool_timeout_sec",
        "enabled",
        "required",
        "enabled_tools",
        "disabled_tools",
        "default_tools_approval_mode",
        "scopes",
        "oauth_resource",
        "env",
        "http_headers",
        "env_http_headers",
        "tools",
    )
    return {key: data[key] for key in key_order if key in data}


def _strip_compatible_codex_transport_type(source: dict) -> None:
    """Validate portable MCP transport metadata before rendering Codex TOML."""
    if "type" not in source:
        return

    transport_type = source.pop("type")
    if not isinstance(transport_type, str):
        raise ValueError("Codex MCP portable 'type' must be a string")
    expected_key = _CODEX_PORTABLE_TRANSPORT_KEYS.get(transport_type)
    if expected_key is None:
        raise ValueError(
            "Codex MCP supports portable types 'http', 'local', and 'stdio'; "
            f"got {transport_type!r}"
        )

    incompatible_key = "command" if expected_key == "url" else "url"
    if expected_key not in source or incompatible_key in source:
        raise ValueError(
            f"Codex MCP type '{transport_type}' requires '{expected_key}' "
            f"and excludes '{incompatible_key}'"
        )


def _validate_server_name(name: object) -> str:
    if not isinstance(name, str) or not name:
        raise ValueError("Codex MCP server names must be non-empty strings")
    if "\n" in name or "\r" in name:
        raise ValueError("Codex MCP server names cannot contain newlines")
    return name


def _require_nonempty_string(data: dict, key: str) -> None:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Codex MCP '{key}' must be a non-empty string")


def _validate_optional_string(data: dict, key: str) -> None:
    if key in data:
        _require_nonempty_string(data, key)


def _validate_optional_string_list(data: dict, key: str) -> None:
    if key not in data:
        return
    value = data[key]
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"Codex MCP '{key}' must be a list of non-empty strings")


def _validate_optional_string_map(data: dict, key: str) -> None:
    if key not in data:
        return
    value = data[key]
    if not isinstance(value, dict) or not all(
        isinstance(item_key, str) and item_key and isinstance(item_value, str)
        for item_key, item_value in value.items()
    ):
        raise ValueError(f"Codex MCP '{key}' must map non-empty strings to strings")


def _validate_env_vars(data: dict) -> None:
    if "env_vars" not in data:
        return
    value = data["env_vars"]
    if not isinstance(value, list):
        raise ValueError("Codex MCP 'env_vars' must be a list")
    for entry in value:
        if isinstance(entry, str) and entry:
            continue
        if not isinstance(entry, dict) or set(entry) - {"name", "source"}:
            raise ValueError(
                "Codex MCP env_vars entries must be strings or name/source objects"
            )
        if not isinstance(entry.get("name"), str) or not entry["name"]:
            raise ValueError("Codex MCP env_vars object requires a non-empty name")
        if entry.get("source", "local") not in {"local", "remote"}:
            raise ValueError("Codex MCP env_vars source must be 'local' or 'remote'")


def _require_choice(data: dict, key: str, choices: set[str] | frozenset[str]) -> None:
    if data[key] not in choices:
        allowed = ", ".join(sorted(choices))
        raise ValueError(f"Codex MCP '{key}' must be one of: {allowed}")


def _validate_tool_policies(data: dict) -> None:
    if "tools" not in data:
        return
    tools = data["tools"]
    if not isinstance(tools, dict):
        raise ValueError("Codex MCP 'tools' must be an object")
    for name, policy in tools.items():
        if not isinstance(name, str) or not name or not isinstance(policy, dict):
            raise ValueError("Codex MCP tools must map names to policy objects")
        if set(policy) != {"approval_mode"}:
            raise ValueError(
                f"Codex MCP tool '{name}' supports only the approval_mode field"
            )
        _require_choice(policy, "approval_mode", _CODEX_APPROVAL_MODES)


def _format_toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_format_toml_value(v) for v in value) + "]"
    if isinstance(value, dict):
        values = ", ".join(
            f"{_format_toml_key(str(key))} = {_format_toml_value(item)}"
            for key, item in value.items()
        )
        return "{ " + values + " }"
    raise TypeError(f"Unsupported TOML value: {value!r}")


def _format_toml_key(key: str) -> str:
    if _TOML_BARE_KEY_RE.fullmatch(key):
        return key
    return json.dumps(key)


def _render_toml_table(prefix: str, data: dict, lines: list[str]) -> None:
    scalars = [(k, v) for k, v in data.items() if not isinstance(v, dict)]
    tables = [(k, v) for k, v in data.items() if isinstance(v, dict) and v]

    if prefix:
        lines.append(f"[{prefix}]")
    for key, value in scalars:
        lines.append(f"{_format_toml_key(key)} = {_format_toml_value(value)}")

    for key, value in tables:
        if lines and lines[-1] != "":
            lines.append("")
        child_key = _format_toml_key(key)
        child_prefix = f"{prefix}.{child_key}" if prefix else child_key
        _render_toml_table(child_prefix, value, lines)


def _render_managed_codex_block(servers: dict[str, dict]) -> str:
    lines: list[str] = []
    lines.append(CODEX_MCP_BLOCK_START)
    for name in sorted(servers):
        if len(lines) > 1 and lines[-1] != "":
            lines.append("")
        prefix = f"mcp_servers.{_format_toml_key(name)}"
        _render_toml_table(prefix, servers[name], lines)
    lines.append(CODEX_MCP_BLOCK_END)
    return "\n".join(lines) + "\n"


def _compose_codex_toml(base: str, managed: dict[str, dict]) -> str:
    if not managed:
        return base
    if not base:
        return _render_managed_codex_block(managed)
    prefix = base
    if not prefix.endswith("\n"):
        prefix += "\n"
    if not prefix.endswith("\n\n"):
        prefix += "\n"
    return prefix + _render_managed_codex_block(managed)


def _split_codex_managed_block(text: str, path: Path) -> tuple[str, dict[str, dict]]:
    lines = text.splitlines(keepends=True)
    starts = [
        i for i, line in enumerate(lines) if line.strip() == CODEX_MCP_BLOCK_START
    ]
    ends = [i for i, line in enumerate(lines) if line.strip() == CODEX_MCP_BLOCK_END]
    if not starts and not ends:
        return text, {}
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise ValueError(f"{path} has malformed ai-toolkit Codex MCP markers")

    start, end = starts[0], ends[0]
    block_text = "".join(lines[start + 1 : end])
    block_data = _parse_toml(block_text, path) if block_text.strip() else {}
    if set(block_data) - {"mcp_servers"}:
        raise ValueError(f"{path} has unexpected data inside the managed MCP block")
    bucket = block_data.get("mcp_servers", {})
    if not isinstance(bucket, dict):
        raise ValueError(f"{path} has invalid managed mcp_servers data")
    managed = {
        _validate_server_name(name): _normalize_toml_server(server)
        for name, server in bucket.items()
    }
    base = "".join(lines[:start] + lines[end + 1 :])
    _parse_toml(base, path)
    return base, managed


def _remove_selected_toml_server_tables(
    text: str,
    server_names: set[str],
    path: Path,
) -> str:
    if not server_names:
        return text
    lines = text.splitlines(keepends=True)
    headers = _toml_table_headers(lines)
    remove_lines: set[int] = set()
    for position, (line_index, table_path) in enumerate(headers):
        next_index = (
            headers[position + 1][0] if position + 1 < len(headers) else len(lines)
        )
        if (
            len(table_path) >= 2
            and table_path[0] == "mcp_servers"
            and table_path[1] in server_names
        ):
            remove_lines.update(range(line_index, next_index))

    rendered = "".join(
        line for index, line in enumerate(lines) if index not in remove_lines
    )
    data = _parse_toml(rendered, path)
    bucket = data.get("mcp_servers", {})
    if not isinstance(bucket, dict):
        raise ValueError(f"{path} has invalid mcp_servers data")
    remaining = server_names & set(bucket)
    if remaining:
        names = ", ".join(sorted(remaining))
        raise ValueError(
            f"Cannot safely replace inline/dotted Codex MCP server definition(s): {names}"
        )
    return rendered


def _toml_table_headers(lines: list[str]) -> list[tuple[int, tuple[str, ...]]]:
    headers: list[tuple[int, tuple[str, ...]]] = []
    multiline: str | None = None
    for index, line in enumerate(lines):
        if multiline is None:
            table_path = _toml_table_header_path(line)
            if table_path is not None:
                headers.append((index, table_path))
        multiline = _toml_multiline_state(line, multiline)
    return headers


def _toml_table_header_path(line: str) -> tuple[str, ...] | None:
    stripped = line.strip()
    if not stripped.startswith("[") or stripped.startswith("[["):
        return None
    if tomllib is None:  # pragma: no cover
        raise RuntimeError("tomllib is unavailable")
    probe = "__ai_toolkit_table_probe__"
    try:
        parsed = tomllib.loads(f"{stripped}\n{probe} = true\n")
    except tomllib.TOMLDecodeError:
        return None
    found = _find_toml_probe_path(parsed, probe, ())
    return found


def _find_toml_probe_path(
    data: dict, probe: str, path: tuple[str, ...]
) -> tuple[str, ...] | None:
    if data.get(probe) is True:
        return path
    for key, value in data.items():
        if isinstance(value, dict):
            found = _find_toml_probe_path(value, probe, path + (key,))
            if found is not None:
                return found
    return None


def _toml_multiline_state(line: str, state: str | None) -> str | None:
    index = 0
    while index < len(line):
        if state == "basic":
            if line.startswith('"""', index) and not _is_escaped(line, index):
                state = None
                index += 3
            else:
                index += 1
            continue
        if state == "literal":
            if line.startswith("'''", index):
                state = None
                index += 3
            else:
                index += 1
            continue

        if line[index] == "#":
            break
        if line.startswith('"""', index):
            state = "basic"
            index += 3
            continue
        if line.startswith("'''", index):
            state = "literal"
            index += 3
            continue
        if line[index] == '"':
            index = _skip_single_line_basic_string(line, index + 1)
            continue
        if line[index] == "'":
            closing = line.find("'", index + 1)
            index = len(line) if closing < 0 else closing + 1
            continue
        index += 1
    return state


def _skip_single_line_basic_string(line: str, index: int) -> int:
    while index < len(line):
        if line[index] == '"' and not _is_escaped(line, index):
            return index + 1
        index += 1
    return index


def _is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    index -= 1
    while index >= 0 and text[index] == "\\":
        backslashes += 1
        index -= 1
    return backslashes % 2 == 1


def _load_toml_document(path: Path) -> tuple[bytes | None, str]:
    original = _read_optional_file(path)
    if original is None:
        return None, ""
    try:
        text = original.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"{path} is not valid UTF-8 TOML: {error}") from error
    _parse_toml(text, path)
    return original, text


def _read_optional_file(path: Path) -> bytes | None:
    _assert_safe_config_path(path)
    if not path.exists():
        return None
    if not path.is_file():
        raise RuntimeError(f"MCP config destination is not a file: {path}")
    return path.read_bytes()


def _parse_toml(text: str, path: Path) -> dict:
    if not text.strip():
        return {}
    if tomllib is None:  # pragma: no cover
        raise RuntimeError("tomllib is unavailable")
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"{path} contains invalid TOML: {error}") from error
    if not isinstance(data, dict):  # pragma: no cover - tomllib always returns dict
        raise ValueError(f"{path} must contain a TOML document")
    return data


def _assert_safe_config_path(path: Path) -> None:
    # The config itself, its editor directory, and the caller-provided project
    # or HOME root must not redirect writes through symlinks. Checking the
    # grandparent is necessary for layouts such as `.codex/config.toml`.
    for candidate in (path, path.parent, path.parent.parent):
        if candidate.is_symlink():
            raise RuntimeError(f"Refusing symlinked MCP config path: {candidate}")


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    _assert_safe_config_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_config_path(path)
    mode = path.stat().st_mode & 0o777 if path.exists() and path.is_file() else None
    fd, temp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temp_path = Path(temp_name)
    try:
        if mode is not None:
            os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as handle:
            fd = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        _assert_safe_config_path(path)
        os.replace(temp_path, path)
        _fsync_directory(path.parent)
    except Exception:
        if fd >= 0:
            os.close(fd)
        temp_path.unlink(missing_ok=True)
        raise


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(path, flags)
    except OSError as error:
        if error.errno in _UNSUPPORTED_DIRECTORY_FSYNC_ERRNOS:
            return
        raise
    try:
        try:
            os.fsync(fd)
        except OSError as error:
            if error.errno not in _UNSUPPORTED_DIRECTORY_FSYNC_ERRNOS:
                raise
    finally:
        os.close(fd)
