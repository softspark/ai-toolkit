---
name: refactor-plan
description: "Create a detailed refactor plan with tiny commits via user interview, then file as a GitHub issue RFC. Use when user wants to plan a refactor, create a refactoring RFC, or break a refactor into safe incremental steps."
user-invocable: true
effort: high
argument-hint: "[area or module to refactor]"
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# Refactor Plan

$ARGUMENTS

Create a detailed refactor plan with tiny commits via user interview, filed as a GitHub issue.

## Usage

```
/refactor-plan [area or module to refactor]
```

## What This Command Does

1. **Gathers** detailed problem description from user
2. **Explores** the codebase to verify assertions
3. **Presents** alternative approaches (>=3 options)
4. **Interviews** about implementation details
5. **Checks** test coverage of affected area
6. **Breaks** into tiny commits (Martin Fowler: each step keeps codebase working)
7. **Files** as GitHub issue via `gh issue create`

## Process

### 1. Gather Problem

Ask for detailed description of:
- The problem they want to solve
- Potential ideas for solutions

### 2. Explore Codebase

Use Agent (subagent_type=Explore) to verify assertions and understand current state.

### 3. Present Alternatives

Present >=3 alternative approaches. Discuss trade-offs.

### 4. Interview

Detailed interview about chosen approach. Hammer out exact scope — what changes, what doesn't.

### 5. Check Test Coverage

Explore existing test coverage for the affected area. If insufficient, ask about testing plans.

### 6. Break into Tiny Commits

Each commit:
- Leaves the codebase in a working state
- Is the smallest possible step
- Can be reviewed independently

### 7. File GitHub Issue

Use `gh issue create` with template below. Share URL immediately.

## Issue Template

<refactor-plan-template>

## Problem Statement

The problem from the developer's perspective.

## Solution

The solution from the developer's perspective.

## Commits

Detailed plan in plain English, broken into the tiniest commits possible. Each commit leaves the codebase working.

## Decision Document

Implementation decisions made:
- Modules to build/modify
- Interface changes
- Architectural decisions
- Schema changes
- API contracts

Do NOT include file paths or code snippets — they go stale.

## Testing Decisions

- What makes a good test (external behavior, not implementation details)
- Which modules to test
- Prior art for tests in the codebase

## Out of Scope

What is explicitly NOT part of this refactor.

</refactor-plan-template>

## Rules

- **MUST** present >=3 alternative approaches with trade-offs before committing to one
- **MUST** break the refactor into commits small enough to roll back individually — a commit that cannot be reverted is not tiny
- **MUST** verify test coverage of the affected area before planning; insufficient coverage is a blocker, not a warning
- **NEVER** embed file paths, code snippets, or function names in the issue body — the plan outlives the code
- **NEVER** ask for review after creating the issue — file it immediately, share the URL, iterate in comments
- **CRITICAL**: dead-code cleanup is **per step**, not deferred (Constitution Art. VI.1). "We'll delete the old code later" is only acceptable during explicit expand-contract phases, and the cleanup step must be in the plan.
- **MANDATORY**: the Out of Scope section names what is NOT part of this refactor — scope clarity prevents reviewer confusion

## Gotchas

- "Tiny" is relative to the reviewer's context. A 20-line commit that touches the hot path is not tiny in practice — tiny means **tractable**, not short.
- Tests for refactors are often omitted with "the existing tests cover it". Verify by running the suite with coverage in the affected area, not by asking.
- Rebasing a long chain of tiny commits is painful when the target branch moves. Recommend landing the chain weekly and rebasing on `main` before each review round.
- GitHub issue RFCs tend to get stale if the refactor drags. Add a "Status" line that updates with each landed commit so readers see progress without scrolling through comments.
- Expand-contract refactors with double-writes silently leak cost — both paths are live, both pay resources. Set a hard deadline in the plan for when the old path is removed.

## When NOT to Use

- For **executing** a refactor directly — use `/refactor`
- For architecture-level audit without a specific refactor in mind — use `/architecture-audit`
- For creating a PRD (product requirements) — use `/write-a-prd`
- For a plan without the GitHub RFC step — use `/plan` or `/plan-writing`
- For interface design of a single module — use `/design-an-interface`
