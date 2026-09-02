#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Owned editor-native rule files for generic plugin runtimes."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path

from injection import markers_end, markers_start, trim_trailing_blanks


SAFE_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
MARKER_PATTERN = re.compile(
    r"<!-- TOOLKIT:(?P<section>[A-Za-z0-9][A-Za-z0-9._:-]*) "
    r"(?P<kind>START|END) -->"
)


@dataclass(frozen=True, slots=True)
class RuleFileUpdate:
    """One preflighted rule file replacement."""

    path: Path
    original: bytes | None
    content: bytes | None


@dataclass(frozen=True, slots=True)
class PluginRulePlan:
    """Preflighted native rule updates plus state ownership metadata."""

    updates: tuple[RuleFileUpdate, ...]
    ownership: dict | None
    installed: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    preserved: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OwnedMarkerSpan:
    """One unambiguous, balanced marker span in a Gemini context file."""

    start: int
    end: int
    block: str


def plugin_rule_source(plugin_name: str) -> str:
    """Return the stable ownership identifier for plugin rules."""
    _require_safe_name(plugin_name, "plugin")
    return f"ai-toolkit-plugin-{plugin_name}"


def prepare_plugin_rule_install(
    plugin_name: str,
    editor: str,
    rule_specs: list[dict],
    previous_ownership: dict | None,
) -> PluginRulePlan | None:
    """Preflight pack-owned rules for an editor's global native surface."""
    owned_specs = [spec for spec in rule_specs if not spec.get("is_core")]
    if not owned_specs:
        return None
    if editor == "gemini":
        return _prepare_gemini_install(
            plugin_name,
            owned_specs,
            previous_ownership,
        )
    if editor != "cursor":
        return None

    source = plugin_rule_source(plugin_name)
    previous_entries = _owned_entries(previous_ownership, source)
    updates: list[RuleFileUpdate] = []
    entries: dict[str, dict[str, str]] = {}
    installed: list[str] = []
    for spec in owned_specs:
        rule_name = _require_safe_name(spec.get("name"), "rule")
        source_path = Path(spec["source"])
        if source_path.is_symlink() or not source_path.is_file():
            raise RuntimeError(f"Refusing unsafe plugin rule source: {source_path}")
        path = (
            Path.home() / ".cursor" / "rules" / f"plugin-{plugin_name}-{rule_name}.mdc"
        )
        content = _render_cursor_rule(rule_name, source_path)
        original = _read_optional(path)
        previous = previous_entries.get(rule_name, {})
        if original is not None and not _matches_owned_file(path, original, previous):
            raise RuntimeError(f"Refusing user-owned plugin rule collision: {path}")
        updates.append(RuleFileUpdate(path=path, original=original, content=content))
        entries[rule_name] = {
            "path": str(path),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        installed.append(rule_name)

    return PluginRulePlan(
        updates=tuple(updates),
        ownership={"source": source, "entries": entries},
        installed=tuple(sorted(installed)),
    )


def prepare_plugin_rule_removal(
    plugin_name: str,
    editor: str,
    ownership: dict | None,
) -> PluginRulePlan | None:
    """Remove only unchanged rule files recorded as plugin-owned."""
    source = plugin_rule_source(plugin_name)
    entries = _owned_entries(ownership, source)
    if not entries:
        return None
    if editor == "gemini":
        return _prepare_gemini_removal(plugin_name, entries)
    if editor != "cursor":
        return None

    updates: list[RuleFileUpdate] = []
    removed: list[str] = []
    preserved: list[str] = []
    for rule_name, entry in entries.items():
        path = Path(entry.get("path", ""))
        expected_path = (
            Path.home() / ".cursor" / "rules" / f"plugin-{plugin_name}-{rule_name}.mdc"
        )
        if path != expected_path:
            preserved.append(rule_name)
            continue
        original = _read_optional(path)
        if original is None:
            continue
        if _matches_owned_file(path, original, entry):
            updates.append(RuleFileUpdate(path=path, original=original, content=None))
            removed.append(rule_name)
        else:
            preserved.append(rule_name)
    return PluginRulePlan(
        updates=tuple(updates),
        ownership=None,
        removed=tuple(sorted(removed)),
        preserved=tuple(sorted(preserved)),
    )


def _render_cursor_rule(rule_name: str, source_path: Path) -> bytes:
    content = source_path.read_text(encoding="utf-8").rstrip("\n")
    rendered = (
        "---\n"
        f"description: Plugin rule: {rule_name}\n"
        "alwaysApply: true\n"
        "---\n\n"
        f"{content}\n"
    )
    return rendered.encode("utf-8")


def _prepare_gemini_install(
    plugin_name: str,
    rule_specs: list[dict],
    previous_ownership: dict | None,
) -> PluginRulePlan:
    source = plugin_rule_source(plugin_name)
    previous_entries = _owned_entries(previous_ownership, source)
    path = Path.home() / ".gemini" / "GEMINI.md"
    original = _read_optional(path)
    working = original.decode("utf-8") if original is not None else ""
    blocks: list[str] = []
    entries: dict[str, dict[str, str]] = {}
    installed: list[str] = []

    for spec in rule_specs:
        rule_name = _require_safe_name(spec.get("name"), "rule")
        source_path = Path(spec["source"])
        if source_path.is_symlink() or not source_path.is_file():
            raise RuntimeError(f"Refusing unsafe plugin rule source: {source_path}")
        section = f"plugin-{plugin_name}-{rule_name}"
        current_span = _owned_marker_span(working, section)
        previous = previous_entries.get(rule_name, {})
        if current_span is not None:
            if not _matches_owned_section(path, section, current_span.block, previous):
                raise RuntimeError(
                    f"Refusing user-owned plugin rule section collision: {section}"
                )
            working = _remove_marker_span(working, current_span)

        content = source_path.read_text(encoding="utf-8").rstrip("\n")
        block = markers_start(section) + content + markers_end(section)
        blocks.append(block)
        entries[rule_name] = {
            "path": str(path),
            "section": section,
            "sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
        }
        installed.append(rule_name)

    base = trim_trailing_blanks(working)
    parts = [base] if base else []
    parts.extend(blocks)
    rendered = ("\n\n".join(parts) + "\n").encode("utf-8")
    return PluginRulePlan(
        updates=(RuleFileUpdate(path=path, original=original, content=rendered),),
        ownership={"source": source, "entries": entries},
        installed=tuple(sorted(installed)),
    )


def _prepare_gemini_removal(
    plugin_name: str,
    entries: dict[str, dict],
) -> PluginRulePlan:
    path = Path.home() / ".gemini" / "GEMINI.md"
    original = _read_optional(path)
    if original is None:
        return PluginRulePlan(updates=(), ownership=None)
    working = original.decode("utf-8")
    removed: list[str] = []
    preserved: list[str] = []
    for rule_name, entry in entries.items():
        section = f"plugin-{plugin_name}-{rule_name}"
        span = _owned_marker_span(working, section)
        if span is None:
            continue
        if _matches_owned_section(path, section, span.block, entry):
            working = _remove_marker_span(working, span)
            removed.append(rule_name)
        else:
            preserved.append(rule_name)

    trimmed = trim_trailing_blanks(working)
    content = (trimmed + "\n").encode("utf-8") if trimmed else None
    updates = (
        (RuleFileUpdate(path=path, original=original, content=content),)
        if removed
        else ()
    )
    return PluginRulePlan(
        updates=updates,
        ownership=None,
        removed=tuple(sorted(removed)),
        preserved=tuple(sorted(preserved)),
    )


def _owned_marker_span(content: str, section: str) -> OwnedMarkerSpan | None:
    """Find exactly one balanced, non-crossed marker span for ``section``."""
    markers = tuple(MARKER_PATTERN.finditer(content))
    owned = tuple(match for match in markers if match.group("section") == section)
    if not owned:
        return None
    starts = tuple(match for match in owned if match.group("kind") == "START")
    ends = tuple(match for match in owned if match.group("kind") == "END")
    if len(starts) != 1 or len(ends) != 1:
        raise RuntimeError(f"Malformed or duplicate owned Gemini markers: {section}")

    stack: list[re.Match[str]] = []
    for marker in markers:
        marker_section = marker.group("section")
        if marker.group("kind") == "START":
            if stack and any(item.group("section") == section for item in stack):
                raise RuntimeError(f"Nested owned Gemini marker span: {section}")
            stack.append(marker)
            continue
        if not stack:
            if marker_section == section:
                raise RuntimeError(f"Orphaned owned Gemini marker: {section}")
            continue
        opened = stack[-1]
        if opened.group("section") != marker_section:
            if marker_section == section or any(
                item.group("section") == section for item in stack
            ):
                raise RuntimeError(f"Crossed owned Gemini marker span: {section}")
            continue
        stack.pop()
        if marker_section == section:
            start_index = opened.start()
            end_index = marker.end()
            return OwnedMarkerSpan(
                start=start_index,
                end=end_index,
                block=content[start_index:end_index],
            )
    raise RuntimeError(f"Unbalanced owned Gemini marker span: {section}")


def _remove_marker_span(content: str, span: OwnedMarkerSpan) -> str:
    """Remove only the byte-equivalent character span already verified above."""
    return content[: span.start] + content[span.end :]


def _matches_owned_section(
    path: Path,
    section: str,
    block: str,
    entry: object,
) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get("path") != str(path) or entry.get("section") != section:
        return False
    expected_hash = entry.get("sha256")
    return (
        isinstance(expected_hash, str)
        and hashlib.sha256(block.encode("utf-8")).hexdigest() == expected_hash
    )


def _owned_entries(ownership: object, source: str) -> dict[str, dict]:
    if not isinstance(ownership, dict) or ownership.get("source") != source:
        return {}
    entries = ownership.get("entries")
    if not isinstance(entries, dict):
        return {}
    return {
        name: entry
        for name, entry in entries.items()
        if isinstance(name, str) and isinstance(entry, dict)
    }


def _matches_owned_file(path: Path, content: bytes, entry: object) -> bool:
    if not isinstance(entry, dict) or entry.get("path") != str(path):
        return False
    expected_hash = entry.get("sha256")
    return (
        isinstance(expected_hash, str)
        and hashlib.sha256(content).hexdigest() == expected_hash
    )


def _require_safe_name(value: object, label: str) -> str:
    if not isinstance(value, str) or SAFE_NAME_PATTERN.fullmatch(value) is None:
        raise ValueError(f"Unsafe {label} name: {value!r}")
    return value


def _read_optional(path: Path) -> bytes | None:
    _assert_safe_path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError(f"Plugin rule destination is not a file: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _assert_safe_path(path: Path) -> None:
    absolute = path.expanduser().absolute()
    home = Path.home().absolute()
    try:
        relative = absolute.relative_to(home)
    except ValueError as error:
        raise RuntimeError(f"Plugin rule path escapes HOME: {absolute}") from error
    current = home
    root_info = os.lstat(current)
    if stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode):
        raise RuntimeError(f"Unsafe plugin rule HOME: {current}")
    for part in relative.parts[:-1]:
        current /= part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"Refusing symlinked plugin rule path: {current}")
        if not stat.S_ISDIR(info.st_mode):
            raise RuntimeError(f"Plugin rule ancestor is not a directory: {current}")
