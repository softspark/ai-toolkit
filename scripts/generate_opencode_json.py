#!/usr/bin/env python3
"""Merge MCP servers from .mcp.json into opencode.json for opencode.

opencode MCP config: https://opencode.ai/docs/mcp-servers/

Schema per server:
  Local:  {"type": "local",  "command": [...], "enabled": true, "environment": {...}}
  Remote: {"type": "remote", "url": "...",      "enabled": true, "headers": {...}}

Our canonical source is .mcp.json (Claude-style) with:
  {"mcpServers": {"name": {"command": "...", "args": [...], "env": {...}}}}
  or: {"name": {"url": "..."}} for remote.

We translate into opencode's shape and merge under the ``mcp`` key.
All non-``mcp`` keys are preserved verbatim — idempotent on re-run.

Usage:
  python3 scripts/generate_opencode_json.py [target-dir]
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

SCHEMA_URL = "https://opencode.ai/config.json"


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _translate_server(name: str, server: dict) -> dict:
    """Translate a Claude-style server entry into opencode's shape."""
    out: dict = {}
    if "url" in server:
        out["type"] = "remote"
        out["url"] = server["url"]
        if "headers" in server and isinstance(server["headers"], dict):
            out["headers"] = copy.deepcopy(server["headers"])
    elif "command" in server:
        out["type"] = "local"
        cmd = server["command"]
        args = server.get("args") or []
        if isinstance(cmd, list):
            out["command"] = list(cmd) + list(args)
        else:
            out["command"] = [cmd, *args]
        env = server.get("env") or server.get("environment")
        if isinstance(env, dict) and env:
            out["environment"] = copy.deepcopy(env)
    else:
        # Unknown shape — preserve as-is so opencode can report the error
        out = copy.deepcopy(server)
        out.setdefault("type", "local")

    out.setdefault("enabled", True)
    if "timeout" in server:
        out["timeout"] = server["timeout"]
    return out


def _read_mcp_servers(project_dir: Path) -> dict:
    """Read canonical .mcp.json and return the servers map.

    Returns {} when no .mcp.json exists (non-fatal).
    """
    config = project_dir / ".mcp.json"
    if not config.is_file():
        return {}
    data = _load_json(config)
    servers = data.get("mcpServers", {})
    if not isinstance(servers, dict):
        return {}
    return servers


def merge_into_opencode_json(
    target_dir: Path, output_path: Path | None = None
) -> tuple[Path, int]:
    """Merge .mcp.json servers into an opencode.json file.

    Reads ``target_dir/.mcp.json`` as the canonical source. By default
    writes to ``target_dir/opencode.json`` (project-local). Pass
    ``output_path=~/.config/opencode/opencode.json`` for the global layout.

    Returns (path, server_count). If no .mcp.json exists, still ensures
    the output has the $schema key set (creates a minimal file).
    """
    servers = _read_mcp_servers(target_dir)
    path = output_path if output_path is not None else target_dir / "opencode.json"
    data = _load_json(path)
    data.setdefault("$schema", SCHEMA_URL)

    if servers:
        bucket = data.setdefault("mcp", {})
        if not isinstance(bucket, dict):
            raise ValueError(f"{path} has invalid 'mcp' data (expected object)")
        for name, entry in servers.items():
            if not isinstance(entry, dict):
                continue
            bucket[name] = _translate_server(name, entry)

    _write_json(path, data)
    return path, len(servers)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    path, count = merge_into_opencode_json(target)
    rel = path.relative_to(target) if path.is_relative_to(target) else path
    if count:
        print(f"Generated: {rel} ({count} MCP server(s) merged)")
    else:
        print(f"Generated: {rel} (no MCP servers; .mcp.json not found)")


if __name__ == "__main__":
    main()
