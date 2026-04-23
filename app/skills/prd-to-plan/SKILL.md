---
name: prd-to-plan
description: "Convert a PRD into a phased implementation plan using tracer-bullet vertical slices. Use when user wants to break down a PRD, create an implementation plan, plan phases from a PRD, or mentions tracer bullets."
user-invocable: true
effort: high
argument-hint: "[PRD issue number or paste PRD]"
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# PRD to Plan

$ARGUMENTS

Break a PRD into a phased implementation plan using vertical slices (tracer bullets). Output is a Markdown file in `./plans/`.

## Usage

```
/prd-to-plan [PRD issue number or description]
```

## What This Command Does

1. **Loads** the PRD (from GitHub issue or conversation)
2. **Explores** the codebase to understand architecture
3. **Identifies** durable architectural decisions
4. **Drafts** vertical slices (tracer bullets)
5. **Quizzes** user on granularity
6. **Writes** plan file to `./plans/`

## Process

### 1. Confirm PRD is in Context

If not provided, ask for the PRD GitHub issue number or content. Fetch with `gh issue view <number>` if needed.

### 2. Explore the Codebase

Use Agent (subagent_type=Explore) to understand current architecture, existing patterns, and integration layers.

### 3. Identify Durable Architectural Decisions

Before slicing, identify decisions unlikely to change:
- Route structures / URL patterns
- Database schema shape
- Key data models
- Authentication / authorization approach
- Third-party service boundaries

### 4. Draft Vertical Slices

Break PRD into **tracer bullet** phases. Each phase is a thin vertical slice cutting through ALL layers end-to-end.

| Rule | Description |
|------|-------------|
| Complete path | Each slice delivers narrow but COMPLETE path through every layer (schema, API, UI, tests) |
| Demoable | A completed slice is demoable or verifiable on its own |
| Thin over thick | Prefer many thin slices over few thick ones |
| Durable | Do NOT include file names, function names, or implementation details likely to change |
| Include decisions | DO include durable decisions: route paths, schema shapes, data model names |

### 5. Quiz the User

Present breakdown as numbered list. For each phase show:
- **Title**: short descriptive name
- **User stories covered**: which stories from the PRD

Ask:
- Does the granularity feel right? (too coarse / too fine)
- Should any phases be merged or split?

Iterate until approved.

### 6. Write Plan File

Create `./plans/` if needed. Write as `./plans/{feature-name}.md`.

## Plan Template

```markdown
# Plan: {Feature Name}

> Source PRD: #{issue-number}

## Architectural Decisions

Durable decisions that apply across all phases:

- **Routes**: ...
- **Schema**: ...
- **Key models**: ...

---

## Phase 1: {Title}

**User stories**: {list from PRD}

### What to build

Concise description of this vertical slice. End-to-end behavior, not layer-by-layer.

### Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2

---

## Phase 2: {Title}

(repeat for each phase)
```

## Rules

- **MUST** slice vertically — every phase cuts through all layers (schema, API, UI, tests). Horizontal layer-by-layer phases defer integration risk to the end.
- **MUST** identify Architectural Decisions **before** slicing — decisions that apply across phases live in their own section, not repeated in each phase
- **NEVER** embed file paths, function names, or implementation details that couple the plan to current code — the plan outlives the code it describes
- **NEVER** write the plan file before the user approves the slicing — drafts burn tokens and invite scope drift
- **CRITICAL**: each phase is independently demoable on its own. If phase N only makes sense in combination with phase N+1, merge them.
- **MANDATORY**: the first phase ships **end-to-end** (however thin). Deferring any layer to a later phase defeats tracer-bullet discipline.

## Gotchas

- Architectural Decisions feel like premature commitment — "we can decide routes later". In practice, every phase needs a route to hit, so postponing them creates conflicting guesses across phases. Decide once, apply everywhere.
- PRDs with long lists of user stories tempt the planner to make each story a phase. User stories are requirements, not phases — group several stories into one vertical slice when they share architecture.
- "Demoable" means an external stakeholder can watch the feature work, not that a unit test passes. If a phase only ships backend API with no UI to exercise it, it is not demoable.
- Fetching the PRD with `gh issue view <n>` captures the body but not the comments. Crucial clarifications often live in the comments — include `--comments` or remind the user to paste important threads.
- Plans written against a moving PRD (the PRD is still being edited) invalidate on every edit. Freeze the PRD snapshot at plan-write time, reference the snapshot commit or comment ID.

## When NOT to Use

- For filing GitHub issues from a plan — use `/prd-to-issues`
- For writing the PRD itself — use `/write-a-prd`
- For planning without a PRD — use `/plan` (general-purpose)
- For stress-testing a plan that already exists — use `/grill-me`
- For refactor planning — use `/refactor-plan` (incremental commits, not tracer bullets)
