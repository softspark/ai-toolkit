#!/usr/bin/env python3
"""ai-toolkit stats -- Show skill usage statistics.

Reads ~/.softspark/ai-toolkit/stats.json (populated by track-usage.sh hook)
and displays a sorted table of skill invocations.

Options:
  --reset     Clear all stats
  --json      Output raw JSON
  --summary   Output product telemetry summary
"""
from __future__ import annotations

from datetime import datetime, timedelta
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import STATS_FILE as _STATS_FILE

STATS_FILE = _STATS_FILE
TOOLKIT_DIR = Path(__file__).resolve().parent.parent


def _load_stats() -> dict:
    """Load the stats file, returning an empty dict when absent."""
    if not STATS_FILE.is_file():
        return {}
    with open(STATS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _aggregate_rows(data: dict) -> list[tuple[str, dict]]:
    """Normalize supported stats formats into sorted (name, info) rows."""
    if not data:
        return []

    # Handle both formats: {skill: {count, last_used}} and {loop_runs: [...]}
    if "loop_runs" in data:
        agg: dict[str, dict] = {}
        for run in data.get("loop_runs", []):
            cmd = run.get("command", "unknown")
            iters = run.get("iterations", [])
            if cmd not in agg:
                agg[cmd] = {"count": 0, "last_used": "unknown"}
            agg[cmd]["count"] += len(iters) if iters else 1
            started = run.get("started_at", "")
            if started > agg[cmd]["last_used"]:
                agg[cmd]["last_used"] = started
        return sorted(agg.items(), key=lambda x: x[1].get("count", 0), reverse=True)

    skill_data = {k: v for k, v in data.items() if isinstance(v, dict)}
    return sorted(skill_data.items(), key=lambda x: x[1].get("count", 0), reverse=True)


def _catalog_skill_names() -> set[str]:
    """Return skill directory names from the installed toolkit catalog."""
    skills_dir = TOOLKIT_DIR / "app" / "skills"
    if not skills_dir.is_dir():
        return set()
    return {
        p.name
        for p in skills_dir.iterdir()
        if p.is_dir() and not p.name.startswith("_") and (p / "SKILL.md").is_file()
    }


def _parse_datetime(value: str) -> datetime | None:
    """Parse stats timestamps emitted by toolkit hooks and loop runs."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value[:19] + ("Z" if fmt.endswith("Z") else ""), fmt)
        except ValueError:
            continue
    return None


def _build_summary(rows: list[tuple[str, dict]]) -> dict:
    """Build machine-readable product telemetry from aggregated rows."""
    catalog = _catalog_skill_names()
    used_names = {name for name, _ in rows}
    used_catalog = used_names & catalog if catalog else used_names
    total = sum(int(info.get("count", 0) or 0) for _, info in rows)

    cutoff = datetime.now() - timedelta(days=7)
    active_7d = 0
    for _, info in rows:
        last_used = _parse_datetime(str(info.get("last_used", "")))
        if last_used and last_used >= cutoff:
            active_7d += 1

    catalog_total = len(catalog)
    unused = max(catalog_total - len(used_catalog), 0) if catalog_total else 0

    return {
        "totalInvocations": total,
        "uniqueSkillsUsed": len(used_names),
        "catalogSkillsTotal": catalog_total,
        "unusedCatalogSkills": unused,
        "catalogCoveragePct": round((len(used_catalog) / catalog_total) * 100, 1) if catalog_total else 0,
        "activeSkills7d": active_7d,
        "topSkills": [
            {
                "name": name,
                "count": int(info.get("count", 0) or 0),
                "lastUsed": info.get("last_used", "unknown"),
            }
            for name, info in rows[:5]
        ],
    }


def _print_summary(summary: dict) -> None:
    """Print a compact human-readable product telemetry summary."""
    print("Product Telemetry")
    print("=================")
    print(f"Total invocations: {summary['totalInvocations']}")
    print(f"Unique skills used: {summary['uniqueSkillsUsed']}")
    print(f"Catalog skills total: {summary['catalogSkillsTotal']}")
    print(f"Unused catalog skills: {summary['unusedCatalogSkills']}")
    print(f"Catalog coverage: {summary['catalogCoveragePct']}%")
    print(f"Active skills in last 7 days: {summary['activeSkills7d']}")
    if summary["topSkills"]:
        print()
        print("Top skills:")
        for item in summary["topSkills"]:
            print(f"- {item['name']}: {item['count']} ({item['lastUsed']})")


def main() -> None:
    """Display, export, or reset usage statistics."""
    args = set(sys.argv[1:])

    # --reset
    if "--reset" in args:
        if STATS_FILE.is_file():
            STATS_FILE.unlink()
            print("Stats reset.")
        else:
            print("No stats file found.")
        return

    data = _load_stats()
    rows = _aggregate_rows(data)

    if "--summary" in args:
        summary = _build_summary(rows)
        if "--json" in args:
            print(json.dumps(summary, indent=2))
        else:
            _print_summary(summary)
        return

    # --json
    if "--json" in args:
        print(STATS_FILE.read_text(encoding="utf-8") if STATS_FILE.is_file() else "{}")
        return

    # Default: pretty-print table
    if not STATS_FILE.is_file():
        print("No usage stats recorded yet.")
        print("Stats are collected when skills are invoked via slash commands.")
        print()
        print(f"File: {STATS_FILE}")
        return

    print("AI Toolkit Usage Stats")
    print("========================")
    print()

    if not rows:
        print("No invocations recorded.")
        return

    print(f"{'Skill':<30} {'Count':>6}  {'Last Used':<20}")
    print("-" * 60)
    for name, info in rows:
        count = info.get("count", 0)
        last = info.get("last_used", "unknown")
        print(f"{name:<30} {count:>6}  {last:<20}")

    total = sum(v.get("count", 0) for _, v in rows)
    print()
    print(f"Total invocations: {total}")
    print(f"Unique skills: {len(rows)}")
    print()
    print(f"File: {STATS_FILE}")
    print("Reset: ai-toolkit stats --reset")


if __name__ == "__main__":
    main()
