---
title: "Completed: Token-Usage Re-Measurement and rtk v0.49.0 Replay"
category: planning
service: ai-toolkit
tags:
  - token-reduction
  - measurement
  - context-window
  - usage-limits
  - rtk
  - compaction
  - postmortem
doc_type: postmortem
status: completed
created: "2026-09-16"
last_updated: "2026-09-16"
completion: "100% — closed on the exploratory corpus by maintainer decision; target-size re-run dropped"
description: "Re-measured what tool output costs Claude Code sessions after the July closure proved unreproducible: committed harness, request-level accounting, holdout-validated token attribution, forward simulation of compaction, offline replay of rtk v0.49.0 against thresholds fixed in advance. rtk misses them at the point estimate; the July number was wrong, its conclusion held. Ships a 1.9-2.6x over-count fix in session_token_stats.py and a measured token density for pack-codebase."
---

# Completed: Token-Usage Re-Measurement and rtk v0.49.0 Replay

The July line of work ended in
[Closed: Tool-Output Token Reduction](tool-output-token-reduction-closed-20260727.md),
which put rtk-pack at 0.0615% of input tokens. That number could not be re-derived:
its harness was never committed and its 1224-transcript corpus aged out of Claude
Code's 30-day transcript retention. This work rebuilt the measurement in
`benchmarks/token_usage/`, where it cannot be lost the same way, and closed on a
15-session corpus. All figures are aggregates; no session id, path or command text
appears here, because `kb/` ships in the npm package.

**Outcome in one line:** the July number was wrong in both directions, the July
decision was right — rtk is worth about 2% of context tokens in sessions that do not
compact, below the bar set before the replay ran.

## 1. The plan as executed

| Phase | What it did | Result |
|---|---|---|
| 0. Preserve data | Snapshot of every transcript, subagent file and persisted tool result, outside the repository, owner-only; transcript retention raised; statusline tap logging rate-limit utilisation | Done; the retention change and the tap were removed when the re-run was dropped |
| 1. Harness | `transcript.py`, `attribute.py`, `simulate.py`, `survey.py`, `decompose.py`, tests that fail on deliberately wrong input | Done; every parser rule survived mutation testing (8 mutants killed) |
| 2. Decomposition | Category ceilings on the context window, bootstrap CIs, leave-top-3-out, a reconstruction of the July headline | Done, section 3 |
| 3. rtk replay | `replay_rtk.py` + container-side runner, pinned binary, no network | Done, section 4 |
| 4. Target-size re-run | Wait for the K1a CI half-width to reach 0.5 pp (it was 0.96 pp) | **Dropped** by the maintainer: the point estimate and the break-even already decide |
| 5. Record | This document, fixes in section 5 | Done |

An independent methodology review before Phase 1 raised twelve flaws. The ones that
changed the method: compaction must be simulated forward (removal can raise the
total), extra turns caused by rtk need a break-even figure, K2 needs per-model prices
rather than a weight regression on account-wide utilisation, the validation gates
must use a holdout instead of calibrating and validating on the same deltas, and
results must never be written inside the repository.

## 2. What was wrong with the July numbers

Measured on the September corpus. D1, D2 and D3 are properties of the data or of the
July documents; whether the lost July harness had D1 is unknown.

| # | Defect | Direction |
|---|---|---|
| D1 | A transcript writes one assistant line per content block, 1.905 lines per request, and repeats usage on each. `scripts/session_token_stats.py` summed lines: 1.9x (cache reads) to 2.6x (output) over. Fixed, section 5. | inflates |
| D2 | A saved token counted once against a denominator that counts re-reads (4.54% of input volume and 26.1% of `cache_read` for the same results). | understates |
| D3 | Amplification by turns remaining ignores compaction. | overstates |
| D4 | `bytes / 4`. Measured on a holdout: Bash 0.44 tokens per byte, rag-mcp 0.41, browser 0.45 — the 4.7+ tokenizer. | understates ~1.8x |
| D5 | `rtk pipe` caps differ from live commands (grep 10 matches per file vs 25 plus line shortening). | ambiguous |
| D6 | 9 of 12 persisted previews carry only the `<persisted-output>` marker, not `persistedOutputPath`. | misattributes |

Rebuilt one definition at a time, the July headline reads **4.4%** on today's corpus
("`bytes / 4` over line-summed volume", about 0.1 pp from July's 4.54%), 8.7% with
request deduplication, 15.2% with measured tokens per byte. Reconstructed, not
recovered.

## 3. Decomposition

- **M1, context window.** `C = input + cache_creation + cache_read` per request, the
  formula behind `context_window.used_percentage`. Removal is simulated forward:
  auto-compaction fires at the threshold, bounded between the largest context that
  did not trigger it and the observed `preTokens` (both bounds reported), and drops to
  the observed post size plus the observed rebuild of 53K–64K tokens; manual
  compactions stay put. With nothing removed the simulation reproduces all 19
  transcripts exactly.
- **M2, usage limits.** Not published per token. Reported per usage category per
  model, plus a proxy weighted by API list price read on 2026-09-16 (1-hour cache
  writes at 2x; Fable 5.1 cache reads at 0.025x).

Attribution on the holdout half: predicted over observed growth 1.003 (reverse split
1.019), median absolute error 19 tokens per window. A median-of-ratios rate had
predicted 0.79 of the total; ratio-of-sums replaced it. Bash is 51.6% of non-boundary
context growth. The largest session holds 51.5% of `ΣC`, the top three 90.5%.

Ceilings — every token of the category removed, lower threshold bound:

| Category | all sessions | without compaction | with compaction |
|---|---:|---:|---:|
| Bash | 5.5% (CI -11% to 17%) | 26.7% | 3.2% |
| all tool results | 2.6% | 33.9% | -0.7% |
| rag-mcp | 1.1% | 5.1% | 0.7% |

**Less content delays compaction, and delayed requests run near the threshold.**
Removing every Bash result delays auto compaction by 783 requests in total and
raises `ΣC` in two of the three compacting sessions. Fewer compactions and fewer
tokens are different goals, which is why K1 was split in two.

## 4. rtk v0.49.0 replay

Thresholds fixed before the replay: **K1a** sessions without compaction, `ΣC`
reduction >= 2% at the point estimate, 90% CI lower bound > 0, still >= 2% with each
of the three largest left out; **K1b** sessions with compaction, no auto compaction
moves earlier; **K2** price-weighted usage reduction >= 2%; plus the **retry
break-even**, extra requests per 100 rewritten commands that cancel the saving.

Pinned binary (SHA-256 in `replay_rtk.py`; the release's glibc 2.39 requirement makes
a Debian bookworm image fail every call silently), container with no network and a
read-only root, telemetry and recall off. Through rtk's own Claude hook: 1462 of 4222
Bash calls rewritten, 44.7% of Bash bytes. Of the rewritten bytes, 50% are commands
with several rtk calls and 11% are `rtk read` (0 at its default level); only 24.8%
pass through a measurable filter.

| Filter | Samples | Bytes removed |
|---|---:|---:|
| grep | 345 | 16.8% |
| git diff | 12 | 27.0% |
| find | 11 | 38.6% |
| git log | 6 | 75.5% |
| git status | 5 | 0.4% |

About 13% of removed bytes are whitespace, so the byte-based token conversion holds.

| Level (unmeasured rewrites save) | K1a | K1b | K2 | Retry break-even |
|---|---|---|---|---|
| lower (nothing) | 0.49% — fail | pass | 0.25% — fail | ~1 per 100 |
| **point (pooled measured share)** | **1.95%, CI 0.9–2.8% — fail** | **pass** | **0.89% — fail** | **3.2–3.8 per 100** |
| upper (best family with >= 20 samples, never below pooled) | 1.95% — fail | pass | 0.89% — fail | 3.2–3.8 per 100 |
| extreme (git log's 75% on every unmeasured rewrite) | 6.5% — pass | pass | 2.02% — pass | ~8.4 per 100 |

**Decision: rtk is not adopted and no live A/B runs.** Only the extreme level passes,
and it assumes every compound command shrinks like six `git log` samples. Three to
four extra requests per hundred rewritten commands erase the point-estimate saving,
and rtk's truncated grep and condensed diffs make that retry rate plausible.

## 5. What shipped

- **`scripts/session_token_stats.py`** reads usage once per `requestId` (fallback
  `message.id`), takes the largest `output_tokens`, skips repeated `uuid` records and
  `<synthetic>` placeholders, and never picks a subagent transcript as the latest
  session. On the corpus the old code over-counted 1.9x to 2.6x per field, which is
  what `/briefing --tokens` and the trend baseline showed. Three bats tests, red on
  the old code.
- **`scripts/pack_codebase.py`** estimates tokens at the measured 0.44 per character
  instead of 4 characters per token, which had let a 100k pack reach about 180k real
  tokens. One bats test, red on the old code.
- **`benchmarks/token_usage/`** — the harness and its tests. Every writer refuses paths
  inside the repository.
- A statusline comment that had described colour thresholds the code never used.

Not changed, deliberately: `scripts/compile_slm.py` targets `cl100k_base` for small
local models, and `scripts/doctor.py` estimates prose, which this work did not
measure.

## 6. Left open

- **Session shape is the larger lever, unmeasured.** Tokens follow session length and
  compaction far more than tool output: a request late in a long session re-reads up
  to ~1M tokens, and a compaction resets that to ~80K. Shorter sessions, or earlier
  compaction via `/compact` or `autoCompactWindow`, should cut usage more than any
  output filter, at a cost in post-summary context quality and 130–150 seconds per
  compaction. `simulate.py` can price this without touching any setting; nobody has.
- **Unmeasured compound commands** are half the rewritten bytes. Any future claim
  that rtk passes must measure them, not bound them.
- **Account-wide rate-limit utilisation** arrives as integer percentages in the
  statusline payload; a weight regression on it was ruled out as unidentifiable.

## 7. Reproduce

```bash
cd benchmarks
python3 -m token_usage.survey    <projects-root>
python3 -m token_usage.decompose <projects-root> --out <outside-repo>/decompose.json
python3 -m token_usage.replay_rtk <projects-root> --rtk <pinned-binary> \
    --work <outside-repo>/rtk-replay --out <outside-repo>/rtk-replay.json
```

Tests: `tests/python/test_token_usage_*.py`, `tests/test_session_token_stats.bats`,
`tests/test_pack_codebase.bats`.

## Related

- [Closed: Tool-Output Token Reduction](tool-output-token-reduction-closed-20260727.md) — the July closure this re-measures
- [rtk Pack Integration](rtk-pack-integration-20260726.md) — the July Phase 0 and replay
- [rtk-pack Retirement](rtk-pack-retirement-20260727.md) — the July install failure
- [Output & Token Discipline](output-token-discipline-plan-20260504.md) — where `session_token_stats.py` came from
