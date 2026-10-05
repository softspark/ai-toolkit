#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Route Codex CLI to an isolated account home by project directory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import codex_usage
import tomllib
from account_profiles import (
    PROFILE_NAME,
    Registry,
    match_project,
    parse_run,
    worktree_origin,
)
from account_status import AccountStatus, print_status
from paths import TOOLKIT_DATA_DIR

SHARED_FILES = ("config.toml", "AGENTS.md", "AGENTS.override.md", "agents", "skills", "rules",
                "hooks.json", "ai-toolkit-hooks")
AUTH_OVERRIDES = ("CODEX_API_KEY", "CODEX_ACCESS_TOKEN", "OPENAI_API_KEY")
VALUE_FLAGS = {"-c", "--config", "-m", "--model", "-C", "--cd", "-p", "--profile", "-s", "--sandbox",
               "-a", "--ask-for-approval", "--enable", "--disable", "--add-dir", "-i", "--image",
               "--local-provider"}
SHARED_SERVER_COMMANDS = {"agents", "remote-control", "app"}


def registry_path() -> Path:
    return Path(os.environ.get("CODEX_SWITCH_CONFIG", TOOLKIT_DATA_DIR / "codex-switch.json")).expanduser()


def account_home(registry: Registry, name: str) -> Path:
    return Path(registry.account(name) or Path.home() / ".codex").expanduser().resolve()


def validate_registry(raw: object) -> Registry:
    if not isinstance(raw, dict) or type(raw.get("version")) is not int or raw["version"] != 1:
        raise ValueError("Invalid Codex registry version")
    accounts, projects, default = raw.get("accounts"), raw.get("projects"), raw.get("default")
    if not isinstance(accounts, dict) or not accounts or not isinstance(projects, dict):
        raise ValueError("Invalid Codex registry: expected accounts and projects objects")
    homes: set[Path] = set()
    for name, value in accounts.items():
        if not isinstance(name, str) or not PROFILE_NAME.fullmatch(name):
            raise ValueError("Invalid Codex profile name")
        if value is None and name == "default":
            home = (Path.home() / ".codex").resolve()
        elif isinstance(value, str) and Path(value).is_absolute():
            home = Path(value).resolve()
        else:
            raise ValueError("Profile homes must be absolute paths; only default may be null")
        if home in homes or (name != "default" and home == (Path.home() / ".codex").resolve()):
            raise ValueError("Codex profile homes must be distinct, including symlinks")
        homes.add(home)
    if not isinstance(default, str) or default not in accounts:
        raise ValueError("Invalid default Codex profile")
    for directory, name in projects.items():
        if not isinstance(directory, str) or not Path(directory).is_absolute():
            raise ValueError("Project paths must be absolute")
        if not isinstance(name, str) or name not in accounts:
            raise ValueError("Project refers to an unknown Codex profile")
    return Registry(default, accounts, projects)


def read_registry() -> Registry:
    path = registry_path()
    if not path.is_file():
        raise ValueError("No Codex profiles configured. Run: ai-toolkit codex-switch init")
    return validate_registry(json.loads(path.read_text(encoding="utf-8")))


def save_registry(registry: Registry) -> None:
    data = {"version": 1, "default": registry.default, "accounts": registry.accounts, "projects": registry.projects}
    validate_registry(data)
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(data, stream, indent=2)
        stream.write("\n")
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def add_account(registry: Registry, name: str, share: bool) -> None:
    if not PROFILE_NAME.fullmatch(name) or name in registry.accounts:
        raise ValueError("Invalid or already registered profile name")
    home = (TOOLKIT_DATA_DIR / "codex-profiles" / name).absolute()
    if home.exists() or home.is_symlink():
        raise ValueError(f"Refusing to overwrite existing Codex home: {home}")
    home.mkdir(parents=True, mode=0o700)
    if share:
        source_home = account_home(registry, "default")
        for item in SHARED_FILES:
            source = source_home / item
            if source.exists():
                (home / item).symlink_to(source, target_is_directory=source.is_dir())
    registry.accounts[name] = str(home)


def select_account(registry: Registry, override: str | None, cwd: Path | None = None) -> dict[str, str | None]:
    name, project, source = registry.default, None, "default"
    if override is not None:
        name, source = override, "override"
    else:
        directory = (cwd or Path.cwd()).resolve()
        match = match_project(registry, directory)
        if match:
            name, project = match
            source = "project"
        else:
            origin = worktree_origin(directory)
            match = match_project(registry, origin) if origin else None
            if match:
                name, project = match
                source = "worktree"
    return {"account": name, "config_dir": str(account_home(registry, name)), "project": project, "source": source}


def is_state_override(value: str) -> bool:
    try:
        return "sqlite_home" in tomllib.loads(value.split("=", 1)[0] + "=0")
    except tomllib.TOMLDecodeError:
        return False


def launch_options(args: list[str]) -> tuple[Path | None, list[str]]:
    """Inspect native flags without consuming or rewriting any forwarded argument."""
    cwd, command = None, []
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--":
            break
        if token in {"--remote", "--remote-auth-token-env"} or token.startswith(("--remote=", "--remote-auth-token-env=")):
            command.append("remote")
        if token in VALUE_FLAGS and index + 1 < len(args):
            value = args[index + 1]
            if token in {"-C", "--cd"}:
                cwd = Path(value).expanduser().resolve()
            if token in {"-c", "--config"} and is_state_override(value):
                command.append("shared-state")
            index += 2
            continue
        if token.startswith("--cd="):
            cwd = Path(token.split("=", 1)[1]).expanduser().resolve()
        elif (token.startswith("--config=") and is_state_override(token.split("=", 1)[1])) or (
            token.startswith("-c") and len(token) > 2 and is_state_override(token[2:].removeprefix("="))
        ):
            command.append("shared-state")
        elif token.startswith("-C") and len(token) > 2:
            cwd = Path(token[2:].removeprefix("=")).expanduser().resolve()
        elif not token.startswith("-") and not command:
            command.append(token)
        index += 1
    return cwd, command


def launch(registry: Registry, override: str | None, args: list[str]) -> None:
    cwd, command = launch_options(args)
    selected = select_account(registry, override, cwd)
    name = selected["account"]
    assert name is not None
    home = account_home(registry, name)
    env = dict(os.environ)
    binary = shutil.which("codex")
    if binary is None:
        raise ValueError("Codex CLI executable 'codex' was not found on PATH")
    isolated = name != "default"
    if isolated:
        if not home.is_dir():
            raise ValueError(f"Codex home is missing: {home}")
        if set(command) & (SHARED_SERVER_COMMANDS | {"remote", "shared-state", "app-server"}):
            raise ValueError("Remote/shared-server or shared-state options cannot guarantee the selected profile")
        overrides = [key for key in AUTH_OVERRIDES if env.get(key)]
        if overrides:
            raise ValueError("Unset authentication overrides before using a named profile: " + ", ".join(overrides))
        env["CODEX_HOME"] = str(home)
        env.pop("CODEX_SQLITE_HOME", None)
        args = ["--no-daemon", "-c", "sqlite_home=" + json.dumps(str(home)), *args]
    elif registry.account(name) is None:
        env.pop("CODEX_HOME", None)
    else:
        env["CODEX_HOME"] = str(home)
    os.execvpe(binary, [binary, *args], env)


def account_statuses(registry: Registry, selected: str | None, *, refresh: bool = False) -> list[AccountStatus]:
    accounts: list[AccountStatus] = []
    for name in registry.accounts:
        home = account_home(registry, name)
        usage = codex_usage.refresh_usage(home)
        accounts.append({"name": name, "selected": name == selected, "is_default": name == registry.default,
                         "config_dir": str(home), "projects": sorted(p for p, a in registry.projects.items() if a == name),
                         "usage": usage})
    return accounts


def show_status(registry: Registry, options: argparse.Namespace) -> None:
    selected = select_account(registry, options.account)
    accounts = account_statuses(registry, selected["account"], refresh=options.refresh)
    if options.json:
        print(json.dumps({**selected, "account_count": len(accounts), "default_account": registry.default,
                          "accounts": accounts}))
    else:
        print_status(selected, accounts, verbose=options.verbose, color_mode=options.color, title="CODEX ACCOUNTS")
        for account in accounts:
            if account["usage"].get("refresh_error"):
                print(f"  {account['name']}: refresh failed ({account['usage']['refresh_error']})")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="ai-toolkit codex-switch", description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Keep the existing Codex home as the default profile")
    add = sub.add_parser("add", help="Create an isolated Codex account home")
    add.add_argument("name")
    add.add_argument("--share-config", action="store_true")
    bind = sub.add_parser("bind")
    bind.add_argument("path")
    bind.add_argument("account")
    default = sub.add_parser("default")
    default.add_argument("account")
    login = sub.add_parser("login")
    login.add_argument("account")
    status = sub.add_parser("status")
    status.add_argument("--account")
    status.add_argument("--json", action="store_true")
    status.add_argument("--verbose", "-v", action="store_true")
    status.add_argument("--color", choices=("auto", "always", "never"), default="auto")
    status.add_argument("--refresh", action="store_true", help="Compatibility alias; status always reads live limits")
    sub.add_parser("run", help="run [--account NAME] [--] CODEX_ARGS...")
    return result


def dispatch(options: argparse.Namespace, registry: Registry) -> None:
    if options.command == "status":
        show_status(registry, options)
        return
    if options.command == "login":
        launch(registry, options.account, ["login"])
        return
    if options.command == "add":
        add_account(registry, options.name, options.share_config)
    elif options.command == "bind":
        registry.account(options.account)
        path = Path(options.path).expanduser().resolve()
        if not path.is_dir():
            raise ValueError("Project directory does not exist")
        registry.projects[str(path)] = options.account
    elif options.command == "default":
        registry.account(options.account)
        registry.default = options.account
    save_registry(registry)
    print(f"Saved: {registry_path()}")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        if args and args[0] == "run":
            override, forwarded = parse_run(args[1:])
            launch(read_registry(), override, forwarded)
            return 0
        options = parser().parse_args(args)
        if options.command == "init":
            if registry_path().exists():
                read_registry()
            else:
                configured = os.environ.get("CODEX_HOME")
                home = Path(configured).expanduser() if configured else None
                if home is not None and (not home.is_absolute() or not home.is_dir()):
                    raise ValueError("Existing CODEX_HOME must be an absolute directory")
                save_registry(Registry("default", {"default": str(home.resolve()) if home else None}, {}))
            print(f"Initialized: {registry_path()}")
            return 0
        dispatch(options, read_registry())
        return 0
    except (ValueError, OSError) as error:
        print(f"ai-toolkit codex-switch: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
