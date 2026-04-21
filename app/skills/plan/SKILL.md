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
