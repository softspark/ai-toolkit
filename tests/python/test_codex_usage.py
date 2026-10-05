# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""The quota reader sends only read-only RPCs and never touches credentials."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import codex_usage

NOW = 1_800_000_000.0


def bucket(percentage=25, duration=300, **extra):
    return {"limitId": "codex", "primary": {
        "usedPercent": percentage, "windowDurationMins": duration, "resetsAt": NOW + 3600,
    }, **extra}


@pytest.fixture
def profile(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_TOOLKIT_HOME", str(tmp_path / "toolkit"))
    for name in ("CODEX_ACCESS_TOKEN", "CODEX_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    directory = tmp_path / "profile"
    directory.mkdir()
    return directory


@pytest.fixture
def fake_codex(profile, tmp_path, monkeypatch):
    # This fixture implements the official newline JSON handshake, no network.
    source = '''import json, os, signal, sys, time
from pathlib import Path
home = Path(os.environ["CODEX_HOME"])
(home / "pid").write_text(str(os.getpid()))
(home / "environment.json").write_text(json.dumps({
    "sqlite_home": os.environ.get("CODEX_SQLITE_HOME"), "argv": sys.argv[1:]}))
mode = os.environ.get("FAKE_CODEX_MODE", "success")
if mode == "timeout":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
for line in sys.stdin:
    request = json.loads(line)
    with (home / "protocol.log").open("a") as log:
        log.write(json.dumps(request) + "\\n")
    method = request["method"]
    if mode == "timeout":
        time.sleep(30)
    if method == "initialize":
        if mode == "init-error":
            print(json.dumps({"id": request["id"], "error": {"message": "SECRET", "code": -32601}}), flush=True)
        else:
            print(json.dumps({"id": request["id"], "result": {"userAgent": "fake"}}), flush=True)
    elif method == "account/rateLimits/read":
        print("SECRET STDERR", file=sys.stderr, flush=True)
        if mode == "exit":
            sys.exit(1)
        if mode == "partial":
            sys.stdout.write('{"id": 2')
            sys.stdout.flush()
            time.sleep(30)
        if mode == "invalid":
            print("not-json SECRET", flush=True)
        elif mode == "huge":
            print("x" * 2200000, flush=True)
        elif mode.startswith("error:"):
            print(json.dumps({"id": request["id"], "error": {"code": -32000, "message": mode[6:] + " SECRET"}}), flush=True)
        else:
            print(json.dumps({"method": "account/rateLimits/updated", "params": {"SECRET": "ignored"}}), flush=True)
            print(json.dumps({"id": request["id"], "result": {"rateLimits": {
                "limitId": "codex", "primary": {"usedPercent": int(os.environ.get("FAKE_PERCENT", "25")),
                    "windowDurationMins": 300, "resetsAt": 2500000000}
            }, "accountId": "SECRET", "email": "SECRET"}}), flush=True)
'''
    compile(source, "fake-codex", "exec")
    binary = tmp_path / "bin" / "codex"
    binary.parent.mkdir()
    binary.write_text(f"#!{sys.executable}\n" + source)
    binary.chmod(0o700)
    monkeypatch.setenv("PATH", str(binary.parent))
    return binary


def test_quota_windows_maps_duration_not_position():
    result = codex_usage.quota_windows({"rateLimits": bucket(duration=10080, secondary={
        "usedPercent": 40, "windowDurationMins": 300, "resetsAt": NOW + 10,
    })})
    assert result["five_hour"]["used_percentage"] == 40
    assert result["seven_day"]["used_percentage"] == 25


def test_prefer_codex_bucket_over_legacy_and_other_buckets():
    result = codex_usage.quota_windows({
        "rateLimits": bucket(1), "rateLimitsByLimitId": {"codex": bucket(50), "other": bucket(99)},
    })
    assert result["five_hour"]["used_percentage"] == 50


@pytest.mark.parametrize("result", [
    {}, {"rateLimits": None}, {"rateLimitsByLimitId": {"other": bucket()}},
    {"rateLimits": bucket(limitId="other")}, {"rateLimits": bucket(duration=15)},
    {"rateLimits": bucket(duration=None)}, {"rateLimits": bucket(duration=[])},
])
def test_other_buckets_and_unknown_durations_do_not_become_five_hour(result):
    assert codex_usage.quota_windows(result) == {}


@pytest.mark.parametrize("value", [True, None, "25", -1, 101, float("inf"), float("nan")])
def test_reject_invalid_percentage(value):
    assert codex_usage.quota_windows({"rateLimits": bucket(value)}) == {}


def test_protocol_handshake_returns_live_usage_without_cache_and_reaps_process(profile, fake_codex, capsys, monkeypatch):
    monkeypatch.setenv("CODEX_SQLITE_HOME", "/must-not-use")
    result = codex_usage.refresh_usage(profile)
    assert result["refreshed"] is True
    assert result["state"] == "live"
    assert result["age_seconds"] == 0
    assert result["windows"]["five_hour"]["used_percentage"] == 25
    assert result["windows"]["five_hour"]["state"] == "live"
    calls = [json.loads(line) for line in (profile / "protocol.log").read_text().splitlines()]
    assert [call["method"] for call in calls] == ["initialize", "initialized", "account/rateLimits/read"]
    assert calls[0]["params"]["clientInfo"]["name"] == "ai_toolkit_usage"
    env = json.loads((profile / "environment.json").read_text())
    assert env["sqlite_home"] is None
    assert env["argv"] == ["-c", "sqlite_home=" + json.dumps(str(profile)), "app-server", "--listen", "stdio://"]
    assert "SECRET" not in json.dumps(result)
    assert not (profile.parent / "toolkit").exists()
    assert capsys.readouterr().err == ""
    with pytest.raises(ProcessLookupError):
        os.kill(int((profile / "pid").read_text()), 0)


@pytest.mark.parametrize(("mode", "expected"), [
    ("init-error", "unsupported_cli"), ("invalid", "protocol_error"), ("huge", "protocol_error"),
    ("exit", "process_exited"), ("error:API key accounts unsupported", "api_key_unsupported"),
    ("error:Not authenticated", "not_authenticated"), ("error:upstream down", "request_failed"),
])
def test_rpc_failures_are_sanitized(profile, fake_codex, monkeypatch, mode, expected):
    monkeypatch.setenv("FAKE_CODEX_MODE", mode)
    result = codex_usage.refresh_usage(profile)
    assert result["refresh_error"] == expected
    assert result["refreshed"] is False
    assert result["state"] == "error"
    assert result["windows"] == {}
    assert "SECRET" not in json.dumps(result)
    assert not (profile.parent / "toolkit").exists()


@pytest.mark.parametrize("mode", ["timeout", "partial"])
def test_timeout_including_partial_line_reaps_child(profile, fake_codex, monkeypatch, mode):
    monkeypatch.setenv("FAKE_CODEX_MODE", mode)
    start = time.monotonic()
    result = codex_usage.refresh_usage(profile, timeout=0.3)
    assert result["refresh_error"] == "timeout"
    assert time.monotonic() - start < 3
    with pytest.raises(ProcessLookupError):
        os.kill(int((profile / "pid").read_text()), 0)


def test_failed_fetch_never_returns_previous_success(profile, fake_codex, monkeypatch):
    first = codex_usage.refresh_usage(profile)
    assert first["windows"]["five_hour"]["used_percentage"] == 25
    monkeypatch.setenv("FAKE_CODEX_MODE", "error:network failure")
    result = codex_usage.refresh_usage(profile)
    assert result == {"state": "error", "windows": {}, "observed_at": None, "age_seconds": None,
                      "refreshed": False, "refresh_error": "request_failed"}
    assert not (profile.parent / "toolkit").exists()


def test_each_fetch_gets_current_provider_value(profile, fake_codex, monkeypatch):
    assert codex_usage.refresh_usage(profile)["windows"]["five_hour"]["used_percentage"] == 25
    monkeypatch.setenv("FAKE_PERCENT", "47")
    assert codex_usage.refresh_usage(profile)["windows"]["five_hour"]["used_percentage"] == 47
    calls = [json.loads(line) for line in (profile / "protocol.log").read_text().splitlines()]
    assert sum(call["method"] == "account/rateLimits/read" for call in calls) == 2


@pytest.mark.parametrize("mode", ["success", "error:network failure"])
def test_old_disk_cache_is_ignored_and_untouched(profile, fake_codex, monkeypatch, mode):
    path = profile.parent / "toolkit" / "codex-usage" / (hashlib.sha256(str(profile).encode()).hexdigest() + ".json")
    path.parent.mkdir(parents=True)
    old_snapshot = json.dumps({"version": 1, "config_dir": str(profile), "observed_at": time.time(),
                              "windows": {"five_hour": {"used_percentage": 99, "resets_at": 2500000000}}})
    path.write_text(old_snapshot)
    monkeypatch.setenv("FAKE_CODEX_MODE", mode)
    result = codex_usage.refresh_usage(profile)
    assert path.read_text() == old_snapshot
    if mode == "success":
        assert result["windows"]["five_hour"]["used_percentage"] == 25
    else:
        assert result["state"] == "error"
        assert result["windows"] == {}


@pytest.mark.parametrize("name", ["OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN"])
def test_external_auth_cannot_replace_profile_identity(profile, fake_codex, monkeypatch, name):
    monkeypatch.setenv(name, "SECRET")
    assert codex_usage.refresh_usage(profile)["refresh_error"] == "auth_override"
    assert not (profile / "pid").exists()


def test_missing_binary_and_profile_return_safe_codes(profile, monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path / "no-binary"))
    assert codex_usage.refresh_usage(profile)["refresh_error"] == "codex_not_found"
    assert codex_usage.refresh_usage(tmp_path / "missing")["refresh_error"] == "profile_not_initialized"


@pytest.mark.parametrize("timeout", [0, -1, True, float("nan"), float("inf"), 301])
def test_invalid_deadline_does_not_spawn(profile, fake_codex, timeout):
    assert codex_usage.refresh_usage(profile, timeout=timeout)["refresh_error"] == "invalid_timeout"
    assert not (profile / "pid").exists()
