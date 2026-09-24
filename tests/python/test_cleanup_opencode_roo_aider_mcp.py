# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Uninstall cleanup/discover for OpenCode, Roo, Aider and MCP template servers.

Each surface is installed with its real generator, mixed with user-owned
content, then cleaned: managed output goes, user content stays, a second run
is a no-op, ``discover`` matches ``cleanup``, and symlinks are never followed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import generate_aider_conf  # noqa: E402
import generate_conventions  # noqa: E402
import generate_opencode  # noqa: E402
import generate_opencode_agents  # noqa: E402
import generate_opencode_commands  # noqa: E402
import generate_opencode_json  # noqa: E402
import generate_opencode_plugin  # noqa: E402
import generate_roo_modes  # noqa: E402
import generate_roo_rules  # noqa: E402
import mcp_editors  # noqa: E402
from injection import markers_end, markers_start  # noqa: E402

SECTION = f"{markers_start()}toolkit text{markers_end()}\n"


def _roots(tmp_path: Path, scope: str) -> tuple[Path, Path | None, Path]:
    """Return (target, config_root argument, effective OpenCode base)."""
    if scope == "global":
        base = tmp_path / ".config" / "opencode"
        return tmp_path, base, base
    return tmp_path, None, tmp_path / ".opencode"


def _check_cycle(module, target: Path, expected: int, **kwargs) -> None:
    assert module.discover(target, **kwargs) == expected
    assert module.cleanup(target, **kwargs) == expected
    assert module.discover(target, **kwargs) == 0
    assert module.cleanup(target, **kwargs) == 0


# --------------------------------------------------------------------- OpenCode


@pytest.mark.parametrize("scope", ["local", "global"])
def test_opencode_native_files_removed_user_files_kept(tmp_path: Path, scope: str) -> None:
    target, config_root, base = _roots(tmp_path, scope)
    written_agents, _ = generate_opencode_agents.generate(target, config_root=config_root)
    written_commands, _ = generate_opencode_commands.generate(target, config_root=config_root)
    generate_opencode_plugin.generate(target, config_root=config_root)
    (base / "agents" / "mine.md").write_text("user agent\n")
    (base / "commands" / "mine.md").write_text("user command\n")

    _check_cycle(generate_opencode_agents, target, written_agents, config_root=config_root)
    _check_cycle(generate_opencode_commands, target, written_commands, config_root=config_root)
    _check_cycle(generate_opencode_plugin, target, 1, config_root=config_root)

    assert (base / "agents" / "mine.md").read_text() == "user agent\n"
    assert (base / "commands" / "mine.md").read_text() == "user command\n"
    assert not list(base.rglob("ai-toolkit-*"))
    assert not (base / "plugins").exists()


@pytest.mark.parametrize("scope", ["local", "global"])
def test_opencode_prunes_only_emptied_directories(tmp_path: Path, scope: str) -> None:
    target, config_root, base = _roots(tmp_path, scope)
    generate_opencode_agents.generate(target, config_root=config_root)
    generate_opencode_commands.generate(target, config_root=config_root)
    generate_opencode_plugin.generate(target, config_root=config_root)

    for module in (generate_opencode_agents, generate_opencode_commands, generate_opencode_plugin):
        module.cleanup(target, config_root=config_root)

    assert not base.exists()
    assert target.is_dir()
    if scope == "global":
        assert (tmp_path / ".config").is_dir()


def test_opencode_plugin_without_generated_header_is_kept(tmp_path: Path) -> None:
    plugin = tmp_path / ".opencode" / "plugins" / "ai-toolkit-hooks.js"
    plugin.parent.mkdir(parents=True)
    plugin.write_text("// my own plugin\n")

    _check_cycle(generate_opencode_plugin, tmp_path, 0)
    assert plugin.read_text() == "// my own plugin\n"


def test_opencode_symlinked_file_skipped_and_root_refused(tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("keep me\n")
    agents = tmp_path / ".opencode" / "agents"
    agents.mkdir(parents=True)
    (agents / "ai-toolkit-evil.md").symlink_to(outside)

    _check_cycle(generate_opencode_agents, tmp_path, 0)
    assert (agents / "ai-toolkit-evil.md").is_symlink()
    assert outside.read_text() == "keep me\n"

    real = tmp_path / "real-commands"
    real.mkdir()
    (real / "ai-toolkit-x.md").write_text("x\n")
    (tmp_path / ".opencode" / "commands").symlink_to(real, target_is_directory=True)
    with pytest.raises(RuntimeError, match="symlinked"):
        generate_opencode_commands.discover(tmp_path)
    with pytest.raises(RuntimeError, match="symlinked"):
        generate_opencode_commands.cleanup(tmp_path)
    assert (real / "ai-toolkit-x.md").is_file()


@pytest.mark.parametrize("scope", ["local", "global"])
def test_opencode_json_removed_only_when_schema_is_all_that_remains(
    tmp_path: Path, scope: str
) -> None:
    output = tmp_path / ".config" / "opencode" / "opencode.json" if scope == "global" else None
    path, _ = generate_opencode_json.merge_into_opencode_json(tmp_path, output_path=output)
    assert json.loads(path.read_text()) == {"$schema": generate_opencode_json.SCHEMA_URL}

    _check_cycle(generate_opencode_json, tmp_path, 1, output_path=output)
    assert not path.exists()
    assert tmp_path.is_dir()
    if scope == "global":
        assert not path.parent.exists()


@pytest.mark.parametrize(
    "document",
    [
        {"$schema": generate_opencode_json.SCHEMA_URL, "theme": "dark"},
        {"$schema": generate_opencode_json.SCHEMA_URL, "mcp": {"db": {"type": "local"}}},
        {"$schema": "https://example.invalid/other.json"},
    ],
)
def test_opencode_json_with_user_or_mirrored_data_is_kept(tmp_path: Path, document: dict) -> None:
    path = tmp_path / "opencode.json"
    path.write_text(json.dumps(document))

    _check_cycle(generate_opencode_json, tmp_path, 0)
    assert json.loads(path.read_text()) == document


def test_opencode_json_invalid_or_symlinked_is_kept(tmp_path: Path) -> None:
    (tmp_path / "opencode.json").write_text("{not json")
    _check_cycle(generate_opencode_json, tmp_path, 0)
    assert (tmp_path / "opencode.json").read_text() == "{not json"

    other = tmp_path / "other"
    other.mkdir()
    target = other / "opencode.json"
    target.write_text(json.dumps({"$schema": generate_opencode_json.SCHEMA_URL}))
    (tmp_path / "opencode.json").unlink()
    (tmp_path / "opencode.json").symlink_to(target)
    _check_cycle(generate_opencode_json, tmp_path, 0)
    assert target.is_file()


@pytest.mark.parametrize("scope", ["local", "global"])
def test_opencode_agents_md_sections_stripped(tmp_path: Path, scope: str) -> None:
    config_root = tmp_path / ".config" / "opencode" if scope == "global" else None
    agents_md = (config_root or tmp_path) / "AGENTS.md"
    agents_md.parent.mkdir(parents=True, exist_ok=True)
    agents_md.write_text(f"# Mine\n\n{SECTION}")

    _check_cycle(generate_opencode, tmp_path, 1, config_root=config_root)
    assert agents_md.read_text() == "# Mine\n"

    agents_md.write_text(SECTION)
    _check_cycle(generate_opencode, tmp_path, 1, config_root=config_root)
    assert not agents_md.exists()
    if scope == "global":
        assert not config_root.exists()


# -------------------------------------------------------------------------- Roo


@pytest.mark.parametrize("scope", ["local", "global"])
def test_roo_rules_removed_user_rules_kept(tmp_path: Path, scope: str) -> None:
    output_root = tmp_path / ".roo" / "rules" if scope == "global" else None
    generate_roo_rules.generate(tmp_path, output_root=output_root)
    rules = tmp_path / ".roo" / "rules"
    managed = len(list(rules.glob("ai-toolkit-*.md")))
    assert managed > 0

    _check_cycle(generate_roo_rules, tmp_path, managed, output_root=output_root)
    assert not (tmp_path / ".roo").exists()

    generate_roo_rules.generate(tmp_path, output_root=output_root)
    (rules / "mine.md").write_text("user rule\n")
    (tmp_path / ".roo" / "mcp.json").write_text("{}\n")
    _check_cycle(generate_roo_rules, tmp_path, managed, output_root=output_root)
    assert (rules / "mine.md").read_text() == "user rule\n"
    assert (tmp_path / ".roo" / "mcp.json").is_file()


def test_roo_rules_symlinked_root_refused(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (real / "ai-toolkit-code-style.md").write_text("x\n")
    (tmp_path / ".roo").mkdir()
    (tmp_path / ".roo" / "rules").symlink_to(real, target_is_directory=True)

    with pytest.raises(RuntimeError, match="symlinked"):
        generate_roo_rules.cleanup(tmp_path)
    assert (real / "ai-toolkit-code-style.md").is_file()


def _generated_roomodes(capsys: pytest.CaptureFixture[str]) -> dict:
    generate_roo_modes.main()
    return json.loads(capsys.readouterr().out)


def test_roomodes_all_toolkit_modes_deletes_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    roomodes = tmp_path / ".roomodes"
    roomodes.write_text(json.dumps(_generated_roomodes(capsys), indent=2))

    _check_cycle(generate_roo_modes, tmp_path, 1)
    assert not roomodes.exists()


def test_roomodes_user_modes_and_keys_survive(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = _generated_roomodes(capsys)
    toolkit_mode = data["customModes"][0]
    legacy_mode = {k: v for k, v in data["customModes"][1].items()
                   if k not in {"description", "whenToUse"}}
    user_mode = {"slug": "my-mode", "name": "Mine", "roleDefinition": "a\n\nb",
                 "groups": generate_roo_modes.MODE_GROUPS}
    edited_mode = dict(data["customModes"][2], groups=["read"])
    roomodes = tmp_path / ".roomodes"
    roomodes.write_text(json.dumps({
        "customModes": [toolkit_mode, legacy_mode, user_mode, edited_mode],
        "extra": True,
    }))

    _check_cycle(generate_roo_modes, tmp_path, 1)
    assert json.loads(roomodes.read_text()) == {
        "customModes": [user_mode, edited_mode],
        "extra": True,
    }


def test_roomodes_invalid_or_symlinked_is_kept(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    roomodes = tmp_path / ".roomodes"
    roomodes.write_text("not json")
    _check_cycle(generate_roo_modes, tmp_path, 0)
    assert roomodes.read_text() == "not json"

    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps(_generated_roomodes(capsys)))
    roomodes.unlink()
    roomodes.symlink_to(outside)
    _check_cycle(generate_roo_modes, tmp_path, 0)
    assert json.loads(outside.read_text())["customModes"]


# ------------------------------------------------------------------------ Aider


def test_aider_generated_config_removed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    generate_aider_conf.main()
    (tmp_path / ".aider.conf.yml").write_text(capsys.readouterr().out)

    _check_cycle(generate_aider_conf, tmp_path, 1)
    assert not (tmp_path / ".aider.conf.yml").exists()


def test_aider_global_config_format_removed(tmp_path: Path) -> None:
    # Same first line install_steps.ai_tools._install_aider_global writes.
    (tmp_path / ".aider.conf.yml").write_text(
        "# Aider configuration generated by ai-toolkit\n"
        "# Aider docs: https://aider.chat/docs/config/aider_conf.html\n\narchitect: true\n"
    )
    _check_cycle(generate_aider_conf, tmp_path, 1)


@pytest.mark.parametrize(
    "content",
    ["model: mine\n", "model: x\n# Aider configuration generated by ai-toolkit\n"],
)
def test_aider_user_config_kept(tmp_path: Path, content: str) -> None:
    (tmp_path / ".aider.conf.yml").write_text(content)
    _check_cycle(generate_aider_conf, tmp_path, 0)
    assert (tmp_path / ".aider.conf.yml").read_text() == content


def test_aider_symlinked_config_skipped(tmp_path: Path) -> None:
    outside = tmp_path / "outside.yml"
    outside.write_text("# Aider configuration generated by ai-toolkit\n")
    (tmp_path / ".aider.conf.yml").symlink_to(outside)
    _check_cycle(generate_aider_conf, tmp_path, 0)
    assert outside.is_file()


@pytest.mark.parametrize("global_install", [False, True])
def test_aider_conventions_stripped_then_deleted(tmp_path: Path, global_install: bool) -> None:
    name = ".aider-ai-toolkit-CONVENTIONS.md" if global_install else "CONVENTIONS.md"
    path = tmp_path / name
    path.write_text(f"# Team rules\n\n{SECTION}")

    _check_cycle(generate_conventions, tmp_path, 1, global_install=global_install)
    assert path.read_text() == "# Team rules\n"

    path.write_text(SECTION)
    _check_cycle(generate_conventions, tmp_path, 1, global_install=global_install)
    assert not path.exists()


def test_aider_conventions_without_markers_kept(tmp_path: Path) -> None:
    (tmp_path / "CONVENTIONS.md").write_text("# Only mine\n")
    _check_cycle(generate_conventions, tmp_path, 0)
    assert (tmp_path / "CONVENTIONS.md").read_text() == "# Only mine\n"


# -------------------------------------------------------------------------- MCP


@pytest.fixture
def mcp_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("CODEX_HOME", "COPILOT_HOME", "CLAUDE_USER_DATA_DIR"):
        monkeypatch.delenv(name, raising=False)
    home = tmp_path / "home"
    home.mkdir()
    return home


def _template_servers(name: str) -> dict:
    data = json.loads((mcp_editors.TEMPLATES_DIR / f"{name}.json").read_text())
    return data["mcpServers"]


def test_mcp_template_servers_removed_user_servers_kept(mcp_home: Path) -> None:
    servers = _template_servers("context7")
    editors = ["claude", "cursor", "codex"]
    mcp_editors.install_servers(editors, servers, scope="global", home=mcp_home)
    user = {"mine": {"command": "my-server"}}
    mcp_editors.install_servers(editors, user, scope="global", home=mcp_home)
    claude = mcp_home / ".claude.json"
    data = json.loads(claude.read_text())
    data["projects"] = {"/x": {"allowedTools": []}}
    claude.write_text(json.dumps(data))

    expected = len(servers) * len(editors)
    assert mcp_editors.discover_template_servers(["context7"], home=mcp_home) == expected
    assert mcp_editors.cleanup_template_servers(["context7"], home=mcp_home) == expected
    assert mcp_editors.discover_template_servers(["context7"], home=mcp_home) == 0
    assert mcp_editors.cleanup_template_servers(["context7"], home=mcp_home) == 0

    claude_data = json.loads(claude.read_text())
    assert claude_data["mcpServers"] == user
    assert claude_data["projects"] == {"/x": {"allowedTools": []}}
    cursor = json.loads((mcp_home / ".cursor" / "mcp.json").read_text())
    assert cursor["mcpServers"] == user
    codex = (mcp_home / ".codex" / "config.toml").read_text()
    assert "mine" in codex and "context7" not in codex


def test_mcp_edited_or_unrecorded_servers_kept(mcp_home: Path, tmp_path: Path) -> None:
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "tpl.json").write_text(json.dumps({"mcpServers": {"srv": {"command": "a"}}}))
    cursor = mcp_home / ".cursor" / "mcp.json"
    cursor.parent.mkdir()
    edited = {"mcpServers": {"srv": {"command": "a", "args": ["--mine"]}}}
    cursor.write_text(json.dumps(edited))

    for names in (["tpl"], ["other"], ["../tpl"]):
        assert mcp_editors.discover_template_servers(names, home=mcp_home, templates_dir=templates) == 0
        assert mcp_editors.cleanup_template_servers(names, home=mcp_home, templates_dir=templates) == 0
    assert json.loads(cursor.read_text()) == edited


def test_mcp_symlinked_config_refused(mcp_home: Path, tmp_path: Path) -> None:
    servers = _template_servers("context7")
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"mcpServers": servers}))
    (mcp_home / ".cursor").mkdir()
    (mcp_home / ".cursor" / "mcp.json").symlink_to(outside)

    with pytest.raises(RuntimeError, match="symlinked"):
        mcp_editors.cleanup_template_servers(["context7"], home=mcp_home)
    assert json.loads(outside.read_text()) == {"mcpServers": servers}
