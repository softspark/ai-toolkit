#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Decide which registered rules a client-specific instruction file receives.

A registered rule (``~/.softspark/ai-toolkit/rules/<name>.md``) that tells the
agent to call an MCP server is useless, and actively misleading, in a client
where that server is not configured. When the installer knows which clients
read a file, a rule is emitted only when:

* every MCP server it requires is configured for at least one of those
  clients (project or global scope), matched by server name or by the
  basename of the server's ``command``; and
* it is not opt-in, or it was explicitly opted in (``--opt-in-rules``).

Requirements come from ``requires_mcp`` in ``sources.json`` (set with
``add-rule --requires-mcp``). Without it, a rule named ``<server>-rules`` or
``<server>`` whose name contains an ``mcp`` segment requires ``<server>``.
``rag-mcp-legal-rules`` is opt-in by default, others only with ``opt_in``.

When no clients are known (a bare generator run), every rule is emitted, as
before.

Stdlib only.
"""
from __future__ import annotations

import json
import os
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

# Antigravity truncates any rule file (AGENTS.md, GEMINI.md, .agents/rules/*.md)
# above this size, on line boundaries (antigravity.google/docs/rules/).
ANTIGRAVITY_RULE_LIMIT_BYTES = 24_000

DEFAULT_OPT_IN_RULES = frozenset({"rag-mcp-legal-rules"})

RULE_CLIENTS_ENV = "AI_TOOLKIT_RULE_CLIENTS"
RULE_PROJECT_ENV = "AI_TOOLKIT_RULE_PROJECT_DIR"
OPT_IN_RULES_ENV = "AI_TOOLKIT_OPT_IN_RULES"

# (project path, global path, key holding the server map, format)
_CLIENT_MCP_CONFIGS: dict[str, tuple[str | None, str | None, str, str]] = {
    "antigravity": (".agents/mcp_config.json", ".gemini/config/mcp_config.json", "mcpServers", "json"),
    "gemini": (".gemini/settings.json", ".gemini/settings.json", "mcpServers", "json"),
    "copilot": (".github/mcp.json", ".copilot/mcp-config.json", "mcpServers", "json"),
    "codex": (".codex/config.toml", ".codex/config.toml", "mcp_servers", "toml"),
    "opencode": ("opencode.json", ".config/opencode/opencode.json", "mcp", "json"),
}


def required_mcp_servers(rule_name: str, metadata: dict[str, Any] | None = None) -> tuple[str, ...]:
    """Return the MCP servers a registered rule depends on."""
    declared = (metadata or {}).get("requires_mcp")
    if isinstance(declared, list):
        return tuple(str(name) for name in declared if str(name))
    base = rule_name.removesuffix("-rules")
    return (base,) if "mcp" in base.split("-") else ()


def is_opt_in(rule_name: str, metadata: dict[str, Any] | None = None) -> bool:
    """Return True when a rule must be explicitly opted in."""
    declared = (metadata or {}).get("opt_in")
    if isinstance(declared, bool):
        return declared
    return rule_name in DEFAULT_OPT_IN_RULES


def _server_names(servers: object) -> set[str]:
    if not isinstance(servers, dict):
        return set()
    names: set[str] = set()
    for name, spec in servers.items():
        names.add(str(name))
        command = spec.get("command") if isinstance(spec, dict) else None
        if isinstance(command, list) and command:
            command = command[0]
        if isinstance(command, str) and command:
            names.add(Path(command).name)
    return names


def _read_servers(path: Path, key: str, fmt: str) -> set[str]:
    if not path.is_file():
        return set()
    try:
        if fmt == "toml":
            data: object = tomllib.loads(path.read_text(encoding="utf-8"))
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return _server_names(data.get(key) if isinstance(data, dict) else None)


def configured_mcp_servers(
    clients: Iterable[str],
    *,
    project_dir: Path | None = None,
    home: Path | None = None,
) -> set[str]:
    """Return server names (and command basenames) configured for ``clients``."""
    home = home or Path.home()
    found: set[str] = set()
    for client in clients:
        spec = _CLIENT_MCP_CONFIGS.get(client)
        if spec is None:
            continue
        project_rel, global_rel, key, fmt = spec
        if project_dir is not None and project_rel:
            found |= _read_servers(project_dir / project_rel, key, fmt)
        if global_rel:
            found |= _read_servers(home / global_rel, key, fmt)
    return found


def _load_metadata(rules_dir: Path) -> dict[str, dict[str, Any]]:
    from rule_sources import load_sources

    return load_sources(rules_dir)


def select_rule_files(
    rules_dir: Path | None,
    *,
    clients: Iterable[str] | None,
    project_dir: Path | None = None,
    home: Path | None = None,
    opted_in: Iterable[str] = (),
) -> list[Path]:
    """Return the registered rule files a file read by ``clients`` receives."""
    if not rules_dir or not rules_dir.is_dir():
        return []
    files = sorted(rules_dir.glob("*.md"))
    client_list = list(clients or [])
    if not client_list:
        return files
    metadata = _load_metadata(rules_dir)
    servers = configured_mcp_servers(client_list, project_dir=project_dir, home=home)
    allowed_opt_in = set(opted_in)
    selected: list[Path] = []
    for path in files:
        meta = metadata.get(path.stem)
        if is_opt_in(path.stem, meta) and path.stem not in allowed_opt_in:
            continue
        if all(server in servers for server in required_mcp_servers(path.stem, meta)):
            selected.append(path)
    return selected


def fallback_note(rule_name: str, metadata: dict[str, Any] | None = None) -> str:
    """Return the explicit unavailable-server fallback for an MCP rule."""
    servers = required_mcp_servers(rule_name, metadata)
    if not servers:
        return ""
    names = ", ".join(f"`{server}`" for server in servers)
    return (
        f"> If the {names} MCP server is not available in this session, say so "
        "plainly before answering. For a knowledge base, read the project's "
        "`kb/` files directly instead; never present an answer as if the "
        "server had been queried.\n"
    )


def rule_text(path: Path, metadata: dict[str, Any] | None = None) -> str:
    """Return a registered rule's content followed by its fallback note."""
    content = path.read_text(encoding="utf-8").rstrip("\n") + "\n"
    note = fallback_note(path.stem, metadata)
    return f"{content}\n{note}" if note else content


def selection_env(
    clients: Iterable[str] | None,
    project_dir: Path | None,
    opted_in: Iterable[str],
) -> dict[str, str]:
    """Environment that makes a generator subprocess apply the same selection."""
    env = {RULE_CLIENTS_ENV: ",".join(clients or [])}
    if project_dir is not None:
        env[RULE_PROJECT_ENV] = str(project_dir)
    env[OPT_IN_RULES_ENV] = ",".join(opted_in)
    return env


def print_rule_blocks(rules_dir: Path) -> None:
    """Print each selected registered rule as a ``TOOLKIT:<name>`` block.

    Skipped when AI_TOOLKIT_NO_CUSTOM_RULES=1 so a maintainer's personal
    registered rules never leak into the toolkit's own canonical files. An
    installer that knows the file's reader clients passes them through the
    environment (``selection_env``) so MCP-dependent rules follow those
    clients' MCP configuration.
    """
    if not rules_dir.is_dir() or os.environ.get("AI_TOOLKIT_NO_CUSTOM_RULES") == "1":
        return
    clients = [c for c in os.environ.get(RULE_CLIENTS_ENV, "").split(",") if c]
    project = os.environ.get(RULE_PROJECT_ENV)
    opted_in = [r for r in os.environ.get(OPT_IN_RULES_ENV, "").split(",") if r]
    files = select_rule_files(
        rules_dir,
        clients=clients,
        project_dir=Path(project) if project else None,
        opted_in=opted_in,
    )
    metadata = _load_metadata(rules_dir)
    for rule_file in files:
        rule_name = rule_file.stem
        print()
        print(f"<!-- TOOLKIT:{rule_name} START -->")
        print("<!-- Auto-injected by ai-toolkit. Re-run to update. -->")
        print()
        print(rule_text(rule_file, metadata.get(rule_name)).rstrip())
        print()
        print(f"<!-- TOOLKIT:{rule_name} END -->")
