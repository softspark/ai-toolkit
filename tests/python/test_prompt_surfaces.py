# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Regression coverage for host-scoped delegation in native client exports."""

from __future__ import annotations

import importlib
import json
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from codex_skill_adapter import (  # noqa: E402
    build_codex_skill_text,
    build_opencode_skill_text,
    is_codex_adapted_skill,
    sync_codex_skill,
)
from prompt_surfaces import (  # noqa: E402
    CLAUDE_CODE_ONLY_END as END,
    CLAUDE_CODE_ONLY_START as START,
    strip_claude_code_only,
)

PRIVATE_BLOCK = f'{START}\nAgent(subagent_type="codex:codex-rescue")\n{END}\n'
BODY = 'Keep before.\n' + PRIVATE_BLOCK + 'Keep after.\n```python\nmodel = "claude-sonnet-5"\n```\n'


def test_filter_keeps_surrounding_bytes_and_multiple_blocks() -> None:
    source = "first\r\n" + PRIVATE_BLOCK + "middle\n" + PRIVATE_BLOCK + "last"
    assert strip_claude_code_only(source) == "first\r\nmiddle\nlast"
    assert strip_claude_code_only(f"Inline {START} example") == f"Inline {START} example"


@pytest.mark.parametrize("fence", ["```html", "```python", "~~~~text"])
def test_filter_preserves_reserved_markers_in_literal_examples(fence: str) -> None:
    closing = fence[:4] if fence.startswith("~") else "```"
    source = f'{fence}\n{PRIVATE_BLOCK}{closing}\n'
    assert strip_claude_code_only(source) == source


def test_filter_preserves_yaml_block_scalar_markers() -> None:
    source = f'---\nhooks:\n  Stop: |\n    {START}\n    keep literal\n    {END}\n---\n'
    assert strip_claude_code_only(source) == source


@pytest.mark.parametrize("literal", [START, END])
def test_fenced_markers_inside_removed_block_cannot_leak_dispatch(literal: str) -> None:
    source = f'{START}\n```html\n{literal}\n```\nDelegate to codex:codex-rescue\n{END}\nKeep after.\n'
    assert strip_claude_code_only(source) == "Keep after.\n"


@pytest.mark.parametrize("source", [START, END, f"{START}\n{START}\n{END}\n"])
def test_filter_rejects_unbalanced_blocks(source: str) -> None:
    with pytest.raises(ValueError, match="CLAUDE_CODE_ONLY"):
        strip_claude_code_only(source)


@pytest.fixture
def source_agent(tmp_path: Path) -> Path:
    path = tmp_path / "sample.md"
    path.write_text(
        '---\nname: sample\ndescription: Test agent\ntools: Read, Bash\n'
        'model: opus\neffort: xhigh\n---\n' + BODY,
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize(("module_name", "renderer"), [
    ("generate_codex_agents", "_render_agent"),
    ("generate_copilot", "_render_agent"),
    ("generate_antigravity_agents", "render_agent"),
    ("generate_gemini_agents", "render_agent"),
    ("generate_cursor_agents", "_render_cursor_agent"),
    ("generate_augment_agents", "_render_augment_agent"),
    ("generate_opencode_agents", "_render_opencode_agent"),
])
def test_native_agent_exports_omit_claude_plugin_and_preserve_model_selection(
    source_agent: Path, module_name: str, renderer: str,
) -> None:
    rendered = getattr(importlib.import_module(module_name), renderer)(source_agent)
    text = rendered if isinstance(rendered, str) else rendered[-1]
    if module_name == "generate_codex_agents":
        document = tomllib.loads(text)
        assert "model" not in document
        assert "model_reasoning_effort" not in document
        body = document["developer_instructions"]
    else:
        header, body = text.split("---", 2)[1:]
        assert "effort:" not in header
        if module_name in {"generate_cursor_agents", "generate_antigravity_agents"}:
            assert "model: inherit" in header
        else:
            assert "model:" not in header
    assert "codex:codex-rescue" not in body
    assert "CLAUDE_CODE_ONLY" not in body
    assert "Keep before." in body and "Keep after." in body
    assert 'model = "claude-sonnet-5"' in body
    assert PRIVATE_BLOCK in source_agent.read_text(encoding="utf-8")


def test_roo_mode_export_omits_claude_only_delegation(
    source_agent: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    module = importlib.import_module("generate_roo_modes")
    monkeypatch.setattr(module, "agents_dir", source_agent.parent)
    module.main()
    modes = json.loads(capsys.readouterr().out)["customModes"]
    assert len(modes) == 1
    assert "codex:codex-rescue" not in modes[0]["roleDefinition"]
    assert "Keep after." in modes[0]["roleDefinition"]


@pytest.fixture
def native_skill(tmp_path: Path) -> Path:
    path = tmp_path / "sample" / "SKILL.md"
    path.parent.mkdir()
    path.write_text(
        '---\nname: sample\ndescription: Native skill\nuser-invocable: false\n'
        'model: native-model\neffort: high\nhooks:\n  Stop: []\n---\n' + BODY,
        encoding="utf-8",
    )
    (path.parent / "reference.txt").write_text("Kept resource.", encoding="utf-8")
    return path


def test_marker_only_skill_materializes_without_losing_native_metadata(
    native_skill: Path, tmp_path: Path,
) -> None:
    original = native_skill.read_text(encoding="utf-8")
    assert is_codex_adapted_skill(native_skill)
    for render in (build_codex_skill_text, build_opencode_skill_text):
        result = render(native_skill)
        assert result.split("---", 2)[1] == original.split("---", 2)[1]
        assert "codex:codex-rescue" not in result
        assert 'model = "claude-sonnet-5"' in result
    destination = tmp_path / "output"
    destination.mkdir()
    sync_codex_skill(native_skill.parent, destination)
    installed = destination / "sample" / "SKILL.md"
    assert not installed.is_symlink()
    assert "codex:codex-rescue" not in installed.read_text(encoding="utf-8")
    assert (installed.parent / "reference.txt").read_text(encoding="utf-8") == "Kept resource."
    assert native_skill.read_text(encoding="utf-8") == original


@pytest.mark.parametrize(("module_name", "renderer"), [
    ("generate_opencode_commands", "_render_opencode_command"),
    ("generate_augment_commands", "_render_augment_command"),
])
def test_native_commands_filter_host_specific_dispatch(
    native_skill: Path, module_name: str, renderer: str,
) -> None:
    result = getattr(importlib.import_module(module_name), renderer)(native_skill)
    assert "codex:codex-rescue" not in result
    assert "Keep after." in result


def test_antigravity_plugin_filters_skills_and_preserves_other_assets(native_skill: Path) -> None:
    from antigravity_plugin import _adapt_skill_files

    original = native_skill.read_bytes()
    files = [("skills/sample/SKILL.md", original, 0o644), ("skills/sample/data.bin", b"\x00", 0o644)]
    result = _adapt_skill_files(files)
    assert b"codex:codex-rescue" not in result[0][1]
    assert b"model: native-model" in result[0][1]
    assert result[1] == files[1]


def test_copilot_skill_and_prompt_filter_plugin_dispatch(native_skill: Path) -> None:
    from generate_copilot import _portable_copilot_body, _render_skill_markdown

    _, skill = _render_skill_markdown(native_skill.parent)
    prompt = _portable_copilot_body(BODY, include_execution_note=True)
    for result in (skill, prompt):
        assert "codex:codex-rescue" not in result
        assert 'model = "claude-sonnet-5"' in result


def test_codex_plugin_stage_omits_claude_delegation(tmp_path: Path) -> None:
    from codex_plugin import stage_plugin, validate_staged_plugin

    staged = tmp_path / "plugin"
    stage_plugin(staged)
    assert validate_staged_plugin(staged) == []
    skill = (staged / "skills/model-routing-patterns/SKILL.md").read_text(encoding="utf-8")
    assert "codex:codex-rescue" not in skill
    assert "--model gpt-6-astra" not in skill


@pytest.mark.parametrize("vendor", ["cursor", "augment", "opencode"])
def test_malformed_agent_fails_before_any_existing_output_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, vendor: str,
) -> None:
    module = importlib.import_module(f"generate_{vendor}_agents")
    source = tmp_path / "source"
    source.mkdir()
    for name, body in (("a-valid", BODY), ("z-invalid", START)):
        (source / f"{name}.md").write_text(
            f"---\nname: {name}\ndescription: Test\ntools: Read\n---\n{body}", encoding="utf-8",
        )
    monkeypatch.setattr(module, "agents_dir", source)
    output = tmp_path / "output"
    agents = output / f".{vendor}" / "agents"
    agents.mkdir(parents=True)
    previous = agents / "ai-toolkit-a-valid.md"
    previous.write_text("Original", encoding="utf-8")
    with pytest.raises(ValueError, match="Unterminated"):
        module.generate(output)
    assert previous.read_text(encoding="utf-8") == "Original"
    assert len(list(agents.iterdir())) == 1


@pytest.mark.parametrize("vendor", ["augment", "opencode"])
def test_malformed_command_fails_before_any_existing_output_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, vendor: str,
) -> None:
    module = importlib.import_module(f"generate_{vendor}_commands")
    source = tmp_path / "source"
    source.mkdir()
    for name, body in (("a-valid", BODY), ("z-invalid", START)):
        skill = source / name / "SKILL.md"
        skill.parent.mkdir()
        skill.write_text(
            f"---\nname: {name}\ndescription: Test\nuser-invocable: true\n---\n{body}",
            encoding="utf-8",
        )
    monkeypatch.setattr(module, "skills_dir", source)
    output = tmp_path / "output"
    commands = output / f".{vendor}" / "commands"
    commands.mkdir(parents=True)
    previous = commands / "ai-toolkit-a-valid.md"
    previous.write_text("Original", encoding="utf-8")
    with pytest.raises(ValueError, match="Unterminated"):
        module.generate(output)
    assert previous.read_text(encoding="utf-8") == "Original"
    assert len(list(commands.iterdir())) == 1


@pytest.mark.parametrize("name", [
    "orchestrate", "workflow", "swarm", "agent-creator", "subagent-development",
    "autonomous-dev", "model-routing-patterns",
])
def test_real_codex_skills_cannot_delegate_back_to_claude_plugin(name: str) -> None:
    source = ROOT / "app" / "skills" / name / "SKILL.md"
    result = build_codex_skill_text(source)
    assert "codex:codex-rescue" not in result
    assert "--model gpt-6-astra" not in result
    assert "CLAUDE_CODE_ONLY" not in result


def test_native_worker_and_supervisor_defaults_follow_approved_roles() -> None:
    from frontmatter import frontmatter_field

    expected = {
        "backend-specialist": ("sonnet", "high"),
        "test-engineer": ("sonnet", "high"),
        "orchestrator": ("opus", "high"),
        "debugger": ("opus", "xhigh"),
    }
    for name, (model, effort) in expected.items():
        source = ROOT / "app" / "agents" / f"{name}.md"
        assert frontmatter_field(source, "model") == model
        assert frontmatter_field(source, "effort") == effort
