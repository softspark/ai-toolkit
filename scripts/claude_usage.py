# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Read live subscription limits using the same OAuth endpoint as Claude /usage.

The internal endpoint and credential layout were verified against Claude Code
2.1.289. Credentials stay in memory, are never copied, and are not refreshed or
rewritten here. Native Claude owns token rotation and its concurrent locks.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

IS_MACOS = sys.platform == "darwin"
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
MAX_BYTES = 65_536
WINDOW_NAMES = ("five_hour", "seven_day")


class UsageError(Exception):
    """A fixed error code that never contains provider messages or credentials."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int,
                         msg: str, headers: Any, newurl: str) -> None:
        raise UsageError("redirect_refused")


def keychain_service(config_dir: str | None) -> str:
    suffix = ""
    if config_dir:
        suffix = "-" + hashlib.sha256(unicodedata.normalize("NFC", config_dir).encode()).hexdigest()[:8]
    return "Claude Code-credentials" + suffix


def keychain_account() -> str:
    import pwd

    name = os.environ.get("USER") or pwd.getpwuid(os.getuid()).pw_name
    return name if re.fullmatch(r"[a-zA-Z0-9._-]+", name) else "claude-code-user"


def parse_credentials(raw: bytes) -> dict[str, object]:
    if len(raw) > MAX_BYTES:
        raise UsageError("invalid_credentials")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError) as error:
        raise UsageError("invalid_credentials") from error
    if not isinstance(value, dict):
        raise UsageError("invalid_credentials")
    return value


def read_credentials(config_dir: str | None, timeout: float) -> dict[str, object]:
    # A parent process's storage override must not merge unrelated profile logins.
    if "CLAUDE_SECURESTORAGE_CONFIG_DIR" in os.environ:
        raise UsageError("credential_location_override")
    directory = Path(unicodedata.normalize("NFC", config_dir)) if config_dir else Path.home() / ".claude"
    if not directory.is_dir():
        raise UsageError("not_authenticated")
    if IS_MACOS:
        result = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-a", keychain_account(),
             "-w", "-s", keychain_service(config_dir)],
            capture_output=True, timeout=min(timeout, 5), check=False,
        )
        if result.returncode == 0:
            return parse_credentials(result.stdout.strip())
        if result.returncode != 44:
            raise UsageError("keychain_unavailable")
    try:
        with (directory / ".credentials.json").open("rb") as stream:
            return parse_credentials(stream.read(MAX_BYTES + 1))
    except FileNotFoundError as error:
        raise UsageError("not_authenticated") from error
    except OSError as error:
        raise UsageError("credentials_unavailable") from error


def access_token(credentials: dict[str, object]) -> str:
    oauth = credentials.get("claudeAiOauth")
    if not isinstance(oauth, dict):
        raise UsageError("not_authenticated")
    token = oauth.get("accessToken")
    if not isinstance(token, str) or not token or not token.isascii() or any(char.isspace() for char in token):
        raise UsageError("invalid_credentials")
    expiry = oauth.get("expiresAt")
    if expiry is not None:
        if isinstance(expiry, bool) or not isinstance(expiry, (int, float)) or not 0 <= expiry <= 253_402_300_799_000:
            raise UsageError("invalid_credentials")
        if expiry <= time.time() * 1000:
            raise UsageError("authentication_expired")
    return token


def request_usage(config_dir: str | None, timeout: float) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    token = access_token(read_credentials(config_dir, timeout))
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise UsageError("timeout")
    request = urllib.request.Request(USAGE_URL, headers={
        "Authorization": "Bearer " + token,
        "anthropic-beta": "oauth-2025-04-20",
        "Content-Type": "application/json",
        "User-Agent": "ai-toolkit-usage/1.0",
    })
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=remaining) as response:
            raw = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        code = {401: "authentication_expired", 403: "permission_denied", 429: "rate_limited"}.get(
            error.code, "request_failed")
        error.close()
        raise UsageError(code) from None
    if len(raw) > MAX_BYTES:
        raise UsageError("invalid_response")
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeError) as error:
        raise UsageError("invalid_response") from error
    if not isinstance(result, dict):
        raise UsageError("invalid_response")
    return result


def quota_windows(result: dict[str, object]) -> dict[str, dict[str, object]]:
    windows: dict[str, dict[str, object]] = {}
    for name in WINDOW_NAMES:
        raw = result.get(name)
        if not isinstance(raw, dict):
            continue
        percentage, reset = raw.get("utilization"), raw.get("resets_at")
        if isinstance(percentage, bool) or not isinstance(percentage, (int, float)) or not 0 <= percentage <= 100:
            continue
        if not isinstance(reset, str):
            continue
        try:
            moment = datetime.fromisoformat(reset.replace("Z", "+00:00"))
            if moment.tzinfo is None:
                continue
            timestamp = moment.timestamp()
        except (ValueError, OverflowError, OSError):
            continue
        if timestamp < 0:
            continue
        windows[name] = {"used_percentage": float(percentage), "resets_at": timestamp, "state": "live"}
    return windows


def failed_usage(code: str) -> dict[str, object]:
    return {"state": "error", "observed_at": None, "age_seconds": None, "windows": {},
            "refreshed": False, "refresh_error": code}


def refresh_usage(config_dir: str | None, *, timeout: float = 10) -> dict[str, object]:
    """Fetch now; never read or write quota snapshots and never return old data."""
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 300:
        return failed_usage("invalid_timeout")
    try:
        windows = quota_windows(request_usage(config_dir, timeout))
        if not windows:
            return failed_usage("usage_unavailable")
        return {"state": "live", "observed_at": time.time(), "age_seconds": 0.0,
                "windows": windows, "refreshed": True}
    except UsageError as error:
        return failed_usage(str(error))
    except (TimeoutError, subprocess.TimeoutExpired):
        return failed_usage("timeout")
    except http.client.HTTPException:
        return failed_usage("invalid_response")
    except (OSError, subprocess.SubprocessError):
        return failed_usage("io_error")
