---
name: teams
description: "Launch pre-configured Agent Teams for common workflows"
effort: max
user-invocable: true
argument-hint: "<preset> [task-description]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, TeamCreate, TeamDelete, SendMessage, TaskCreate, TaskList, TaskUpdate, TaskGet
---

# /teams - Agent Teams Presets

$ARGUMENTS

## What This Does

Launches a pre-configured Agent Teams composition for your task.

Requires: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

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

## Usage Examples

```
/teams review           # Launch review team on current changes
/teams debug            # Launch debug team for current issue
/teams feature          # Launch feature team for new feature
/teams security         # Launch security audit team
/teams migration        # Launch migration team
```

## Preset Definitions

### review
- **Agents**: code-reviewer (lead), security-auditor, performance-optimizer
- **Ownership**: code-reviewer owns review summary; others own their domain reports
- **Aggregation**: consensus — flag issues found by 2+ agents as high priority
- **Output**: `REVIEW.md` with severity-ranked findings

### debug
- **Agents**: debugger (lead), backend-specialist, incident-responder
- **Ownership**: debugger owns root-cause analysis; others own hypothesis testing
- **Aggregation**: relay — debugger synthesizes findings from others
- **Output**: `DEBUG_REPORT.md` with root cause and fix

### feature
- **Agents**: orchestrator (lead), backend-specialist, frontend-specialist, test-engineer
- **Ownership**: orchestrator owns plan; specialists own their files; test-engineer owns tests
- **Aggregation**: map-reduce — orchestrator integrates all outputs
- **Output**: implemented feature + tests

### fullstack
- **Agents**: backend-specialist, frontend-specialist, database-architect, devops-implementer
- **Ownership**: each agent owns their layer (API, UI, DB, infra)
- **Aggregation**: relay — backend-specialist synthesizes integration
- **Output**: full stack implementation

### research
- **Agents**: technical-researcher (lead), data-analyst, prompt-engineer
- **Ownership**: technical-researcher owns synthesis; others own domain findings
- **Aggregation**: consensus — areas of agreement highlighted
- **Output**: `RESEARCH.md` with findings and recommendations

### security
- **Agents**: security-architect (lead), security-auditor, backend-specialist
- **Ownership**: security-architect owns threat model; auditor owns findings; backend owns remediation
- **Aggregation**: relay — security-architect integrates all
- **Output**: `SECURITY_AUDIT.md` with CVSS-scored findings

### migration
- **Agents**: database-architect (lead), backend-specialist, devops-implementer
- **Ownership**: database-architect owns schema; backend owns code changes; devops owns deployment
- **Aggregation**: relay — database-architect coordinates sequence
- **Output**: migration scripts + rollback plan + deployment runbook

## Steps

1. Parse `$ARGUMENTS` to extract `<preset>` and optional `[task-description]`
2. Validate preset is one of: review, debug, feature, fullstack, research, security, migration
3. Check `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set; warn if not
4. Display the team composition and ownership rules
5. Ask user to confirm before launching
6. Launch the appropriate agents using the Agent tool with the task description
7. Apply the aggregation strategy to synthesize results
8. Produce the defined output document

## Environment

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```
