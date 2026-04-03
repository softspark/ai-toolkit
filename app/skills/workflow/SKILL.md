---
name: workflow
description: "Start and manage autonomous agent workflows"
user-invocable: true
effort: max
argument-hint: "[type] [task description]"
context: fork
agent: orchestrator
model: opus
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, TeamCreate, TeamDelete, SendMessage, TaskCreate, TaskList, TaskUpdate, TaskGet, TaskOutput, TaskStop
---

# /workflow - Autonomous Agent Workflow

$ARGUMENTS

## Step 1 — Select workflow type

```
Is production DOWN?               → incident-response
Performance degraded >50%?        → performance-optimization
Bug spanning multiple layers?     → debugging
Warning / trend?                  → proactive-troubleshooting
Planned infra change?             → infrastructure-change
Planned app deploy?               → application-deploy
New feature (full stack)?         → feature-development
New feature (backend only)?       → backend-feature
New feature (frontend only)?      → frontend-feature
New API endpoint?                 → api-design
Schema / migration change?        → database-evolution
Boost test coverage?              → test-coverage
Security assessment?              → security-audit
Exploring unfamiliar codebase?    → codebase-onboarding
Technical research / spike?       → spike
```

## Step 2 — Define success criteria (MANDATORY)

Cannot proceed without:

```yaml
Deliverables: [what outputs are expected]
Verification: [how to verify — tests, metrics, commands]
Definition of done: [quality bar]
```

Present to user and wait for approval.

## Step 3 — Spawn agents via Agent tool

Launch agents **in parallel where independent, sequentially where dependent**. Use the `Agent` tool — never do the work inline.

---

### Existing workflows

**`debugging`**
```
# Sequential diagnosis:
Agent(subagent_type="debugger",              prompt="Diagnose issue, 5 Whys, propose solution options. READ-ONLY.")
Agent(subagent_type="explorer-agent",        prompt="Trace call path across layers. READ-ONLY.")
# Parallel fix:
Agent(subagent_type="backend-specialist",    prompt="Implement fix. Own files: src/")
Agent(subagent_type="test-engineer",         prompt="Write regression test. Own files: tests/")
# Sequential:
Agent(subagent_type="documenter",            prompt="Document in kb/troubleshooting/ if recurring.")
```

**`incident-response`**
```
Agent(subagent_type="incident-responder",    prompt="Triage, root cause, immediate mitigation. READ-ONLY.")
# After triage:
Agent(subagent_type="backend-specialist",    prompt="Apply fix. Own files: src/")
Agent(subagent_type="documenter",            prompt="Write postmortem (MANDATORY). Own files: kb/")
```

**`performance-optimization`**
```
Agent(subagent_type="performance-optimizer", prompt="Profile, identify bottlenecks, propose fixes. READ-ONLY.")
Agent(subagent_type="backend-specialist",    prompt="Implement optimizations. Own files: src/")
Agent(subagent_type="test-engineer",         prompt="Benchmark before/after. Own files: tests/benchmarks/")
Agent(subagent_type="documenter",            prompt="Document baseline and results. Own files: kb/")
```

**`infrastructure-change`**
```
Agent(subagent_type="infrastructure-architect", prompt="Design change, create architecture note. Own files: docs/")
Agent(subagent_type="devops-implementer",       prompt="Implement infra changes. Own files: docker/, .github/, infra/")
Agent(subagent_type="security-auditor",         prompt="Review for security issues. READ-ONLY.")
Agent(subagent_type="test-engineer",            prompt="Smoke tests and health checks. Own files: tests/")
Agent(subagent_type="documenter",               prompt="Runbook + deployment docs. Own files: kb/")
```

**`application-deploy`**
```
Agent(subagent_type="devops-implementer",    prompt="Execute deployment. Own files: .github/, scripts/")
Agent(subagent_type="test-engineer",         prompt="Post-deploy smoke tests.")
Agent(subagent_type="documenter",            prompt="Release notes. Own files: kb/")
```

**`proactive-troubleshooting`**
```
Agent(subagent_type="debugger",              prompt="Investigate warning/trend, assess risk. READ-ONLY.")
Agent(subagent_type="performance-optimizer", prompt="Check performance metrics. READ-ONLY.")
Agent(subagent_type="backend-specialist",    prompt="Apply preventive fix if needed. Own files: src/")
Agent(subagent_type="documenter",            prompt="Update monitoring/alerting docs. Own files: kb/")
```

---

### New workflows

**`feature-development`** — full stack feature, plan → implement → test → ship
```
# Sequential planning:
Agent(subagent_type="project-planner",       prompt="Requirements, acceptance criteria, task breakdown. Own files: docs/")
Agent(subagent_type="explorer-agent",        prompt="Find integration points in codebase. READ-ONLY.")
# Parallel implementation:
Agent(subagent_type="backend-specialist",    prompt="API routes, business logic, data layer. Own files: src/api/, src/services/")
Agent(subagent_type="frontend-specialist",   prompt="UI components, state management. Own files: src/components/, src/pages/")
Agent(subagent_type="database-architect",    prompt="Schema changes + migrations if needed. Own files: migrations/")
# Parallel validation:
Agent(subagent_type="test-engineer",         prompt="Unit + integration tests. Own files: tests/")
Agent(subagent_type="security-auditor",      prompt="Security review of new attack surface. READ-ONLY.")
# Sequential finalization:
Agent(subagent_type="documenter",            prompt="API docs, KB update, changelog. Own files: kb/, docs/")
```

**`backend-feature`** — backend only: API + logic + tests
```
Agent(subagent_type="explorer-agent",        prompt="Find integration points and patterns. READ-ONLY.")
Agent(subagent_type="backend-specialist",    prompt="Implement endpoint + business logic. Own files: src/")
Agent(subagent_type="database-architect",    prompt="Schema/query changes if needed. Own files: migrations/")
Agent(subagent_type="test-engineer",         prompt="Unit + integration tests. Own files: tests/")
Agent(subagent_type="security-auditor",      prompt="Auth/authz, input validation review. READ-ONLY.")
```

**`frontend-feature`** — UI feature: component + state + tests
```
Agent(subagent_type="explorer-agent",        prompt="Find existing components and patterns. READ-ONLY.")
Agent(subagent_type="frontend-specialist",   prompt="Build component, state, routing. Own files: src/components/, src/pages/")
Agent(subagent_type="test-engineer",         prompt="Component tests, E2E if needed. Own files: tests/")
Agent(subagent_type="documenter",            prompt="Component docs / Storybook if applicable.")
```

**`api-design`** — design + implement + test + document a new API
```
# Sequential design:
Agent(subagent_type="tech-lead",             prompt="API contract, versioning, error format. Own files: docs/api-spec.md")
Agent(subagent_type="database-architect",    prompt="Data model for new resources. Own files: migrations/")
# Parallel implementation + validation:
Agent(subagent_type="backend-specialist",    prompt="Implement endpoint, validation, business logic. Own files: src/")
Agent(subagent_type="test-engineer",         prompt="Contract tests, integration tests. Own files: tests/")
Agent(subagent_type="security-auditor",      prompt="Auth/authz, rate limiting, input validation. READ-ONLY.")
Agent(subagent_type="performance-optimizer", prompt="Response time benchmark. READ-ONLY.")
# Sequential:
Agent(subagent_type="documenter",            prompt="OpenAPI spec, API reference docs. Own files: docs/")
```

**`database-evolution`** — schema change: design + migrate + update code + validate
```
# Sequential analysis:
Agent(subagent_type="database-architect",    prompt="Design schema change, migration + rollback plan. Own files: migrations/")
Agent(subagent_type="explorer-agent",        prompt="Find all code referencing affected tables/columns. READ-ONLY.")
# Parallel implementation:
Agent(subagent_type="backend-specialist",    prompt="Update ORM models, queries, data access layer. Own files: src/")
Agent(subagent_type="test-engineer",         prompt="Migration tests, data integrity checks. Own files: tests/")
# Parallel validation:
Agent(subagent_type="performance-optimizer", prompt="EXPLAIN ANALYZE on new queries, index efficiency. READ-ONLY.")
Agent(subagent_type="security-auditor",      prompt="SQL injection vectors in new query patterns. READ-ONLY.")
# Sequential:
Agent(subagent_type="documenter",            prompt="Update schema docs, migration changelog. Own files: kb/")
```

**`test-coverage`** — systematically boost test coverage for a module
```
# Sequential analysis:
Agent(subagent_type="explorer-agent",        prompt="Map untested code paths, find coverage gaps. READ-ONLY.")
# Parallel writing:
Agent(subagent_type="test-engineer",         prompt="Write unit tests for uncovered functions. Own files: tests/unit/")
Agent(subagent_type="backend-specialist",    prompt="Add integration test fixtures, mock external services. Own files: tests/integration/")
# Sequential review:
Agent(subagent_type="code-reviewer",         prompt="Review test quality — no false positives, deterministic. READ-ONLY.")
```

**`security-audit`** — comprehensive multi-vector security assessment
```
# Sequential recon:
Agent(subagent_type="explorer-agent",        prompt="Map attack surface, entry points, data flows. READ-ONLY.")
# Parallel audit:
Agent(subagent_type="security-auditor",      prompt="OWASP Top 10, injection, auth review. READ-ONLY.")
Agent(subagent_type="code-reviewer",         prompt="Secrets in code, error handling, logging gaps. READ-ONLY.")
Agent(subagent_type="devops-implementer",    prompt="Infra misconfig, Docker hardening, network. READ-ONLY.")
Agent(subagent_type="database-architect",    prompt="SQL injection vectors, access controls, encryption. READ-ONLY.")
# Sequential:
Agent(subagent_type="tech-lead",             prompt="Prioritize findings, assign severity (CVSS).")
Agent(subagent_type="documenter",            prompt="Security audit report + remediation checklist. Own files: kb/")
```

**`codebase-onboarding`** — understand an unfamiliar codebase fast (READ-ONLY)
```
# Parallel discovery:
Agent(subagent_type="explorer-agent",        prompt="Project structure, tech stack, entry points. READ-ONLY.")
Agent(subagent_type="tech-lead",             prompt="Architecture patterns, design decisions, conventions. READ-ONLY.")
Agent(subagent_type="database-architect",    prompt="Data model, relationships, migration history. READ-ONLY.")
# Parallel analysis:
Agent(subagent_type="test-engineer",         prompt="Test coverage, test patterns, CI pipeline. READ-ONLY.")
Agent(subagent_type="security-auditor",      prompt="Current security posture, credential management. READ-ONLY.")
# Sequential synthesis:
Agent(subagent_type="documenter",            prompt="Write onboarding guide + architecture overview. Own files: docs/ONBOARDING.md")
```

**`spike`** — time-boxed technical research to inform a decision
```
# Parallel research:
Agent(subagent_type="explorer-agent",        prompt="Existing codebase patterns relevant to decision. READ-ONLY.")
Agent(subagent_type="tech-lead",             prompt="Architecture implications, trade-off analysis. READ-ONLY.")
Agent(subagent_type="backend-specialist",    prompt="Implementation feasibility, proof of concept.")
# Sequential evaluation:
Agent(subagent_type="security-auditor",      prompt="Security implications of each option. READ-ONLY.")
Agent(subagent_type="performance-optimizer", prompt="Performance implications of each option. READ-ONLY.")
# Sequential decision:
Agent(subagent_type="tech-lead",             prompt="Comparison matrix, recommendation.")
Agent(subagent_type="documenter",            prompt="Write architecture note + spike findings. Own files: kb/reference/")
```

---

## Step 4 — Track status

| Event | Action |
|-------|--------|
| Agent started | `TaskUpdate(status="in_progress")` |
| Agent complete | `TaskUpdate(status="completed")` |
| Blocked | Document blocker, reassign or escalate |

## Step 5 — Exit gate

Workflow is NOT done until:
- [ ] Tests pass
- [ ] Documentation updated in `kb/`
- [ ] Postmortem written (incident-response only)
- [ ] Plan archived to `kb/history/completed/`

## Devil's Advocate (workflows >1h)

Before implementation:
- What could go wrong?
- Hidden costs / tech debt?
- At least 3 alternatives considered?
