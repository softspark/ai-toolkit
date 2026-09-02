#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Plugin-owned MCP template installation and conservative removal."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.11+ is required
    tomllib = None  # type: ignore[assignment]

from mcp_editors import (
    ConfigUpdate,
    apply_config_updates,
    prepare_install_servers,
    prepare_remove_servers,
)


TOOLKIT_DIR = Path(__file__).resolve().parent.parent
BUILTIN_TEMPLATES_DIR = TOOLKIT_DIR / "app" / "mcp-templates"
MCP_REFERENCE_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
LOCAL_ENDPOINT_MARKERS = ("localhost", "127.0.0.1", "[::1]")


@dataclass(frozen=True, slots=True)
class PluginMcpInstallPlan:
    """Preflighted native config update plus ownership metadata."""

    updates: tuple[ConfigUpdate, ...]
    ownership: dict
    hints: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PluginMcpRemovalPlan:
    """Preflighted removal that preserves changed or foreign entries."""

    updates: tuple[ConfigUpdate, ...]
    removed: tuple[str, ...]
    preserved: tuple[str, ...]


def plugin_mcp_source(plugin_name: str) -> str:
    """Return the stable ownership identifier for one plugin pack."""
    if MCP_REFERENCE_PATTERN.fullmatch(plugin_name) is None:
        raise ValueError(f"Unsafe plugin name: {plugin_name!r}")
    return f"ai-toolkit-plugin-{plugin_name}"


def prepare_plugin_mcp_install(
    plugin_name: str,
    editor: str,
    pack: dict,
    pack_dir: Path,
    previous_ownership: dict | None,
) -> PluginMcpInstallPlan | None:
    """Resolve, validate, and preflight a plugin's global MCP installation."""
    references = pack.get("includes", {}).get("mcp", [])
    if not references:
        return None
    if not isinstance(references, list):
        raise ValueError("includes.mcp must be a list")

    servers: dict = {}
    hints: list[str] = []
    for reference in references:
        template = _load_template(reference, pack_dir)
        for server_name, server in template["mcpServers"].items():
            if server_name in servers:
                raise ValueError(
                    f"Duplicate MCP server '{server_name}' in plugin '{plugin_name}'"
                )
            servers[server_name] = server
        hint = template.get("postInstall")
        if isinstance(hint, str) and hint not in hints:
            hints.append(hint)

    updates = tuple(prepare_install_servers([editor], servers, scope="global"))
    existing = _servers_from_updates(editor, updates, use_original=True)
    source = plugin_mcp_source(plugin_name)
    owned_servers = _owned_servers(previous_ownership, source)
    for server_name in servers:
        current = existing.get(server_name)
        if current is None:
            continue
        if owned_servers.get(server_name) == current:
            continue
        raise RuntimeError(
            f"Refusing user-owned MCP server collision for '{server_name}' "
            f"in {editor}; remove or rename it explicitly"
        )

    rendered = _servers_from_updates(editor, updates, use_original=False)
    ownership = {
        "source": source,
        "servers": {name: rendered[name] for name in sorted(servers)},
    }
    return PluginMcpInstallPlan(
        updates=updates,
        ownership=ownership,
        hints=tuple(hints),
    )


def apply_plugin_mcp_install(plan: PluginMcpInstallPlan | None) -> None:
    """Commit a previously preflighted MCP install and print its operator hints."""
    if plan is None:
        return
    apply_config_updates(list(plan.updates))
    for server_name in plan.ownership["servers"]:
        print(f"    Installed MCP server: {server_name}")
    for hint in plan.hints:
        print(f"    MCP note: {hint}")


def prepare_plugin_mcp_removal(
    plugin_name: str,
    editor: str,
    ownership: dict | None,
) -> PluginMcpRemovalPlan | None:
    """Preflight removal of only unchanged entries recorded as plugin-owned."""
    source = plugin_mcp_source(plugin_name)
    owned_servers = _owned_servers(ownership, source)
    if not owned_servers:
        return None

    inspection = tuple(prepare_remove_servers([editor], [], scope="global"))
    existing = _servers_from_updates(editor, inspection, use_original=True)
    removable: list[str] = []
    preserved: list[str] = []
    for server_name, expected in owned_servers.items():
        current = existing.get(server_name)
        if current is None:
            continue
        if current == expected:
            removable.append(server_name)
        else:
            preserved.append(server_name)

    updates = (
        tuple(prepare_remove_servers([editor], removable, scope="global"))
        if removable
        else ()
    )
    return PluginMcpRemovalPlan(
        updates=updates,
        removed=tuple(sorted(removable)),
        preserved=tuple(sorted(preserved)),
    )


def apply_plugin_mcp_removal(plan: PluginMcpRemovalPlan | None) -> None:
    """Commit an ownership-checked MCP removal."""
    if plan is None:
        return
    apply_config_updates(list(plan.updates))
    for server_name in plan.removed:
        print(f"    Removed MCP server: {server_name}")
    for server_name in plan.preserved:
        print(f"    WARN preserved changed or user-owned MCP server: {server_name}")


def _load_template(reference: object, pack_dir: Path) -> dict:
    if (
        not isinstance(reference, str)
        or MCP_REFERENCE_PATTERN.fullmatch(reference) is None
    ):
        raise ValueError(f"Invalid includes.mcp reference: {reference!r}")
    candidates = (
        pack_dir / "mcp" / f"{reference}.json",
        BUILTIN_TEMPLATES_DIR / f"{reference}.json",
    )
    template_path = next((path for path in candidates if path.is_file()), None)
    if template_path is None:
        raise FileNotFoundError(
            f"MCP template '{reference}' not found in {pack_dir / 'mcp'} "
            "or built-in templates"
        )
    if template_path.is_symlink():
        raise RuntimeError(f"Refusing symlinked MCP template: {template_path}")

    try:
        template = json.loads(template_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid MCP template JSON at {template_path}: {error}"
        ) from error
    _validate_template(reference, template, template_path)
    return template


def _validate_template(reference: str, template: object, template_path: Path) -> None:
    if not isinstance(template, dict):
        raise ValueError(f"MCP template must be an object: {template_path}")
    if template.get("name") != reference:
        raise ValueError(
            f"MCP template name must equal includes.mcp reference '{reference}': "
            f"{template_path}"
        )
    servers = template.get("mcpServers")
    if not isinstance(servers, dict) or not servers:
        raise ValueError(f"MCP template requires non-empty mcpServers: {template_path}")
    if not all(_is_valid_server(name, server) for name, server in servers.items()):
        raise ValueError(f"MCP template has invalid server entries: {template_path}")

    local_remote = any(
        isinstance(server.get("url"), str)
        and any(marker in server["url"].lower() for marker in LOCAL_ENDPOINT_MARKERS)
        for server in servers.values()
    )
    warning = template.get("postInstall", "")
    if local_remote and (
        not isinstance(warning, str) or "unauthenticated" not in warning.lower()
    ):
        raise ValueError(
            "Local HTTP MCP template must warn that access is unauthenticated: "
            f"{template_path}"
        )


def _is_valid_server(name: object, server: object) -> bool:
    if (
        not isinstance(name, str)
        or MCP_REFERENCE_PATTERN.fullmatch(name) is None
        or not isinstance(server, dict)
    ):
        return False
    transports = [key for key in ("command", "url") if key in server]
    return (
        len(transports) == 1
        and isinstance(server[transports[0]], str)
        and bool(server[transports[0]].strip())
    )


def _owned_servers(ownership: object, source: str) -> dict:
    if not isinstance(ownership, dict) or ownership.get("source") != source:
        return {}
    servers = ownership.get("servers")
    if not isinstance(servers, dict):
        return {}
    return {
        name: config
        for name, config in servers.items()
        if isinstance(name, str) and isinstance(config, dict)
    }


def _servers_from_updates(
    editor: str,
    updates: tuple[ConfigUpdate, ...],
    *,
    use_original: bool,
) -> dict:
    if not updates:
        return {}
    payload = updates[0].original if use_original else updates[0].content
    if payload is None:
        return {}
    if editor == "codex":
        if tomllib is None:  # pragma: no cover
            raise RuntimeError("tomllib is unavailable")
        document = tomllib.loads(payload.decode("utf-8"))
        servers = document.get("mcp_servers", {})
    else:
        document = json.loads(payload.decode("utf-8"))
        servers = document.get("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError("Native MCP config has invalid server data")
    return servers
