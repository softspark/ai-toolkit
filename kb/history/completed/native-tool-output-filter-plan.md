---
title: "Implementation Plan: Native Tool Output Filter"
category: planning
service: ai-toolkit
tags:
  - output-filter
  - hooks
  - recovery
  - performance
  - claude-code
doc_type: plan
status: completed
created: "2026-07-23"
last_updated: "2026-07-23"
completed: "2026-07-23"
completion: "100% of approved Claude Code scope; other runtimes remain manual-only by capability decision"
shipped_in: "Unreleased"
description: "Approved implementation plan and completion evidence for the original dependency-free ai-toolkit tool-output filter, including conservative profiles, exact recovery, telemetry, runtime capability gates, and adjacent repairs."
---

# Implementation Plan: Native Tool Output Filter

## Status

Completed on 2026-07-23 after user approval.

Completion evidence:

- 69 focused Python tests pass, including the production-wrapper benchmark.
- The 100-sample cold wrapper measures 63.565 ms p95 against the 75 ms gate.
- The 8 MiB profile case measures 4.354 ms p95 and 8,792,932 peak traced
  bytes against the 150 ms and 41,943,040 byte gates.
- The strict repository validator reports 44 agents, 108 skills, and 1477
  tests with zero errors or warnings.
- Ruff, mypy, ShellCheck, skill audit, generated artifacts, and the final
  repository test gate pass for the changed surface.

## Context

`ai-toolkit` currently controls assistant response length and reports real
Claude session tokens, but it does not transform live tool output before that
output reaches the model. The requested feature is an original, MIT-licensed,
dependency-free implementation inside `ai-toolkit`. RTK is research input only:
no runtime dependency, vendoring, translated code, copied filters, fixtures,
regex tables, CLI names, or configuration keys.

The first native integration targets Claude Code because current Claude hooks
support replacing successful tool output through
`PostToolUse.hookSpecificOutput.updatedToolOutput`. The transformer remains
strictly post-execution and cannot alter the command, arguments, environment,
working directory, permission decision, exit status, or signal.

This feature is separate from MCP `tools/list` description trimming. Hooks can
transform an executed tool result, but they do not intercept MCP catalog
metadata. [PATH: kb/history/completed/f2-mcp-trim-spike-20260504.md]
[PATH: kb/planning/mcp-context-trim-v4-prd.md]

Relevant local boundaries:

- Fixed lifecycle enforcement belongs in hooks. [PATH: CLAUDE.md:10]
- The current safety guards run in `PreToolUse`. [PATH: app/hooks.json:37]
- Hook runtime Python helpers are deployed explicitly.
  [PATH: scripts/install_steps/hooks.py:71]
- Runtime hook schemas differ by editor.
  [PATH: kb/reference/hooks-catalog.md:571]
- Existing output/token work intentionally uses native mechanisms.
  [PATH: kb/history/completed/output-token-discipline-plan-20260504.md]
- Claude hook contract:
  <https://code.claude.com/docs/en/hooks>

## Scope

### Included

- Python standard library implementation under `scripts/`.
- Pure post-execution transformation of successful textual Bash output.
- `off`, `observe`, and `safe` modes.
- Claude Code integration through `PostToolUse.updatedToolOutput`.
- Manual CLI for fixture inspection, status, recovery, and cleanup.
- Two initial deterministic profiles:
  - `repeat-lines`: aggregate adjacent identical non-diagnostic lines and state
    their multiplicity.
  - `tap-success`: compact valid successful TAP while retaining plan,
    directives, comments, totals, duration, and all diagnostic material.
- Byte and line savings, latency, outcome, profile ID, and profile version.
- Exact, bounded, session-scoped raw recovery when `safe` mode is enabled.
- Capability-gated adapters for additional runtimes after Phase 2.

### Excluded

- RTK binaries, libraries, source code, filters, fixtures, configuration, or
  branding.
- Command rewriting, `sh -c`, shell parsing, permission decisions, or command
  execution by the filter.
- LLM-generated summaries or network calls.
- Project-defined regex filters in the first release.
- Failed commands, non-empty `stderr`, signals, TTY/streaming output, binary or
  invalid text, pipes, redirects, security scanners, dependency audits,
  deployment, migrations, permission failures, and destructive-command
  diagnostics.
- `Read`, web results, arbitrary MCP results, and MCP `tools/list`.
- Claims that byte reduction equals billed-token or whole-session savings.

## Architecture

```text
PostToolUse payload
        |
        v
runtime adapter validates the native payload and output shape
        |
        +-- unsupported, disabled, unsafe, failed, or malformed --> no hook output
        |
        v
eligibility policy selects an explicit profile
        |
        v
pure deterministic transformer
        |
        v
invariant gate
  - mandatory facts preserved
  - no forbidden invention
  - deterministic and idempotent
  - at least 15% and 1 KiB smaller
        |
        +-- invariant failure --> exact raw passthrough + session circuit breaker
        |
        v
exact raw response written to bounded ephemeral recovery store
        |
        +-- recovery unavailable --> exact raw passthrough
        |
        v
hookSpecificOutput.updatedToolOutput
```

### Module layout

```text
scripts/
  tool_output_filter/
    __init__.py
    contracts.py
    engine.py
    hook_runtime.py
    input.py
    policy.py
    invariants.py
    recovery.py
    telemetry.py
    profiles/
      __init__.py
      repeat_lines.py
      tap_success.py
  output_filter_hook.py
  output_filter_cli.py
  benchmark_output_filter.py

app/
  hooks/
    filter-tool-output.sh
    session-end.sh
  hooks.json
  output-filter-policy.json

tests/
  fixtures/output-filter/
    repeat-basic/
    tap-basic/
    tap-diagnostic/
    ansi-adversarial/
  test_tool_output_filter.py
  test_tool_output_filter_cli.py
  test_tool_output_filter_properties.py
  test_tool_output_filter_recovery.py
  test_tool_output_filter_benchmark.py
  test_output_filter_config.bats
  test_output_filter_hook.bats

kb/reference/
  tool-output-filter.md
```

### Configuration contract

```json
{
  "toolOutputFilter": {
    "mode": "off",
    "profiles": ["repeat-lines", "tap-success"],
    "maxInputBytes": 8388608,
    "minSavingsBytes": 1024,
    "minSavingsRatio": 0.15,
    "recovery": {
      "mode": "ephemeral",
      "ttlMinutes": 60,
      "maxSessionBytes": 33554432
    }
  }
}
```

- `off`: no Python invocation and no metrics.
- `observe`: calculate an eligible result and metadata, but return no hook
  output, so the model receives the original bytes.
- `safe`: replace only output that passes every invariant and has exact raw
  recovery available.
- `AI_TOOLKIT_OUTPUT_FILTER_DISABLE=1`: global emergency bypass.
- Three consecutive runtime or invariant failures disable filtering for the
  current session and emit one bounded warning.
- All profiles remain explicit opt-in until GA evidence is reviewed.

### Recovery and privacy

- Store the exact original tool-response object, not a redacted approximation.
- Location:
  `~/.softspark/ai-toolkit/sessions/<repo-key>/output-filter/<session>/<opaque-id>`.
- Directory mode `0700`, file mode `0600`, exclusive no-follow creation,
  opaque random identifiers, atomic publication, quota, and TTL.
- Never store raw commands, paths, output, environment values, or session IDs
  in telemetry.
- Telemetry contains only profile ID/version, input/output byte and line
  counts, latency, outcome, and fallback reason.
- Session end, explicit clean, uninstall, and expired-TTL cleanup remove only
  ai-toolkit-owned recovery artifacts.
- If the platform cannot provide the secure-store contract, `safe` degrades to
  raw passthrough. It must not silently become lossy.

## Success Criteria

- [x] No new npm, pip, Cargo, system, or runtime dependency.
- [x] Shadow/observe mode is byte-identical for 100% of fixtures and native
      hook-contract test payloads.
- [x] Any exception, timeout, unsupported encoding, unknown profile, malformed
      payload, failed invariant, unavailable recovery store, non-zero exit,
      signal, or non-empty `stderr` returns the exact original output.
- [x] Every omission is marked with profile/version, original and emitted
      line counts, and an opaque exact-recovery handle.
- [x] Golden fixtures preserve 100% of declared mandatory facts and introduce
      zero non-marker facts.
- [x] Filter output is deterministic, idempotent, and never larger than raw.
- [x] Eligible fixtures achieve median reduction of at least 30%; replacement
      requires at least 15% and 1 KiB saved per call.
- [x] Hard input cap is 8 MiB; larger payloads pass through without parsing.
- [x] Algorithm p95 is at most 20 ms for 100 KiB and 150 ms for 8 MiB; cold
      end-to-end hook invocation p95 is at most 75 ms on CI reference runners.
- [x] Peak traced Python allocation is at most three times input size plus
      16 MiB.
- [x] No regex has unbounded catastrophic backtracking.
- [x] Claude Code `safe` mode is opt-in and can be disabled globally without
      reinstalling.
- [x] Additional runtimes activate only after their native result-replacement
      contract has captured fixtures and passing integration tests.
- [x] Full repository validation and test suite are green.

## Pre-Mortem

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| A profile removes a discriminating fact | High | High | Mandatory-fact fixtures, adversarial sentinels, raw recovery, one regression disables the profile |
| A runtime changes its tool-output schema | Medium | High | Versioned adapters, strict shape validation, unknown shape returns no hook output |
| Filtering hides security or failure diagnostics | Medium | High | Explicit exclusion list, successful stdout-only MVP, failures always raw |
| Recovery leaks secrets or paths | Medium | High | Exact data only in opt-in ephemeral spool, `0700`/`0600`, no-follow, quota, TTL, complete cleanup |
| Hook latency degrades normal tool use | Medium | Medium | Bash fast-path, size threshold, hard cap, benchmark gates, circuit breaker |
| Command classification mishandles shell syntax | High | Medium | No command rewriting or execution, conservative allowlist, pipes/redirects bypass |
| Regex or parser behavior is locale/version-specific | Medium | High | Independently captured multi-version fixtures; malformed/localized output passes raw |
| Concurrent sessions corrupt metrics or recovery | Medium | Medium | Per-session directories, opaque IDs, atomic writes; do not reuse global `session-edits.json` |
| Runtime adapters diverge in safety behavior | High | High | Capability matrix and one adapter at a time; no guessed compatibility |
| Scope expands into MCP catalog proxying | Medium | Medium | Keep MCP trim as a separate PRD and release boundary |

## Tasks

### Phase 1: Observable vertical slice, no output mutation (M)

Success criteria:

- Claude PostToolUse payloads are parsed by a native Python stdlib engine.
- `off` and `observe` modes cannot change model-visible output.
- Independent fixture format and semantic oracle are operational.
- No raw tool output or command is persisted.

Tasks:

- [x] Define contracts, independent fixture provenance ledger, conservative
      eligibility rules, and clean implementation boundary.
      Owner: `infrastructure-architect`.
      Files: `kb/reference/tool-output-filter.md`,
      `tests/fixtures/output-filter/README.md`.
- [x] Implement pure engine, policy, invariants, `repeat-lines` candidate, and
      `tap-success` candidate in observe-only mode.
      Owner: `backend-specialist`.
      Files: `scripts/tool_output_filter/**`.
- [x] Add manual `inspect`, `status`, recovery, and cleanup CLI.
      Owner: `backend-specialist`.
      Files: `scripts/output_filter_cli.py`, `bin/ai-toolkit.js`.
- [x] Add Claude PostToolUse adapter last in hook order and deploy the Python
      runtime package with installed hooks.
      Owner: `command-expert`.
      Files: `app/hooks/filter-tool-output.sh`, `app/hooks.json`,
      `scripts/install_steps/hooks.py`.
- [x] Add `toolOutputFilter` schema, merge, validation, and effective-policy
      materialization; fix config-lock source/version/integrity staleness and
      the Article VII reserved-number mismatch while those files are open.
      Owner: `backend-specialist`.
      Files: `scripts/schemas/ai-toolkit-config.schema.json`,
      `scripts/config_merger.py`, `scripts/config_validator.py`,
      `scripts/config_lock.py`, `app/output-filter-policy.json`.
- [x] Build unit, property, hook-contract, malformed, binary, Unicode,
      ANSI/OSC, injection, huge-line, and concurrency tests.
      Owner: `test-engineer`.
      Files: `tests/test_tool_output_filter*.py`,
      `tests/test_tool_output_filter*.bats`,
      `tests/fixtures/output-filter/**`.

Rollback/scope cut:

- Remove the owned PostToolUse entry and deployed runtime package.
- If native payload fixtures are unstable, ship only the manual inspect CLI
  and fixture oracle; do not enable the hook.

### Phase 2: Claude Code safe mode with exact recovery (L)

Dependency: Phase 1 must pass all observe-mode and performance gates.

Success criteria:

- `safe` is explicit opt-in.
- Only successful, stdout-only, allowlisted text is replaceable.
- Exact raw recovery is available before replacement is emitted.
- Every failure path is byte-identical passthrough.

Tasks:

- [x] Promote `repeat-lines` and `tap-success` only after mandatory-fact,
      idempotence, determinism, and minimum-savings gates pass.
      Owner: `backend-specialist`.
      Files: `scripts/tool_output_filter/profiles/**`,
      `scripts/tool_output_filter/invariants.py`.
- [x] Implement bounded secure ephemeral recovery and exact `recover`/`clean`
      CLI operations.
      Owner: `security-architect`.
      Files: `scripts/tool_output_filter/recovery.py`,
      `scripts/output_filter_cli.py`.
- [x] Add session circuit breaker, metadata-only telemetry, TTL/quota cleanup,
      and owned-artifact removal.
      Owner: `backend-specialist`.
      Files: `scripts/tool_output_filter/telemetry.py`,
      `app/hooks/session-end.sh`, `scripts/uninstall.py`.
- [x] Verify safety precedence and that filtering cannot emit permission
      decisions, execute output, or change original tool input/status.
      Owner: `security-auditor`.
      Files: `tests/test_tool_output_filter.py`,
      `tests/test_tool_output_filter_recovery.py`,
      `tests/test_output_filter_hook.bats`.
- [x] Add deterministic benchmark corpus and enforce latency, memory, maximum
      input, and savings thresholds.
      Owner: `performance-optimizer`.
      Files: `scripts/benchmark_output_filter.py`,
      `benchmarks/output-filter/**`.

Rollback/scope cut:

- Global disable returns the hook to observe/raw behavior immediately.
- Per-profile disable preserves other validated profiles.
- If exact secure recovery is unavailable on a platform, that platform stays
  in `observe`; no weaker recovery implementation is accepted.
- If TAP cannot meet semantic gates, release only `repeat-lines`.

### Phase 3: Capability-gated runtime expansion (L)

Dependency: Phase 2 must complete Claude safe-mode dogfooding without a
confirmed semantic loss.

Success criteria:

- Each runtime has a documented capability: native replacement, observe-only,
  manual CLI, or unsupported.
- No adapter uses command rewriting or `additionalContext` as fake replacement.
- Each active adapter has captured native payload/output fixtures.

Tasks:

- [x] Build and document the capability matrix from current runtime contracts.
      Owner: `technical-researcher`.
      Files: `kb/reference/tool-output-filter.md`,
      `kb/reference/supported-tools-registry.md`.
- [x] Classify adapters one by one and keep OpenCode, Cursor, and the remaining
      runtimes manual-only because no independently verified native
      result-replacement contract passed the release boundary.
      Owner: `command-expert`.
      Files: `scripts/generate_opencode_plugin.py`,
      `scripts/generate_cursor_hooks.py`, runtime-specific fixture files.
- [x] Fix ignored OpenCode guard block propagation before adding its filter
      adapter.
      Owner: `backend-specialist`.
      Files: `scripts/generate_opencode_plugin.py`,
      `tests/test_opencode*.bats`.
- [x] Fix Gemini invalid-settings overwrite and non-atomic write before any
      Gemini filter adapter is attempted.
      Owner: `backend-specialist`.
      Files: `scripts/generate_gemini_hooks.py`,
      `tests/test_gemini.bats`.
- [x] Add per-runtime uninstall, rollback, user-hook preservation, failure, and
      schema-drift tests.
      Owner: `test-engineer`.
      Files: `tests/test_hooks_per_editor.bats`,
      `tests/test_*hooks*.bats`.

Rollback/scope cut:

- A runtime without safe native replacement remains manual CLI or
  observe-only.
- Any runtime-specific regression removes only its owned adapter.
- Cross-runtime uniformity is not a release requirement.

### Phase 4: Documentation and GA decision (M)

Dependency: Phases 1 and 2 are mandatory; Phase 3 may remain partial.

Success criteria:

- Dogfood evidence distinguishes eligible-output byte savings from actual
  session token receipts.
- Documentation lists exclusions, recovery sensitivity, and bypass procedure.
- `safe` remains opt-in unless a separate user-approved promotion decision is
  made.

Tasks:

- [x] Review available shadow/safe evidence, false-positive and
      circuit-breaker paths, and latency. No production Claude JSONL receipt
      evidence was collected in this implementation run, so documentation
      makes no token-savings claim and `safe` remains opt-in.
      Owner: `data-analyst`.
      Files: `kb/reference/tool-output-filter.md`,
      `kb/reference/stats.md`.
- [x] Update all hook counts, architecture references, CLI help, lifecycle
      catalog, README, changelog, generated instruction surfaces, and release
      notes.
      Owner: `documenter`.
      Files: `README.md`, `CLAUDE.md`, `ARCHITECTURE.md`,
      `app/ARCHITECTURE.md`, `kb/reference/architecture-overview.md`,
      `kb/reference/hooks-catalog.md`, `CHANGELOG.md`, `AGENTS.md`,
      `llms.txt`, `llms-full.txt`, `package.json`, `plugin.json`.
- [x] Re-read the complete diff for orphaned references, dead code, missing
      behavior coverage, stale docs, and unexpected generated changes.
      Owner: `code-reviewer`.
      Files: all changed files.

Rollback/scope cut:

- Release `observe` and manual CLI only if active-mode evidence is insufficient.
- Do not promote any profile to default without separate approval.

## Dependencies

```text
Phase 1 → Phase 2 → Phase 3 → Phase 4
                   └────────→ Phase 4 if runtime expansion is deferred
```

There are no circular dependencies. Phase 1 is shippable as diagnostics,
Phase 2 as Claude-only opt-in filtering, and Phase 3 as incremental
runtime-by-runtime support.

## Verification

Focused verification:

1. `python3 -m unittest discover -s tests -p 'test_tool_output_filter*.py'`
2. `bats tests/test_output_filter_config.bats tests/test_output_filter_hook.bats`
3. `python3 scripts/benchmark_output_filter.py`
4. `shellcheck --severity=warning app/hooks/*.sh`

Repository quality gates:

1. `npm run generate:all`
2. `python3 scripts/validate.py --strict`
3. `python3 scripts/audit_skills.py --ci`
4. `npm test`
5. `git diff --check`
6. Re-read `git diff` and confirm no orphaned references, missing tests, stale
   docs, copied upstream expressions, or new external dependencies.

Expected result: every command exits `0`, focused semantic fixtures report zero
missing mandatory facts and zero forbidden inventions, active replacements meet
the savings threshold, and all unsafe paths remain exact passthrough.

## Agent Assignments

| Responsibility | Agent | Model |
|---|---|---|
| Architecture and contracts | `infrastructure-architect` | Assigned tier, no override |
| Python engine and configuration | `backend-specialist` | Assigned tier, no override |
| Hook and runtime adapters | `command-expert` | Assigned tier, no override |
| Recovery threat model | `security-architect` | Assigned tier, no override |
| Security verification | `security-auditor` | Assigned tier, no override |
| Semantic and integration tests | `test-engineer` | Assigned tier, no override |
| Performance gates | `performance-optimizer` | Assigned tier, no override |
| Runtime contract research | `technical-researcher` | Assigned tier, no override |
| Evidence analysis | `data-analyst` | Assigned tier, no override |
| Documentation | `documenter` | Assigned tier, no override |
| Final diff review | `code-reviewer` | Assigned tier, no override |

## Independent-Implementation Boundary

- Implement from this plan, local ai-toolkit requirements, native runtime
  contracts, and independently captured command outputs.
- Do not consult or copy RTK source while implementing filters.
- Do not copy or transliterate identifiers, control flow, comments, regex
  tables, filter order, fixtures, messages, configuration keys, default values,
  benchmarks, or documentation wording.
- Record the origin and rationale of each filter rule in the fixture provenance
  ledger.
- If any upstream expression is intentionally adapted, stop and perform an
  Apache-2.0 attribution and NOTICE review before continuing.
