---
name: teams
description: "Launches pre-configured multi-agent teams for code review, debugging, feature development, security audits, and database migrations. Use when the user asks to start a multi-agent workflow, coordinate agent teams, run a team review, or needs parallel agent collaboration on a complex task."
effort: max
user-invocable: true
argument-hint: "<preset> [task-description]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, TeamCreate, TeamDelete, SendMessage, TaskCreate, TaskList, TaskUpdate, TaskGet
---

# /teams: Agent Teams Presets

$ARGUMENTS

Launches a pre-configured Agent Teams composition for your task. Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

## Available Presets

| Preset | Agents | Use Case |
|--------|--------|----------|
| `review` | code-reviewer, security-auditor, performance-optimizer | PR code review |
| `debug` | debugger, backend-specialist, incident-responder | Multi-file bug investigation |
| `feature` | orchestrator, backend-specialist, frontend-specialist, test-engineer | Full feature implementation |
| `fullstack` | backend-specialist, frontend-specialist, database-architect, devops-implementer | Full-stack task |
| `research` | technical-researcher, data-analyst, prompt-engineer | Deep research task |
| `security` | security-architect, security-auditor, backend-specialist | Security audit |
| `migration` | database-architect, backend-specialist, devops-implementer | Database migration |

See [reference/presets.md](reference/presets.md) for detailed ownership, aggregation strategies, and output formats for each preset.

## Usage

```
/teams review              # Launch review team on current changes
/teams debug               # Launch debug team for current issue
/teams feature add auth    # Launch feature team with task context
/teams security            # Launch security audit team
```

## Workflow

1. **Parse** `$ARGUMENTS`: extract `<preset>` and optional `[task-description]`
2. **Validate** preset is one of: review, debug, feature, fullstack, research, security, migration
3. **Check environment**: verify `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set; warn if missing
4. **Display** team composition and ownership rules from [reference/presets.md](reference/presets.md)
5. **Confirm** with user before launching
6. **Launch agents**: spawn each agent with its assigned scope using the Agent tool:
   ```
   Agent({ description: "code-reviewer: PR review lead", prompt: "[task + ownership rules]" })
   Agent({ description: "security-auditor: security findings", prompt: "[task + domain scope]" })
   ```
7. **Aggregate results**: apply the preset's aggregation strategy (consensus, relay, or map-reduce)
8. **Produce output**: write the defined output document (e.g., `REVIEW.md`, `DEBUG_REPORT.md`)

### Error Handling

- If an agent fails or times out: log the failure, continue with remaining agents, note the gap in the output
- If agents produce conflicting findings: the lead agent resolves conflicts; flag unresolved disagreements for user review

## Environment

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```
