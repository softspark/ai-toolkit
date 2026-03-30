---
name: write-a-prd
description: "Create a Product Requirements Document through interactive interview, codebase exploration, and deep module design. Use when user wants to write a PRD, create product requirements, or plan a new feature from scratch."
user-invocable: true
effort: high
argument-hint: "[feature or problem description]"
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# Write a PRD

$ARGUMENTS

Create a PRD through structured interview, codebase exploration, and module design, then submit as a GitHub issue.

## Usage

```
/write-a-prd [feature or problem description]
```

## What This Command Does

1. **Gathers** detailed problem description from user
2. **Explores** the codebase to verify assertions and understand current state
3. **Interviews** relentlessly about every design branch until shared understanding
4. **Sketches** major modules — actively seeking deep modules (small interface, deep implementation)
5. **Writes** the PRD and submits as GitHub issue via `gh issue create`

## Process

### 1. Gather Problem Description

Ask the user for a detailed description of:
- The problem they want to solve
- Any potential ideas for solutions
- Who the users/actors are

### 2. Explore the Codebase

Use Agent (subagent_type=Explore) to understand:
- Current architecture relevant to the feature
- Existing patterns and conventions
- Integration points
- Related code that might be affected

### 3. Interview Relentlessly

Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask questions one at a time. If a question can be answered by exploring the codebase, explore instead of asking.

### 4. Sketch Modules

Identify major modules to build or modify. Look for opportunities to extract **deep modules** — modules that encapsulate significant functionality behind a simple, testable interface.

Check with the user:
- Do these modules match their expectations?
- Which modules need tests?

### 5. Write and Submit PRD

Use the template below. Submit as GitHub issue via `gh issue create`. Share the URL.

## PRD Template

<prd-template>

## Problem Statement

The problem from the user's perspective.

## Solution

The solution from the user's perspective.

## User Stories

Extensive numbered list:

1. As an <actor>, I want a <feature>, so that <benefit>

Cover ALL aspects of the feature.

## Implementation Decisions

- Modules to build/modify
- Interface designs for those modules
- Architectural decisions
- Schema changes
- API contracts

Do NOT include specific file paths or code snippets — they go stale quickly.

## Testing Decisions

- What makes a good test (external behavior, not implementation details)
- Which modules to test
- Prior art for tests in the codebase

## Out of Scope

What is explicitly NOT part of this PRD.

## Further Notes

Any additional context.

</prd-template>

## Visual Companion (Optional)

When upcoming questions will involve visual content (mockups, layouts, diagrams), offer the browser companion:

> "Some of what we're working on might be easier to explain visually. I can show mockups and diagrams in a browser. Want to try it?"

**This offer MUST be its own message.** Do not combine with other questions. Wait for response.

If accepted, start the server and use it for visual questions only. Text/conceptual questions stay in terminal.

See [reference/visual-companion.md](reference/visual-companion.md) for details.

## Rules

- Interview relentlessly — don't settle for vague answers
- No file paths or code snippets in the PRD (durability principle)
- User stories must be extensive and cover all aspects
- Submit immediately via `gh issue create` — don't ask for review
- Deep modules over shallow modules
