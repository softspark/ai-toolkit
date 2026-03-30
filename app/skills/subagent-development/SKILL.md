---
name: subagent-development
description: "Execute implementation plans using fresh subagents per task with two-stage review: spec compliance first, then code quality. Use when executing plans with independent tasks."
user-invocable: true
effort: high
argument-hint: "[plan file or task description]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
---

# Subagent Development

$ARGUMENTS

Execute implementation plans by dispatching fresh subagents per task, then running a two-stage review gate: spec compliance first, code quality second. Fresh context per subagent prevents accumulated confusion. Two-stage review catches different failure modes: spec review catches wrong behavior, quality review catches bad structure.

## Usage

```
/subagent-development [plan file or task description]
```

## Why This Works

| Property | Benefit |
|----------|---------|
| Fresh subagent per task | No accumulated context drift or confusion |
| Spec review first | Catches wrong behavior before quality review wastes time on wrong code |
| Quality review second | Catches structural issues after behavior is confirmed correct |
| Sequential tasks | No merge conflicts, each task builds on verified previous work |

## Process Flow

```
Read plan
    |
    v
Extract ordered task list
    |
    v
For each task:
    |
    +---> [1] Dispatch IMPLEMENTER subagent
    |         |
    |         v
    |     Handle status (see Status Protocol)
    |         |
    |         v
    +---> [2] Dispatch SPEC REVIEWER subagent
    |         |
    |         v
    |     APPROVED? --no--> fix issues, re-review
    |         |
    |        yes
    |         |
    |         v
    +---> [3] Dispatch QUALITY REVIEWER subagent
    |         |
    |         v
    |     Critical issues? --yes--> fix, re-review
    |         |
    |         no
    |         v
    |     Mark task complete
    |
    v
Next task (or done)
```

## Step 1 -- Read and Parse Plan

Read the plan file. Extract:

1. **Ordered task list** -- each task with description, acceptance criteria, file scope
2. **Global constraints** -- what must NOT change, architecture rules, shared conventions
3. **Dependencies** -- which tasks depend on which (execute in dependency order)

Present the task list to the user. Wait for approval before proceeding.

## Step 2 -- Execute Tasks Sequentially

For each task in order:

### 2a. Gather Context

Before dispatching the implementer, gather:

- Relevant source files the task will read or modify
- Related test files
- Any output/artifacts from previously completed tasks
- Global constraints from the plan

### 2b. Dispatch Implementer

Use the `Agent` tool with the [implementer prompt template](reference/implementer-prompt.md).

Select model based on task complexity:

| Task Type | Model | Examples |
|-----------|-------|---------|
| Mechanical | Cheapest available | Rename, move, config change, 1-2 files with clear spec |
| Integration | Standard | Wire up existing components, add endpoint using established patterns |
| Design/Complex | Most capable | New architecture, complex algorithms, cross-cutting concerns |

### 2c. Handle Implementer Status

The implementer reports one of four statuses:

| Status | Handling |
|--------|----------|
| **DONE** | Proceed to spec review |
| **DONE_WITH_CONCERNS** | Read concerns. If they relate to correctness or scope violations, address them before review. If observational only (style preference, future improvement), note them and proceed to spec review |
| **NEEDS_CONTEXT** | Provide the missing context the implementer identified. Re-dispatch with the same task plus the additional context |
| **BLOCKED** | Assess the blocker. Context problem: re-dispatch with better context. Task too complex for selected model: re-dispatch with more capable model. Plan is wrong or ambiguous: escalate to user for clarification |

### 2d. Spec Review (Stage 1)

Use the `Agent` tool with the [spec reviewer prompt template](reference/spec-reviewer-prompt.md).

The spec reviewer checks:

- All requirements from the task are implemented
- Nothing extra was added beyond the spec
- Nothing is missing
- Behavior matches acceptance criteria

If **APPROVED**: proceed to quality review.

If **issues found**: fix the issues (re-dispatch implementer with specific fix instructions or fix inline if trivial), then re-run spec review. Do not proceed to quality review until spec review passes.

### 2e. Quality Review (Stage 2)

Use the `Agent` tool with the [quality reviewer prompt template](reference/code-quality-reviewer-prompt.md).

The quality reviewer categorizes findings:

| Category | Action |
|----------|--------|
| **Critical** | Must fix before proceeding. Re-dispatch implementer or fix inline |
| **Important** | Should fix. Fix now unless time-boxed, then document for follow-up |
| **Suggestions** | Nice to have. Note for future improvement, do not block progress |

After fixing any Critical issues, re-run quality review to confirm.

### 2f. Mark Task Complete

Record:

- Task ID and description
- Files modified
- Commit SHA (if commits were made)
- Any concerns or suggestions deferred for later

## Step 3 -- Summary Report

After all tasks complete, produce:

```markdown
## Subagent Development Report

### Plan
[Plan file or description]

### Tasks Completed
| # | Task | Files Modified | Status | Notes |
|---|------|---------------|--------|-------|
| 1 | ... | ... | Done | ... |
| 2 | ... | ... | Done | ... |

### Deferred Items
- [Any "Important" or "Suggestion" issues not addressed]

### Verification
- [ ] All tasks implemented
- [ ] All spec reviews passed
- [ ] All quality reviews passed (no Critical issues remaining)
- [ ] Tests pass
```

## Model Selection Guidance

Before dispatching each subagent, assess the task:

```
Is the task mechanical (rename, config, boilerplate)?
    --> Use cheapest model

Does the task integrate existing patterns (1-3 files)?
    --> Use standard model

Does the task require design decisions or span 4+ files?
    --> Use most capable model

Is it a review task?
    --> Always use most capable model (reviews catch what implementers miss)
```

## Review Order Rule

```
Spec compliance review MUST pass BEFORE quality review starts.
```

Rationale: quality-reviewing code that does the wrong thing wastes everyone's time. Confirm the code does what was asked first, then confirm it does it well.

## Red Flags -- STOP Immediately

If you observe any of these, stop and correct course:

- **Skipping reviews**: Every task gets both reviews. No exceptions, regardless of task size
- **Proceeding with unfixed Critical issues**: Critical means critical. Fix before moving on
- **Dispatching multiple implementers in parallel**: Tasks are sequential. The next implementer needs to see the previous task's completed state
- **Implementer modifying files outside its scope**: Re-dispatch with explicit constraints
- **Review rubber-stamping**: If a reviewer approves in under 10 seconds with no specifics, the review is suspect. Re-dispatch with instructions to be thorough
- **Accumulated context**: If you find yourself passing growing context between tasks, you are doing it wrong. Each subagent gets fresh context relevant to its task only

## Checklist Per Task

```
[ ] Context gathered for this specific task
[ ] Implementer dispatched with correct model
[ ] Implementer status handled per protocol
[ ] Spec review passed (all requirements met, nothing extra, nothing missing)
[ ] Quality review passed (no Critical issues)
[ ] Task marked complete with file list and notes
```
