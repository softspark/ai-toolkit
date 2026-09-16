# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Tests for benchmarks/token_usage/attribute.py.

The synthetic windows are generated from known parameters — an overhead per
attachment set and a tokens-per-byte rate per category — so the fit has a right
answer to recover and a wrong one to be caught giving.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[2] / "benchmarks"
sys.path.insert(0, str(BENCH))

from token_usage.attribute import (  # noqa: E402
    Item,
    Window,
    attribute,
    evaluate,
    fit,
    in_holdout,
    isolated,
    predict,
    tool_category,
    windows,
)
from token_usage.transcript import (  # noqa: E402
    Attachment,
    Compaction,
    ParseStats,
    Prompt,
    Request,
    ToolResult,
    Transcript,
)

RATES = {"bash": 0.45, "rag-mcp": 0.30}
OVERHEAD = {("output_style", "total_tokens_reminder"): 70, ("output_style",): 55}


def window(i: int, category: str, size: int, attachments: tuple[str, ...], **flags: bool) -> Window:
    delta = OVERHEAD.get(attachments, 60) + round(RATES.get(category, 0.25) * size)
    return Window(index=i, key=f"req-{i}", delta=delta, model_switch=flags.get("switch", False),
                  compaction=flags.get("compaction", False),
                  items=(Item(kind="tool_result", category=category, text_bytes=size, tool_use_id=f"t{i}"),),
                  attachment_types=attachments)


def synthetic_sample() -> list[Window]:
    sample: list[Window] = []
    both = ("output_style", "total_tokens_reminder")
    for i in range(400):
        attachments = both if i % 4 else ("output_style",)
        if i % 5 == 0:
            sample.append(window(i, "bash", 20, attachments))
        elif i % 5 in (1, 2, 3):
            sample.append(window(i, "bash", 600 + 37 * i, attachments))
        else:
            sample.append(window(i, "rag-mcp", 900 + 11 * i, attachments))
    return sample


def test_tool_categories() -> None:
    assert [tool_category(n) for n in ("Bash", "Read", "Edit", "mcp__rag-mcp__smart_query",
                                         "mcp__Claude_Browser__computer", "WebFetch")] == \
        ["bash", "read", "edit", "rag-mcp", "browser", "other-tool"]


def test_fit_recovers_known_overheads_and_rates() -> None:
    model = fit(synthetic_sample())
    assert model.base_by_attachments[("output_style", "total_tokens_reminder")] == pytest.approx(70, abs=10)
    assert model.base_by_attachments[("output_style",)] == pytest.approx(55, abs=10)
    assert model.rate["bash"] == pytest.approx(0.45, abs=0.01)
    assert model.rate["rag-mcp"] == pytest.approx(0.30, abs=0.01)
    # The rates must differ: one pooled rate would hide the category structure.
    assert abs(model.rate["bash"] - model.rate["rag-mcp"]) > 0.1


def test_bytes_over_four_would_fail_the_same_check() -> None:
    sample = synthetic_sample()
    model = fit(sample)
    quarter = type(model)(base_by_attachments=model.base_by_attachments, base_default=model.base_default,
                          rate={c: 0.25 for c in model.rate}, pooled_rate=0.25, samples=model.samples)
    assert evaluate(model, sample).predicted_over_observed == pytest.approx(1.0, abs=0.02)
    assert evaluate(quarter, sample).predicted_over_observed < 0.8


def test_boundary_and_multi_item_windows_are_never_fitted() -> None:
    sample = synthetic_sample()
    poisoned = [window(1000 + i, "bash", 5000, ("output_style",), switch=True) for i in range(50)]
    poisoned = [Window(index=w.index, key=w.key, delta=-90000, model_switch=True, compaction=False,
                       items=w.items, attachment_types=w.attachment_types) for w in poisoned]
    assert not any(isolated(w) for w in poisoned)
    assert fit(sample + poisoned).rate["bash"] == pytest.approx(fit(sample).rate["bash"])


def test_holdout_split_is_stable_and_roughly_even() -> None:
    sample = synthetic_sample()
    first = [in_holdout(w) for w in sample]
    assert first == [in_holdout(w) for w in sample]
    assert 0.35 < sum(first) / len(first) < 0.65


def test_attribution_names_its_residual() -> None:
    model = fit(synthetic_sample())
    plain = window(1, "bash", 2000, ("output_style", "total_tokens_reminder"))
    parts = attribute(model, plain)
    assert sum(parts.values()) == pytest.approx(plain.delta)
    assert parts["bash"] == pytest.approx(900, rel=0.03)

    schema = Window(index=2, key="k", delta=4000, model_switch=False, compaction=False,
                    items=(Item(kind="tool_result", category="other-tool", text_bytes=100, tool_use_id="t",
                                tool_reference_count=3),), attachment_types=())
    assert attribute(model, schema)["tool-schema"] > 3000
    switched = window(3, "bash", 100, (), switch=True)
    assert "boundary" in attribute(model, switched)
    assert predict(model, plain) == pytest.approx(plain.delta, rel=0.05)


def _request(rid: str, order: int, model: str, context: int, out: int) -> Request:
    return Request(request_id=rid, order=order, model=model, timestamp="", input_tokens=0,
                   cache_creation_tokens=0, cache_creation_1h_tokens=0, cache_read_tokens=context,
                   output_tokens=out, iterations=1)


def test_windows_collect_items_between_requests() -> None:
    transcript = Transcript(
        path=Path("x.jsonl"), agent_id=None, parent_tool_use_id=None,
        requests=(_request("r1", 1, "m", 1000, 10), _request("r2", 5, "m", 1500, 20),
                  _request("r3", 9, "other", 800, 5)),
        tool_uses={},
        tool_results=(ToolResult(tool_use_id="t1", tool_name="Bash", request_id="r1", order=3, text_bytes=900,
                                 image_count=0, image_bytes=0, tool_reference_count=0, is_error=False,
                                 persisted=False),),
        compactions=(Compaction(order=7, trigger="auto", pre_tokens=1500, post_tokens=300),),
        attachments=(Attachment(order=4, type="output_style"),),
        prompts=(Prompt(order=6, text_bytes=40),),
        meta_messages=(Prompt(order=8, text_bytes=900),),
        stats=ParseStats(lines=0, malformed=0, duplicate_uuids=0, assistant_lines=0, synthetic=0,
                         multi_iteration=0),
    )
    first, second = windows(transcript)
    assert (first.delta, first.attachment_types, [i.category for i in first.items]) == (490, ("output_style",), ["bash"])
    assert isolated(first)
    assert second.compaction and second.model_switch and [i.kind for i in second.items] == ["prompt", "meta"]
    assert not isolated(second)


def test_windows_carrying_unstored_content_are_not_isolated() -> None:
    model = fit(synthetic_sample())
    heavy = Window(index=1, key="k1", delta=12000, model_switch=False, compaction=False,
                   items=(Item(kind="tool_result", category="bash", text_bytes=21, tool_use_id="t"),),
                   attachment_types=("nested_memory", "output_style"))
    skill = Window(index=2, key="k2", delta=9000, model_switch=False, compaction=False,
                   items=(Item(kind="tool_result", category="other-tool", text_bytes=27, tool_use_id="t"),
                          Item(kind="meta", category="meta", text_bytes=18000, tool_use_id=None)),
                   attachment_types=("output_style",))
    assert not isolated(heavy) and not isolated(skill)
    assert attribute(model, heavy)["attachment"] > 11000
    assert attribute(model, skill)["meta"] > 5000
