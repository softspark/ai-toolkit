# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Augment native permissions must remain restrictive through generation and cleanup."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import generate_augment_agents as augment  # noqa: E402
import generate_augment_hooks as hooks  # noqa: E402
import mcp_editors  # noqa: E402
from frontmatter import parse_frontmatter  # noqa: E402

LEGACY = '---\nname: legacy\ndescription: "Old export"\ntools: [Read]\ndisabled_tools: []\n---\nLegacy body\n'
USER = "---\nname: personal\ntools: [view]\n---\nUser-authored notes\n"


def write_agent(directory: Path, name: str, tools: str) -> Path:
    path = directory / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'---\nname: {name}\ndescription: "Example"\nmodel: opus\ntools: {tools}\n---\nAgent body\n',
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize(("source", "expected"), [
    ("Read", ["view"]),
    ("Grep, Glob, Grep", ["codebase-retrieval", "view"]),
    ("Glob", ["view", "codebase-retrieval"]),
    ("Write, Edit, Bash", ["save-file", "str-replace-editor", "launch-process"]),
    ("Read, Grep, Glob", ["view", "codebase-retrieval"]),
])
def test_native_allowlist_maps_only_granted_tools(tmp_path: Path, source: str, expected: list[str]) -> None:
    path = write_agent(tmp_path, "example", source)

    rendered = augment._render_augment_agent(path, major=0)
    frontmatter = parse_frontmatter(rendered)

    assert frontmatter["tools"] == expected
    assert "disabled_tools" not in frontmatter
    assert "model" not in frontmatter


def test_read_only_explorer_has_no_shell_or_write_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    augment.generate(tmp_path)

    result = (tmp_path / ".augment/agents/ai-toolkit-explorer-agent.md").read_text()

    assert parse_frontmatter(result)["tools"] == ["read", "grep", "find"]
    assert parse_frontmatter(result)["extensions"] == "false"


def test_installed_client_selects_and_migrates_agent_tools(tmp_path, monkeypatch):
    client = tmp_path / "bin/auggie"
    client.parent.mkdir()
    monkeypatch.setenv("PATH", str(client.parent))
    agent = tmp_path / ".augment/agents/ai-toolkit-explorer-agent.md"
    for version, expected in (("0.37.1", ["view", "codebase-retrieval"]),
                              ("1.2.2", ["read", "grep", "find"])):
        client.write_text(f'#!/bin/sh\n[ "$1" = "--version" ] || exit 64\necho "auggie {version}"\n')
        client.chmod(0o755)
        augment.generate(tmp_path)
        installed = agent.read_text()
        metadata = parse_frontmatter(installed)
        assert metadata["tools"] == expected
        assert "model" not in metadata and "thinking" not in metadata
        client.unlink()
        augment.generate(tmp_path)
        assert agent.read_text() == installed


@pytest.mark.parametrize("tool,fields", [
    ("write", {"path": "tsconfig.json", "content": "{}"}),
    ("save-file", {"path": "pyproject.toml", "file_content": "[tool.ruff]"}),
    ("edit", {"path": "pyproject.toml", "edits": [
        {"oldText": "first", "newText": "first edit"},
        {"oldText": "second", "newText": "[tool.ruff]"},
    ]}),
    ("str-replace-editor", {"path": "pyproject.toml", "new_str_1": "[tool.ruff]"}),
])
def test_generated_augment_hook_runs_with_native_payload(tmp_path, tool, fields):
    repo = Path(__file__).resolve().parents[2]
    runtime = tmp_path / ".softspark/ai-toolkit/hooks"
    runtime.parent.mkdir(parents=True)
    shutil.copytree(repo / "app/hooks", runtime)
    settings_path = hooks.generate(tmp_path)
    registered = json.loads(settings_path.read_text())["hooks"]
    env = {**os.environ, "HOME": str(tmp_path)}
    payload = json.dumps({"tool_name": tool, "tool_input": fields, "conversation_id": "fixture"})
    for event, handler in (("PreToolUse", "guard-config.sh"), ("PostToolUse", "post-tool-use.sh")):
        commands = [hook["command"] for group in registered[event]
                    if re.search(group["matcher"], tool, re.IGNORECASE)
                    for hook in group["hooks"] if handler in hook["command"]]
        assert len(commands) == 1
        result = subprocess.run(["bash", "-c", commands[0]], cwd=tmp_path, env=env,
                                input=payload, capture_output=True, text=True, check=False)
        if event == "PreToolUse":
            assert result.returncode == 2 and "protected" in result.stderr
        else:
            assert result.returncode == 0, result.stderr
            context = json.loads(result.stdout)["hookSpecificOutput"]
            assert context["hookEventName"] == event and context["additionalContext"]


@pytest.mark.parametrize("invalid", ["{", "[]", '{"hooks": []}'])
def test_hook_migration_preserves_unreadable_settings(tmp_path, invalid):
    path = tmp_path / ".augment/settings.json"
    path.parent.mkdir()
    path.write_text(invalid)
    with pytest.raises(ValueError):
        hooks.generate(tmp_path)
    assert path.read_text() == invalid


def test_augment_v1_upgrade_rolls_back_earlier_agent_on_failure(tmp_path, monkeypatch):
    source = tmp_path / "source"
    monkeypatch.setattr(augment, "agents_dir", source)
    for name in ("a-first", "z-second"):
        write_agent(source, name, "Read")
    monkeypatch.setattr(augment, "_target_major", lambda _: 0)
    augment.generate(tmp_path)
    out = tmp_path / ".augment/agents"
    originals = {p.name: p.read_bytes() for p in out.iterdir()}
    write = mcp_editors._atomic_write_bytes

    def fail_second(path, content):
        if path.name == "ai-toolkit-z-second.md":
            raise OSError("fixture write failure")
        write(path, content)

    monkeypatch.setattr(augment, "_target_major", lambda _: 1)
    monkeypatch.setattr(mcp_editors, "_atomic_write_bytes", fail_second)
    with pytest.raises(OSError, match="fixture write failure"):
        augment.generate(tmp_path)
    assert {p.name: p.read_bytes() for p in out.iterdir()} == originals


def test_hook_refresh_preserves_user_handler_in_legacy_group(tmp_path, monkeypatch):
    path = tmp_path / ".augment/settings.json"
    path.parent.mkdir()
    user = {"type": "command", "command": "company-audit"}
    old = {"type": "command", "command": "old-handler", "_source": "ai-toolkit"}
    group = {"matcher": "write", "hooks": [old, user]}
    path.write_text(json.dumps({"hooks": {"PostToolUse": [group]}, "model": "my-choice"}))
    path.chmod(0o640)
    original_mode = path.stat().st_mode
    # Exercise the portable mode-preservation branch through a real refresh.
    monkeypatch.delattr(os, "fchmod", raising=False)
    hooks.generate(tmp_path)
    current = json.loads(path.read_text())
    assert current["model"] == "my-choice"
    assert path.stat().st_mode == original_mode
    assert current["hooks"]["PostToolUse"][0] == {"matcher": "write", "hooks": [user]}


def test_security_auditor_keeps_local_scanner_access_and_omits_editors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    root = Path(__file__).resolve().parents[2]
    source = (root / "app/agents/security-auditor.md").read_text(encoding="utf-8")
    assert set(parse_frontmatter(source)["tools"].split(", ")) == {"Read", "Grep", "Glob", "Bash"}
    scanner = (root / "app/skills/hipaa-validate/SKILL.md").read_text(encoding="utf-8")
    assert parse_frontmatter(scanner)["agent"] == "security-auditor"

    augment.generate(tmp_path)
    emitted = (tmp_path / ".augment/agents/ai-toolkit-security-auditor.md").read_text()

    assert parse_frontmatter(emitted)["tools"] == ["read", "grep", "find", "bash"]
    assert "Use Bash only for local inspection" in emitted
    assert "## Regression checks" in emitted
    assert "### Test Payloads" not in emitted


def test_unsupported_orchestration_is_explained_without_extra_permissions(tmp_path: Path) -> None:
    source = write_agent(tmp_path, "coordinator", "Read, Agent, TeamCreate, TeamDelete, SendMessage, TaskCreate, TaskList, TaskUpdate")

    result = augment._render_augment_agent(source)

    assert parse_frontmatter(result)["tools"] == ["read"]
    assert "unavailable in this exported agent" in result
    assert "Do not simulate these tools or claim delegation occurred" in result


@pytest.mark.parametrize("existing", [False, True])
def test_unknown_tool_fails_before_any_output_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: bool) -> None:
    source = tmp_path / "source"
    write_agent(source, "a-valid", "Read")
    write_agent(source, "z-invalid", "Read, FutureDangerousTool")
    monkeypatch.setattr(augment, "agents_dir", source)
    project = tmp_path / "project"
    project.mkdir()
    output = project / ".augment/agents"
    if existing:
        output.mkdir(parents=True)
        (output / "ai-toolkit-a-valid.md").write_text(LEGACY)

    with pytest.raises(ValueError, match="FutureDangerousTool"):
        augment.generate(project)

    if existing:
        assert {p.name: p.read_text() for p in output.iterdir()} == {"ai-toolkit-a-valid.md": LEGACY}
    else:
        assert not output.exists()


@pytest.mark.parametrize("tools", ["", "Agent, TeamCreate, SendMessage"])
def test_empty_native_allowlist_fails_before_any_output_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tools: str) -> None:
    source = tmp_path / "source"
    write_agent(source, "a-valid", "Read")
    write_agent(source, "z-empty", tools)
    monkeypatch.setattr(augment, "agents_dir", source)
    project = tmp_path / "project"
    output = project / ".augment/agents"
    output.mkdir(parents=True)
    previous = output / "ai-toolkit-a-valid.md"
    previous.write_text(LEGACY)

    with pytest.raises(ValueError, match="empty native allowlist"):
        augment.generate(project)

    assert {path.name: path.read_text() for path in output.iterdir()} == {previous.name: LEGACY}


def test_stale_cleanup_removes_old_and_new_owned_exports_but_preserves_user_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source"
    source.mkdir()
    monkeypatch.setattr(augment, "agents_dir", source)
    output = tmp_path / ".augment/agents"
    output.mkdir(parents=True)
    (output / "ai-toolkit-legacy.md").write_text(LEGACY)
    new_source = write_agent(tmp_path / "fixture", "new", "Read")
    (output / "ai-toolkit-new.md").write_text(augment._render_augment_agent(new_source))
    (output / "ai-toolkit-personal.md").write_text(USER)

    assert augment.generate(tmp_path) == (0, 2)

    assert {p.name: p.read_text() for p in output.iterdir()} == {"ai-toolkit-personal.md": USER}


def test_uninstall_recognizes_legacy_and_marker_exports_only(tmp_path: Path) -> None:
    output = tmp_path / ".augment/agents"
    output.mkdir(parents=True)
    source = write_agent(tmp_path / "source", "new", "Read")
    (output / "ai-toolkit-new.md").write_text(augment._render_augment_agent(source))
    (output / "ai-toolkit-legacy.md").write_text(LEGACY)
    (output / "ai-toolkit-personal.md").write_text(USER)

    assert augment.discover(tmp_path) == 2
    assert augment.cleanup(tmp_path) == 2
    assert augment.cleanup(tmp_path) == 0
    assert (output / "ai-toolkit-personal.md").read_text() == USER


@pytest.mark.parametrize("symlink", [False, True])
def test_regeneration_preserves_unowned_destination(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, symlink: bool) -> None:
    source = tmp_path / "source"
    write_agent(source, "example", "Read")
    monkeypatch.setattr(augment, "agents_dir", source)
    output = tmp_path / ".augment/agents"
    output.mkdir(parents=True)
    destination = output / "ai-toolkit-example.md"
    outside = tmp_path / "personal.md"
    outside.write_text(USER)
    if symlink:
        destination.symlink_to(outside)
    else:
        destination.write_text(USER)

    assert augment.generate(tmp_path) == (0, 0)

    assert destination.read_text() == USER
    assert outside.read_text() == USER


def test_legacy_current_agent_upgrades_to_marked_native_allowlist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source"
    write_agent(source, "example", "Read")
    monkeypatch.setattr(augment, "agents_dir", source)
    output = tmp_path / ".augment/agents"
    output.mkdir(parents=True)
    destination = output / "ai-toolkit-example.md"
    destination.write_text(LEGACY)

    assert augment.generate(tmp_path) == (1, 0)

    result = destination.read_text()
    assert "<!-- ai-toolkit-managed: augment-agent -->" in result
    assert parse_frontmatter(result)["tools"] == ["view"]
    assert "disabled_tools" not in parse_frontmatter(result)


@pytest.mark.parametrize("relative", [".augment", ".augment/agents"])
def test_generation_refuses_symlinked_output_directory(tmp_path: Path, relative: str) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "personal.md"
    sentinel.write_text(USER)
    project = tmp_path / "project"
    destination = project / relative
    destination.parent.mkdir(parents=True)
    destination.symlink_to(outside, target_is_directory=True)

    with pytest.raises(RuntimeError, match="Refusing symlinked"):
        augment.generate(project)

    assert {path.name: path.read_text() for path in outside.iterdir()} == {"personal.md": USER}


def test_legacy_example_in_user_body_is_preserved_on_generate_and_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source"
    write_agent(source, "personal", "Read")
    monkeypatch.setattr(augment, "agents_dir", source)
    output = tmp_path / ".augment/agents"
    output.mkdir(parents=True)
    user_text = (
        '---\nname: personal\ndescription: "User notes"\ntools: [view]\n---\n'
        '\n```yaml\ndisabled_tools: []\n---\n```\n'
    )
    for name in ("ai-toolkit-personal.md", "ai-toolkit-orphan.md"):
        (output / name).write_text(user_text)
    before = {path.name: path.read_text() for path in output.iterdir()}

    assert augment.generate(tmp_path) == (0, 0)
    assert augment.discover(tmp_path) == 0
    assert augment.cleanup(tmp_path) == 0

    assert {path.name: path.read_text() for path in output.iterdir()} == before
