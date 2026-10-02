#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Read-only Claude SessionStart hint, never an effective plugin authorization.

Only the official Codex plugin's installed metadata and local enablement are
inspected. CLI overrides, managed policy, account access and the runtime agent
catalog remain Claude's responsibility. No plugin code is read or executed.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

PLUGIN_KEY = "codex@openai-codex"
MAX_METADATA_BYTES = 1024 * 1024
NATIVE_HINT = (
    "AI Toolkit: Codex delegation is not confirmed for this Claude session. "
    "Use available native agents and the current model selection; do not install, "
    "enable or force Codex. Recheck availability if the session configuration changes."
)
AVAILABLE_HINT = (
    "AI Toolkit: local metadata indicates the installed Codex plugin is enabled. "
    "Apply the model-routing-patterns skill before choosing an executor, including "
    "its security Astra/xhigh and debugging routes. "
    "This is a hint, not authorization: delegate only if codex:codex-rescue is also "
    "callable in the current Claude agent catalog and the task permits it. Respect "
    "managed/session restrictions and explicit model choices. Otherwise use available "
    "native agents and the current model selection. The wrapper only forwards; "
    "the Codex worker researches and verifies, and the supervisor checks the result."
)


def _read_text(path: Path) -> str:
    if not path.is_file():
        raise ValueError("Metadata is not a regular file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_METADATA_BYTES + 1)
    if len(raw) > MAX_METADATA_BYTES:
        raise ValueError("Metadata is too large")
    return raw.decode("utf-8")


def _read_object(path: Path) -> dict[str, object]:
    value: object = json.loads(_read_text(path))
    if not isinstance(value, dict):
        raise ValueError("Metadata must be an object")
    return value


def _absolute_path(value: object) -> Path:
    if not isinstance(value, str) or not value or not Path(value).is_absolute():
        raise ValueError("Metadata requires an absolute path")
    return Path(value).resolve()


def _local_settings_root(cwd: Path, home: Path) -> Path:
    """Find Git/common-worktree root without invoking Git or another process."""
    if os.name == "nt":
        return cwd
    for root in (cwd, *cwd.parents):
        git_path = root / ".git"
        if not git_path.exists():
            continue
        if root == home or any(
            path.exists() and path.stat().st_uid != os.getuid() for path in (root, git_path, root / ".claude")
        ):
            return cwd
        if git_path.is_file():
            directive = _read_text(git_path).strip()
            if not directive.startswith("gitdir: "):
                raise ValueError("Invalid worktree metadata")
            git_dir = (root / directive.removeprefix("gitdir: ")).resolve()
            common_path = git_dir / "commondir"
            if common_path.is_file():
                common_dir = (git_dir / _read_text(common_path).strip()).resolve()
                if common_dir.name != ".git":
                    raise ValueError("Unrecognized common-worktree directory")
                return common_dir.parent
        return root
    return cwd


def _is_enabled(paths: list[Path]) -> bool:
    enabled = False
    for path in dict.fromkeys(paths):
        if not path.exists():
            continue
        plugins = _read_object(path).get("enabledPlugins", {})
        if not isinstance(plugins, dict):
            raise ValueError("Invalid plugin settings")
        if PLUGIN_KEY in plugins:
            value = plugins[PLUGIN_KEY]
            if not isinstance(value, bool):
                raise ValueError("Invalid plugin enablement")
            enabled = value
    return enabled


def _has_installed_agent(registry: Path, project_paths: set[Path]) -> bool:
    plugins = _read_object(registry).get("plugins")
    if not isinstance(plugins, dict):
        return False
    entries = plugins.get(PLUGIN_KEY)
    if not isinstance(entries, list):
        return False
    candidates: list[tuple[int, Path]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        scope = entry.get("scope")
        if scope not in ("user", "project", "local"):
            continue
        if scope != "user" and _absolute_path(entry.get("projectPath")) not in project_paths:
            continue
        priority = {"user": 0, "project": 1, "local": 2}[scope]
        candidates.append((priority, _absolute_path(entry.get("installPath"))))
    if not candidates:
        return False
    _, install_path = max(candidates, key=lambda item: item[0])
    return (install_path / "agents" / "codex-rescue.md").is_file()


def capability_hint(payload: Mapping[str, object], env: Mapping[str, str]) -> str:
    """Return fixed, non-sensitive guidance for Claude only; never alter settings."""
    if (
        not env.get("CLAUDE_PROJECT_DIR")
        or env.get("CODEX_THREAD_ID")
        or env.get("AI_TOOLKIT_HOOK_FORMAT") == "json"
        or env.get("AI_TOOLKIT_HOOK_QUIET") == "1"
        or env.get("TOOLKIT_HOOK_PROFILE") == "minimal"
        or payload.get("hook_event_name") != "SessionStart"
    ):
        return ""
    try:
        home = _absolute_path(env.get("HOME"))
        config_dir = _absolute_path(env.get("CLAUDE_CONFIG_DIR") or str(home / ".claude"))
        cwd = _absolute_path(payload.get("cwd") or env["CLAUDE_PROJECT_DIR"])
        if not cwd.is_dir():
            return NATIVE_HINT
        root = _local_settings_root(cwd, home)
        settings = [
            config_dir / "settings.json",
            cwd / ".claude" / "settings.json",
            cwd / ".claude" / "settings.local.json",
            root / ".claude" / "settings.local.json",
        ]
        if _is_enabled(settings) and _has_installed_agent(
            config_dir / "plugins" / "installed_plugins.json", {cwd, root}
        ):
            return AVAILABLE_HINT
    except (OSError, ValueError, RuntimeError, RecursionError):
        pass
    return NATIVE_HINT


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_METADATA_BYTES + 1)
        if len(raw) > MAX_METADATA_BYTES:
            return 0
        payload: object = json.loads(raw)
        if isinstance(payload, dict) and (hint := capability_hint(payload, os.environ)):
            print(hint)
    except (OSError, ValueError, RecursionError):
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
