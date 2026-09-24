# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Uninstall cleanup for the Cursor and Windsurf/Devin generator surfaces.

Each generator module exposes ``discover`` (no side effects) and ``cleanup``
over the same selection. These tests pin ownership: managed artifacts go,
user files and user text stay, symlinks are never followed, and a second
run is a no-op.

Run: npm run test:py (pytest, config in pytest.ini).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import generate_cursor_agents  # noqa: E402
import generate_cursor_hooks  # noqa: E402
import generate_cursor_mdc  # noqa: E402
import generate_cursor_rules  # noqa: E402
import generate_cursor_skills  # noqa: E402
import generate_devin_hooks  # noqa: E402
import generate_windsurf  # noqa: E402
import generate_windsurf_rules  # noqa: E402
import generate_windsurf_skills  # noqa: E402
from skill_pointer import POINTER_SKILL_NAME, write_pointer_skill  # noqa: E402

TOOLKIT_BLOCK = (
    "<!-- TOOLKIT:ai-toolkit START -->\n"
    "<!-- Auto-injected by ai-toolkit. Re-run to update. -->\n\n"
    "# Rules generated from ai-toolkit agents\n\n"
    "<!-- TOOLKIT:ai-toolkit END -->\n\n"
    "<!-- TOOLKIT:output-mode START -->\n"
    "concise\n"
    "<!-- TOOLKIT:output-mode END -->\n"
)
USER_HOOK = {"command": "./my-hook.sh", "_source": "user"}


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _files(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def _assert_cleanup(module: ModuleType, target: Path, expected: int, **kwargs: str) -> None:
    """discover == cleanup == expected, then an idempotent second run."""
    assert module.discover(target, **kwargs) == expected
    assert module.cleanup(target, **kwargs) == expected
    assert module.discover(target, **kwargs) == 0
    assert module.cleanup(target, **kwargs) == 0


# ── shared refusals ──────────────────────────────────────────────────────────

ALL_MODULES = (
    generate_cursor_rules,
    generate_windsurf,
    generate_cursor_mdc,
    generate_cursor_agents,
    generate_cursor_skills,
    generate_cursor_hooks,
    generate_windsurf_rules,
    generate_devin_hooks,
    generate_windsurf_skills,
)


@pytest.mark.parametrize("module", ALL_MODULES, ids=lambda m: m.__name__)
def test_symlinked_target_is_refused(module: ModuleType, tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(RuntimeError):
        module.cleanup(link)
    with pytest.raises(RuntimeError):
        module.discover(link)


@pytest.mark.parametrize("module", ALL_MODULES, ids=lambda m: m.__name__)
def test_empty_target_is_a_no_op(module: ModuleType, tmp_path: Path) -> None:
    assert module.discover(tmp_path) == 0
    assert module.cleanup(tmp_path) == 0
    assert _files(tmp_path) == []


# ── marker-injected rule files ───────────────────────────────────────────────

def test_cursorrules_toolkit_only_file_is_deleted(tmp_path: Path) -> None:
    _write(tmp_path / ".cursorrules", TOOLKIT_BLOCK)
    _assert_cleanup(generate_cursor_rules, tmp_path, 1)
    assert not (tmp_path / ".cursorrules").exists()


def test_cursorrules_keeps_user_text(tmp_path: Path) -> None:
    rules = _write(tmp_path / ".cursorrules", "# My rules\nBe terse.\n\n" + TOOLKIT_BLOCK)
    _assert_cleanup(generate_cursor_rules, tmp_path, 1)
    assert rules.read_text(encoding="utf-8") == "# My rules\nBe terse.\n"


def test_cursorrules_without_markers_is_untouched(tmp_path: Path) -> None:
    rules = _write(tmp_path / ".cursorrules", "user only\n")
    _assert_cleanup(generate_cursor_rules, tmp_path, 0)
    assert rules.read_text(encoding="utf-8") == "user only\n"


def test_cursorrules_symlink_is_skipped_not_followed(tmp_path: Path) -> None:
    shared = _write(tmp_path / "shared.md", TOOLKIT_BLOCK)
    project = tmp_path / "project"
    project.mkdir()
    (project / ".cursorrules").symlink_to(shared)
    _assert_cleanup(generate_cursor_rules, project, 0)
    assert shared.read_text(encoding="utf-8") == TOOLKIT_BLOCK


def test_windsurf_scopes_select_local_and_global_files(tmp_path: Path) -> None:
    local = _write(tmp_path / ".windsurfrules", "keep me\n\n" + TOOLKIT_BLOCK)
    _write(tmp_path / ".codeium/windsurf/memories/global_rules.md", TOOLKIT_BLOCK)
    _write(tmp_path / ".config/devin/AGENTS.md", TOOLKIT_BLOCK)
    _write(tmp_path / ".config/other.txt", "unrelated\n")

    _assert_cleanup(generate_windsurf, tmp_path, 1, scope="local")
    assert local.read_text(encoding="utf-8") == "keep me\n"
    assert (tmp_path / ".config/devin/AGENTS.md").exists()

    _assert_cleanup(generate_windsurf, tmp_path, 2, scope="global")
    assert not (tmp_path / ".codeium").exists()
    assert not (tmp_path / ".config/devin").exists()
    assert (tmp_path / ".config/other.txt").exists()


def test_windsurf_default_scope_covers_both(tmp_path: Path) -> None:
    _write(tmp_path / ".windsurfrules", TOOLKIT_BLOCK)
    _write(tmp_path / ".config/devin/AGENTS.md", "user\n\n" + TOOLKIT_BLOCK)
    _assert_cleanup(generate_windsurf, tmp_path, 2)
    assert (tmp_path / ".config/devin/AGENTS.md").read_text(encoding="utf-8") == "user\n"


def test_windsurf_symlinked_config_is_refused_but_other_files_are_stripped(
    tmp_path: Path,
) -> None:
    dotfiles = tmp_path / "dotfiles"
    agents = _write(dotfiles / "devin/AGENTS.md", TOOLKIT_BLOCK)
    home = tmp_path / "home"
    home.mkdir()
    (home / ".config").symlink_to(dotfiles, target_is_directory=True)
    _write(home / ".codeium/windsurf/memories/global_rules.md", TOOLKIT_BLOCK)

    with pytest.raises(RuntimeError, match="devin/AGENTS.md"):
        generate_windsurf.cleanup(home, scope="global")
    assert not (home / ".codeium").exists()
    assert agents.read_text(encoding="utf-8") == TOOLKIT_BLOCK


def test_windsurf_rejects_unknown_scope(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        generate_windsurf.cleanup(tmp_path, scope="project")


# ── Cursor .mdc rules and agents ─────────────────────────────────────────────

def test_cursor_mdc_removes_generated_rules_only(tmp_path: Path) -> None:
    generate_cursor_mdc.generate(tmp_path)
    generated = len(list((tmp_path / ".cursor/rules").glob("ai-toolkit-*.mdc")))
    assert generated >= 6
    user = _write(tmp_path / ".cursor/rules/team.mdc", "---\nalwaysApply: true\n---\n")
    plugin = _write(tmp_path / ".cursor/rules/plugin-pack-x.mdc", "plugin\n")
    _assert_cleanup(generate_cursor_mdc, tmp_path, generated)
    assert _files(tmp_path / ".cursor") == ["rules", "rules/plugin-pack-x.mdc", "rules/team.mdc"]
    assert user.exists() and plugin.exists()


def test_cursor_mdc_prunes_emptied_directories(tmp_path: Path) -> None:
    generate_cursor_mdc.generate(tmp_path)
    generate_cursor_mdc.cleanup(tmp_path)
    assert not (tmp_path / ".cursor").exists()


def test_cursor_mdc_symlinked_rules_dir_is_refused(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    victim = _write(elsewhere / "ai-toolkit-security.mdc", "not ours to follow\n")
    project = tmp_path / "project"
    (project / ".cursor").mkdir(parents=True)
    (project / ".cursor/rules").symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(RuntimeError):
        generate_cursor_mdc.cleanup(project)
    assert victim.exists()


def test_cursor_mdc_symlinked_rule_file_is_skipped(tmp_path: Path) -> None:
    victim = _write(tmp_path / "victim.mdc", "keep\n")
    rules = tmp_path / "project/.cursor/rules"
    rules.mkdir(parents=True)
    (rules / "ai-toolkit-security.mdc").symlink_to(victim)
    _assert_cleanup(generate_cursor_mdc, tmp_path / "project", 0)
    assert victim.read_text(encoding="utf-8") == "keep\n"
    assert (rules / "ai-toolkit-security.mdc").is_symlink()


def test_cursor_agents_removes_prefixed_agents_only(tmp_path: Path) -> None:
    written, _ = generate_cursor_agents.generate(tmp_path)
    user = _write(tmp_path / ".cursor/agents/my-agent.md", "---\nname: my-agent\n---\n")
    _assert_cleanup(generate_cursor_agents, tmp_path, written)
    assert _files(tmp_path / ".cursor") == ["agents", "agents/my-agent.md"]
    assert user.exists()


def test_cursor_agents_config_root_layout(tmp_path: Path) -> None:
    config_root = tmp_path / ".cursor"
    written, _ = generate_cursor_agents.generate(tmp_path, config_root=config_root)
    assert generate_cursor_agents.discover(tmp_path, config_root=config_root) == written
    assert generate_cursor_agents.cleanup(tmp_path, config_root=config_root) == written
    assert not config_root.exists()


# ── skill pointers ───────────────────────────────────────────────────────────

def test_cursor_skill_pointer_removed_user_skill_kept(tmp_path: Path) -> None:
    generate_cursor_skills.generate(tmp_path)
    user = _write(tmp_path / ".cursor/skills/mine/SKILL.md", "---\nname: mine\n---\n")
    _assert_cleanup(generate_cursor_skills, tmp_path, 1)
    assert not (tmp_path / ".cursor/skills" / POINTER_SKILL_NAME).exists()
    assert user.exists()


def test_cursor_skill_pointer_dir_with_user_extras_is_kept(tmp_path: Path) -> None:
    generate_cursor_skills.generate(tmp_path)
    notes = _write(tmp_path / ".cursor/skills" / POINTER_SKILL_NAME / "notes.md", "mine\n")
    _assert_cleanup(generate_cursor_skills, tmp_path, 1)
    assert notes.exists()
    assert not (notes.parent / "SKILL.md").exists()


def test_cursor_user_authored_skill_at_pointer_path_is_kept(tmp_path: Path) -> None:
    skill = _write(
        tmp_path / ".cursor/skills" / POINTER_SKILL_NAME / "SKILL.md",
        f"---\nname: {POINTER_SKILL_NAME}\n---\nMy own catalogue.\n",
    )
    _assert_cleanup(generate_cursor_skills, tmp_path, 0)
    assert skill.exists()


def test_windsurf_skill_pointers_by_scope(tmp_path: Path) -> None:
    generate_windsurf_skills.generate(tmp_path)
    generate_windsurf_skills.generate(tmp_path, skill_root=".codeium/windsurf/skills")
    write_pointer_skill(tmp_path, ".devin/skills", "Windsurf")  # retired location
    _write(tmp_path / ".codeium/windsurf/mcp_config.json", "{}\n")

    _assert_cleanup(generate_windsurf_skills, tmp_path, 2, scope="local")
    assert not (tmp_path / ".windsurf").exists()
    assert not (tmp_path / ".devin").exists()

    _assert_cleanup(generate_windsurf_skills, tmp_path, 1, scope="global")
    assert _files(tmp_path) == [".codeium", ".codeium/windsurf", ".codeium/windsurf/mcp_config.json"]


def test_windsurf_skill_symlinked_root_is_refused(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    write_pointer_skill(elsewhere, "skills", "Windsurf")
    project = tmp_path / "project"
    (project / ".windsurf").mkdir(parents=True)
    (project / ".windsurf/skills").symlink_to(elsewhere / "skills", target_is_directory=True)
    with pytest.raises(RuntimeError):
        generate_windsurf_skills.cleanup(project, scope="local")
    assert (elsewhere / "skills" / POINTER_SKILL_NAME / "SKILL.md").exists()


# ── Windsurf/Devin rules and workflows ───────────────────────────────────────

def test_windsurf_rules_and_workflows_removed_user_files_kept(tmp_path: Path) -> None:
    generate_windsurf_rules.generate(tmp_path)
    managed = sum(
        len(list((tmp_path / tree / sub).glob("ai-toolkit-*")))
        for tree in (".devin", ".windsurf")
        for sub in ("rules", "workflows")
    )
    user_rule = _write(tmp_path / ".devin/rules/team.md", "team rule\n")
    user_flow = _write(tmp_path / ".windsurf/workflows/release.md", "release\n")
    _assert_cleanup(generate_windsurf_rules, tmp_path, managed)
    assert _files(tmp_path) == [
        ".devin", ".devin/rules", ".devin/rules/team.md",
        ".windsurf", ".windsurf/workflows", ".windsurf/workflows/release.md",
    ]
    assert user_rule.exists() and user_flow.exists()


def test_windsurf_rules_symlinked_directory_is_refused(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    victim = _write(elsewhere / "ai-toolkit-security.md", "not ours to follow\n")
    project = tmp_path / "project"
    (project / ".devin").mkdir(parents=True)
    (project / ".devin/rules").symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(RuntimeError):
        generate_windsurf_rules.discover(project)
    with pytest.raises(RuntimeError):
        generate_windsurf_rules.cleanup(project)
    assert victim.exists()


# ── Cursor hooks ─────────────────────────────────────────────────────────────

def _cursor_config(target: Path) -> Path:
    return target / ".cursor/hooks.json"


def test_cursor_hooks_toolkit_only_install_is_fully_removed(tmp_path: Path) -> None:
    generate_cursor_hooks.generate(tmp_path)
    _assert_cleanup(generate_cursor_hooks, tmp_path, 2)
    assert not (tmp_path / ".cursor").exists()


def test_cursor_hooks_user_entries_survive(tmp_path: Path) -> None:
    config = _write(
        _cursor_config(tmp_path),
        json.dumps({"version": 1, "hooks": {"stop": [USER_HOOK]}}),
    )
    generate_cursor_hooks.generate(tmp_path)
    _assert_cleanup(generate_cursor_hooks, tmp_path, 2)
    assert json.loads(config.read_text(encoding="utf-8")) == {
        "version": 1,
        "hooks": {"stop": [USER_HOOK]},
    }
    assert _files(tmp_path / ".cursor") == ["hooks.json"]


def test_cursor_hooks_legacy_shell_left_by_old_cleanup_is_removed(tmp_path: Path) -> None:
    generate_cursor_hooks.generate(tmp_path)
    _write(_cursor_config(tmp_path), json.dumps({"version": 1}))
    _assert_cleanup(generate_cursor_hooks, tmp_path, 2)
    assert not (tmp_path / ".cursor").exists()


def test_cursor_hooks_bare_shell_without_runtime_is_kept(tmp_path: Path) -> None:
    config = _write(_cursor_config(tmp_path), json.dumps({"version": 1}))
    _assert_cleanup(generate_cursor_hooks, tmp_path, 0)
    assert config.exists()


def test_cursor_hooks_user_runtime_without_marker_is_kept(tmp_path: Path) -> None:
    runtime = _write(tmp_path / ".cursor/hooks/ai-toolkit/cursor_hook.py", "print('mine')\n")
    _assert_cleanup(generate_cursor_hooks, tmp_path, 0)
    assert runtime.exists()


def test_cursor_hooks_invalid_json_raises_and_keeps_runtime(tmp_path: Path) -> None:
    generate_cursor_hooks.generate(tmp_path)
    config = _write(_cursor_config(tmp_path), "{not json")
    with pytest.raises(ValueError):
        generate_cursor_hooks.cleanup(tmp_path)
    assert config.read_text(encoding="utf-8") == "{not json"
    assert (tmp_path / ".cursor/hooks/ai-toolkit/cursor_hook.py").exists()


def test_cursor_hooks_symlinked_cursor_dir_is_refused(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    generate_cursor_hooks.generate(elsewhere)
    home = tmp_path / "home"
    home.mkdir()
    (home / ".cursor").symlink_to(elsewhere / ".cursor", target_is_directory=True)
    with pytest.raises(RuntimeError):
        generate_cursor_hooks.cleanup(home)
    assert _cursor_config(elsewhere).exists()


# ── Devin hooks ──────────────────────────────────────────────────────────────

def test_devin_hooks_toolkit_only_file_is_deleted(tmp_path: Path) -> None:
    generate_devin_hooks.generate(tmp_path)
    _assert_cleanup(generate_devin_hooks, tmp_path, 1)
    assert not (tmp_path / ".devin").exists()


def test_devin_hooks_keep_user_groups_and_drop_untagged_toolkit_handlers(
    tmp_path: Path,
) -> None:
    user_handler = {"type": "command", "command": "./lint.sh"}
    untagged_toolkit = {
        "type": "command",
        "command": '"$HOME/.softspark/ai-toolkit/hooks/guard-path.sh"',
    }
    path = _write(
        tmp_path / ".devin/hooks.v1.json",
        json.dumps({
            "PreToolUse": [
                {"matcher": "^exec$", "hooks": [user_handler, untagged_toolkit]},
                {"matcher": "^read$", "hooks": [untagged_toolkit]},
            ],
        }),
    )
    generate_devin_hooks.generate(tmp_path)
    _assert_cleanup(generate_devin_hooks, tmp_path, 1)
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "PreToolUse": [{"matcher": "^exec$", "hooks": [user_handler]}],
    }


def test_devin_hooks_retired_cascade_file(tmp_path: Path) -> None:
    legacy = _write(
        tmp_path / ".windsurf/hooks.json",
        json.dumps({
            "theme": "dark",
            "hooks": {
                "pre_run_command": [
                    {"_source": "ai-toolkit", "command": "x"},
                    {"hooks": [{"_source": "ai-toolkit", "command": "y"}]},
                    USER_HOOK,
                ],
            },
        }),
    )
    _assert_cleanup(generate_devin_hooks, tmp_path, 1)
    assert json.loads(legacy.read_text(encoding="utf-8")) == {
        "theme": "dark",
        "hooks": {"pre_run_command": [USER_HOOK]},
    }


def test_devin_hooks_invalid_json_raises(tmp_path: Path) -> None:
    path = _write(tmp_path / ".devin/hooks.v1.json", "{broken")
    with pytest.raises(ValueError):
        generate_devin_hooks.cleanup(tmp_path)
    assert path.read_text(encoding="utf-8") == "{broken"
