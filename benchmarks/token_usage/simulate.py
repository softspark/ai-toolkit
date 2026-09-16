# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Forward-simulate a session's context path when content is removed as it enters.

Removing tokens from a tool result does not just subtract them from every later
request. It also moves the next auto-compaction: a smaller context reaches the
threshold later, and every request in the delay runs near the threshold instead
of near the post-compaction size. Subtracting the removal until the observed
compaction and stopping there — the shortcut this replaces — can report a saving
where there is a loss. So the path is rebuilt step by step:

- a manual compaction happens where it was observed, whatever the context size;
- an auto compaction fires when the counterfactual context reaches the threshold
  of the next pending auto compaction, and drops to that compaction's observed
  post size;
- growth between requests is the observed growth minus what was removed in that
  window, so model-switch drops and cache rebuilds carry over unchanged.

The threshold itself is not recorded. What is recorded bounds it: it is above the
largest context in the segment that did not trigger a compaction, and at most
the observed ``preTokens``. ``bound="upper"`` uses ``preTokens`` and makes any
removal in the segment delay the compaction; ``bound="lower"`` uses the largest
non-triggering context and delays it least. Report both.

With nothing removed the simulation must reproduce the observed path exactly
under either bound; ``replay_identity`` is that check, and a transcript it fails
on is not simulated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from .transcript import Transcript

Bound = Literal["upper", "lower"]


@dataclass(frozen=True, slots=True)
class Step:
    """Growth between request t and t+1, in the terms the simulation needs."""

    growth: int  # context(t+1) - context(t); used when no compaction happens in the window
    event: str  # "" | "auto" | "manual"
    pre_growth: int = 0  # pre_tokens - context(t): growth up to the compaction
    post_tokens: int = 0  # size right after the compaction
    after_growth: int = 0  # context(t+1) - post_tokens: rebuild after the compaction plus new content
    new_growth: int = 0  # the part of after_growth a window would add without a compaction
    threshold_upper: int = 0  # auto: observed pre_tokens
    threshold_lower: int = 0  # auto: largest context in the segment that did not trigger, plus one


@dataclass(frozen=True, slots=True)
class ContextPath:
    contexts: tuple[float, ...]
    auto_compactions: int
    manual_compactions: int
    auto_fire_steps: tuple[int, ...] = ()

    @property
    def total(self) -> float:
        return sum(self.contexts)


def steps(transcript: Transcript) -> tuple[int, list[Step]]:
    requests = transcript.requests
    if not requests:
        return 0, []
    compactions = sorted(transcript.compactions, key=lambda c: c.order)
    pairs = list(zip(requests, requests[1:]))
    inside_of = [[c for c in compactions if b.order < c.order < a.order] for b, a in pairs]
    # The first request after a compaction re-attaches files, memory and skills —
    # 53K to 64K tokens on the September corpus. Without a compaction that content
    # is still in the history, so a window that does not compact adds only a
    # typical window's growth; the rebuild is paid only where a compaction fires.
    plain_growth = sorted(a.context_tokens - b.context_tokens for (b, a), inside in zip(pairs, inside_of) if not inside)
    typical = plain_growth[len(plain_growth) // 2] if plain_growth else 0
    out: list[Step] = []
    segment_max = requests[0].context_tokens
    for (before, after), inside in zip(pairs, inside_of):
        segment_max = max(segment_max, before.context_tokens)
        if not inside:
            out.append(Step(growth=after.context_tokens - before.context_tokens, event=""))
            continue
        last = inside[-1]
        after_growth = after.context_tokens - last.post_tokens
        out.append(Step(
            growth=after.context_tokens - before.context_tokens,
            event="manual" if last.trigger == "manual" else "auto",
            pre_growth=last.pre_tokens - before.context_tokens,
            post_tokens=last.post_tokens,
            after_growth=after_growth,
            new_growth=max(0, min(after_growth, typical)),
            threshold_upper=last.pre_tokens,
            threshold_lower=segment_max + 1,
        ))
        segment_max = after.context_tokens
    return requests[0].context_tokens, out


def simulate(start: int, path: Sequence[Step], removed: Sequence[float], *, bound: Bound = "upper") -> ContextPath:
    """``removed[t]`` is the number of tokens taken out of what entered between request t and t+1."""
    if len(removed) != len(path):
        raise ValueError("one removal per step is required")
    autos = [s for s in path if s.event == "auto"]
    pending = 0  # index of the next observed auto compaction the counterfactual has not fired yet

    def threshold() -> float:
        step = autos[pending]
        return float(step.threshold_upper if bound == "upper" else step.threshold_lower)

    context = float(start)
    contexts = [context]
    fired_manual = 0
    fired_at: list[int] = []
    for index, (step, cut) in enumerate(zip(path, removed)):
        if step.event == "manual":
            context = float(step.post_tokens + step.after_growth)
            fired_manual += 1
        elif step.event == "auto" and pending < len(autos):
            if context + step.pre_growth - cut >= threshold():
                context = float(autos[pending].post_tokens + step.after_growth)
                fired_at.append(index)
                pending += 1
            else:
                context = context + step.pre_growth - cut + step.new_growth
        elif step.event == "auto":
            context = context + step.pre_growth - cut + step.new_growth
        else:
            candidate = context + step.growth - cut
            if pending < len(autos) and candidate >= threshold():
                # Compacting here pays the rebuild the observed compaction paid.
                context = float(autos[pending].post_tokens + autos[pending].after_growth)
                fired_at.append(index)
                pending += 1
            else:
                context = candidate
        contexts.append(context)
    return ContextPath(contexts=tuple(contexts), auto_compactions=len(fired_at), manual_compactions=fired_manual,
                       auto_fire_steps=tuple(fired_at))


def replay_identity(transcript: Transcript) -> bool:
    """True when, under both threshold bounds, removing nothing reproduces every observed context size."""
    if not transcript.requests:
        return True  # nothing observed, nothing to reproduce
    start, path = steps(transcript)
    observed = [float(r.context_tokens) for r in transcript.requests]
    autos = sum(1 for s in path if s.event == "auto")
    for bound in ("upper", "lower"):
        replayed = simulate(start, path, [0.0] * len(path), bound=bound)
        if list(replayed.contexts) != observed or replayed.auto_compactions != autos:
            return False
    return True
