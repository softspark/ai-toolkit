# AGENTS.md

This file describes the specialized AI agents bundled with ai-toolkit.
It is auto-generated from `app/agents/*.md` frontmatter — do not edit manually.

To regenerate: `python3 scripts/generate_agents_md.py > AGENTS.md`

Compatible with: Claude Code, Codex, OpenCode, Gemini CLI.

---

## Usage

### Claude Code
Agents are loaded automatically from `.claude/agents/` after running `install.sh`.
Invoke via the Agent tool:
```
Use subagent_type: "backend-specialist" to implement the API endpoint.
```

### Codex / OpenCode
Reference agents by name in your prompts:
```
@backend-specialist implement the payment API
```

### Gemini CLI
Use agent descriptions as system context:
```
gemini --system "$(cat .claude/agents/backend-specialist.md)" "implement the API"
```

---

## Agents

### `ai-engineer`

AI/ML integration specialist. Use for LLM integration, vector databases, RAG pipelines, embeddings, AI agent orchestration, document indexing, semantic search, hybrid retrieval, and answer generation. Triggers: ai, ml, llm, embedding, vector, rag, agent, openai, anthropic, search, retrieval, indexing, chunking, reranking.

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `backend-specialist`

Expert backend architect for Node.js, Python, PHP, and modern serverless systems. Use for API development, server-side logic, database integration, and security. Triggers: backend, server, api, endpoint, database, auth, fastapi, express, laravel.

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `business-intelligence`

Opportunity Discovery agent. Scans data models and code to identify missing business metrics, KPIs, and opportunities for value creation.

**Tools:** `Read, Write, Bash`

---

### `chaos-monkey`

Resilience testing agent. Use to inject faults, latency, and failures into the system to verify robustness and recovery mechanisms.

**Tools:** `Read, Write, Bash`

---

### `chief-of-staff`

Executive Summary agent. Aggregates reports from all other agents to reduce noise and present a single, actionable daily briefing to the user.

**Tools:** `Read, Write, Bash`

---

### `code-archaeologist`

Legacy code investigation and understanding specialist. Trigger words: legacy code, code archaeology, dead code, technical debt, dependency analysis, refactoring, code history

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `code-reviewer`

Code review and security audit expert. Use for security reviews, Devil's Advocate analysis, quality audits, best practices validation. Triggers: review, security, audit, quality, best practices, vulnerability.

**Tools:** `Read, Edit`

---

### `command-expert`

CLI commands and shell scripting specialist. Trigger words: bash, shell, CLI, script, automation, command line, build script, deployment script

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `data-analyst`

Data analysis and visualization expert. Use for SQL queries, data exploration, analytics, reporting, and insights. Triggers: data, analysis, sql, query, visualization, metrics, dashboard, pandas, report.

**Tools:** `Read, Write, Edit, Bash, Grep`

---

### `data-scientist`

Statistical analysis and data insights specialist. Use for statistical analysis, data visualization, EDA, A/B testing, and predictive modeling. Triggers: statistics, visualization, eda, analysis, hypothesis testing, ab test.

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `database-architect`

Database design, optimization, and operations expert. Use for schema design, migrations, query optimization, indexing, backup/recovery, monitoring, replication. Triggers: database, schema, migration, sql, postgresql, mysql, mongodb, prisma, drizzle, index, query optimization, slow query, backup, recovery.

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `debugger`

Root cause analysis expert. Use for cryptic errors, stack traces, intermittent failures, silent bugs, and systematic debugging. Triggers: debug, error, exception, traceback, bug, failure, root cause.

**Tools:** `Read, Edit, Bash`

---

### `devops-implementer`

Infrastructure implementation expert. Use for writing Terraform, Ansible, Docker, and shell scripts based on approved architecture notes and implementation summaries. Triggers: terraform, ansible, docker, kubernetes, shell, infrastructure, deployment, configuration.

**Tools:** `Read, Write, Edit, Bash`

---

### `documenter`

Documentation and KB expert. Use for architecture notes, runbooks, changelogs, KB updates, how-to guides, API docs, READMEs, tutorials, SOP creation, KB organization, content quality review. Triggers: document, documentation, architecture-note, runbook, changelog, howto, readme, kb, sop, technical writing.

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `explorer-agent`

Codebase exploration and discovery agent. Use for mapping project structure, finding dependencies, understanding architecture, and research. Does NOT write code - only reads and analyzes.

**Tools:** `Read, Grep, Glob`

---

### `fact-checker`

Claim verification expert. Use for verifying facts, source validation, RAG result accuracy checking. Triggers: fact check, verify, accuracy, claim, source validation.

**Tools:** `Read`

---

### `frontend-specialist`

Senior Frontend Architect for React, Next.js, Vue, and modern web systems. Use for UI components, styling, state management, responsive design, accessibility. Triggers: component, react, vue, ui, ux, css, tailwind, responsive, nextjs.

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `game-developer`

Game development across all platforms (PC, Web, Mobile, VR/AR). Use for Unity, Godot, Unreal, Phaser, Three.js. Covers game mechanics, multiplayer, optimization, 2D/3D graphics.

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `incident-responder`

Production incident response expert. Use for P1-P4 incidents, outages, emergency fixes, and postmortem documentation. Triggers: incident, outage, production down, emergency, P1, alert, monitoring.

**Tools:** `Read, Write, Edit, Bash`

---

### `infrastructure-architect`

System design expert. Use for architectural decisions, architecture notes, trade-off analysis, technology selection. Triggers: architecture, design, decision, trade-off, scalability, infrastructure planning.

**Tools:** `Read, Write, Edit`

---

### `infrastructure-validator`

Deployment validation expert. Use for deployment verification, health checks, testing, rollback procedures. Triggers: validate, deploy, deployment, health check, smoke test, rollback.

**Tools:** `Read, Edit, Bash`

---

### `llm-ops-engineer`

LLM operations expert. Use for LLM caching, fallback strategies, cost optimization, observability, and reliability. Triggers: llm, language model, openai, ollama, caching, fallback, token, cost.

**Tools:** `Read, Write, Edit, Bash`

---

### `mcp-specialist`

MCP server design, implementation, client configuration, and integration troubleshooting. Triggers: mcp, model context protocol, json-rpc, sse, stdio, mcp server, mcp config, mcp integration, mcp connection, claude desktop, mcp client.

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `mcp-testing-engineer`

MCP protocol testing expert. Use for MCP server testing, protocol compliance, transport validation, integration testing. Triggers: mcp test, protocol compliance, mcp validation, transport testing.

**Tools:** `Read, Write, Edit, Bash`

---

### `meta-architect`

Self-Optimization agent. Analyzes system performance and mistakes to update agent definitions and instructions. The only agent allowed to modify .claude/agents/*.

**Tools:** `Read, Write, Edit, Bash, Grep`

---

### `ml-engineer`

Machine learning systems specialist. Use for model training, data pipelines, MLOps, and model deployment. Triggers: ml, machine learning, model training, mlops, tensorflow, pytorch, scikit-learn.

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `mobile-developer`

Expert in React Native, Flutter, and native mobile development. Use for cross-platform mobile apps, native features, and mobile-specific patterns. Triggers: mobile, react native, flutter, ios, android, app store, expo, swift, kotlin.

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `night-watchman`

Autonomous maintenance agent. Use for automated dependency updates, dead code removal, refactoring, and project hygiene tasks. Typically scheduled to run off-hours.

**Tools:** `Read, Write, Edit, Bash, Grep`

---

### `nlp-engineer`

Natural Language Processing specialist. Use for text processing, NER, text classification, information extraction, and language model fine-tuning. Triggers: nlp, ner, tokenization, text classification, sentiment, spacy, transformers.

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `orchestrator`

Multi-agent coordination and task orchestration. Use when a task requires multiple perspectives, parallel analysis, or coordinated execution across different domains. Invoke for complex tasks benefiting from security, backend, frontend, testing, and DevOps expertise combined.

**Tools:** `Read, Grep, Glob, Bash, Write, Edit, Agent, TeamCreate, TeamDelete, SendMessage, TaskCreate, TaskList, TaskUpdate`

---

### `performance-optimizer`

Performance optimization expert. Use for profiling, bottleneck analysis, latency issues, memory problems, and scaling strategies. Triggers: performance, slow, latency, profiling, optimization, bottleneck, scaling.

**Tools:** `Read, Edit, Bash`

---

### `predictive-analyst`

Precognition agent. Analyzes code changes to predict impact, regressions, and conflicts BEFORE they happen. Uses dependency graphs and historical data.

**Tools:** `Read, Write, Bash, Grep, Glob`

---

### `product-manager`

Product management and value maximization expert. Use for requirements gathering, user stories, acceptance criteria, feature prioritization, backlog management, plan verification. Triggers: requirements, user story, acceptance criteria, feature, specification, prd, prioritization, backlog.

**Tools:** `Read, Write, Grep, Glob`

---

### `project-planner`

Smart project planning agent. Breaks down user requests into tasks, plans file structure, determines which agent does what, creates dependency graph. Use when starting new projects or planning major features.

**Tools:** `Read, Grep, Glob, Bash, Write`

---

### `prompt-engineer`

LLM prompt design and optimization specialist. Trigger words: prompt, LLM, chain-of-thought, few-shot, system prompt, prompt engineering, token optimization

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `qa-automation-engineer`

Test automation and QA specialist. Use for E2E testing, API testing, performance testing, and CI/CD test integration. Triggers: e2e, playwright, cypress, selenium, api test, performance test, automation.

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `search-specialist`

Information retrieval and search optimization specialist. Trigger words: search, query, semantic search, information retrieval, relevance, ranking, search optimization

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `security-architect`

Proactive security design expert. Use for Threat Modeling, architecture security reviews, and designing secure systems (AuthN/AuthZ, Crypto).

**Tools:** `Read, Write, Edit, Bash`

---

### `security-auditor`

Security expert. Use for OWASP Top 10, CVE analysis, security audits, penetration testing, vulnerability assessment, hardening. Triggers: security, owasp, cve, vulnerability, audit, hardening, penetration, pentest, injection test, api security.

**Tools:** `Read, Write, Edit, Bash`

---

### `seo-specialist`

Search engine optimization specialist. Trigger words: SEO, search engine, meta tags, structured data, Core Web Vitals, sitemap, robots.txt, schema.org

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `system-governor`

The Guardian of the Constitution. Validates all evolutionary changes and enforces immutable rules. Has VETO power.

**Tools:** `Read, Write, Bash`

---

### `tech-lead`

Technical authority for code quality, architecture patterns, and stack decisions. Use for code reviews, technological disputes, and standards enforcement.

**Tools:** `Read, Write, Edit, Bash`

---

### `technical-researcher`

Deep technical investigation and multi-source research synthesis specialist. Trigger words: technical research, feasibility study, root cause analysis, API investigation, compatibility research, comparison matrix, synthesize, aggregate, report, executive summary, gap analysis, findings, multi-source, cross-reference

**Tools:** `Read, Write, Edit, Bash, Grep, Glob`

---

### `test-engineer`

Testing expert. Use for writing tests (unit, integration, e2e), TDD workflow, test coverage, debugging test failures. Triggers: test, pytest, unittest, coverage, tdd, testing, mock, fixture.

**Tools:** `Read, Write, Edit, Bash`

---

