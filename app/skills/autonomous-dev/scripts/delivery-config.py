#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Read-only project preflight; never contact MCP, run commands or write files."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import stat
from pathlib import Path
from typing import NoReturn, TypedDict, cast
from urllib.parse import urlsplit

MAX_CONFIG_BYTES = 256 * 1024
PROJECT_KEY = re.compile(r"[A-Z][A-Z0-9_]*")
TASK_KEY = re.compile(r"([A-Z][A-Z0-9_]*)-[1-9][0-9]*")
GITHUB_REPOSITORY = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?/[A-Za-z0-9_.-]+")
LIVE_CHECKS = [
    "Config validation does not verify MCP availability or remote project-to-instance mapping.",
    "The skill must verify Jira permissions and allowed status transitions live.",
    "The skill must verify Git repository ownership and publication permissions live; a Jira key does not establish them.",
    "Validation commands are data only; their existence and results require project checks.",
]


class Diagnostic(TypedDict):
    level: str
    code: str
    field: str
    message: str


class TaskIdentity(TypedDict):
    provider: str
    key: str
    url: str
    subject: str


class ConfigReport(TypedDict):
    ok: bool
    config: dict[str, object] | None
    task: TaskIdentity | None
    diagnostics: list[Diagnostic]
    liveChecks: list[str]


class ConfigError(Exception):
    """A diagnostic whose message never includes raw configuration values."""

    def __init__(self, code: str, field: str, message: str) -> None:
        super().__init__(message)
        self.diagnostic: Diagnostic = {
            "level": "error",
            "code": code,
            "field": field,
            "message": message,
        }


class JsonParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ConfigError(
            "arguments",
            "cli",
            "Use --config PATH and optional --task KEY_OR_BROWSE_URL; see --help.",
        )


def _object(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ConfigError("type", field, "Expected a JSON object.")
    return cast("dict[str, object]", value)


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ConfigError("type", field, "Expected a nonempty string without NUL characters.")
    return value.strip()


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError("type", field, "Expected a boolean.")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError(
                "json_duplicate_key",
                "config",
                "Duplicate JSON keys are ambiguous and must be removed.",
            )
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    raise ConfigError("json_number", "config", "JSON must not contain nonfinite numbers.")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        _reject_constant(value)
    return number


def load_config(path: Path) -> dict[str, object]:
    """Read at most 256 KiB from a regular UTF-8 file and reject ambiguous JSON."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise ConfigError("config_file", "config", "Configuration must be a regular file.")
            if metadata.st_size > MAX_CONFIG_BYTES:
                raise ConfigError("config_size", "config", "Configuration exceeds the 256 KiB limit.")
            data = stream.read(MAX_CONFIG_BYTES + 1)
        if len(data) > MAX_CONFIG_BYTES:
            raise ConfigError("config_size", "config", "Configuration exceeds the 256 KiB limit.")
        value: object = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
    except OSError as error:
        raise ConfigError(
            "config_read",
            "config",
            "Cannot read configuration; check its path and permissions.",
        ) from error
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ConfigError("config_json", "config", "Configuration must be valid, bounded UTF-8 JSON.") from error
    return _object(value, "config")


def _repository(value: object, field: str) -> str:
    repository = _text(value, field)
    if not GITHUB_REPOSITORY.fullmatch(repository) or repository.split("/")[1] in {
        ".",
        "..",
    }:
        raise ConfigError(
            "repository",
            field,
            "Expected a GitHub owner/repository identity, without a URL or credentials.",
        )
    return repository.lower()


def _https_url(value: object, field: str) -> str:
    url = _text(value, field)
    if any(character.isspace() or ord(character) < 32 for character in url) or any(c in url for c in "\\%?#"):
        raise ConfigError(
            "url",
            field,
            "Use a canonical HTTPS URL without whitespace, escaping, query or fragment.",
        )
    try:
        parsed = urlsplit(url)
        port = parsed.port
        hostname = parsed.hostname
    except ValueError as error:
        raise ConfigError("url", field, "Use a valid HTTPS instance URL.") from error
    if parsed.scheme != "https" or not hostname or parsed.username is not None or parsed.password is not None:
        raise ConfigError("url", field, "Use HTTPS with a host and no embedded credentials.")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", hostname) or parsed.netloc.endswith(":"):
        raise ConfigError("url", field, "Use a canonical DNS host or IPv4 address.")
    path = parsed.path.rstrip("/")
    if not re.fullmatch(r"(?:/[A-Za-z0-9._~-]+)*", path) or any(part in {".", ".."} for part in path.split("/")):
        raise ConfigError(
            "url",
            field,
            "Use a canonical instance path without empty or relative segments.",
        )
    authority = hostname.lower() if port in {None, 443} else f"{hostname.lower()}:{port}"
    return f"https://{authority}{path}"


def _status_mapping(value: object) -> dict[str, object]:
    mapping = _object(value, "issueTracker.statusMapping")
    if set(mapping) - {"implement", "readyPr"}:
        raise ConfigError(
            "status_mapping",
            "issueTracker.statusMapping",
            "Only implement and readyPr mappings are supported.",
        )
    return {
        stage: None if name is None else _text(name, f"issueTracker.statusMapping.{stage}")
        for stage, name in mapping.items()
    }


def _issue_tracker(value: object) -> dict[str, object]:
    tracker = _object(value, "issueTracker")
    provider = _text(tracker.get("provider"), "issueTracker.provider")
    if provider == "none":
        return {"provider": "none"}
    if provider == "github":
        return {
            "provider": provider,
            "repository": _repository(tracker.get("repository"), "issueTracker.repository"),
        }
    if provider != "jira-mcp":
        raise ConfigError(
            "provider",
            "issueTracker.provider",
            "Supported providers: none, github, jira-mcp.",
        )
    project = _text(tracker.get("projectKey"), "issueTracker.projectKey")
    if not PROJECT_KEY.fullmatch(project):
        raise ConfigError(
            "project_key",
            "issueTracker.projectKey",
            "Expected an uppercase Jira project key.",
        )
    result: dict[str, object] = {"provider": provider, "projectKey": project}
    if "instanceUrl" in tracker:
        result["instanceUrl"] = _https_url(tracker["instanceUrl"], "issueTracker.instanceUrl")
    if "statusMapping" in tracker:
        result["statusMapping"] = _status_mapping(tracker["statusMapping"])
    return result


def _code_host(value: object) -> dict[str, object]:
    host = _object(value, "codeHost")
    provider = _text(host.get("provider"), "codeHost.provider")
    if provider == "none":
        return {"provider": "none"}
    if provider == "github":
        return {
            "provider": provider,
            "repository": _repository(host.get("repository"), "codeHost.repository"),
        }
    raise ConfigError("provider", "codeHost.provider", "Supported providers: none, github.")


def _delivery_roles(
    raw: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    legacy: dict[str, object] | None = None
    if "tracker" in raw:
        tracker = _object(raw["tracker"], "tracker")
        if tracker.get("provider") not in ("github", "none"):
            raise ConfigError(
                "provider",
                "tracker.provider",
                "Legacy tracker supports github or none; use explicit roles.",
            )
        legacy = _code_host(tracker)
    default = legacy if legacy is not None else {"provider": "none"}
    issue_tracker = _issue_tracker(raw.get("issueTracker", default))
    code_host = _code_host(raw.get("codeHost", default))
    if legacy is not None and (issue_tracker != legacy or code_host != legacy):
        raise ConfigError(
            "role_conflict",
            "tracker",
            "Legacy tracker conflicts with explicit roles; remove it or align both roles.",
        )
    return issue_tracker, code_host


def _knowledge(value: object) -> dict[str, object]:
    knowledge = _object(value, "knowledge")
    provider = _text(knowledge.get("provider"), "knowledge.provider")
    if provider not in {"local", "rag-mcp"}:
        raise ConfigError("provider", "knowledge.provider", "Supported providers: local, rag-mcp.")
    result: dict[str, object] = {
        "provider": provider,
        "required": _boolean(knowledge.get("required", False), "knowledge.required"),
    }
    if provider == "rag-mcp":
        services = knowledge.get("services")
        if not isinstance(services, list) or not services:
            raise ConfigError(
                "services",
                "knowledge.services",
                "rag-mcp requires a nonempty list of technical service names.",
            )
        result["services"] = list(dict.fromkeys(_text(service, "knowledge.services") for service in services))
    return result


def _validation(value: object) -> dict[str, object]:
    commands = _object(value, "validation").get("commands")
    if not isinstance(commands, list) or not commands:
        raise ConfigError(
            "commands",
            "validation.commands",
            "Provide a nonempty list of actual project command strings.",
        )
    checked: list[str] = []
    for command in commands:
        _text(command, "validation.commands")
        checked.append(cast("str", command))
    return {"commands": checked}


def _qa(value: object) -> dict[str, object]:
    qa = _object(value, "qa")
    result: dict[str, object] = {"required": _boolean(qa.get("required"), "qa.required")}
    for name in ("browserProvider", "startCommand", "healthPath"):
        if name in qa:
            _text(qa[name], f"qa.{name}")
            result[name] = qa[name]
    return result


def _ci(value: object) -> dict[str, object]:
    ci = _object(value, "ci")
    required = _boolean(ci.get("required"), "ci.required")
    wait = ci.get("maxWaitMinutes", 20)
    if type(wait) is not int or not 0 <= wait <= 60:
        raise ConfigError("wait_budget", "ci.maxWaitMinutes", "Expected an integer from 0 through 60.")
    return {"required": required, "maxWaitMinutes": wait}


def normalize_config(raw: dict[str, object]) -> dict[str, object]:
    """Normalize known fields; unknown custom fields remain only in the input file."""
    if type(raw.get("version")) is not int or raw.get("version") != 1:
        raise ConfigError("version", "version", "Only integer configuration version 1 is supported.")
    issue_tracker, code_host = _delivery_roles(raw)
    labels = _object(raw.get("labels", {}), "labels")
    return {
        "version": 1,
        "baseBranch": _text(raw.get("baseBranch"), "baseBranch"),
        "validation": _validation(raw.get("validation")),
        "issueTracker": issue_tracker,
        "codeHost": code_host,
        "knowledge": _knowledge(raw.get("knowledge", {"provider": "local"})),
        "qa": _qa(raw.get("qa")),
        "ci": _ci(raw.get("ci")),
        "labels": {"enabled": _boolean(labels.get("enabled", False), "labels.enabled")},
    }


def resolve_task(config: dict[str, object], task: str) -> TaskIdentity:
    """Resolve an explicitly mapped Jira key/URL; this does not validate remote identity."""
    tracker = _object(config.get("issueTracker"), "issueTracker")
    if tracker.get("provider") != "jira-mcp":
        raise ConfigError("task_provider", "task", "--task requires issueTracker.provider=jira-mcp.")
    if "instanceUrl" not in tracker:
        raise ConfigError(
            "instance_required",
            "issueTracker.instanceUrl",
            "Obtain the configured instance identity from jira-mcp before resolving a task.",
        )
    instance = _https_url(tracker["instanceUrl"], "issueTracker.instanceUrl")
    source = _text(task, "task")
    candidate = source if TASK_KEY.fullmatch(source) else _https_url(source, "task")
    key = candidate.rsplit("/", 1)[-1]
    match = TASK_KEY.fullmatch(key)
    if match is None:
        raise ConfigError(
            "task_key",
            "task",
            "Expected an uppercase Jira key or its canonical /browse/KEY URL.",
        )
    if match.group(1) != tracker.get("projectKey"):
        raise ConfigError(
            "task_project",
            "task",
            "Task project must match the configured Jira projectKey.",
        )
    url = f"{instance}/browse/{key}"
    if candidate != key and candidate != url:
        raise ConfigError(
            "task_instance",
            "task",
            "Task URL must match the configured HTTPS instance and its /browse/KEY path.",
        )
    return {"provider": "jira-mcp", "key": key, "url": url, "subject": f"jira:{url}"}


def check_config(path: Path, task: str | None = None) -> ConfigReport:
    """Return a sanitized local-only report without modifying configuration bytes."""
    report: ConfigReport = {
        "ok": False,
        "config": None,
        "task": None,
        "diagnostics": [],
        "liveChecks": list(LIVE_CHECKS),
    }
    try:
        config = normalize_config(load_config(path))
        identity = resolve_task(config, task) if task is not None else None
    except ConfigError as error:
        report["diagnostics"].append(error.diagnostic)
        return report
    report["ok"] = True
    report["config"] = config
    report["task"] = identity
    report["diagnostics"].append(
        {
            "level": "info",
            "code": "local_only",
            "field": "config",
            "message": "Local config validation passed; live integration checks remain required.",
        }
    )
    return report


def parser() -> argparse.ArgumentParser:
    result = JsonParser(description=__doc__)
    result.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Project autonomous.json to validate without changing it",
    )
    result.add_argument("--task", help="Jira KEY or canonical HTTPS /browse/KEY URL")
    return result


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
    except ConfigError as error:
        report: ConfigReport = {
            "ok": False,
            "config": None,
            "task": None,
            "diagnostics": [error.diagnostic],
            "liveChecks": list(LIVE_CHECKS),
        }
    else:
        report = check_config(args.config, args.task)
    print(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
