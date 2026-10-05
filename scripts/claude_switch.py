#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Select a Claude Code login by directory without moving credentials."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import claude_usage
from account_profiles import (
    PROFILE_NAME,
    Registry,
    match_project,
    parse_run,
    worktree_origin,
)
from account_status import AccountStatus, print_status
from paths import TOOLKIT_DATA_DIR

SHARED_FILES = (
    "agents", "skills", "rules", "commands", "output-styles",
    "CLAUDE.md", "ARCHITECTURE.md", "settings.json",
)
AUTH_OVERRIDES = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
    "ANTHROPIC_BASE_URL", "ANTHROPIC_PROFILE", "ANTHROPIC_FEDERATION_RULE_ID",
    "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR", "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR",
)


def account_statuses(registry: Registry, selected: str | None) -> list[AccountStatus]:
    accounts: list[AccountStatus] = []
    for name, directory in registry.accounts.items():
        config_dir = Path(directory) if directory else Path.home() / ".claude"
        accounts.append({
            "name": name,
            "selected": name == selected,
            "is_default": name == registry.default,
            "config_dir": str(config_dir),
            "projects": sorted(project for project, owner in registry.projects.items() if owner == name),
            "usage": claude_usage.refresh_usage(directory),
        })
    return accounts


def registry_path() -> Path:
    return Path(os.environ.get("CLAUDE_SWITCH_CONFIG", TOOLKIT_DATA_DIR / "claude-switch.json")).expanduser()


def validate_registry(raw: object) -> Registry:
    if not isinstance(raw, dict) or type(raw.get("version")) is not int or raw["version"] != 1:
        raise ValueError("Invalid registry: expected version 1")
    accounts, projects = raw.get("accounts"), raw.get("projects")
    if not isinstance(accounts, dict) or not accounts or not isinstance(projects, dict):
        raise ValueError("Invalid registry: accounts and projects must be objects")
    directories: set[Path] = set()
    for name, directory in accounts.items():
        if not isinstance(name, str) or not PROFILE_NAME.fullmatch(name):
            raise ValueError("Invalid registry: invalid account name")
        if directory is None and name == "default":
            continue
        if not isinstance(directory, str) or not Path(directory).is_absolute():
            raise ValueError("Invalid registry: account directories must be absolute")
        resolved = Path(directory).resolve()
        if resolved == (Path.home() / ".claude").resolve() or resolved in directories:
            raise ValueError("Invalid registry: account directories must be distinct from each other and ~/.claude")
        directories.add(resolved)
    default = raw.get("default")
    if not isinstance(default, str) or default not in accounts:
        raise ValueError("Invalid registry: unknown default account")
    for directory, name in projects.items():
        if not isinstance(directory, str) or not Path(directory).is_absolute():
            raise ValueError("Invalid registry: project directories must be absolute")
        if not isinstance(name, str) or name not in accounts:
            raise ValueError("Invalid registry: project references unknown account")
    return Registry(default, accounts, projects)


def read_registry(path: Path) -> Registry:
    if not path.exists():
        raise ValueError("No Claude switch configuration. Run: ai-toolkit claude-switch init")
    try:
        return validate_registry(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ValueError("Invalid Claude switch configuration JSON") from error


def save_registry(path: Path, registry: Registry) -> None:
    raw = {"version": 1, "default": registry.default, "accounts": registry.accounts, "projects": registry.projects}
    validate_registry(raw)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Same-directory replace keeps readers from seeing a half-written registry.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(raw, stream, indent=2)
        stream.write("\n")
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def add_account(registry: Registry, name: str, share: bool) -> None:
    if not PROFILE_NAME.fullmatch(name):
        raise ValueError("Account name must use letters, digits, underscores or hyphens (1-64 characters)")
    if name in registry.accounts:
        raise ValueError(f"Account already exists: {name}")
    directory = (TOOLKIT_DATA_DIR / "claude-profiles" / name).absolute()
    if directory.exists() or directory.is_symlink():
        raise ValueError(f"Profile directory already exists; refusing to overwrite: {directory}")
    directory.mkdir(parents=True, mode=0o700)
    if share:
        for item in SHARED_FILES:
            source = Path.home() / ".claude" / item
            if source.exists():
                (directory / item).symlink_to(source, target_is_directory=source.is_dir())
    registry.accounts[name] = str(directory)


def select_account(registry: Registry, override: str | None) -> dict[str, str | None]:
    account, project, source = registry.default, None, "default"
    if override is not None:
        account, source = override, "override"
    else:
        cwd = Path.cwd().resolve()
        match = match_project(registry, cwd)
        if match:
            account, project = match
            source = "project"
        else:
            origin = worktree_origin(cwd)
            match = match_project(registry, origin) if origin else None
            if match:
                account, project = match
                source = "worktree"
    directory = registry.account(account)
    return {"account": account, "config_dir": directory or str(Path.home() / ".claude"),
            "project": project, "source": source}


def warn_auth_overrides(env: dict[str, str]) -> None:
    active = [name for name in AUTH_OVERRIDES if env.get(name)]
    if active:
        print("Warning: authentication/provider overrides may bypass the selected login: "
              + ", ".join(active) + ". Check /status before using Claude.", file=sys.stderr)


def launch(registry: Registry, override: str | None, args: list[str]) -> None:
    selected = select_account(registry, override)
    name = selected["account"]
    assert name is not None
    binary = shutil.which("claude")
    if binary is None:
        raise ValueError("Claude Code executable 'claude' was not found on PATH")
    env = dict(os.environ)
    directory = registry.account(name)
    if directory is None:
        # Explicitly setting ~/.claude can select a different macOS Keychain item.
        env.pop("CLAUDE_CONFIG_DIR", None)
    else:
        if "CLAUDE_SECURESTORAGE_CONFIG_DIR" in env:
            raise ValueError("Unset CLAUDE_SECURESTORAGE_CONFIG_DIR before using a named profile")
        if not Path(directory).is_dir():
            raise ValueError(f"Profile directory is missing: {directory}")
        env["CLAUDE_CONFIG_DIR"] = directory
    warn_auth_overrides(env)
    os.execvpe(binary, [binary, *args], env)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="ai-toolkit claude-switch", description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Register the existing default Claude login")
    add = commands.add_parser("add", help="Create an isolated account profile")
    add.add_argument("name")
    add.add_argument("--share-config", action="store_true", help="Link reusable ~/.claude settings and toolkit assets")
    bind = commands.add_parser("bind", help="Assign a directory and its descendants to an account")
    bind.add_argument("path")
    bind.add_argument("account")
    default = commands.add_parser("default", help="Choose the fallback account")
    default.add_argument("account")
    status = commands.add_parser("status", help="Fetch current limits for all profiles and show routing")
    status.add_argument("--refresh", action="store_true", help="Fetch current limits (default)")
    status.add_argument("--account")
    status.add_argument("--json", action="store_true")
    status.add_argument("--verbose", "-v", action="store_true", help="Show configuration and exact UTC timestamps")
    status.add_argument("--color", choices=("auto", "always", "never"), default="auto", help="Terminal colors (default: auto)")
    login = commands.add_parser("login", help="Run Claude auth login for a profile")
    login.add_argument("account")
    commands.add_parser("run", help="Launch Claude: run [--account NAME] [--] [CLAUDE_ARGS...]")
    return result


def dispatch(options: argparse.Namespace, path: Path, registry: Registry) -> None:
    if options.command == "status":
        selected = select_account(registry, options.account)
        accounts = account_statuses(registry, selected["account"])
        if options.json:
            print(json.dumps({**selected, "account_count": len(accounts), "default_account": registry.default,
                              "accounts": accounts}))
        else:
            print_status(selected, accounts, verbose=options.verbose, color_mode=options.color)
        return
    if options.command == "login":
        launch(registry, options.account, ["auth", "login"])
        return
    if options.command == "add":
        add_account(registry, options.name, options.share_config)
    elif options.command == "bind":
        registry.account(options.account)
        project = Path(options.path).expanduser().resolve()
        if not project.is_dir():
            raise ValueError(f"Project directory does not exist: {project}")
        registry.projects[str(project)] = options.account
    elif options.command == "default":
        registry.account(options.account)
        registry.default = options.account
    save_registry(path, registry)
    print(f"Saved: {path}")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        if args and args[0] == "run":
            override, forwarded = parse_run(args[1:])
            launch(read_registry(registry_path()), override, forwarded)
            return 0
        options = parser().parse_args(args)
        path = registry_path()
        if options.command == "init":
            if path.exists():
                read_registry(path)
                print(f"Already initialized: {path}")
            else:
                save_registry(path, Registry("default", {"default": None}, {}))
                print(f"Initialized: {path}")
            return 0
        dispatch(options, path, read_registry(path))
        return 0
    except (ValueError, OSError) as error:
        print(f"ai-toolkit claude-switch: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
