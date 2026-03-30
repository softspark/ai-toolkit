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

- Minimal user interaction — investigate autonomously
- No file paths or line numbers in the issue (durability)
- TDD plan uses vertical slices, not horizontal
- File immediately — don't ask for review
