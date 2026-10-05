---
title: "AI Toolkit - Agents Catalog"
category: reference
service: ai-toolkit
tags: [agents, catalog, roles, ai-development]
version: "1.5.0"
created: "2026-03-23"
last_updated: "2026-10-01"
description: "Complete catalog of specialized agents with roles, models, and use cases."
---

# Agents Catalog

The model column describes configured Claude tiers, not fixed API versions.
Aliases resolve through the active provider/client configuration. Codex and
Copilot generated agents preserve the host's selected model rather than copying
Claude aliases. See [Model Compatibility](model-compatibility.md) for the dated
model reference, effort boundaries and validation limits.

Bounded implementation agents use Sonnet with `high` effort. The orchestrator
uses Opus `high`, and the debugger uses Opus `xhigh`. Other roles retain their
configured tiers. In Claude Code, an installed, enabled and runtime-callable
Codex plugin is an additional executor; absent that capability, native agents
keep their configured models. See [conditional delegation](model-compatibility.md#conditional-claude-to-codex-delegation).

## By Category

### Orchestration & Planning (4)

| Agent | Model | Use Case |
|-------|-------|----------|
| **orchestrator** | opus | Multi-agent coordination, 3+ agents per task |
| **project-planner** | opus | Task breakdown, dependency graphs, file structure |
| **product-manager** | opus | Requirements, user stories, acceptance criteria, backlog prioritization |
| **tech-lead** | opus | Code quality authority, architecture patterns |

### Development (5)

| Agent | Model | Use Case |
|-------|-------|----------|
| **backend-specialist** | sonnet | Node.js, Python, PHP, FastAPI, APIs |
| **frontend-specialist** | sonnet | React, Next.js, Vue, Nuxt, Tailwind |
| **mobile-developer** | sonnet | React Native, Flutter, native iOS/Android |
| **game-developer** | sonnet | Unity, Godot, Unreal, Phaser, Three.js |
| **database-architect** | opus | Schema design, migrations, query optimization, operations |

### AI/ML (6)

| Agent | Model | Use Case |
|-------|-------|----------|
| **ai-engineer** | sonnet | LLM integration, vector databases, RAG pipelines, agent orchestration |
| **ml-engineer** | sonnet | Model training, MLOps, TensorFlow, PyTorch |
| **nlp-engineer** | sonnet | NLP pipelines, NER, text classification, transformers |
| **data-scientist** | opus | Statistics, visualization, EDA, hypothesis testing |
| **data-analyst** | sonnet | SQL, analytics, reporting, dashboards |
| **prompt-engineer** | opus | Prompt design, chain-of-thought, few-shot, optimization |

### Quality & Security (6)

| Agent | Model | Use Case |
|-------|-------|----------|
| **code-reviewer** | opus | Code review, standards, quality audit |
| **test-engineer** | sonnet | Test strategy, TDD, unit/integration/E2E tests |
| **qa-automation-engineer** | sonnet | Playwright, Cypress, API testing, performance testing |
| **security-auditor** | opus | OWASP, CVE analysis, pen testing, vulnerability assessment |
| **security-architect** | opus | Threat modeling, secure design, AuthN/AuthZ |
| **system-governor** | opus | Constitution guardian, validates changes, VETO power |

### Infrastructure & DevOps (6)

| Agent | Model | Use Case |
|-------|-------|----------|
| **devops-implementer** | sonnet | Terraform, Ansible, Docker, Kubernetes, CI/CD |
| **infrastructure-architect** | opus | System design, architecture notes, trade-off analysis |
| **infrastructure-validator** | sonnet | Deployment verification, health checks, rollback |
| **incident-responder** | sonnet | P1-P4 incidents, emergency fixes, postmortem |
| **performance-optimizer** | opus | Profiling, bottleneck analysis, latency, scaling |
| **llm-ops-engineer** | opus | LLM caching, fallback, cost optimization, observability |

### Research & Documentation (5)

| Agent | Model | Use Case |
|-------|-------|----------|
| **explorer-agent** | sonnet | Codebase discovery (READ-ONLY, never writes) |
| **technical-researcher** | opus | Deep technical investigation, research synthesis |
| **search-specialist** | sonnet | Search optimization, relevance ranking |
| **fact-checker** | sonnet | Claim verification, source validation |
| **documenter** | sonnet | Documentation, KB management, SOPs, API docs, tutorials |

### MCP (2)

| Agent | Model | Use Case |
|-------|-------|----------|
| **mcp-specialist** | sonnet | MCP server design, client config, troubleshooting |
| **mcp-testing-engineer** | sonnet | MCP protocol compliance, transport testing |

### Management & Evolution (4)

| Agent | Model | Use Case |
|-------|-------|----------|
| **chief-of-staff** | sonnet | Executive summaries, daily briefings, noise reduction |
| **meta-architect** | opus | Self-optimization, agent definition updates |
| **predictive-analyst** | sonnet | Impact prediction, regression forecasting |
| **business-intelligence** | sonnet | Opportunity discovery, KPI gaps, value creation |

### Autonomous (2)

| Agent | Model | Use Case |
|-------|-------|----------|
| **night-watchman** | sonnet | Autonomous maintenance: dependency updates, dead code |
| **chaos-monkey** | opus | Resilience testing: fault injection, failure verification |

### Specialist (4)

| Agent | Model | Use Case |
|-------|-------|----------|
| **debugger** | opus | Root cause analysis, stack traces, intermittent failures |
| **code-archaeologist** | sonnet | Legacy code investigation, technical debt |
| **command-expert** | sonnet | CLI commands, bash scripting, build scripts |
| **seo-specialist** | sonnet | SEO optimization, meta tags, Core Web Vitals |

## Agent Selection Matrix

| Task Type | Primary | Supporting | Validation |
|-----------|---------|------------|------------|
| New Feature | backend/frontend-specialist | test-engineer | code-reviewer |
| Bug Fix | debugger | backend/frontend | test-engineer |
| Performance | performance-optimizer | database-architect | infrastructure-validator |
| Security | security-auditor | security-architect | code-reviewer |
| Architecture | infrastructure-architect | devops-implementer | security-auditor |
| Documentation | documenter | explorer-agent | tech-lead |
| AI/ML | ai-engineer | ml-engineer | data-scientist |
| Research | technical-researcher | search-specialist | fact-checker |
