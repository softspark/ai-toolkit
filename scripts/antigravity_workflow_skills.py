# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Preserve Antigravity workflow command names as owned native skills."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import secure_fs
from dir_rules_shared import STANDARD_WORKFLOWS
from frontmatter import parse_frontmatter, split_frontmatter
from secure_fs import SecureDestination, SecureTransaction, lexical_absolute, run_secure_transaction

MANAGED_MARKER = "<!-- ai-toolkit-managed: antigravity-workflow-skill -->"


def is_workflow_skill(content: bytes | None) -> bool:
    return content is not None and MANAGED_MARKER.encode() in content[:1024]


def owned_workflow_skill_edit(content: bytes) -> bytes | None:
    return None if is_workflow_skill(content) else content


def workflow_skill_paths(root: Path) -> list[Path]:
    """Return regular owned definitions, never following skill-directory links."""
    if root.is_symlink():
        raise RuntimeError(f"Refusing symlinked Antigravity skills directory: {root}")
    if not root.is_dir():
        return []
    paths: list[Path] = []
    for child in sorted(root.glob("ai-toolkit-*")):
        path = child / "SKILL.md"
        if child.is_symlink() or path.is_symlink() or not path.is_file():
            continue
        if is_workflow_skill(path.read_bytes()):
            paths.append(path)
    return paths


def render_workflow_skills() -> dict[str, bytes]:
    rendered: dict[str, bytes] = {}
    for filename, render in STANDARD_WORKFLOWS.items():
        if Path(filename).name != filename or not filename.startswith("ai-toolkit-") or not filename.endswith(".md"):
            raise ValueError(f"Invalid workflow name: {filename}")
        name = Path(filename).stem
        source = render()
        description = parse_frontmatter(source).get("description")
        if not isinstance(description, str) or not description:
            raise ValueError(f"Missing workflow description: {name}")
        _, body = split_frontmatter(source)
        text = f"---\nname: {name}\ndescription: {json.dumps(description)}\n---\n\n{MANAGED_MARKER}\n{body}"
        rendered[name] = text.encode()
    return rendered


def sync_workflow_skills(target: Path, relative_roots: tuple[str, ...]) -> int:
    """Preflight all destinations and atomically update only owned skill files."""
    if not secure_fs.SECURE_DIR_FD:
        print(
            "Antigravity workflow-skill generation requires POSIX path protection. "
            "Use WSL or Antigravity /migrate-workflows; legacy workflow/pointer output is retained.",
            file=sys.stderr,
        )
        return 0
    target = lexical_absolute(target)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Antigravity target: {target}")
    rendered = render_workflow_skills()
    writes: list[tuple[SecureDestination, bytes]] = []
    stale: list[SecureDestination] = []
    for relative in relative_roots:
        root = target / relative
        for path in workflow_skill_paths(root):
            if path.parent.name not in rendered:
                stale.append(SecureDestination(path, target, "stale Antigravity workflow skill"))
        for name, content in rendered.items():
            path = root / name / "SKILL.md"
            if path.parent.is_symlink() or path.is_symlink():
                continue
            writes.append((SecureDestination(path, target, f"Antigravity workflow skill {name}"), content))

    def apply(transaction: SecureTransaction) -> int:
        count = 0
        for destination, content in writes:
            existing = transaction.initial_content(destination)
            if existing is not None and not is_workflow_skill(existing):
                continue
            transaction.atomic_write(destination, content, 0o644)
            count += 1
        for destination in stale:
            if is_workflow_skill(transaction.initial_content(destination)):
                transaction.unlink(destination)
        return count

    return run_secure_transaction([destination for destination, _ in writes] + stale, apply)
