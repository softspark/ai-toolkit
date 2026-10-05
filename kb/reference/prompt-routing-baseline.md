---
title: "Prompt routing baseline"
category: reference
section: reference
service: ai-toolkit
tags: [benchmark, hooks, routing, evaluation]
version: "1.1.0"
created: "2026-10-04"
last_updated: "2026-10-05"
description: "Offline B1 diagnostic baseline, dataset contract and missing evidence for prompt routing evaluation."
---

# Prompt routing baseline

**B1 status: preparation complete, evaluation Inconclusive.** The repository
contains 20 synthetic diagnostic cases, not the required 100–200 independently
labeled natural prompts. These cases demonstrate specific behaviors; their
error rate cannot establish a representative G-ROUTE result. Targeted fixes
after 5.2.0 address reproduced PL/EN boundary and marked-quote errors, while the
historical measurements below retain their original source identity. This
implements the B1 preparation in rag-mcp's
`kb/planning/rag-reranker-and-toolkit-routing-plan-20261003.md`.

## Targeted corrections in 5.2.1

Version 5.2.1 fixes reproduced reminder-classification errors without adding
a model, telemetry, network request, `plan`/`review` output category or skill
suggestion. `_prompt-intent.py` applies Unicode-aware PL/EN boundaries and ignores
marked quotes/pastes. Architecture still precedes debug, and the original
prompt still controls the independent search-required flag. The
[hook catalog](hooks-catalog.md) defines the supported markers and limitations.

The first 17 targeted regressions produced 12 failures against the released
hook and passed after the fix. The final 23 regressions also cover punctuation,
known slash commands, multiple-backtick inline code, explicit XML paste wrappers,
Python import isolation and generic fallback when the helper fails. Five
installation-path checks exercise the delivered helper rather than source alone.

On the unchanged 20-case public diagnostic, the current source produces 14/20
expected categories versus the baseline's 6/20. Five remaining cases expect
`plan` or `review`, which this compatibility-preserving fix does not introduce.
One remaining case uses an unmarked prose quotation, outside the supported
marker contract. The diagnostic was used during development, so this is bug-fix
evidence, not an independently held-out G-ROUTE result.

One sequential run on 2026-10-05 measured whole-process p50 54.274 ms and p95
57.999 ms. It does not pass the proposed 50 ms qualification threshold; host
timing and representative quality still require their separate evaluation.
Private natural-prompt drafts and their predictions remain outside Git and
were not used to tune these changes.

## Baseline behavior in 5.2.0

In 5.2.0, `app/hooks/user-prompt-submit.sh` emits architecture, debug or generic
context. This benchmark maps generic context to `none`; `plan` and `review`
remain separate expected categories so their absence is visible in the matrix.
The hook gives architecture substring matches priority over debug matches. It
has no Polish vocabulary, word boundaries, explicit slash-command precedence,
paste exclusion or suggested skill. These are observations for B2, not changes
made by the benchmark.

`PROMPT_IS_QUESTION=0` suppresses the search-required flag for notification
prefixes and single tokens. It does **not** suppress the later category context.
`<task-notification>error…` still gets debugging context. A token containing
`debug` does too. `track-usage.sh` counts user slash commands, not actual model
Skill calls; both suggestion accuracy and actual model selection accuracy are
reported as unavailable, never as zero errors.

Sources: [hook catalog](hooks-catalog.md),
`app/hooks/user-prompt-submit.sh`, `app/hooks/track-usage.sh`.

## Reproduce offline

From the ai-toolkit repository root, with Python 3.10+, Bash and jq installed:

```bash
python3 scripts/benchmark_prompt_routing.py --repeats 3
python3 scripts/benchmark_prompt_routing.py --profile minimal --repeats 3
python3 scripts/benchmark_prompt_routing.py --dataset /private/path/labeled-prompts.json --repeats 3
```

The runner executes the actual hook in a temporary home and working directory,
with a fresh environment, `AI_TOOLKIT_SEARCH_FIRST=off` and JSON context output.
It does not read session logs, invoke models, install telemetry, call retrieval,
or write to the real user state directory. This controls category measurement;
it excludes production search-provider detection and search flag writes from
the latency scenario. Audit the hook again before running a future revision;
the runner is process isolation for state, not an OS network sandbox.

Each case runs 1–5 times (default 3), with a two-second per-process timeout.
Datasets are bounded to 1000 cases, 10 MB and 100,000 characters per prompt.
The p50/p95 values use nearest rank over whole-process wall times, including
Bash startup and JSON I/O. Processes are fresh, sequential and have no model
cold/warm distinction. Repeats improve timing samples, not category sample size.
Unexpected hook output or non-deterministic categories fail the run. Minimal
profile requires silence and never receives a category accuracy score.

JSON output contains aggregates, zero-based mismatch indices and source hashes.
It contains no prompt text, raw hook output, dataset path or custom case IDs.
Keep natural datasets and their reports outside Git. The only checked-in prompts
are deliberately authored public synthetic fixtures.

## Dataset contract and remaining evidence

The JSON root requires `schema_version: 1`, `origin: "synthetic" | "natural"`,
`labels: "developer" | "independent"`, and a nonempty `cases` array. Each case
requires:

| Field | Values |
|---|---|
| `prompt` | Exact submitted text; empty string is valid |
| `expected_category` | `architecture`, `debug`, `plan`, `review`, `none` |
| `expected_skill` | Skill name or JSON `null` for no matching skill |
| `language` | `pl`, `en`, `mixed`, `neutral` |

Use [the synthetic fixture](../../benchmarks/prompt-routing/diagnostic.json) as a
schema example. Provenance fields are declarations, not independently verified
evidence. The runner always reports Inconclusive because it measures a baseline,
not candidate improvement. A human must check dataset independence, relevance,
privacy and separation of calibration/final evaluation before freezing G0-eval.

Still needed: 100–200 anonymized natural PL/EN prompts with independent category
and skill labels, at least 20 with no matching skill, explicit commands,
notifications and pasted content; separate calibration/final sets; and
consented, separately observed model Skill selections. The original preparation
did not read private session logs. A subsequent 100-case local review draft was
prepared outside Git on 2026-10-05; its labels remain unreviewed and its filtered
selection does not meet this evaluation contract. No private prompt text or
natural-data report is committed here, and no live model inference was run.

Quoted-text fixture 16 uses a Markdown fence and is covered by the current marker
contract. Fixture 15 is an unmarked prose quotation and remains a diagnostic
slice outside that guarantee. The [hook catalog](hooks-catalog.md) names the
recognized formats; client-specific paste metadata is not assumed.

## Diagnostic measurement, 2026-10-04

Baseline source SHA: `62990cfd9dab31e02cdb50dd38456c8555616795`.
Platform: Darwin 25.6.0 arm64; Python 3.14.7. Hook SHA-256:
`830a51637b45634041e72b24ccf25e95131d767d48666d1b7169eb26f16f9238`.
Dataset SHA-256:
`a09f767e9eed417f684e5c270b04c2566ab16a58436eb7444bee68c2a94b5adb`.
The baseline records hashes for the three sourced shell helpers. Current runs
also record `_prompt-intent.py`, so classifier changes invalidate the recorded
implementation identity even when the shell entry point is unchanged.

The 20 cases comprise 12 EN, 5 PL, 2 mixed and 1 neutral; 9 expect no skill.
The first three reproduce the architecture/debug/generic prompts already in
`tests/test_hooks.bats`; the remaining authored cases probe planned behavior.
Labels were written by the benchmark author, not independent annotators.

| Measurement | Standard | Minimal |
|---|---:|---:|
| Correct categories / cases | 6 / 20 | Not applicable |
| Diagnostic category accuracy | 30% | Not applicable |
| False architecture classifications | 5 | Not applicable |
| False debug classifications | 3 | Not applicable |
| Whole-process p50 | 37.121 ms | 7.523 ms |
| Whole-process p95 | 47.159 ms | 8.715 ms |
| Timing samples | 60 | 60 |
| All output silent | Not applicable | Yes |

Confusion matrix, expected rows and emitted columns:

| Expected | architecture | debug | plan | review | none |
|---|---:|---:|---:|---:|---:|
| architecture | 1 | 0 | 0 | 0 | 1 |
| debug | 0 | 2 | 0 | 0 | 1 |
| plan | 0 | 0 | 0 | 0 | 2 |
| review | 1 | 0 | 0 | 0 | 2 |
| none | 4 | 3 | 0 | 0 | 3 |

The descriptive Wilson 95% interval is 14.55–51.90%; it does not turn these
selected synthetic cases into a population estimate. The observed p95 is for
this controlled host run only, not proof of meeting the production 50 ms gate.
A separate reviewer run with `--repeats 1` reproduced 6/20 and both hashes but
measured p95 57.132 ms over 20 timing samples. It is a separate observation, not
pooled with the 60-sample run, and reinforces the need for a frozen timing protocol.
No candidate, natural-prompt baseline or model skill-selection improvement has
been measured. G-ROUTE remains Inconclusive.

## Verification of B1 preparation

On 2026-10-04, focused Python tests passed (12), the existing hook/editor Bats
tests passed (199), the full Python suite passed (723), repository `lint:py`
passed, and strict mypy passed for the new runner. The repository validator
passed again with zero errors and warnings after concurrent unrelated CLI changes
(74 KB documents and 1,954 Bats tests in the current inventory).
The new Python files also passed the broader inherited Ruff rules.

```bash
python3 scripts/validate.py --strict
uv run --no-project --with 'pytest>=8,<10' --with 'mypy>=1.10,<3' python -m pytest tests/python
bats tests/test_hooks.bats tests/test_hooks_per_editor.bats
npm run lint:py
mypy --strict scripts/benchmark_prompt_routing.py
npm test
```

The first full Bats run enumerated 1,953 tests and exited 1. Its captured output showed
`README badges match ground truth` failing while unrelated `claude-switch`
changes increased the test count during this work; the output was truncated,
so this report does not claim that was the only failure. Those concurrent edits
were preserved. The badge was subsequently updated by that concurrent work;
the focused badge test passed when the coordinator reran it.

A complete coordinator run then isolated two npm-pack failures: invoking the
new npm by absolute path still let nested commands resolve the old system npm.
Both tests passed with the Node 22 bin directory prepended to `PATH`. The final
full run used that same environment and passed **1,954/1,954 Bats tests**, exit 0.
Its log is `/private/tmp/rag-routing-ai-toolkit-bats-node22-20261004.log`.
These results cover the shared working tree, including concurrent CLI changes;
they are not evidence bound to a new release commit.

Unqualified `ruff check .` still has findings on existing files under inherited
broader rules. The repository's documented lint command and the new files pass;
this is not a claim that every existing file passes the broader configuration.

The system npm 6.7 did not execute scripts correctly with Node 22. For the final
lint/full Bats environment, Node 22.22.2's bin directory must come first in `PATH`,
so subprocesses also resolve npm 11.13.0 from that installation.
The local system Python lacked pytest; the Python suite used an isolated uv
environment. A requested coverage-tool environment was canceled before launch;
coverage was not measured. No coverage percentage or completed evaluation is
claimed.
