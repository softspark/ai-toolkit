---
name: triage-issue
description: "Triage a bug by deeply exploring the codebase for root cause, then create a GitHub issue with a TDD-based fix plan. Mostly hands-off — minimal user interaction. Use when user reports a bug, wants to investigate an issue, mentions triage, or wants a fix plan."
user-invocable: true
effort: high
argument-hint: "[bug description or symptom]"
agent: debugger
context: fork
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# Triage Issue

$ARGUMENTS

Investigate a bug, find root cause, and create a GitHub issue with a TDD fix plan. Mostly hands-off.

## Usage

```
/triage-issue [bug description or symptom]
```

## What This Command Does

1. **Captures** problem description (ONE question max)
2. **Explores** codebase deeply for root cause
3. **Identifies** fix approach
4. **Designs** TDD fix plan (RED→GREEN cycles)
5. **Creates** GitHub issue via `gh issue create`

## Process

### 1. Capture the Problem

Get brief description. If not provided, ask ONE question: "What's the problem you're seeing?"

Do NOT ask follow-up questions. Start investigating immediately.

### 2. Explore and Diagnose

Use Agent (subagent_type=Explore) to deeply investigate:

| Target | What to look for |
|--------|-----------------|
| Manifestation | Where the bug appears (entry points, UI, API) |
| Code path | Trace the flow from trigger to symptom |
| Root cause | Why it fails (not just the symptom) |
| Related code | Similar patterns, adjacent modules, existing tests |
| Recent changes | `git log` on relevant files |
| Working patterns | Similar code elsewhere that works correctly |

### 3. Identify Fix Approach

Determine:
- Minimal change to fix root cause
- Affected modules/interfaces
- Behaviors to verify via tests
- Classification: regression, missing feature, or design flaw

### 4. Design TDD Fix Plan

Ordered list of RED→GREEN cycles. Each cycle is one vertical slice:

- **RED**: Specific test capturing broken/missing behavior
- **GREEN**: Minimal code change to pass that test

Rules:
- Tests verify behavior through public interfaces
- One test at a time, vertical slices
- Tests must survive internal refactors
- Describe behaviors and contracts, not internal structure

### 5. Create GitHub Issue

Use `gh issue create` with template below. Share URL immediately.

## Issue Template

<issue-template>

## Problem

- What happens (actual behavior)
- What should happen (expected behavior)
- How to reproduce

## Root Cause Analysis

What was found during investigation:
- The code path involved
- Why the current code fails
- Contributing factors

Do NOT include file paths, line numbers, or implementation details. Describe modules, behaviors, and contracts.

## TDD Fix Plan

1. **RED**: Write test that [expected behavior]
   **GREEN**: [Minimal change to pass]

2. **RED**: Write test that [next behavior]
   **GREEN**: [Minimal change to pass]

**REFACTOR**: [Cleanup after all tests pass]

## Acceptance Criteria

- [ ] Criterion 1
- [ ] All new tests pass
- [ ] Existing tests still pass

</issue-template>

## Rules

- **MUST** explore the codebase for root cause before filing — symptoms masquerade as causes often
- **MUST** propose a TDD fix plan with ordered RED→GREEN cycles, each a vertical slice
- **NEVER** ask follow-up clarifying questions; one initial question maximum, then investigate autonomously
- **NEVER** include file paths, function names, or line numbers in the issue body — they go stale before the issue is picked up
- **CRITICAL**: the issue must be reproducible. If reproduction steps cannot be determined from the investigation, say so explicitly in the Problem section — do not fabricate them.
- **MANDATORY**: file the issue immediately via `gh issue create` and share the URL — do not ask the user to review a draft first

## Gotchas

- `gh issue create` without `--body` opens `$EDITOR`. In automated flows the skill hangs — always pass the body file or inline text.
- "Root cause" often turns out to be two concurrent issues. If the investigation keeps branching, file the most-probable primary cause and note the secondary as a follow-up in the same issue.
- TDD plans with more than ~5 RED→GREEN cycles usually conceal a deeper design issue. Short plans (2-3 cycles) reflect confident root-cause identification; long plans reflect fishing.
- The `debugger` agent explored autonomously but returns a narrative. Parse it for: confirmed hypothesis, code paths, and recent changes. Discard speculation.
- Bugs in framework-adjacent code (middleware, ORM hooks) require test setup that mirrors the framework's call context. A TDD plan that writes the test "like a unit test" may not actually reproduce the framework bug.

## When NOT to Use

- For a conversational bug report from a non-engineer — use `/qa-session` first, which returns refined reports this skill can then process
- For a specific reproducible error with known root cause — use `/fix` directly
- For architectural-scale problems — use `/architecture-audit`
- For creating issues from a PRD — use `/prd-to-issues`
- For debugging without filing an issue — use `/debug`
