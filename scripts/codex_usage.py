# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Read subscription quotas through Codex's documented app-server protocol.

No model turn, credential parsing, login, or account mutation is performed.
Protocol: https://learn.chatgpt.com/docs/app-server
"""

from __future__ import annotations

import json
import math
import os
import selectors
import subprocess
import time
from pathlib import Path

MAX_TIMESTAMP = 253_402_300_799
MAX_PROTOCOL_BYTES = 2_097_152
WINDOW_DURATIONS = {300: "five_hour", 10080: "seven_day"}


class UsageError(Exception):
    """A safe error code; upstream messages must never reach the display."""


def number(value: object, maximum: float) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not 0 <= value <= maximum:
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def quota_windows(result: dict[str, object]) -> dict[str, dict[str, float]]:
    buckets = result.get("rateLimitsByLimitId")
    bucket = buckets.get("codex") if isinstance(buckets, dict) else None
    if bucket is None:
        bucket = result.get("rateLimits")
    if not isinstance(bucket, dict) or bucket.get("limitId") not in (None, "codex"):
        return {}
    windows: dict[str, dict[str, float]] = {}
    for slot in ("primary", "secondary"):
        raw = bucket.get(slot)
        if not isinstance(raw, dict):
            continue
        duration = number(raw.get("windowDurationMins"), MAX_TIMESTAMP)
        name = WINDOW_DURATIONS.get(int(duration)) if duration is not None and duration.is_integer() else None
        percentage = number(raw.get("usedPercent"), 100)
        reset = number(raw.get("resetsAt"), MAX_TIMESTAMP)
        if name and percentage is not None and reset is not None:
            windows[name] = {"used_percentage": percentage, "resets_at": reset}
    return windows


def rpc_error(error: object) -> UsageError:
    if not isinstance(error, dict):
        return UsageError("protocol_error")
    message = str(error.get("message", "")).lower()
    if any(text in message for text in (
        "unauthorized", "not authenticated", "not logged", "login required", "authentication required",
    )):
        return UsageError("not_authenticated")
    if any(text in message for text in ("api key", "api-key", "apikey", "requires chatgpt")):
        return UsageError("api_key_unsupported")
    if error.get("code") == -32601:
        return UsageError("unsupported_cli")
    return UsageError("request_failed")


class Connection:
    """Bounded newline JSON transport with one deadline for the entire read."""

    def __init__(self, process: subprocess.Popen[bytes], deadline: float) -> None:
        self.process = process
        self.deadline = deadline
        self.pending = b""
        self.total_bytes = 0

    def send(self, message: dict[str, object]) -> None:
        if self.process.stdin is None:
            raise UsageError("protocol_error")
        self.process.stdin.write(json.dumps(message).encode() + b"\n")
        self.process.stdin.flush()

    def receive(self) -> dict[str, object]:
        if self.process.stdout is None:
            raise UsageError("protocol_error")
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            while b"\n" not in self.pending:
                remaining = self.deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise UsageError("timeout")
                chunk = os.read(self.process.stdout.fileno(), 65_536)
                if not chunk:
                    raise UsageError("process_exited")
                self.total_bytes += len(chunk)
                if self.total_bytes > MAX_PROTOCOL_BYTES:
                    raise UsageError("protocol_error")
                self.pending += chunk
        line, self.pending = self.pending.split(b"\n", 1)
        try:
            value = json.loads(line)
        except (ValueError, UnicodeError) as error:
            raise UsageError("protocol_error") from error
        if not isinstance(value, dict):
            raise UsageError("protocol_error")
        return value

    def response(self, request_id: int) -> dict[str, object]:
        while time.monotonic() < self.deadline:
            message = self.receive()
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise rpc_error(message["error"])
            result = message.get("result")
            if isinstance(result, dict):
                return result
            raise UsageError("protocol_error")
        raise UsageError("timeout")


def stop_process(process: subprocess.Popen[bytes]) -> None:
    """Reap only the app-server we created, including a hung server."""
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=0.3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1)
    for stream in (process.stdin, process.stdout):
        if stream is not None:
            stream.close()


def request_usage(config_dir: Path, timeout: float) -> dict[str, object]:
    env = os.environ.copy()
    if any(env.get(name) for name in ("CODEX_ACCESS_TOKEN", "CODEX_API_KEY", "OPENAI_API_KEY")):
        raise UsageError("auth_override")
    directory = config_dir.expanduser().resolve()
    if not directory.is_dir():
        raise UsageError("profile_not_initialized")
    env["CODEX_HOME"] = str(directory)
    env.pop("CODEX_SQLITE_HOME", None)
    try:
        process = subprocess.Popen(
            ["codex", "-c", "sqlite_home=" + json.dumps(str(directory)),
             "app-server", "--listen", "stdio://"], env=env, cwd=directory,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as error:
        raise UsageError("codex_not_found") from error
    try:
        connection = Connection(process, time.monotonic() + timeout)
        connection.send({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "ai_toolkit_usage", "title": "AI Toolkit usage", "version": "1.0"},
        }})
        connection.response(1)
        connection.send({"method": "initialized", "params": {}})
        connection.send({"id": 2, "method": "account/rateLimits/read"})
        return connection.response(2)
    finally:
        stop_process(process)


def failed_refresh(code: str) -> dict[str, object]:
    return {"state": "error", "observed_at": None, "age_seconds": None, "windows": {},
            "refresh_error": code, "refreshed": False}


def refresh_usage(config_dir: Path, *, timeout: float = 10) -> dict[str, object]:
    """Read current quotas without a model turn, disk cache, or historical fallback."""
    if number(timeout, 300) is None or timeout <= 0:
        return failed_refresh("invalid_timeout")
    try:
        windows = quota_windows(request_usage(config_dir, timeout))
        if not windows:
            return failed_refresh("usage_unavailable")
        return {"state": "live", "observed_at": time.time(), "age_seconds": 0.0,
                "windows": {name: {**window, "state": "live"} for name, window in windows.items()},
                "refreshed": True}
    except UsageError as error:
        return failed_refresh(str(error))
    except (OSError, subprocess.SubprocessError):
        return failed_refresh("io_error")
