# Agent Teams Preset Definitions

Detailed configuration for each `/teams` preset. Each preset defines agents, ownership, aggregation strategy, and output format.

## review

- **Agents**: code-reviewer (lead), security-auditor, performance-optimizer
- **Ownership**: code-reviewer owns review summary; others own their domain reports
- **Aggregation**: consensus — flag issues found by 2+ agents as high priority
- **Output**: `REVIEW.md` with severity-ranked findings

## debug

- **Agents**: debugger (lead), backend-specialist, incident-responder
- **Ownership**: debugger owns root-cause analysis; others own hypothesis testing
- **Aggregation**: relay — debugger synthesizes findings from others
- **Output**: `DEBUG_REPORT.md` with root cause and fix

## feature

- **Agents**: orchestrator (lead), backend-specialist, frontend-specialist, test-engineer
- **Ownership**: orchestrator owns plan; specialists own their files; test-engineer owns tests
- **Aggregation**: map-reduce — orchestrator integrates all outputs
- **Output**: implemented feature + tests

## fullstack

- **Agents**: backend-specialist, frontend-specialist, database-architect, devops-implementer
- **Ownership**: each agent owns their layer (API, UI, DB, infra)
- **Aggregation**: relay — backend-specialist synthesizes integration
- **Output**: full stack implementation

## research

- **Agents**: technical-researcher (lead), data-analyst, prompt-engineer
- **Ownership**: technical-researcher owns synthesis; others own domain findings
- **Aggregation**: consensus — areas of agreement highlighted
- **Output**: `RESEARCH.md` with findings and recommendations

## security

- **Agents**: security-architect (lead), security-auditor, backend-specialist
- **Ownership**: security-architect owns threat model; auditor owns findings; backend owns remediation
- **Aggregation**: relay — security-architect integrates all
- **Output**: `SECURITY_AUDIT.md` with CVSS-scored findings

## migration

- **Agents**: database-architect (lead), backend-specialist, devops-implementer
- **Ownership**: database-architect owns schema; backend owns code changes; devops owns deployment
- **Aggregation**: relay — database-architect coordinates sequence
- **Output**: migration scripts + rollback plan + deployment runbook
