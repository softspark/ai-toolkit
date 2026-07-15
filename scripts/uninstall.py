#!/usr/bin/env python3
"""Safely remove ai-toolkit-managed runtime customizations.

The default scope is the current user's global install. ``--local`` targets a
project, while an explicit legacy positional target scans both project and
home-style locations for backward compatibility. Only files, symlinks, JSON
handlers, and marker blocks with verifiable ai-toolkit ownership are removed.

Usage:
    python3 scripts/uninstall.py [--yes] [--local|--global] [--target DIR]
    python3 scripts/uninstall.py [--yes] [legacy-target-dir]
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import app_dir, toolkit_dir
from injection import strip_all_sections, strip_section, trim_trailing_blanks


CODEX_AGENT_MARKER = "# ai-toolkit-managed: codex-agent"
CODEX_ADAPTED_SKILL_MARKER = ".ai-toolkit-codex-adapted"
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


def _discover_claude_hooks(claude_dir: Path) -> list[tuple[str, str]]:
    hooks_file = claude_dir / "hooks.json"
    if hooks_file.is_symlink() and _is_toolkit_link(hooks_file):
        return [(f"Symlink: hooks.json -> {hooks_file.readlink()} (legacy)", "hooks-link")]
    if hooks_file.is_symlink() or not hooks_file.is_file():
        return []
    content = hooks_file.read_text(encoding="utf-8")
    if '"_source"' in content and '"ai-toolkit"' in content:
        return [("Merged: hooks.json (toolkit entries)", "hooks-merged")]
    return []


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


def discover_components(claude_dir: Path) -> list[tuple[str, str]]:
    """Find verifiably managed Claude Code components."""
    found = _discover_claude_link_directories(claude_dir)
    agent_links = _managed_links(claude_dir / "agents", "*.md")
    if agent_links:
        found.append((f"Symlinks: agents/ ({len(agent_links)} toolkit files)", "agent-link"))
    skill_links = _managed_links(claude_dir / "skills")
    if skill_links:
        found.append((f"Symlinks: skills/ ({len(skill_links)} toolkit directories)", "skill-link"))
    found.extend(_discover_claude_hooks(claude_dir))
    found.extend(_discover_claude_markers(claude_dir))
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


def _remove_claude_hooks(claude_dir: Path, trusted_root: Path) -> None:
    hooks_file = claude_dir / "hooks.json"
    if hooks_file.is_symlink() and _is_toolkit_link(hooks_file):
        _safe_unlink(hooks_file, trusted_root)
        print("  Removed: .claude/hooks.json (managed legacy symlink)")
    elif not hooks_file.is_symlink() and hooks_file.is_file():
        content = hooks_file.read_text(encoding="utf-8")
        if '"_source"' in content and '"ai-toolkit"' in content:
            merge_hooks = toolkit_dir / "scripts" / "merge-hooks.py"
            metadata = _safe_lstat(hooks_file, trusted_root)
            mode = stat.S_IMODE(metadata.st_mode) if metadata is not None else 0o644
            with tempfile.TemporaryDirectory(prefix="ai-toolkit-uninstall-") as directory:
                temporary = Path(directory) / "hooks.json"
                temporary.write_text(content, encoding="utf-8")
                subprocess.run(
                    ["python3", str(merge_hooks), "strip", str(temporary)],
                    check=True,
                )
                updated = temporary.read_bytes()
            _atomic_write_bytes(hooks_file, updated, mode, trusted_root)
            print("  Stripped: .claude/hooks.json (user hooks preserved)")


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


def remove_components(claude_dir: Path, trusted_root: Path) -> None:
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
    _remove_claude_hooks(claude_dir, trusted_root)
    _remove_claude_markers(claude_dir, trusted_root)


# ---------------------------------------------------------------------------
# Codex cleanup
# ---------------------------------------------------------------------------

def _is_codex_agent(path: Path) -> bool:
    return _has_marker(path, CODEX_AGENT_MARKER, lines=3)


def _is_codex_skill(path: Path) -> bool:
    if path.is_symlink():
        return _is_toolkit_link(path)
    marker = path / CODEX_ADAPTED_SKILL_MARKER
    return path.is_dir() and not marker.is_symlink() and marker.is_file()


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
            if child.name in {"SKILL.md", CODEX_ADAPTED_SKILL_MARKER}:
                if not child.is_symlink() and child.is_file():
                    _safe_unlink(child, trusted_root)
                continue
            if child.is_symlink() and _is_toolkit_link(child):
                _safe_unlink(child, trusted_root)
        _prune_empty(skill, trusted_root=trusted_root)
        removed += 1
    _prune_empty(skills_root, skills_root.parent, trusted_root=trusted_root)
    return removed


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
        (claude / "constitution.md", False),
        (claude / "ARCHITECTURE.md", False),
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
    return [
        (path, recursive, trusted_root)
        for path, (recursive, trusted_root) in specs.items()
    ]


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Remove only ai-toolkit-managed Claude, Codex, and Copilot "
            "customizations while preserving user-owned content."
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
        claude, codex, copilot = _surface_roots(target, scope)
        _preflight(target, claude, codex, copilot)
        components = discover_components(claude)
        for surface in codex:
            components.extend(_discover_codex(surface))
        for surface in copilot:
            components.extend(_discover_copilot(surface))
    except (OSError, RuntimeError, UnicodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print("AI Toolkit Uninstaller")
    print("======================")
    print(f"Target: {target} ({scope})")
    print()
    for description, _ in components:
        print(f"  {description}")

    if not components:
        print("No toolkit components found. Nothing to remove.")
        return

    print()
    print(f"Found {len(components)} managed component group(s).")
    print("User-owned files, handlers, skills, and plugin-owned Codex hooks are preserved.")
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

    transaction: _UninstallTransaction | None = None
    try:
        transaction = _UninstallTransaction(
            _transaction_specs(claude, codex, copilot)
        )
        _preflight(target, claude, codex, copilot)
        remove_components(claude, target)
        for surface in codex:
            _preflight(target, claude, [surface], [])
            _remove_codex(surface)
        for surface in copilot:
            _preflight(target, claude, [], [surface])
            _remove_copilot(surface)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
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

    print()
    print("Managed toolkit components removed successfully.")
    print("To reinstall: npm install -g @softspark/ai-toolkit && ai-toolkit install")


if __name__ == "__main__":
    main()
