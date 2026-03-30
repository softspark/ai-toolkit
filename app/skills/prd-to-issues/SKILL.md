---
name: prd-to-issues
description: "Break a PRD into independently-grabbable GitHub issues using vertical slices with HITL/AFK tagging and dependency ordering. Use when user wants to convert a PRD to issues, create tickets, or break down a PRD into work items."
effort: medium
disable-model-invocation: true
argument-hint: "[PRD issue number]"
allowed-tools: Read, Grep, Glob, Bash
---

# PRD to Issues

$ARGUMENTS

Break a PRD into independently-grabbable GitHub issues using vertical slices (tracer bullets).

## Usage

```
/prd-to-issues [PRD issue number]
```

## What This Command Does

1. **Fetches** PRD from GitHub issue
2. **Explores** codebase for context
3. **Drafts** vertical slices with HITL/AFK classification
4. **Quizzes** user on breakdown
5. **Creates** GitHub issues in dependency order via `gh issue create`

## Process

### 1. Locate the PRD

Fetch with `gh issue view <number>` (with comments). If no number provided, ask.

### 2. Draft Vertical Slices

Each issue is a thin vertical slice cutting through ALL layers end-to-end.

| Classification | Description |
|---------------|-------------|
| **AFK** | Can be implemented and merged without human interaction (prefer) |
| **HITL** | Requires human decision — architectural choice, design review, etc. |

### 3. Quiz the User

Present as numbered list. For each slice show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Blocked by**: which other slices must complete first
- **User stories covered**: which stories from the PRD

Ask:
- Granularity right? (too coarse / too fine)
- Dependency relationships correct?
- HITL vs AFK classification correct?
- Any slices to merge or split?

Iterate until approved.

### 4. Create GitHub Issues

Create in dependency order (blockers first) so real issue numbers can be referenced.

Use `gh issue create` with the template below for each slice.

## Issue Template

<issue-template>

## Parent PRD

#{prd-issue-number}

## What to build

Concise description of this vertical slice. End-to-end behavior, not layer-by-layer. Reference parent PRD sections, don't duplicate.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Blocked by

- Blocked by #{issue-number} (if any)

Or "None — can start immediately" if no blockers.

## User stories addressed

Reference by number from the parent PRD:

- User story 3
- User story 7

</issue-template>

## Rules

- Every issue must be a VERTICAL slice — never horizontal
- Create in dependency order for real issue number references
- Do NOT close or modify the parent PRD issue
- Do NOT ask user to review before creating — file and share URLs
- Maximize parallelism — independent issues should have no blockers
- No file paths or line numbers in issue bodies
