#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Safely remove ai-toolkit-managed runtime data and customizations.

The default scope is the current user's global install. ``--local`` targets a
project, while an explicit legacy positional target scans both project and
home-style locations for backward compatibility. Only files, symlinks, JSON
handlers, settings, and marker blocks with verifiable ai-toolkit ownership are
removed from shared locations.

Global scope first runs the local uninstall in every registered project, then
removes the user-level install and, last, the toolkit data directory
(``~/.softspark/ai-toolkit``: hook scripts, state, registry, session history,
logs, plugins). That directory is archived to
``~/ai-toolkit-backup-<time>.tar.gz`` and the archive is verified before
anything in it is deleted.

Usage:
    python3 scripts/uninstall.py [--yes] [--local|--global] [--target DIR]
    python3 scripts/uninstall.py [--yes] [legacy-target-dir]
"""
from __future__ import annotations

import argparse
import copy
import importlib
import importlib.util
import json
import os
import re
import secrets
import stat
import sys
import tarfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import app_dir, toolkit_dir
from codex_skill_adapter import (
    ADAPTED_MARKERS,
    SKILL_SURFACE_OWNERS_MARKER,
    skill_surface_owners,
)
from injection import strip_all_sections, strip_section, trim_trailing_blanks
from install_steps.hooks import SKILL_LISTING_BUDGET_DEFAULT, TOOLKIT_ENV_VARS
from install_steps.skill_scope import STATE_MANAGED_KEY
# Retirement cleanup for the v4.16.x tool-output filter. The runtime package
# that wrote those files is gone; output_filter_retirement re-states its
# ownership rules as self-contained constants for both install and uninstall.
from output_filter_retirement import (
    PROJECT_OWNER_NAME as _OUTPUT_FILTER_OWNER_NAME,
    PROJECT_POLICY_NAME as _OUTPUT_FILTER_POLICY_NAME,
    clean_owned_recovery_tree,
    count_owned_recovery_artifacts,
    managed_project_policy as _managed_output_filter_policy,
)


CODEX_AGENT_MARKER = "# ai-toolkit-managed: codex-agent"
CODEX_HOOK_ASSET_MARKER = "# ai-toolkit-managed: codex-hook-script"
COPILOT_MARKER = "<!-- ai-toolkit-managed: github-copilot -->"
COPILOT_SKILL_MANIFEST = ".ai-toolkit-managed-files"
COPILOT_HOOK_ASSET_MARKER = "# ai-toolkit-managed: github-copilot-hook"
HOOK_OWNER_KEY = "AI_TOOLKIT_HOOK_OWNER"
LEGACY_CODEX_HOOK_PATH = ".softspark/ai-toolkit/hooks/"

_TOOLKIT_SECTION_RE = re.compile(
    r"^<!-- TOOLKIT:(?P<section>.+) START -->$",
    re.MULTILINE,
)
_CODEX_OWNER_RE = re.compile(
    r"(?:^|\s)AI_TOOLKIT_HOOK_OWNER=(?:['\"])?ai-toolkit(?:['\"])?(?=\s|$)"
)


@dataclass(frozen=True)
class CodexSurface:
    config_root: Path
    instructions: Path
    skills_root: Path
    assets_root: Path


@dataclass(frozen=True)
class CopilotSurface:
    customization_root: Path
    instructions: Path


@dataclass(frozen=True)
class _PathSnapshot:
    kind: str
    mode: int
    atime_ns: int
    mtime_ns: int
    trusted_root: Path
    content: bytes | None = None
    link_target: str | None = None


_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
_SECURE_DIR_FD = (
    hasattr(os, "O_DIRECTORY")
    and hasattr(os, "O_NOFOLLOW")
    and all(
        function in os.supports_dir_fd
        for function in (
            os.open,
            os.unlink,
            os.rmdir,
            os.mkdir,
            os.rename,
            os.stat,
            os.readlink,
            os.symlink,
        )
    )
)
_UNSAFE_MUTATION_PLATFORM_ERROR = (
    "Safe uninstall mutations require POSIX dir_fd and O_NOFOLLOW support, "
    "which this Python runtime does not provide. No files were changed. "
    "On Windows, run ai-toolkit uninstall from WSL."
)


def _require_secure_mutation_support() -> None:
    if not _SECURE_DIR_FD:
        raise RuntimeError(_UNSAFE_MUTATION_PLATFORM_ERROR)


def _lexical_absolute(path: Path) -> Path:
    """Return an absolute normalized path without resolving symlinks."""
    return Path(os.path.abspath(os.fspath(path)))


def _mutation_parts(path: Path, trusted_root: Path) -> tuple[Path, Path, tuple[str, ...]]:
    normalized_path = _lexical_absolute(path)
    normalized_root = _lexical_absolute(trusted_root)
    try:
        relative = normalized_path.relative_to(normalized_root)
    except ValueError as error:
        raise RuntimeError(
            f"Refusing mutation outside trusted root {normalized_root}: {normalized_path}"
        ) from error
    if relative == Path(".") or not relative.parts or ".." in relative.parts:
        raise RuntimeError(
            f"Refusing mutation of trusted root itself: {normalized_path}"
        )
    return normalized_path, normalized_root, relative.parts


@contextmanager
def _open_mutation_parent(
    path: Path,
    trusted_root: Path,
) -> Iterator[tuple[int, Path]]:
    """Pin each ancestor with ``O_NOFOLLOW`` and yield the target's parent fd."""
    _require_secure_mutation_support()
    normalized_path, normalized_root, parts = _mutation_parts(path, trusted_root)
    directory_fd = -1
    try:
        directory_fd = os.open(normalized_root, _DIRECTORY_FLAGS)
        for part in parts[:-1]:
            next_fd = os.open(part, _DIRECTORY_FLAGS, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
    except OSError as error:
        if directory_fd >= 0:
            os.close(directory_fd)
        raise RuntimeError(
            "Refusing mutation through an unsafe ancestor between "
            f"{normalized_root} and {normalized_path.parent}: {error}"
        ) from error
    try:
        yield directory_fd, normalized_path
    finally:
        os.close(directory_fd)


def _assert_mutation_parent(path: Path, trusted_root: Path) -> None:
    """Reject any symlink/non-directory ancestor below an explicit boundary."""
    with _open_mutation_parent(path, trusted_root):
        pass


def _safe_lstat(path: Path, trusted_root: Path) -> os.stat_result | None:
    with _open_mutation_parent(path, trusted_root) as (parent_fd, normalized_path):
        try:
            return os.stat(
                normalized_path.name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return None


def _safe_readlink(path: Path, trusted_root: Path) -> str:
    with _open_mutation_parent(path, trusted_root) as (parent_fd, normalized_path):
        return os.readlink(normalized_path.name, dir_fd=parent_fd)


def _safe_unlink(path: Path, trusted_root: Path) -> None:
    _assert_mutation_parent(path, trusted_root)
    with _open_mutation_parent(path, trusted_root) as (parent_fd, normalized_path):
        os.unlink(normalized_path.name, dir_fd=parent_fd)


def _safe_rmdir(path: Path, trusted_root: Path) -> None:
    _assert_mutation_parent(path, trusted_root)
    with _open_mutation_parent(path, trusted_root) as (parent_fd, normalized_path):
        os.rmdir(normalized_path.name, dir_fd=parent_fd)


def _safe_mkdir(path: Path, mode: int, trusted_root: Path) -> None:
    _assert_mutation_parent(path, trusted_root)
    with _open_mutation_parent(path, trusted_root) as (parent_fd, normalized_path):
        os.mkdir(normalized_path.name, mode=mode, dir_fd=parent_fd)


def _safe_symlink(target: str, path: Path, trusted_root: Path) -> None:
    _assert_mutation_parent(path, trusted_root)
    with _open_mutation_parent(path, trusted_root) as (parent_fd, normalized_path):
        os.symlink(target, normalized_path.name, dir_fd=parent_fd)


def _safe_chmod(path: Path, mode: int, trusted_root: Path) -> None:
    _assert_mutation_parent(path, trusted_root)
    with _open_mutation_parent(path, trusted_root) as (parent_fd, normalized_path):
        os.chmod(
            normalized_path.name,
            mode,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )


def _safe_utime(
    path: Path,
    times: tuple[int, int],
    trusted_root: Path,
) -> None:
    _assert_mutation_parent(path, trusted_root)
    with _open_mutation_parent(path, trusted_root) as (parent_fd, normalized_path):
        os.utime(
            normalized_path.name,
            ns=times,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )


class _UninstallTransaction:
    """Snapshot touched surfaces and restore their original bytes on failure."""

    def __init__(self, specs: list[tuple[Path, bool, Path]]) -> None:
        self._entries: dict[Path, _PathSnapshot] = {}
        for path, recursive, trusted_root in specs:
            self._capture(path, recursive=recursive, trusted_root=trusted_root)

    def _capture(self, path: Path, *, recursive: bool, trusted_root: Path) -> None:
        if not path.exists() and not path.is_symlink():
            return
        metadata = os.lstat(path)
        mode = stat.S_IMODE(metadata.st_mode)
        common = {
            "mode": mode,
            "atime_ns": metadata.st_atime_ns,
            "mtime_ns": metadata.st_mtime_ns,
            "trusted_root": trusted_root,
        }
        if stat.S_ISLNK(metadata.st_mode):
            self._entries.setdefault(
                path,
                _PathSnapshot("symlink", link_target=os.readlink(path), **common),
            )
            return
        if stat.S_ISREG(metadata.st_mode):
            self._entries.setdefault(
                path,
                _PathSnapshot("file", content=path.read_bytes(), **common),
            )
            return
        if not stat.S_ISDIR(metadata.st_mode):
            raise RuntimeError(f"Unsupported uninstall path type: {path}")
        self._entries.setdefault(path, _PathSnapshot("directory", **common))
        if recursive:
            for child in sorted(path.iterdir()):
                self._capture(child, recursive=True, trusted_root=trusted_root)

    def rollback(self) -> None:
        errors: list[str] = []
        directories = [
            (path, entry)
            for path, entry in self._entries.items()
            if entry.kind == "directory"
        ]
        leaves = [
            (path, entry)
            for path, entry in self._entries.items()
            if entry.kind != "directory"
        ]
        for path, entry in sorted(directories, key=lambda item: len(item[0].parts)):
            try:
                self._restore_directory(path, entry)
            except (OSError, RuntimeError) as error:
                errors.append(f"{path}: {error}")
        for path, entry in sorted(leaves, key=lambda item: len(item[0].parts)):
            try:
                self._restore_leaf(path, entry)
            except (OSError, RuntimeError) as error:
                errors.append(f"{path}: {error}")
        for path, entry in sorted(
            directories,
            key=lambda item: len(item[0].parts),
            reverse=True,
        ):
            try:
                _safe_chmod(path, entry.mode, entry.trusted_root)
                _safe_utime(
                    path,
                    (entry.atime_ns, entry.mtime_ns),
                    entry.trusted_root,
                )
            except (OSError, RuntimeError) as error:
                errors.append(f"{path}: {error}")
        if errors:
            raise RuntimeError("rollback incomplete: " + "; ".join(errors))

    @staticmethod
    def _restore_directory(path: Path, entry: _PathSnapshot) -> None:
        metadata = _safe_lstat(path, entry.trusted_root)
        if metadata is not None and stat.S_ISLNK(metadata.st_mode):
            raise RuntimeError("directory path became a symlink")
        if metadata is not None and not stat.S_ISDIR(metadata.st_mode):
            raise RuntimeError("directory path became a non-directory")
        if metadata is None:
            _safe_mkdir(path, entry.mode, entry.trusted_root)
        _safe_chmod(path, entry.mode, entry.trusted_root)

    @staticmethod
    def _restore_leaf(path: Path, entry: _PathSnapshot) -> None:
        metadata = _safe_lstat(path, entry.trusted_root)
        if entry.kind == "file":
            if metadata is not None and stat.S_ISLNK(metadata.st_mode):
                _safe_unlink(path, entry.trusted_root)
            elif metadata is not None and not stat.S_ISREG(metadata.st_mode):
                raise RuntimeError("file path became a non-file")
            _atomic_write_bytes(
                path,
                entry.content or b"",
                entry.mode,
                entry.trusted_root,
            )
            _safe_utime(
                path,
                (entry.atime_ns, entry.mtime_ns),
                entry.trusted_root,
            )
            return
        if metadata is not None and stat.S_ISLNK(metadata.st_mode):
            if _safe_readlink(path, entry.trusted_root) == entry.link_target:
                return
            _safe_unlink(path, entry.trusted_root)
        elif metadata is not None:
            if stat.S_ISDIR(metadata.st_mode):
                _safe_rmdir(path, entry.trusted_root)
            else:
                _safe_unlink(path, entry.trusted_root)
        _safe_symlink(entry.link_target or "", path, entry.trusted_root)


def _link_target(path: Path) -> Path:
    raw = Path(os.readlink(path))
    return (path.parent / raw if not raw.is_absolute() else raw).resolve(strict=False)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _is_toolkit_link(path: Path) -> bool:
    """Return whether a symlink points into an ai-toolkit ``app`` directory."""
    if not path.is_symlink():
        return False
    target = _link_target(path)
    if _is_relative_to(target, app_dir.resolve()):
        return True
    normalized = target.as_posix()
    return "/ai-toolkit/app/" in normalized


def _read_prefix(path: Path, limit: int = 512) -> str:
    if path.is_symlink() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")[:limit]
    except (OSError, UnicodeError):
        return ""


def _has_marker(path: Path, marker: str, *, lines: int | None = None) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    if lines is not None:
        content = "\n".join(content.splitlines()[:lines])
    return marker in content


def _atomic_write_bytes(
    path: Path,
    content: bytes,
    mode: int,
    trusted_root: Path,
) -> None:
    _assert_mutation_parent(path, trusted_root)
    metadata = _safe_lstat(path, trusted_root)
    if metadata is not None and stat.S_ISLNK(metadata.st_mode):
        raise RuntimeError(f"Refusing to replace symlink: {path}")

    with _open_mutation_parent(path, trusted_root) as (parent_fd, normalized_path):
        target_name = normalized_path.name
        temporary_name = f".{target_name}.{secrets.token_hex(8)}.tmp"
        temporary_fd = -1
        try:
            temporary_fd = os.open(
                temporary_name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                mode,
                dir_fd=parent_fd,
            )
            with os.fdopen(temporary_fd, "wb") as handle:
                temporary_fd = -1
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                os.fchmod(handle.fileno(), mode)
            current = (
                os.stat(
                    target_name,
                    dir_fd=parent_fd,
                    follow_symlinks=False,
                )
                if metadata is not None
                else None
            )
            if current is not None and stat.S_ISLNK(current.st_mode):
                raise RuntimeError(f"Destination became a symlink: {path}")
            os.replace(
                temporary_name,
                target_name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
        finally:
            if temporary_fd >= 0:
                os.close(temporary_fd)
            try:
                os.unlink(temporary_name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass


def _atomic_write_text(path: Path, content: str, trusted_root: Path) -> None:
    metadata = _safe_lstat(path, trusted_root)
    mode = stat.S_IMODE(metadata.st_mode) if metadata is not None else 0o644
    _atomic_write_bytes(path, content.encode(), mode, trusted_root)


def _write_or_remove(path: Path, content: str, trusted_root: Path) -> None:
    content = trim_trailing_blanks(content).lstrip("\n")
    if content.strip():
        _atomic_write_text(path, content + "\n", trusted_root)
    else:
        _safe_unlink(path, trusted_root)


def _strip_instruction_file(
    path: Path,
    *,
    preserve_plugins: bool,
    trusted_root: Path,
) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    original = path.read_text(encoding="utf-8")
    if "<!-- TOOLKIT:" not in original:
        return False
    if preserve_plugins:
        updated = original
        sections = set(_TOOLKIT_SECTION_RE.findall(original))
        for section in sorted(sections):
            if not section.startswith("plugin-"):
                updated = strip_section(updated, section)
    else:
        updated = strip_all_sections(original)
    if updated == original:
        return False
    _write_or_remove(path, updated, trusted_root)
    return True


def _load_json(path: Path, label: str) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"  Warning: preserved invalid {label}: {path} ({error})", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print(f"  Warning: preserved non-object {label}: {path}", file=sys.stderr)
        return None
    return data


def _prune_empty(*paths: Path, trusted_root: Path) -> None:
    unique = sorted(set(paths), key=lambda path: len(path.parts), reverse=True)
    for path in unique:
        if path.is_symlink() or not path.is_dir():
            continue
        try:
            _safe_rmdir(path, trusted_root)
        except (OSError, RuntimeError):
            pass


# ---------------------------------------------------------------------------
# Claude Code compatibility cleanup
# ---------------------------------------------------------------------------

def _discover_claude_link_directories(claude_dir: Path) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for item in ("agents", "skills", "commands"):
        target = claude_dir / item
        if target.is_symlink() and _is_toolkit_link(target):
            found.append((f"Symlink: {item} -> {target.readlink()} (directory)", "old-dir"))
    return found


def _managed_links(directory: Path, pattern: str | None = None) -> list[Path]:
    if not directory.is_dir() or directory.is_symlink():
        return []
    candidates = directory.glob(pattern) if pattern is not None else directory.iterdir()
    return [
        path for path in candidates
        if path.is_symlink() and _is_toolkit_link(path)
    ]


def _merge_hooks() -> Any:
    """Load ``merge-hooks.py``; its hyphenated name rules out a plain import."""
    spec = importlib.util.spec_from_file_location(
        "ai_toolkit_merge_hooks",
        toolkit_dir / "scripts" / "merge-hooks.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load scripts/merge-hooks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _toolkit_hooks() -> dict[str, Any]:
    data = _load_json(app_dir / "hooks.json", "toolkit hooks file")
    hooks = data.get("hooks") if data is not None else None
    return hooks if isinstance(hooks, dict) else {}


def _toolkit_style_names() -> dict[str, str]:
    """Map each shipped output style file name to its ``name:`` value."""
    styles: dict[str, str] = {}
    for path in sorted((app_dir / "output-styles").glob("*.md")):
        match = re.search(r"^name:\s*(.+?)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            styles[path.name] = match.group(1).strip("'\"")
    return styles


def _without_toolkit_settings(
    data: dict[str, Any],
    managed_overrides: set[str],
) -> tuple[dict[str, Any], list[str]]:
    """Return ``data`` minus every setting the toolkit wrote, and their keys.

    Hooks and statusLine are matched by tag, toolkit signature, or a command
    under the toolkit hooks directory. Scalar settings are removed only while
    they still hold the value the toolkit set, so a user's own choice stays.
    """
    updated = copy.deepcopy(data)
    changed: list[str] = []
    merge_hooks = _merge_hooks()
    hooks = updated.get("hooks")
    if isinstance(hooks, dict):
        stripped = merge_hooks._without_toolkit_handlers(
            merge_hooks.strip_toolkit(hooks, _toolkit_hooks())
        )
        if stripped != hooks:
            changed.append("hooks")
            if stripped:
                updated["hooks"] = stripped
            else:
                updated.pop("hooks")
    status_line = updated.get("statusLine")
    if isinstance(status_line, dict) and (
        status_line.get("_source") == merge_hooks.SOURCE_TAG
        or merge_hooks._runs_toolkit_script(status_line)
    ):
        updated.pop("statusLine")
        changed.append("statusLine")
    if updated.get("outputStyle") in set(_toolkit_style_names().values()):
        updated.pop("outputStyle")
        changed.append("outputStyle")
    env = updated.get("env")
    if isinstance(env, dict):
        for key, value in TOOLKIT_ENV_VARS.items():
            if env.get(key) == value:
                env.pop(key)
                changed.append(f"env.{key}")
        if not env:
            updated.pop("env")
    if updated.get("skillListingBudgetFraction") == SKILL_LISTING_BUDGET_DEFAULT:
        updated.pop("skillListingBudgetFraction")
        changed.append("skillListingBudgetFraction")
    overrides = updated.get("skillOverrides")
    if isinstance(overrides, dict):
        owned = sorted(
            name for name in managed_overrides if overrides.get(name) == "off"
        )
        for name in owned:
            overrides.pop(name)
        if owned:
            changed.append(f"skillOverrides ({len(owned)})")
        if not overrides:
            updated.pop("skillOverrides")
    return updated, changed


def _managed_skill_overrides(data_dir: Path | None) -> set[str]:
    state = _load_json(data_dir / "state.json", "toolkit state") if data_dir else None
    names = state.get(STATE_MANAGED_KEY, []) if state is not None else []
    return {name for name in names if isinstance(name, str)} if isinstance(names, list) else set()


def _discover_claude_hooks(
    claude_dir: Path,
    managed_overrides: set[str],
) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    hooks_file = claude_dir / "hooks.json"
    if hooks_file.is_symlink() and _is_toolkit_link(hooks_file):
        found.append((f"Symlink: hooks.json -> {hooks_file.readlink()} (legacy)", "hooks-link"))
    for name in ("hooks.json", "settings.json"):
        data = _load_json(claude_dir / name, f"Claude {name}")
        if data is None:
            continue
        _, changed = _without_toolkit_settings(data, managed_overrides)
        if changed:
            found.append((f"Merged: {name} ({', '.join(changed)})", "settings"))
    return found


def _toolkit_output_styles(claude_dir: Path) -> list[Path]:
    styles_dir = claude_dir / "output-styles"
    if not styles_dir.is_dir() or styles_dir.is_symlink():
        return []
    return [
        styles_dir / name for name in _toolkit_style_names()
        if (styles_dir / name).is_file() and not (styles_dir / name).is_symlink()
    ]


def _discover_output_filter_policy(claude_dir: Path) -> list[tuple[str, str]]:
    if not _managed_output_filter_policy(claude_dir):
        return []
    return [(
        f"Managed: {_OUTPUT_FILTER_POLICY_NAME} (project output-filter policy)",
        "output-filter-policy",
    )]


def _remove_output_filter_policy(claude_dir: Path, trusted_root: Path) -> None:
    managed = _managed_output_filter_policy(claude_dir)
    for path in managed:
        _safe_unlink(path, trusted_root)
    if managed:
        print(f"  Removed: .claude/{_OUTPUT_FILTER_POLICY_NAME} (managed)")


def _discover_claude_markers(claude_dir: Path) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for item in ("constitution.md", "ARCHITECTURE.md"):
        target = claude_dir / item
        if target.is_symlink() and _is_toolkit_link(target):
            found.append((f"Symlink: {item} -> {target.readlink()} (legacy)", "marker-link"))
        elif not target.is_symlink() and target.is_file() and "<!-- TOOLKIT:" in (
            target.read_text(encoding="utf-8")
        ):
            found.append((f"Injected: {item} (marker-based)", "marker-inject"))
    return found


def _managed_rule_files(claude_dir: Path) -> list[Path]:
    """``rules/ai-toolkit-*.md``: the prefix is reserved for the toolkit."""
    rules_root = claude_dir / "rules"
    if not rules_root.is_dir() or rules_root.is_symlink():
        return []
    return sorted(
        path for path in rules_root.glob("ai-toolkit-*.md")
        if path.is_file() and not path.is_symlink()
    )


def _discover_claude_rules(claude_dir: Path) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    rules = _managed_rule_files(claude_dir)
    if rules:
        found.append((f"Rules: rules/ai-toolkit-*.md ({len(rules)} file(s))", "claude-rules"))
    claude_md = claude_dir / "CLAUDE.md"
    if (
        not claude_md.is_symlink()
        and claude_md.is_file()
        and "<!-- TOOLKIT:" in claude_md.read_text(encoding="utf-8")
    ):
        found.append(("Injected: CLAUDE.md (toolkit sections)", "claude-md"))
    return found


def _remove_claude_rules(claude_dir: Path, trusted_root: Path) -> None:
    rules = _managed_rule_files(claude_dir)
    for path in rules:
        _safe_unlink(path, trusted_root)
    if rules:
        print(f"  Removed: {len(rules)} .claude/rules/ai-toolkit-*.md rule file(s)")
    _prune_empty(claude_dir / "rules", trusted_root=trusted_root)
    # Plugin-owned sections belong to installed plugins, not to the toolkit.
    if _strip_instruction_file(
        claude_dir / "CLAUDE.md",
        preserve_plugins=True,
        trusted_root=trusted_root,
    ):
        print("  Stripped: .claude/CLAUDE.md (user content preserved)")


def discover_components(
    claude_dir: Path,
    managed_overrides: set[str] | None = None,
) -> list[tuple[str, str]]:
    """Find verifiably managed Claude Code components."""
    found = _discover_claude_link_directories(claude_dir)
    agent_links = _managed_links(claude_dir / "agents", "*.md")
    if agent_links:
        found.append((f"Symlinks: agents/ ({len(agent_links)} toolkit files)", "agent-link"))
    skill_links = _managed_links(claude_dir / "skills")
    if skill_links:
        found.append((f"Symlinks: skills/ ({len(skill_links)} toolkit directories)", "skill-link"))
    found.extend(_discover_claude_hooks(claude_dir, managed_overrides or set()))
    styles = _toolkit_output_styles(claude_dir)
    if styles:
        found.append((f"Copied: output-styles/ ({len(styles)} toolkit styles)", "output-styles"))
    found.extend(_discover_claude_markers(claude_dir))
    found.extend(_discover_claude_rules(claude_dir))
    found.extend(_discover_output_filter_policy(claude_dir))
    return found


def _remove_claude_link_directories(
    claude_dir: Path,
    trusted_root: Path,
) -> None:
    for item in ("agents", "skills", "commands"):
        target = claude_dir / item
        if target.is_symlink() and _is_toolkit_link(target):
            _safe_unlink(target, trusted_root)
            print(f"  Removed: .claude/{item} (managed directory symlink)")


def _remove_claude_links(
    directory: Path,
    pattern: str | None,
    label: str,
    trusted_root: Path,
) -> None:
    managed = _managed_links(directory, pattern)
    for path in managed:
        if not path.is_symlink() or not _is_toolkit_link(path):
            raise RuntimeError(f"Managed Claude link changed before removal: {path}")
        _safe_unlink(path, trusted_root)
    if managed:
        print(f"  Removed: {len(managed)} Claude {label} symlink(s)")
    _prune_empty(directory, trusted_root=trusted_root)


def _remove_claude_hooks(
    claude_dir: Path,
    trusted_root: Path,
    managed_overrides: set[str],
) -> None:
    hooks_file = claude_dir / "hooks.json"
    if hooks_file.is_symlink() and _is_toolkit_link(hooks_file):
        _safe_unlink(hooks_file, trusted_root)
        print("  Removed: .claude/hooks.json (managed legacy symlink)")
    for name in ("hooks.json", "settings.json"):
        path = claude_dir / name
        data = _load_json(path, f"Claude {name}")
        if data is None:
            continue
        updated, changed = _without_toolkit_settings(data, managed_overrides)
        if not changed:
            continue
        if updated:
            _atomic_write_text(
                path,
                json.dumps(updated, indent=4, ensure_ascii=False) + "\n",
                trusted_root,
            )
            print(f"  Stripped: .claude/{name} ({', '.join(changed)}; user settings preserved)")
        else:
            _safe_unlink(path, trusted_root)
            print(f"  Removed: .claude/{name} (held only toolkit settings)")


def _remove_output_styles(claude_dir: Path, trusted_root: Path) -> None:
    styles = _toolkit_output_styles(claude_dir)
    for path in styles:
        _safe_unlink(path, trusted_root)
    if styles:
        print(f"  Removed: {len(styles)} .claude/output-styles/ toolkit style(s)")
    _prune_empty(claude_dir / "output-styles", trusted_root=trusted_root)


def _remove_claude_markers(claude_dir: Path, trusted_root: Path) -> None:
    for item in ("constitution.md", "ARCHITECTURE.md"):
        target = claude_dir / item
        if target.is_symlink() and _is_toolkit_link(target):
            _safe_unlink(target, trusted_root)
            print(f"  Removed: .claude/{item} (managed legacy symlink)")
        elif _strip_instruction_file(
            target,
            preserve_plugins=False,
            trusted_root=trusted_root,
        ):
            print(f"  Stripped: .claude/{item} (user content preserved)")


def remove_components(
    claude_dir: Path,
    trusted_root: Path,
    managed_overrides: set[str] | None = None,
) -> None:
    """Remove only verifiably managed Claude Code components."""
    _remove_claude_link_directories(claude_dir, trusted_root)
    _remove_claude_links(
        claude_dir / "agents",
        "*.md",
        "agent",
        trusted_root,
    )
    _remove_claude_links(
        claude_dir / "skills",
        None,
        "skill",
        trusted_root,
    )
    _remove_claude_hooks(claude_dir, trusted_root, managed_overrides or set())
    _remove_output_styles(claude_dir, trusted_root)
    _remove_claude_markers(claude_dir, trusted_root)
    _remove_claude_rules(claude_dir, trusted_root)
    _remove_output_filter_policy(claude_dir, trusted_root)
    _prune_empty(claude_dir, trusted_root=trusted_root)


# ---------------------------------------------------------------------------
# Codex cleanup
# ---------------------------------------------------------------------------

def _is_codex_agent(path: Path) -> bool:
    return _has_marker(path, CODEX_AGENT_MARKER, lines=3)


def _is_codex_skill(path: Path) -> bool:
    if path.is_symlink():
        return _is_toolkit_link(path)
    return path.is_dir() and any(
        not (path / marker_name).is_symlink()
        and (path / marker_name).is_file()
        for marker_name in ADAPTED_MARKERS
    )


def _remove_codex_skills(skills_root: Path, trusted_root: Path) -> int:
    if not skills_root.is_dir() or skills_root.is_symlink():
        return 0
    removed = 0
    for skill in sorted(skills_root.iterdir()):
        if skill.is_symlink():
            if _is_toolkit_link(skill):
                _safe_unlink(skill, trusted_root)
                removed += 1
            continue
        if not _is_codex_skill(skill):
            continue
        for child in sorted(skill.iterdir()):
            if child.name in {"SKILL.md", *ADAPTED_MARKERS}:
                if not child.is_symlink() and child.is_file():
                    _safe_unlink(child, trusted_root)
                continue
            if child.is_symlink() and _is_toolkit_link(child):
                _safe_unlink(child, trusted_root)
        _prune_empty(skill, trusted_root=trusted_root)
        removed += 1
    _prune_empty(skills_root, skills_root.parent, trusted_root=trusted_root)
    return removed


def _remove_skill_surface_owners_marker(
    skills_root: Path,
    trusted_root: Path,
) -> bool:
    """Remove a valid owner marker after every managed skill is gone."""
    marker = skills_root.parent / SKILL_SURFACE_OWNERS_MARKER
    owners = skill_surface_owners(skills_root)
    if not owners:
        return False
    if skills_root.is_dir() and any(
        _is_codex_skill(skill) for skill in skills_root.iterdir()
    ):
        return False
    if skill_surface_owners(skills_root) != owners:
        raise RuntimeError(f"Skill surface ownership changed before removal: {marker}")
    _safe_unlink(marker, trusted_root)
    return True


def _is_codex_core_handler(handler: Any, group: dict[str, Any]) -> bool:
    if group.get("_source") == "ai-toolkit":
        return True
    if not isinstance(handler, dict):
        return False
    if handler.get("_source") == "ai-toolkit":
        return True
    command = handler.get("command")
    return isinstance(command, str) and (
        _CODEX_OWNER_RE.search(command) is not None
        or LEGACY_CODEX_HOOK_PATH in command
    )


def _without_codex_hooks(data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    updated = copy.deepcopy(data)
    hooks = updated.get("hooks")
    if not isinstance(hooks, dict):
        return updated, 0
    removed = 0
    retained_events: dict[str, Any] = {}
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            retained_events[event] = groups
            continue
        retained_groups: list[Any] = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                retained_groups.append(group)
                continue
            handlers = group["hooks"]
            retained = [
                handler for handler in handlers
                if not _is_codex_core_handler(handler, group)
            ]
            removed += len(handlers) - len(retained)
            if retained:
                retained_group = dict(group)
                retained_group["hooks"] = retained
                if retained_group.get("_source") == "ai-toolkit":
                    retained_group.pop("_source", None)
                retained_groups.append(retained_group)
        if retained_groups:
            retained_events[event] = retained_groups
    updated["hooks"] = retained_events
    return updated, removed


def _remove_codex_hooks(path: Path, trusted_root: Path) -> int:
    data = _load_json(path, "Codex hooks file")
    if data is None:
        return 0
    updated, removed = _without_codex_hooks(data)
    if not removed:
        return 0
    if not updated.get("hooks") and set(updated) == {"hooks"}:
        _safe_unlink(path, trusted_root)
    else:
        _atomic_write_text(
            path,
            json.dumps(updated, indent=4, ensure_ascii=False) + "\n",
            trusted_root,
        )
    return removed


def _remove_marked_assets(root: Path, marker: str, trusted_root: Path) -> int:
    if not root.is_dir() or root.is_symlink():
        return 0
    removed = 0
    for path in sorted(root.iterdir()):
        if path.is_symlink() or not path.is_file():
            continue
        if marker in _read_prefix(path):
            if marker not in _read_prefix(path):
                raise RuntimeError(f"Managed hook asset changed before removal: {path}")
            _safe_unlink(path, trusted_root)
            removed += 1
    _prune_empty(root, trusted_root=trusted_root)
    return removed


def _discover_codex(surface: CodexSurface) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if surface.instructions.is_file() and "<!-- TOOLKIT:" in (
        surface.instructions.read_text(encoding="utf-8")
    ):
        found.append((f"Injected: {surface.instructions} (Codex instructions)", "codex-rules"))
    agents = surface.config_root / "agents"
    if agents.is_dir() and not agents.is_symlink():
        count = sum(1 for path in agents.glob("*.toml") if _is_codex_agent(path))
        if count:
            found.append((f"Managed: {agents} ({count} Codex agents)", "codex-agents"))
    if surface.skills_root.is_dir() and not surface.skills_root.is_symlink():
        count = sum(1 for path in surface.skills_root.iterdir() if _is_codex_skill(path))
        if count:
            found.append((f"Managed: {surface.skills_root} ({count} Codex skills)", "codex-skills"))
    owners = skill_surface_owners(surface.skills_root)
    if owners:
        marker = surface.skills_root.parent / SKILL_SURFACE_OWNERS_MARKER
        found.append((
            f"Managed: {marker} ({', '.join(sorted(owners))})",
            "agent-skill-owners",
        ))
    hooks_path = surface.config_root / "hooks.json"
    data = _load_json(hooks_path, "Codex hooks file")
    if data is not None:
        _, count = _without_codex_hooks(data)
        if count:
            found.append((f"Merged: {hooks_path} ({count} Codex hooks)", "codex-hooks"))
    if surface.assets_root.is_dir() and not surface.assets_root.is_symlink():
        count = sum(
            1 for path in surface.assets_root.iterdir()
            if not path.is_symlink() and path.is_file()
            and CODEX_HOOK_ASSET_MARKER in _read_prefix(path)
        )
        if count:
            found.append((f"Managed: {surface.assets_root} ({count} Codex hook assets)", "codex-assets"))
    return found


def _remove_codex(surface: CodexSurface) -> None:
    config_boundary = surface.config_root.parent
    instruction_boundary = surface.instructions.parent
    skills_boundary = surface.skills_root.parent.parent
    if _strip_instruction_file(
        surface.instructions,
        preserve_plugins=True,
        trusted_root=instruction_boundary,
    ):
        print(f"  Stripped: {surface.instructions} (plugin/user content preserved)")
    agents = surface.config_root / "agents"
    removed_agents = 0
    if agents.is_dir() and not agents.is_symlink():
        for path in sorted(agents.glob("*.toml")):
            if _is_codex_agent(path):
                if not _is_codex_agent(path):
                    raise RuntimeError(f"Managed Codex agent changed before removal: {path}")
                _safe_unlink(path, config_boundary)
                removed_agents += 1
        _prune_empty(agents, trusted_root=config_boundary)
    if removed_agents:
        print(f"  Removed: {removed_agents} Codex native agent(s)")
    removed_skills = _remove_codex_skills(
        surface.skills_root,
        skills_boundary,
    )
    if removed_skills:
        print(f"  Removed: {removed_skills} managed Codex skill(s)")
    if _remove_skill_surface_owners_marker(
        surface.skills_root,
        skills_boundary,
    ):
        print("  Removed: managed agent-skill owner marker")
    removed_hooks = _remove_codex_hooks(
        surface.config_root / "hooks.json",
        config_boundary,
    )
    if removed_hooks:
        print(f"  Removed: {removed_hooks} managed Codex hook handler(s)")
    removed_assets = _remove_marked_assets(
        surface.assets_root,
        CODEX_HOOK_ASSET_MARKER,
        config_boundary,
    )
    if removed_assets:
        print(f"  Removed: {removed_assets} managed Codex hook asset(s)")
    _prune_empty(surface.config_root, trusted_root=config_boundary)
    _prune_empty(surface.skills_root.parent, trusted_root=skills_boundary)


# ---------------------------------------------------------------------------
# GitHub Copilot cleanup
# ---------------------------------------------------------------------------

def _is_copilot_file(path: Path) -> bool:
    return _has_marker(path, COPILOT_MARKER, lines=12)


def _safe_manifest_paths(skill: Path) -> list[Path] | None:
    manifest = skill / COPILOT_SKILL_MANIFEST
    if manifest.is_symlink() or not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, list) or any(not isinstance(item, str) for item in data):
        return None
    paths: list[Path] = []
    for item in data:
        relative = Path(item)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            return None
        paths.append(skill.joinpath(*relative.parts))
    return paths


def _has_symlinked_ancestor(path: Path, boundary: Path) -> bool:
    """Return whether ``path`` escapes through a symlink below ``boundary``."""
    current = path.parent
    while current != boundary:
        if not _is_relative_to(current, boundary) or current.is_symlink():
            return True
        current = current.parent
    return False


def _is_copilot_skill(skill: Path) -> bool:
    return (
        not skill.is_symlink()
        and skill.is_dir()
        and _is_copilot_file(skill / "SKILL.md")
    )


def _remove_copilot_skill(skill: Path, trusted_root: Path) -> bool:
    if not _is_copilot_skill(skill):
        return False
    manifest = skill / COPILOT_SKILL_MANIFEST
    managed_paths = _safe_manifest_paths(skill)
    removed_parents: set[Path] = set()
    if managed_paths is not None:
        for path in sorted(set(managed_paths), key=lambda item: len(item.parts), reverse=True):
            if (
                path.is_symlink()
                or _has_symlinked_ancestor(path, skill)
                or not path.is_file()
            ):
                continue
            _safe_unlink(path, trusted_root)
            removed_parents.add(path.parent)
    skill_file = skill / "SKILL.md"
    if _is_copilot_file(skill_file):
        if not _is_copilot_file(skill_file):
            raise RuntimeError(f"Managed Copilot skill changed before removal: {skill_file}")
        _safe_unlink(skill_file, trusted_root)
        removed_parents.add(skill)
    if managed_paths is not None and manifest.is_file() and not manifest.is_symlink():
        _safe_unlink(manifest, trusted_root)
    for parent in sorted(removed_parents, key=lambda item: len(item.parts), reverse=True):
        current = parent
        while current != skill.parent and _is_relative_to(current, skill):
            before = current
            _prune_empty(current, trusted_root=trusted_root)
            if before.exists():
                break
            current = current.parent
    _prune_empty(skill, trusted_root=trusted_root)
    return True


def _is_copilot_core_hook(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    env = entry.get("env")
    return isinstance(env, dict) and env.get(HOOK_OWNER_KEY) == "ai-toolkit"


def _without_copilot_hooks(data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    updated = copy.deepcopy(data)
    hooks = updated.get("hooks")
    if not isinstance(hooks, dict):
        return updated, 0
    removed = 0
    retained_hooks: dict[str, Any] = {}
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            retained_hooks[event] = entries
            continue
        retained = [entry for entry in entries if not _is_copilot_core_hook(entry)]
        removed += len(entries) - len(retained)
        if retained:
            retained_hooks[event] = retained
    updated["hooks"] = retained_hooks
    return updated, removed


def _remove_copilot_hooks(path: Path, trusted_root: Path) -> int:
    data = _load_json(path, "Copilot hooks file")
    if data is None:
        return 0
    updated, removed = _without_copilot_hooks(data)
    if not removed:
        return 0
    if not updated.get("hooks") and set(updated) <= {"version", "hooks"}:
        _safe_unlink(path, trusted_root)
    else:
        _atomic_write_text(
            path,
            json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
            trusted_root,
        )
    return removed


def _discover_copilot(surface: CopilotSurface) -> list[tuple[str, str]]:
    root = surface.customization_root
    found: list[tuple[str, str]] = []
    if surface.instructions.is_file() and "<!-- TOOLKIT:" in (
        surface.instructions.read_text(encoding="utf-8")
    ):
        found.append((f"Injected: {surface.instructions} (Copilot instructions)", "copilot-rules"))
    for directory_name, suffix, kind in (
        ("instructions", ".instructions.md", "instructions"),
        ("agents", ".agent.md", "agents"),
        ("prompts", ".prompt.md", "prompts"),
    ):
        directory = root / directory_name
        if directory.is_dir() and not directory.is_symlink():
            count = sum(
                1 for path in directory.glob(f"*{suffix}") if _is_copilot_file(path)
            )
            if count:
                found.append((f"Managed: {directory} ({count} Copilot {kind})", f"copilot-{kind}"))
    skills = root / "skills"
    if skills.is_dir() and not skills.is_symlink():
        count = sum(1 for skill in skills.iterdir() if _is_copilot_skill(skill))
        if count:
            found.append((f"Managed: {skills} ({count} Copilot skills)", "copilot-skills"))
    hooks_path = root / "hooks" / "ai-toolkit.json"
    data = _load_json(hooks_path, "Copilot hooks file")
    if data is not None:
        _, count = _without_copilot_hooks(data)
        if count:
            found.append((f"Managed: {hooks_path} ({count} Copilot hooks)", "copilot-hooks"))
    assets = root / "hooks" / "ai-toolkit"
    if assets.is_dir() and not assets.is_symlink():
        count = sum(
            1 for path in assets.iterdir()
            if not path.is_symlink() and path.is_file()
            and COPILOT_HOOK_ASSET_MARKER in _read_prefix(path)
        )
        if count:
            found.append((f"Managed: {assets} ({count} Copilot hook assets)", "copilot-assets"))
    return found


def _remove_copilot(surface: CopilotSurface) -> None:
    root = surface.customization_root
    trusted_root = root.parent
    if _strip_instruction_file(
        surface.instructions,
        preserve_plugins=False,
        trusted_root=trusted_root,
    ):
        print(f"  Stripped: {surface.instructions} (user content preserved)")
    for directory_name, suffix, label in (
        ("instructions", ".instructions.md", "instruction"),
        ("agents", ".agent.md", "agent"),
        ("prompts", ".prompt.md", "prompt"),
    ):
        directory = root / directory_name
        removed = 0
        if directory.is_dir() and not directory.is_symlink():
            for path in sorted(directory.glob(f"*{suffix}")):
                if _is_copilot_file(path):
                    if not _is_copilot_file(path):
                        raise RuntimeError(f"Managed Copilot file changed before removal: {path}")
                    _safe_unlink(path, trusted_root)
                    removed += 1
            _prune_empty(directory, trusted_root=trusted_root)
        if removed:
            print(f"  Removed: {removed} managed Copilot {label}(s)")
    skills = root / "skills"
    removed_skills = 0
    if skills.is_dir() and not skills.is_symlink():
        for skill in sorted(skills.iterdir()):
            if _remove_copilot_skill(skill, trusted_root):
                removed_skills += 1
        _prune_empty(skills, trusted_root=trusted_root)
    if removed_skills:
        print(f"  Removed: {removed_skills} managed Copilot skill(s)")
    hooks_dir = root / "hooks"
    removed_hooks = _remove_copilot_hooks(
        hooks_dir / "ai-toolkit.json",
        trusted_root,
    )
    if removed_hooks:
        print(f"  Removed: {removed_hooks} managed Copilot hook(s)")
    removed_assets = _remove_marked_assets(
        hooks_dir / "ai-toolkit",
        COPILOT_HOOK_ASSET_MARKER,
        trusted_root,
    )
    if removed_assets:
        print(f"  Removed: {removed_assets} managed Copilot hook asset(s)")
    _prune_empty(hooks_dir, root, trusted_root=trusted_root)


# ---------------------------------------------------------------------------
# Scope resolution, safety preflight, CLI
# ---------------------------------------------------------------------------

def _discover_recovery(sessions_root: Path) -> list[tuple[str, str]]:
    try:
        os.lstat(sessions_root)
    except FileNotFoundError:
        return []
    artifact_count = count_owned_recovery_artifacts(sessions_root)
    if artifact_count == 0:
        return []
    noun = "artifact" if artifact_count == 1 else "artifacts"
    return [
        (
            "Recovery: sessions/*/output-filter "
            f"({artifact_count} owned {noun}) under {sessions_root}",
            "output-filter-recovery",
        )
    ]


def _remove_recovery(sessions_root: Path) -> None:
    """Remove owned recovery last so its failure rolls back other surfaces."""
    try:
        removed = clean_owned_recovery_tree(sessions_root)
    except OSError as error:
        raise RuntimeError(
            "output-filter recovery cleanup failed; an I/O fault after "
            "preflight may have left recovery cleanup partial"
        ) from error
    print(f"  Removed: {removed} output-filter recovery file(s)")


# ---------------------------------------------------------------------------
# Toolkit data directory (~/.softspark/ai-toolkit) and registered projects
# ---------------------------------------------------------------------------

def _data_dir(target: Path, scope: str) -> Path | None:
    """Resolve the toolkit data directory the way ``paths.py`` does."""
    if scope == "local":
        return None
    fallback = target / ".softspark" / "ai-toolkit"
    if scope != "global":
        return fallback
    configured = os.environ.get("AI_TOOLKIT_HOME")
    if configured:
        return _configured_home("AI_TOOLKIT_HOME", fallback, strict_absolute=True)
    softspark = _configured_home("SOFTSPARK_HOME", target / ".softspark", strict_absolute=True)
    return softspark / "ai-toolkit"


def _data_files(data_dir: Path) -> list[Path]:
    """Every entry below ``data_dir``, without following symlinks."""
    entries: list[Path] = []
    for root, directories, files in os.walk(data_dir, followlinks=False):
        base = Path(root)
        entries.extend(base / name for name in (*directories, *files))
    return entries


def _discover_data_dir(data_dir: Path | None) -> list[tuple[str, str]]:
    if data_dir is None or not data_dir.is_dir() or data_dir.is_symlink():
        return []
    count = len(_data_files(data_dir))
    return [(
        f"Data: {data_dir} ({count} entries: hook scripts, state, session history, "
        "logs, plugins; archived before removal)",
        "data-dir",
    )]


def _archive_data_dir(data_dir: Path, target: Path) -> Path:
    """Write and verify a ``tar.gz`` of the whole data directory."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    archive = target / f"ai-toolkit-backup-{stamp}.tar.gz"
    suffix = 1
    while archive.exists() or archive.is_symlink():
        archive = target / f"ai-toolkit-backup-{stamp}-{suffix}.tar.gz"
        suffix += 1
    expected = {
        (Path(data_dir.name) / path.relative_to(data_dir)).as_posix()
        for path in _data_files(data_dir)
    } | {data_dir.name}
    with tarfile.open(archive, "x:gz", dereference=False) as bundle:
        bundle.add(data_dir, arcname=data_dir.name, recursive=True)
    os.chmod(archive, 0o600)
    with tarfile.open(archive, "r:gz") as bundle:
        archived = set(bundle.getnames())
    missing = expected - archived
    if missing:
        raise RuntimeError(
            f"backup {archive} is missing {len(missing)} entr(y/ies), "
            f"e.g. {sorted(missing)[0]}; nothing was removed from {data_dir}"
        )
    return archive


def _remove_tree(root: Path, trusted_root: Path) -> None:
    """Delete ``root`` bottom-up; symlinks are unlinked, never followed."""
    for current, directories, files in os.walk(root, topdown=False, followlinks=False):
        base = Path(current)
        for name in files:
            _safe_unlink(base / name, trusted_root)
        for name in directories:
            path = base / name
            if path.is_symlink():
                _safe_unlink(path, trusted_root)
            else:
                _safe_rmdir(path, trusted_root)
    _safe_rmdir(root, trusted_root)


def _remove_data_dir(data_dir: Path, target: Path) -> None:
    trusted_root = data_dir.parent
    archive = _archive_data_dir(data_dir, target)
    print(f"  Archived: {data_dir} -> {archive}")
    try:
        _remove_tree(data_dir, trusted_root)
    except (OSError, RuntimeError) as error:
        raise RuntimeError(
            f"data directory removal failed ({error}); restore it from {archive}"
        ) from error
    print(f"  Removed: {data_dir}")
    if trusted_root.name == ".softspark":
        # Shared with other SoftSpark tools; removed only when nothing is left.
        _prune_empty(trusted_root, trusted_root=trusted_root.parent)


def _registered_projects(data_dir: Path | None, target: Path) -> list[Path]:
    """Registered project roots that still exist, excluding the home itself."""
    if data_dir is None:
        return []
    registry = _load_json(data_dir / "projects.json", "project registry")
    entries = registry.get("projects", []) if registry is not None else []
    projects: list[Path] = []
    for entry in entries if isinstance(entries, list) else []:
        raw = entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(raw, str) or not raw:
            continue
        path = Path(raw)
        if (
            path.is_absolute()
            and path.is_dir()
            and not path.is_symlink()
            and _lexical_absolute(path) != _lexical_absolute(target)
        ):
            projects.append(path)
    return sorted(set(projects))


# ---------------------------------------------------------------------------
# Project-local files outside .claude/
# ---------------------------------------------------------------------------

PRE_COMMIT_MARKER = "ai-toolkit fallback pre-commit hook"
GENERATED_PROJECT_FILES = (".softspark-toolkit.lock.json", ".softspark-toolkit-extends.json")
_CONSTITUTION_IMPORT_LINES = ("## Project Constitution", "@.claude/constitution.md")


def _pre_commit_hook(target: Path) -> Path | None:
    hook = target / ".git" / "hooks" / "pre-commit"
    return hook if _has_marker(hook, PRE_COMMIT_MARKER, lines=3) else None


def _without_constitution_import(text: str) -> str:
    kept = [line for line in text.splitlines() if line.strip() not in _CONSTITUTION_IMPORT_LINES]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip() + "\n"


def _project_claude_md_update(target: Path) -> tuple[Path, str | None] | None:
    """Root ``CLAUDE.md`` after removing what the toolkit put there.

    Returns ``(path, None)`` when the file is an untouched template, the new
    text when only the constitution import has to go, and ``None`` otherwise.
    """
    path = target / "CLAUDE.md"
    if path.is_symlink() or not path.is_file():
        return None
    original = path.read_text(encoding="utf-8")
    if (target / ".claude" / "constitution.md").is_file() and "<!-- TOOLKIT:" not in (
        (target / ".claude" / "constitution.md").read_text(encoding="utf-8")
    ):
        return None  # project-owned constitution text still needs its import
    updated = _without_constitution_import(original)
    template = app_dir / "CLAUDE.md.template"
    if template.is_file() and updated == _without_constitution_import(
        template.read_text(encoding="utf-8")
    ):
        return path, None
    if updated.strip() != original.strip():
        return path, updated
    return None


def _default_settings_local(path: Path) -> bool:
    data = _load_json(path, "project settings.local.json")
    if data is None:
        return False
    defaults = _load_json(app_dir / "mcp-defaults.json", "MCP defaults")
    return data in ({"mcpServers": {}, "env": {}}, defaults)


def _discover_project_files(target: Path) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for name in GENERATED_PROJECT_FILES:
        path = target / name
        if path.is_file() and not path.is_symlink():
            found.append((f"Generated: {name}", "project-file"))
    if _pre_commit_hook(target) is not None:
        found.append(("Installed: .git/hooks/pre-commit (toolkit fallback)", "pre-commit"))
    update = _project_claude_md_update(target)
    if update is not None:
        what = "unchanged template" if update[1] is None else "constitution import"
        found.append((f"Generated: CLAUDE.md ({what})", "project-claude-md"))
    if _default_settings_local(target / ".claude" / "settings.local.json"):
        found.append(("Generated: .claude/settings.local.json (unchanged defaults)", "settings-local"))
    return found


def _remove_project_files(target: Path) -> None:
    for name in GENERATED_PROJECT_FILES:
        path = target / name
        if path.is_file() and not path.is_symlink():
            _safe_unlink(path, target)
            print(f"  Removed: {name}")
    hook = _pre_commit_hook(target)
    if hook is not None:
        _safe_unlink(hook, target)
        backup = hook.with_name("pre-commit.backup")
        if backup.is_file() and not backup.is_symlink():
            with _open_mutation_parent(hook, target) as (parent_fd, _):
                os.rename(backup.name, hook.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            print("  Restored: .git/hooks/pre-commit from pre-commit.backup")
        else:
            print("  Removed: .git/hooks/pre-commit (toolkit fallback)")
    update = _project_claude_md_update(target)
    if update is not None:
        path, text = update
        if text is None:
            _safe_unlink(path, target)
            print("  Removed: CLAUDE.md (unchanged toolkit template)")
        else:
            _atomic_write_text(path, text, target)
            print("  Stripped: CLAUDE.md (constitution import; user content preserved)")
    settings_local = target / ".claude" / "settings.local.json"
    if _default_settings_local(settings_local):
        _safe_unlink(settings_local, target)
        print("  Removed: .claude/settings.local.json (unchanged defaults)")
        _prune_empty(target / ".claude", trusted_root=target)


def _configured_home(env_name: str, fallback: Path, *, strict_absolute: bool) -> Path:
    value = os.environ.get(env_name)
    if not value:
        return fallback
    path = Path(value).expanduser()
    if strict_absolute and not path.is_absolute():
        raise RuntimeError(f"{env_name} must be an absolute path")
    return path.absolute()


def _surface_roots(
    target: Path,
    scope: str,
) -> tuple[Path, list[CodexSurface], list[CopilotSurface]]:
    claude = target / ".claude"
    codex: list[CodexSurface] = []
    copilot: list[CopilotSurface] = []

    if scope in {"local", "both"}:
        codex.append(CodexSurface(
            target / ".codex",
            target / "AGENTS.md",
            target / ".agents" / "skills",
            target / ".codex" / "hooks",
        ))
        github = target / ".github"
        copilot.append(CopilotSurface(github, github / "copilot-instructions.md"))

    if scope in {"global", "both"}:
        use_environment = scope == "global"
        codex_root = (
            _configured_home("CODEX_HOME", target / ".codex", strict_absolute=True)
            if use_environment else target / ".codex"
        )
        codex.append(CodexSurface(
            codex_root,
            codex_root / "AGENTS.md",
            target / ".agents" / "skills",
            codex_root / "ai-toolkit-hooks",
        ))
        copilot_root = (
            _configured_home("COPILOT_HOME", target / ".copilot", strict_absolute=False)
            if use_environment else target / ".copilot"
        )
        copilot.append(CopilotSurface(
            copilot_root,
            copilot_root / "copilot-instructions.md",
        ))

    return claude, list(dict.fromkeys(codex)), list(dict.fromkeys(copilot))


def _assert_regular_root(path: Path, label: str) -> None:
    if path.is_symlink():
        raise RuntimeError(f"Refusing symlinked {label}: {path}")


def _preflight(
    target: Path,
    claude: Path,
    codex: list[CodexSurface],
    copilot: list[CopilotSurface],
) -> None:
    _assert_regular_root(target, "uninstall target")
    _assert_regular_root(claude, "Claude configuration root")
    for surface in codex:
        for path, label in (
            (surface.config_root, "Codex configuration root"),
            (surface.instructions, "Codex instruction file"),
            (surface.config_root / "agents", "Codex agents directory"),
            (surface.config_root / "hooks.json", "Codex hooks file"),
            (surface.assets_root, "Codex hook assets directory"),
            (surface.skills_root.parent, "Codex shared agents directory"),
            (surface.skills_root, "Codex skills directory"),
        ):
            _assert_regular_root(path, label)
    for surface in copilot:
        root = surface.customization_root
        for path, label in (
            (root, "Copilot customization root"),
            (surface.instructions, "Copilot instruction file"),
            (root / "instructions", "Copilot instructions directory"),
            (root / "agents", "Copilot agents directory"),
            (root / "prompts", "Copilot prompts directory"),
            (root / "skills", "Copilot skills directory"),
            (root / "hooks", "Copilot hooks directory"),
            (root / "hooks" / "ai-toolkit.json", "Copilot hooks file"),
            (root / "hooks" / "ai-toolkit", "Copilot hook assets directory"),
        ):
            _assert_regular_root(path, label)


def _transaction_specs(
    claude: Path,
    codex: list[CodexSurface],
    copilot: list[CopilotSurface],
    *,
    target: Path,
    scope: str,
) -> list[tuple[Path, bool, Path]]:
    specs: dict[Path, tuple[bool, Path]] = {}

    def add(path: Path, recursive: bool, trusted_root: Path) -> None:
        existing = specs.get(path)
        if existing is not None and existing[1] != trusted_root:
            raise RuntimeError(
                f"Conflicting trusted roots for transaction path {path}: "
                f"{existing[1]} and {trusted_root}"
            )
        specs[path] = (recursive or (existing[0] if existing else False), trusted_root)

    claude_boundary = claude.parent
    for path, recursive in (
        (claude / "agents", True),
        (claude / "skills", True),
        (claude / "commands", True),
        (claude / "hooks.json", False),
        (claude / "settings.json", False),
        (claude / "output-styles", True),
        (claude / "constitution.md", False),
        (claude / "ARCHITECTURE.md", False),
        (claude / "rules", True),
        (claude / "CLAUDE.md", False),
        (claude / "settings.local.json", False),
        (claude / _OUTPUT_FILTER_POLICY_NAME, False),
        (claude / _OUTPUT_FILTER_OWNER_NAME, False),
    ):
        add(path, recursive, claude_boundary)
    for surface in codex:
        config_boundary = surface.config_root.parent
        skills_boundary = surface.skills_root.parent.parent
        for path, recursive, trusted_root in (
            (surface.config_root, False, config_boundary),
            (surface.instructions, False, surface.instructions.parent),
            (surface.config_root / "agents", True, config_boundary),
            (surface.config_root / "hooks.json", False, config_boundary),
            (surface.assets_root, True, config_boundary),
            (surface.skills_root.parent, False, skills_boundary),
            (
                surface.skills_root.parent / SKILL_SURFACE_OWNERS_MARKER,
                False,
                skills_boundary,
            ),
            (surface.skills_root, True, skills_boundary),
        ):
            add(path, recursive, trusted_root)
    for surface in copilot:
        root = surface.customization_root
        trusted_root = root.parent
        for path, recursive in (
            (root, False),
            (surface.instructions, False),
            (root / "instructions", True),
            (root / "agents", True),
            (root / "prompts", True),
            (root / "skills", True),
            (root / "hooks", True),
        ):
            add(path, recursive, trusted_root)
    if scope in {"local", "both"}:
        hooks_dir = target / ".git" / "hooks"
        for path in (
            target / "CLAUDE.md",
            hooks_dir / "pre-commit",
            hooks_dir / "pre-commit.backup",
            *(target / name for name in GENERATED_PROJECT_FILES),
        ):
            add(path, False, target)
    for config_root in _opencode_config_roots(target, scope):
        root = config_root if config_root is not None else target / ".opencode"
        add(root / "skills", True, target)
    for root in _cline_transaction_roots(target, scope):
        add(root, True, target)
    return [
        (path, recursive, trusted_root)
        for path, (recursive, trusted_root) in specs.items()
    ]


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Remove everything ai-toolkit installed: Claude Code and editor "
            "surfaces, settings it wrote, and (global) every registered "
            "project plus the toolkit data directory, archived first. "
            "User-owned content in shared files is preserved."
        ),
        epilog=(
            "Global Codex and Copilot locations honor CODEX_HOME and "
            "COPILOT_HOME. A legacy positional target scans local and "
            "home-style paths below that directory."
        ),
    )
    parser.add_argument("legacy_target", nargs="?", type=Path, metavar="target-dir")
    parser.add_argument("--target", type=Path, help="explicit home or project root")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--local", action="store_true", help="remove project-local surfaces")
    scope.add_argument("--global", dest="global_scope", action="store_true", help="remove user-level surfaces")
    parser.add_argument("--yes", "-y", action="store_true", help="skip confirmation")
    args = parser.parse_args(argv)
    if args.target is not None and args.legacy_target is not None:
        parser.error("use either --target DIR or the positional target-dir, not both")
    return args


def _opencode_config_roots(target: Path, scope: str) -> list[Path | None]:
    roots: list[Path | None] = []
    if scope in {"local", "both"}:
        roots.append(None)
    if scope in {"global", "both"}:
        roots.append(target / ".config" / "opencode")
    return roots


def _cline_transaction_roots(target: Path, scope: str) -> list[Path]:
    roots = {target / ".cline" / "skills"}
    if scope in {"local", "both"}:
        roots.update(
            {
                target / ".cline" / "rules",
                target / ".cline" / "hooks",
                target / ".clinerules",
            }
        )
    if scope in {"global", "both"}:
        roots.update(
            {
                target / ".cline" / "rules",
                target / ".cline" / "hooks",
                target / "Documents" / "Cline" / "Rules",
                target / "Documents" / "Cline" / "Hooks",
            }
        )
    return sorted(roots)


def _discover_opencode_skills(
    target: Path,
    scope: str,
) -> list[tuple[str, str]]:
    from generate_opencode_skills import discover

    found: list[tuple[str, str]] = []
    for config_root in _opencode_config_roots(target, scope):
        count = discover(target, config_root=config_root)
        if count:
            location = config_root or target / ".opencode"
            found.append(
                (f"Managed: {location / 'skills'} ({count} OpenCode skills)",
                 "opencode-skills")
            )
    return found


def _discover_cline_surfaces(target: Path, scope: str) -> list[tuple[str, str]]:
    from generate_cline_hooks import discover as discover_cline_hooks
    from generate_cline_rules import managed_files as managed_cline_rules
    from generate_cline_skills import discover as discover_cline_skills

    count = 0
    if scope in {"local", "both"}:
        count += len(managed_cline_rules(target))
        count += discover_cline_hooks(target)
    if scope in {"global", "both"}:
        global_rules = (
            target / ".cline" / "rules",
            target / "Documents" / "Cline" / "Rules",
        )
        count += len(
            managed_cline_rules(
                target,
                output_roots=global_rules,
                include_workflows=False,
            )
        )
        if scope == "global":
            count += discover_cline_hooks(
                target,
                hooks_root=target / ".cline" / "hooks",
            )
        count += discover_cline_hooks(
            target,
            hooks_root=target / "Documents" / "Cline" / "Hooks",
        )
    count += discover_cline_skills(target)
    if not count:
        return []
    return [(f"Managed: Cline native surfaces ({count} artifacts)", "cline")]


def _cleanup_cline_surfaces(target: Path, scope: str) -> None:
    from generate_cline_hooks import cleanup as cleanup_cline_hooks
    from generate_cline_rules import cleanup as cleanup_cline_rules
    from generate_cline_skills import cleanup as cleanup_cline_skills

    if scope in {"local", "both"}:
        cleanup_cline_rules(target)
        cleanup_cline_hooks(target)
    if scope in {"global", "both"}:
        global_rule_roots = [target / "Documents" / "Cline" / "Rules"]
        if scope == "global":
            global_rule_roots.insert(0, target / ".cline" / "rules")
        cleanup_cline_rules(
            target,
            output_roots=tuple(global_rule_roots),
            include_workflows=False,
        )
        if scope == "global":
            cleanup_cline_hooks(
                target,
                hooks_root=target / ".cline" / "hooks",
            )
        cleanup_cline_hooks(
            target,
            hooks_root=target / "Documents" / "Cline" / "Hooks",
        )
    cleanup_cline_skills(target)


_LOCAL_EDITOR_SURFACES: tuple[tuple[str, str, dict[str, Any]], ...] = (
    ("Cursor rules", "generate_cursor_rules", {}),
    ("Cursor rule files", "generate_cursor_mdc", {}),
    ("Cursor agents", "generate_cursor_agents", {}),
    ("Cursor skills", "generate_cursor_skills", {}),
    ("Cursor hooks", "generate_cursor_hooks", {}),
    ("Windsurf rules", "generate_windsurf", {"scope": "local"}),
    ("Windsurf/Devin rule files", "generate_windsurf_rules", {}),
    ("Windsurf skills", "generate_windsurf_skills", {"scope": "local"}),
    ("Devin hooks", "generate_devin_hooks", {}),
    ("Gemini instructions", "generate_gemini", {}),
    ("Gemini commands", "generate_gemini_commands", {}),
    ("Gemini skills", "generate_gemini_skills", {}),
    ("Gemini agents", "generate_gemini_agents", {}),
    ("Gemini hooks", "generate_gemini_hooks", {}),
    ("Antigravity rules", "generate_antigravity", {}),
    ("Antigravity hooks", "generate_antigravity_hooks", {}),
    ("Antigravity agents", "generate_antigravity_agents", {}),
    ("Augment instructions", "generate_augment", {}),
    ("Augment rule files", "generate_augment_rules", {}),
    ("Augment agents", "generate_augment_agents", {}),
    ("Augment commands", "generate_augment_commands", {}),
    ("Augment skills", "generate_augment_skills", {}),
    ("OpenCode agents", "generate_opencode_agents", {}),
    ("OpenCode commands", "generate_opencode_commands", {}),
    ("OpenCode plugin", "generate_opencode_plugin", {}),
    ("OpenCode config", "generate_opencode_json", {}),
    ("OpenCode instructions", "generate_opencode", {}),
    ("Roo rules", "generate_roo_rules", {}),
    ("Roo modes", "generate_roo_modes", {}),
    ("Aider config", "generate_aider_conf", {}),
    ("Aider conventions", "generate_conventions", {}),
)


def _global_editor_surfaces(home: Path) -> tuple[tuple[str, str, dict[str, Any]], ...]:
    opencode = home / ".config" / "opencode"
    return (
        ("Cursor hooks", "generate_cursor_hooks", {}),
        ("Windsurf/Devin global rules", "generate_windsurf", {"scope": "global"}),
        ("Windsurf skills", "generate_windsurf_skills", {"scope": "global"}),
        ("Gemini instructions", "generate_gemini", {"global_install": True}),
        ("Gemini commands", "generate_gemini_commands", {}),
        ("Gemini skills", "generate_gemini_skills", {}),
        ("Gemini agents", "generate_gemini_agents", {}),
        ("Gemini hooks", "generate_gemini_hooks", {}),
        ("Antigravity skills", "generate_antigravity", {"global_install": True}),
        ("Antigravity hooks", "generate_antigravity_hooks", {"global_install": True}),
        ("Antigravity agents", "generate_antigravity_agents",
         {"config_root": home / ".gemini" / "config"}),
        ("Augment instructions", "generate_augment", {}),
        ("Augment agents", "generate_augment_agents", {}),
        ("Augment commands", "generate_augment_commands", {}),
        ("Augment hooks", "generate_augment_hooks", {}),
        ("OpenCode agents", "generate_opencode_agents", {"config_root": opencode}),
        ("OpenCode commands", "generate_opencode_commands", {"config_root": opencode}),
        ("OpenCode plugin", "generate_opencode_plugin", {"config_root": opencode}),
        ("OpenCode config", "generate_opencode_json",
         {"output_path": opencode / "opencode.json"}),
        ("OpenCode instructions", "generate_opencode", {"config_root": opencode}),
        ("Roo rules", "generate_roo_rules", {"output_root": home / ".roo" / "rules"}),
        ("Aider config", "generate_aider_conf", {}),
        ("Aider conventions", "generate_conventions", {"global_install": True}),
    )


def _editor_surfaces(target: Path, scope: str) -> list[tuple[str, str, dict[str, Any]]]:
    """``(label, generator module, kwargs)`` for each editor surface to clean.

    Each generator owns its ``discover``/``cleanup`` pair and the ownership
    rule behind it (markers, generated headers, ``ai-toolkit-`` prefixes).
    Augment hooks are cleaned at global scope only: a local install writes
    them into the shared ``~/.augment/settings.json``.
    """
    surfaces: list[tuple[str, str, dict[str, Any]]] = []
    if scope in {"local", "both"}:
        surfaces.extend(_LOCAL_EDITOR_SURFACES)
    if scope in {"global", "both"}:
        surfaces.extend(_global_editor_surfaces(target))
    unique: dict[tuple[str, str], tuple[str, str, dict[str, Any]]] = {}
    for label, module, kwargs in surfaces:
        unique.setdefault((module, repr(sorted(kwargs.items()))), (label, module, kwargs))
    return list(unique.values())


def _discover_editor_surfaces(
    target: Path,
    scope: str,
) -> tuple[list[tuple[str, str]], list[str]]:
    found: list[tuple[str, str]] = []
    warnings: list[str] = []
    for label, module_name, kwargs in _editor_surfaces(target, scope):
        try:
            count = importlib.import_module(module_name).discover(target, **kwargs)
        except (OSError, RuntimeError, ValueError) as error:
            warnings.append(f"{label}: {error}")
            continue
        if count:
            found.append((f"Managed: {label} ({count})", "editor"))
    return found, warnings


def _mcp_template_home(target: Path) -> Path | None:
    """``None`` lets mcp_editors honor CODEX_HOME/COPILOT_HOME for the real home."""
    return None if _lexical_absolute(target) == _lexical_absolute(Path.home()) else target


def _recorded_mcp_templates(data_dir: Path | None) -> list[str]:
    state = _load_json(data_dir / "state.json", "toolkit state") if data_dir else None
    names = state.get("mcp_templates", []) if state is not None else []
    return [name for name in names if isinstance(name, str)] if isinstance(names, list) else []


def _discover_mcp_templates(target: Path, data_dir: Path | None) -> list[tuple[str, str]]:
    names = _recorded_mcp_templates(data_dir)
    if not names:
        return []
    from mcp_editors import discover_template_servers

    count = discover_template_servers(names, home=_mcp_template_home(target))
    return [(f"Merged: MCP servers from templates {', '.join(names)} ({count})", "mcp")] if count else []


def _remove_mcp_templates(target: Path, data_dir: Path | None) -> None:
    names = _recorded_mcp_templates(data_dir)
    if not names:
        return
    from mcp_editors import cleanup_template_servers

    removed = cleanup_template_servers(names, home=_mcp_template_home(target))
    if removed:
        print(f"  Removed: {removed} MCP server entr(y/ies) from templates {', '.join(names)}")


_INJECTED_SOURCES = (
    ("inject-hook hooks", "inject_hook_cli"),
    ("inject-mcp servers", "inject_mcp_cli"),
)


def _discover_plugins(data_dir: Path | None) -> tuple[list[tuple[str, str]], list[str]]:
    """Plugin packs installed with ``ai-toolkit plugin install``.

    Their hooks, rules, sections and scripts are tracked in the data
    directory, so they are removed through the plugin lifecycle before it goes.
    """
    if data_dir is None or not data_dir.is_dir():
        return [], []
    from plugin import discover_installed

    try:
        count = discover_installed(data_dir)
    except ValueError as error:
        return [], [f"plugin packs: {error}"]
    return ([(f"Installed: plugin packs ({count} pack/runtime pairs)", "plugins")]
            if count else []), []


def _remove_plugins(plan: _Plan) -> None:
    if not any(kind == "plugins" for _, kind in plan.components) or plan.data_dir is None:
        return
    from plugin import remove_all_installed

    removed = remove_all_installed(plan.data_dir)
    print(f"  Removed: {removed} plugin pack/runtime pair(s)")


def _discover_injected(target: Path, data_dir: Path | None) -> list[tuple[str, str]]:
    """Entries added by ``inject-hook``/``inject-mcp``, whose registry lives in
    the data directory: once that is gone, ``remove-*`` can no longer reach them."""
    if data_dir is None or not data_dir.is_dir():
        return []
    found: list[tuple[str, str]] = []
    for label, module_name in _INJECTED_SOURCES:
        count = importlib.import_module(module_name).discover_injected(target, data_dir)
        if count:
            found.append((f"Injected: {label} ({count})", "injected"))
    return found


def _remove_injected(target: Path, data_dir: Path | None) -> None:
    if data_dir is None or not data_dir.is_dir():
        return
    for label, module_name in _INJECTED_SOURCES:
        removed = importlib.import_module(module_name).cleanup_injected(target, data_dir)
        if removed:
            print(f"  Removed: {removed} {label}")


def _remove_editor_managed_surfaces(target: Path, scope: str) -> None:
    """Strip every managed editor surface outside the Codex/Copilot roots.

    Editor cleanup is best effort: a surface that cannot be cleaned safely
    (for example behind a symlinked root) is reported and left in place.
    Cline cleanup is transactional and fail-closed so the outer uninstall can
    roll every managed Cline root back after a partial failure.
    """
    from generate_opencode_skills import cleanup as cleanup_opencode_skills

    # Skills first, so the later OpenCode passes can prune an emptied root.
    for config_root in _opencode_config_roots(target, scope):
        try:
            cleanup_opencode_skills(target, config_root=config_root)
        except (OSError, RuntimeError, ValueError) as error:
            print(f"  WARN could not clean OpenCode skills: {error}")
        else:
            print("  Cleaned: OpenCode skills")

    for label, module_name, kwargs in _editor_surfaces(target, scope):
        try:
            removed = importlib.import_module(module_name).cleanup(target, **kwargs)
        except (ImportError, OSError, RuntimeError, ValueError) as error:
            print(f"  WARN could not clean {label}: {error}")
        else:
            if removed:
                print(f"  Cleaned: {label} ({removed})")

    _cleanup_cline_surfaces(target, scope)
    cline_documents = target / "Documents" / "Cline"
    _prune_empty(
        *(target / ".cline" / name for name in ("hooks", "rules", "skills")),
        target / ".cline",
        *(target / ".clinerules" / name for name in ("hooks", "workflows")),
        target / ".clinerules",
        cline_documents / "Hooks",
        cline_documents / "Rules",
        cline_documents,
        trusted_root=target,
    )
    print("  Cleaned: Cline native surfaces")


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    explicit_target = args.target or args.legacy_target
    if args.local:
        scope = "local"
        target = explicit_target or Path.cwd()
    elif args.global_scope:
        scope = "global"
        target = explicit_target or Path.home()
    elif explicit_target is not None:
        scope = "both"
        target = explicit_target
    else:
        scope = "global"
        target = Path.home()
    target = target.expanduser().absolute()

    if not target.is_dir():
        print(f"Error: uninstall target is not a directory: {target}", file=sys.stderr)
        raise SystemExit(1)

    try:
        plan = _plan(target, scope)
        project_plans = [
            _plan(project, "local")
            for project in (
                _registered_projects(plan.data_dir, target) if scope == "global" else []
            )
        ]
    except (OSError, RuntimeError, UnicodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print("AI Toolkit Uninstaller")
    print("======================")
    print(f"Target: {target} ({scope})")
    print()
    for description, _ in plan.components:
        print(f"  {description}")
    for project_plan in project_plans:
        if project_plan.components:
            print()
            print(f"Registered project: {project_plan.target} (local)")
            for description, _ in project_plan.components:
                print(f"  {description}")
    warnings = [w for p in (plan, *project_plans) for w in p.warnings]
    if warnings:
        print()
        print("Cannot be cleaned safely, left in place:")
        for warning in warnings:
            print(f"  WARN {warning}")

    total = len(plan.components) + sum(len(p.components) for p in project_plans)
    if not total:
        print("No toolkit components found. Nothing to remove.")
        if scope == "local":
            _unregister_project(target)
        return

    print()
    print(f"Found {total} managed component group(s).")
    print("User-owned files, handlers, skills, and plugin-owned Codex hooks are preserved.")
    if plan.data_dir is not None and plan.data_dir.is_dir():
        print(f"The data directory is archived to {target}/ai-toolkit-backup-<time>.tar.gz first.")
    print()
    if not args.yes:
        try:
            response = input("Remove these components? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return
        if response not in {"y", "yes"}:
            print("Cancelled.")
            return

    try:
        _require_secure_mutation_support()
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    # Projects first: a project failure stops before the global install, the
    # registry, and the data directory are touched.
    for project_plan in project_plans:
        if project_plan.components:
            print()
            print(f"Project: {project_plan.target}")
            _execute(project_plan)
    if project_plans:
        print()
    _execute(plan)
    if scope == "local":
        _unregister_project(target)

    print()
    print("Managed toolkit components removed successfully.")
    print("To reinstall: npm install -g @softspark/ai-toolkit && ai-toolkit install")


@dataclass
class _Plan:
    target: Path
    scope: str
    claude: Path
    codex: list[CodexSurface]
    copilot: list[CopilotSurface]
    components: list[tuple[str, str]]
    managed_overrides: set[str]
    recovery_root: Path | None
    recovery_components: list[tuple[str, str]]
    data_dir: Path | None
    warnings: list[str]


def _plan(target: Path, scope: str) -> _Plan:
    """Discover everything one target holds, without changing anything."""
    claude, codex, copilot = _surface_roots(target, scope)
    _preflight(target, claude, codex, copilot)
    data_dir = _data_dir(target, scope)
    if data_dir is not None:
        _assert_regular_root(data_dir, "toolkit data directory")
    managed_overrides = _managed_skill_overrides(data_dir)
    components = discover_components(claude, managed_overrides)
    for surface in codex:
        components.extend(_discover_codex(surface))
    for surface in copilot:
        components.extend(_discover_copilot(surface))
    components.extend(_discover_opencode_skills(target, scope))
    components.extend(_discover_cline_surfaces(target, scope))
    editor_components, warnings = _discover_editor_surfaces(target, scope)
    components.extend(editor_components)
    components.extend(_discover_mcp_templates(target, data_dir))
    components.extend(_discover_injected(target, data_dir))
    plugin_components, plugin_warnings = _discover_plugins(data_dir)
    components.extend(plugin_components)
    warnings.extend(plugin_warnings)
    if scope in {"local", "both"}:
        components.extend(_discover_project_files(target))
    recovery_root = data_dir / "sessions" if data_dir is not None else None
    recovery_components = (
        _discover_recovery(recovery_root) if recovery_root is not None else []
    )
    components.extend(recovery_components)
    components.extend(_discover_data_dir(data_dir))
    return _Plan(
        target, scope, claude, codex, copilot, components,
        managed_overrides, recovery_root, recovery_components, data_dir, warnings,
    )


def _execute(plan: _Plan) -> None:
    """Apply one plan in its own rollback transaction; exit 1 on failure."""
    target, claude = plan.target, plan.claude
    transaction: _UninstallTransaction | None = None
    try:
        transaction = _UninstallTransaction(
            _transaction_specs(
                claude,
                plan.codex,
                plan.copilot,
                target=target,
                scope=plan.scope,
            )
        )
        _preflight(target, claude, plan.codex, plan.copilot)
        # Before the toolkit settings pass, so a settings.json left holding
        # only toolkit keys is deleted instead of rewritten as ``{}``.
        _remove_plugins(plan)
        _remove_injected(target, plan.data_dir)
        remove_components(claude, target, plan.managed_overrides)
        for surface in plan.codex:
            _preflight(target, claude, [surface], [])
            _remove_codex(surface)
        for surface in plan.copilot:
            _preflight(target, claude, [], [surface])
            _remove_copilot(surface)
        _remove_editor_managed_surfaces(target, plan.scope)
        _remove_mcp_templates(target, plan.data_dir)
        if plan.scope in {"local", "both"}:
            _remove_project_files(target)
        if plan.recovery_root is not None and plan.recovery_components:
            # The recovery API preflights its complete tree before the first
            # unlink. A later I/O fault can still leave recovery partially
            # cleaned; the transaction restores every other runtime surface.
            _remove_recovery(plan.recovery_root)
        if plan.data_dir is not None and plan.data_dir.is_dir():
            # Last, and archived first: a failure here rolls back every other
            # surface, and the archive holds whatever was already deleted.
            _remove_data_dir(plan.data_dir, target)
    except (OSError, RuntimeError, tarfile.TarError) as error:
        rollback_error: RuntimeError | None = None
        if transaction is not None:
            try:
                transaction.rollback()
            except RuntimeError as failure:
                rollback_error = failure
        if rollback_error is not None:
            print(
                f"Error: uninstall stopped: {error}; {rollback_error}",
                file=sys.stderr,
            )
        else:
            print(f"Error: uninstall stopped and rolled back: {error}", file=sys.stderr)
        raise SystemExit(1) from error


def _unregister_project(target: Path) -> None:
    from paths import PROJECTS_FILE

    if not PROJECTS_FILE.is_file():
        return
    from install_steps.project_registry import unregister_project

    if unregister_project(target):
        print(f"  Unregistered: {target} from {PROJECTS_FILE}")


if __name__ == "__main__":
    main()
