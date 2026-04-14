---
title: "AI Toolkit - Skills Catalog"
category: reference
service: ai-toolkit
tags: [skills, domain-knowledge, catalog, task-skills, hybrid-skills]
version: "1.4.3"
created: "2026-03-23"
last_updated: "2026-04-12"
description: "Complete skills catalog with task, hybrid, and knowledge skills. Includes Codex adaptation notes, effort levels, skill-scoped hooks, executable scripts, security auditor, and persona presets."
---

# Skills Catalog

All functionality is unified under skills. Task and hybrid skills are user-invocable as slash commands. Knowledge skills provide domain patterns auto-loaded by agents.

## Skill Tiers

| Tier | Skills | When |
|------|--------|------|
| **1 — Quick single-agent** | `/debug`, `/review`, `/refactor`, `/analyze`, `/docs`, `/plan`, `/explain`, `/tdd`, `/grill-me`, `/triage-issue` | One concern, fast |
| **1.5 — Product planning** | `/write-a-prd` → `/prd-to-plan` → `/prd-to-issues` | Interview-driven PRD → vertical-slice plan → GitHub issues |
| **1.5 — Design & architecture** | `/design-an-interface`, `/architecture-audit`, `/refactor-plan`, `/ubiquitous-language`, `/qa-session` | Parallel sub-agent exploration |
| **2 — Multi-agent workflow** | `/workflow <type>` | Cross-cutting task with known pattern |
| **3 — Custom parallelism** | `/orchestrate`, `/swarm` | No predefined workflow matches |

## Task Skills (29)

Task skills execute a specific action. Invoked via slash commands. `disable-model-invocation: true`.

| Skill | Slash Command | Effort | Description |
|-------|---------------|--------|-------------|
| **commit** | `/commit` | medium | Create well-structured git commits (Conventional Commits) |
| **pr** | `/pr` | medium | Create GitHub pull request with template and checks |
| **test** | `/test` | medium | Run tests (auto-detect: pytest, vitest, jest, phpunit, flutter, go, cargo) |
| **build** | `/build` | low | Build the current project (auto-detects project type) |
| **lint** | `/lint` | low | Run linting and type checking (ruff/mypy, eslint/tsc, phpstan, dart analyze) |
| **fix** | `/fix` | low | Autonomously fix failing tests or lint errors (iterative loop) |
| **deploy** | `/deploy` | medium | Deploy to target environment with pre-deployment checks |
| **rollback** | `/rollback` | medium | Safe rollback (git, database migrations, deployments) |
| **migrate** | `/migrate` | medium | Database migration workflow (auto-detect: Alembic, Prisma, Laravel, Django) |
| **ci** | `/ci` | medium | Generate/manage CI/CD pipeline configuration (GitHub Actions, GitLab CI) |
| **panic** | `/panic` | low | EMERGENCY: Immediately halt all autonomous agent operations |
| **index** | `/index` | low | Reindex knowledge base to vector store with change detection |
| **onboard** | `/onboard` | medium | Guided project setup with the toolkit |
| **night-watch** | `/night-watch` | medium | Trigger Night Watchman autonomous maintenance cycle |
| **evolve** | `/evolve` | medium | Trigger Meta-Architect self-optimization cycle |
| **chaos** | `/chaos` | medium | Trigger Chaos Engineering experiment |
| **predict** | `/predict` | medium | Predict impact and risks of code changes |
| **biz-scan** | `/biz-scan` | medium | Scan project for business value opportunities and metric gaps |
| **briefing** | `/briefing` | medium | Generate daily executive summary of system status |
| **evaluate** | `/evaluate` | medium | Evaluate RAG quality using LLM-as-a-Judge methodology |
| **skill-creator** | `/skill-creator` | high | Create new skills following Agent Skills standard |
| **hook-creator** | `/hook-creator` | high | Create new Claude Code hooks with conventions and validation |
| **command-creator** | `/command-creator` | high | Create new slash commands with frontmatter and workflow guidance |
| **agent-creator** | `/agent-creator` | high | Create new specialized agents with trigger and tool selection guidance |
| **plugin-creator** | `/plugin-creator` | high | Create experimental opt-in plugin packs with manifests, conventions, and optional modules |
| **health** | `/health` | medium | Check health of project services (auto-detect) |
| **prd-to-issues** | `/prd-to-issues` | medium | Break PRD into GitHub issues with vertical slices and HITL/AFK tagging |
| **skill-audit** | `/skill-audit` | medium | Scan skills and agents for security risks: dangerous patterns, secrets, excessive permissions |
| **hipaa-validate** | `/hipaa-validate` | medium | Scan codebase for HIPAA compliance issues: PHI exposure, missing audit logging, unencrypted transmission/storage, access control gaps, temp file exposure, and missing BAA references |

## Hybrid Skills (31)

Hybrid skills combine slash-command invocation with domain knowledge that agents reference.

| Skill | Slash Command | Effort | Description |
|-------|---------------|--------|-------------|
| **explore** | `/explore` | medium | Explore and understand codebase structure and tech stack |
| **debug** | `/debug` | medium | Systematic debugging with logs, health checks, diagnostics (Tier 1 — single agent) |
| **review** | `/review` | high | Review code changes: quality, security, performance (Tier 1 — single agent) |
| **plan** | `/plan` | high | Create structured plan with task breakdown and agent assignments |
| **refactor** | `/refactor` | high | Plan and execute code refactoring with safety checks (Tier 1 — single agent) |
| **analyze** | `/analyze` | medium | Analyze code quality, complexity, and patterns |
| **cve-scan** | `/cve-scan` | medium | Scan project dependencies for known CVEs using native audit tools (npm, pip, composer, cargo, go, ruby, dart) |
| **docs** | `/docs` | high | Generate/update docs: README, API docs, architecture notes, changelogs (Tier 1 — single agent) |
| **search** | `/search` | medium | Search knowledge base (MCP tools with local fallback) |
| **explain** | `/explain` | medium | Explain architecture of a file/module using Mermaid diagrams |
| **orchestrate** | `/orchestrate` | max | Custom multi-agent parallelism — Tier 3, native in Claude, Codex-adapted to `spawn_agent` workflows |
| **swarm** | `/swarm` | max | Massive parallelism: map-reduce, consensus, relay — Tier 3 |
| **workflow** | `/workflow` | max | 15 predefined multi-agent workflow types — Tier 2, Codex-adapted to native subagent orchestration |
| **instinct-review** | `/instinct-review` | low | Review, curate, and manage learned instincts from past sessions |
| **teams** | `/teams` | max | Launch pre-configured Agent Teams compositions for common workflows |
| **write-a-prd** | `/write-a-prd` | high | Create PRD through interactive interview, codebase exploration, and module design |
| **prd-to-plan** | `/prd-to-plan` | high | Convert PRD into phased implementation plan using tracer-bullet vertical slices |
| **tdd** | `/tdd` | high | Test-driven development with red-green-refactor loop and vertical slices |
| **design-an-interface** | `/design-an-interface` | high | Generate 3+ radically different interface designs using parallel sub-agents |
| **grill-me** | `/grill-me` | medium | Stress-test a plan through relentless Socratic questioning |
| **ubiquitous-language** | `/ubiquitous-language` | medium | Extract DDD-style ubiquitous language glossary from conversation |
| **refactor-plan** | `/refactor-plan` | high | Create detailed refactor plan with tiny commits via user interview |
| **qa-session** | `/qa-session` | high | Interactive QA session — report bugs conversationally, file GitHub issues |
| **triage-issue** | `/triage-issue` | high | Triage bug with deep codebase exploration and TDD fix plan |
| **architecture-audit** | `/architecture-audit` | high | Discover shallow modules and propose module-deepening refactors |
| **subagent-development** | `/subagent-development` | high | Execute plans with 2-stage review (spec + quality) per task |
| **repeat** | `/repeat` | medium | Autonomous loop with safety controls (Ralph Wiggum pattern) |
| **mem-search** | `/mem-search` | medium | Search past coding sessions via natural language (memory-pack) |
| **persona** | `/persona` | low | Switch engineering persona at runtime (backend-lead, frontend-lead, devops-eng, junior-dev) |
| **council** | `/council` | high | 4-perspective decision evaluation (Advocate, Critic, Pragmatist, User-Proxy) with synthesis and confidence-rated recommendation. Tier 1, orchestrator, `context: fork`. |
| **introspect** | `/introspect` | medium | Agent self-debugging: classify failure pattern, suggest smallest recovery action, emit structured introspection report |

### `/workflow` types

| Type | Agents | Use case |
|------|--------|----------|
| `feature-development` | 8 | Full stack feature: plan → backend + frontend + DB + tests + security + docs |
| `backend-feature` | 5 | Backend only: API + logic + DB + tests + security |
| `frontend-feature` | 4 | UI: component + state + tests + docs |
| `api-design` | 7 | API contract → implement → test → benchmark → document |
| `database-evolution` | 7 | Schema change + migration + ORM update + tests + perf + security |
| `test-coverage` | 4 | Boost coverage: map gaps → unit tests + fixtures → review |
| `security-audit` | 7 | Multi-vector: OWASP + code + infra + DB → prioritize → report |
| `codebase-onboarding` | 6 | Read-only: structure + architecture + DB + tests + security → guide |
| `spike` | 7 | Research → feasibility → security + perf → architecture note |
| `debugging` | 5 | Diagnose → fix → test → document |
| `incident-response` | 3 | Triage → fix → postmortem |
| `performance-optimization` | 4 | Profile → optimize → benchmark → document |
| `infrastructure-change` | 5 | Design + implement + security + tests + runbook |
| `application-deploy` | 3 | Deploy → smoke test → release notes |
| `proactive-troubleshooting` | 4 | Investigate → check perf → preventive fix → docs |

## Knowledge Skills - Development (16)

| Skill | Directory | Domain |
|-------|-----------|--------|
| **app-builder** | `skills/app-builder/` | Full-stack application architecture |
| **api-patterns** | `skills/api-patterns/` | REST/GraphQL design, versioning, error handling |
| **database-patterns** | `skills/database-patterns/` | Schema design, indexing, query optimization |
| **flutter-patterns** | `skills/flutter-patterns/` | Flutter/Dart architecture, state management |
| **ecommerce-patterns** | `skills/ecommerce-patterns/` | E-commerce: catalog, cart, checkout, payments |
| **clean-code** | `skills/clean-code/` | Multi-language code quality: Python, TS, PHP, Go, Dart |
| **typescript-patterns** | `skills/typescript-patterns/` | TypeScript/JavaScript patterns for frontend and backend |
| **rust-patterns** | `skills/rust-patterns/` | Ownership, borrowing, error handling, Cargo, tokio, serde |
| **java-patterns** | `skills/java-patterns/` | Records, sealed classes, Stream API, Spring Boot, JUnit 5 |
| **csharp-patterns** | `skills/csharp-patterns/` | Nullable refs, async/await, ASP.NET Core, EF Core |
| **kotlin-patterns** | `skills/kotlin-patterns/` | Coroutines, DSLs, sealed classes, Ktor, MockK |
| **swift-patterns** | `skills/swift-patterns/` | Protocol-oriented, SwiftUI, async/await, SPM |
| **ruby-patterns** | `skills/ruby-patterns/` | Blocks, Rails conventions, RSpec, ActiveRecord |
| **design-engineering** | `skills/design-engineering/` | UI polish, animation craft, easing, transforms, accessibility |
| **documentation-standards** | `skills/documentation-standards/` | KB document conventions, frontmatter validation, category taxonomy |
| **brand-voice** | `skills/brand-voice/` | Anti-trope list, voice principles, LLM rhetoric prevention |

## Knowledge Skills - Infrastructure (6)

| Skill | Directory | Domain |
|-------|-----------|--------|
| **docker-devops** | `skills/docker-devops/` | Docker, deployment, infrastructure |
| **security-patterns** | `skills/security-patterns/` | OWASP, auth, encryption, vulnerability prevention |
| **ci-cd-patterns** | `skills/ci-cd-patterns/` | GitHub Actions, GitLab CI, Docker builds, Kubernetes |
| **observability-patterns** | `skills/observability-patterns/` | Logging, metrics, tracing, monitoring, SLOs |
| **testing-patterns** | `skills/testing-patterns/` | Multi-language TDD: pytest, vitest, phpunit, go test, flutter |
| **migration-patterns** | `skills/migration-patterns/` | Database migrations, API versioning, zero-downtime |

## Knowledge Skills - AI/RAG (2)

| Skill | Directory | Domain |
|-------|-----------|--------|
| **rag-patterns** | `skills/rag-patterns/` | RAG pipelines, chunking, reranking, evaluation |
| **mcp-patterns** | `skills/mcp-patterns/` | MCP protocol, server/client design, tools |

## Knowledge Skills - Process (7)

| Skill | Directory | Domain |
|-------|-----------|--------|
| **plan-writing** | `skills/plan-writing/` | Implementation plans, success criteria, pre-mortem |
| **debugging-tactics** | `skills/debugging-tactics/` | Iron Law 4-phase debugging: root cause → pattern → hypothesis → fix |
| **git-mastery** | `skills/git-mastery/` | Git workflows, branching, conflict resolution |
| **architecture-decision** | `skills/architecture-decision/` | Architecture notes, trade-off analysis, alternatives |
| **performance-profiling** | `skills/performance-profiling/` | Profiling, bottleneck analysis, optimization |
| **research-mastery** | `skills/research-mastery/` | Multi-source research, synthesis, fact-checking |
| **verification-before-completion** | `skills/verification-before-completion/` | Iron Law: evidence-before-claims, no completion without fresh verification |

## Knowledge Skills - Orchestration (1)

| Skill | Directory | Domain |
|-------|-----------|--------|
| **hive-mind** | `skills/hive-mind/` | Multi-agent aggregation, consensus, swarm patterns |

## Quality Guardrails

### Anti-Rationalization Tables

15 core skills include `## Common Rationalizations` — domain-specific tables of excuses and rebuttals that prevent agent drift and shortcut-taking:

| Skill | Example rationalization blocked |
|-------|---------------------------------|
| `/review` | "Small change, quick scan is enough" |
| `/debug` | "It must be a library bug" |
| `/refactor` | "It works, don't touch it" |
| `/tdd` | "Too simple to test" |
| `/plan` | "Planning is wasted time, just start coding" |
| `/docs` | "The code is self-documenting" |
| `/analyze` | "The linter is green, the code is fine" |
| `security-patterns` | "It's an internal API, security doesn't matter" |
| `testing-patterns` | "Tests slow down development" |
| `api-patterns` | "We'll version the API later" |
| `ci-cd-patterns` | "Manual deploys give us more control" |
| `clean-code` | "It's readable enough" |
| `performance-profiling` | "It feels slow, let me optimize this function" |
| `git-mastery` | "One big commit is simpler" |
| `database-patterns` | "We'll add indexes later when it's slow" |

### Confidence Scoring (`/review`)

The `/review` skill outputs structured findings with:
- **Severity**: critical / major / minor / nit
- **Confidence score**: 1-10 per finding with calibration guide
- **Evidence requirement**: each finding must include file:line + reasoning

### Self-Evaluation — LLM-as-Judge (`/review`)

After completing a review, the agent performs a self-evaluation pass:
1. Verify vs assume — did I read actual code for each finding?
2. Check the inverse — if X is a problem, is NOT-X also a problem elsewhere?
3. Detect anchoring bias — did early findings bias toward similar patterns?
4. Check unhappy paths — error handling, edge cases, failure modes
5. Calibrate confidence — overconfident? re-examine weakest finding

### Agent Verification Checklists

10 key agents include `## Verification Checklist` — exit criteria before presenting results:
`code-reviewer`, `test-engineer`, `security-auditor`, `debugger`, `backend-specialist`, `frontend-specialist`, `database-architect`, `performance-optimizer`, `devops-implementer`, `documenter`.

### Skill Reference Routing

7 core skills include `## Related Skills` sections suggesting logical follow-up skills:
`/review`, `/debug`, `/plan`, `/refactor`, `/tdd`, `/docs`, `/analyze`.

### Intent Capture Interview (`/onboard`)

Step 0 interview before setup — 5 targeted questions to capture undocumented project intent, customizing the generated `CLAUDE.md`.

---

## Advanced Features

### Effort Levels
- **low**: Mechanical operations (lint, build, fix, panic, index)
- **medium**: Standard operations (most skills)
- **high**: Complex reasoning (review, plan, refactor, docs, skill-creator)
- **max**: Multi-agent orchestration (orchestrate, swarm, workflow)

### Skill-Scoped Hooks
5 skills have lifecycle hooks:
- **commit**: PreToolUse — lint reminder before committing
- **test**: PostToolUse — coverage threshold reminder
- **deploy**: PostToolUse — health check reminder
- **migrate**: PreToolUse — backup reminder before migrations
- **rollback**: PostToolUse — verification reminder after rollback

### Skill Frontmatter Conventions
- `agent: <name>` — delegates to a specialized agent persona
- `context: fork` — runs skill in isolated forked context
- `allowed-tools: ...` — tools available to the agent when processing this skill
- `depends-on: skill-a, skill-b` — declares dependencies on other skills (validated by `validate.py`)

### Codex CLI Adaptation

Codex CLI receives the full skill catalog during `ai-toolkit install --local --editors codex`.

- Native Codex-compatible skills are symlinked directly into `.agents/skills/`
- Claude-oriented orchestration skills are generated as Codex wrappers
- Adapted wrappers translate `Agent`, `Team*`, and `Task*` guidance to `spawn_agent`, `send_input`, `wait_agent`, `close_agent`, and `update_plan`

Common adapted skills:

- `/orchestrate`
- `/workflow`
- `/swarm`
- `/teams`
- `/subagent-development`
- `/tdd`

The translated skill content keeps the original support assets (`reference/`,
`scripts/`, `assets/`) while replacing Claude-specific runtime instructions.

See `kb/reference/codex-cli-compatibility.md` for the detailed mapping and hook limits.

### Skill Dependencies (`depends-on`)
Skills can declare dependencies on other skills (primarily knowledge skills) for documentation and validation:
```yaml
depends-on: clean-code, api-patterns
```
- CSV list of skill directory names
- Validated by `validate.py` — each dep must exist as `app/skills/{dep}/SKILL.md`
- Reported in `evaluate_skills.py` quality metrics
- No runtime autoloading — Claude loads knowledge skills contextually based on topic matching

### SLM Compilation (`compile-slm`)

Compiles the full toolkit into a minimal system prompt for local Small Language Models (Ollama, LM Studio, Aider, Continue.dev). Pipeline: Parse → Score → Compress → Pack → Validate → Emit.

| Flag | Purpose |
|------|---------|
| `--model-size` | 7b/8b/14b/32b/70b — auto-selects budget + compression level |
| `--budget` | Token budget override (2K-16K) |
| `--persona` | Boost persona-relevant skills in scoring |
| `--lang` | Include language-specific rules |
| `--format` | Output: raw, ollama, json-string, aider |
| `--dry-run` | Preview included components + token utilization |

Profile `offline-slm` in `manifest.json` — installs core only, then compiles.

### Executable Scripts (18 total, stdlib-only, JSON output)

| Skill | Script | Purpose |
|-------|--------|---------|
| **commit** | `scripts/pre-commit-check.py` | Staged files, secrets detection |
| **test** | `scripts/detect-runner.py` | Auto-detect test framework |
| **lint** | `scripts/detect-linters.py` | Detect available linters |
| **build** | `scripts/detect-build.py` | Detect build system |
| **deploy** | `scripts/pre_deploy_check.py` | Pre-deployment readiness |
| **rollback** | `scripts/rollback_info.py` | Rollback context |
| **migrate** | `scripts/migration-status.py` | Detect migration tool, status |
| **ci** | `scripts/ci-detect.py` | Detect CI platform |
| **fix** | `scripts/error-classifier.py` | Classify lint/test errors |
| **pr** | `scripts/pr-summary.py` | Generate PR title/description |
| **review** | `scripts/diff-analyzer.py` | Parse git diff, categorize files |
| **debug** | `scripts/error-parser.py` | Parse stack traces |
| **explore** | `scripts/visualize.py` | Interactive HTML codebase tree |
| **explain** | `scripts/dependency-graph.py` | Import graph → Mermaid |
| **docs** | `scripts/doc-inventory.py` | Inventory docs, measure coverage |
| **refactor** | `scripts/refactor-scan.py` | Detect code smells |
| **health** | `scripts/health_check.py` | JSON health report |
| **analyze** | `scripts/complexity.py` | Code complexity metrics |
