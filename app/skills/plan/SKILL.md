---
name: plan
description: "Plan implementation with tasks and success criteria"
user-invocable: true
effort: high
argument-hint: "[goal]"
allowed-tools: Read, Grep, Glob
---

# Project Planning

$ARGUMENTS

Create a structured plan for a new project or feature.

## Usage

```
/plan [description]
```

## What This Command Does

1. **Analyzes** the request
2. **Identifies** project type and tech stack
3. **Breaks down** into tasks
4. **Creates** plan file with agent assignments

## Plan File Output

Creates a `{project-slug}.md` file in project root:

```markdown
# {Project Name} - Implementation Plan

## Overview
- **Type**: [Web App / Mobile App / API / etc.]
- **Stack**: [Tech choices]
- **Complexity**: [Low / Medium / High]

## Requirements
1. [Requirement 1]
2. [Requirement 2]

## Task Breakdown

### Phase 1: Foundation
- [ ] Task 1 (Agent: backend-specialist)
- [ ] Task 2 (Agent: database-architect)

### Phase 2: Core Features
- [ ] Task 3 (Agent: frontend-specialist)
- [ ] Task 4 (Agent: backend-specialist)

### Phase 3: Polish
- [ ] Task 5 (Agent: test-engineer)
- [ ] Task 6 (Agent: devops-implementer)

## Agent Assignment

| Task | Agent | Dependencies |
|------|-------|--------------|
| Database | database-architect | None |
| API | backend-specialist | Database |
| UI | frontend-specialist | API |
| Tests | test-engineer | All above |

## File Structure
```
project/
├── src/
└── ...
```

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

## Project Type Detection

| Keywords | Type | Primary Agents |
|----------|------|----------------|
| landing, website | Static Site | frontend-specialist |
| dashboard, admin | Web App | frontend + backend |
| api, rest | API Only | backend-specialist |
| mobile, ios, android | Mobile | mobile-developer |
| game, unity | Game | game-developer |

## PLAN MODE RULES

During planning:
- Create plan documents
- Define tasks and structure
- NO code writing
- NO file creation (except plan)

## Common Rationalizations

| Excuse | Why It's Wrong |
|--------|----------------|
| "We already know what to build" | Assumed requirements lead to rework — validate assumptions explicitly |
| "Planning is wasted time, just start coding" | Unplanned work has 3-5x more rework — 30 min planning saves days |
| "The requirements will change anyway" | Plans adapt — without one, you can't assess impact of changes |
| "It's a small feature, no plan needed" | Small features in complex systems have hidden dependencies — map them |
| "We'll figure it out as we go" | Discovery without structure leads to scope creep and missed edge cases |

## Next Steps

After plan approval:
1. Use `/orchestrate` to execute with agents
2. Or manually invoke specific agents

## KB Integration

Before planning:
```python
smart_query("project template: {type}")
hybrid_search_kb("architecture {pattern}")
```

## Related Skills
- Plan approved? → `/orchestrate` or `/workflow` to execute with agents
- Need requirements first? → `/write-a-prd` for structured product requirements
- Want to stress-test the plan? → `/grill-me` for Socratic questioning
- Ready to break into issues? → `/prd-to-plan` → `/triage-issue`
