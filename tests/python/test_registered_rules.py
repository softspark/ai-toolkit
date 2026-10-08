# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Client-aware registered rules, opt-in persistence and GEMINI.md migration.

A registered rule that tells the agent to call an MCP server reaches a
client's instruction file only when one of the file's reader clients has that
server configured; opt-in rules need ``--opt-in-rules``. Installer paths run
in subprocesses with ``HOME`` and ``AI_TOOLKIT_HOME`` pointed at a temporary
directory, so no test reads or writes the real home.

Run: npm run test:py (pytest, config in pytest.ini).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import registered_rules as rr  # noqa: E402
from rule_sources import (  # noqa: E402
    load_sources,
    register_path_source,
    register_url_source,
    set_rule_policy,
)


def _write_rules(rules_dir: Path, *names: str) -> None:
    rules_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        (rules_dir / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")


def _env(home: Path) -> dict[str, str]:
    return {
        **os.environ,
        "HOME": str(home),
        "AI_TOOLKIT_HOME": str(home / ".softspark" / "ai-toolkit"),
    }


def _run(code: str, home: Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", f"import sys; sys.path.insert(0, {str(SCRIPTS)!r})\n{code}"],
        env=_env(home), cwd=cwd, capture_output=True, text=True, timeout=120, check=False,
    )


# ── Requirements and opt-in ────────────────────────────────────────────────

def test_requirements_are_inferred_from_mcp_rule_names() -> None:
    assert rr.required_mcp_servers("rag-mcp-rules") == ("rag-mcp",)
    assert rr.required_mcp_servers("rag-mcp-legal-rules") == ("rag-mcp-legal",)
    assert rr.required_mcp_servers("jira-mcp") == ("jira-mcp",)
    assert rr.required_mcp_servers("team-style") == ()
    assert rr.required_mcp_servers("jira-mcp", {"requires_mcp": []}) == ()
    assert rr.required_mcp_servers("notes", {"requires_mcp": ["kb"]}) == ("kb",)


def test_legal_rule_is_opt_in_by_default_and_metadata_overrides() -> None:
    assert rr.is_opt_in("rag-mcp-legal-rules")
    assert not rr.is_opt_in("rag-mcp-rules")
    assert not rr.is_opt_in("rag-mcp-legal-rules", {"opt_in": False})
    assert rr.is_opt_in("team-style", {"opt_in": True})


def test_configured_servers_read_each_client_format(tmp_path: Path) -> None:
    home, project = tmp_path / "home", tmp_path / "project"
    (home / ".gemini" / "config").mkdir(parents=True)
    (home / ".gemini" / "config" / "mcp_config.json").write_text(
        json.dumps({"mcpServers": {"rag-mcp": {"serverUrl": "http://x"}}}))
    (project / ".agents").mkdir(parents=True)
    (project / ".agents" / "mcp_config.json").write_text(
        json.dumps({"mcpServers": {"jira": {"command": "/usr/local/bin/jira-mcp"}}}))
    (home / ".codex").mkdir()
    (home / ".codex" / "config.toml").write_text('[mcp_servers.confluence-mcp]\ncommand = "x"\n')
    (home / ".config" / "opencode").mkdir(parents=True)
    (home / ".config" / "opencode" / "opencode.json").write_text(
        json.dumps({"mcp": {"ctx": {"command": ["npx", "ctx"]}}}))

    agy = rr.configured_mcp_servers(["antigravity"], project_dir=project, home=home)
    assert {"rag-mcp", "jira", "jira-mcp"} <= agy
    assert "confluence-mcp" in rr.configured_mcp_servers(["codex"], home=home)
    assert {"ctx", "npx"} <= rr.configured_mcp_servers(["opencode"], home=home)
    assert rr.configured_mcp_servers(["unknown"], home=home) == set()


def test_selection_gates_on_reader_clients_and_opt_in(tmp_path: Path) -> None:
    rules, home = tmp_path / "rules", tmp_path / "home"
    _write_rules(rules, "rag-mcp-rules", "rag-mcp-legal-rules", "jira-mcp", "team-style")
    (home / ".gemini" / "config").mkdir(parents=True)
    (home / ".gemini" / "config" / "mcp_config.json").write_text(json.dumps(
        {"mcpServers": {"rag-mcp": {}, "rag-mcp-legal": {}}}))

    def names(**kwargs: object) -> list[str]:
        return [p.stem for p in rr.select_rule_files(rules, home=home, **kwargs)]  # type: ignore[arg-type]

    assert names(clients=None) == ["jira-mcp", "rag-mcp-legal-rules", "rag-mcp-rules", "team-style"]
    assert names(clients=["antigravity"]) == ["rag-mcp-rules", "team-style"]
    assert names(clients=["antigravity"], opted_in=["rag-mcp-legal-rules"]) == [
        "rag-mcp-legal-rules", "rag-mcp-rules", "team-style",
    ]
    assert names(clients=["gemini"]) == ["team-style"]


def test_fallback_note_only_for_mcp_rules(tmp_path: Path) -> None:
    _write_rules(tmp_path, "rag-mcp-rules", "team-style")
    rag = rr.rule_text(tmp_path / "rag-mcp-rules.md")
    assert "`rag-mcp` MCP server is not available" in rag and "`kb/`" in rag
    assert rr.rule_text(tmp_path / "team-style.md") == "# team-style\n"


# ── Policy metadata ────────────────────────────────────────────────────────

def test_policy_survives_content_refresh(tmp_path: Path) -> None:
    rules = tmp_path / "rules"
    rules.mkdir()
    register_url_source(rules, "notes", "https://example.invalid/notes.md", content=b"a")
    set_rule_policy(rules, "notes", requires_mcp=["kb"], opt_in=True)
    register_url_source(rules, "notes", "https://example.invalid/notes.md", content=b"b")
    assert load_sources(rules)["notes"]["requires_mcp"] == ["kb"]
    assert load_sources(rules)["notes"]["opt_in"] is True

    source = tmp_path / "local.md"
    source.write_text("x")
    register_path_source(rules, "local", source, content=b"x")
    set_rule_policy(rules, "local", requires_mcp=[])
    register_path_source(rules, "local", source, content=b"y")
    assert load_sources(rules)["local"]["requires_mcp"] == []


def test_add_rule_records_policy_flags(tmp_path: Path) -> None:
    home = tmp_path / "home"
    rule = tmp_path / "notes.md"
    rule.write_text("# notes\n")
    done = subprocess.run(
        [sys.executable, str(SCRIPTS / "add_rule.py"), str(rule),
         "--requires-mcp=kb,docs", "--opt-in"],
        env=_env(home), capture_output=True, text=True, timeout=60, check=False,
    )
    assert done.returncode == 0, done.stderr
    meta = load_sources(home / ".softspark" / "ai-toolkit" / "rules")["notes"]
    assert meta["requires_mcp"] == ["docs", "kb"] and meta["opt_in"] is True


# ── Generator output through the installer ────────────────────────────────

def test_generator_blocks_follow_selection_environment(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _write_rules(home / ".softspark" / "ai-toolkit" / "rules", "rag-mcp-rules", "jira-mcp")
    env = _env(home)
    plain = subprocess.run([sys.executable, str(SCRIPTS / "generate_codex.py")],
                           env=env, capture_output=True, text=True, check=True)
    assert "TOOLKIT:jira-mcp START" in plain.stdout
    gated = subprocess.run(
        [sys.executable, str(SCRIPTS / "generate_codex.py")],
        env={**env, **rr.selection_env(("codex",), None, ())},
        capture_output=True, text=True, check=True,
    )
    assert "TOOLKIT:jira-mcp" not in gated.stdout
    assert "TOOLKIT:rag-mcp-rules" not in gated.stdout


def test_global_gemini_md_migrates_legacy_copy_with_backup(tmp_path: Path) -> None:
    home = tmp_path / "home"
    gemini = home / ".gemini" / "GEMINI.md"
    gemini.parent.mkdir(parents=True)
    legacy = (
        "# Personal notes\n\nKeep me.\n\n"
        "# AI Toolkit — Gemini CLI Configuration\n\nShared AI development toolkit.\n\n"
        "## Available Agents (47)\n\n- **a**: b\n\n## Available Skills (59)\n\n- **c**: d\n\n"
        "## Workflow Guidelines\n\n- x\n\n"
        "# More personal notes\n\nKeep me too.\n\n"
        "<!-- TOOLKIT:ai-toolkit START -->\nold block\n<!-- TOOLKIT:ai-toolkit END -->\n"
    )
    gemini.write_text(legacy, encoding="utf-8")
    done = _run(
        "from pathlib import Path\n"
        "from install_steps.ai_tools import inject_with_rules\n"
        f"inject_with_rules('generate-gemini.sh', Path({str(gemini)!r}), Path({str(tmp_path / 'none')!r}),"
        " clients=('gemini', 'antigravity'))\n",
        home,
    )
    assert done.returncode == 0, done.stderr
    result = gemini.read_text(encoding="utf-8")
    assert result.count("# AI Toolkit — Gemini CLI Configuration") == 1
    assert "Keep me." in result and "Keep me too." in result
    assert "## Available Agents" not in result and "## Available Skills" not in result
    assert "old block" not in result
    assert len(result.encode("utf-8")) < rr.ANTIGRAVITY_RULE_LIMIT_BYTES
    assert "Migrated: removed unmarked legacy" in done.stdout
    backups = list((home / ".softspark" / "ai-toolkit" / "backups").glob("*GEMINI.md.*.bak"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == legacy

    again = _run(
        "from pathlib import Path\n"
        "from install_steps.ai_tools import inject_with_rules\n"
        f"inject_with_rules('generate-gemini.sh', Path({str(gemini)!r}), Path({str(tmp_path / 'none')!r}),"
        " clients=('gemini', 'antigravity'))\n",
        home,
    )
    assert "Migrated" not in again.stdout
    assert gemini.read_text(encoding="utf-8") == result


def test_oversized_file_read_by_antigravity_is_reported(tmp_path: Path) -> None:
    home = tmp_path / "home"
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# Mine\n\n" + "x" * 25_000 + "\n", encoding="utf-8")
    done = _run(
        "from pathlib import Path\n"
        "from install_steps.ai_tools import inject_with_rules\n"
        f"inject_with_rules('generate_codex.py', Path({str(agents)!r}), Path({str(tmp_path / 'none')!r}),"
        f" clients=('codex', 'antigravity'), project_dir=Path({str(tmp_path)!r}))\n",
        home,
    )
    assert done.returncode == 0, done.stderr
    assert "WARNING" in done.stdout and "truncates rule files above 24000 bytes" in done.stdout


def test_project_opt_in_rules_persist_in_registry(tmp_path: Path) -> None:
    home, project = tmp_path / "home", tmp_path / "project"
    project.mkdir()
    done = _run(
        "from install_steps.project_registry import project_opt_in_rules, register_project\n"
        f"p = {str(project)!r}\n"
        "register_project(p, editors=['antigravity'], opt_in_rules=['rag-mcp-legal-rules'])\n"
        "register_project(p, editors=['antigravity'])\n"
        "assert project_opt_in_rules(p) == ['rag-mcp-legal-rules'], project_opt_in_rules(p)\n"
        "register_project(p, opt_in_rules=[])\n"
        "assert project_opt_in_rules(p) == []\n",
        home,
    )
    assert done.returncode == 0, done.stderr
