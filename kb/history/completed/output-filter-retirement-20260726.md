---
title: "Retirement: Native Tool-Output Filter — Measured 0% and Removed"
category: planning
service: ai-toolkit
tags:
  - output-filter
  - token-reduction
  - postmortem
  - measurement
  - claude-code
doc_type: postmortem
status: completed
created: "2026-07-26"
last_updated: "2026-07-26"
shipped_in: "v4.17.0 (removal)"
description: "Why the native tool-output filter shipped in v4.16.0 was removed in v4.17.0: measured 0.0000% whole-session token saving on real traffic, because agent-issued commands are compound and the design accepted only simple registered shapes."
---

# Retirement: Native Tool-Output Filter

**Shipped:** v4.16.0 (2026-07-23). **Removed:** v4.17.0 (2026-07-26).

## The number

Measured whole-session input-token saving: **0.0000%**.

Real Bash results from local Claude Code transcripts were replayed through the
shipped classifier and the full filter registry. The filters ran on the actual
captured output; this is a measurement, not an estimate.

| Scope | Value |
|---|---:|
| Transcripts replayed | 134, across 22 distinct projects |
| Successful Bash results | 7600 |
| Of those, parsed as a simple command shape | 145 (1.9%) |
| Of those, matched a registered shape | 18 (0.24%) — 16 `git diff`, 2 `git show` |
| Accepted by any filter | **0** |
| Bytes saved | **0** |

The classifier was verified working before the result was accepted: `git
status`, `git log -n 20`, `pytest -v`, `bats --tap`, and `npm test` each
produced exactly one candidate. The zero is real.

## Why: the premise, not the implementation

Seventeen filters were correct. They cleared their byte floors on owned
fixtures (44–95% reduction), stayed inside every latency budget at the 8 MiB
engine cap, passed adversarial safety review, and never once compressed a
failure. None of that mattered, because the commands they were built for are
not the commands that get issued.

95% of successful Bash invocations are compound. The byte pool breaks down as:

| Class | Share of compound bytes | Why the filter refused it |
|---|---:|---|
| `;` chain | 44.3% | multiple output producers, attribution ambiguous |
| multiline script | 29.1% | rejected at the raw-string boundary |
| pipeline | 12.7% | the pipe transformed the output |
| `&&` chain with producing segments | 5.6% | multiple output producers |
| redirect, substitution | 4.4% | rejected at the raw-string boundary |
| heredoc | 3.5% | rejected at the raw-string boundary |

Every one of those refusals was the correct safety decision in isolation.
Together they excluded the entire population.

The most-frequent single shape was `cd <path> && …`, at 375 results and 480 KB.
A bounded `cd`-prefix subset had already been designed, threat-modelled, and
measured during Phase 3, and it was dropped because it covered 0.00% of the
compound pool. The retirement measurement confirms why: of those 375 results,
only 5 had a single simple second segment, and those 5 produced 0 bytes of
output.

## What was already rejected on the way, and still stands

- **Read-result coverage: rejected on the `Edit` exact-match hazard.** On
  670.7 KB of real Read content, adjacent-duplicate collapse saves 0.00%,
  blank-run collapse 0.04%, trailing-whitespace 0.00%. Anything above noise
  requires elision, and 80.7% of `Edit` old-strings target a file read earlier
  in the same session, 63.4% of them multi-line byte-exact quotes. A Read
  result asserts what is on disk, so omission is a false claim rather than a
  summary.
- **Compound-command subset: designed, measured at 0.00% coverage, dropped.**
  The pipeline-truncator shape failed on an inversion: a truncated document
  parses cleanly exactly where the shape would pay, and rejects exactly where
  truncation is detectable.

## The process lesson

The plan validated its **design** exhaustively across five phases and its
**premise** not at all until the fifth. Fixtures measured the filter; only real
traffic measured the value, and the two disagreed by two orders of magnitude.

The end-to-end replay that produced the 0% took under an hour and could have
run on day one, before any filter existed. Any future plan of this shape must
put premise validation in Phase 0, with a kill number published before the
measurement rather than argued after it.

## Evaluated as a replacement: rtk

`rtk` (https://github.com/rtk-ai/rtk, Apache-2.0) rewrites commands at
`PreToolUse` rather than filtering output afterwards, which is the mechanism
this project's own safety contract had excluded. Its rewrite pipeline was
ported and validated against 197 of its own test assertions (197/197 exact
agreement), then applied to the same traffic:

- addresses **31.5%** of successful Bash bytes, **9.7%** of all tool-result
  bytes — genuinely non-zero, so the in-house 0% was a coverage failure rather
  than a law of nature;
- projected saving is **0.32–0.48%** of session input tokens on rtk's own
  60–90% claim, and **0.15–0.21%** once its filters' actual behaviour is
  modelled;
- its two largest families here under-deliver: `rtk read` returns files
  verbatim at the default `--level none`, and `rtk grep` models at 12.3%
  against a claimed 75%;
- custom TOML filters, the documented extension point, would reach 1.91% of
  Bash bytes. The large misses are structurally unreachable from config:
  `| head` and `| tail` (34.6%) are blocked by the pipeline-final rule, and
  `sed` (19.4%) sits in the hard-ignored prefix list.

Not adopted.

## Where the tokens actually are

The measurement points somewhere other than command output. In this traffic,
`Read` is 53.8% of tool-result bytes, and within Bash the two largest buckets
are `sed` used as a file reader (16.2%) and `| head` / `| tail` pipeline tails
(34.6%). Those are file-reading patterns, not tool reports. Any future attempt
at token reduction should start there, and should start by measuring.
