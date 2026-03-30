#!/usr/bin/env python3
"""benchmark-ecosystem — Generate ecosystem benchmark snapshot.

Usage:
    benchmark_ecosystem.py [--offline] [--json|--dashboard-json|--markdown] [--out FILE]
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

SNAPSHOT_DATE = "2026-03-28"
STALE_THRESHOLD_DAYS = 30

SNAPSHOT_DATA = [
    {
        "repo": "anthropics/claude-code",
        "category": "official",
        "stars": 83535,
        "updated_at": "2026-03-27T16:50:16Z",
        "commands_md": 18,
        "agents_md": 15,
        "skills": 10,
        "hook_settings_files": 5,
        "notes": "Official Claude Code repo with plugin layout, development kits, and modular commands/agents/hooks.",
    },
    {
        "repo": "affaan-m/everything-claude-code",
        "category": "ecosystem-scale",
        "stars": 111863,
        "updated_at": "2026-03-27T16:55:18Z",
        "commands_md": 271,
        "agents_md": 152,
        "skills": 397,
        "hook_settings_files": 2,
        "notes": "Large ecosystem catalog. High inspiration value, high discoverability-debt risk.",
    },
    {
        "repo": "ChrisWiles/claude-code-showcase",
        "category": "practical-showcase",
        "stars": 5593,
        "updated_at": "2026-03-27T13:13:35Z",
        "commands_md": 6,
        "agents_md": 2,
        "skills": 6,
        "hook_settings_files": 1,
        "notes": "Practical edit-time hooks, branch safety, formatting, and testing patterns.",
    },
    {
        "repo": "disler/claude-code-hooks-mastery",
        "category": "hooks-reference",
        "stars": 3421,
        "updated_at": "2026-03-27T15:49:11Z",
        "commands_md": 21,
        "agents_md": 19,
        "skills": 0,
        "hook_settings_files": 1,
        "notes": "Strong reference for lifecycle breadth, status lines, and operational hook patterns.",
    },
    {
        "repo": "codeaholicguy/ai-devkit",
        "category": "cross-tool",
        "stars": 985,
        "updated_at": "2026-03-27T00:00:00Z",
        "commands_md": 0,
        "agents_md": 0,
        "skills": 0,
        "hook_settings_files": 0,
        "notes": "Cross-tool toolkit positioning benchmark.",
    },
    {
        "repo": "alirezarezvani/claude-code-skill-factory",
        "category": "meta-tooling",
        "stars": 638,
        "updated_at": "2026-03-27T00:00:00Z",
        "commands_md": 0,
        "agents_md": 0,
        "skills": 0,
        "hook_settings_files": 0,
        "notes": "Skill/agent/prompt factory inspiration for creator workflows.",
    },
]

COMPARISON_MATRIX = [
    {
        "pattern": "plugin-manifest-support",
        "current_state": "implemented",
        "benchmark_signal": "official Claude Code plugin layout",
        "priority": "high",
        "evidence": ["anthropics/claude-code"],
    },
    {
        "pattern": "creator-workflows",
        "current_state": "implemented",
        "benchmark_signal": "meta-tooling for commands, hooks, agents, plugins",
        "priority": "high",
        "evidence": ["anthropics/claude-code", "alirezarezvani/claude-code-skill-factory"],
    },
    {
        "pattern": "lifecycle-breadth",
        "current_state": "implemented",
        "benchmark_signal": "prompt governance, post-tool feedback, subagent hooks, session end",
        "priority": "high",
        "evidence": ["disler/claude-code-hooks-mastery", "ChrisWiles/claude-code-showcase"],
    },
    {
        "pattern": "plugin-packs",
        "current_state": "implemented-experimental",
        "benchmark_signal": "modular domain packaging",
        "priority": "medium",
        "evidence": ["anthropics/claude-code", "affaan-m/everything-claude-code"],
    },
    {
        "pattern": "benchmark-harvesting",
        "current_state": "implemented",
        "benchmark_signal": "repeatable evidence for docs and roadmap decisions",
        "priority": "medium",
        "evidence": ["anthropics/claude-code", "codeaholicguy/ai-devkit"],
    },
]


def refresh_online(snapshot: list[dict]) -> list[dict]:
    """Try to refresh star counts from GitHub API."""
    import copy
    rows = copy.deepcopy(snapshot)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-toolkit-benchmark-script",
    }
    for item in rows:
        repo = item["repo"]
        url = f"https://api.github.com/repos/{repo}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.load(response)
            item["stars"] = data.get("stargazers_count", item["stars"])
            item["updated_at"] = data.get("updated_at", item["updated_at"])
            item["source"] = "github-api"
            if data.get("description"):
                item["description"] = data["description"]
        except Exception:
            item["source"] = "snapshot"
    return rows


def annotate_snapshot(snapshot: list[dict]) -> list[dict]:
    """Add source annotation to snapshot data."""
    import copy
    rows = copy.deepcopy(snapshot)
    for row in rows:
        row.setdefault("source", "snapshot")
    return rows


def render_dashboard(rows: list[dict], mode: str) -> dict:
    """Build dashboard JSON."""
    snapshot_date = date.fromisoformat(SNAPSHOT_DATE)
    today = datetime.now(timezone.utc).date()
    age_days = (today - snapshot_date).days

    def status_for_age(days: int, stale_days: int) -> str:
        if days <= max(7, stale_days // 3):
            return "fresh"
        if days <= stale_days:
            return "aging"
        return "stale"

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "mode": mode,
        "snapshot_date": str(snapshot_date),
        "freshness": {
            "stale_threshold_days": STALE_THRESHOLD_DAYS,
            "age_days": age_days,
            "status": status_for_age(age_days, STALE_THRESHOLD_DAYS),
        },
        "summary": {
            "repo_count": len(rows),
            "stars_total": sum(int(r.get("stars", 0)) for r in rows),
            "categories": sorted({r.get("category", "unknown") for r in rows}),
            "official_repo": "anthropics/claude-code",
        },
        "comparison_matrix": COMPARISON_MATRIX,
        "repos": rows,
    }


def render_markdown(dashboard: dict) -> str:
    """Render dashboard as Markdown."""
    lines: list[str] = []
    data = dashboard
    rows = data["repos"]

    lines.append("# Claude Ecosystem Benchmark Snapshot")
    lines.append("")
    lines.append("Generated by `scripts/benchmark-ecosystem.sh`.")
    lines.append("")
    lines.append(f"- Snapshot date: `{data['snapshot_date']}`")
    f = data["freshness"]
    lines.append(f"- Freshness: `{f['status']}` ({f['age_days']} day(s) old, threshold {f['stale_threshold_days']} days)")
    lines.append(f"- Mode: `{data['mode']}`")
    lines.append("")
    lines.append("| Repository | Category | Stars | Commands | Agents | Skills | Hook/Settings Files |")
    lines.append("|------------|----------|-------|----------|--------|--------|---------------------|")
    for row in rows:
        lines.append(f"| `{row['repo']}` | {row['category']} | {row['stars']} | {row['commands_md']} | {row['agents_md']} | {row['skills']} | {row['hook_settings_files']} |")
    lines.append("")
    lines.append("## Comparison Matrix")
    lines.append("")
    lines.append("| Pattern | Current State | Benchmark Signal | Priority |")
    lines.append("|---------|---------------|------------------|----------|")
    for row in data["comparison_matrix"]:
        lines.append(f"| `{row['pattern']}` | {row['current_state']} | {row['benchmark_signal']} | {row['priority']} |")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for row in rows:
        lines.append(f"- **`{row['repo']}`** — {row['notes']}")

    return "\n".join(lines)


def main() -> None:
    fmt = "markdown"
    outfile = ""
    offline = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--offline":
            offline = True
        elif a == "--json":
            fmt = "json"
        elif a == "--dashboard-json":
            fmt = "dashboard-json"
        elif a == "--markdown":
            fmt = "markdown"
        elif a == "--format":
            i += 1
            fmt = args[i] if i < len(args) else "markdown"
        elif a == "--out":
            i += 1
            outfile = args[i] if i < len(args) else ""
        elif a in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        else:
            print(f"Unknown option: {a}", file=sys.stderr)
            sys.exit(1)
        i += 1

    mode = "offline"
    if offline:
        data = annotate_snapshot(SNAPSHOT_DATA)
    else:
        mode = "online"
        try:
            data = refresh_online(SNAPSHOT_DATA)
        except Exception:
            data = annotate_snapshot(SNAPSHOT_DATA)
            mode = "offline"

    dashboard = render_dashboard(data, mode)

    if fmt == "json":
        output = json.dumps(data, indent=2)
    elif fmt == "dashboard-json":
        output = json.dumps(dashboard, indent=2)
    else:
        output = render_markdown(dashboard)

    if outfile:
        Path(outfile).parent.mkdir(parents=True, exist_ok=True)
        Path(outfile).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
