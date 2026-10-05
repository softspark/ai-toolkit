# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Local metadata hints must never enable a missing or disabled Codex plugin."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from claude_codex_capability import (  # noqa: E402
    AVAILABLE_HINT,
    MAX_METADATA_BYTES,
    NATIVE_HINT,
    PLUGIN_KEY,
    capability_hint,
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def installation(tmp_path: Path) -> tuple[Path, Path, dict[str, str], dict[str, object]]:
    home, project = tmp_path / "home", tmp_path / "project"
    project.mkdir()
    config = home / ".claude"
    install = config / "plugins/cache/openai-codex/codex/1.0.6"
    (install / "agents").mkdir(parents=True)
    (install / "agents/codex-rescue.md").write_text("not executed", encoding="utf-8")
    write_json(config / "settings.json", {"enabledPlugins": {PLUGIN_KEY: True}})
    write_json(
        config / "plugins/installed_plugins.json",
        {
            "version": 2,
            "plugins": {PLUGIN_KEY: [{"scope": "user", "installPath": str(install)}]},
        },
    )
    env = {"HOME": str(home), "CLAUDE_PROJECT_DIR": str(project)}
    payload: dict[str, object] = {"hook_event_name": "SessionStart", "cwd": str(project)}
    return config, project, env, payload


def test_installed_enabled_plugin_provides_hint_without_authorizing_runtime(installation):
    _, _, env, payload = installation
    hint = capability_hint(payload, env)
    assert hint == AVAILABLE_HINT
    assert "callable in the current Claude agent catalog" in hint
    assert "not authorization" in hint


@pytest.mark.parametrize("location", ["settings.json", "plugins/installed_plugins.json"])
def test_missing_configuration_preserves_native_models(installation, location):
    config, _, env, payload = installation
    (config / location).unlink()
    assert capability_hint(payload, env) == NATIVE_HINT


@pytest.mark.parametrize("value", [False, "true", 1, None, [], {"enabled": True}])
def test_only_boolean_enablement_is_accepted(installation, value):
    config, _, env, payload = installation
    write_json(config / "settings.json", {"enabledPlugins": {PLUGIN_KEY: value}})
    assert capability_hint(payload, env) == NATIVE_HINT


@pytest.mark.parametrize("location", ["settings.json", "plugins/installed_plugins.json"])
@pytest.mark.parametrize("contents", ["{", "null", "[]", "42", "\udcff"])
def test_malformed_metadata_gracefully_preserves_native_models(installation, location, contents):
    config, _, env, payload = installation
    (config / location).write_bytes(contents.encode("utf-8", errors="surrogatepass"))
    assert capability_hint(payload, env) == NATIVE_HINT


@pytest.mark.parametrize("setting", ["settings.json", "settings.local.json"])
def test_project_override_disables_user_plugin(installation, setting):
    _, project, env, payload = installation
    write_json(project / ".claude" / setting, {"enabledPlugins": {PLUGIN_KEY: False}})
    assert capability_hint(payload, env) == NATIVE_HINT


def test_local_override_can_enable_project_disabled_plugin(installation):
    _, project, env, payload = installation
    write_json(project / ".claude/settings.json", {"enabledPlugins": {PLUGIN_KEY: False}})
    write_json(project / ".claude/settings.local.json", {"enabledPlugins": {PLUGIN_KEY: True}})
    assert capability_hint(payload, env) == AVAILABLE_HINT


def test_malformed_project_settings_do_not_fall_back_to_enabled_user_plugin(installation):
    _, project, env, payload = installation
    write_json(project / ".claude/settings.local.json", {"enabledPlugins": []})
    assert capability_hint(payload, env) == NATIVE_HINT


def test_git_root_local_settings_override_legacy_subdirectory_local_settings(installation):
    _, project, env, payload = installation
    (project / ".git").mkdir()
    child = project / "subdirectory"
    child.mkdir()
    write_json(child / ".claude/settings.local.json", {"enabledPlugins": {PLUGIN_KEY: True}})
    write_json(project / ".claude/settings.local.json", {"enabledPlugins": {PLUGIN_KEY: False}})
    assert capability_hint({**payload, "cwd": str(child)}, env) == NATIVE_HINT


def test_worktree_uses_main_checkout_local_settings(installation):
    _, project, env, payload = installation
    git_dir = project / ".git/worktrees/task"
    git_dir.mkdir(parents=True)
    (git_dir / "commondir").write_text("../..", encoding="utf-8")
    worktree = project.parent / "worktree"
    worktree.mkdir()
    (worktree / ".git").write_text(f"gitdir: {git_dir}\n", encoding="utf-8")
    write_json(project / ".claude/settings.local.json", {"enabledPlugins": {PLUGIN_KEY: False}})
    assert capability_hint({**payload, "cwd": str(worktree)}, env) == NATIVE_HINT


def test_payload_cwd_overrides_startup_project_after_directory_change(installation):
    _, project, env, payload = installation
    new_project = project.parent / "new-project"
    new_project.mkdir()
    write_json(new_project / ".claude/settings.local.json", {"enabledPlugins": {PLUGIN_KEY: False}})
    assert capability_hint({**payload, "cwd": str(new_project)}, env) == NATIVE_HINT


@pytest.mark.parametrize("scope", ["project", "local"])
@pytest.mark.parametrize("matching", [True, False])
def test_installation_scope_must_match_current_project(installation, scope, matching):
    config, project, env, payload = installation
    registry = config / "plugins/installed_plugins.json"
    data = json.loads(registry.read_text())
    data["plugins"][PLUGIN_KEY][0].update(
        {
            "scope": scope,
            "projectPath": str(project if matching else project.parent / "another-project"),
        }
    )
    write_json(registry, data)
    assert capability_hint(payload, env) == (AVAILABLE_HINT if matching else NATIVE_HINT)


def test_missing_agent_file_never_claims_availability(installation):
    config, _, env, payload = installation
    (config / "plugins/cache/openai-codex/codex/1.0.6/agents/codex-rescue.md").unlink()
    assert capability_hint(payload, env) == NATIVE_HINT


def test_project_installation_has_precedence_over_stale_user_installation(installation):
    config, project, env, payload = installation
    registry = config / "plugins/installed_plugins.json"
    data = json.loads(registry.read_text())
    data["plugins"][PLUGIN_KEY].append(
        {
            "scope": "project",
            "projectPath": str(project),
            "installPath": str(config / "missing-project-install"),
        }
    )
    write_json(registry, data)
    assert capability_hint(payload, env) == NATIVE_HINT


def test_custom_config_directory_replaces_default_directory(installation):
    config, _, env, payload = installation
    custom = config.parent / "custom config"
    config.rename(custom)
    registry = custom / "plugins/installed_plugins.json"
    data = json.loads(registry.read_text())
    data["plugins"][PLUGIN_KEY][0]["installPath"] = str(custom / "plugins/cache/openai-codex/codex/1.0.6")
    write_json(registry, data)
    assert capability_hint(payload, {**env, "CLAUDE_CONFIG_DIR": str(custom)}) == AVAILABLE_HINT
    assert capability_hint(payload, env) == NATIVE_HINT


@pytest.mark.parametrize(
    "overrides",
    [
        {"CLAUDE_PROJECT_DIR": ""},
        {"CODEX_THREAD_ID": "native-codex"},
        {"AI_TOOLKIT_HOOK_FORMAT": "json"},
        {"TOOLKIT_HOOK_PROFILE": "minimal"},
        {"AI_TOOLKIT_HOOK_QUIET": "1"},
    ],
)
def test_native_clients_and_opt_out_profiles_emit_no_claude_hint(installation, overrides):
    _, _, env, payload = installation
    assert capability_hint(payload, {**env, **overrides}) == ""


@pytest.mark.parametrize("payload", [{}, {"event": "session.created"}, {"hook_event_name": "SubagentStart"}])
def test_non_claude_session_payload_emits_no_hint(installation, payload):
    _, _, env, _ = installation
    assert capability_hint(payload, env) == ""


def test_oversized_metadata_is_ignored(installation):
    config, _, env, payload = installation
    (config / "settings.json").write_text(" " * (MAX_METADATA_BYTES + 1))
    assert capability_hint(payload, env) == NATIVE_HINT


def test_hint_contains_no_private_paths_or_raw_metadata_and_detection_is_read_only(installation):
    config, _, env, payload = installation
    write_json(
        config / "settings.json",
        {
            "enabledPlugins": {PLUGIN_KEY: True},
            "env": {"PRIVATE_VALUE": "do-not-display"},
        },
    )
    before = {p: p.read_bytes() for p in config.rglob("*") if p.is_file()}
    hint = capability_hint(payload, env)
    assert str(config) not in hint
    assert "do-not-display" not in hint
    assert before == {p: p.read_bytes() for p in config.rglob("*") if p.is_file()}
