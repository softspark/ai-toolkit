# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Account routing must preserve native defaults and isolate named Codex homes."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "codex_switch.py"


@dataclass
class Installation:
    home: Path
    env: dict[str, str]
    cwd: Path
    executable: Path

    @property
    def registry(self) -> Path:
        return self.home / ".softspark/ai-toolkit/codex-switch.json"

    def profile(self, name: str) -> Path:
        return self.home / ".softspark/ai-toolkit/codex-profiles" / name

    def run(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], env=self.env, cwd=cwd or self.cwd,
            capture_output=True, text=True, timeout=15, check=False,
        )

    def success(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        result = self.run(*args, cwd=cwd)
        assert result.returncode == 0, result.stderr
        return result

    def status(self, *args: str, cwd: Path | None = None) -> dict:
        return json.loads(self.success("status", "--json", *args, cwd=cwd).stdout)

    def native(self, *args: str, cwd: Path | None = None) -> dict:
        return json.loads(self.success("run", *args, cwd=cwd).stdout)


@pytest.fixture
def installation(tmp_path):
    home, binary, cwd = tmp_path / "home", tmp_path / "bin", tmp_path / "workspace"
    for directory in (home, binary, cwd):
        directory.mkdir()
    env = dict(os.environ)
    for name in ("AI_TOOLKIT_HOME", "SOFTSPARK_HOME", "CODEX_SWITCH_CONFIG", "CODEX_HOME",
                 "CODEX_SQLITE_HOME", "CODEX_ACCESS_TOKEN", "CODEX_API_KEY", "OPENAI_API_KEY",
                 "GIT_DIR", "GIT_WORK_TREE"):
        env.pop(name, None)
    env.update(HOME=str(home), PATH=f"{binary}{os.pathsep}{env.get('PATH', '')}")
    executable = binary / "codex"
    # Reviewed fake: prints controlled routing metadata; never calls a provider.
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json, os, signal, sys\n"
        "if '--fake-signal' in sys.argv: os.kill(os.getpid(), signal.SIGTERM)\n"
        "if '--fake-exit' in sys.argv: sys.exit(23)\n"
        "print(json.dumps({'argv': sys.argv[1:], 'home': os.environ.get('CODEX_HOME'), "
        "'sqlite': os.environ.get('CODEX_SQLITE_HOME'), 'cwd': os.getcwd(), "
        "'custom': os.environ.get('SWITCH_TEST_CUSTOM')}))\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    return Installation(home, env, cwd, executable)


@pytest.fixture
def configured(installation):
    installation.success("init")
    installation.success("add", "infinity")
    installation.success("add", "play-reserve")
    return installation


@pytest.fixture
def refresh_accounts(configured):
    (configured.home / ".codex").mkdir()
    configured.env["CODEX_SQLITE_HOME"] = "/must-not-use-shared-state"
    # Reviewed fake: local JSON-RPC only, recording each selected home; no auth/network.
    source = '''import json, os, sys, time
from pathlib import Path
home = Path(os.environ["CODEX_HOME"])
(home / "environment.json").write_text(json.dumps({
    "home": str(home), "cwd": os.getcwd(), "sqlite": os.environ.get("CODEX_SQLITE_HOME"),
    "argv": sys.argv[1:]}))
for line in sys.stdin:
    request = json.loads(line)
    with (home / "protocol.log").open("a") as log:
        log.write(json.dumps(request) + "\\n")
    if request["method"] == "initialize":
        response = {"result": {"userAgent": "fake"}}
    elif request["method"] == "account/rateLimits/read":
        print("SECRET STDERR", file=sys.stderr, flush=True)
        if home.name == "infinity":
            response = {"error": {"code": -32000, "message": "Not authenticated SECRET"}}
        else:
            response = {"result": {"email": "SECRET", "rateLimits": {"limitId": "codex",
                "primary": {"usedPercent": {".codex": 17, "play-reserve": 63}[home.name],
                    "windowDurationMins": 300, "resetsAt": time.time() + 3600}}}}
    else:
        continue
    print(json.dumps({"id": request["id"], **response}), flush=True)
'''
    compile(source, "fake-refresh-codex", "exec")
    configured.executable.write_text(f"#!{sys.executable}\n" + source, encoding="utf-8")
    return configured


def test_init_preserves_default_credentials_and_is_idempotent(installation):
    original = installation.home / ".codex"
    original.mkdir()
    credential = original / "auth.json"
    credential.write_text("test-only-original", encoding="utf-8")
    installation.success("init")
    before = installation.registry.read_bytes()
    assert json.loads(before) == {"version": 1, "default": "default", "accounts": {"default": None}, "projects": {}}
    installation.success("init")
    assert installation.registry.read_bytes() == before
    assert credential.read_text() == "test-only-original"


def test_init_captures_existing_codex_home_and_preserves_native_default(installation, tmp_path):
    original = tmp_path / "existing-home"
    original.mkdir()
    installation.env.update(CODEX_HOME=str(original), CODEX_SQLITE_HOME="original-state")
    installation.success("init")
    assert json.loads(installation.registry.read_text())["accounts"] == {"default": str(original)}
    result = installation.native("--help")
    assert result["home"] == str(original)
    assert result["sqlite"] == "original-state"
    assert result["argv"] == ["--help"]


@pytest.mark.parametrize("value", ["relative", "/not-an-existing-codex-home"])
def test_init_rejects_invalid_inherited_home_without_writing(installation, value):
    installation.env["CODEX_HOME"] = value
    assert installation.run("init").returncode != 0
    assert not installation.registry.exists()


def test_custom_registry_location_is_honored(installation, tmp_path):
    alternate = tmp_path / "custom" / "profiles.json"
    installation.env["CODEX_SWITCH_CONFIG"] = str(alternate)
    installation.success("init")
    assert alternate.is_file()
    assert not installation.registry.exists()


def test_add_creates_private_empty_home_and_duplicate_preserves_state(configured):
    profile = configured.profile("infinity")
    assert profile.stat().st_mode & 0o077 == 0
    assert list(profile.iterdir()) == []
    (profile / "auth.json").write_text("test-only-named", encoding="utf-8")
    before = configured.registry.read_bytes()
    assert configured.run("add", "infinity").returncode != 0
    assert configured.registry.read_bytes() == before
    assert (profile / "auth.json").read_text() == "test-only-named"


@pytest.mark.parametrize("name", ["../escape", "/absolute", "has space", "", "a" * 65])
def test_invalid_profile_names_do_not_mutate_registry(configured, name):
    before = configured.registry.read_bytes()
    assert configured.run("add", name).returncode != 0
    assert configured.registry.read_bytes() == before


def test_share_config_links_only_reusable_assets(installation):
    source = installation.home / ".codex"
    source.mkdir()
    shared = ("config.toml", "AGENTS.md", "AGENTS.override.md", "agents", "skills", "rules",
              "hooks.json", "ai-toolkit-hooks")
    private = ("auth.json", "state_5.sqlite", "history.jsonl", "plugins", "sessions", "hook-trust.json")
    for name in (*shared, *private):
        if "." in name:
            (source / name).write_text("test fixture", encoding="utf-8")
        else:
            (source / name).mkdir()
    installation.success("init")
    installation.success("add", "infinity", "--share-config")
    profile = installation.profile("infinity")
    assert {path.name for path in profile.iterdir()} == set(shared)
    for name in shared:
        assert (profile / name).is_symlink()
        assert (profile / name).resolve() == source / name
    for name in private:
        assert not (profile / name).exists()


def test_add_never_overwrites_existing_unregistered_directory(configured):
    target = configured.profile("occupied")
    target.mkdir()
    (target / "auth.json").write_text("test-only", encoding="utf-8")
    assert configured.run("add", "occupied").returncode != 0
    assert (target / "auth.json").read_text() == "test-only"


def test_project_routing_uses_boundaries_and_deepest_match(configured):
    project = configured.cwd / "project"
    nested = project / "nested"
    sibling = configured.cwd / "project-other"
    nested.mkdir(parents=True)
    sibling.mkdir()
    configured.success("bind", str(project), "infinity")
    configured.success("bind", str(nested), "play-reserve")
    assert configured.status(cwd=project)["account"] == "infinity"
    assert configured.status(cwd=nested)["account"] == "play-reserve"
    assert configured.status(cwd=sibling)["account"] == "default"


def test_git_worktree_inherits_original_project_profile(configured, tmp_path):
    repository, worktree = configured.cwd / "repo", tmp_path / "linked"
    repository.mkdir()
    commands = [
        ["git", "init", str(repository)],
        ["git", "-C", str(repository), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "commit", "--allow-empty", "-m", "test: worktree fixture"],
        ["git", "-C", str(repository), "worktree", "add", "-b", "test-linked", str(worktree)],
    ]
    for command in commands:
        subprocess.run(command, env=configured.env, check=True, capture_output=True, text=True)
    configured.success("bind", str(repository), "infinity")
    result = configured.status(cwd=worktree)
    assert result["account"] == "infinity"
    assert result["source"] == "worktree"


@pytest.mark.parametrize("selector", [["--account", "infinity"], ["--account=infinity"]])
def test_account_override_preserves_native_arguments(configured, selector):
    arguments = ["exec", "--json", "prompt with spaces", "--", "--account", "literal"]
    result = configured.native(*selector, *arguments)
    home = configured.profile("infinity")
    assert result["home"] == str(home)
    assert result["argv"] == ["--no-daemon", "-c", "sqlite_home=" + json.dumps(str(home)), *arguments]


@pytest.mark.parametrize("style", ["-C", "--cd", "--cd=", "-Cjoined", "-C="])
def test_native_cd_flag_selects_target_project(configured, style):
    project = configured.cwd / "target"
    project.mkdir()
    configured.success("bind", str(project), "infinity")
    args = ["-C" + str(project)] if style == "-Cjoined" else (
        [style + str(project)] if style in {"--cd=", "-C="} else [style, str(project)])
    result = configured.native(*args, "--help")
    assert result["home"] == str(configured.profile("infinity"))
    assert result["argv"][-len(args) - 1:] == [*args, "--help"]


def test_explicit_account_wins_over_cd_project(configured):
    configured.success("bind", str(configured.cwd), "infinity")
    result = configured.native("--account", "play-reserve", "-C", str(configured.cwd))
    assert result["home"] == str(configured.profile("play-reserve"))


def test_named_profile_clears_inherited_sqlite_and_overrides_home(configured):
    configured.env.update(CODEX_HOME="inherited-home", CODEX_SQLITE_HOME="inherited-state", SWITCH_TEST_CUSTOM="keep")
    result = configured.native("--account", "infinity")
    assert result["home"] == str(configured.profile("infinity"))
    assert result["sqlite"] is None
    assert result["custom"] == "keep"


def test_null_default_restores_native_home_and_preserves_other_environment(configured):
    configured.env.update(CODEX_HOME="inherited-home", CODEX_SQLITE_HOME="existing-state", SWITCH_TEST_CUSTOM="keep")
    result = configured.native("--account", "default", "--help")
    assert result == {"argv": ["--help"], "home": None, "sqlite": "existing-state",
                      "cwd": str(configured.cwd), "custom": "keep"}


@pytest.mark.parametrize("name", ["CODEX_API_KEY", "CODEX_ACCESS_TOKEN", "OPENAI_API_KEY"])
def test_named_profile_rejects_auth_overrides_without_printing_secret(configured, name):
    configured.env[name] = "TEST-SECRET-MUST-NOT-LEAK"
    result = configured.run("run", "--account", "infinity")
    assert result.returncode != 0
    assert name in result.stderr
    assert "TEST-SECRET-MUST-NOT-LEAK" not in result.stdout + result.stderr


@pytest.mark.parametrize("arguments", [
    ["--remote", "unix://"], ["--remote=unix://"],
    ["--remote-auth-token-env", "TEST_TOKEN"], ["--remote-auth-token-env=TEST_TOKEN"],
    ["agents"], ["remote-control"], ["app"], ["app-server", "daemon", "start"],
    ["--local-provider", "ollama", "app"],
    ["--local-provider", "ollama", "agents"],
    ["--local-provider", "ollama", "app-server", "daemon", "start"],
    ["-c", 'sqlite_home="/tmp/shared"'], ["--config", 'sqlite_home="/tmp/shared"'],
    ['--config=sqlite_home="/tmp/shared"'], ['-csqlite_home="/tmp/shared"'], ['-c=sqlite_home="/tmp/shared"'],
    ["-c", '"sqlite_home"="/tmp/shared"'], ["-c", "'sqlite_home'='/tmp/shared'"],
])
def test_named_profile_rejects_remote_shared_server_and_sqlite_bypasses(configured, arguments):
    result = configured.run("run", "--account", "infinity", *arguments)
    assert result.returncode != 0, result.stdout
    assert "cannot guarantee" in result.stderr


def test_native_prompt_after_separator_is_not_inspected_as_flags(configured):
    result = configured.native("--account", "infinity", "exec", "--", "--remote=literal-prompt")
    assert result["argv"][-3:] == ["exec", "--", "--remote=literal-prompt"]


def test_native_flag_value_is_not_mistaken_for_daemon_subcommand(configured):
    result = configured.native("--account", "infinity", "--model", "app", "--help")
    assert result["argv"][-3:] == ["--model", "app", "--help"]


def test_login_uses_selected_profile_without_touching_default(configured):
    result = json.loads(configured.success("login", "infinity").stdout)
    assert result["home"] == str(configured.profile("infinity"))
    assert result["argv"][-1] == "login"
    assert not (configured.home / ".codex" / "auth.json").exists()


def test_status_includes_all_profiles_configuration_and_selected_project(configured):
    configured.success("bind", str(configured.cwd), "infinity")
    result = configured.status()
    assert result["account_count"] == 3
    assert result["default_account"] == "default"
    assert result["source"] == "project"
    rows = {row["name"]: row for row in result["accounts"]}
    assert rows["infinity"]["selected"] is True
    assert rows["infinity"]["projects"] == [str(configured.cwd)]
    assert rows["default"]["is_default"] is True
    assert all(row["usage"]["state"] == "error" for row in rows.values())
    assert all(row["usage"]["windows"] == {} for row in rows.values())


def test_status_ignores_old_profile_cache(configured):
    profile = configured.profile("infinity")
    cache = configured.registry.parent / "codex-usage" / (hashlib.sha256(str(profile).encode()).hexdigest() + ".json")
    cache.parent.mkdir()
    now = time.time()
    cache.write_text(json.dumps({
        "version": 1, "config_dir": str(profile), "observed_at": now,
        "windows": {"five_hour": {"used_percentage": 42, "resets_at": now + 1800}},
    }), encoding="utf-8")
    rows = {row["name"]: row for row in configured.status()["accounts"]}
    assert rows["infinity"]["usage"]["windows"] == {}
    assert rows["infinity"]["usage"]["state"] == "error"
    assert rows["default"]["usage"]["state"] == "error"
    output = configured.success("status", "--verbose", "--color", "never").stdout
    assert "CODEX ACCOUNTS" in output
    assert "42%" not in output
    assert "Config:" in output
    assert "--refresh" not in output


@pytest.mark.parametrize("display_args", [("--json",), ("--color", "never")], ids=["json", "text"])
@pytest.mark.parametrize("refresh_args", [(), ("--refresh",)], ids=["default-live", "refresh-alias"])
def test_status_isolates_profiles_and_continues_after_account_failure(refresh_accounts, display_args, refresh_args):
    installation = refresh_accounts
    homes = {"default": installation.home / ".codex",
             "infinity": installation.profile("infinity"),
             "play-reserve": installation.profile("play-reserve")}
    expected_usage = {"default": 17, "play-reserve": 63}

    result = installation.success("status", *refresh_args, *display_args)

    assert "SECRET" not in result.stdout + result.stderr
    if "--json" in display_args:
        status = json.loads(result.stdout)
        assert status["account_count"] == 3
        rows = {row["name"]: row for row in status["accounts"]}
        assert rows["infinity"]["usage"]["refresh_error"] == "not_authenticated"
        assert rows["infinity"]["usage"]["refreshed"] is False
        assert rows["infinity"]["usage"]["state"] == "error"
        assert rows["infinity"]["usage"]["windows"] == {}
        for name, percentage in expected_usage.items():
            assert rows[name]["config_dir"] == str(homes[name])
            assert rows[name]["usage"]["refreshed"] is True
            assert rows[name]["usage"]["state"] == "live"
            assert rows[name]["usage"]["windows"]["five_hour"]["used_percentage"] == percentage
    else:
        assert "infinity: refresh failed (not_authenticated)" in result.stdout
        assert "17%" in result.stdout and "63%" in result.stdout
    for name, home in homes.items():
        metadata = json.loads((home / "environment.json").read_text())
        assert metadata == {"home": str(home), "cwd": str(home), "sqlite": None,
                            "argv": ["-c", "sqlite_home=" + json.dumps(str(home)),
                                     "app-server", "--listen", "stdio://"]}
        requests = [json.loads(line) for line in (home / "protocol.log").read_text().splitlines()]
        assert [request["method"] for request in requests] == ["initialize", "initialized", "account/rateLimits/read"]
    assert not (installation.registry.parent / "codex-usage").exists()


def test_default_selection_changes_routing_without_swapping_credentials(configured):
    configured.success("default", "infinity")
    assert configured.status()["account"] == "infinity"
    assert configured.native()["home"] == str(configured.profile("infinity"))


@pytest.mark.parametrize("content", ["{", "[]", '{"version": true}', '{"version": 2}'])
def test_invalid_registry_fails_without_traceback(configured, content):
    configured.registry.write_text(content, encoding="utf-8")
    result = configured.run("status")
    assert result.returncode != 0
    assert "Traceback" not in result.stderr


def test_registry_rejects_two_profiles_resolving_to_same_home(configured, tmp_path):
    alias = tmp_path / "same-home"
    alias.symlink_to(configured.profile("infinity"), target_is_directory=True)
    raw = json.loads(configured.registry.read_text())
    raw["accounts"]["play-reserve"] = str(alias)
    configured.registry.write_text(json.dumps(raw), encoding="utf-8")
    result = configured.run("status")
    assert result.returncode != 0
    assert "distinct" in result.stderr


def test_missing_binary_fails_actionably(configured, tmp_path):
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    configured.env["PATH"] = str(empty)
    result = configured.run("run", "--account", "default")
    assert result.returncode != 0
    assert "not found on PATH" in result.stderr


def test_missing_profile_home_is_not_recreated_on_launch(configured):
    profile = configured.profile("infinity")
    profile.rename(profile.with_name("moved-profile"))
    result = configured.run("run", "--account", "infinity")
    assert result.returncode != 0
    assert "missing" in result.stderr
    assert not profile.exists()


@pytest.mark.parametrize("argument,code", [("--fake-exit", 23), ("--fake-signal", -signal.SIGTERM)])
def test_native_exit_status_and_signal_are_preserved(configured, argument, code):
    assert configured.run("run", "--account", "infinity", argument).returncode == code


def test_removed_shell_init_is_rejected_without_emitting_a_shell_function(installation):
    result = installation.run("shell-init")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
    assert "codex()" not in result.stdout
