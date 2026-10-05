# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Show usage and project routing for all configured Claude and Codex accounts."""

from __future__ import annotations

import argparse
import json
from typing import TypedDict

import claude_switch
import codex_switch
from account_status import AccountStatus, print_status


class ProviderStatus(TypedDict):
    state: str
    default_account: str | None
    selected: dict[str, str | None] | None
    accounts: list[AccountStatus]
    error: str | None


def read_provider(name: str, *, refresh: bool) -> ProviderStatus:
    status: ProviderStatus = {
        "state": "not_configured", "default_account": None,
        "selected": None, "accounts": [], "error": None,
    }
    try:
        path = claude_switch.registry_path() if name == "claude" else codex_switch.registry_path()
        try:
            path.stat()
        except FileNotFoundError:
            return status
        if name == "claude":
            registry = claude_switch.read_registry(path)
            selected = claude_switch.select_account(registry, None)
            accounts = claude_switch.account_statuses(registry, selected["account"])
        else:
            registry = codex_switch.read_registry()
            selected = codex_switch.select_account(registry, None)
            accounts = codex_switch.account_statuses(registry, selected["account"], refresh=refresh)
        status.update({"state": "configured", "default_account": registry.default,
                       "selected": selected, "accounts": accounts})
    except (OSError, ValueError):
        status.update({"state": "error", "error": "invalid_configuration"})
    return status


def print_provider(name: str, provider: ProviderStatus, options: argparse.Namespace) -> None:
    title = name.upper() + " ACCOUNTS"
    if provider["state"] == "error":
        print(f"\n  {title}: invalid or unreadable account configuration\n")
        return
    selected = provider["selected"]
    if selected is None:
        return
    print_status(selected, provider["accounts"], verbose=options.verbose,
                 color_mode=options.color, title=title)
    for account in provider["accounts"]:
        error = account["usage"].get("refresh_error")
        if error:
            print(f"  {name}/{account['name']}: refresh failed ({error})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-toolkit llm-status", description=__doc__)
    parser.add_argument("action", nargs="?", choices=("refresh",), help="Fetch current limits for every account (default)")
    parser.add_argument("--refresh", action="store_true", help="Fetch current limits for every account (default)")
    parser.add_argument("--json", action="store_true", help="Output every provider and account as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Include paths, project bindings and timestamps")
    parser.add_argument("--color", choices=("auto", "always", "never"), default="auto")
    options = parser.parse_args(argv)
    providers = {name: read_provider(name, refresh=True) for name in ("claude", "codex")}
    count = sum(len(provider["accounts"]) for provider in providers.values())
    has_error = any(provider["state"] == "error" for provider in providers.values())
    if options.json:
        print(json.dumps({"account_count": count, "providers": providers}))
    else:
        print(f"\n  LLM STATUS · {count} accounts")
        for name, provider in providers.items():
            print_provider(name, provider, options)
        if count == 0 and not has_error:
            print("  No accounts configured. Run: ai-toolkit claude-switch init or ai-toolkit codex-switch init\n")
        elif count:
            print("  Live requests only; failed accounts have no substituted values.\n")
    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
