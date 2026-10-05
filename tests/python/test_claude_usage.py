# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Live Claude quota requests must isolate credentials and never persist limits."""

from __future__ import annotations

import hashlib
import http.client
import io
import json
import subprocess
import sys
import time
import unicodedata
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import claude_usage

TOKEN = "TEST-SECRET-ACCESS-TOKEN"


def response(percentage=23):
    return {"five_hour": {"utilization": percentage, "resets_at": "2090-01-01T00:00:00Z"},
            "seven_day": {"utilization": 14, "resets_at": "2090-01-03T00:00:00+00:00"}}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CLAUDE_SECURESTORAGE_CONFIG_DIR", raising=False)
    monkeypatch.setattr(claude_usage, "IS_MACOS", False)
    def no_io(*args, **kwargs):
        raise AssertionError("Unexpected external process or HTTP request")
    monkeypatch.setattr(claude_usage.subprocess, "run", no_io)
    monkeypatch.setattr(claude_usage.urllib.request, "build_opener", no_io)


@pytest.fixture
def profile(tmp_path):
    path = tmp_path / "profile"
    path.mkdir()
    (path / ".credentials.json").write_text(json.dumps({"claudeAiOauth": {
        "accessToken": TOKEN, "expiresAt": (time.time() + 3600) * 1000,
    }}))
    return str(path)


def opener(monkeypatch, result=None, error=None):
    calls = []
    def open_request(request, timeout):
        calls.append((request, timeout))
        if error:
            raise error
        return io.BytesIO(json.dumps(result if result is not None else response()).encode())
    monkeypatch.setattr(claude_usage.urllib.request, "build_opener",
                        lambda *handlers: SimpleNamespace(open=open_request))
    return calls


def test_live_request_uses_fixed_endpoint_and_profile_token_without_persistence(profile, monkeypatch, tmp_path):
    calls = opener(monkeypatch)
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    usage = claude_usage.refresh_usage(profile)
    assert usage["state"] == "live" and usage["refreshed"] is True
    assert usage["windows"]["five_hour"]["used_percentage"] == 23
    request, timeout = calls[0]
    assert request.full_url == "https://api.anthropic.com/api/oauth/usage"
    assert request.get_method() == "GET"
    assert request.get_header("Authorization") == "Bearer " + TOKEN
    assert request.get_header("Anthropic-beta") == "oauth-2025-04-20"
    assert 0 < timeout <= 10
    assert TOKEN not in json.dumps(usage)
    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


def test_each_request_obtains_new_values_and_failure_cannot_fall_back(profile, monkeypatch):
    opener(monkeypatch, response(10))
    assert claude_usage.refresh_usage(profile)["windows"]["five_hour"]["used_percentage"] == 10
    opener(monkeypatch, response(42))
    assert claude_usage.refresh_usage(profile)["windows"]["five_hour"]["used_percentage"] == 42
    opener(monkeypatch, error=urllib.error.URLError("SECRET"))
    usage = claude_usage.refresh_usage(profile)
    assert usage["state"] == "error" and usage["windows"] == {}
    assert usage["observed_at"] is None and usage["refreshed"] is False
    assert "SECRET" not in json.dumps(usage)


@pytest.mark.parametrize("code,expected", [(401, "authentication_expired"), (403, "permission_denied"),
                                           (429, "rate_limited"), (500, "request_failed")])
def test_http_errors_are_sanitized_without_old_values(profile, monkeypatch, code, expected):
    error = urllib.error.HTTPError(claude_usage.USAGE_URL, code, "SECRET", {}, io.BytesIO(b"SECRET"))
    opener(monkeypatch, error=error)
    usage = claude_usage.refresh_usage(profile)
    assert usage["refresh_error"] == expected
    assert usage["windows"] == {}
    assert "SECRET" not in json.dumps(usage)


@pytest.mark.parametrize("error,expected", [
    (TimeoutError("SECRET"), "timeout"),
    (subprocess.TimeoutExpired("SECRET", 1), "timeout"),
    (http.client.IncompleteRead(b"SECRET"), "invalid_response"),
    (http.client.BadStatusLine("SECRET"), "invalid_response"),
])
def test_transport_failures_remain_per_account_errors(profile, monkeypatch, error, expected):
    opener(monkeypatch, error=error)
    result = claude_usage.refresh_usage(profile)
    assert result["refresh_error"] == expected
    assert "SECRET" not in json.dumps(result)


@pytest.mark.parametrize("raw", [b"SECRET", b"[]", b"x" * 65537])
def test_invalid_response_cannot_leak_provider_data(profile, monkeypatch, raw):
    monkeypatch.setattr(claude_usage.urllib.request, "build_opener",
                        lambda *args: SimpleNamespace(open=lambda *a, **kw: io.BytesIO(raw)))
    result = claude_usage.refresh_usage(profile)
    assert result["refresh_error"] == "invalid_response"
    assert "SECRET" not in json.dumps(result)


def test_redirect_cannot_forward_credentials():
    request = claude_usage.urllib.request.Request(claude_usage.USAGE_URL)
    with pytest.raises(claude_usage.UsageError, match="redirect_refused"):
        claude_usage.NoRedirect().redirect_request(request, None, 302, "redirect", {}, "https://elsewhere.invalid")


@pytest.mark.parametrize("directory", [None, "/tmp/.claude", "/tmp/profile", "/tmp/cafe\u0301/../profile"])
def test_native_keychain_service_uses_raw_nfc_directory(directory):
    normalized = unicodedata.normalize("NFC", directory) if directory else ""
    suffix = "-" + hashlib.sha256(normalized.encode()).hexdigest()[:8] if directory else ""
    assert claude_usage.keychain_service(directory) == "Claude Code-credentials" + suffix


def test_keychain_reads_only_selected_service_and_account(profile, monkeypatch):
    monkeypatch.setattr(claude_usage, "IS_MACOS", True)
    monkeypatch.setenv("USER", "test-user")
    calls = []
    raw = json.dumps({"claudeAiOauth": {"accessToken": TOKEN}}).encode()
    def keychain(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout=raw)
    monkeypatch.setattr(claude_usage.subprocess, "run", keychain)
    credentials = claude_usage.read_credentials(profile, 5)
    assert claude_usage.access_token(credentials) == TOKEN
    assert calls == [["/usr/bin/security", "find-generic-password", "-a", "test-user",
                      "-w", "-s", claude_usage.keychain_service(profile)]]


def test_missing_named_keychain_never_uses_default_service(profile, monkeypatch):
    monkeypatch.setattr(claude_usage, "IS_MACOS", True)
    (Path(profile) / ".credentials.json").rename(Path(profile) / "backup.json")
    calls = []
    def keychain(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=44, stdout=b"")
    monkeypatch.setattr(claude_usage.subprocess, "run", keychain)
    assert claude_usage.refresh_usage(profile)["refresh_error"] == "not_authenticated"
    assert len(calls) == 1 and calls[0][-1] != "Claude Code-credentials"


def test_keychain_access_denied_does_not_silently_fall_back_to_file(profile, monkeypatch):
    monkeypatch.setattr(claude_usage, "IS_MACOS", True)
    monkeypatch.setattr(claude_usage.subprocess, "run",
                        lambda *a, **kw: SimpleNamespace(returncode=36, stdout=b"SECRET"))
    assert claude_usage.refresh_usage(profile)["refresh_error"] == "keychain_unavailable"


@pytest.mark.parametrize("expiry", [True, "invalid", float("nan"), float("inf"), 10 ** 400])
def test_malformed_expiry_returns_error_before_http(profile, expiry):
    (Path(profile) / ".credentials.json").write_text(json.dumps({"claudeAiOauth": {
        "accessToken": TOKEN, "expiresAt": expiry,
    }}))
    assert claude_usage.refresh_usage(profile)["refresh_error"] == "invalid_credentials"


def test_expired_token_is_not_rotated_or_sent(profile):
    path = Path(profile) / ".credentials.json"
    path.write_text(json.dumps({"claudeAiOauth": {"accessToken": TOKEN, "refreshToken": "PRIVATE", "expiresAt": 1}}))
    before = path.read_bytes()
    assert claude_usage.refresh_usage(profile)["refresh_error"] == "authentication_expired"
    assert path.read_bytes() == before


def test_storage_override_cannot_redirect_all_profiles(profile, monkeypatch):
    monkeypatch.setenv("CLAUDE_SECURESTORAGE_CONFIG_DIR", "")
    assert claude_usage.refresh_usage(profile)["refresh_error"] == "credential_location_override"


@pytest.mark.parametrize("percentage", [True, -1, 101, "25", float("nan"), None])
def test_invalid_window_percentage_stays_unknown(percentage):
    raw = response(percentage)
    assert "five_hour" not in claude_usage.quota_windows(raw)


@pytest.mark.parametrize("reset", ["invalid", "2090-01-01T00:00:00", None, 123])
def test_invalid_or_timezone_free_reset_stays_unknown(reset):
    raw = response()
    raw["five_hour"]["resets_at"] = reset
    assert "five_hour" not in claude_usage.quota_windows(raw)


@pytest.mark.parametrize("timeout", [True, 0, -1, float("nan"), float("inf")])
def test_invalid_timeout_does_not_access_credentials(timeout):
    assert claude_usage.refresh_usage(None, timeout=timeout)["refresh_error"] == "invalid_timeout"
