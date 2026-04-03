---
name: orchestrate
description: "Coordinate multiple specialized agents in parallel"
user-invocable: true
effort: max
argument-hint: "[task]"
context: fork
agent: orchestrator
model: opus
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, TeamCreate, TeamDelete, SendMessage, TaskCreate, TaskList, TaskUpdate, TaskGet, TaskOutput, TaskStop
---

# /orchestrate - Multi-Agent Coordination

$ARGUMENTS

## MANDATORY: You MUST use the Agent tool

**DO NOT analyze or implement this task yourself.** Your only job is to decompose the task and invoke specialized agents via the `Agent` tool. If you attempt to do the work inline, you have failed.

## Step 1 — Decompose

Analyze the task and identify 3–6 sub-domains (e.g. backend, frontend, security, testing, docs). Define clear file ownership per domain so agents don't conflict.

Present the decomposition to the user and wait for approval before Step 2.

## Step 2 — Spawn agents in parallel (REQUIRED)

Call the `Agent` tool **multiple times in a single response** — one call per sub-domain. All independent agents MUST be launched in the same message to run in parallel.

Example for a feature implementation task:

```
Agent(subagent_type="backend-specialist", prompt="...", ...)
Agent(subagent_type="frontend-specialist", prompt="...", ...)
Agent(subagent_type="test-engineer", prompt="...", ...)
Agent(subagent_type="security-auditor", prompt="...", ...)
```

Each agent prompt MUST include:
1. The original user task
2. The specific sub-task this agent owns
3. File paths this agent is allowed to modify
4. Success criteria for this agent's work

## Step 3 — Synthesize

After all agents complete, generate the Orchestration Report combining their findings.

## Available Agents

| Agent | Domain |
|-------|--------|
| `backend-specialist` | API, server logic, databases |
| `frontend-specialist` | React, Vue, UI components |
| `test-engineer` | Unit, integration, E2E tests |
| `security-auditor` | OWASP, vulnerabilities, auth |
| `database-architect` | Schema, migrations, queries |
| `devops-implementer` | Docker, CI/CD, infra |
| `performance-optimizer` | Profiling, bottlenecks |
| `documenter` | KB, architecture notes, runbooks |
| `code-reviewer` | Code quality, patterns |
| `tech-lead` | Architecture, standards |

## Output Format

```markdown
## Orchestration Report

### Task
[Original task]

### Agents Invoked
| # | Agent | Sub-task | Files | Status |
|---|-------|----------|-------|--------|
| 1 | backend-specialist | API layer | src/api/ | Done |
| 2 | frontend-specialist | UI components | src/components/ | Done |
| 3 | test-engineer | Test suite | tests/ | Done |

### Key Findings
1. **[Agent]**: Finding
2. **[Agent]**: Finding

### Summary
[Synthesis]
```
