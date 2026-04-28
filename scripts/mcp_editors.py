#!/usr/bin/env python3
"""Editor-specific MCP config adapters for ai-toolkit."""
from __future__ import annotations

import copy
import json
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
        "project_path": None,
        "global_path": ".codex/config.toml",
        "format": "toml",
        "doc_scope": "global",
    },
}


PROJECT_SCOPED_EDITORS = {
    name for name, spec in EDITOR_SPECS.items() if spec.get("project_path")
}


def supported_editors() -> list[str]:
    """Return all editor ids with native MCP adapters."""
    return sorted(EDITOR_SPECS)


def editor_rows() -> list[dict[str, str]]:
    """Return display metadata for `ai-toolkit mcp editors`."""
    rows: list[dict[str, str]] = []
    for name in supported_editors():
        spec = EDITOR_SPECS[name]
        rows.append({
            "name": name,
            "label": str(spec["label"]),
            "scope": str(spec["doc_scope"]),
            "project_path": str(spec.get("project_path") or "—"),
            "global_path": str(spec.get("global_path") or "—"),
            "format": str(spec["format"]),
        })
    return rows


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
            raise ValueError(f"Editor '{editor}' does not support project-scoped MCP config")
        base = project_dir or Path.cwd()
        return base / str(rel)
    if scope == "global":
        rel = spec.get("global_path")
        if not rel:
            raise ValueError(f"Editor '{editor}' does not support global MCP config")
        return (home or Path.home()) / str(rel)
    raise ValueError(f"Unsupported scope: {scope}")


def load_project_mcp_servers(project_dir: Path) -> dict:
    """Load `.mcp.json` servers from a project directory."""
    config_path = project_dir / ".mcp.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"{config_path} not found")
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
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
    updated: list[Path] = []
    for editor in editors:
        path = resolve_editor_path(
            editor,
            scope,
            project_dir=project_dir,
            home=home,
        )
        if EDITOR_SPECS[editor]["format"] == "toml":
            _merge_toml_servers(path, servers)
        else:
            _merge_json_servers(path, editor, servers)
        updated.append(path)
    return updated


def remove_servers(
    editors: list[str],
    server_names: list[str],
    *,
    scope: str,
    project_dir: Path | None = None,
    home: Path | None = None,
) -> list[Path]:
    """Remove servers from native editor config files."""
    updated: list[Path] = []
    for editor in editors:
        path = resolve_editor_path(
            editor,
            scope,
            project_dir=project_dir,
            home=home,
        )
        if EDITOR_SPECS[editor]["format"] == "toml":
            _remove_toml_servers(path, server_names)
        else:
            _remove_json_servers(path, server_names)
        updated.append(path)
    return updated


def sync_project_mcp_to_editors(project_dir: Path, editors: list[str]) -> list[Path]:
    """Mirror `.mcp.json` into project-scoped editor configs.

    Claude project settings are always synced when `.mcp.json` exists.
    """
    config_path = project_dir / ".mcp.json"
    if not config_path.is_file():
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
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _write_json_file(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _normalize_server(editor: str, server: dict) -> dict:
    data = copy.deepcopy(server)
    if editor == "copilot":
        if "url" in data:
            data.setdefault("type", "http")
        elif "command" in data:
            data.setdefault("type", "local")
        data.setdefault("tools", ["*"])
    return data


def _merge_json_servers(path: Path, editor: str, servers: dict) -> None:
    data = _load_json_file(path)
    bucket = data.setdefault("mcpServers", {})
    if not isinstance(bucket, dict):
        raise ValueError(f"{path} has invalid mcpServers data")
    for key, value in servers.items():
        bucket[key] = _normalize_server(editor, value)
    _write_json_file(path, data)


def _remove_json_servers(path: Path, server_names: list[str]) -> None:
    if not path.is_file():
        return
    data = _load_json_file(path)
    bucket = data.get("mcpServers", {})
    if not isinstance(bucket, dict):
        raise ValueError(f"{path} has invalid mcpServers data")
    for name in server_names:
        bucket.pop(name, None)
    data["mcpServers"] = bucket
    _write_json_file(path, data)


def _load_toml_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    if tomllib is None:  # pragma: no cover
        raise RuntimeError("tomllib is unavailable")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _merge_toml_servers(path: Path, servers: dict) -> None:
    data = _load_toml_file(path)
    bucket = data.setdefault("mcp_servers", {})
    if not isinstance(bucket, dict):
        raise ValueError(f"{path} has invalid mcp_servers data")
    for key, value in servers.items():
        bucket[key] = _normalize_toml_server(value)
    _write_toml_file(path, data)


def _remove_toml_servers(path: Path, server_names: list[str]) -> None:
    if not path.is_file():
        return
    data = _load_toml_file(path)
    bucket = data.get("mcp_servers", {})
    if not isinstance(bucket, dict):
        raise ValueError(f"{path} has invalid mcp_servers data")
    for name in server_names:
        bucket.pop(name, None)
    data["mcp_servers"] = bucket
    _write_toml_file(path, data)


def _normalize_toml_server(server: dict) -> dict:
    data: dict = {}
    for key, value in copy.deepcopy(server).items():
        if value in (None, {}, []):
            continue
        data[key] = value
    return data


def _format_toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_format_toml_value(v) for v in value) + "]"
    raise TypeError(f"Unsupported TOML value: {value!r}")


def _format_toml_key(key: str) -> str:
    if key.replace("-", "").replace("_", "").isalnum():
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


def _write_toml_file(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    _render_toml_table("", data, lines)
    text = "\n".join(lines).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")
