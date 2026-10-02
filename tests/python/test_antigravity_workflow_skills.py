# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Workflow retirement must preserve slash names and user-owned shared skills."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import generate_antigravity as generator  # noqa: E402
from antigravity_workflow_skills import (  # noqa: E402
    MANAGED_MARKER,
    render_workflow_skills,
    sync_workflow_skills,
)
from dir_rules_shared import STANDARD_WORKFLOWS  # noqa: E402
from frontmatter import parse_frontmatter, split_frontmatter  # noqa: E402
from install_steps.ai_tools import _detect_editors  # noqa: E402
from secure_fs import SecureTransaction  # noqa: E402


def test_every_legacy_workflow_keeps_its_slash_name_and_body(tmp_path: Path) -> None:
    generator.generate(tmp_path)
    rendered = render_workflow_skills()
    assert len(rendered) == len(STANDARD_WORKFLOWS) == 13
    for filename, render in STANDARD_WORKFLOWS.items():
        name = Path(filename).stem
        skill = tmp_path / ".agents/skills" / name / "SKILL.md"
        text = skill.read_text()
        assert parse_frontmatter(text)["name"] == name
        assert parse_frontmatter(text)["description"] == parse_frontmatter(render())["description"]
        assert split_frontmatter(render())[1] in text
        legacy = (tmp_path / ".agents/workflows" / filename).read_text()
        assert "DEPRECATED: workflows retire 2026-11-01" in legacy
        assert split_frontmatter(render())[1].strip() in legacy
    assert "codex" not in _detect_editors(tmp_path)
    assert "antigravity" in _detect_editors(tmp_path)


def test_global_workflow_skills_are_available_in_both_product_roots(tmp_path: Path) -> None:
    generator.generate_global(tmp_path)
    for root in (".gemini/config/skills", ".gemini/antigravity-cli/skills"):
        assert len(list((tmp_path / root).glob("ai-toolkit-*/SKILL.md"))) == 14
    before = {p: p.read_bytes() for p in tmp_path.rglob("SKILL.md")}
    generator.generate_global(tmp_path)
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("SKILL.md")}


def test_explicit_skill_directory_opt_out_keeps_legacy_contract(tmp_path: Path) -> None:
    generator.generate(tmp_path, emit_skill_pointer=False)
    assert not (tmp_path / ".agents/skills").exists()
    assert len(list((tmp_path / ".agents/workflows").glob("*.md"))) == 13


def test_owned_cleanup_preserves_user_collisions_and_extra_resources(tmp_path: Path) -> None:
    root = tmp_path / ".agents/skills"
    user = root / "ai-toolkit-code-review/SKILL.md"
    user.parent.mkdir(parents=True)
    user.write_text("user-owned content")
    generator.generate(tmp_path)
    assert user.read_text() == "user-owned content"
    extra = root / "ai-toolkit-debug/notes.txt"
    extra.write_text("user notes")
    expected = generator.discover(tmp_path)
    assert generator.cleanup(tmp_path) == expected
    assert user.read_text() == "user-owned content"
    assert extra.read_text() == "user notes"
    assert not (extra.parent / "SKILL.md").exists()
    assert generator.cleanup(tmp_path) == 0


def test_generated_skills_do_not_claim_unrelated_shared_codex_skills(tmp_path: Path) -> None:
    generator.generate(tmp_path)
    native = tmp_path / ".agents/skills/my-native-skill/SKILL.md"
    native.parent.mkdir()
    native.write_text("native user skill")
    assert "codex" in _detect_editors(tmp_path)
    generator.cleanup(tmp_path)
    assert native.read_text() == "native user skill"


@pytest.mark.parametrize("ancestor", [".agents", ".agents/skills"])
def test_symlinked_ancestors_fail_before_external_writes(tmp_path: Path, ancestor: str) -> None:
    target, outside = tmp_path / "target", tmp_path / "outside"
    target.mkdir()
    outside.mkdir()
    link = target / ancestor
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(RuntimeError):
        sync_workflow_skills(target, (".agents/skills",))
    assert list(outside.iterdir()) == []


def test_symlinked_user_skill_collision_is_preserved(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text("user data")
    root = tmp_path / ".agents/skills"
    root.mkdir(parents=True)
    (root / "ai-toolkit-debug").symlink_to(outside, target_is_directory=True)
    sync_workflow_skills(tmp_path, (".agents/skills",))
    assert (root / "ai-toolkit-debug").is_symlink()
    assert (outside / "SKILL.md").read_text() == "user data"


def test_write_failure_rolls_back_all_workflow_skills(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sync_workflow_skills(tmp_path, (".agents/skills",))
    original = {path: path.read_bytes() for path in tmp_path.rglob("SKILL.md")}
    real_write = SecureTransaction.atomic_write
    calls = 0

    def fail_second(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("write failed")
        return real_write(self, *args, **kwargs)

    monkeypatch.setattr(SecureTransaction, "atomic_write", fail_second)
    with pytest.raises(OSError, match="write failed"):
        sync_workflow_skills(tmp_path, (".agents/skills",))
    assert original == {path: path.read_bytes() for path in tmp_path.rglob("SKILL.md")}


def test_refresh_removes_only_stale_owned_workflow_definitions(tmp_path: Path) -> None:
    stale = tmp_path / ".agents/skills/ai-toolkit-retired/SKILL.md"
    stale.parent.mkdir(parents=True)
    stale.write_text(MANAGED_MARKER + "\nstale generated definition")
    extra = stale.parent / "user.txt"
    extra.write_text("keep")
    sync_workflow_skills(tmp_path, (".agents/skills",))
    assert not stale.exists()
    assert extra.read_text() == "keep"


def test_doctor_accepts_complete_migration_and_warns_for_unmigrated_commands(tmp_path: Path) -> None:
    from doctor import DiagResult, check_antigravity_workflows

    generator.generate(tmp_path)
    result = DiagResult()
    check_antigravity_workflows(result, tmp_path, tmp_path / "home")
    assert result.warnings == 0
    (tmp_path / ".agents/skills/ai-toolkit-debug/SKILL.md").unlink()
    check_antigravity_workflows(result, tmp_path, tmp_path / "home")
    assert result.warnings == 1


def test_doctor_checks_global_user_workflows_without_changing_them(tmp_path: Path) -> None:
    from doctor import DiagResult, check_antigravity_workflows

    workflow = tmp_path / "home/.gemini/config/workflows/mine.md"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("user workflow")
    result = DiagResult()
    check_antigravity_workflows(result, tmp_path, tmp_path / "home")
    assert result.warnings == 1
    assert workflow.read_text() == "user workflow"


def test_unsupported_native_runtime_keeps_legacy_output_without_unsafe_skill_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    import secure_fs

    monkeypatch.setattr(secure_fs, "SECURE_DIR_FD", False)
    generator.generate(tmp_path)
    assert "Use WSL or Antigravity /migrate-workflows" in capsys.readouterr().err
    assert (tmp_path / ".agents/workflows/ai-toolkit-debug.md").is_file()
    assert (tmp_path / ".agents/skills/ai-toolkit-skill-catalogue/SKILL.md").is_file()
    assert not (tmp_path / ".agents/skills/ai-toolkit-debug").exists()
