#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Check QA descriptors against a clean Git worktree and an HTTP endpoint.

Only fixed Git read commands and bounded HTTP GET requests are executed. Runtime
commands in the descriptor are data; this helper never starts or stops resources.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import ipaddress
import json
import queue
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlsplit

MAX_DESCRIPTOR_BYTES = 65536
MAX_IDENTITY_BYTES = 16384
GIT_TIMEOUT = 10
IDENTITY_FIELDS = ("repository", "worktree", "headSha", "sourceFingerprint")
REQUIRED_FIELDS = {
    "version", "runId", *IDENTITY_FIELDS, "baseUrl", "healthUrl", "browser",
    "ownership", "commands", "credentials", "artifactsDir",
}


class CheckError(ValueError):
    """A descriptor, source, or readiness check failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


def git(worktree: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", str(worktree), *args],
        capture_output=True,
        text=True, timeout=GIT_TIMEOUT, check=False,
    )
    require(result.returncode == 0, "Git source inspection failed")
    return result.stdout.strip()


def require_clean_source(worktree: Path, inspected: set[Path]) -> None:
    require(worktree not in inspected, "recursive submodule source identity cannot be verified")
    inspected.add(worktree)
    root = Path(git(worktree, "rev-parse", "--show-toplevel")).resolve()
    require(root == worktree, "worktree root is invalid or a submodule is uninitialized")
    index_entries = git(worktree, "ls-files", "-v", "-z").split("\0")
    require(not any(entry and (entry[0].islower() or entry[0] == "S") for entry in index_entries),
            "source cannot be verified with assume-unchanged or skip-worktree flags")
    status = git(worktree, "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none")
    require(not status, "source is dirty; commit the intended source before QA")
    for entry in git(worktree, "ls-files", "--stage", "-z").split("\0"):
        if entry.startswith("160000 "):
            module_path = worktree / entry.split("\t", 1)[1]
            require((module_path / ".git").exists(), "submodule is uninitialized; source cannot be verified")
            require_clean_source(module_path.resolve(strict=True), inspected)


def snapshot(worktree: Path) -> dict[str, str]:
    worktree = worktree.resolve(strict=True)
    require_clean_source(worktree, set())
    repository = Path(git(worktree, "rev-parse", "--git-common-dir"))
    if not repository.is_absolute():
        repository = worktree / repository
    head = git(worktree, "rev-parse", "HEAD")
    tree = git(worktree, "rev-parse", "HEAD^{tree}")
    fingerprint = hashlib.sha256(f"{worktree}\n{head}\n{tree}".encode()).hexdigest()
    return {
        "repository": str(repository.resolve()), "worktree": str(worktree),
        "headSha": head, "sourceFingerprint": fingerprint,
    }


def object_fields(value: Any, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CheckError("expected a JSON object")
    require(required <= value.keys(), "descriptor is missing required fields")
    require(value.keys() <= required | (optional or set()), "descriptor has unsupported fields")
    return value


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not any(ord(c) < 32 for c in value)


def read_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), "descriptor must be a regular file")
    require(path.stat().st_size <= MAX_DESCRIPTOR_BYTES, "descriptor is too large")
    data = json.loads(path.read_text(encoding="utf-8"))
    return object_fields(data, REQUIRED_FIELDS, {"readiness"})


def validate_metadata(data: dict[str, Any]) -> None:
    require(type(data["version"]) is int and data["version"] == 1, "unsupported descriptor version")
    require(nonempty_string(data["runId"]), "runId must be nonempty")
    require(all(nonempty_string(data[name]) for name in IDENTITY_FIELDS), "invalid source identity")
    browser = object_fields(data["browser"], {"provider"}, {"command"})
    require(nonempty_string(browser["provider"]), "browser provider must be nonempty")
    if "command" in browser:
        require(nonempty_string(browser["command"]), "browser command must be nonempty")
    commands = object_fields(data["commands"], {"start", "stop"})
    require(all(value is None or nonempty_string(value) for value in commands.values()),
            "commands must be nonempty strings or null")
    credentials = data["credentials"]
    require(isinstance(credentials, dict), "credentials must contain environment references")
    require(all(nonempty_string(key) and isinstance(value, str)
                and re.fullmatch(r"[A-Z_][A-Z0-9_]*", value)
                for key, value in credentials.items()),
            "credentials must contain environment variable names only")
    validate_ownership(data["ownership"], commands)


def validate_ownership(value: Any, commands: dict[str, Any]) -> None:
    ownership = object_fields(value, {"startedByRun", "resources"})
    require(type(ownership["startedByRun"]) is bool, "startedByRun must be a boolean")
    require(isinstance(ownership["resources"], list), "resources must be an array")
    for resource in ownership["resources"]:
        resource = object_fields(resource, {"kind", "id", "identity"})
        require(isinstance(resource["kind"], str)
                and resource["kind"] in {"process", "container", "service", "preview"},
                "unsupported owned resource kind")
        require(nonempty_string(resource["id"]) and nonempty_string(resource["identity"]),
                "resource id and creation identity are required")
    if ownership["startedByRun"]:
        require(bool(ownership["resources"]) and all(commands.values()),
                "owned environments require resources and start/stop commands")
    else:
        require(not ownership["resources"] and commands["stop"] is None,
                "reused environments cannot claim owned resources or a stop command")


def validate_paths(data: dict[str, Any], descriptor: Path, run_dir: Path, worktree: Path) -> None:
    require(run_dir.is_absolute(), "run directory must be absolute")
    run_dir = run_dir.resolve(strict=True)
    roots = [line[9:] for line in git(worktree, "worktree", "list", "--porcelain", "-z").split("\0")
             if line.startswith("worktree ")]
    require(not any(run_dir.is_relative_to(Path(root).resolve()) for root in roots),
            "run directory must be outside every repository worktree")
    require(descriptor.resolve(strict=True).is_relative_to(run_dir),
            "descriptor must be inside the run directory")
    require(isinstance(data["artifactsDir"], str), "artifactsDir must be an absolute path")
    artifacts = Path(data["artifactsDir"])
    require(artifacts.is_absolute() and artifacts.resolve().is_relative_to(run_dir),
            "artifactsDir must be inside the run directory")


def parse_url(value: Any) -> SplitResult:
    if not isinstance(value, str) or not nonempty_string(value):
        raise CheckError("endpoint URL must be a nonempty string")
    parsed = urlsplit(value)
    require(parsed.scheme in {"http", "https"} and bool(parsed.hostname), "invalid HTTP endpoint")
    require(parsed.username is None and parsed.password is None and not parsed.query and not parsed.fragment,
            "endpoint credentials, query strings and fragments are unsupported")
    require("\\" not in value and "%" not in parsed.netloc, "invalid endpoint address")
    require(parsed.port is None or 1 <= parsed.port <= 65535, "invalid endpoint port")
    return parsed


def origin(parsed: SplitResult) -> tuple[str, str, int]:
    return parsed.scheme, parsed.hostname or "", parsed.port or (443 if parsed.scheme == "https" else 80)


def validate_url(value: Any, remote_origins: set[tuple[str, str, int]]) -> SplitResult:
    parsed = parse_url(value)
    try:
        local = ipaddress.ip_address(parsed.hostname or "").is_loopback
    except ValueError:
        local = parsed.hostname == "localhost"
    if not local:
        require(parsed.scheme == "https" and origin(parsed) in remote_origins,
                "remote endpoint requires an explicit HTTPS origin allowlist")
    return parsed


def allow_origins(values: list[str]) -> set[tuple[str, str, int]]:
    result = set()
    for value in values:
        parsed = parse_url(value)
        require(parsed.scheme == "https" and parsed.path in {"", "/"},
                "remote allowlist entries must be HTTPS origins")
        result.add(origin(parsed))
    return result


def request_http(url: SplitResult, timeout: float, identity: bool) -> bytes:
    host = "127.0.0.1" if url.hostname == "localhost" else url.hostname or ""
    connection_class = http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
    connection = connection_class(host, port=url.port, timeout=timeout)
    try:
        connection.request("GET", url.path or "/", headers={"Accept": "application/json"})
        response = connection.getresponse()
        require(200 <= response.status < 300, "readiness endpoint returned a non-2xx status; redirects are refused")
        body = response.read(MAX_IDENTITY_BYTES + 1) if identity else b""
        require(len(body) <= MAX_IDENTITY_BYTES, "runtime identity response is too large")
        return body
    finally:
        connection.close()


def request(url: SplitResult, timeout: float, identity: bool = False) -> bytes:
    """Bound the entire probe, including DNS and slowly streamed HTTP headers."""
    result: queue.Queue[bytes | Exception] = queue.Queue(maxsize=1)

    def probe() -> None:
        try:
            result.put(request_http(url, timeout, identity))
        except (OSError, ValueError, http.client.HTTPException) as error:
            result.put(error)

    threading.Thread(target=probe, daemon=True).start()
    try:
        response = result.get(timeout=timeout)
    except queue.Empty as error:
        raise CheckError("readiness endpoint exceeded the request deadline") from error
    if isinstance(response, Exception):
        raise response
    return response


def check(args: argparse.Namespace) -> dict[str, Any]:
    source = snapshot(args.worktree)
    data = read_json(args.descriptor)
    validate_metadata(data)
    require(all(data[name] == source[name] for name in IDENTITY_FIELDS),
            "descriptor source identity is stale or belongs to another worktree")
    validate_paths(data, args.descriptor, args.run_dir, args.worktree)
    remote_origins = allow_origins(args.allow_remote_origin)
    base = validate_url(data["baseUrl"], remote_origins)
    health = validate_url(data["healthUrl"], remote_origins)
    require(origin(base) == origin(health), "baseUrl and healthUrl must share an origin")
    identity_url = None
    if "readiness" in data:
        readiness = object_fields(data["readiness"], {"identityUrl"})
        identity_url = validate_url(readiness["identityUrl"], remote_origins)
        require(origin(base) == origin(identity_url), "identity URL must share the application origin")
    request(health, args.timeout)
    if identity_url:
        runtime = json.loads(request(identity_url, args.timeout, identity=True))
        runtime = object_fields(runtime, set(IDENTITY_FIELDS))
        require(all(runtime[name] == source[name] for name in IDENTITY_FIELDS),
                "running application source identity does not match the worktree")
    require(snapshot(args.worktree) == source, "source changed during readiness check")
    return {"ok": True, "runId": data["runId"], **source, "httpReady": True,
            "runtimeIdentity": "verified" if identity_url else "unverified",
            "artifactsDir": data["artifactsDir"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    source = commands.add_parser("snapshot", help="print a clean Git source identity as JSON")
    source.add_argument("--worktree", required=True, type=Path)
    readiness = commands.add_parser("check", help="validate a descriptor and probe HTTP readiness")
    readiness.add_argument("--descriptor", required=True, type=Path)
    readiness.add_argument("--worktree", required=True, type=Path)
    readiness.add_argument("--run-dir", required=True, type=Path)
    readiness.add_argument("--timeout", type=float, default=3.0)
    readiness.add_argument("--allow-remote-origin", action="append", default=[])
    args = parser.parse_args()
    try:
        if args.command == "snapshot":
            result: dict[str, Any] = {"ok": True, **snapshot(args.worktree)}
        else:
            require(0 < args.timeout <= 10, "timeout must be greater than zero and at most 10 seconds")
            result = check(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (CheckError, OSError, ValueError, RecursionError,
            subprocess.TimeoutExpired, http.client.HTTPException) as error:
        message = str(error) if isinstance(error, CheckError) else "descriptor, Git or HTTP inspection failed"
        print(json.dumps({"ok": False, "error": message}, sort_keys=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
