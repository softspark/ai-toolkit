# ai-toolkit

> Professional-grade AI coding toolkit with multi-platform support. Machine-enforced safety, 91 skills, 44 agents, expanded lifecycle hooks, persona presets, experimental opt-in plugin packs, and benchmark tooling — works with Claude, Cursor, Windsurf, Copilot, Gemini, Cline, Roo Code, Aider, Augment, and Google Antigravity, ready in 60 seconds.

[![CI](https://github.com/softspark/ai-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/softspark/ai-toolkit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-92-brightgreen)](app/skills/)
[![Agents](https://img.shields.io/badge/agents-44-blue)](app/agents/)
[![Tests](https://img.shields.io/badge/tests-451%20passing-success)](tests/)

---

## Install

```bash
# Option A: install globally (once per machine)
npm install -g @softspark/ai-toolkit
ai-toolkit install

# Option B: try without installing (npx)
npx @softspark/ai-toolkit install
```

**That's it.** Claude Code picks up 91 skills, 44 agents, quality hooks, and the safety constitution automatically.

### Update

```bash
npm install -g @softspark/ai-toolkit@latest && ai-toolkit update
```

### Per-Project Setup

After global install, run `--local` in each project. By default, only Claude Code configs are installed (CLAUDE.md, settings, constitution, language rules). Add `--editors` for other tools:

```bash
cd your-project/
ai-toolkit install --local                     # Claude Code only
ai-toolkit install --local --editors all       # + all editors (Cursor, Windsurf, Cline, Roo, Aider, Augment, Copilot, Antigravity)
ai-toolkit install --local --editors cursor,aider  # + specific editors
ai-toolkit update --local                      # auto-detects editors from existing project files
```

### Plugin Management

```bash
ai-toolkit plugin list             # show available packs
ai-toolkit plugin install --all    # install all packs
ai-toolkit plugin update --all     # re-apply after toolkit updates
ai-toolkit plugin status           # show what's installed
ai-toolkit plugin clean memory-pack --days 30  # prune old data
```

After each `ai-toolkit update`, also run `ai-toolkit plugin update --all` to keep plugin hooks and scripts in sync.

### Install Profiles

```bash
ai-toolkit install --profile minimal    # agents + skills only (no hooks, no constitution)
ai-toolkit install --profile standard   # full install (default)
ai-toolkit install --profile strict     # full install + git hooks even without --local
```

### Persona Presets

Personas adjust communication style, preferred skills, and code review priorities per engineering role.

**Install-time (persistent — injected into CLAUDE.md):**

```bash
ai-toolkit install --persona backend-lead    # system design, API stability, data integrity
ai-toolkit install --persona frontend-lead   # component architecture, a11y, Core Web Vitals
ai-toolkit install --persona devops-eng      # infra-as-code, CI/CD, rollback safety
ai-toolkit install --persona junior-dev      # step-by-step explanations, learning focus
```

**Runtime (session-scoped — no reinstall needed):**

```bash
/persona backend-lead     # activate for this session
/persona --list           # show available personas
/persona --clear          # reset to default
```

### Selective Install / Update

```bash
ai-toolkit install --only agents,hooks   # first-time: only listed components
ai-toolkit install --skip hooks          # first-time: skip listed components
ai-toolkit update --only agents,hooks    # re-apply: only listed components
ai-toolkit update --skip cursor          # re-apply: skip listed components
ai-toolkit install --list                # dry-run: show what would be applied
```

### Verify & Repair

```bash
ai-toolkit validate           # check toolkit integrity
ai-toolkit validate --strict  # CI-grade: warnings = errors
ai-toolkit doctor             # diagnose install health, hooks, and artifact drift
ai-toolkit doctor --fix  # auto-repair: broken symlinks, missing hooks, stale artifacts
```

### Eject (standalone, no toolkit dependency)

```bash
ai-toolkit eject              # export to current directory
ai-toolkit eject /path/to    # export to custom directory
```

Replaces all symlinks with real files, inlines rules into CLAUDE.md, copies constitution and architecture. After eject you can `npm uninstall -g @softspark/ai-toolkit`.

---

## Platform Support

| Platform | Config Files | How | Scope |
|----------|-------------|-----|-------|
| Claude Code | `~/.claude/` | `ai-toolkit install` | global |
| Cursor | `~/.cursor/rules` + `.cursor/rules/*.mdc` | `ai-toolkit install` / `--local` | global + project |
| Windsurf | `~/.codeium/.../global_rules.md` + `.windsurf/rules/*.md` | `ai-toolkit install` / `--local` | global + project |
| Gemini CLI | `~/.gemini/GEMINI.md` | `ai-toolkit install` | global |
| GitHub Copilot | `.github/copilot-instructions.md` | `ai-toolkit install --local` | project |
| Cline | `.clinerules` + `.cline/rules/*.md` | `ai-toolkit install --local` | project |
| Roo Code | `.roomodes` + `.roo/rules/*.md` | `ai-toolkit install --local` | project |
| Aider | `.aider.conf.yml` + `CONVENTIONS.md` | `ai-toolkit install --local` | project |
| Augment | `.augment/rules/ai-toolkit-*.md` | `ai-toolkit install --local` | project |
| Google Antigravity | `.agent/rules/*.md` + `.agent/workflows/*.md` | `ai-toolkit install --local` | project |
| Codex / OpenCode | `AGENTS.md` | `ai-toolkit agents-md` | project |

> **Note:** Claude Code is always installed (primary platform with full feature support). Other editors are installed on demand with `--editors <list>` or auto-detected from existing project files. All platforms receive the same agent/skill catalog, guidelines, rules, language-specific rules, and registered custom rules. For editors lacking native bash lifecycle hooks, `--local` installs a Git hooks fallback (`.git/hooks/pre-commit`) to enforce quality gates pre-commit.

---

## What You Get

| Component | Count | Description |
|-----------|-------|-------------|
| `skills/` (task) | 29 | Slash commands: `/commit`, `/build`, `/deploy`, `/test`, `/skill-audit`, `/hipaa-validate`, ... |
| `skills/` (hybrid) | 31 | Slash commands with agent knowledge base |
| `skills/` (knowledge) | 32 | Domain knowledge auto-loaded by agents |
| `agents/` | 44 | Specialized agents across 10 categories |
| `hooks/` | 21 global + 5 skill-scoped | Quality gates, path safety, CLAUDE.md enforcement, notifications, prompt governance, subagent lifecycle, session-end handoff, usage tracking, config protection, MCP health, governance audit |
| `plugins/` | 11 experimental opt-in packs | Domain bundles for security, research, frontend, enterprise, and 6 language packs (not part of the default install) |
| `output-styles/` | 1 style | System prompt output style overrides (e.g. Golden Rules) |
| `constitution.md` | 5 articles | Machine-enforced safety rules |
| `rules/` | auto-injected | Rules injected into your CLAUDE.md on `install` / `update` |
| `kb/` | reference docs | Architecture, operating models, procedures, and best practices |

---

## Architecture

```
ai-toolkit/
├── app/
│   ├── agents/          # 44 agent definitions
│   │   ├── orchestrator.md
│   │   ├── backend-specialist.md
│   │   ├── security-architect.md
│   │   └── ... (41 more)
│   ├── skills/          # 91 skills (task / hybrid / knowledge)
│   │   ├── commit/      # /commit slash command
│   │   ├── review/      # /review slash command
│   │   ├── clean-code/  # knowledge skill (auto-loaded)
│   │   └── ... (87 more)
│   ├── rules/           # Auto-injected into your CLAUDE.md
│   ├── hooks/           # Hook scripts (copied to ~/.ai-toolkit/hooks/)
│   │   ├── session-start.sh      # MANDATORY reminder + session context
│   │   ├── guard-destructive.sh  # Block rm -rf, DROP TABLE, etc.
│   │   ├── guard-path.sh         # Block wrong-user path hallucination
│   │   ├── guard-config.sh       # Block edits to linter/formatter configs
│   │   ├── user-prompt-submit.sh # Prompt governance reminder
│   │   ├── quality-check.sh      # Multi-language lint on stop
│   │   ├── quality-gate.sh       # Block task completion on errors
│   │   ├── save-session.sh       # Persist session context
│   │   ├── subagent-start.sh     # Subagent scope reminder
│   │   ├── subagent-stop.sh      # Subagent completion checklist
│   │   ├── pre-compact.sh        # Save context before compaction
│   │   ├── pre-compact-save.sh   # Timestamped backup before compaction
│   │   ├── session-end.sh        # Session handoff snapshot
│   │   ├── post-tool-use.sh      # Lightweight feedback after edits
│   │   ├── mcp-health.sh         # MCP server availability check
│   │   ├── governance-capture.sh # Security-sensitive op logging
│   │   ├── commit-quality.sh     # Conventional commit advisory
│   │   ├── session-context.sh    # Environment snapshot on start
│   │   ├── track-usage.sh        # Skill invocation tracking
│   │   └── notify-waiting.sh     # Cross-platform "Claude waiting" notification
│   ├── hooks.json       # Hook definitions (merged into settings.json)
│   ├── plugins/         # Experimental plugin packs (opt-in, not part of default install)
│   ├── output-styles/   # System prompt output style overrides
│   ├── constitution.md  # 5 immutable safety articles
│   └── ARCHITECTURE.md  # Full system design
├── kb/                  # Reference docs, architecture notes, procedures, plans
├── scripts/             # Validation, install, evaluation scripts
├── tests/               # Bats test suite
└── CHANGELOG.md
```

**Distribution model:** Symlink-based for agents/skills, copy-based for hooks. `~/.claude/agents/` and `~/.claude/skills/` contain per-file symlinks into the npm package. Hook scripts are copied to `~/.ai-toolkit/hooks/` and referenced from `~/.claude/settings.json`. Run `ai-toolkit update` after `npm install` — all projects pick up changes instantly. (See [Distribution Model](kb/reference/distribution-model.md))

---

## Key Slash Commands

| Command | Purpose | Effort |
|---------|---------|--------|
| `/workflow <type>` | Pre-defined multi-agent workflow (15 types — see below) | max |
| `/orchestrate` | Custom multi-agent coordination (3–6 agents, you define domains) | max |
| `/swarm` | Parallel Agent Teams: `map-reduce`, `consensus`, or `relay` | max |
| `/plan` | Implementation plan with task breakdown | high |
| `/review` | Code review: quality, security, performance | high |
| `/debug` | Systematic debugging with diagnostics | medium |
| `/refactor` | Safe refactoring with pattern analysis | high |
| `/explore` | Interactive codebase visualization and discovery | medium |
| `/test` | Run tests (Python, JS/TS, PHP, Flutter, Go, Rust) | medium |
| `/deploy` | Deploy with pre-flight checks | medium |
| `/rollback` | Rollback deployment with state verification | medium |
| `/ci` | Generate CI/CD pipeline configuration | medium |
| `/migrate` | Database migration workflow | medium |
| `/commit` | Structured commit with linting | medium |
| `/pr` | Pull request with generated checklist | medium |
| `/docs` | Generate README, API docs, architecture notes, changelogs | high |
| `/hook-creator` | Scaffold a new Claude Code hook with validation conventions | high |
| `/command-creator` | Scaffold a new slash command with frontmatter and workflow guidance | high |
| `/agent-creator` | Scaffold a new specialized agent with tools and trigger guidance | high |
| `/plugin-creator` | Scaffold an experimental plugin pack with manifest and optional modules | high |
| `/skill-audit` | Scan skills/agents for security risks: dangerous patterns, secrets, permissions | medium |
| `/cve-scan` | Scan project dependencies for known CVEs using native audit tools (npm, pip, composer, cargo, go, ruby, dart) | medium |
| `/hipaa-validate` | Scan codebase for HIPAA compliance: PHI exposure, missing audit logging, unencrypted transmission/storage, access control gaps, temp file exposure, missing BAA references | medium |
| `/analyze` | Code quality, complexity, and pattern analysis | medium |
| `/fix` | Auto-fix lint/type errors | low |
| `/build` | Build with issue detection | low |
| `/lint` | Run linters and report issues | low |
| `/health` | Service health report | medium |
| `/panic` | Emergency halt all autonomous operations | low |
| `/write-a-prd` | Create PRD through interactive interview and module design | high |
| `/prd-to-plan` | Convert PRD into phased vertical-slice implementation plan | high |
| `/prd-to-issues` | Break PRD into GitHub issues with HITL/AFK tagging | medium |
| `/tdd` | Test-driven development with red-green-refactor loop | high |
| `/design-an-interface` | Generate 3+ radically different interface designs (parallel agents) | high |
| `/grill-me` | Stress-test a plan through relentless Socratic questioning | medium |
| `/ubiquitous-language` | Extract DDD-style glossary from conversation | medium |
| `/refactor-plan` | Plan refactor with tiny commits via interview | high |
| `/qa-session` | Interactive QA — report bugs, file GitHub issues | high |
| `/triage-issue` | Triage bug with deep investigation and TDD fix plan | high |
| `/architecture-audit` | Discover shallow modules, propose deepening refactors | high |
| `/subagent-development` | Execute plans with 2-stage review (spec + quality) per task | high |
| `/repeat` | Autonomous loop with safety controls (Ralph Wiggum pattern) | medium |
| `/mem-search` | Search past coding sessions via natural language (memory-pack) | medium |
| `/persona` | Switch engineering persona at runtime (session-scoped) | low |
| `/council` | 4-perspective decision evaluation (Advocate, Critic, Pragmatist, User-Proxy) | high |
| `/introspect` | Agent self-debugging with 7 failure pattern classification and recovery actions | medium |

### `/workflow` Types

```bash
/workflow feature-development    # New feature, full stack
/workflow backend-feature        # API + logic + tests
/workflow frontend-feature       # UI component + state + tests
/workflow api-design             # Design → implement → document
/workflow database-evolution     # Schema change + migration + code
/workflow test-coverage          # Boost coverage for a module
/workflow security-audit         # Multi-vector security assessment
/workflow codebase-onboarding    # Understand unfamiliar codebase
/workflow spike                  # Time-boxed research → architecture note
/workflow debugging              # Bug spanning multiple layers
/workflow incident-response      # Production down
/workflow performance-optimization  # Degradation >50%
/workflow infrastructure-change  # Docker, CI/CD, infra
/workflow application-deploy     # Full deploy workflow
/workflow proactive-troubleshooting  # Warning / trend analysis
```

### Multi-Agent Skill Selection

```
Need multi-agent coordination?
├── Know your domains? → /orchestrate (ad-hoc, 3-6 agents)
├── Have a known pattern? → /workflow <type> (15 templates)
├── Need consensus/map-reduce? → /swarm <mode>
├── Want Agent Teams API? → /teams (experimental)
└── Executing a plan? → /subagent-development
```

---

## Unique Differentiators

### 1. Machine-Enforced Constitution

Unlike other toolkits that put safety rules in documentation only, ai-toolkit enforces a 5-article constitution via `PreToolUse` hooks. The hook actually **blocks** execution of:
- Mass deletion (`rm -rf`, `DROP TABLE`)
- Blind overwrites of uncommitted work
- Any action that could cause irreversible data loss

### 2. Hooks as Executable Scripts

Hook logic lives in `app/hooks/*.sh` — not inline JSON one-liners. Scripts are copied to `~/.ai-toolkit/hooks/` on install and referenced from `~/.claude/settings.json`. Easy to read, debug, and extend.

**12 lifecycle events / 21 global hook entries:**

| Event | Script | Action |
|-------|--------|--------|
| SessionStart | `session-start.sh` | MANDATORY rules reminder + session context + instincts |
| SessionStart | `mcp-health.sh` | Check MCP server command availability (non-blocking warning) |
| SessionStart | `session-context.sh` | Capture environment snapshot (pwd, git branch, versions) to `~/.ai-toolkit/sessions/current-context.json` |
| Notification | *(inline)* | macOS desktop notification |
| PreToolUse | `guard-destructive.sh` | Block `rm -rf`, `DROP TABLE`, etc. |
| PreToolUse | `guard-path.sh` | Block wrong-user path hallucination |
| PreToolUse | `guard-config.sh` | Block edits to linter/formatter config files unless explicitly requested |
| PreToolUse | `commit-quality.sh` | Advisory validation of git commit messages (conventional commits, length, no WIP) |
| UserPromptSubmit | `user-prompt-submit.sh` | Prompt governance reminder for planning, research, and safe execution |
| UserPromptSubmit | `track-usage.sh` | Record skill invocations to local stats |
| PostToolUse | `post-tool-use.sh` | Lightweight validation reminders after edits |
| PostToolUse | `governance-capture.sh` | Log security-sensitive operations to `~/.ai-toolkit/governance.log` (JSONL) |
| Stop | `quality-check.sh` | Multi-language lint (ruff/tsc/phpstan/dart/go) |
| Stop | `save-session.sh` | Persist session context for cross-session continuity |
| TaskCompleted | `quality-gate.sh` | Block task completion on lint/type errors |
| SubagentStart | `subagent-start.sh` | Narrow-scope reminder for spawned subagents |
| SubagentStop | `subagent-stop.sh` | Completion checklist for subagent handoff |
| PreCompact | `pre-compact.sh` | Smart compaction: prioritized context (instincts > tasks > git state > decisions) |
| PreCompact | `pre-compact-save.sh` | Save timestamped context backup before compaction to `~/.ai-toolkit/compactions/` |
| SessionEnd | `session-end.sh` | Persist a session-end handoff note |
| TeammateIdle | *(inline)* | Completeness reminder |

**5 skill-scoped hooks:**

| Skill | Hook | Action |
|-------|------|--------|
| `/commit` | Pre | Run linter, block on failure |
| `/test` | Post | Coverage check, report threshold |
| `/deploy` | Post | Health check, rollback if degraded |
| `/migrate` | Pre | Backup verification |
| `/rollback` | Post | State verification |

### 3. Security Scanning

Two complementary security tools:

**`/skill-audit`** — scan skills and agents for code-level risks:

```bash
/skill-audit                              # Interactive (Claude remediation)
python3 scripts/audit_skills.py --ci      # CI mode: exit 1 on HIGH
```

Detects: `eval()`/`exec()`, hardcoded secrets, permission issues, bash risks.

**`/cve-scan`** — scan project dependencies for known CVEs:

```bash
/cve-scan                                 # Auto-detect ecosystems, scan all
python3 app/skills/cve-scan/scripts/cve_scan.py          # Direct invocation
python3 app/skills/cve-scan/scripts/cve_scan.py --json   # Machine-readable
```

Supports: npm, pip, composer, cargo, go, ruby, dart. Uses native audit tools — zero external deps.

**Severity levels:** HIGH (blocks CI), WARN (should fix), INFO (review)

### 4. Effort-Based Model Budgeting

Every skill declares an effort level used for model token budgeting:
- `low` — lint, build, fix (fast, cheap)
- `medium` — debug, analyze, ci
- `high` — review, plan, refactor, docs
- `max` — orchestrate, swarm, workflow

### 5. Multi-Language Quality Gates

The `Stop` hook runs after every response across 5 languages:

| Language | Lint | Type Check |
|----------|------|-----------|
| Python | ruff | mypy --strict |
| TypeScript | ESLint/tsc | tsc --noEmit |
| PHP | phpstan | phpstan |
| Dart | dart analyze | dart analyze |
| Go | go vet | go vet |

### 6. Iron Law Enforcement

Three skills enforce non-negotiable quality gates with anti-rationalization tables:

| Skill | Iron Law | What it prevents |
|-------|----------|-----------------|
| `/tdd` | `NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST` | Code written before test? Delete it. Start over. No exceptions. |
| `debugging-tactics` | `NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST` | 4-phase debugging: root cause → pattern → hypothesis → fix. 3+ failed fixes → question architecture. |
| `verification-before-completion` | `NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE` | Gate function: IDENTIFY → RUN → READ → VERIFY → CLAIM. "Should work now" is not evidence. |

Additionally, **15 core skills** include `## Common Rationalizations` tables — domain-specific excuses with rebuttals that prevent agent drift and shortcut-taking. Skills with rationalization tables: `/review`, `/debug`, `/refactor`, `/tdd`, `/plan`, `/docs`, `/analyze`, `security-patterns`, `testing-patterns`, `api-patterns`, `ci-cd-patterns`, `clean-code`, `performance-profiling`, `git-mastery`, `database-patterns`.

### Confidence Scoring & Self-Evaluation (`/review`)

The `/review` skill outputs findings with per-issue confidence scores (1-10) and severity classification (critical/major/minor/nit). After completing a review, an LLM-as-Judge self-evaluation pass checks for blind spots: anchoring bias, assumption vs verification, missing unhappy paths, and calibrates confidence scores.

### Agent Verification Checklists

10 key agents include `## Verification Checklist` — exit criteria that MUST be met before presenting results. Each checklist is domain-specific:

| Agent | Key exit criteria |
|-------|------------------|
| `code-reviewer` | Every finding has file:line + evidence, not just opinion |
| `security-auditor` | Each finding includes proof-of-concept or exploit path |
| `test-engineer` | No empty/placeholder tests, mocks only at boundaries |
| `debugger` | Root cause identified, regression test added |
| `backend-specialist` | Input validation, error format, query optimization |
| `frontend-specialist` | Empty/loading/error states, accessibility, responsive |
| `database-architect` | Migration tested on prod-like volume, rollback tested |
| `performance-optimizer` | Baseline measured, profiler evidence attached |
| `devops-implementer` | Dry run passed, rollback documented, no hardcoded secrets |
| `documenter` | Code examples runnable, no placeholders, valid links |

### Skill Reference Routing

7 core skills include `## Related Skills` sections that suggest logical follow-up skills, improving discoverability:

```
/review → found issues? → /debug, /tdd, /cve-scan, /analyze
/debug  → bug fixed?   → /review, /tdd, /workflow incident-response
/plan   → approved?    → /orchestrate, /write-a-prd, /grill-me
```

### Intent Capture Interview (`/onboard`)

The `/onboard` skill now includes a Step 0 interview phase before setup — asking 5 targeted questions to capture undocumented project intent (common contributor mistakes, protected files, deployment model, non-obvious constraints, review culture). Answers customize the generated `CLAUDE.md`.

### 7. Two-Stage Review (`/subagent-development`)

Per-task review pipeline inspired by [obra/superpowers](https://github.com/obra/superpowers):

```
Implementer → Spec Compliance Review → Code Quality Review → Next Task
```

- Implementer reports status: `DONE` / `DONE_WITH_CONCERNS` / `NEEDS_CONTEXT` / `BLOCKED`
- Spec reviewer verifies: all requirements met, nothing extra, nothing missing
- Quality reviewer checks: SOLID, naming, error handling, tests, security
- Prompt templates included: `reference/implementer-prompt.md`, `spec-reviewer-prompt.md`, `code-quality-reviewer-prompt.md`

### 8. Ralph Wiggum Loop (`/repeat`)

Autonomous agent loop with safety controls:

```bash
/repeat 5m /test          # run tests every 5 min until all pass
/repeat --iterations 3 /review   # max 3 review passes
```

| Safety Control | Default |
|----------------|---------|
| Max iterations | 5 |
| Circuit breaker | 3 consecutive failures → halt |
| Min interval | 1 minute |
| Exit detection | DONE / COMPLETE / ALL PASS |
| Stats logging | Every iteration to `stats.json` |

Constitution Article I, Section 4 enforces these limits.

### 9. Visual Brainstorming Companion

Optional browser-based companion for `/write-a-prd` and `/design-an-interface`:

- Ephemeral Node.js HTTP server (auto-kills after 30min idle)
- Dark theme, responsive, zero external dependencies
- Per-question routing: mockups/diagrams → browser, text/conceptual → terminal
- Consent-based: offered once as its own message, never forced

### 10. Persistent Memory (`memory-pack` plugin)

SQLite-based session memory (opt-in plugin pack):

| Component | Purpose |
|-----------|---------|
| `observation-capture.sh` | PostToolUse hook — captures tool actions to SQLite |
| `session-summary.sh` | Stop hook — AI-compress session observations |
| `mem-search` skill | FTS5 full-text search across past sessions |
| `<private>` tags | Content between tags stripped before storage |
| Progressive disclosure | Summary (~500 tok) → relevant (~2k tok) → full |



### 11. Persona Presets

4 engineering personas that adjust Claude's communication style per role:

| Persona | Focus | Key Skills |
|---------|-------|------------|
| `backend-lead` | System design, scalability, data integrity | `/workflow backend-feature`, `/tdd` |
| `frontend-lead` | Component architecture, a11y, Core Web Vitals | `/design-an-interface`, `/review` |
| `devops-eng` | IaC, CI/CD, blast radius, rollback safety | `/workflow infrastructure-change`, `/deploy` |
| `junior-dev` | Step-by-step explanations, learning focus | `/explain`, `/explore`, `/debug` |

Persistent via `--persona` at install time, or session-scoped via `/persona` runtime command.

### 12. KB Integration Protocol

Agents follow a research-before-action protocol enforced via rules:
1. `smart_query()` or `hybrid_search_kb()` before any technical answer
2. Source citation mandatory (`[PATH: kb/...]`)
3. Strict order: KB → Files → External Docs → General Knowledge

---

## MCP Templates

25 ready-to-use MCP server configuration templates. Install any with a single command:

```bash
ai-toolkit mcp add github slack           # add GitHub + Slack MCP servers
ai-toolkit mcp list                       # browse all 25 templates
ai-toolkit mcp show postgres              # inspect config before adding
```

Templates include: GitHub, PostgreSQL, Slack, Sentry, Context7, Brave Search, Supabase, Cloudflare, Vercel, and 16 more. Each is a validated JSON config fragment merged into `.mcp.json`.

---

## Language Rules

68 language-specific coding rules across 13 languages: TypeScript, Python, Go, Rust, Java, Kotlin, Swift, Dart, C#, PHP, C++, Ruby, plus common rules. Each language has 5 rule categories: coding-style, testing, patterns, frameworks, security.

```bash
ai-toolkit install --local                   # auto-detects project language, installs matching rules
ai-toolkit install --local --lang typescript  # explicit language selection
ai-toolkit install --local --lang go,python   # multiple languages
```

`--local` automatically detects languages using two-phase detection: config markers (package.json, go.mod, Cargo.toml, etc.) plus source file extension scanning (.py, .ts, .go, etc.). `--lang` accepts aliases (`go`, `c++`, `cs`). Rules are injected into `CLAUDE.md` and auto-updated on `ai-toolkit update --local`.

When `--editors` is used alongside detected or explicit languages, language rules are propagated to all configured editors — not just Claude. Each editor receives the full rule content in its native format:

| Editor | Language rule file | Activation |
|--------|-------------------|------------|
| Cursor | `.cursor/rules/ai-toolkit-lang-<lang>.mdc` | `globs` per file type (e.g. `**/*.py`) |
| Windsurf | `.windsurf/rules/ai-toolkit-lang-<lang>.md` | always loaded |
| Cline | `.cline/rules/ai-toolkit-lang-<lang>.md` | always loaded |
| Roo Code | `.roo/rules/ai-toolkit-lang-<lang>.md` | always loaded |
| Augment | `.augment/rules/ai-toolkit-lang-<lang>.md` | `auto_attached` with globs |
| Antigravity | `.agent/rules/ai-toolkit-lang-<lang>.md` | always loaded |

Registered rules (`ai-toolkit add-rule`) are also propagated to directory-based editor configs as `ai-toolkit-custom-<name>` files.

---

## Extension API

Generic API for external tools to inject rules and hooks into the toolkit:

```bash
# Rules — injected into CLAUDE.md with HTML markers
ai-toolkit inject-rule ./jira-rules.md    # idempotent, source-tagged block
ai-toolkit remove-rule jira-rules

# Hooks — injected into settings.json with _source tags
ai-toolkit inject-hook ./my-hooks.json    # idempotent, _source tagged
ai-toolkit remove-hook my-hooks
```

Injection is idempotent — re-running updates only the marked block, never touching content outside it. See [`kb/reference/extension-api.md`](kb/reference/extension-api.md).

---

## Manifest Install

Module-level install granularity. Install only what you need:

```bash
ai-toolkit install --modules core,agents,rules-typescript
ai-toolkit install --local                # auto-detects language, installs matching rules
ai-toolkit status                         # show installed modules and versions
ai-toolkit update                         # incremental re-install (only changed modules)
```

Install state is tracked in `~/.ai-toolkit/state.json`. See [`kb/reference/manifest-install.md`](kb/reference/manifest-install.md).

---

## Plugin Packs (Opt-in)

11 experimental plugin packs — domain bundles not part of the default install. Each pack bundles agents, skills, hooks, and/or rules for a specific domain.

| Pack | Domain | Agents | Skills | Hooks | Description |
|------|--------|--------|--------|-------|-------------|
| `security-pack` | security | 3 | 3 | 2 | Security auditing, threat modeling, OWASP checks |
| `research-pack` | research | 4 | 4 | 1 | Multi-source research, synthesis, fact-checking |
| `frontend-pack` | frontend | 3 | 3 | 1 | React/Vue/CSS craft, SEO, design engineering |
| `enterprise-pack` | enterprise | 3 | 3 | 3 | Executive briefings, infra architecture, status reporting |
| `memory-pack` | memory | 0 | 1 | 2 | SQLite-based persistent memory with FTS5 search across sessions |
| `rust-pack` | rust | 0 | 1 | 0 | Rust ownership, borrowing, Cargo, tokio, serde patterns |
| `java-pack` | java | 0 | 1 | 0 | Records, sealed classes, Spring Boot, JUnit 5 |
| `csharp-pack` | csharp | 0 | 1 | 0 | Nullable refs, async/await, ASP.NET Core, EF Core |
| `kotlin-pack` | kotlin | 0 | 1 | 0 | Coroutines, DSLs, sealed classes, Ktor, MockK |
| `swift-pack` | swift | 0 | 1 | 0 | Protocol-oriented, SwiftUI, async/await, SPM |
| `ruby-pack` | ruby | 0 | 1 | 0 | Blocks, Rails conventions, RSpec, ActiveRecord |

All packs have `status: experimental`. Each has a `plugin.json` manifest and `README.md` with installation instructions.

---

## Comparison

| Feature | ai-toolkit | everything-claude-code | wshobson/agents | ruflo |
|---------|---------------|----------------------|-----------------|-------|
| Skills | 91 | 100+ | 146 | 20+ |
| Agents | 44 | 30+ | 112 | 20+ |
| Machine-enforced constitution | **Yes** | No (docs only) | No | No |
| Skill-scoped lifecycle hooks | **Yes** | No | No | No |
| Effort-based model budgeting | **Yes** | No | No | No |
| Test suite | Yes (bats) | Yes (997 tests) | No | Yes |
| npm/npx install | Yes | Yes | Yes | Yes |
| Cross-tool support | **Cursor, Windsurf, Copilot, Gemini, Cline, Roo, Aider, Codex** | 5+ tools | Smithery | Limited |
| Selective install | Yes | Yes | Yes (72 plugins) | No |
| Session persistence | Yes | Yes | No | No |
| Architecture notes | **Yes** | No | No | No |
| KB/RAG integration | **Yes** | No | No | Yes |
| License | MIT | MIT | MIT | MIT |

---

## Agent Teams

Native support for `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` — automatically enabled during `ai-toolkit install` / `update` via `env` in `~/.claude/settings.json`.

Pre-configured team presets via `/teams`:

| Preset | Agents | Use Case |
|--------|--------|----------|
| `review` | code-reviewer, security-auditor, performance-optimizer | PR review |
| `debug` | debugger, backend-specialist, incident-responder | Multi-file bug |
| `feature` | orchestrator, backend-specialist, frontend-specialist, test-engineer | Full feature |
| `fullstack` | backend-specialist, frontend-specialist, database-architect, devops-implementer | Stack feature |
| `research` | technical-researcher, data-analyst, prompt-engineer | Deep research |
| `security` | security-architect, security-auditor, backend-specialist | Security audit |
| `migration` | database-architect, backend-specialist, devops-implementer | DB migration |

---

## Cross-Tool Support

| Tool | Config | Scope |
|------|--------|-------|
| Claude Code | `~/.claude/settings.json` (hooks), `~/.claude/` (agents, skills, constitution) | global |
| Cursor | `~/.cursor/rules` | global |
| Windsurf | `~/.codeium/windsurf/memories/global_rules.md` | global |
| Gemini CLI | `~/.gemini/GEMINI.md` | global |
| GitHub Copilot | `.github/copilot-instructions.md` | project |
| Cline | `.clinerules` | project |
| Roo Code | `.roomodes` | project |
| Aider | `.aider.conf.yml` | project |
| Codex / OpenCode | `AGENTS.md` | project |

```bash
# First-time install (Claude + Cursor + Windsurf + Gemini)
ai-toolkit install

# After npm update — re-apply updated components
ai-toolkit update

# Init project (Claude Code configs only: CLAUDE.md, settings, constitution, language rules)
ai-toolkit install --local

# Init with all editors (Cursor, Windsurf, Cline, Roo, Aider, Augment, Copilot, Antigravity)
ai-toolkit install --local --editors all

# Update project — auto-detects editors from existing config files
ai-toolkit update --local
```

> `install --local` prepares project files only. Hooks stay global and remain merged into `~/.claude/settings.json`. Git hooks are added as a safety fallback for editors without native hooks.

---

## Session Persistence

Context survives across Claude Code sessions:

```bash
# Enabled by default after install
# Saved to: .claude/session-context.md
# Loaded on: SessionStart hook
```

---

## Hook Runtime Profiles

```bash
# In .claude/settings.local.json
{
  "env": {
    "TOOLKIT_HOOK_PROFILE": "minimal"  # minimal | standard | strict
  }
}
```

| Profile | Description |
|---------|-------------|
| `minimal` | Destructive command guard only |
| `standard` | All hooks (default) |
| `strict` | Standard + coverage enforcement + strict type checks |

---

## Post-Install Setup

1. **Customize CLAUDE.md** — add your project's tech stack, commands, and conventions at the top (above the toolkit markers).

2. **Configure settings**:
   ```bash
   # .claude/settings.local.json
   {
     "mcpServers": { ... },
     "env": { "TOOLKIT_HOOK_PROFILE": "standard" }
   }
   ```

3. **Verify**:
   ```bash
   ai-toolkit validate
   ```

4. **Start**:
   ```
   /onboard     # guided setup
   /explore     # understand your codebase
   /plan        # plan a feature
   ```

---

## CLI Reference

```
Usage: ai-toolkit <command> [options]
```

| Command | Description |
|---------|-------------|
| `install` | First-time global install into `~/.claude/` + Cursor, Windsurf, Gemini |
| `install --local` | Claude Code configs only; add `--editors all` or `--editors cursor,aider` for other tools |
| `update` | Re-apply toolkit after `npm install -g @softspark/ai-toolkit@latest` |
| `update --local` | Re-apply + auto-detect editors from existing project files |
| `reset --local` | Wipe all project-local configs and recreate from scratch (clean slate) |
| `add-rule <rule.md> [name]` | Register rule in `~/.ai-toolkit/rules/` — auto-applied on every `update` |
| `remove-rule <name> [dir]` | Unregister rule from `~/.ai-toolkit/rules/` and remove its block from `CLAUDE.md` |
| `inject-hook <file.json>` | Inject external hooks into settings.json (idempotent, `_source` tagged) |
| `remove-hook <name>` | Remove injected hooks by source name |
| `mcp list` | List available MCP server templates (25 templates) |
| `mcp add <name> [names...]` | Add MCP server template(s) to `.mcp.json` |
| `mcp show <name>` | Show MCP template config details |
| `mcp remove <name>` | Remove MCP server from `.mcp.json` |
| `status` | Show installed modules and version |
| `update` | Re-install with saved modules (incremental) |
| `validate` | Verify toolkit integrity (`--strict` for CI-grade, warnings = errors) |
| `doctor` | Diagnose install health, hooks, quick-win assets, and artifact drift |
| `doctor --fix` | Auto-repair broken symlinks, missing hooks, stale artifacts |
| `eject [dir]` | Export standalone config (no symlinks, no toolkit dependency) |
| `plugin list` | Show available plugin packs with install status |
| `plugin install <name>` | Install a plugin pack (hooks, scripts, verify agents/skills) |
| `plugin install --all` | Install all 11 plugin packs |
| `plugin update <name>` | Update a plugin pack (remove + reinstall, preserves data) |
| `plugin update --all` | Update all installed plugin packs |
| `plugin clean <name> [--days N]` | Prune old plugin data (default: 90 days) |
| `plugin remove <name>` | Remove a plugin pack |
| `plugin status` | Show installed plugins with data stats (DB size, observation count) |
| `stats` | Show skill usage statistics (`--reset` to clear, `--json` for raw output) |
| `benchmark --my-config` | Compare your installed config vs toolkit defaults vs ecosystem |
| `benchmark-ecosystem` | Generate a benchmark snapshot for official Claude Code and external ecosystem repos |
| `create skill <name>` | Scaffold new skill from template (`--template=linter\|reviewer\|generator\|workflow\|knowledge`) |
| `sync` | Config portability via GitHub Gist (`--export`, `--push`, `--pull`, `--import`) |
| `evaluate` | Run skill evaluation suite |
| `uninstall` | Remove toolkit from `~/.claude/` |
| `cursor-rules` | Generate `.cursorrules` in current dir |
| `windsurf-rules` | Generate `.windsurfrules` in current dir |
| `copilot-instructions` | Generate `.github/copilot-instructions.md` in current dir |
| `gemini-md` | Generate `GEMINI.md` in current dir |
| `cline-rules` | Generate `.clinerules` in current dir |
| `roo-modes` | Generate `.roomodes` in current dir |
| `aider-conf` | Generate `.aider.conf.yml` in current dir |
| `conventions-md` | Generate `CONVENTIONS.md` for Aider (auto-loaded) |
| `augment-rules` | Generate `.augment/rules/ai-toolkit.md` (legacy single file) |
| `augment-dir-rules` | Generate `.augment/rules/ai-toolkit-*.md` (recommended) |
| `cursor-mdc` | Generate `.cursor/rules/*.mdc` for Cursor (recommended) |
| `windsurf-dir-rules` | Generate `.windsurf/rules/*.md` for Windsurf |
| `cline-dir-rules` | Generate `.cline/rules/*.md` for Cline |
| `roo-dir-rules` | Generate `.roo/rules/*.md` for Roo Code |
| `antigravity-rules` | Generate `.agent/rules/` and `.agent/workflows/` for Google Antigravity |
| `agents-md` | Regenerate `AGENTS.md` from agent definitions |
| `llms-txt` | Generate `llms.txt` and `llms-full.txt` |
| `generate-all` | Generate all platform configs at once |
| `help` | Show help |

**Options for `install` and `update`:**

```bash
ai-toolkit install --only agents,hooks   # apply only listed components
ai-toolkit install --skip hooks          # skip listed components
ai-toolkit install --profile minimal     # profile preset: minimal | standard | strict
ai-toolkit install --persona backend-lead # persona preset: backend-lead | frontend-lead | devops-eng | junior-dev
ai-toolkit install --local               # Claude Code only (CLAUDE.md, settings, constitution, language rules)
ai-toolkit install --local --editors all # Claude Code + all editors (Cursor, Windsurf, Cline, Roo, Aider, Augment, Copilot, Antigravity)
ai-toolkit install --local --editors cursor,aider  # Claude Code + specific editors
ai-toolkit update --local                # re-apply; auto-detects editors from existing project files
ai-toolkit install --list                # dry-run: show what would be applied
ai-toolkit install --modules core,agents,rules-typescript  # selective module install
ai-toolkit install --lang typescript     # explicit language for rules install
```

---

## Injecting Rules from Another Repo

Any repo can register its rules so they are automatically injected into all AI tool configs on every `update`:

```bash
cd /path/to/your-repo
ai-toolkit add-rule ./jira-rules.md
# Registered: 'jira-rules' → ~/.ai-toolkit/rules/jira-rules.md

ai-toolkit update
# → injects jira-rules into ~/.claude/CLAUDE.md, ~/.cursor/rules, Windsurf, Gemini
```

Rules are stored in `~/.ai-toolkit/rules/` and re-applied on every `update`. Injection is **idempotent** — re-running updates only the marked block, never touching content outside it.

To unregister:

```bash
ai-toolkit remove-rule jira-rules
# Removes from ~/.ai-toolkit/rules/ and strips the block from ~/.claude/CLAUDE.md
```

See [`kb/reference/integrations.md`](kb/reference/integrations.md) for known integrations.

---

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md) for responsible disclosure policy.

## License

MIT -- see [LICENSE](LICENSE).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

*Extracted from production use at SoftSpark. Built to be the toolkit we wished existed.*
