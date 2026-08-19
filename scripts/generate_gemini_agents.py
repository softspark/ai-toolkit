#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate native Gemini CLI subagents under ``.gemini/agents``."""

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
MANAGED_MARKER = "<!-- ai-toolkit-managed: gemini-agent -->"
SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _body(source: Path) -> str:
    text = source.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return text.strip()
    parts = text.split("---", 2)
    return (parts[2] if len(parts) == 3 else text).strip()


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_agent(source: Path) -> tuple[str, str]:
    """Return a Gemini agent name and its native Markdown definition."""
    if source.is_symlink() or not source.is_file():
        raise RuntimeError(f"Unsafe Gemini agent source: {source}")
    name = frontmatter_field(source, "name")
    description = frontmatter_field(source, "description")
    if not SAFE_NAME.fullmatch(name):
        raise ValueError(f"Invalid Gemini agent name in {source}: {name!r}")
    if not description:
        raise ValueError(f"Missing Gemini agent description in {source}")
    lines = [
        "---",
        f"name: {name}",
        f"description: {_quote(description)}",
        "kind: local",
        "---",
        "",
        MANAGED_MARKER,
        "",
        _body(source),
        "",
    ]
    return name, "\n".join(lines)


def _is_managed(content: bytes | None) -> bool:
    return content is not None and MANAGED_MARKER.encode() in content[:2048]


def _stale_files(output_dir: Path, expected: set[str]) -> list[Path]:
    if not output_dir.exists():
        return []
    if output_dir.is_symlink() or not output_dir.is_dir():
        raise RuntimeError(f"Unsafe Gemini agents directory: {output_dir}")
    stale: list[Path] = []
    for candidate in sorted(output_dir.glob(f"{AGENT_PREFIX}*.md")):
        if (
            candidate.name in expected
            or candidate.is_symlink()
            or not candidate.is_file()
        ):
            continue
        try:
            content = candidate.read_bytes()
        except OSError:
            continue
        if _is_managed(content):
            stale.append(candidate)
    return stale


def _source_plan(source_root: Path) -> list[tuple[str, str]]:
    plan: list[tuple[str, str]] = []
    seen: set[str] = set()
    for source in sorted(source_root.glob("*.md")):
        name, rendered = render_agent(source)
        if name in seen:
            raise ValueError(f"Duplicate Gemini agent name: {name}")
        seen.add(name)
        plan.append((name, rendered))
    return plan


def generate(
    target_dir: Path,
    *,
    source_dir: Path | None = None,
) -> tuple[int, int]:
    """Write all native Gemini agents and return ``(written, removed)``."""
    source_root = lexical_absolute(source_dir or agents_dir)
    if source_root.is_symlink() or not source_root.is_dir():
        raise RuntimeError(f"Unsafe Gemini agents source directory: {source_root}")
    plan = _source_plan(source_root)
    target_dir = lexical_absolute(target_dir)
    if target_dir.is_symlink() or not target_dir.is_dir():
        raise RuntimeError(f"Unsafe Gemini target directory: {target_dir}")
    gemini_dir = target_dir / ".gemini"
    output_dir = gemini_dir / "agents"
    if gemini_dir.is_symlink() or output_dir.is_symlink():
        raise RuntimeError(f"Unsafe Gemini agents path: {output_dir}")
    expected = {f"{AGENT_PREFIX}{name}.md" for name, _ in plan}
    stale = _stale_files(output_dir, expected)
    trusted_root = nearest_existing_root(target_dir)
    writes = [
        (
            SecureDestination(
                output_dir / f"{AGENT_PREFIX}{name}.md",
                trusted_root,
                f"Gemini agent {name}",
            ),
            rendered.encode(),
        )
        for name, rendered in plan
    ]
    stale_destinations = [
        SecureDestination(path, trusted_root, f"stale Gemini agent {path.name}")
        for path in stale
    ]

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
            if _is_managed(transaction.initial_content(destination)):
                transaction.unlink(destination)
                removed += 1
        return written, removed

    return run_secure_transaction(
        [destination for destination, _ in writes] + stale_destinations,
        apply,
    )


def cleanup(target_dir: Path) -> int:
    """Remove only managed Gemini agent files from ``target_dir``."""
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Gemini target directory: {target}")
    output_dir = target / ".gemini" / "agents"
    stale = _stale_files(output_dir, set())
    if not stale:
        return 0
    trusted_root = nearest_existing_root(target)
    destinations = [
        SecureDestination(path, trusted_root, f"Gemini agent {path.name}")
        for path in stale
    ]

    def apply(transaction: SecureTransaction) -> int:
        removed = 0
        for destination in destinations:
            if _is_managed(transaction.initial_content(destination)):
                transaction.unlink(destination)
                removed += 1
        return removed

    return run_secure_transaction(destinations, apply)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    written, removed = generate(target)
    print(f"Generated: .gemini/agents/ ({written} agents, {removed} stale removed)")


if __name__ == "__main__":
    main()
