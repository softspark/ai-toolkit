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


<!-- TOOLKIT:jira-rules START -->
<!-- Auto-injected by ai-toolkit. Re-run to update. -->

# Jira MCP Server

Tools: `sync_tasks`, `read_cached_tasks`, `update_task_status`, `add_task_comment`, `reassign_task`, `get_task_statuses`, `get_task_details`, `log_task_time`, `get_task_time_tracking`

## Key Rules

- **Always `sync_tasks` first** before reading — cache may be stale.
- **Time format:** `"2h 30m"` — hours and minutes only, never days.
- **Status changes:** call `get_task_statuses` first to check valid transitions.
- **Multi-instance:** project key determines which Jira instance is used (mapped in config.json).

## Workflow

1. `sync_tasks(jql="assignee=currentUser() AND status!=Done")` — fetch fresh
2. `read_cached_tasks()` — work offline
3. `get_task_details(task_key="PROJ-123")` — deep dive
4. `update_task_status(...)` / `add_task_comment(...)` / `log_task_time(...)` — mutate

<!-- TOOLKIT:jira-rules END -->

<!-- TOOLKIT:rag-mcp-rules START -->
<!-- Auto-injected by ai-toolkit. Re-run to update. -->

## INSTANT ACTION RULE (GOLDEN RULE)

**ANY technical question? -> INSTANTLY call `smart_query()` OR `hybrid_search_kb()` BEFORE outputting text!**

1. **Search First:** `smart_query()` or `hybrid_search_kb()` (NEVER skip, even if you "know").
2. **Cite Sources:** always include `[PATH: kb/...]`.
3. **Strict Order:** Semantic Search -> Files -> External Docs -> General Knowledge.

Default tool: `smart_query()`. Use `hybrid_search_kb()` for speed, `crag_search()` for vague queries, `multi_hop_search()` for complex reasoning.

## kb_id vs file_path

- `get_document(path=...)` takes `kb_id` from search results (e.g., `local/softspark/project/reference/api.md`)
- `Read`/`Edit` take filesystem `file_path` (e.g., `./reference/api.md`)
- **DO NOT CONFUSE** these fields.

## SOPs

ALWAYS check `kb/procedures/` first: `smart_query("SOP for <task>")`.

<!-- TOOLKIT:rag-mcp-rules END -->

<!-- TOOLKIT:ai-toolkit START -->
<!-- Auto-generated by ai-toolkit. Re-run to update. -->

# AI Toolkit — Codex CLI Configuration

Shared AI development toolkit with specialized agents, Codex-compatible skills, quality hooks, and a safety constitution.

## Available Agents

Specialized agent personas — apply their expertise for relevant tasks:

- **ai-engineer**: AI/ML integration specialist. Use for LLM integration, vector databases, RAG pipelines, embeddings, AI agent orchestration, document indexing, semantic search, hybrid retrieval, and answer generation. Triggers: ai, ml, llm, embedding, vector, rag, agent, openai, anthropic, search, retrieval, indexing, chunking, reranking.
- **backend-specialist**: Expert backend architect for Node.js, Python, PHP, and modern serverless systems. Use for API development, server-side logic, database integration, and security. Triggers: backend, server, api, endpoint, database, auth, fastapi, express, laravel.
- **business-intelligence**: Opportunity Discovery agent. Scans data models and code to identify missing business metrics, KPIs, and opportunities for value creation.
- **chaos-monkey**: Resilience testing agent. Use to inject faults, latency, and failures into the system to verify robustness and recovery mechanisms.
- **chief-of-staff**: Executive Summary agent. Aggregates reports from all other agents to reduce noise and present a single, actionable daily briefing to the user.
- **code-archaeologist**: Legacy code investigation and understanding specialist. Trigger words: legacy code, code archaeology, dead code, technical debt, dependency analysis, refactoring, code history
- **code-reviewer**: Code review and security audit expert. Use for security reviews, Devil's Advocate analysis, quality audits, best practices validation. Triggers: review, security, audit, quality, best practices, vulnerability.
- **command-expert**: CLI commands and shell scripting specialist. Trigger words: bash, shell, CLI, script, automation, command line, build script, deployment script
- **data-analyst**: Data analysis and visualization expert. Use for SQL queries, data exploration, analytics, reporting, and insights. Triggers: data, analysis, sql, query, visualization, metrics, dashboard, pandas, report.
- **data-scientist**: Statistical analysis and data insights specialist. Use for statistical analysis, data visualization, EDA, A/B testing, and predictive modeling. Triggers: statistics, visualization, eda, analysis, hypothesis testing, ab test.
- **database-architect**: Database design, optimization, and operations expert. Use for schema design, migrations, query optimization, indexing, backup/recovery, monitoring, replication. Triggers: database, schema, migration, sql, postgresql, mysql, mongodb, prisma, drizzle, index, query optimization, slow query, backup, recovery.
- **debugger**: Root cause analysis expert. Use for cryptic errors, stack traces, intermittent failures, silent bugs, and systematic debugging. Triggers: debug, error, exception, traceback, bug, failure, root cause.
- **devops-implementer**: Infrastructure implementation expert. Use for writing Terraform, Ansible, Docker, and shell scripts based on approved architecture notes and implementation summaries. Triggers: terraform, ansible, docker, kubernetes, shell, infrastructure, deployment, configuration.
- **documenter**: Documentation and KB expert. Use for architecture notes, runbooks, changelogs, KB updates, how-to guides, API docs, READMEs, tutorials, SOP creation, KB organization, content quality review. Triggers: document, documentation, architecture-note, runbook, changelog, howto, readme, kb, sop, technical writing.
- **explorer-agent**: Codebase exploration and discovery agent. Use for mapping project structure, finding dependencies, understanding architecture, and research. Does NOT write code - only reads and analyzes.
- **fact-checker**: Claim verification expert. Use for verifying facts, source validation, RAG result accuracy checking. Triggers: fact check, verify, accuracy, claim, source validation.
- **frontend-specialist**: Senior Frontend Architect for React, Next.js, Vue, and modern web systems. Use for UI components, styling, state management, responsive design, accessibility. Triggers: component, react, vue, ui, ux, css, tailwind, responsive, nextjs.
- **game-developer**: Game development across all platforms (PC, Web, Mobile, VR/AR). Use for Unity, Godot, Unreal, Phaser, Three.js. Covers game mechanics, multiplayer, optimization, 2D/3D graphics.
- **incident-responder**: Production incident response expert. Use for P1-P4 incidents, outages, emergency fixes, and postmortem documentation. Triggers: incident, outage, production down, emergency, P1, alert, monitoring.
- **infrastructure-architect**: System design expert. Use for architectural decisions, architecture notes, trade-off analysis, technology selection. Triggers: architecture, design, decision, trade-off, scalability, infrastructure planning.
- **infrastructure-validator**: Deployment validation expert. Use for deployment verification, health checks, testing, rollback procedures. Triggers: validate, deploy, deployment, health check, smoke test, rollback.
- **llm-ops-engineer**: LLM operations expert. Use for LLM caching, fallback strategies, cost optimization, observability, and reliability. Triggers: llm, language model, openai, ollama, caching, fallback, token, cost.
- **mcp-specialist**: MCP server design, implementation, client configuration, and integration troubleshooting. Triggers: mcp, model context protocol, json-rpc, sse, stdio, mcp server, mcp config, mcp integration, mcp connection, claude desktop, mcp client.
- **mcp-testing-engineer**: MCP protocol testing expert. Use for MCP server testing, protocol compliance, transport validation, integration testing. Triggers: mcp test, protocol compliance, mcp validation, transport testing.
- **meta-architect**: Self-Optimization agent. Analyzes system performance and mistakes to update agent definitions and instructions. The only agent allowed to modify .claude/agents/*.
- **ml-engineer**: Machine learning systems specialist. Use for model training, data pipelines, MLOps, and model deployment. Triggers: ml, machine learning, model training, mlops, tensorflow, pytorch, scikit-learn.
- **mobile-developer**: Expert in React Native, Flutter, and native mobile development. Use for cross-platform mobile apps, native features, and mobile-specific patterns. Triggers: mobile, react native, flutter, ios, android, app store, expo, swift, kotlin.
- **night-watchman**: Autonomous maintenance agent. Use for automated dependency updates, dead code removal, refactoring, and project hygiene tasks. Typically scheduled to run off-hours.
- **nlp-engineer**: Natural Language Processing specialist. Use for text processing, NER, text classification, information extraction, and language model fine-tuning. Triggers: nlp, ner, tokenization, text classification, sentiment, spacy, transformers.
- **orchestrator**: Multi-agent coordination and task orchestration. Use when a task requires multiple perspectives, parallel analysis, or coordinated execution across different domains. Invoke for complex tasks benefiting from security, backend, frontend, testing, and DevOps expertise combined.
- **performance-optimizer**: Performance optimization expert. Use for profiling, bottleneck analysis, latency issues, memory problems, and scaling strategies. Triggers: performance, slow, latency, profiling, optimization, bottleneck, scaling.
- **predictive-analyst**: Precognition agent. Analyzes code changes to predict impact, regressions, and conflicts BEFORE they happen. Uses dependency graphs and historical data.
- **product-manager**: Product management and value maximization expert. Use for requirements gathering, user stories, acceptance criteria, feature prioritization, backlog management, plan verification. Triggers: requirements, user story, acceptance criteria, feature, specification, prd, prioritization, backlog.
- **project-planner**: Smart project planning agent. Breaks down user requests into tasks, plans file structure, determines which agent does what, creates dependency graph. Use when starting new projects or planning major features.
- **prompt-engineer**: LLM prompt design and optimization specialist. Trigger words: prompt, LLM, chain-of-thought, few-shot, system prompt, prompt engineering, token optimization
- **qa-automation-engineer**: Test automation and QA specialist. Use for E2E testing, API testing, performance testing, and CI/CD test integration. Triggers: e2e, playwright, cypress, selenium, api test, performance test, automation.
- **search-specialist**: Information retrieval and search optimization specialist. Trigger words: search, query, semantic search, information retrieval, relevance, ranking, search optimization
- **security-architect**: Proactive security design expert. Use for Threat Modeling, architecture security reviews, and designing secure systems (AuthN/AuthZ, Crypto).
- **security-auditor**: Security expert. Use for OWASP Top 10, CVE analysis, security audits, penetration testing, vulnerability assessment, hardening. Triggers: security, owasp, cve, vulnerability, audit, hardening, penetration, pentest, injection test, api security.
- **seo-specialist**: Search engine optimization specialist. Trigger words: SEO, search engine, meta tags, structured data, Core Web Vitals, sitemap, robots.txt, schema.org
- **system-governor**: The Guardian of the Constitution. Validates all evolutionary changes and enforces immutable rules. Has VETO power.
- **tech-lead**: Technical authority for code quality, architecture patterns, and stack decisions. Use for code reviews, technological disputes, and standards enforcement.
- **technical-researcher**: Deep technical investigation and multi-source research synthesis specialist. Trigger words: technical research, feasibility study, root cause analysis, API investigation, compatibility research, comparison matrix, synthesize, aggregate, report, executive summary, gap analysis, findings, multi-source, cross-reference
- **test-engineer**: Testing expert. Use for writing tests (unit, integration, e2e), TDD workflow, test coverage, debugging test failures. Triggers: test, pytest, unittest, coverage, tdd, testing, mock, fixture.

## Available Skills

Skills are invocable commands or auto-loaded knowledge sources:

- **agent-creator**: Creates new specialized agents with frontmatter, tool selection, and delegation guidance
- **analyze**: Analyze code quality, complexity, and patterns
- **api-patterns**: Loaded when user asks about REST API design or GraphQL patterns
- **app-builder**: Loaded when user asks to scaffold or build a full-stack app
- **architecture-decision**: Loaded when user asks about architecture decisions or architecture note writing
- **biz-scan**: Scan codebase for business opportunities and KPIs
- **brand-voice**: Loaded when writing documentation, content, README, or user-facing text. Prevents generic LLM rhetoric and enforces direct, technical voice.
- **briefing**: Generate executive daily briefing across all agents
- **build**: Build the project with auto-detected toolchain
- **chaos**: Inject controlled faults for resilience testing
- **ci**: Detect and run CI pipeline with status reporting
- **ci-cd-patterns**: Loaded when user asks about CI/CD pipelines or deployment automation
- **clean-code**: Loaded when user asks about clean code, naming, or code quality
- **command-creator**: Creates new Claude Code slash commands with frontmatter, workflow guidance, and validation
- **commit**: Create Conventional Commits with pre-commit validation
- **csharp-patterns**: Loaded when user asks about C# or .NET development patterns
- **cve-scan**: Scan project dependencies for known CVEs using native audit tools (npm, pip, composer, cargo, go, bundler, dart)
- **database-patterns**: Loaded when user asks about database schema or query optimization
- **debug**: Debug errors and trace root causes systematically
- **debugging-tactics**: Loaded when user is debugging an issue or needs root cause analysis
- **deploy**: Deploy with pre-flight checks and health verification
- **design-engineering**: Loaded when user asks about UI animations or CSS design craft
- **docker-devops**: Loaded when user asks about Docker, containers, or DevOps patterns
- **docs**: Generate and update README, API docs, and architecture notes
- **documentation-standards**: Loaded when creating or updating KB documents, architecture notes, SOPs, or any file in kb/ directory
- **ecommerce-patterns**: Loaded when user asks about e-commerce or shopping cart features
- **evaluate**: Evaluate skill quality and RAG retrieval accuracy
- **evolve**: Evolve agent definitions via meta-architect
- **explain**: Explain code, architecture, or concepts with diagrams
- **explore**: Explore codebase structure, stack, and architecture
- **fix**: Auto-fix lint errors, type issues, and simple bugs
- **flutter-patterns**: Loaded when user asks about Flutter or Dart development patterns
- **git-mastery**: Loaded when user asks about advanced Git workflows or history rewriting
- **health**: Report service and infrastructure health status
- **hipaa-validate**: Validate code against HIPAA policy: PHI exposure, missing audit logging, unencrypted transmission/storage, access control gaps, temp file exposure, and missing BAA references
- **hive-mind**: Loaded when orchestrating multi-agent swarms or consensus workflows
- **hook-creator**: Creates new Claude Code hooks with guided workflow, strict conventions, and validation
- **index**: Index codebase into the knowledge base
- **instinct-review**: Review and manage learned instincts from past sessions
- **introspect**: Agent self-debugging and recovery. Use when stuck in loops, making repeated errors, or quality degrades. Triggers: introspect, self-debug, stuck, loop, why failing.
- **java-patterns**: Loaded when user asks about Java development patterns
- **kotlin-patterns**: Loaded when user asks about Kotlin development patterns
- **lint**: Lint code with auto-detected tools and fix suggestions
- **mcp-patterns**: Loaded when user asks about MCP servers or tool protocol design
- **mem-search**: Search past coding sessions using natural language. Finds relevant observations, decisions, and context from previous work.
- **migrate**: Run database migrations with backup verification
- **migration-patterns**: Loaded when user asks about database migrations or zero-downtime deploys
- **night-watch**: Run autonomous maintenance and dependency updates
- **observability-patterns**: Loaded when user asks about logging, metrics, or tracing patterns
- **onboard**: Generate project onboarding materials
- **panic**: Emergency stabilization via system-governor agent
- **performance-profiling**: Loaded when user asks about performance profiling or optimization
- **persona**: Switch engineering persona at runtime: backend-lead, frontend-lead, devops-eng, junior-dev
- **plan**: Plan implementation with tasks and success criteria
- **plan-writing**: Loaded when user asks to write an implementation plan or pre-mortem
- **plugin-creator**: Creates experimental opt-in Claude Code plugin packs with manifests, conventions, and optional module scaffolding
- **pr**: Create pull requests with pre-flight validation
- **prd-to-issues**: Break a PRD into independently-grabbable GitHub issues using vertical slices with HITL/AFK tagging and dependency ordering. Use when user wants to convert a PRD to issues, create tickets, or break down a PRD into work items.
- **predict**: Predict regressions and impact before changes land
- **rag-patterns**: Loaded when user asks about RAG systems, embeddings, or vector search
- **refactor**: Refactor code for quality and maintainability
- **research-mastery**: Loaded when user asks to research, verify, or synthesize information
- **review**: Review code for quality, security, and correctness
- **rollback**: Roll back a deployment safely with verification
- **ruby-patterns**: Loaded when user asks about Ruby development patterns
- **rust-patterns**: Loaded when user asks about Rust development patterns
- **search**: Search the knowledge base with semantic and hybrid modes
- **security-patterns**: Loaded when user asks about security, OWASP, or auth patterns
- **skill-audit**: Scan skills and agents for security risks: dangerous patterns, secrets, excessive permissions
- **skill-creator**: Create new skills from templates with guided workflow
- **swift-patterns**: Loaded when user asks about Swift or iOS development patterns
- **test**: Run tests with coverage analysis and reporting
- **testing-patterns**: Loaded when user asks about testing strategy, fixtures, or mocking
- **typescript-patterns**: Loaded when user asks about TypeScript patterns or type safety
- **ubiquitous-language**: Extract a DDD-style ubiquitous language glossary from the conversation, flagging ambiguities and proposing canonical terms. Saves to UBIQUITOUS_LANGUAGE.md. Use when user wants to define domain terms, build a glossary, harden terminology, or mentions DDD or domain model.
- **verification-before-completion**: Loaded when agent is about to claim work is complete, fixed, or passing — requires running verification commands and confirming output before making any success claims. Evidence before assertions, always.

## Quality Standards

Derived from the immutable safety constitution (5 articles):

**Article I — Safety First**
- No data loss: never delete files without backup verification or using reversible operations
- No blind execution: never run LLM-generated code without static analysis or review
- No infinite loops: all autonomous loops must have a maximum iteration count (max 3)

**Article II — Hierarchy of Truth**
- The Knowledge Base (`kb/`) is the source of truth; if code contradicts KB, check KB freshness
- Use the research-mastery skill before any major decision; guessing is forbidden

**Article III — Operational Integrity**
- "Green Tests" is the only definition of Done; forced merges on red tests are unacceptable
- Never delete audit logs or KB archives without explicit user approval and backup verification
- Agents cannot change their own model or tool permissions without user approval

**Article IV — Self-Preservation**
- The constitution file is read-only for all agents except the user
- If a constitutional violation is detected, halt the offending operation immediately

**Article V — Resource Governance**
- Commands like `rm -rf`, `DROP TABLE`, `FORMAT` require explicit user confirmation
- Operate within assigned model tiers; model tier changes require user approval

## Workflow Guidelines

- **Plan First**: Tasks longer than 1 hour require a plan, success criteria, and pre-mortem
- **Multi-Agent**: Use minimum 3 agents for complex tasks; single-agent for simple tasks
- **2-Phase Execution**: Plan → User Approval → Implement (never skip the approval checkpoint)
- **KB-First Research**: Search the knowledge base before writing code or answering questions
- **Structured Commits**: Use `feat/fix/docs/refactor/test/chore` prefixes (Conventional Commits)
- **Quality Gates**: Run `ruff check .` (Python), `tsc` (TypeScript), `go vet` (Go) before marking done
- **Cite Sources**: Always reference `[PATH: ...]` when making decisions based on existing knowledge
- **Read-Only Exploration**: Discovery agents never write; writing agents never explore blindly
- **No Secrets in Code**: Never commit credentials, API keys, or sensitive configuration values
<!-- TOOLKIT:ai-toolkit END -->
