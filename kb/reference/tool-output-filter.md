---
title: "Native Tool Output Filter"
category: reference
service: ai-toolkit
tags: [output-filter, hooks, recovery, telemetry, claude-code]
version: "1.0.1"
created: "2026-07-23"
last_updated: "2026-07-24"
description: "Contract, configuration, safety boundaries, recovery, CLI, and runtime support for the native ai-toolkit output filter."
---

# Native Tool Output Filter

## Overview

ai-toolkit includes an original, dependency-free filter for selected
post-execution tool results. It is disabled by default and does not depend on,
vendor, execute, or copy another output-filter package.

The active adapter targets Claude Code because its `PostToolUse` contract can
replace a native tool response through
`hookSpecificOutput.updatedToolOutput`. The replacement object retains the
native response shape and changes only `stdout`. See the
[Claude Code hooks reference](https://code.claude.com/docs/en/hooks).

The filter never changes the command, arguments, environment, working
directory, permission decision, exit status, or signal. [PATH:
scripts/tool_output_filter/hook_runtime.py] [PATH:
scripts/tool_output_filter/engine.py]

## Modes

| Mode | Model-visible result | Recovery | Telemetry |
|------|----------------------|----------|-----------|
| `off` | Original | None | None |
| `observe` | Original | No raw response | Content-free decision metadata |
| `safe` | Replacement only after every gate passes | Exact native response saved first | Content-free decision metadata |

`off` is a shell fast path, so the Python runtime is not started. Any runtime
error, malformed payload, unsafe command, failed invariant, unavailable secure
storage, or insufficient saving leaves the original response unchanged.

Three consecutive profile, invariant, or recovery safety failures open a
persistent session-scoped circuit breaker. One bounded Claude system message
reports the bypass, then later results stay unchanged for that session.

## Configuration

Configure the project in `.softspark-toolkit.json`:

```json
{
  "toolOutputFilter": {
    "mode": "observe",
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

Run `ai-toolkit install --local` or `ai-toolkit update --local` to materialize
the effective policy as:

```text
<project>/.claude/ai-toolkit-output-filter.json
<project>/.claude/.ai-toolkit-output-filter.owner
```

The managed files use mode `0600`. The hook accepts a project policy only when
the project root is registered in `~/.softspark/ai-toolkit/projects.json`
**and** the regular owner marker matches ai-toolkit. Registration is the
security boundary: the owner marker is a public constant, so requiring the
registry stops a cloned or untrusted checkout from self-enabling filtering by
committing its own marker. An unregistered project, a missing or foreign
marker, or a symlinked project root or `.claude` directory falls back to the
installed global policy at
`~/.softspark/ai-toolkit/hooks/output-filter-policy.json`, which defaults to
`off`. [PATH: app/hooks/filter-tool-output.sh] [PATH:
scripts/install_steps/ai_tools.py]

`jq` is a required system dependency for the lifecycle hooks and is verified
by `python3 scripts/check_deps.py` alongside `python3`, `git`, and `node`.

Before executing anything, the hook validates the resolved Python runtime path:
it must be a readable regular file and must not be a symlink. A missing,
non-regular, unreadable, or symlinked runtime makes the hook exit silently and
leave the tool response unchanged, so a tampered or half-installed runtime
cannot be invoked. The same regular-file rule applies to every policy file the
hook reads. [PATH: app/hooks/filter-tool-output.sh]

Set `AI_TOOLKIT_OUTPUT_FILTER_DISABLE=1` for an immediate bypass without
reinstalling. `AI_TOOLKIT_OUTPUT_FILTER_POLICY` may point the hook to an
explicit regular policy file for controlled operational testing. When
exercising the hook manually this way, pre-create the per-repository session
base `~/.softspark/ai-toolkit/sessions/<repo-key>/` (mode `0700`) first: the
engine never creates that base itself (in live sessions the lifecycle hooks
do), and without it `safe` mode silently returns the original response. The hook is
also skipped by the `minimal` hook profile and may be listed in
`AI_TOOLKIT_DISABLED_HOOKS`. `AI_TOOLKIT_OUTPUT_FILTER_HOOK_RUNTIME` is reserved
for controlled runtime testing; the manual and cleanup CLI remains
`output_filter_cli.py`.

## Eligibility

The Claude adapter considers only a completed `PostToolUse` event with:

- tool name `Bash`;
- a non-empty native session ID of at most 160 ASCII letters, digits,
  underscores, or hyphens;
- string `stdout`;
- empty `stderr`;
- `interrupted: false`;
- `isImage: false`;
- a command that matches a strict allowlist for test, lint, typecheck, or
  validation tools;
- input at or below 8 MiB;
- valid text without binary or terminal-control content.

The following always pass through unchanged:

- failed, interrupted, image, binary, invalid-text, TTY, or streaming results;
- pipes, redirects, shell chaining, substitutions, and multiline commands;
- deployment, release, migration, publish, destroy, audit, and security-scanner
  commands;
- arbitrary Python scripts and unknown command shapes;
- output with non-empty stderr;
- unknown profiles or native payload shapes;
- candidates that save less than both the configured byte and ratio threshold.

The command classifier is eligibility logic only. It never parses and
re-executes a command. [PATH: scripts/tool_output_filter/hook_runtime.py]

## Profiles

### `repeat-lines`

Collapses only adjacent identical, non-diagnostic lines. It retains the first
line and adds a versioned marker with the exact number of omitted copies.
Warnings, failures, permissions, security diagnostics, blank lines, comments,
existing filter markers, and control-bearing output are not collapsed.

### `tap-success`

Accepts only a strict, complete, successful TAP stream with a single plan and
contiguous `ok` result numbers. It retains the TAP version, plan, directives,
comments, totals, duration, and other summary lines. Diagnostics, `not ok`,
non-zero failure summaries, malformed plans, gaps, duplicates, and unknown
content reject the whole profile.

Both profiles are deterministic and idempotent. A safe replacement must remain
smaller after the recovery marker is added. [PATH:
scripts/tool_output_filter/profiles/] [PATH:
tests/test_tool_output_filter_properties.py]

## Exact Recovery and Privacy

Before `safe` mode emits a replacement, it stores and reloads the complete
native tool-response object. Equality must succeed before the hook prints
`updatedToolOutput`.

```text
~/.softspark/ai-toolkit/sessions/<repo-key>/
└── output-filter/
    └── <hashed-session>/
        ├── <opaque-handle>.json
        ├── .circuit-state.json
        └── .telemetry.jsonl
```

Recovery directories use `0700`; response, state, and telemetry files use
`0600`. Creation and cleanup use pinned directory descriptors, no-follow
operations, atomic publication, opaque random handles, a per-session quota,
and TTL cleanup. If this secure contract is unavailable, `safe` mode returns
the original response.

The replacement ends with a marker similar to:

```text
[ai-toolkit-output-filter repeat-lines/v1; original_lines=500; emitted_lines=3; recovery=<opaque-handle>]
```

The recovery file can contain everything returned by the tool, including
secrets. Treat the session directory as sensitive. Telemetry never stores raw
output, commands, paths, environment values, session IDs, or recovery handles.
It contains only profile/version, input/output byte and line counts, latency,
outcome, and a bounded fallback reason.

Session end, explicit cleanup, and global uninstall remove only validated
ai-toolkit-owned filter artifacts. Foreign files and directories are
preserved. [PATH: scripts/tool_output_filter/recovery.py] [PATH:
app/hooks/session-end.sh] [PATH: scripts/uninstall.py]

## CLI

Inspect candidate savings without changing output:

```bash
some-test-command | ai-toolkit output-filter inspect --profile repeat-lines
some-tap-command | ai-toolkit output-filter inspect --profile tap-success
```

The JSON report contains counts, eligibility, outcome, and fallback reason. It
does not echo stdin.

Inspect the effective trusted project or global policy:

```bash
ai-toolkit output-filter status
ai-toolkit output-filter status --policy /path/to/materialized-policy.json
```

Recover the exact native response object using the handle printed in a safe
replacement:

```bash
ai-toolkit output-filter recover <opaque-handle>
```

The default lookup derives the current repository session directory. Advanced
or test workflows can add `--base-directory PATH` or `--session-id ID`.

Clean the ending session, expired exact responses, or all filter artifacts for
the current repository:

```bash
ai-toolkit output-filter clean --session-id <native-session-id>
ai-toolkit output-filter clean --session-id <native-session-id> --expired
ai-toolkit output-filter clean
```

`--expired` requires `--session-id`. Cleanup prints only the removed artifact
count and scope.

## Runtime Capability Matrix

| Runtime | Active result replacement | Capability |
|---------|---------------------------|------------|
| Claude Code | Yes, opt-in | Native `PostToolUse.updatedToolOutput` adapter |
| Claude Chat / Cowork | No | Plugin export explicitly excludes the Claude Code-only hook |
| Cursor | No | Manual `output-filter inspect` only |
| Windsurf / Devin | No | Manual `output-filter inspect` only |
| GitHub Copilot | No | Manual `output-filter inspect` only |
| Gemini CLI | No | Manual `output-filter inspect` only |
| Cline | No | Manual `output-filter inspect` only |
| Roo Code | No | Manual `output-filter inspect` only |
| Aider | No | Manual `output-filter inspect` only |
| Augment | No | Manual `output-filter inspect` only |
| Google Antigravity | No | Manual `output-filter inspect` only |
| Codex CLI | No | Manual `output-filter inspect` only |
| OpenCode | No | Manual `output-filter inspect` only |

An editor hook, extra context message, or command wrapper is not treated as
result replacement. A new adapter requires a verified native replacement
contract and dedicated native payload tests.

## Benchmark Semantics

Run the deterministic offline corpus:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/benchmark_output_filter.py
```

The benchmark measures profile p95 latency, production Bash-wrapper latency
with a fresh Python process per sample in one native session, traced peak
allocation, and eligible-output byte reduction. It uses 100 samples by default
to avoid a one-sample p95 swing. The current gates are:

- at least 30% candidate byte reduction;
- at most 20 ms p95 for profile inputs up to 100 KiB;
- at most 150 ms p95 for the 8 MiB profile case;
- at most 75 ms p95 for a cold end-to-end hook process;
- peak traced allocation no greater than three input sizes plus 16 MiB.

Byte reduction is not billed-token savings and is not a whole-session cost
claim. Measure actual model token receipts separately before changing the
default mode. [PATH: scripts/benchmark_output_filter.py] [PATH:
benchmarks/output-filter/]

## Related

- [Hooks Catalog](hooks-catalog.md)
- [Supported Tools Registry](supported-tools-registry.md)
- [Architecture Overview](architecture-overview.md)
- [Output Token Discipline Plan](../history/completed/output-token-discipline-plan-20260504.md)
