#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Decompose a transcript corpus: what each category costs the context window.

Usage (from benchmarks/):
    python3 -m token_usage.decompose [PROJECTS_ROOT] [--out FILE]

Prints aggregates as JSON (or writes them to FILE, which must lie outside this
repository). Nothing identifies a session, a path, a command or a message.

For each category the report gives its **ceiling**: the reduction in total
context tokens (sum over requests of input + cache writes + cache reads) if every
token that category put into the context had never entered it, simulated forward
with compactions at their thresholds under both threshold bounds. No mechanism
acting on that category can do better than its ceiling.

It also rebuilds the July headline under that method's definitions, one change
at a time, so the effect of each defect is a number rather than an argument. The
July harness was never committed; the definitions are reconstructed from its KB
documents and labelled as such.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from .attribute import Fit, Item, Window, evaluate, fit, in_holdout, isolated, windows
from .simulate import Bound, simulate, steps
from .transcript import Session, Transcript, discover_sessions, load_session, refuse_repo_path

TOOL_CATEGORIES = ("bash", "rag-mcp", "read", "browser", "edit", "other-tool")
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20260916

# USD per million tokens: input, 5m cache write, 1h cache write, cache read, output.
# Read from https://platform.claude.com/docs/en/about-claude/pricing on 2026-09-16.
# Used only as relative weights for the K2 threshold: subscription limits are not
# published per token, and API list price is the stated proxy. A model missing
# from the table is reported, never priced by guess.
PRICES: dict[str, tuple[float, float, float, float, float]] = {
    "claude-opus-5": (5.0, 6.25, 10.0, 0.50, 25.0),
    "claude-opus-4-8": (5.0, 6.25, 10.0, 0.50, 25.0),
    "claude-fable-5-1": (10.0, 12.50, 20.0, 0.25, 50.0),
}

Selector = Callable[[Item], float]  # fraction of the item's tokens removed, 0..1


def _transcripts(session: Session) -> list[Transcript]:
    return [session.main, *session.subagents]


def removals(transcript: Transcript, model: Fit, select: Selector) -> list[float]:
    """Tokens removed per step; step i is the window between request i and i+1."""
    return [
        sum(model.rate_for(item.category) * item.text_bytes * select(item) for item in window.items)
        for window in windows(transcript)
    ]


@dataclass(frozen=True, slots=True)
class SessionOutcome:
    observed: float
    counterfactual: float
    compactions_observed: int
    compactions_counterfactual: int
    auto_delay_requests: int = 0  # summed over auto compactions that fire in both paths
    auto_avoided: int = 0  # observed auto compactions the counterfactual never reaches
    earliest_shift: int = 0  # most negative (earliest) shift of any auto compaction; 0 if none moved earlier
    requests: int = 0


def outcome(session: Session, model: Fit, select: Selector, bound: Bound) -> SessionOutcome:
    observed = counterfactual = 0.0
    compact_obs = compact_cf = delay = avoided = earliest = requests = 0
    for transcript in _transcripts(session):
        if not transcript.requests:
            continue
        start, path = steps(transcript)
        base = simulate(start, path, [0.0] * len(path), bound=bound)
        cf = simulate(start, path, removals(transcript, model, select), bound=bound)
        observed += base.total
        counterfactual += cf.total
        requests += len(transcript.requests)
        compact_obs += base.auto_compactions + base.manual_compactions
        compact_cf += cf.auto_compactions + cf.manual_compactions
        shifts = [c - o for o, c in zip(base.auto_fire_steps, cf.auto_fire_steps)]
        delay += sum(shifts)
        earliest = min([earliest, *shifts])
        avoided += max(0, base.auto_compactions - cf.auto_compactions)
    return SessionOutcome(observed, counterfactual, compact_obs, compact_cf, delay, avoided, earliest, requests)


def reduction(outcomes: Sequence[SessionOutcome]) -> float:
    observed = sum(o.observed for o in outcomes)
    return 1.0 - sum(o.counterfactual for o in outcomes) / observed if observed else 0.0


def bootstrap_interval(outcomes: Sequence[SessionOutcome], *, level: float = 0.90) -> tuple[float, float]:
    """Percentile interval of the pooled reduction, resampling whole sessions."""
    rng = random.Random(BOOTSTRAP_SEED)
    stats = sorted(
        reduction([outcomes[rng.randrange(len(outcomes))] for _ in outcomes])
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    tail = (1.0 - level) / 2
    return stats[int(tail * len(stats))], stats[min(len(stats) - 1, int((1.0 - tail) * len(stats)))]


def without_largest(outcomes: Sequence[SessionOutcome], count: int = 3) -> list[float]:
    """The reduction recomputed with each of the ``count`` largest sessions left out in turn."""
    ranked = sorted(range(len(outcomes)), key=lambda i: outcomes[i].observed, reverse=True)[:count]
    return [reduction([o for j, o in enumerate(outcomes) if j != i]) for i in ranked]


def ceiling_report(sessions: Sequence[Session], model: Fit, select: Selector) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for bound in ("lower", "upper"):
        outcomes = [outcome(s, model, select, bound) for s in sessions]
        low, high = bootstrap_interval(outcomes)
        compacting = [o for o in outcomes if o.compactions_observed]
        report[bound] = {
            "reduction": round(reduction(outcomes), 5),
            "ci90": [round(low, 5), round(high, 5)],
            "without_each_top3": [round(r, 5) for r in without_largest(outcomes)],
            "reduction_sessions_without_compaction": round(
                reduction([o for o in outcomes if not o.compactions_observed]), 5),
            "reduction_sessions_with_compaction": round(reduction(compacting), 5),
            "compactions_observed_vs_counterfactual": [sum(o.compactions_observed for o in outcomes),
                                                       sum(o.compactions_counterfactual for o in outcomes)],
            "auto_compaction_delay_requests": sum(o.auto_delay_requests for o in outcomes),
            "auto_compactions_avoided": sum(o.auto_avoided for o in outcomes),
        }
    return report


def category_selector(categories: Sequence[str]) -> Selector:
    wanted = frozenset(categories)
    return lambda item: 1.0 if item.kind == "tool_result" and item.category in wanted else 0.0


def usage_categories(sessions: Sequence[Session], model: Fit, select: Selector) -> dict[str, Any]:
    """Relative reduction per usage category per model, under the lower threshold bound.

    Cache writes shrink by what is removed on entry; cache reads follow the
    simulated context. Where the counterfactual compacts at a different request
    than observed, the cache rewrite of the summary moves with it; that shift is
    not modelled, and is a few summary-sized writes against billions of reads.
    """
    observed: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    counterfactual: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for session in sessions:
        for transcript in _transcripts(session):
            if not transcript.requests:
                continue
            start, path = steps(transcript)
            cut = removals(transcript, model, select)
            cf = simulate(start, path, cut, bound="lower")
            for i, request in enumerate(transcript.requests):
                entered = cut[i - 1] if i else 0.0
                write = max(0.0, request.cache_creation_tokens - entered)
                share_1h = (request.cache_creation_1h_tokens / request.cache_creation_tokens
                            if request.cache_creation_tokens else 0.0)
                read = max(0.0, cf.contexts[i] - request.input_tokens - write)
                for bucket, value, cf_value in (
                    ("input", request.input_tokens, request.input_tokens),
                    ("cache_write_5m", request.cache_creation_tokens - request.cache_creation_1h_tokens,
                     write * (1.0 - share_1h)),
                    ("cache_write_1h", request.cache_creation_1h_tokens, write * share_1h),
                    ("cache_read", request.cache_read_tokens, read),
                    ("output", request.output_tokens, request.output_tokens),
                ):
                    observed[request.model][bucket] += value
                    counterfactual[request.model][bucket] += cf_value
    return {
        "per_model": {
            model_id: {
                bucket: {
                    "observed": round(total),
                    "reduction": round(1.0 - counterfactual[model_id][bucket] / total, 5) if total else 0.0,
                }
                for bucket, total in buckets.items()
            }
            for model_id, buckets in observed.items()
        },
        "api_price_weighted_reduction": price_weighted_reduction(observed, counterfactual),
        "unpriced_models": sorted(m for m in observed if m not in PRICES),
    }


BUCKET_PRICE_INDEX = {"input": 0, "cache_write_5m": 1, "cache_write_1h": 2, "cache_read": 3, "output": 4}


def price_weighted_reduction(observed: dict[str, dict[str, float]],
                             counterfactual: dict[str, dict[str, float]]) -> float:
    """Reduction in list-price-weighted usage across priced models; the K2 proxy."""
    before = after = 0.0
    for model_id, buckets in observed.items():
        prices = PRICES.get(model_id)
        if prices is None:
            continue
        for bucket, value in buckets.items():
            before += prices[BUCKET_PRICE_INDEX[bucket]] * value
            after += prices[BUCKET_PRICE_INDEX[bucket]] * counterfactual[model_id][bucket]
    return round(1.0 - after / before, 5) if before else 0.0


def reconstructed_july(sessions: Sequence[Session], model: Fit, categories: Sequence[str]) -> dict[str, float]:
    """The July headline, rebuilt one definition at a time. Reconstructed, not recovered."""
    wanted = frozenset(categories)
    result_bytes = 0
    measured_tokens = 0.0
    line_volume = 0.0
    request_volume = 0.0
    amplified = 0.0
    cache_read = 0.0
    for session in sessions:
        for transcript in _transcripts(session):
            requests = transcript.requests
            request_volume += sum(r.input_tokens + r.cache_creation_tokens for r in requests)
            cache_read += sum(r.cache_read_tokens for r in requests)
            lines_per_request = (
                (transcript.stats.assistant_lines - transcript.stats.synthetic) / len(requests) if requests else 0.0
            )
            line_volume += lines_per_request * sum(r.input_tokens + r.cache_creation_tokens for r in requests)
            for window in windows(transcript):
                remaining = len(requests) - (window.index + 1)
                for item in window.items:
                    if item.kind != "tool_result" or item.category not in wanted:
                        continue
                    result_bytes += item.text_bytes
                    tokens = model.rate_for(item.category) * item.text_bytes
                    measured_tokens += tokens
                    amplified += tokens * remaining
    return {
        "a_bytes_over_4_vs_line_summed_volume": round((result_bytes / 4) / line_volume, 5) if line_volume else 0.0,
        "b_dedup_requests": round((result_bytes / 4) / request_volume, 5) if request_volume else 0.0,
        "c_measured_tokens_per_byte": round(measured_tokens / request_volume, 5) if request_volume else 0.0,
        "d_amplified_ignoring_compaction_vs_cache_read": round(amplified / cache_read, 5) if cache_read else 0.0,
    }


def attribution_quality(all_windows: Sequence[Window]) -> tuple[Fit, dict[str, Any]]:
    train = [w for w in all_windows if not in_holdout(w)]
    holdout = [w for w in all_windows if in_holdout(w)]
    model = fit(train)
    forward, reverse = evaluate(model, holdout), evaluate(fit(holdout), train)
    return model, {
        "isolated_windows": {"train": sum(map(isolated, train)), "holdout": sum(map(isolated, holdout))},
        "tokens_per_byte": {k: round(v, 4) for k, v in sorted(model.rate.items())},
        "pooled_tokens_per_byte": round(model.pooled_rate, 4),
        "overhead_tokens_default": model.base_default,
        "holdout": {
            "median_abs_error_tokens": round(forward.median_abs_error_tokens, 1),
            "median_abs_pct_error_large": round(forward.median_abs_pct_error_large, 4),
            "predicted_over_observed": round(forward.predicted_over_observed, 4),
            "reverse_split_predicted_over_observed": round(reverse.predicted_over_observed, 4),
        },
    }


def decompose(projects_root: Path) -> dict[str, Any]:
    sessions = [load_session(path) for path in discover_sessions(projects_root)]
    all_windows = [w for s in sessions for t in _transcripts(s) for w in windows(t)]
    model, quality = attribution_quality(all_windows)
    return {
        "label": "exploratory; n below any convergence target",
        "sessions": len(sessions),
        "attribution": quality,
        "ceilings": {
            **{c: ceiling_report(sessions, model, category_selector([c])) for c in TOOL_CATEGORIES},
            "all_tool_results": ceiling_report(sessions, model, category_selector(TOOL_CATEGORIES)),
        },
        "usage_categories_bash_ceiling": usage_categories(sessions, model, category_selector(["bash"])),
        "reconstructed_july_method": {
            "bash": reconstructed_july(sessions, model, ["bash"]),
            "all_tool_results": reconstructed_july(sessions, model, TOOL_CATEGORIES),
        },
    }


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("root", nargs="?", default=str(Path.home() / ".claude" / "projects"))
    parser.add_argument("--out", help="write the JSON here instead of stdout; must be outside the repository")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    report = json.dumps(decompose(root), indent=2) + "\n"
    if args.out:
        refuse_repo_path(Path(args.out)).write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
