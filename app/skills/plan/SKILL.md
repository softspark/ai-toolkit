---
name: plan
description: "Breaks down feature requests and project goals into phased implementation plans with task lists, agent assignments, dependency graphs, and success criteria. Use when the user asks to plan a feature, create an implementation roadmap, break down a coding task, or outline project phases."
user-invocable: true
effort: high
argument-hint: "[goal]"
allowed-tools: Read, Grep, Glob
---

# Project Planning

$ARGUMENTS

## Workflow

1. **Analyze scope**: read the goal, scan relevant source files to understand current state
2. **Detect project type**: match keywords to determine stack and primary agents (see table below)
3. **Break into phases**: group tasks by dependency order (foundation, core, polish)
4. **Assign agents**: map each task to the best-fit agent with explicit dependencies
5. **Write plan file**: create `{project-slug}.md` in project root using [templates/plan-template.md](templates/plan-template.md)
6. **Validate**: confirm every requirement maps to at least one task, no circular dependencies exist, and success criteria are measurable

## Project Type Detection

| Keywords | Type | Primary Agents |
|----------|------|----------------|
| landing, website | Static Site | frontend-specialist |
| dashboard, admin | Web App | frontend + backend |
| api, rest, graphql | API Only | backend-specialist |
| mobile, ios, android | Mobile | mobile-developer |
| cli, terminal | CLI Tool | backend-specialist |

## Planning Constraints

- Create plan documents only, NO code writing, NO file creation (except the plan)
- Each task must name affected file(s) and a single owning agent
- Phases must have explicit dependency edges (`Phase 1 -> Phase 2`)
- Success criteria must be verifiable (command to run, expected output, or observable behavior)

## KB Integration

Before planning:

```python
smart_query("project template: {type}")
hybrid_search_kb("architecture {pattern}")
```

## Related Skills

- Plan approved? -> `/orchestrate` or `/workflow` to execute with agents
- Need requirements first? -> `/write-a-prd` for structured product requirements
- Want to stress-test the plan? -> `/grill-me` for Socratic questioning
- Ready to break into issues? -> `/prd-to-plan` -> `/triage-issue`

## Rules

- **MUST** break work into phases where each phase is independently shippable (tracer-bullet discipline) — waterfall phases defer all risk to the end
- **MUST** define measurable success criteria per phase before proposing tasks — "the user is happy" is not a criterion
- **NEVER** write code in this skill — the output is a plan document, not a patch
- **NEVER** invent an agent; every task lists a real agent from `app/agents/` or a real skill from `app/skills/` with a reason for the choice
- **CRITICAL**: every phase has an explicit rollback or scope-cut option. A plan with no way to stop mid-project is a sunk-cost trap.
- **MANDATORY**: dependencies between phases are explicit edges (`Phase 1 → Phase 2`). Circular dependencies are always a planning bug, not a valid state.

## Gotchas

- "SMART" tasks are often too small to be strategic and too vague to be tactical. Tasks at the plan level should be phase-aligned outcomes ("authentication ships behind a feature flag"), not implementation steps ("add JWT middleware").
- Agent assignment drifts during execution — the agent named in the plan may be unavailable or wrong when the work starts. Document the **role** (`backend-specialist`) alongside the assigned agent, so a substitute is unambiguous.
- Plans that start with a Research phase often consume 80% of the timeline without producing shippable output. If research is truly needed, cap it with a timebox and a concrete artifact (ADR, spike doc).
- Dependency graphs with diamond patterns (A→B, A→C, B→D, C→D) silently serialize D. If parallel phases feel slow, check for an unintended diamond.
- Success criteria based on code metrics (coverage, lint count) incentivize gaming them. Prefer user-facing criteria (p95 latency, first-time-success rate on the happy path).

## When NOT to Use

- For writing a **PRD** (product requirements) first — use `/write-a-prd`
- For breaking a PRD into phases — use `/prd-to-plan`
- For filing issues against a plan — use `/prd-to-issues`
- For stress-testing an existing plan — use `/grill-me`
- For executing a plan with agents — use `/orchestrate` or `/workflow`
- For a refactor with incremental commits — use `/refactor-plan`
