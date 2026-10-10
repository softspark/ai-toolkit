# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Global Claude MCP changes reach every claude-switch profile.

claude-switch launches each account with its own ``CLAUDE_CONFIG_DIR``, and
Claude Code then reads user-scope MCP servers from that directory's
``.claude.json``, not from ``~/.claude.json``. Each case runs in a subprocess
with ``HOME`` pointed at a temporary directory and no inherited profile
variables, so the real home is never read or written.

Run: npm run test:py (pytest, config in pytest.ini).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
JIRA = {"type": "stdio", "command": "jira-mcp", "args": []}
RAG = {"type": "http", "url": "http://localhost:8081/mcp/sse"}


def _run(home: Path, code: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items()
           if k not in {"CLAUDE_CONFIG_DIR", "CLAUDE_SWITCH_CONFIG", "AI_TOOLKIT_HOME", "SOFTSPARK_HOME",
                        "CODEX_HOME", "COPILOT_HOME", "CLAUDE_USER_DATA_DIR"}}
    env.update(HOME=str(home), **extra_env)
    return subprocess.run(
        [sys.executable, "-c", f"import sys; sys.path.insert(0, {str(SCRIPTS)!r})\n{code}"],
        env=env, capture_output=True, text=True, timeout=60, check=False,
    )


def _registry(home: Path, default: str, accounts: dict[str, str | None]) -> None:
    path = home / ".softspark" / "ai-toolkit" / "claude-switch.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "default": default,
                                "accounts": accounts, "projects": {}}))


def _servers(path: Path) -> dict[str, object]:
    return json.loads(path.read_text()).get("mcpServers", {}) if path.exists() else {}


def test_without_profiles_global_scope_is_home_claude_json(tmp_path: Path) -> None:
    done = _run(tmp_path, "from mcp_editors import claude_user_configs\nprint(claude_user_configs())")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == str([tmp_path / ".claude.json"])


def test_global_install_and_remove_reach_every_profile(tmp_path: Path) -> None:
    profiles = tmp_path / ".softspark" / "ai-toolkit" / "claude-profiles"
    primary, client = profiles / "primary", profiles / "client"
    for directory in (primary, client):
        directory.mkdir(parents=True)
    (primary / ".claude.json").write_text(json.dumps({"oauthAccount": {"id": "kept"}}))
    _registry(tmp_path, "default", {"default": str(primary), "client": str(client)})

    done = _run(tmp_path, (
        "from mcp_editors import claude_user_configs, install_servers\n"
        "print([str(p) for p in claude_user_configs()])\n"
        f"install_servers(['claude'], {{'jira': {JIRA!r}}}, scope='global')\n"
    ))
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout.replace("'", '"')) == [
        str(primary / ".claude.json"), str(client / ".claude.json"),
    ]
    assert _servers(primary / ".claude.json") == {"jira": JIRA}
    assert _servers(client / ".claude.json") == {"jira": JIRA}
    assert json.loads((primary / ".claude.json").read_text())["oauthAccount"] == {"id": "kept"}
    assert not (tmp_path / ".claude.json").exists()

    done = _run(tmp_path, "from mcp_editors import remove_servers\n"
                          "remove_servers(['claude'], ['jira'], scope='global')\n")
    assert done.returncode == 0, done.stderr
    assert _servers(primary / ".claude.json") == {}
    assert _servers(client / ".claude.json") == {}


def _two_profiles(home: Path) -> tuple[Path, Path]:
    profiles = home / ".softspark" / "ai-toolkit" / "claude-profiles"
    primary, client = profiles / "primary", profiles / "client"
    for directory in (primary, client):
        directory.mkdir(parents=True)
    _registry(home, "default", {"default": str(primary), "client": str(client)})
    return primary, client


def _rag_template(home: Path) -> Path:
    template = home / "rag-mcp.json"
    template.write_text(json.dumps({"mcpServers": {"rag": RAG}}))
    return template


def test_inject_mcp_and_remove_mcp_reach_every_profile(tmp_path: Path) -> None:
    primary, client = _two_profiles(tmp_path)
    template = _rag_template(tmp_path)

    done = _run(tmp_path, f"import inject_mcp_cli\ninject_mcp_cli.inject({str(template)!r}, {str(tmp_path)!r})")
    assert done.returncode == 0, done.stderr
    assert _servers(primary / ".claude.json") == {"rag": RAG}
    assert _servers(client / ".claude.json") == {"rag": RAG}

    done = _run(tmp_path, f"import inject_mcp_cli\ninject_mcp_cli.remove('rag-mcp', {str(tmp_path)!r})")
    assert done.returncode == 0, done.stderr
    assert _servers(primary / ".claude.json") == {}
    assert _servers(client / ".claude.json") == {}


def test_uninstall_cleanup_of_injected_mcp_reaches_every_profile(tmp_path: Path) -> None:
    primary, client = _two_profiles(tmp_path)
    template = _rag_template(tmp_path)
    data_dir = tmp_path / ".softspark" / "ai-toolkit"
    # Seeded as propagation writes them, so this checks cleanup on its own.
    for profile in (primary, client):
        (profile / ".claude.json").write_text(json.dumps({"mcpServers": {"rag": RAG}}))

    done = _run(tmp_path, (
        "from pathlib import Path\nimport inject_mcp_cli\n"
        f"inject_mcp_cli.inject({str(template)!r}, {str(tmp_path)!r})\n"
        f"print(inject_mcp_cli.cleanup_injected(Path({str(tmp_path)!r}), Path({str(data_dir)!r})))"
    ))
    assert done.returncode == 0, done.stderr
    assert _servers(primary / ".claude.json") == {}
    assert _servers(client / ".claude.json") == {}


def test_inject_mcp_into_another_directory_leaves_profiles_alone(tmp_path: Path) -> None:
    primary, client = _two_profiles(tmp_path)
    template = _rag_template(tmp_path)
    target = tmp_path / "sandbox"
    target.mkdir()

    done = _run(tmp_path, f"import inject_mcp_cli\ninject_mcp_cli.inject({str(template)!r}, {str(target)!r})")
    assert done.returncode == 0, done.stderr
    assert _servers(target / ".claude.json") == {"rag": RAG}
    assert _servers(primary / ".claude.json") == {}
    assert _servers(client / ".claude.json") == {}


def test_legacy_default_account_keeps_home_claude_json_first(tmp_path: Path) -> None:
    client = tmp_path / "profiles" / "client"
    client.mkdir(parents=True)
    _registry(tmp_path, "default", {"default": None, "client": str(client)})
    done = _run(tmp_path, "from mcp_editors import resolve_editor_path\n"
                          "print(resolve_editor_path('claude', 'global'))")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == str(tmp_path / ".claude.json")


def test_active_config_dir_counts_only_inside_home(tmp_path: Path) -> None:
    inside = tmp_path / "manual-profile"
    outside = tmp_path.parent / f"{tmp_path.name}-elsewhere"
    code = "from mcp_editors import claude_user_configs\nprint([str(p) for p in claude_user_configs()])"
    # Without claude-switch, Claude reads only the active directory's config.
    done = _run(tmp_path, code, CLAUDE_CONFIG_DIR=str(inside))
    assert json.loads(done.stdout.replace("'", '"')) == [str(inside / ".claude.json")]
    done = _run(tmp_path, code, CLAUDE_CONFIG_DIR=str(outside))
    assert json.loads(done.stdout.replace("'", '"')) == [str(tmp_path / ".claude.json")]


def test_plugin_install_refuses_a_user_server_in_any_profile(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles"
    primary, client = profiles / "primary", profiles / "client"
    for directory in (primary, client):
        directory.mkdir(parents=True)
    (client / ".claude.json").write_text(json.dumps({"mcpServers": {"context7": {"command": "mine"}}}))
    _registry(tmp_path, "default", {"default": str(primary), "client": str(client)})
    done = _run(tmp_path, (
        "from pathlib import Path\n"
        "from plugin_mcp import prepare_plugin_mcp_install\n"
        "try:\n"
        "    prepare_plugin_mcp_install('demo', 'claude', {'includes': {'mcp': ['context7']}}, Path('.'), None)\n"
        "except RuntimeError as error:\n"
        "    print(error)\n"
    ))
    assert done.returncode == 0, done.stderr
    assert "Refusing user-owned MCP server collision for 'context7'" in done.stdout
    assert str(client / ".claude.json") in done.stdout
