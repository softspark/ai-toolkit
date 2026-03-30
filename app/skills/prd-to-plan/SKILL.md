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

- Every phase must be a VERTICAL slice (all layers), never HORIZONTAL (one layer)
- No file paths or implementation details that couple to current code
- Each phase must be independently demoable
- Get user approval before writing the plan file
