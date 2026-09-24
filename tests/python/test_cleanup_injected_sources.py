# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Uninstall cleanup of inject-hook and inject-mcp sources.

Sources are injected with the real ``inject`` functions into a temp HOME
whose registry lives under a temp data dir, mixed with user, toolkit and
plugin-owned entries, then removed by ``cleanup_injected``: only injected
entries go, files are rewritten (never deleted), a second run is a no-op,
``discover_injected`` matches, and symlinked configs are refused.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import hook_sources  # noqa: E402
import inject_hook_cli  # noqa: E402
import inject_mcp_cli  # noqa: E402
import mcp_sources  # noqa: E402
import paths  # noqa: E402

USER_HOOK = {"matcher": "Bash", "hooks": [{"type": "command", "command": "mine.sh"}]}
TOOLKIT_HOOK = {"_source": "ai-toolkit", "matcher": "", "hooks": [{"type": "command", "command": "tk.sh"}]}
PLUGIN_HOOK = {"_source": "ai-toolkit-plugin-pack", "hooks": [{"type": "command", "command": "p.sh"}]}


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Temp HOME plus a data dir the injectors register into."""
    for name in ("CODEX_HOME", "COPILOT_HOME", "CLAUDE_USER_DATA_DIR"):
        monkeypatch.delenv(name, raising=False)
    home = tmp_path / "home"
    data_dir = home / ".softspark" / "ai-toolkit"
    home.mkdir()
    monkeypatch.setattr(paths, "TOOLKIT_DATA_DIR", data_dir)
    monkeypatch.setattr(paths, "EXTERNAL_HOOKS_DIR", data_dir / "hooks" / "external")
    monkeypatch.setattr(hook_sources, "EXTERNAL_HOOKS_DIR", data_dir / "hooks" / "external")
    monkeypatch.setattr(mcp_sources, "EXTERNAL_MCP_DIR", data_dir / "mcp-templates" / "external")
    return home, data_dir


def _cycle(module, home: Path, data_dir: Path, expected: int) -> None:
    assert module.discover_injected(home, data_dir) == expected
    assert module.cleanup_injected(home, data_dir) == expected
    assert module.discover_injected(home, data_dir) == 0
    assert module.cleanup_injected(home, data_dir) == 0


# ------------------------------------------------------------------------ hooks


def _inject_hooks(tmp_path: Path, home: Path, name: str = "ext") -> Path:
    source = tmp_path / f"{name}.json"
    source.write_text(json.dumps({"hooks": {
        "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": f"{name}.sh"}]}],
        "Stop": [{"hooks": [{"type": "command", "command": f"{name}-stop.sh"}]}],
    }}))
    inject_hook_cli.inject(str(source), str(home))
    return source


def _seed_settings(home: Path) -> Path:
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps({
        "model": "opus",
        "hooks": {"PreToolUse": [USER_HOOK, TOOLKIT_HOOK], "Stop": [PLUGIN_HOOK]},
    }))
    return settings


def test_injected_hooks_removed_everything_else_kept(tmp_path: Path, env) -> None:
    home, data_dir = env
    settings = _seed_settings(home)
    codex = home / ".codex" / "hooks.json"
    codex.parent.mkdir()
    codex.write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "user-codex.sh"}]},
    ]}}))
    _inject_hooks(tmp_path, home)
    assert "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-external-" in codex.read_text()

    # 2 settings entries + 2 Codex handlers.
    _cycle(inject_hook_cli, home, data_dir, 4)

    data = json.loads(settings.read_text())
    assert data["model"] == "opus"
    assert data["hooks"] == {"PreToolUse": [USER_HOOK, TOOLKIT_HOOK], "Stop": [PLUGIN_HOOK]}
    codex_text = codex.read_text()
    assert "user-codex.sh" in codex_text and "ext.sh" not in codex_text
    assert (data_dir / "hooks" / "external" / "sources.json").is_file()


def test_injected_hook_with_dropped_tag_matched_by_registry(tmp_path: Path, env) -> None:
    home, data_dir = env
    _inject_hooks(tmp_path, home)
    settings = home / ".claude" / "settings.json"
    data = json.loads(settings.read_text())
    for entries in data["hooks"].values():
        for entry in entries:
            entry.pop("_source", None)  # Claude Code rewrote settings.json
    data["hooks"]["PreToolUse"].append(USER_HOOK)
    settings.write_text(json.dumps(data))

    # 2 untagged settings entries matched via the recorded source file + 2 Codex handlers.
    _cycle(inject_hook_cli, home, data_dir, 4)
    assert json.loads(settings.read_text())["hooks"] == {"PreToolUse": [USER_HOOK]}


def test_unregistered_tag_survives_and_empty_hooks_key_dropped(tmp_path: Path, env) -> None:
    home, data_dir = env
    _inject_hooks(tmp_path, home)
    settings = home / ".claude" / "settings.json"
    data = json.loads(settings.read_text())
    data["theme"] = "dark"
    settings.write_text(json.dumps(data))

    _cycle(inject_hook_cli, home, data_dir, 4)  # 2 settings entries + 2 Codex handlers
    assert json.loads(settings.read_text()) == {"theme": "dark"}

    other = {"_source": "other-tool", "hooks": [{"type": "command", "command": "x"}]}
    settings.write_text(json.dumps({"hooks": {"Stop": [other]}}))
    _cycle(inject_hook_cli, home, data_dir, 0)
    assert json.loads(settings.read_text()) == {"hooks": {"Stop": [other]}}


def test_hooks_nothing_installed_is_noop(env) -> None:
    home, data_dir = env
    _cycle(inject_hook_cli, home, data_dir, 0)
    settings = _seed_settings(home)
    before = settings.read_bytes()
    _cycle(inject_hook_cli, home, data_dir, 0)
    assert settings.read_bytes() == before


def test_hooks_symlinked_settings_refused(tmp_path: Path, env) -> None:
    home, data_dir = env
    _inject_hooks(tmp_path, home)
    (home / ".claude" / "settings.json").unlink()
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"hooks": {"Stop": [
        {"_source": "ext", "hooks": [{"type": "command", "command": "x"}]},
    ]}}))
    (home / ".claude" / "settings.json").symlink_to(outside)
    before = outside.read_bytes()

    with pytest.raises(RuntimeError, match="symlinked"):
        inject_hook_cli.discover_injected(home, data_dir)
    with pytest.raises(RuntimeError, match="symlinked"):
        inject_hook_cli.cleanup_injected(home, data_dir)
    assert outside.read_bytes() == before


# -------------------------------------------------------------------------- MCP


def _inject_mcp(tmp_path: Path, home: Path) -> dict:
    servers = {
        "ext-a": {"command": "npx", "args": ["-y", "ext-a"]},
        "ext-b": {"url": "https://example.invalid/mcp"},
    }
    template = tmp_path / "ext-mcp.json"
    template.write_text(json.dumps({"mcpServers": servers}))
    inject_mcp_cli.inject(str(template), str(home))
    return servers


def test_injected_mcp_removed_user_and_plugin_servers_kept(tmp_path: Path, env) -> None:
    home, data_dir = env
    servers = _inject_mcp(tmp_path, home)
    mcp_json = home / ".mcp.json"
    config = json.loads(mcp_json.read_text())
    config["mcpServers"]["mine"] = {"command": "mine"}
    config["mcpServers"]["plug"] = {"command": "p", "_source": "ai-toolkit-plugin-pack"}
    config["mcpServers"]["foreign"] = {"command": "f", "_source": "other-tool"}
    config["other"] = 1
    mcp_json.write_text(json.dumps(config))
    cursor = home / ".cursor" / "mcp.json"
    cursor_data = json.loads(cursor.read_text())
    cursor_data["mcpServers"]["ext-b"]["url"] = "https://edited.invalid/mcp"
    cursor_data["mcpServers"]["mine"] = {"command": "mine"}
    cursor.write_text(json.dumps(cursor_data))
    claude = home / ".claude.json"
    assert set(json.loads(claude.read_text())["mcpServers"]) == set(servers)

    expected = inject_mcp_cli.discover_injected(home, data_dir)
    # 2 in ~/.mcp.json + at least claude (2) and cursor (1, the edited one stays).
    assert expected >= 5
    _cycle(inject_mcp_cli, home, data_dir, expected)

    config = json.loads(mcp_json.read_text())
    assert config["mcpServers"] == {
        "mine": {"command": "mine"},
        "plug": {"command": "p", "_source": "ai-toolkit-plugin-pack"},
        "foreign": {"command": "f", "_source": "other-tool"},
    }
    assert config["other"] == 1
    assert json.loads(claude.read_text())["mcpServers"] == {}
    assert json.loads(cursor.read_text())["mcpServers"] == {
        "ext-b": {"url": "https://edited.invalid/mcp"},
        "mine": {"command": "mine"},
    }
    propagated = [
        path for path in home.rglob("*")
        if path.is_file() and path.suffix in {".json", ".toml"}
        and data_dir not in path.parents and path not in {mcp_json, cursor}
    ]
    assert len(propagated) >= 8  # every global editor config inject wrote
    for path in propagated:
        assert "ext-a" not in path.read_text() and "ext-b" not in path.read_text(), path
    assert (data_dir / "mcp-templates" / "external" / "sources.json").is_file()


def test_injected_mcp_copies_matched_through_registry(tmp_path: Path, env) -> None:
    home, data_dir = env
    _inject_mcp(tmp_path, home)
    mcp_json = home / ".mcp.json"
    mcp_json.write_text(json.dumps({"mcpServers": {}}))  # tags gone, copies remain

    assert inject_mcp_cli.cleanup_injected(home, data_dir) > 0
    assert json.loads((home / ".claude.json").read_text())["mcpServers"] == {}
    assert json.loads((home / ".cursor" / "mcp.json").read_text())["mcpServers"] == {}


def test_mcp_nothing_installed_is_noop(env) -> None:
    home, data_dir = env
    _cycle(inject_mcp_cli, home, data_dir, 0)


def test_mcp_symlinked_config_refused(tmp_path: Path, env) -> None:
    home, data_dir = env
    _inject_mcp(tmp_path, home)
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"mcpServers": {"x": {"command": "x", "_source": "ext-mcp"}}}))
    (home / ".mcp.json").unlink()
    (home / ".mcp.json").symlink_to(outside)
    before = outside.read_bytes()

    with pytest.raises(RuntimeError, match="symlinked"):
        inject_mcp_cli.cleanup_injected(home, data_dir)
    assert outside.read_bytes() == before
