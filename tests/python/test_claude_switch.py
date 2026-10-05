# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Project routing must preserve Claude arguments and isolate account state."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "claude_switch.py"
AUTH_ENV = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
)


@dataclass
class Installation:
    home: Path
    env: dict[str, str]
    cwd: Path

    def usage(self, account: str, payload: dict[str, object]) -> None:
        fixtures = Path(self.env["TEST_CLAUDE_USAGE_FIXTURES"])
        responses = json.loads(fixtures.read_text())
        profile = None if account == "default" else str(
            self.home / ".softspark/ai-toolkit/claude-profiles" / account,
        )
        responses["default" if profile is None else profile] = payload
        fixtures.write_text(json.dumps(responses), encoding="utf-8")

    @property
    def registry(self) -> Path:
        return self.home / ".softspark/ai-toolkit/claude-switch.json"

    def run(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], cwd=cwd or self.cwd,
            env=self.env, capture_output=True, text=True, timeout=15, check=False,
        )

    def success(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        result = self.run(*args, cwd=cwd)
        assert result.returncode == 0, result.stderr
        return result

    def status(self, *args: str, cwd: Path | None = None) -> dict[str, object]:
        return json.loads(self.success("status", *args, "--json", cwd=cwd).stdout)


@pytest.fixture
def installation(tmp_path: Path) -> Installation:
    home, executable_dir, cwd = tmp_path / "home", tmp_path / "bin", tmp_path / "workspace"
    for directory in (home, executable_dir, cwd):
        directory.mkdir()
    env = dict(os.environ)
    for name in (*AUTH_ENV, "AI_TOOLKIT_HOME", "SOFTSPARK_HOME", "CLAUDE_SWITCH_CONFIG",
                 "CLAUDE_CONFIG_DIR", "CLAUDE_SECURESTORAGE_CONFIG_DIR", "CLAUDECODE", "GIT_DIR", "GIT_WORK_TREE"):
        env.pop(name, None)
    env.update(HOME=str(home), PATH=f"{executable_dir}{os.pathsep}{env.get('PATH', '')}")
    fixtures = tmp_path / "usage-responses.json"
    fixtures.write_text("{}", encoding="utf-8")
    patches = tmp_path / "python-patches"
    patches.mkdir()
    # Reviewed startup patch: every CLI subprocess uses fixture responses only,
    # so status tests never reach user credentials, Keychain, or the network.
    (patches / "sitecustomize.py").write_text(
        "import json, os\n"
        "from pathlib import Path\n"
        "import claude_usage\n"
        "def request_usage(config_dir, timeout=10):\n"
        "    fixtures = json.loads(Path(os.environ['TEST_CLAUDE_USAGE_FIXTURES']).read_text())\n"
        "    key = 'default' if config_dir is None else str(config_dir)\n"
        "    response = fixtures.get(key, {'error': 'not_authenticated'})\n"
        "    if 'error' in response:\n"
        "        raise claude_usage.UsageError(response['error'])\n"
        "    return response\n"
        "claude_usage.request_usage = request_usage\n",
        encoding="utf-8",
    )
    env.update(
        TEST_CLAUDE_USAGE_FIXTURES=str(fixtures),
        PYTHONPATH=os.pathsep.join((str(patches), str(SCRIPT.parent))),
    )
    executable = executable_dir / "claude"
    # Reviewed fake process: reports only controlled test metadata, no network or credentials.
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json, os, signal, sys\n"
        "if '--fake-signal' in sys.argv: os.kill(os.getpid(), signal.SIGTERM)\n"
        "if '--fake-exit' in sys.argv: sys.exit(23)\n"
        "print(json.dumps({'argv': sys.argv[1:], "
        "'config_dir': os.environ.get('CLAUDE_CONFIG_DIR'), "
        "'api_key': os.environ.get('ANTHROPIC_API_KEY')}))\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    return Installation(home, env, cwd)


@pytest.fixture
def configured(installation: Installation) -> Installation:
    installation.success("init")
    installation.success("add", "infinity")
    installation.success("add", "play-reserve")
    return installation


def test_init_preserves_default_login_and_is_idempotent(installation):
    legacy = installation.home / ".claude"
    legacy.mkdir()
    credential = legacy / ".credentials.json"
    credential.write_text("existing-account", encoding="utf-8")
    installation.success("init")
    initial = installation.registry.read_bytes()
    assert json.loads(initial) == {
        "version": 1, "default": "default", "accounts": {"default": None}, "projects": {},
    }
    installation.success("init")
    assert installation.registry.read_bytes() == initial
    assert credential.read_text() == "existing-account"


def test_init_honors_explicit_registry_location(installation, tmp_path):
    registry = tmp_path / "custom/registry.json"
    installation.env["CLAUDE_SWITCH_CONFIG"] = str(registry)
    installation.success("init")
    assert registry.is_file()
    assert not installation.registry.exists()


def test_add_creates_private_directory_and_duplicate_preserves_state(configured):
    registry = json.loads(configured.registry.read_text())
    profile = configured.home / ".softspark/ai-toolkit/claude-profiles/infinity"
    assert registry["accounts"]["infinity"] == str(profile)
    assert profile.is_dir()
    assert profile.stat().st_mode & 0o077 == 0
    credential = profile / ".credentials.json"
    credential.write_text("profile-specific-account", encoding="utf-8")
    before = configured.registry.read_bytes()
    configured.run("add", "infinity")
    assert configured.registry.read_bytes() == before
    assert credential.read_text() == "profile-specific-account"


@pytest.mark.parametrize("name", ["../escape", "/absolute", "has/slash", "", "has space"])
def test_add_rejects_unsafe_account_name_without_mutation(configured, name):
    before = configured.registry.read_bytes()
    assert configured.run("add", name).returncode != 0
    assert configured.registry.read_bytes() == before


def test_share_config_links_only_explicit_reusable_assets(installation):
    source = installation.home / ".claude"
    directories = ("agents", "skills", "rules", "commands", "output-styles")
    files = ("CLAUDE.md", "ARCHITECTURE.md", "settings.json")
    for name in (*directories, "plugins", "projects"):
        (source / name).mkdir(parents=True)
    for name in (*files, ".credentials.json", ".claude.json", "history.jsonl"):
        (source / name).write_text("{}", encoding="utf-8")
    installation.success("init")
    installation.success("add", "infinity", "--share-config")
    profile = installation.home / ".softspark/ai-toolkit/claude-profiles/infinity"
    for name in (*directories, *files):
        assert (profile / name).is_symlink(), name
        assert (profile / name).resolve() == source / name
    for name in ("plugins", "projects", ".credentials.json", ".claude.json", "history.jsonl"):
        assert not (profile / name).exists(), name


def test_unshared_profile_does_not_inherit_settings_or_credentials(installation):
    source = installation.home / ".claude"
    source.mkdir()
    (source / "settings.json").write_text("{}", encoding="utf-8")
    installation.success("init")
    installation.success("add", "isolated")
    profile = installation.home / ".softspark/ai-toolkit/claude-profiles/isolated"
    assert list(profile.iterdir()) == []


def test_status_defaults_to_existing_config(configured):
    status = configured.status()
    assert status["account"] == "default"
    assert status["config_dir"] == str(configured.home / ".claude")
    assert status["project"] is None
    assert status["source"] == "default"


def test_status_lists_every_profile_and_its_bindings(configured):
    project = configured.cwd / "infinity"
    project.mkdir()
    configured.success("bind", str(project), "infinity")
    configured.success("bind", str(configured.cwd), "play-reserve")

    status = configured.status(cwd=project)

    assert status["account_count"] == 3
    assert status["default_account"] == "default"
    accounts = {account["name"]: account for account in status["accounts"]}
    assert set(accounts) == {"default", "infinity", "play-reserve"}
    assert accounts["default"]["is_default"] is True
    assert accounts["default"]["selected"] is False
    assert accounts["default"]["config_dir"] == str(configured.home / ".claude")
    assert accounts["default"]["projects"] == []
    assert accounts["infinity"]["selected"] is True
    assert accounts["infinity"]["projects"] == [str(project.resolve())]
    assert accounts["play-reserve"]["projects"] == [str(configured.cwd.resolve())]
    assert all(account["usage"]["state"] == "error" for account in accounts.values())
    assert all(account["usage"]["windows"] == {} for account in accounts.values())


def test_status_override_marks_selection_without_hiding_other_profiles(configured):
    configured.success("default", "play-reserve")

    status = configured.status("--account", "infinity")

    assert status["account"] == "infinity"
    assert status["source"] == "override"
    assert status["default_account"] == "play-reserve"
    assert len(status["accounts"]) == 3
    assert [account["name"] for account in status["accounts"] if account["selected"]] == ["infinity"]
    assert [account["name"] for account in status["accounts"] if account["is_default"]] == ["play-reserve"]


def test_human_status_reports_unknown_usage_and_configuration(configured):
    configured.success("bind", str(configured.cwd), "infinity")

    result = configured.success("status")

    assert "3 profiles" in result.stdout
    assert "› infinity" in result.stdout
    assert "default *" in result.stdout
    assert "5h" in result.stdout and "7d" in result.stdout
    assert "Unavailable: not_authenticated" in result.stdout
    assert "0%" not in result.stdout
    assert str(configured.cwd) not in result.stdout
    assert str(configured.home) not in result.stdout
    details = configured.success("status", "--verbose").stdout
    assert str(configured.cwd) in details
    assert "~/.claude" in details


def usage_payload(percentage: float) -> dict[str, object]:
    now = time.time()
    return {
        "five_hour": {"utilization": percentage,
                      "resets_at": datetime.fromtimestamp(now + 3600, timezone.utc).isoformat()},
        "seven_day": {"utilization": percentage / 2,
                      "resets_at": datetime.fromtimestamp(now + 86400, timezone.utc).isoformat()},
    }


def test_status_colors_are_opt_in_for_pipes_and_disabled_by_no_color(configured):
    configured.env.pop("NO_COLOR", None)
    assert "\x1b[" not in configured.success("status").stdout
    assert "\x1b[" in configured.success("status", "--color", "always").stdout
    assert "\x1b[" not in configured.success("status", "--color", "never").stdout
    configured.env["NO_COLOR"] = ""
    assert "\x1b[" not in configured.success("status", "--color", "always").stdout


def test_json_remains_plain_and_complete_with_display_options(configured):
    output = configured.success("status", "--json", "--color", "always", "--verbose").stdout
    assert "\x1b" not in output
    report = json.loads(output)
    assert report["account_count"] == 3
    assert report["accounts"][0]["config_dir"] == str(configured.home / ".claude")


def test_narrow_terminal_uses_stacked_layout_without_clipping_limits(configured):
    configured.env["COLUMNS"] = "60"
    configured.usage("default", usage_payload(100))
    output = configured.success("status", "--color", "never").stdout
    assert "100%" in output and "50%" in output
    assert "5h" in output and "7d" in output
    assert "PROFILE" not in output
    assert max(len(line) for line in output.splitlines()) <= 60


def test_zero_usage_has_bar_while_missing_profiles_have_no_fake_percent(configured):
    configured.usage("default", usage_payload(0))
    output = configured.success("status", "--color", "never").stdout
    assert "░░░░░░░░░░ 0%" in output
    assert output.count("Unavailable: not_authenticated") == 2


def test_live_usage_is_isolated_by_profile_in_status(configured):
    configured.usage("default", usage_payload(20))
    configured.usage("infinity", usage_payload(74))
    configured.usage("play-reserve", usage_payload(46))

    status = configured.status("--account", "infinity")
    accounts = {account["name"]: account for account in status["accounts"]}

    assert accounts["default"]["usage"]["windows"]["five_hour"]["used_percentage"] == 20
    usage = accounts["infinity"]["usage"]
    assert usage["state"] == "live"
    assert usage["refreshed"] is True
    assert usage["observed_at"] <= time.time()
    assert usage["windows"]["five_hour"]["used_percentage"] == 74
    assert usage["windows"]["seven_day"]["used_percentage"] == 37
    assert usage["windows"]["five_hour"]["state"] == "live"
    assert accounts["play-reserve"]["usage"]["windows"]["five_hour"]["used_percentage"] == 46
    output = configured.success("status").stdout
    assert "74%" in output and "37%" in output and "20%" in output
    assert "reset in" in output and "live usage" in output
    assert "ago" not in output and "stale" not in output
    assert "UTC" in configured.success("status", "--verbose").stdout


@pytest.mark.parametrize("refresh_args", [(), ("--refresh",)])
def test_every_status_fetches_changed_live_usage_without_disk_cache(configured, refresh_args):
    before = {path.relative_to(configured.home) for path in configured.home.rglob("*")}
    configured.usage("default", usage_payload(12))
    initial = configured.status(*refresh_args)["accounts"][0]["usage"]
    configured.usage("default", usage_payload(68))
    current = configured.status(*refresh_args)["accounts"][0]["usage"]

    assert initial["windows"]["five_hour"]["used_percentage"] == 12
    assert current["windows"]["five_hour"]["used_percentage"] == 68
    assert current["state"] == "live" and current["refreshed"] is True
    assert {path.relative_to(configured.home) for path in configured.home.rglob("*")} == before


def test_failed_account_does_not_fall_back_to_previous_or_other_account_usage(configured):
    configured.usage("default", usage_payload(42))
    configured.usage("infinity", usage_payload(74))
    assert configured.status()["accounts"][0]["usage"]["windows"]["five_hour"]["used_percentage"] == 42
    configured.usage("default", {"error": "authentication_expired"})

    accounts = {account["name"]: account for account in configured.status("--refresh")["accounts"]}

    assert len(accounts) == 3
    failure = accounts["default"]["usage"]
    assert failure["state"] == "error" and failure["refreshed"] is False
    assert failure["windows"] == {}
    assert failure["observed_at"] is None
    assert failure["refresh_error"] == "authentication_expired"
    assert accounts["infinity"]["usage"]["windows"]["five_hour"]["used_percentage"] == 74
    output = configured.success("status").stdout
    assert "Unavailable: authentication_expired" in output
    assert "74%" in output and "42%" not in output


def test_routing_matches_longest_complete_directory_prefix(configured):
    project = configured.cwd / "infinity"
    nested = project / "nested project"
    nested.mkdir(parents=True)
    sibling = configured.cwd / "infinity-extra"
    sibling.mkdir()
    configured.success("bind", str(project), "infinity")
    configured.success("bind", str(nested), "play-reserve")
    assert configured.status(cwd=project)["account"] == "infinity"
    status = configured.status(cwd=nested)
    assert status["account"] == "play-reserve"
    assert status["project"] == str(nested.resolve())
    assert status["source"] == "project"
    assert configured.status(cwd=sibling)["account"] == "default"


def test_bind_and_lookup_resolve_symlinks(configured):
    project = configured.cwd / "real project"
    project.mkdir()
    link = configured.cwd / "project-link"
    link.symlink_to(project, target_is_directory=True)
    configured.success("bind", str(link), "infinity")
    registry = json.loads(configured.registry.read_text())
    assert registry["projects"] == {str(project.resolve()): "infinity"}
    assert configured.status(cwd=link)["account"] == "infinity"


def test_default_change_and_explicit_override_take_effect(configured):
    configured.success("bind", str(configured.cwd), "infinity")
    configured.success("default", "play-reserve")
    assert configured.status(cwd=configured.home)["account"] == "play-reserve"
    status = configured.status("--account", "default")
    assert status["account"] == "default"
    assert status["source"] == "override"


def test_bind_rejects_nonexistent_directory_without_mutation(configured):
    before = configured.registry.read_bytes()
    result = configured.run("bind", str(configured.cwd / "missing"), "infinity")
    assert result.returncode != 0
    assert configured.registry.read_bytes() == before


@pytest.mark.parametrize("args", [
    ("status", "--account", "unknown"), ("run", "--account", "unknown"),
    ("default", "unknown"), ("login", "unknown"),
])
def test_unknown_account_fails_without_launching_claude(configured, args):
    result = configured.run(*args)
    assert result.returncode != 0
    assert '"argv"' not in result.stdout


def test_named_run_replaces_inherited_profile_and_preserves_arguments(configured):
    configured.env["CLAUDE_CONFIG_DIR"] = "/inherited/unrelated-profile"
    args = ["-p", "prompt with spaces", "--model", "sonnet", "--account", "literal-value"]
    output = json.loads(configured.success("run", "--account", "infinity", *args).stdout)
    assert output["argv"] == args
    assert output["config_dir"] == str(
        configured.home / ".softspark/ai-toolkit/claude-profiles/infinity",
    )


def test_default_run_unsets_config_dir_for_legacy_authentication(configured):
    configured.env["CLAUDE_CONFIG_DIR"] = "/inherited/unrelated-profile"
    output = json.loads(configured.success("run", "--account", "default").stdout)
    assert output["config_dir"] is None


def test_bound_project_launches_its_account_without_explicit_override(configured):
    configured.success("bind", str(configured.cwd), "infinity")
    output = json.loads(configured.success("run", "-p", "task").stdout)
    assert output["config_dir"].endswith("/claude-profiles/infinity")
    assert output["argv"] == ["-p", "task"]


def test_equals_override_and_separator_preserve_prompt_flags(configured):
    output = json.loads(configured.success(
        "run", "--account=infinity", "--", "--account=literal", "-p", "task",
    ).stdout)
    assert output["config_dir"].endswith("/claude-profiles/infinity")
    assert output["argv"] == ["--account=literal", "-p", "task"]


def test_missing_profile_never_falls_back_to_default_login(configured):
    profile = configured.home / ".softspark/ai-toolkit/claude-profiles/infinity"
    profile.rename(profile.with_name("infinity-backup"))
    result = configured.run("run", "--account", "infinity")
    assert result.returncode != 0
    assert '"argv"' not in result.stdout
    assert "missing" in result.stderr.lower()


def test_profile_symlink_cannot_alias_existing_default_login(configured):
    profile = configured.home / ".softspark/ai-toolkit/claude-profiles/infinity"
    profile.rename(profile.with_name("infinity-backup"))
    legacy = configured.home / ".claude"
    legacy.mkdir()
    profile.symlink_to(legacy, target_is_directory=True)
    result = configured.run("run", "--account", "infinity")
    assert result.returncode != 0
    assert '"argv"' not in result.stdout


def test_explicit_separator_passes_account_flag_to_claude(configured):
    output = json.loads(configured.success("run", "--", "--account", "literal").stdout)
    assert output["argv"] == ["--account", "literal"]


def test_login_routes_auth_login_to_selected_profile(configured):
    output = json.loads(configured.success("login", "infinity").stdout)
    assert output["argv"] == ["auth", "login"]
    assert output["config_dir"].endswith("/claude-profiles/infinity")


@pytest.mark.parametrize("storage", ["", "/private/credential-store"])
@pytest.mark.parametrize("arguments", [("run", "--account", "infinity"), ("login", "infinity")])
def test_named_profile_rejects_secure_storage_override_without_launching(configured, storage, arguments):
    configured.env["CLAUDE_SECURESTORAGE_CONFIG_DIR"] = storage
    result = configured.run(*arguments)
    assert result.returncode != 0
    assert "CLAUDE_SECURESTORAGE_CONFIG_DIR" in result.stderr
    assert '"argv"' not in result.stdout
    assert "/private/credential-store" not in result.stderr


def test_default_profile_keeps_native_secure_storage_override_behavior(configured):
    configured.env["CLAUDE_SECURESTORAGE_CONFIG_DIR"] = ""
    result = configured.success("run", "--account", "default", "--help")
    assert json.loads(result.stdout)["config_dir"] is None


def test_auth_override_warning_names_variable_without_revealing_value(configured):
    configured.env["ANTHROPIC_API_KEY"] = "test-secret-never-log"
    result = configured.success("run")
    assert "ANTHROPIC_API_KEY" in result.stderr
    assert "test-secret-never-log" not in result.stderr
    assert json.loads(result.stdout)["api_key"] == "test-secret-never-log"


def test_exit_code_and_signal_are_preserved(configured):
    assert configured.run("run", "--fake-exit").returncode == 23
    assert configured.run("run", "--fake-signal").returncode == -signal.SIGTERM


def test_missing_claude_binary_fails_clearly_without_fallback(configured, tmp_path):
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    configured.env["PATH"] = str(empty)
    result = configured.run("run")
    assert result.returncode != 0
    assert "claude" in result.stderr.lower()


def test_missing_registry_requires_initialization(installation):
    result = installation.run("run")
    assert result.returncode != 0
    assert "init" in result.stderr.lower()
    assert '"argv"' not in result.stdout


@pytest.mark.parametrize("contents", [
    "{", "null", "[]", "{}",
    '{"version": 2, "default": "default", "accounts": {"default": null}, "projects": {}}',
    '{"version": 1, "default": "unknown", "accounts": {"default": null}, "projects": {}}',
    '{"version": 1, "default": "default", "accounts": {"default": 5}, "projects": {}}',
])
def test_malformed_registry_fails_closed(configured, contents):
    configured.registry.write_text(contents, encoding="utf-8")
    result = configured.run("run")
    assert result.returncode != 0
    assert '"argv"' not in result.stdout
    assert configured.registry.read_text() == contents


@pytest.mark.parametrize("invalid_case", ["relative-profile", "shared-profile", "unknown-binding", "relative-binding"])
def test_invalid_registry_paths_and_references_fail_closed(configured, invalid_case):
    registry = json.loads(configured.registry.read_text())
    if invalid_case == "relative-profile":
        registry["accounts"]["infinity"] = "relative/profile"
    elif invalid_case == "shared-profile":
        registry["accounts"]["play-reserve"] = registry["accounts"]["infinity"]
    elif invalid_case == "unknown-binding":
        registry["projects"][str(configured.cwd)] = "unknown"
    else:
        registry["projects"]["relative/project"] = "infinity"
    configured.registry.write_text(json.dumps(registry), encoding="utf-8")
    result = configured.run("run")
    assert result.returncode != 0
    assert '"argv"' not in result.stdout


def test_linked_worktree_inherits_main_repository_binding(configured):
    assert shutil.which("git"), "Repository tests require git"
    main, worktree = configured.cwd / "main", configured.cwd / "worktree"
    main.mkdir()
    commands = [
        ["git", "init", "--quiet"],
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "-c", "commit.gpgsign=false", "commit", "--quiet", "--allow-empty", "-m", "test"],
        ["git", "worktree", "add", "--quiet", "--detach", str(worktree)],
    ]
    for command in commands:
        subprocess.run(command, cwd=main, env=configured.env, check=True, capture_output=True)
    configured.success("bind", str(main), "infinity")
    status = configured.status(cwd=worktree)
    assert status["account"] == "infinity"
    assert status["source"] == "worktree"
    configured.success("bind", str(worktree), "play-reserve")
    status = configured.status(cwd=worktree)
    assert status["account"] == "play-reserve"
    assert status["source"] == "project"


def test_removed_shell_init_is_rejected_without_emitting_a_shell_function(installation):
    result = installation.run("shell-init")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
    assert "claude()" not in result.stdout
