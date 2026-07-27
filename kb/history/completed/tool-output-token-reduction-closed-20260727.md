---
title: "Closed: Tool-Output Token Reduction — Three Attempts, One Ceiling"
category: planning
service: ai-toolkit
tags:
  - token-reduction
  - measurement
  - postmortem
  - prompt-caching
  - context-window
  - closed-line-of-work
doc_type: postmortem
status: completed
created: "2026-07-27"
last_updated: "2026-07-27"
description: "Closes the tool-output token-reduction line of work after a third measurement. Decomposes 1189 real sessions by cost: 84% is context being fed to the model, 14.7% is responses. Tool output is a small lever by construction and three independent attempts have now hit the same ceiling. Records what shipped (a 20.2% rag-mcp response trim, worth 0.49% of cost), what was killed by its own kill number, and the three measurement errors made on the way."
---

# Closed: Tool-Output Token Reduction

**Read this before proposing a fourth attempt.**

Three independent efforts have tried to cut tokens by shrinking what tools
return. All three were competently built. All three measured out near zero.

| Attempt | Shipped | Measured saving |
|---|---|---:|
| [Native tool-output filter](output-filter-retirement-20260726.md) | v4.16.0, removed v4.17.0 | **0.0000%** |
| [rtk-pack](rtk-pack-retirement-20260727.md) | v4.18.0, removed v4.19.0 | **0.0615%** |
| This review's only clean win (rag-mcp response trim) | rag-mcp, 2026-07-27 | **0.49%** |

This is not three unlucky implementations. It is one structural fact, measured
three different ways.

## Where the money actually is

1189 sessions with traffic, 83,352 assistant turns, priced at Opus list rates:

| Component | Share of cost |
|---|---:|
| `cache_read` | **63.1%** |
| `cache_creation` | 20.9% |
| `output` | 14.7% |
| `input` (uncached) | 1.3% |

**84% of cost is feeding context to the model.** Responses are 14.7%. That
closes "make the model write less" as a serious lever — the whole `brand-voice`
concise mode plays for a seventh of the bill.

Cache hit rate is **97.4%**. Published guidance treats 80–95% as the achievable
band, so there is nothing to win in cache tuning either.

Session shape: median 29 turns (mean 70.1), median peak context 71,276 tokens
(mean 114,712), median startup context 22,175 tokens.

## Why tool output cannot be the lever

Decomposed by amplification — every tool result is re-read on every turn that
follows it, so a result's true cost is its size times the turns remaining:

| Category | Share of `cache_read` |
|---|---:|
| Fixed startup prelude | 12.4% |
| `Read` results | 15.6% |
| `Bash` results | 6.7% |
| `rag-mcp` results | 3.8% |
| Unattributed (assistant text, thinking, user messages, reminders) | ~61% |

Every tool in the toolbox, amplified across every turn, is **26.1%** of
`cache_read`, and it is not compressible without losing what it says. The
original Phase 0 calculation reached the same place from the other direction:
tool results are 4.54% of input-token volume, so 4.54% is the arithmetic
ceiling for any mechanism operating on them.

Raw tool-result bytes, 113 MB across 1308 session files:

| Tool | Share of bytes |
|---|---:|
| `Read` | 62.2% |
| `Bash` | 26.1% |
| `rag-mcp` (3 tools) | 7.6% |
| everything else | <2% each |

## What shipped

**rag-mcp response compaction** — `compact_payload()` in
`app/rag-mcp-server/routes/kb_search.py`, applied to `smart_query`,
`hybrid_search_kb` and `get_document`, plus both sides of the smart_query cache
so a hit and a miss return identical bytes.

Verified by running the shipped function over 1356 real responses captured from
session logs: **20.2% smaller, with no field the agent acts on removed.**
That is 0.77% of `cache_read`, **0.49% of total cost**.

It drops request echo (`use_hyde`/`use_crag`/`use_multi_hop`), null result
columns, `_from_cache: false`, `total_documents_used` when it equals the result
count, and the part of `source_documents_used` that merely repeats
`results[].kb_id`. It deliberately keeps `file_path` (addresses Read/Edit, where
`kb_id` addresses get_document), `routing` (the only signal for which pipeline
ran), `score: 0.0`, and empty result sets. 16 unit tests, most of them asserting
what must survive rather than what gets removed.

## What was killed, and by what

A kill number was published before the work: *if the shipped changes do not cut
`cache_read` by 3%, stop and do not proceed to the behavioural changes.*

Result: **0.79%.** The threshold was not met, and the remaining items were not
built. The kill number did its job — this is the first of the three attempts
where it bound before code was written rather than after it shipped.

## Three measurement errors, and what they cost

Recorded because each one nearly produced a wrong decision, and because two of
them are the same class of error that produced the previous two failures.

**1. Duplicate reads: 11.1% was actually 0.1%.** The first pass keyed duplicate
detection on `file_path` alone, counting re-reads of *different ranges* of the
same file as waste. Re-keyed on `(file_path, offset, limit)`:

| Key | Duplicates | Bytes | Share of `Read` |
|---|---:|---:|---:|
| path only (wrong) | 1754 | 7,787,530 | 11.1% |
| path + offset + limit (right) | **36** | **90,975** | **0.1%** |

A whole planned deliverable — a session-scoped dedup hook, with a designed
mitigation for the post-compaction re-read hazard — rested on that 11.1%. It
does not exist.

**2. A 58% "trim" that was deleting document content.** An aggressive variant of
the rag-mcp compaction measured 58% smaller. It was whitelisting top-level keys
and thereby dropping `content` — which for `get_document` *is* the document,
30.5% of all bytes those endpoints return. Not a trim; data loss that looked
like a win. The honest figure is 20.2%.

**3. "77.5% of the rag-mcp response is overhead."** Roughly half of that
non-content mass is `kb_id`, `file_path`, `title` and `score` — fields the agent
uses. Removable overhead is about 20%, not 77%.

The common thread: **every one of these errors made the opportunity look bigger
than it is, and every one was caught only by decomposing before building.** The
filter retirement drew the same conclusion about premise validation; rtk-pack
drew it about installing the artifact. This adds a third: decompose the metric
before trusting its headline.

## What is left, and why it was not taken

| Option | Value | Why not |
|---|---:|---|
| Model routing | tens of % | Ruled out by the maintainer — Opus 5 stays |
| Trim the toolkit's own startup prelude | ~2.5% of cost | Ruled out — costs skill/agent discoverability |
| `Read` with ranges instead of whole files | up to 10.4% of `cache_read` | The only remaining item of size, and **not quality-neutral**: it is a behavioural change whose effect on correctness cannot be measured automatically |
| Unattributed ~61% of `cache_read` | unknown | Assistant text, thinking blocks, user messages, system reminders — no clean cut available |

For the record, the startup prelude was measured rather than guessed. Median
startup context is 22,175 tokens against ~7,850 in the documented reference
shape, and the gap is the toolkit's own:

| Component | Count | ~tokens |
|---|---:|---:|
| skill descriptions | 108 | 5,051 |
| agent descriptions | 44 | 2,750 |
| project rules | 5 | 3,802 |
| global rules | 6 | 3,133 |
| `CLAUDE.md` files | 3 | 2,338 |
| **total** | | **17,076** |

The tool built to reduce tokens is the single largest addition to every
session's context. That is worth knowing, and it is still only 2.5% of cost,
because the prelude is 12.4% of `cache_read` and only part of it is removable.

## The rule this leaves behind

**Do not open a fourth tool-output token-reduction effort without first
producing a measurement that beats 4.54%.** That is the ceiling on this workload
and it has now been approached from three directions. Any proposal in this space
must state, before any code, which share of *input token volume* it addresses —
not which share of tool output, not which share of Bash bytes.

If token cost genuinely needs to come down, the levers that are actually large
are model selection and turn count. Both are policy decisions, not engineering
projects, and neither is in this line of work.

## Related

- [Output Filter Retirement](output-filter-retirement-20260726.md) — attempt one, 0.0000%
- [rtk-pack Retirement](rtk-pack-retirement-20260727.md) — attempt two, 0.0615%
- [rtk Pack Integration](rtk-pack-integration-20260726.md) — the Phase 0 ceiling calculation
- [MCP Context Trim v4.0 — abandoned](mcp-context-trim-v4-prd-obsoleted-20260727.md) — a fourth idea in this space, killed by the platform shipping the fix first
- [Output & Token Discipline](output-token-discipline-plan-20260504.md) — the plan all of this descends from
