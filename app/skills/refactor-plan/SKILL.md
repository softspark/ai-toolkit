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

- Present >=3 alternatives before committing to an approach
- Tiny commits — each step keeps codebase working
- No file paths or code snippets in the issue (durability)
- File immediately via `gh issue create` — don't ask for review
- Interview thoroughly before planning
- **Dead code cleanup is mandatory per step, not deferred** (Constitution Art. VI.1): every refactor step must leave the repo with zero orphaned references. "We'll delete the old code in a later step" is only acceptable for transitional double-write / expand-contract phases where both paths are temporarily live — and the cleanup step must be explicitly listed in the plan, not implied.
