#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Survey a transcript corpus and print aggregate figures as JSON.

Usage:
    python3 -m token_usage.survey [PROJECTS_ROOT]     (run from benchmarks/)

PROJECTS_ROOT defaults to ~/.claude/projects. Output is aggregates only: no
session ids, paths, commands or message text. Sessions are labelled S1..Sn by
descending context-token volume, so the labels carry no identity.

This exists so that the corpus numbers quoted in a plan or a KB document come
from a committed script. The July measurement quoted numbers from a harness
that was never committed, and nothing it said can now be re-derived.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .transcript import Session, Transcript, discover_sessions, load_session


def _transcripts(session: Session) -> list[Transcript]:
    return [session.main, *session.subagents]


def _share(part: int, whole: int) -> float:
    return round(part / whole, 4) if whole else 0.0


def survey(projects_root: Path) -> dict[str, Any]:
    sessions = [load_session(path) for path in discover_sessions(projects_root)]
    transcripts = [t for s in sessions for t in _transcripts(s)]

    requests = [r for t in transcripts for r in t.requests]
    text_by_tool: Counter[str] = Counter()
    images = image_bytes = persisted = references = errors = 0
    for t in transcripts:
        for result in t.tool_results:
            text_by_tool[result.tool_name or "<unlinked>"] += result.text_bytes
            images += result.image_count
            image_bytes += result.image_bytes
            persisted += int(result.persisted)
            references += result.tool_reference_count
            errors += int(result.is_error)
    text_total = sum(text_by_tool.values())

    per_session = sorted(
        (sum(r.context_tokens for t in _transcripts(s) for r in t.requests) for s in sessions),
        reverse=True,
    )
    context_total = sum(per_session)
    compactions = [c for t in transcripts for c in t.compactions]

    return {
        "corpus": {
            "sessions": len(sessions),
            "subagent_transcripts": sum(len(s.subagents) for s in sessions),
            "lines": sum(t.stats.lines for t in transcripts),
            "malformed_lines": sum(t.stats.malformed for t in transcripts),
            "duplicate_uuid_records": sum(t.stats.duplicate_uuids for t in transcripts),
        },
        "requests": {
            "assistant_lines": sum(t.stats.assistant_lines for t in transcripts),
            "synthetic_lines": sum(t.stats.synthetic for t in transcripts),
            "distinct_requests": len(requests),
            "lines_per_request": round(
                (sum(t.stats.assistant_lines - t.stats.synthetic for t in transcripts) / len(requests))
                if requests else 0.0, 3),
            "multi_iteration_requests": sum(t.stats.multi_iteration for t in transcripts),
            "model_switches": sum(t.model_switches for t in transcripts),
            "by_model": dict(Counter(r.model for r in requests).most_common()),
        },
        "tool_results": {
            "count": sum(len(t.tool_results) for t in transcripts),
            "text_bytes": text_total,
            "text_share_by_tool": {
                name: _share(size, text_total) for name, size in text_by_tool.most_common(12)
            },
            "image_items": images,
            "image_base64_bytes": image_bytes,
            "persisted_previews": persisted,
            "tool_reference_items": references,
            "errors": errors,
        },
        "context": {
            "sum_context_tokens": context_total,
            "per_session_share": {f"S{i + 1}": _share(v, context_total) for i, v in enumerate(per_session)},
            "top1_share": _share(sum(per_session[:1]), context_total),
            "top3_share": _share(sum(per_session[:3]), context_total),
        },
        "compactions": {
            "count": len(compactions),
            "by_trigger": dict(Counter(c.trigger for c in compactions)),
            "pre_tokens": sorted(c.pre_tokens for c in compactions),
            "post_tokens": sorted(c.post_tokens for c in compactions),
        },
    }


def main(argv: list[str]) -> int:
    root = Path(argv[1]).expanduser() if len(argv) > 1 else Path.home() / ".claude" / "projects"
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    json.dump(survey(root), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
