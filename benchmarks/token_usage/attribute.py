# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Attribute context growth between consecutive requests to what entered it.

Transcripts record usage per request but no token count per tool result. The
growth between request *t* and *t+1* is observable:

    delta(t) = context(t+1) - context(t) - output(t)

and it is made of the tool results, user prompts and attachments written between
the two requests, plus a per-turn overhead. This module fits that relationship on
**isolated windows** — one text-only tool result, nothing else variable — and
applies it everywhere else, keeping what it cannot explain as an explicit
residual rather than spreading it proportionally.

Two decisions the plan's review forced, both deliberate:

- The fit is judged on a holdout half, split by a stable hash of the request id.
  Calibrating and validating on the same deltas would make any "unattributed"
  figure small by construction.
- Rates are per category and in tokens per byte, measured, never ``bytes / 4``.
  On the September corpus large Bash results measure near 0.45 tokens per byte,
  so a bytes-over-four conversion undercounts them by roughly 1.8x.

A window across a model switch or a compaction is not a growth window: the
context is rebuilt, not appended to. Such windows are kept but never fitted, and
their residual is labelled ``boundary``.
"""
from __future__ import annotations

import hashlib
import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .transcript import Transcript

TINY_RESULT_BYTES = 50
MIN_RATE_BYTES = 512
MIN_CATEGORY_SAMPLES = 20
# Attachments whose cost is a small per-turn constant, fitted as part of the
# overhead. Any other attachment type (nested_memory, edited_text_file,
# skill_listing, ...) carries content the transcript does not store, so a window
# holding one cannot be used to fit a rate and its residual is labelled.
LIGHT_ATTACHMENTS = frozenset({
    "output_style", "total_tokens_reminder", "hook_additional_context", "batching_reminder_sent",
})


def tool_category(tool_name: str) -> str:
    if tool_name == "Bash":
        return "bash"
    if tool_name == "Read":
        return "read"
    if tool_name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        return "edit"
    if tool_name.startswith("mcp__rag-mcp__"):
        return "rag-mcp"
    if tool_name.startswith("mcp__Claude_Browser__"):
        return "browser"
    return "other-tool"


@dataclass(frozen=True, slots=True)
class Item:
    kind: str  # "tool_result" | "prompt" | "meta"
    category: str
    text_bytes: int
    tool_use_id: str | None
    image_count: int = 0
    tool_reference_count: int = 0
    persisted: bool = False

    @property
    def text_only(self) -> bool:
        return not (self.image_count or self.tool_reference_count or self.persisted)


@dataclass(frozen=True, slots=True)
class Window:
    index: int
    key: str
    delta: int
    model_switch: bool
    compaction: bool
    items: tuple[Item, ...]
    attachment_types: tuple[str, ...]

    @property
    def boundary(self) -> bool:
        return self.model_switch or self.compaction

    @property
    def heavy_attachments(self) -> bool:
        return any(a not in LIGHT_ATTACHMENTS for a in self.attachment_types)


def windows(transcript: Transcript) -> list[Window]:
    requests = transcript.requests
    results = sorted(transcript.tool_results, key=lambda r: r.order)
    prompts = sorted(transcript.prompts, key=lambda p: p.order)
    metas = sorted(transcript.meta_messages, key=lambda p: p.order)
    attachments = sorted(transcript.attachments, key=lambda a: a.order)
    compaction_orders = [c.order for c in transcript.compactions]
    out: list[Window] = []
    for index, (before, after) in enumerate(zip(requests, requests[1:])):
        lo, hi = before.order, after.order
        items = [
            Item(kind="tool_result", category=tool_category(r.tool_name), text_bytes=r.text_bytes,
                 tool_use_id=r.tool_use_id, image_count=r.image_count,
                 tool_reference_count=r.tool_reference_count, persisted=r.persisted)
            for r in results if lo < r.order < hi
        ]
        items += [Item(kind="prompt", category="prompt", text_bytes=p.text_bytes, tool_use_id=None)
                  for p in prompts if lo < p.order < hi]
        items += [Item(kind="meta", category="meta", text_bytes=p.text_bytes, tool_use_id=None)
                  for p in metas if lo < p.order < hi]
        out.append(Window(
            index=index,
            key=after.request_id,
            delta=after.context_tokens - before.context_tokens - before.output_tokens,
            model_switch=before.model != after.model,
            compaction=any(lo < o < hi for o in compaction_orders),
            items=tuple(items),
            attachment_types=tuple(sorted(a.type for a in attachments if lo < a.order < hi)),
        ))
    return out


def in_holdout(window: Window) -> bool:
    """Stable 50/50 split: the same request always lands on the same side."""
    return hashlib.sha1(window.key.encode("utf-8")).digest()[0] % 2 == 1


def isolated(window: Window) -> bool:
    return (not window.boundary and not window.heavy_attachments and len(window.items) == 1
            and window.items[0].kind == "tool_result" and window.items[0].text_only)


@dataclass(frozen=True, slots=True)
class Fit:
    base_by_attachments: dict[tuple[str, ...], float]
    base_default: float
    rate: dict[str, float]
    pooled_rate: float
    samples: dict[str, int]

    def base(self, window: Window) -> float:
        return self.base_by_attachments.get(window.attachment_types, self.base_default)

    def rate_for(self, category: str) -> float:
        return self.rate.get(category, self.pooled_rate)


def fit(sample: Iterable[Window]) -> Fit:
    usable = [w for w in sample if isolated(w)]
    tiny = [w for w in usable if w.items[0].text_bytes < TINY_RESULT_BYTES]
    if not tiny:
        raise ValueError("no isolated tiny-result windows to estimate the per-turn overhead from")
    by_attachments: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for w in tiny:
        by_attachments[w.attachment_types].append(w.delta)
    base_default = float(statistics.median(w.delta for w in tiny))
    base = {k: float(statistics.median(v)) for k, v in by_attachments.items() if len(v) >= 5}

    def overhead(w: Window) -> float:
        return base.get(w.attachment_types, base_default)

    # Ratio of sums, not a median of per-window ratios. The decision metric is a
    # total, and a median fits the typical window while missing the heavy tail:
    # on the September holdout the median rate predicted 0.79 of observed growth.
    tokens: dict[str, float] = defaultdict(float)
    size: dict[str, int] = defaultdict(int)
    samples: dict[str, int] = defaultdict(int)
    for w in usable:
        item = w.items[0]
        if item.text_bytes >= MIN_RATE_BYTES:
            tokens[item.category] += w.delta - overhead(w)
            size[item.category] += item.text_bytes
            samples[item.category] += 1
    if not size:
        raise ValueError(f"no isolated window carries a result of {MIN_RATE_BYTES} bytes or more")
    return Fit(
        base_by_attachments=base,
        base_default=base_default,
        rate={c: tokens[c] / size[c] for c in size if samples[c] >= MIN_CATEGORY_SAMPLES},
        pooled_rate=sum(tokens.values()) / sum(size.values()),
        samples=dict(samples),
    )


def predict(model: Fit, window: Window) -> float:
    return model.base(window) + sum(model.rate_for(i.category) * i.text_bytes for i in window.items)


@dataclass(frozen=True, slots=True)
class Evaluation:
    windows: int
    median_abs_error_tokens: float
    large_results: int
    median_abs_pct_error_large: float
    predicted_over_observed: float


def evaluate(model: Fit, sample: Iterable[Window]) -> Evaluation:
    usable = [w for w in sample if isolated(w)]
    if not usable:
        raise ValueError("no isolated windows to evaluate on")
    errors = [abs(predict(model, w) - w.delta) for w in usable]
    large = [w for w in usable if w.items[0].text_bytes >= MIN_RATE_BYTES and w.delta > 0]
    observed = sum(w.delta for w in usable)
    return Evaluation(
        windows=len(usable),
        median_abs_error_tokens=float(statistics.median(errors)),
        large_results=len(large),
        median_abs_pct_error_large=float(statistics.median(abs(predict(model, w) - w.delta) / w.delta for w in large))
        if large else 0.0,
        predicted_over_observed=sum(predict(model, w) for w in usable) / observed if observed else 0.0,
    )


def attribute(model: Fit, window: Window) -> dict[str, float]:
    """Split one window's growth into categories; the unexplained part is named, not hidden."""
    parts: dict[str, float] = defaultdict(float)
    parts["overhead"] += model.base(window)
    for item in window.items:
        parts[item.category] += model.rate_for(item.category) * item.text_bytes
    residual = window.delta - sum(parts.values())
    if window.boundary:
        label = "boundary"
    elif window.heavy_attachments:
        label = "attachment"
    elif any(i.tool_reference_count for i in window.items):
        label = "tool-schema"
    elif any(i.image_count for i in window.items):
        label = "image"
    else:
        label = "unattributed"
    parts[label] += residual
    return dict(parts)
