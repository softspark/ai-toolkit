# AI Toolkit Architecture

Universal multi-agent system for software development. Works across all repositories.

## Quick Stats

| Component | Count |
|-----------|-------|
| Agents | 47 |
| Skills | 85 |
| Hooks | 12 events / 15 entries (SessionStart, Notification, PreToolUse ×2, UserPromptSubmit ×2, PostToolUse, Stop ×2, TaskCompleted, TeammateIdle, SubagentStart, SubagentStop, PreCompact, SessionEnd) |

---

## Agents (47)

### Orchestration & Planning (4)
| Agent | Model | Purpose |
|-------|-------|---------|
| `orchestrator` | opus | Multi-agent coordination, minimum 3 agents per task |
| `project-planner` | opus | Task breakdown, plan creation |
| `product-manager` | opus | Requirements, user stories, PRDs, backlog prioritization |
| `tech-lead` | opus | Code quality authority, architecture patterns, stack decisions |

### Development (5)
| Agent | Model | Purpose |
|-------|-------|---------|
| `backend-specialist` | opus | Node.js, Python, PHP, APIs |
| `frontend-specialist` | opus | React, Next.js, Vue, Nuxt |
| `mobile-developer` | opus | React Native, Flutter, native |
| `game-developer` | opus | Unity, Godot, Unreal, Phaser |
| `database-architect` | opus | Schema design, migrations, query optimization, operations |

### AI/ML (7)
| Agent | Model | Purpose |
|-------|-------|---------|
| `ai-engineer` | opus | LLM integration, vector search |
| `ml-engineer` | opus | Model training, MLOps |
| `nlp-engineer` | opus | NLP pipelines, text processing |
| `data-scientist` | opus | Statistics, analysis, visualization |
| `data-analyst` | sonnet | SQL, analytics, reporting |
| `prompt-engineer` | opus | Prompt design, optimization |
| `rag-engineer` | opus | RAG pipelines, retrieval |

### Quality & Security (6)
| Agent | Model | Purpose |
|-------|-------|---------|
| `code-reviewer` | opus | Code review, standards |
| `test-engineer` | opus | Test strategy, implementation |
| `qa-automation-engineer` | opus | E2E, API, performance testing |
| `security-auditor` | opus | Security audit, pen testing, OWASP, vulnerability assessment |
| `security-architect` | opus | Threat modeling, secure design, AuthN/AuthZ |
| `system-governor` | opus | Constitution guardian, VETO power |

### Infrastructure & DevOps (6)
| Agent | Model | Purpose |
|-------|-------|---------|
| `devops-implementer` | opus | CI/CD, automation |
| `infrastructure-architect` | opus | Cloud architecture, IaC |
| `infrastructure-validator` | sonnet | Infrastructure validation |
| `incident-responder` | sonnet | Incident management |
| `performance-optimizer` | opus | Performance tuning |
| `llm-ops-engineer` | opus | LLM operations, monitoring |

### Research & Documentation (6)
| Agent | Model | Purpose |
|-------|-------|---------|
| `explorer-agent` | sonnet | Codebase discovery (READ-ONLY) |
| `research-synthesizer` | opus | Research coordination, synthesis, reports |
| `technical-researcher` | opus | Deep technical investigation |
| `search-specialist` | sonnet | Search optimization |
| `fact-checker` | sonnet | Verification, source checking |
| `documenter` | sonnet | Documentation, KB management, SOPs, API docs |

### Management & Evolution (4)
| Agent | Model | Purpose |
|-------|-------|---------|
| `chief-of-staff` | sonnet | Executive summaries, daily briefings |
| `meta-architect` | opus | Self-optimization, agent definition updates |
| `predictive-analyst` | sonnet | Impact prediction, regression forecasting |
| `business-intelligence` | sonnet | Opportunity discovery, KPI gaps |

### Autonomous (2)
| Agent | Model | Purpose |
|-------|-------|---------|
| `night-watchman` | sonnet | Autonomous maintenance: dependency updates, dead code |
| `chaos-monkey` | opus | Resilience testing: fault injection, failure verification |

### MCP (3)
| Agent | Model | Purpose |
|-------|-------|---------|
| `mcp-expert` | opus | MCP protocol expertise |
| `mcp-server-architect` | opus | MCP server design |
| `mcp-testing-engineer` | sonnet | MCP testing |

### Specialist (4)
| Agent | Model | Purpose |
|-------|-------|---------|
| `debugger` | opus | Bug investigation, root cause |
| `code-archaeologist` | sonnet | Legacy code investigation |
| `command-expert` | sonnet | CLI, bash, automation |
| `seo-specialist` | sonnet | SEO optimization |

---

## Skills (85)

### Task Skills (27)
| Skill | Slash Command | Purpose |
|-------|---------------|---------|
| `commit` | `/commit` | Create well-structured git commits (Conventional Commits) |
| `pr` | `/pr` | Create GitHub pull request with template and checks |
| `test` | `/test` | Run tests (pytest, vitest, phpunit, flutter, go, cargo) |
| `build` | `/build` | Build project (auto-detects type) |
| `lint` | `/lint` | Run linting and type checking |
| `fix` | `/fix` | Auto-fix failing tests or lint errors |
| `deploy` | `/deploy` | Deploy to target environment with pre-checks |
| `rollback` | `/rollback` | Safe rollback (git, database, deployment) |
| `migrate` | `/migrate` | Database migration workflow |
| `ci` | `/ci` | Generate/manage CI/CD pipeline configuration |
| `panic` | `/panic` | Emergency halt all autonomous operations |
| `index` | `/index` | Reindex knowledge base with change detection |
| `onboard` | `/onboard` | Guided project setup with the toolkit |
| `night-watch` | `/night-watch` | Trigger autonomous maintenance cycle |
| `evolve` | `/evolve` | Trigger meta-architect self-optimization |
| `chaos` | `/chaos` | Run chaos engineering experiment |
| `predict` | `/predict` | Analyze code changes for impact and risks |
| `biz-scan` | `/biz-scan` | Scan for business value opportunities |
| `briefing` | `/briefing` | Generate executive summary of system status |
| `evaluate` | `/evaluate` | Evaluate RAG quality |
| `health` | `/health` | Health check (auto-detect services) |
| `skill-creator` | `/skill-creator` | Create new skills following Agent Skills standard |
| `hook-creator` | `/hook-creator` | Create new hooks with guided workflow and validation |
| `command-creator` | `/command-creator` | Create new slash commands with frontmatter and workflow guidance |
| `agent-creator` | `/agent-creator` | Create new specialized agents with tools and trigger guidance |
| `plugin-creator` | `/plugin-creator` | Create experimental opt-in plugin packs with manifests, conventions, and optional modules |
| `prd-to-issues` | `/prd-to-issues` | Break PRD into GitHub issues with vertical slices and HITL/AFK tagging |

### Hybrid Skills (27)
| Skill | Slash Command | Purpose |
|-------|---------------|---------|
| `explore` | `/explore` | Codebase exploration and tech stack discovery |
| `debug` | `/debug` | Systematic debugging with logs and diagnostics |
| `review` | `/review` | Code review for quality, security, performance |
| `plan` | `/plan` | Create structured plan with task breakdown |
| `refactor` | `/refactor` | Plan and execute code refactoring with safety checks |
| `analyze` | `/analyze` | Analyze code quality, complexity, and patterns |
| `docs` | `/docs` | Generate/update documentation (README, API docs, architecture notes) |
| `search` | `/search` | Search knowledge base (MCP + local fallback) |
| `explain` | `/explain` | Explain file/module architecture with Mermaid diagrams |
| `orchestrate` | `/orchestrate` | Multi-agent coordination for complex tasks |
| `swarm` | `/swarm` | Massive parallelism via Agent Teams |
| `workflow` | `/workflow` | Run agent workflow |
| `instinct-review` | `/instinct-review` | Review, curate, and manage learned instincts |
| `teams` | `/teams` | Launch pre-configured Agent Teams compositions |
| `write-a-prd` | `/write-a-prd` | Create PRD through interactive interview and module design |
| `prd-to-plan` | `/prd-to-plan` | Convert PRD into phased vertical-slice implementation plan |
| `tdd` | `/tdd` | Test-driven development with red-green-refactor loop |
| `design-an-interface` | `/design-an-interface` | Generate 3+ radically different interface designs |
| `grill-me` | `/grill-me` | Stress-test a plan through relentless Socratic questioning |
| `ubiquitous-language` | `/ubiquitous-language` | Extract DDD-style ubiquitous language glossary |
| `refactor-plan` | `/refactor-plan` | Create detailed refactor plan with tiny commits |
| `qa-session` | `/qa-session` | Interactive QA session with GitHub issue filing |
| `triage-issue` | `/triage-issue` | Triage bug with deep investigation and TDD fix plan |
| `architecture-audit` | `/architecture-audit` | Discover shallow modules and propose deepening refactors |
| `subagent-development` | `/subagent-development` | Execute plans with 2-stage review (spec + quality) per task |
| `repeat` | `/repeat` | Autonomous loop with safety controls (Ralph Wiggum pattern) |
| `mem-search` | `/mem-search` | Search past coding sessions via natural language (memory-pack) |

### Knowledge Skills - Development (15)
| Skill | Purpose |
|-------|---------|
| `app-builder` | Project scaffolding, tech stack |
| `api-patterns` | REST, GraphQL, JSON-RPC |
| `database-patterns` | Schema, queries, migrations |
| `flutter-patterns` | Flutter/Dart patterns |
| `ecommerce-patterns` | Magento, PrestaShop, etc. |
| `clean-code` | Multi-language code quality principles |
| `typescript-patterns` | TypeScript/JavaScript patterns for frontend and backend |
| `design-engineering` | UI polish, animation craft, easing, transforms, accessibility |
| `documentation-standards` | KB document conventions, frontmatter spec, category taxonomy |
| `rust-patterns` | Ownership, borrowing, Cargo, tokio, serde |
| `java-patterns` | Records, sealed classes, Spring Boot, JUnit 5 |
| `csharp-patterns` | Nullable refs, async/await, ASP.NET Core, EF Core |
| `kotlin-patterns` | Coroutines, DSLs, sealed classes, Ktor, MockK |
| `swift-patterns` | Protocol-oriented, SwiftUI, async/await, SPM |
| `ruby-patterns` | Blocks, Rails conventions, RSpec, ActiveRecord |

### Knowledge Skills - Infrastructure (6)
| Skill | Purpose |
|-------|---------|
| `docker-devops` | Docker, CI/CD |
| `security-patterns` | Auth, validation, security |
| `ci-cd-patterns` | GitHub Actions, GitLab CI, Kubernetes |
| `observability-patterns` | Logging, metrics, tracing, monitoring |
| `testing-patterns` | Multi-language testing strategies |
| `migration-patterns` | Database & API migration patterns |

### Knowledge Skills - AI/RAG (2)
| Skill | Purpose |
|-------|---------|
| `rag-patterns` | RAG, retrieval optimization |
| `mcp-patterns` | MCP server patterns |

### Knowledge Skills - Process (7)
| Skill | Purpose |
|-------|---------|
| `plan-writing` | Task breakdown, planning |
| `debugging-tactics` | Iron Law 4-phase debugging: root cause → pattern → hypothesis → fix |
| `git-mastery` | Safe history rewriting, bisect, complex merges |
| `architecture-decision` | Trade-off analysis, architecture note templates |
| `performance-profiling` | CPU, memory, I/O, database bottleneck profiling |
| `research-mastery` | Hierarchy of Truth protocol |
| `verification-before-completion` | Iron Law: evidence-before-claims, no completion without fresh verification |

### Knowledge Skills - Orchestration (1)
| Skill | Purpose |
|-------|---------|
| `hive-mind` | Swarm intelligence: Consensus, Aggregation |

---

## Orchestration Model

### 2-Phase Orchestration
```
Phase 1: PLANNING
├── Decompose task
├── Select agents (minimum 3)
├── Create dependencies
└── USER CHECKPOINT <- Approval required

Phase 2: IMPLEMENTATION
├── Execute in dependency order
├── Collect results
└── Generate report
```

### Agent Selection Matrix
| Task Type | Primary | Supporting |
|-----------|---------|------------|
| New Feature | backend/frontend | test-engineer, code-reviewer |
| Bug Fix | debugger | backend/frontend, test-engineer |
| Performance | performance-optimizer | database-architect |
| Security | security-auditor | code-reviewer |
| Research | research-synthesizer | technical-researcher, search-specialist |
| Documentation | documenter | explorer-agent |

---

## Directory Structure

```
.claude/
├── ARCHITECTURE.md      # This file
├── agents/              # Agent definitions (47)
├── hooks.json           # Quality gate hooks (multi-language)
├── skills/              # All skills: task, hybrid, knowledge (85)
├── output-styles/       # System prompt output style overrides (e.g. golden-rules)
├── constitution.md      # Immutable safety rules (5 articles)
└── settings.local.json  # Local settings + Agent Teams config
```

---

## Agent Teams Mode (Native Parallelism)

When `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is enabled:

```
Lead Session (You)
├── Teammate 1 (security-auditor) -> tmux pane 1
├── Teammate 2 (backend-specialist) -> tmux pane 2
├── Teammate 3 (test-engineer) -> tmux pane 3
└── Shared Task List
```

### Quality Hooks (`.claude/settings.json` → `hooks`)
| Hook | Trigger | Action |
|------|---------|--------|
| `SessionStart` | Session begins | Loads session context + active instincts |
| `PreToolUse` | Before Bash execution | Guards against destructive commands |
| `PreToolUse` | Before file ops (Read/Edit/Write/Glob/Grep) | Guards against wrong-user path hallucination |
| `UserPromptSubmit` | Before prompt execution | Prompt governance reminder |
| `UserPromptSubmit` | Before prompt execution | Usage tracking (skill invocations) |
| `PostToolUse` | After edit/write tools | Lightweight validation reminder |
| `Stop` | After Claude response | Multi-language quality check + saves session context |
| `TaskCompleted` | Teammate marks task done | Multi-language lint + type check (blocking) |
| `TeammateIdle` | Teammate goes idle | Reminds to verify completeness |
| `SubagentStart` | Subagent starts | Scope reminder for spawned subagents |
| `SubagentStop` | Subagent completes | Handoff checklist for spawned subagents |
| `Notification` | Claude notification | OS notification |
| `PreCompact` | Before compaction | Saves context before compaction boundary |
| `SessionEnd` | Claude session ends | Writes handoff snapshot for the next session |

---

## Principles

1. **Universal**: No project-specific references
2. **KB-First**: Always search before answering
3. **Multi-Agent**: Minimum 3 agents for complex tasks
4. **2-Phase**: Plan -> Approve -> Implement
5. **Read-Only Exploration**: Explorer agent never writes
6. **Cite Sources**: Always include `[PATH: ...]`
7. **Multi-Language**: All tools, hooks, and skills support multiple tech stacks
