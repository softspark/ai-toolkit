#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate native Antigravity subagents under ``.agents/agents``."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from emission import agents_dir
from frontmatter import frontmatter_field
from secure_fs import (
    SecureDestination,
    SecureTransaction,
    lexical_absolute,
    nearest_existing_root,
    run_secure_transaction,
)


AGENT_PREFIX = "ai-toolkit-"
MANAGED_MARKER = "<!-- ai-toolkit-managed: antigravity-agent -->"
SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
TOOL_MAPPING: dict[str, tuple[str, ...]] = {
    "Read": ("view_file",),
    "Write": ("write_to_file",),
    "Edit": ("replace_file_content", "multi_replace_file_content"),
    "Bash": ("run_command",),
    "Grep": ("grep_search",),
    "Glob": ("find_by_name", "list_dir"),
    "Agent": ("invoke_subagent",),
    "TeamCreate": ("manage_subagents",),
    "TeamDelete": ("manage_subagents",),
    "SendMessage": ("send_message",),
    "TaskCreate": ("manage_task",),
    "TaskList": ("manage_task",),
    "TaskUpdate": ("manage_task",),
}


def _source_tools(source: Path) -> list[str]:
    raw = frontmatter_field(source, "tools")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _mapped_tools(source: Path) -> list[str]:
    mapped: list[str] = []
    unknown: list[str] = []
    for tool in _source_tools(source):
        native = TOOL_MAPPING.get(tool)
        if native is None:
            unknown.append(tool)
            continue
        for name in native:
            if name not in mapped:
                mapped.append(name)
    if unknown:
        raise ValueError(
            f"Unknown Antigravity source tool(s) in {source}: "
            + ", ".join(sorted(unknown))
        )
    return mapped


def _body(source: Path) -> str:
    text = source.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return text.strip()
    parts = text.split("---", 2)
    return (parts[2] if len(parts) == 3 else text).strip()


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_agent(source: Path) -> tuple[str, str]:
    """Render and return ``(name, agent.md)`` after strict source validation."""
    if source.is_symlink() or not source.is_file():
        raise RuntimeError(f"Unsafe Antigravity agent source: {source}")
    name = frontmatter_field(source, "name")
    description = frontmatter_field(source, "description")
    if not SAFE_NAME.fullmatch(name):
        raise ValueError(f"Invalid Antigravity agent name in {source}: {name!r}")
    if not description:
        raise ValueError(f"Missing Antigravity agent description in {source}")
    tools = _mapped_tools(source)
    lines = [
        "---",
        f"name: {name}",
        f"description: {_quote(description)}",
        "mainAgent: false",
        "subagent: true",
        "model: inherit",
        "commandExecutionPolicy: sandbox",
        "tools:",
    ]
    lines.extend(f"  - {tool}" for tool in tools)
    lines.extend(["---", "", MANAGED_MARKER, "", _body(source), ""])
    return name, "\n".join(lines)


def _is_managed(content: bytes | None) -> bool:
    return content is not None and MANAGED_MARKER.encode() in content[:2048]


def _source_plan(source_dir: Path) -> list[tuple[str, str]]:
    if source_dir.is_symlink() or not source_dir.is_dir():
        raise RuntimeError(f"Unsafe Antigravity agents source directory: {source_dir}")
    plan: list[tuple[str, str]] = []
    seen: set[str] = set()
    for source in sorted(source_dir.glob("*.md")):
        name, rendered = render_agent(source)
        if name in seen:
            raise ValueError(f"Duplicate Antigravity agent name: {name}")
        seen.add(name)
        plan.append((name, rendered))
    return plan


def _stale_files(output_dir: Path, expected: set[str]) -> list[Path]:
    if not output_dir.exists():
        return []
    if output_dir.is_symlink() or not output_dir.is_dir():
        raise RuntimeError(f"Unsafe Antigravity agents directory: {output_dir}")
    stale: list[Path] = []
    for child in sorted(output_dir.iterdir()):
        if child.name in expected or not child.name.startswith(AGENT_PREFIX):
            continue
        if child.is_symlink() or not child.is_dir():
            continue
        agent_file = child / "agent.md"
        if agent_file.is_symlink() or not agent_file.is_file():
            continue
        try:
            content = agent_file.read_bytes()
        except OSError:
            continue
        if _is_managed(content):
            stale.append(agent_file)
    return stale


def generate(
    target_dir: Path,
    *,
    source_dir: Path | None = None,
    config_root: Path | None = None,
) -> tuple[int, int]:
    """Generate agents atomically and remove only stale managed definitions."""
    source_root = lexical_absolute(source_dir or agents_dir)
    plan = _source_plan(source_root)  # Preflight all source tools before mutation.
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Antigravity target directory: {target}")
    base = lexical_absolute(config_root) if config_root is not None else target / ".agents"
    output_dir = base / "agents"
    if base.is_symlink() or output_dir.is_symlink():
        raise RuntimeError(f"Unsafe Antigravity config path: {output_dir}")
    expected = {f"{AGENT_PREFIX}{name}" for name, _ in plan}
    stale = _stale_files(output_dir, expected)
    root = nearest_existing_root(target)

    writes: list[tuple[SecureDestination, bytes]] = []
    for name, rendered in plan:
        path = output_dir / f"{AGENT_PREFIX}{name}" / "agent.md"
        writes.append(
            (
                SecureDestination(path, root, f"Antigravity agent {name}"),
                rendered.encode(),
            )
        )
    stale_destinations = [
        SecureDestination(path, root, f"stale Antigravity agent {path.parent.name}")
        for path in stale
    ]
    destinations = [destination for destination, _ in writes] + stale_destinations

    def apply(transaction: SecureTransaction) -> tuple[int, int]:
        written = 0
        removed = 0
        for destination, content in writes:
            existing = transaction.initial_content(destination)
            if existing is not None and not _is_managed(existing):
                continue
            transaction.atomic_write(destination, content, 0o644)
            written += 1
        for destination in stale_destinations:
            existing = transaction.initial_content(destination)
            if _is_managed(existing):
                transaction.unlink(destination)
                removed += 1
        return written, removed

    written, removed = run_secure_transaction(destinations, apply)
    for stale_file in stale:
        directory = stale_file.parent
        if directory.is_dir() and not directory.is_symlink():
            try:
                directory.rmdir()
            except OSError:
                pass
    return written, removed


def cleanup(target_dir: Path, *, config_root: Path | None = None) -> int:
    """Remove managed Antigravity agents while preserving every user agent."""
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Antigravity target directory: {target}")
    base = lexical_absolute(config_root) if config_root is not None else target / ".agents"
    output_dir = base / "agents"
    stale = _stale_files(output_dir, set())
    if not stale:
        return 0
    root = nearest_existing_root(target)
    destinations = [
        SecureDestination(path, root, f"Antigravity agent {path.parent.name}")
        for path in stale
    ]

    def apply(transaction: SecureTransaction) -> int:
        removed = 0
        for destination in destinations:
            if _is_managed(transaction.initial_content(destination)):
                transaction.unlink(destination)
                removed += 1
        return removed

    removed = run_secure_transaction(destinations, apply)
    for path in stale:
        try:
            path.parent.rmdir()
        except OSError:
            pass
    return removed


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    written, removed = generate(target)
    print(
        f"Generated: .agents/agents/ ({written} agents, "
        f"{removed} stale removed)"
    )


if __name__ == "__main__":
    main()
