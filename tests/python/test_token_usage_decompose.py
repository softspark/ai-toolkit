# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Tests for benchmarks/token_usage/decompose.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[2] / "benchmarks"
REPO_ROOT = BENCH.parent
sys.path.insert(0, str(BENCH))

from token_usage.attribute import Fit, Item  # noqa: E402
from token_usage.decompose import (  # noqa: E402
    SessionOutcome,
    bootstrap_interval,
    category_selector,
    main,
    price_weighted_reduction,
    reduction,
    removals,
    without_largest,
)
from token_usage.transcript import ParseStats, Request, ToolResult, Transcript  # noqa: E402

MODEL = Fit(base_by_attachments={}, base_default=50.0, rate={"bash": 0.5, "rag-mcp": 0.4}, pooled_rate=0.45,
            samples={})


def _request(rid: str, order: int, context: int) -> Request:
    return Request(request_id=rid, order=order, model="m", timestamp="", input_tokens=0,
                   cache_creation_tokens=0, cache_creation_1h_tokens=0, cache_read_tokens=context,
                   output_tokens=0, iterations=1)


def _result(tid: str, name: str, order: int, size: int) -> ToolResult:
    return ToolResult(tool_use_id=tid, tool_name=name, request_id="", order=order, text_bytes=size, image_count=0,
                      image_bytes=0, tool_reference_count=0, is_error=False, persisted=False)


def test_removals_align_with_simulation_steps_and_respect_the_selector() -> None:
    transcript = Transcript(
        path=Path("x.jsonl"), agent_id=None, parent_tool_use_id=None,
        requests=(_request("r1", 0, 100), _request("r2", 10, 800), _request("r3", 20, 1200)),
        tool_uses={},
        tool_results=(_result("a", "Bash", 5, 1000), _result("b", "mcp__rag-mcp__smart_query", 6, 500),
                      _result("c", "Bash", 15, 200)),
        compactions=(), attachments=(), prompts=(), meta_messages=(),
        stats=ParseStats(lines=0, malformed=0, duplicate_uuids=0, assistant_lines=0, synthetic=0, multi_iteration=0),
    )
    assert removals(transcript, MODEL, category_selector(["bash"])) == [500.0, 100.0]
    assert removals(transcript, MODEL, category_selector(["bash", "rag-mcp"])) == [700.0, 100.0]
    prompt = Item(kind="prompt", category="bash", text_bytes=10, tool_use_id=None)
    assert category_selector(["bash"])(prompt) == 0.0


OUTCOMES = [SessionOutcome(1000.0 * (i + 1), 1000.0 * (i + 1) * (0.9 if i % 2 else 0.95), 0, 0) for i in range(12)]


def test_reduction_is_pooled_not_averaged() -> None:
    skewed = [SessionOutcome(1_000_000.0, 990_000.0, 0, 0), SessionOutcome(10.0, 5.0, 0, 0)]
    assert reduction(skewed) == pytest.approx(10_005 / 1_000_010)


def test_bootstrap_is_deterministic_and_brackets_the_estimate() -> None:
    low, high = bootstrap_interval(OUTCOMES)
    assert (low, high) == bootstrap_interval(OUTCOMES)
    assert low <= reduction(OUTCOMES) <= high
    assert high - low > 0


def test_without_largest_drops_the_biggest_sessions_in_turn() -> None:
    values = without_largest(OUTCOMES)
    assert len(values) == 3
    assert values[0] == pytest.approx(reduction(OUTCOMES[:-1]))


def test_price_weighting_uses_per_model_rates_and_skips_unknown_models() -> None:
    observed = {
        "claude-opus-5": {"input": 0.0, "cache_write_5m": 0.0, "cache_write_1h": 100.0, "cache_read": 1000.0,
                          "output": 10.0},
        "mystery-model": {"input": 1e9, "cache_write_5m": 0.0, "cache_write_1h": 0.0, "cache_read": 0.0,
                          "output": 0.0},
    }
    counterfactual = {
        "claude-opus-5": {"input": 0.0, "cache_write_5m": 0.0, "cache_write_1h": 50.0, "cache_read": 500.0,
                          "output": 10.0},
        "mystery-model": {"input": 0.0, "cache_write_5m": 0.0, "cache_write_1h": 0.0, "cache_read": 0.0,
                          "output": 0.0},
    }
    # Opus 5: before 100*10 + 1000*0.5 + 10*25 = 1750, after 500 + 250 + 250 = 1000.
    assert price_weighted_reduction(observed, counterfactual) == pytest.approx(1 - 1000 / 1750, abs=1e-5)


def test_cli_refuses_to_write_into_the_repository(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    (root / "-p").mkdir(parents=True)
    with pytest.raises(ValueError):
        main([str(root), "--out", str(REPO_ROOT / "benchmarks" / "token_usage" / "report.json")])
    assert not (REPO_ROOT / "benchmarks" / "token_usage" / "report.json").exists()
