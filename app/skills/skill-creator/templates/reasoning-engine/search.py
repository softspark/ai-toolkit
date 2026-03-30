#!/usr/bin/env python3
"""Generic domain reasoning engine for ai-toolkit skills.

Multi-domain search across a categorized knowledge base with anti-pattern filtering.
Python stdlib only, JSON to stdout, zero external deps.

Usage: python3 search.py <query> [--domain <domain>] [--limit <n>]

Threshold rule: Use this pattern when skill has >50 options across >3
compatibility dimensions. Below that threshold, Markdown tables suffice.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load_catalog(assets_dir: Path) -> list[dict]:
    """Load all JSON asset files from the assets directory."""
    items: list[dict] = []
    for f in sorted(assets_dir.glob("*.json")):
        with open(f) as fh:
            data = json.load(fh)
            if isinstance(data, list):
                items.extend(data)
            else:
                items.append(data)
    return items


def match_query(
    items: list[dict], query: str, domain: str | None = None
) -> list[dict]:
    """Score items against query using keyword matching."""
    query_terms = query.lower().split()
    scored: list[dict] = []
    for item in items:
        if domain and item.get("domain", "") != domain:
            continue
        searchable = " ".join(str(v) for v in item.values()).lower()
        score = sum(1 for term in query_terms if term in searchable)
        if score > 0:
            scored.append({**item, "_score": score})
    return sorted(scored, key=lambda x: x["_score"], reverse=True)


def filter_anti_patterns(
    items: list[dict], selected: list[str]
) -> list[dict]:
    """Remove items that conflict with already-selected items."""
    conflicts: set[str] = set()
    for item in items:
        if item.get("id") in selected:
            conflicts.update(item.get("anti_patterns", []))
    return [i for i in items if i.get("id") not in conflicts]


def main() -> None:
    """CLI entrypoint."""
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {"error": "Usage: search.py <query> [--domain D] [--limit N]"}
            )
        )
        sys.exit(1)

    query = sys.argv[1]
    domain: str | None = None
    limit = 10

    args = sys.argv[2:]
    for i, arg in enumerate(args):
        if arg == "--domain" and i + 1 < len(args):
            domain = args[i + 1]
        elif arg == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])

    assets_dir = Path(__file__).parent / "assets"
    if not assets_dir.exists():
        print(
            json.dumps(
                {"error": f"Assets directory not found: {assets_dir}"}
            )
        )
        sys.exit(1)

    catalog = load_catalog(assets_dir)
    results = match_query(catalog, query, domain)
    results = filter_anti_patterns(results, [])[:limit]

    # Remove internal score from output
    for r in results:
        r.pop("_score", None)

    print(
        json.dumps(
            {
                "query": query,
                "domain": domain,
                "results": results,
                "total": len(results),
            }
        )
    )


if __name__ == "__main__":
    main()
