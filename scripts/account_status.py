# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Terminal presentation for isolated AI account profiles."""

from __future__ import annotations

import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


class AccountStatus(TypedDict):
    name: str
    selected: bool
    is_default: bool
    config_dir: str
    projects: list[str]
    usage: dict[str, object]


def format_timestamp(value: object) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "unknown"
    try:
        return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, OverflowError, OSError):
        return "unknown"


def usage_window(usage: dict[str, object], name: str) -> tuple[str, str]:
    windows = usage.get("windows")
    window = windows.get(name) if isinstance(windows, dict) else None
    if not isinstance(window, dict):
        return "unknown", "unknown"
    percentage, state = window.get("used_percentage"), window.get("state")
    used = f"{percentage:g}% ({state})" if isinstance(percentage, (int, float)) else "unknown"
    return used, format_timestamp(window.get("resets_at"))


def paint(text: str, style: str, color: bool) -> str:
    codes = {"title": "1;36", "active": "1", "dim": "2", "good": "32", "warn": "33", "high": "31"}
    return f"\033[{codes[style]}m{text}\033[0m" if color else text


def duration(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "no data"
    seconds = max(0, int(value))
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    return f"{hours}h {minutes % 60}m" if hours < 24 else f"{hours // 24}d {hours % 24}h"


def progress_bar(percentage: float) -> str:
    # Ten cells with eighth-cell steps keep small percentages visible.
    steps = min(80, max(0, round(percentage * 0.8)))
    full, fraction = divmod(steps, 8)
    partial = "▏▎▍▌▋▊▉"[fraction - 1] if fraction else ""
    return "█" * full + partial + "░" * (10 - full - bool(partial))


def window_cell(usage: dict[str, object], name: str, color: bool) -> tuple[str, str]:
    windows = usage.get("windows")
    window = windows.get(name) if isinstance(windows, dict) else None
    if not isinstance(window, dict):
        return paint("not provided".ljust(20), "dim", color), ""
    percentage = window.get("used_percentage")
    if not isinstance(percentage, (int, float)):
        return paint("no data".ljust(20), "dim", color), ""
    label = f"{progress_bar(percentage)} {percentage:g}%"
    style = "warn" if percentage >= 70 else "good"
    if percentage >= 90:
        style = "high"
    reset = window.get("resets_at")
    remaining = duration(reset - time.time()) if isinstance(reset, (int, float)) else "?"
    return paint(label.ljust(20), style, color), f"reset in {remaining}"


def short_path(value: str) -> str:
    path = Path(value)
    try:
        return str(Path("~") / path.relative_to(Path.home()))
    except ValueError:
        return value


def print_account_row(account: AccountStatus, width: int, color: bool) -> None:
    name = ("› " if account["selected"] else "  ") + account["name"] + (" *" if account["is_default"] else "")
    usage = account["usage"]
    if not usage.get("windows"):
        label = "Unavailable: " + str(usage.get("refresh_error", "usage_unavailable"))
        name = name if len(name) <= 22 else name[:21] + "…"
        if width < 86:
            print("  " + paint(name, "active", color))
            print(paint(f"    {label}\n", "dim", color))
        else:
            print("  " + paint(name.ljust(22), "active", color) + "  " + paint(label + "\n", "dim", color))
        return
    updated = "live"
    five, reset_five = window_cell(usage, "five_hour", color)
    week, reset_week = window_cell(usage, "seven_day", color)
    if width < 86:
        print("  " + paint(name, "active" if account["selected"] else "dim", color))
        print(f"    5h  {five}  {reset_five}")
        print(f"    7d  {week}  {reset_week}")
        print(paint(f"    Updated: {updated}\n", "dim", color))
        return
    name = name if len(name) <= 22 else name[:21] + "…"
    print("  " + paint(name.ljust(22), "active" if account["selected"] else "dim", color)
          + f"  {five}  {week}  " + paint(updated, "dim", color))
    if reset_five or reset_week:
        print(paint(f"  {'':22}  {reset_five:20}  {reset_week}", "dim", color))
    print()


def print_status(selected: dict[str, str | None], accounts: list[AccountStatus],
                 *, verbose: bool = False, color_mode: str = "auto",
                 title: str = "CLAUDE ACCOUNTS") -> None:
    color = "NO_COLOR" not in os.environ and (color_mode == "always" or (
        color_mode == "auto" and sys.stdout.isatty() and os.environ.get("TERM") != "dumb"))
    width = shutil.get_terminal_size(fallback=(100, 24)).columns
    print("\n  " + paint(title, "title", color) + paint(f"   {len(accounts)} profiles", "dim", color))
    print(f"  Active: {selected['account']}" + paint(f" · {selected['source']} routing\n", "dim", color))
    if width >= 86:
        print(paint(f"  {'PROFILE':22}  {'5h LIMIT':20}  {'7d LIMIT':20}  UPDATED", "dim", color))
        print(paint("  " + "─" * 76, "dim", color))
    for account in accounts:
        print_account_row(account, width, color)
    print(paint("  › active  * default  · live usage", "dim", color))
    if verbose:
        print_status_details(selected, accounts)
    else:
        print(paint("  Configuration and exact timestamps: --verbose", "dim", color))
    print()


def print_status_details(selected: dict[str, str | None], accounts: list[AccountStatus]) -> None:
    print(f"\n  Selected project: {short_path(selected['project']) if selected['project'] else '(none)'}")
    for account in accounts:
        usage = account["usage"]
        print(f"\n  {account['name']}")
        print(f"    Config:   {short_path(account['config_dir'])}")
        print(f"    Projects: {', '.join(short_path(path) for path in account['projects']) or '(none)'}")
        print(f"    Observed: {format_timestamp(usage.get('observed_at'))} ({usage.get('state')})")
        for name, label in (("five_hour", "5h"), ("seven_day", "7d")):
            used, reset = usage_window(usage, name)
            print(f"    {label}: {used}; resets {reset}")
