---
name: orchestrate
description: "Coordinates multiple specialized agents in parallel. Triggers: orchestrate, multi-agent, parallel agents, coordinate agents."
user-invocable: true
effort: high
argument-hint: "[task]"
context: fork
agent: orchestrator
model: opus
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, TeamCreate, TeamDelete, SendMessage, TaskCreate, TaskList, TaskUpdate, TaskGet, TaskOutput, TaskStop
---

# /orchestrate - Multi-Agent Coordination

$ARGUMENTS

<!-- CLAUDE_CODE_ONLY_START -->
Only in Claude Code, apply the `model-routing-patterns` skill when choosing
executors or creating agent definitions. Delegate to `codex:codex-rescue` only
when its plugin is installed, enabled and callable in this session. Otherwise
use the installed native agents and their configured models. A context without
the Agent tool returns the dispatch decision to its supervisor; it does not
invent a tool or bypass the client. Preserve explicit user choices and verify
actual completion before accepting a delegated result.
<!-- CLAUDE_CODE_ONLY_END -->

## Choose the available execution mode

When the Agent tool is available, decompose the task and delegate owned work to
real agents. The supervisor integrates and verifies their results. If the runtime
has no delegation support, do the authorized work in the current session and
report that limitation. Never invent agent calls or present role-play as delegation.

## Step 1 — Decompose

Analyze the task and identify 3–6 sub-domains (e.g. backend, frontend, security, testing, docs). Define clear file ownership per domain so agents don't conflict.

Present the decomposition and obtain any approval not already covered by the
user's instructions. Preserve approval already given for the task.

## Step 2 — Spawn agents in parallel (REQUIRED)

When available, call the `Agent` tool for independent sub-domains in parallel,
within the runtime's concurrency and nesting limits. Execute dependent tasks in
order and use the current-session fallback when delegation is unavailable.

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
