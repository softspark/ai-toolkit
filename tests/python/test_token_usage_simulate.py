# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Tests for benchmarks/token_usage/simulate.py.

The central case is the one the plan review raised: removing content can delay
an auto-compaction, and the delayed requests then run near the threshold, so a
removal can increase the total context the session consumed. A simulation that
only subtracts removals up to the observed compaction reports a saving there.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[2] / "benchmarks"
sys.path.insert(0, str(BENCH))

from token_usage.simulate import Step, replay_identity, simulate, steps  # noqa: E402
from token_usage.transcript import Compaction, ParseStats, Request, Transcript  # noqa: E402


def grow(n: int) -> Step:
    return Step(growth=n, event="")


# Observed: 100, 200, 300, 400, auto-compaction (pre 500) down to 50, then 60..100.
# The real threshold lies in (400, 500]: 400 did not trigger, 500 did.
OBSERVED = [100, 200, 300, 400, 50, 60, 70, 80, 90, 100]
PATH = [grow(100), grow(100), grow(100),
        Step(growth=-350, event="auto", pre_growth=100, post_tokens=50, after_growth=0,
             threshold_upper=500, threshold_lower=401),
        grow(10), grow(10), grow(10), grow(10), grow(10)]


@pytest.mark.parametrize("bound", ["upper", "lower"])
def test_nothing_removed_reproduces_the_observed_path(bound: str) -> None:
    replay = simulate(100, PATH, [0.0] * len(PATH), bound=bound)  # type: ignore[arg-type]
    assert list(replay.contexts) == OBSERVED
    assert replay.auto_compactions == 1


def test_under_the_lower_bound_a_small_removal_saves_until_the_compaction() -> None:
    cut = [30.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    replay = simulate(100, PATH, cut, bound="lower")
    assert list(replay.contexts) == [100, 170, 270, 370, 50, 60, 70, 80, 90, 100]
    assert sum(OBSERVED) - replay.total == 30 * 3


def test_under_the_upper_bound_the_same_removal_costs_more_than_it_saves() -> None:
    cut = [30.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    replay = simulate(100, PATH, cut, bound="upper")
    # 370 + 100 = 470 does not reach 500: no compaction in the window. Growth of 10
    # per request reaches 500 three requests later, and those requests run near
    # the threshold instead of near 50.
    assert list(replay.contexts) == [100, 170, 270, 370, 470, 480, 490, 50, 60, 70]
    assert replay.auto_compactions == 1
    assert replay.total > sum(OBSERVED)


def test_the_rebuild_after_a_compaction_is_paid_only_where_one_fires() -> None:
    # Observed: the first request after the compaction is 50 (summary) + 60
    # (re-attached files and new content); a plain window grows by 10.
    path = [grow(100), grow(100), grow(100),
            Step(growth=-290, event="auto", pre_growth=100, post_tokens=50, after_growth=60, new_growth=10,
                 threshold_upper=500, threshold_lower=401),
            grow(10), grow(10), grow(10), grow(10), grow(10)]
    observed = simulate(100, path, [0.0] * 9, bound="upper")
    assert list(observed.contexts) == [100, 200, 300, 400, 110, 120, 130, 140, 150, 160]
    assert observed.auto_fire_steps == (3,)

    delayed = simulate(100, path, [30.0] + [0.0] * 8, bound="upper")
    # Not compacting adds a plain window's growth, not the rebuild; compacting
    # three windows later pays the rebuild there.
    assert list(delayed.contexts) == [100, 170, 270, 370, 480, 490, 110, 120, 130, 140]
    assert delayed.auto_fire_steps == (5,)


def test_manual_compactions_stay_where_they_were() -> None:
    path = [grow(100), Step(growth=-150, event="manual", pre_growth=100, post_tokens=40, after_growth=10), grow(20)]
    replay = simulate(100, path, [80.0, 0.0, 0.0])
    assert list(replay.contexts) == [100, 120, 50, 70]
    assert (replay.manual_compactions, replay.auto_compactions) == (1, 0)


def _request(rid: str, order: int, model: str, context: int) -> Request:
    return Request(request_id=rid, order=order, model=model, timestamp="", input_tokens=0,
                   cache_creation_tokens=0, cache_creation_1h_tokens=0, cache_read_tokens=context,
                   output_tokens=0, iterations=1)


def transcript(contexts: list[tuple[int, str]], compactions: tuple[Compaction, ...]) -> Transcript:
    return Transcript(
        path=Path("x.jsonl"), agent_id=None, parent_tool_use_id=None,
        requests=tuple(_request(f"r{i}", i * 10, model, c) for i, (c, model) in enumerate(contexts)),
        tool_uses={}, tool_results=(), compactions=compactions, attachments=(), prompts=(), meta_messages=(),
        stats=ParseStats(lines=0, malformed=0, duplicate_uuids=0, assistant_lines=0, synthetic=0, multi_iteration=0),
    )


def test_identity_holds_with_a_model_switch_and_both_compaction_kinds() -> None:
    t = transcript(
        [(1000, "a"), (5000, "a"), (3000, "b"), (9000, "b"), (1200, "b"), (4000, "b"), (900, "b")],
        (Compaction(order=35, trigger="auto", pre_tokens=9800, post_tokens=1100),
         Compaction(order=55, trigger="manual", pre_tokens=4200, post_tokens=800)),
    )
    start, path = steps(t)
    assert start == 1000 and [s.event for s in path] == ["", "", "", "auto", "", "manual"]
    assert (path[3].threshold_lower, path[3].threshold_upper) == (9001, 9800)
    assert (path[3].after_growth, path[3].new_growth) == (100, 100)
    assert replay_identity(t)


def test_a_transcript_without_requests_is_trivially_reproduced() -> None:
    assert replay_identity(transcript([], ()))


def test_identity_check_can_fail() -> None:
    # A context above the compaction's own preTokens that did not trigger it is
    # inconsistent with any threshold; the check must say so rather than pass.
    t = transcript(
        [(1000, "a"), (9900, "a"), (9950, "a"), (1100, "a")],
        (Compaction(order=25, trigger="auto", pre_tokens=9800, post_tokens=1000),),
    )
    assert not replay_identity(t)
