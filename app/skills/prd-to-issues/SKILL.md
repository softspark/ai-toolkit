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

- **MUST** slice vertically — every issue cuts through schema, API, UI, tests end-to-end. Horizontal slices (all-schema, then all-API) defer integration risk.
- **MUST** create issues in dependency order so blockers have real issue numbers to reference
- **NEVER** close or modify the parent PRD issue — it is the reference anchor for every child issue
- **NEVER** include file paths, line numbers, or function names in issue bodies — they go stale before the issue is picked up
- **CRITICAL**: maximize parallelism. Independent issues have zero `Blocked by` entries; if every issue has blockers, the slicing is wrong.
- **MANDATORY**: every issue lists the user stories it addresses by number from the parent PRD — traceability matters more than brevity

## Gotchas

- `gh issue create` opens `$EDITOR` without `--body` or `--body-file`. In automation, this hangs silently. Always pass the body explicitly.
- Dependency chains longer than 3 hops (A blocks B blocks C blocks D) almost always mean the slicing is too thin. Collapse the chain into fewer, wider slices.
- GitHub issue numbers increment globally in the repo. Creating 5 issues with forward references (#124 blocks #125) requires the blocker to land before the blocked — order matters, and a mid-batch failure leaves dangling references.
- AFK issues (no human interaction) appear attractive but the label is aspirational. Real AFK requires green CI, clear acceptance criteria, and no design ambiguity — misclassifying HITL as AFK creates reopens.
- User stories referenced by "number from the PRD" drift if the PRD gets edited. Quote the story text inline if it is short, or pin to a PRD anchor (`#issue-42 > User Story 7`) to resist drift.

## When NOT to Use

- For breaking a PRD into a **plan** (phases, no issues yet) — use `/prd-to-plan`
- For writing the PRD itself — use `/write-a-prd`
- For filing a single bug — use `/qa-session` or `/triage-issue`
- For a plan that exists but has no PRD — use `/plan` then revisit this skill
- For triaging existing issues (not creating new ones) — this skill is create-only
