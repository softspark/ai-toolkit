---
title: "AI Toolkit - Architecture Overview"
category: reference
service: ai-toolkit
tags: [architecture, overview, design, structure]
version: "1.4.4"
created: "2026-03-23"
last_updated: "2026-04-12"
description: "Architecture of ai-toolkit: directory layout, global install model, editor-aware MCP install, Codex translation layer, skill tiers, and integration with projects."
---

# AI Toolkit Architecture

## Purpose

Shared, project-agnostic AI development toolkit for Claude Code (and compatible assistants like Cursor, Windsurf, Copilot, Gemini, Cline, Roo Code, Aider, Augment, and Google Antigravity). Provides specialized agents, skills (slash commands + knowledge), expanded lifecycle hooks, persona presets, and experimental opt-in plugin packs that teams can adopt separately from the default global install.

## Design Principles

1. **Global install** — one `~/.claude/` install works for all projects; no per-project setup beyond `init`
2. **Merge-friendly** — per-file symlinks, JSON merge, marker injection; user content never overwritten
3. **Composable** — agents reference skills; skills invoke agents; hooks validate all work
4. **Multi-language** — hooks and skills support Python, TypeScript, PHP, Dart, Go
5. **Cost-optimized** — simpler agents run on `sonnet`, complex reasoning on `opus`

## Directory Structure

```
ai-toolkit/
  bin/
    ai-toolkit.js        # CLI entry point (install, init, add-rule, ...)
  app/                       # All toolkit components
    agents/                  # Agent definitions (.md + YAML frontmatter)
    skills/                  # skills: task, hybrid, knowledge
    rules/                   # Rules auto-injected into ~/.claude/CLAUDE.md
    hooks/                   # Hook scripts (copied to ~/.softspark/ai-toolkit/hooks/)
    hooks.json               # Hook definitions (merged into ~/.claude/settings.json)
    constitution.md          # Immutable safety rules, 5 articles (marker-injected)
    ARCHITECTURE.md          # System architecture reference (marker-injected)
    CLAUDE.md.template       # Template for project CLAUDE.md (used by init)
    settings.local.json.template
    .claude-plugin/
      plugin.json            # Official plugin manifest
    plugins/                 # Experimental opt-in plugin packs + optional modules
  scripts/                   # All scripts
    install.py               # Global installer → ~/.claude/ (--local for project-local setup)
    uninstall.py             # Removes toolkit components from ~/.claude/
    inject_rule_cli.py       # Injects a rule into CLAUDE.md (delegates to inject_section_cli.py)
    inject_section_cli.py    # Marker-based content injection (canonical implementation)
    _common.py               # Shared helper for generators (frontmatter, agents/skills emission)
    merge-hooks.py           # JSON merge for hooks into settings.json (inject/strip modes)
    validate.py              # Toolkit integrity check
    evaluate_skills.py       # Skill quality report
    generate_agents_md.py    # Regenerates AGENTS.md
    generate_cursor_rules.py # Generates .cursorrules (sources _common.py)
    generate_windsurf.py     # Generates .windsurfrules (sources _common.py)
    generate_copilot.py      # Generates .github/copilot-instructions.md (sources _common.py)
    generate_gemini.py       # Generates GEMINI.md (sources _common.py)
    generate_cline.py        # Generates .clinerules (sources _common.py)
    generate_roo_modes.py    # Generates .roomodes
    generate_aider_conf.py   # Generates .aider.conf.yml
    generate_llms_txt.py     # Generates llms.txt
    install_git_hooks.py     # Installs fallback pre-commit hook
    plugin.py                # Plugin pack management (install, remove, list, status)
    benchmark_ecosystem.py   # Generates ecosystem benchmark snapshot
    harvest_ecosystem.py     # Writes machine-readable ecosystem harvest JSON
    compile_slm.py           # Compiles toolkit into minimal SLM system prompt (2K-16K tokens)
  tests/                     # Bats test suite
  benchmarks/                # Benchmark tasks + results
  kb/                        # Knowledge base
    reference/               # Catalogs, architecture, usage guides
    procedures/              # SOPs (install, maintenance)
    reference/               # architecture, operating models, and usage guides
```

## Install Model

All components use merge-friendly strategies — user content is never overwritten.

```
Machine (global)                              Project (local)
──────────────────────────────────────────    ──────────────────────────────────────
~/.claude/                                    ~/.softspark/ai-toolkit/
  agents/*.md    → per-file symlinks             rules/     ← registered rules
  skills/*/      → per-dir symlinks              hooks/     ← hook scripts (copied)
  settings.json  ← hooks merged here
  constitution.md ← marker injection            my-project/
  ARCHITECTURE.md ← marker injection              CLAUDE.md            ← project rules
  CLAUDE.md       ← marker injection (rules)      .claude/
                                                    settings.local.json  ← MCP, perms
                                                    constitution.md     ← marker injection
```

| Component | Strategy | Collision handling |
|-----------|----------|-------------------|
| `agents/*.md` | Per-file symlinks | User file with same name wins (toolkit skipped) |
| `skills/*/` | Per-directory symlinks | User dir with same name wins (toolkit skipped) |
| `settings.json` hooks | JSON merge via `merge-hooks.py` | User hooks + settings preserved, toolkit entries tagged with `_source` |
| `constitution.md` | Marker injection via `inject_section_cli.py` | User content outside `<!-- TOOLKIT:* -->` markers untouched |
| `ARCHITECTURE.md` | Marker injection via `inject_section_cli.py` | Same as above |
| `CLAUDE.md` | Marker injection via `inject_rule_cli.py` | Same as above |

**`ai-toolkit install`** — run once per machine, merges toolkit into `~/.claude/`. Auto-upgrades old whole-directory symlinks.

**`ai-toolkit update`** — re-apply after `npm install -g @softspark/ai-toolkit@latest` or after `add-rule` / `remove-rule`. Same as `install` but semantically correct for update flows.

**`ai-toolkit install --local`** — run per project. Always installs Claude Code configs (CLAUDE.md, settings.local.json, constitution.md, language rules). Editor configs are opt-in via `--editors`:
- `--editors all` — install all 9 editors (Cursor, Windsurf, Cline, Roo, Aider, Augment, Copilot, Antigravity, Codex)
- `--editors cursor,aider` — install only selected editors
- (no flag) — auto-detect from existing project files; `update --local` picks up whatever editors already have configs

Each editor gets directory-based format (`.cursor/rules/*.mdc`, `.windsurf/rules/*.md`, `.clinerules/*.md`, `.roo/rules/*.md`, `.augment/rules/ai-toolkit-*.md`, `.agent/rules/*.md`, `CONVENTIONS.md`). Codex local install additionally generates `AGENTS.md`, `.agents/rules/*.md`, `.agents/skills/*`, and `.codex/hooks.json`. Hooks are global-only — not merged into project settings except for editor-native local hook files such as Codex `.codex/hooks.json`.

If a project already has `.mcp.json`, local install mirrors its `mcpServers` entries into `.claude/settings.local.json` plus any selected editors with project-scoped native MCP files (`.cursor/mcp.json`, `.github/mcp.json`).

## CLI Commands

| Command | Target | What it does |
|---------|--------|-------------|
| `install` | `~/.claude/` | First-time: per-file symlinks + JSON merge + marker injection + rules |
| `install --local` | `./` | Claude Code configs + editors via `--editors` (auto-detect or explicit) |
| `update` | `~/.claude/` | Re-apply after npm update or after add-rule/remove-rule |
| `update --local` | `./` | Re-apply + refresh project-local configs |
| `uninstall` | `~/.claude/` | Strips toolkit components (preserves user content) |
| `add-rule <file>` | `~/.softspark/ai-toolkit/rules/` | Register rule — auto-applied on every `update` |
| `remove-rule <name>` | `~/.softspark/ai-toolkit/rules/` + `~/.claude/CLAUDE.md` | Unregister rule and remove its block |
| `mcp add <name...>` | `./.mcp.json` | Merge canonical MCP template(s) into project config |
| `mcp install --editor <name...>` | native editor config | Render MCP template(s) into editor-native config files |
| `validate` | toolkit | Integrity check |
| `doctor` | toolkit | Install health, hooks, benchmark freshness, and artifact drift diagnostics |
| `benchmark-ecosystem` | toolkit | Benchmark snapshot for official Claude Code and external ecosystem repos |
| `evaluate` | toolkit | Skill quality report |
| `cursor-rules` | `./` | Generates `.cursorrules` (legacy) |
| `cursor-mdc` | `./` | Generates `.cursor/rules/*.mdc` (recommended) |
| `windsurf-rules` | `./` | Generates `.windsurfrules` (legacy) |
| `windsurf-dir-rules` | `./` | Generates `.windsurf/rules/*.md` |
| `copilot-instructions` | `./` | Generates `.github/copilot-instructions.md` |
| `gemini-md` | `./` | Generates `GEMINI.md` |
| `cline-rules` | `./` | Generates `.clinerules` (legacy) |
| `cline-dir-rules` | `./` | Generates `.clinerules/*.md` |
| `roo-modes` | `./` | Generates `.roomodes` |
| `roo-dir-rules` | `./` | Generates `.roo/rules/*.md` |
| `aider-conf` | `./` | Generates `.aider.conf.yml` |
| `conventions-md` | `./` | Generates `CONVENTIONS.md` (Aider auto-loaded) |
| `augment-dir-rules` | `./` | Generates `.augment/rules/ai-toolkit-*.md` |
| `antigravity-rules` | `./` | Generates `.agent/rules/` + `.agent/workflows/` |
| `codex-md` | `./` | Generates Codex-facing `AGENTS.md` |
| `codex-rules` | `./` | Generates `.agents/rules/*.md` |
| `codex-hooks` | `./` | Generates `.codex/hooks.json` |
| `agents-md` | toolkit | Regenerates `AGENTS.md` |
| `llms-txt` | `./` | Generates `llms.txt` |
| `generate-all` | `./` | Generates all platform configs at once |

## Skill Tiers

Three tiers determine how to approach a task:

| Tier | Skills | When to use |
|------|--------|-------------|
| **1 — Quick single-agent** | `/debug`, `/review`, `/refactor`, `/analyze`, `/docs`, `/plan`, `/explain` | One concern, one file area, fast |
| **2 — Multi-agent workflow** | `/workflow <type>` | Cross-cutting task with a known pattern |
| **3 — Custom parallelism** | `/orchestrate`, `/swarm` | No predefined workflow matches |

### `/workflow` types (15)

| Type | Use case |
|------|----------|
| `feature-development` | New feature, full stack |
| `backend-feature` | Backend only: API + logic + tests |
| `frontend-feature` | UI component + state + tests |
| `api-design` | New API endpoint design → implement → document |
| `database-evolution` | Schema change + migration + code update |
| `test-coverage` | Boost test coverage for a module |
| `security-audit` | Multi-vector security assessment |
| `codebase-onboarding` | Understand unfamiliar codebase (read-only) |
| `spike` | Time-boxed technical research → architecture note |
| `debugging` | Bug spanning multiple layers |
| `incident-response` | Production down |
| `performance-optimization` | Degradation >50% |
| `infrastructure-change` | Docker, CI/CD, infra |
| `application-deploy` | Deploy |
| `proactive-troubleshooting` | Warning / trend |

## Skill Classification

| Type | Field | Invocation | Count |
|------|-------|-----------|-------|
| Task | `disable-model-invocation: true` | User via `/skill` only | 29 |
| Hybrid | (neither) | User via `/skill` + agent knowledge | 31 |
| Knowledge | `user-invocable: false` | Claude auto-loads | 32 |

## Multi-Agent Execution

Skills that spawn real parallel agents use:
- `agent: <name>` — delegates to a specialized agent persona
- `context: fork` — runs in isolated forked context
- `Agent` tool — spawns subagents in parallel within the agent's response

`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` must be set for Agent Teams (tmux-based) support.

### Codex Translation Layer

Codex does not expose Claude's `Agent`, `Team*`, and `Task*` primitives with the
same runtime semantics. To keep the skill catalog aligned, local Codex install
uses a translation layer:

- native Codex-compatible skills are linked directly
- Claude-only orchestration skills are emitted as generated wrappers
- wrapper guidance maps delegation to `spawn_agent`, `send_input`, `wait_agent`, `close_agent`, and `update_plan`

Codex therefore receives the full skill catalog, but not the full Claude hook
surface or tmux-backed Agent Teams lifecycle.

See `kb/reference/codex-cli-compatibility.md` for the detailed mapping.

## MCP Rendering Layer

`.mcp.json` is the canonical project-level template format. ai-toolkit can render that configuration into editor-native MCP files through `scripts/mcp_editors.py`.

Current native adapters:
- Claude Code: `.claude/settings.local.json` and `~/.claude/settings.json`
- Cursor: `.cursor/mcp.json` and `~/.cursor/mcp.json`
- GitHub Copilot: `.github/mcp.json` and `~/.copilot/mcp-config.json`
- Gemini CLI: `.gemini/settings.json` and `~/.gemini/settings.json`
- Windsurf: `~/.codeium/windsurf/mcp_config.json`
- Cline: `~/.cline/data/settings/cline_mcp_settings.json`
- Augment: `~/.augment/settings.json`
- Codex CLI: `~/.codex/config.toml`

See `kb/reference/mcp-editor-compatibility.md` for the support matrix and scope rules.

## Quality Guardrails

### Anti-Rationalization Tables
15 core skills include `## Common Rationalizations` tables — domain-specific excuses with rebuttals that prevent agent drift. Skills: `/review`, `/debug`, `/refactor`, `/tdd`, `/plan`, `/docs`, `/analyze`, `security-patterns`, `testing-patterns`, `api-patterns`, `ci-cd-patterns`, `clean-code`, `performance-profiling`, `git-mastery`, `database-patterns`.

### Confidence Scoring & LLM-as-Judge (`/review`)
Review findings include per-issue confidence scores (1-10) and severity tiers (critical/major/minor/nit). A self-evaluation pass after review checks for anchoring bias, assumption vs verification, and calibrates confidence.

### Agent Verification Checklists
10 agents have `## Verification Checklist` — domain-specific exit criteria: `code-reviewer`, `test-engineer`, `security-auditor`, `debugger`, `backend-specialist`, `frontend-specialist`, `database-architect`, `performance-optimizer`, `devops-implementer`, `documenter`.

### Skill Reference Routing
7 core skills include `## Related Skills` suggesting follow-up skills: `/review`, `/debug`, `/plan`, `/refactor`, `/tdd`, `/docs`, `/analyze`.

### Intent Capture Interview (`/onboard`)
Step 0 interview — 5 questions to capture undocumented project intent before setup.

## Component Relationships

```
Skills (/review, /deploy, /debug, ...)
    │
    ▼
Agents (code-reviewer, debugger, devops-implementer, ...)
    │
    ├── load: knowledge skills (clean-code, typescript-patterns, ...)
    │
    ├── validated by: hooks in settings.json (SessionStart, PreToolUse, UserPromptSubmit, PostToolUse, Stop, TaskCompleted, TeammateIdle, SubagentStart, SubagentStop, PreCompact, SessionEnd)
    │
    └── constrained by: constitution.md (5 safety articles)
```

## Quality Hooks

21 entries across 12 lifecycle events. See [hooks-catalog.md](hooks-catalog.md) for full details.

| Hook | Trigger | Script | Action |
|------|---------|--------|--------|
| SessionStart | Session start + compact | `session-start.sh` | MANDATORY rules reminder + session context + instincts |
| SessionStart | Session start | `mcp-health.sh` | Check MCP runtime availability |
| SessionStart | Session start | `session-context.sh` | Capture environment snapshot |
| Notification | Claude waiting for input | *(inline)* | macOS desktop notification |
| PreToolUse | Before Bash | `guard-destructive.sh` | Block destructive commands |
| PreToolUse | Before file ops (Bash, Read, Edit, Write, MultiEdit, Glob, Grep, NotebookEdit, mcp\_filesystem) | `guard-path.sh` | Block wrong-user path hallucination |
| PreToolUse | Before Edit/Write/MultiEdit | `guard-config.sh` | Block config file edits without explicit acknowledgment |
| PreToolUse | Before Bash (git commit) | `commit-quality.sh` | Advisory Conventional Commits format check |
| UserPromptSubmit | Before user prompt execution | `user-prompt-submit.sh` | Prompt governance reminder |
| UserPromptSubmit | Before user prompt execution | `track-usage.sh` | Record skill invocations to stats.json |
| PostToolUse | After edit/write tools | `post-tool-use.sh` | Lightweight validation reminders |
| PostToolUse | After any tool | `governance-capture.sh` | Log security-sensitive operations |
| Stop | After response | `quality-check.sh` | Multi-language lint |
| Stop | After response | `save-session.sh` | Persist session context |
| TaskCompleted | Agent Teams: task done | `quality-gate.sh` | Block completion on errors |
| TeammateIdle | Agent Teams: idle | *(inline)* | Completeness reminder |
| SubagentStart | Subagent spawn | `subagent-start.sh` | Scope reminder for subagents |
| SubagentStop | Subagent completion | `subagent-stop.sh` | Handoff checklist for subagents |
| PreCompact | Before compaction | `pre-compact.sh` | Save prioritized context: instincts > tasks > git state > decisions |
| PreCompact | Before compaction | `pre-compact-save.sh` | Timestamped context snapshot to audit trail |
| SessionEnd | Session end | `session-end.sh` | Persist handoff note for the next session |

Scripts at `~/.softspark/ai-toolkit/hooks/`. See [hooks-catalog.md](hooks-catalog.md) for details.

## Constitution (5 Articles)

| Article | Key Rule |
|---------|----------|
| I Safety First | No data loss, no blind execution, max 3 loop iterations |
| II Hierarchy of Truth | KB is source of truth, research protocol mandatory |
| III Operational Integrity | Green tests = Done, logs are evidence |
| IV Self-Preservation | Constitution is read-only, kill switch via system-governor |
| V Resource Governance | No destructive commands without confirmation |

## Persona Presets

Optional engineering personas injected via `ai-toolkit install --persona <name>`. Each persona adds role-specific communication style, preferred skills, and code review priorities to CLAUDE.md.

| Persona | Focus |
|---------|-------|
| `backend-lead` | System design, scalability, data integrity, API stability |
| `frontend-lead` | Component architecture, a11y, state management, Core Web Vitals |
| `devops-eng` | Infrastructure as code, CI/CD, rollback safety, observability |
| `junior-dev` | Step-by-step explanations, learning resources, small PRs |

Persona files live in `app/personas/*.md` and use the same `inject_rule` mechanism as registered rules.

## Skill Security Auditing

`/skill-audit` scans `app/skills/` and `app/agents/` for security risks:
- **Frontmatter**: overly permissive `allowed-tools`, knowledge skills with Bash
- **Scripts**: `eval()`, `exec()`, `os.system()`, `subprocess(shell=True)`, `pickle.loads`
- **Secrets**: AWS keys, GitHub PATs, private keys, hardcoded passwords
- **Bash**: `curl | bash`, unquoted variables, `chmod 777`

Severity levels: HIGH (blocks deployment), WARN (should fix), INFO (best practice). CI-ready with non-zero exit on HIGH findings.

## Agent Model Tiers

| Model | Purpose | Count |
|-------|---------|-------|
| opus | Complex reasoning, code generation, security | 32 |
| sonnet | Documentation, analysis, pattern-following | 15 |

## Extension Points

### MCP Templates
`app/plugins/mcp-templates/` contains 25 ready-to-use MCP server config templates. Opt-in via `ai-toolkit install --modules mcp-templates` or activated automatically with `--profile strict|full`.

### Language Rules
`app/rules/` provides language-specific rule files covering 13 languages (TypeScript, Python, Go, Rust, Java, Kotlin, Swift, Dart, C#, PHP, C++, Ruby, common). Auto-detected from project files via `--auto-detect` or selectable with `--modules rules-<lang>`. See README.md for current count.

### Extension API (`inject-hook`)
`inject_section_cli.py` provides a stable marker-based API for injecting content into `CLAUDE.md`, `constitution.md`, or `ARCHITECTURE.md` without overwriting user content.

### Manifest Install (`--modules`, `--auto-detect`)
`manifest.json` defines all installable components as named modules. Install individual modules with `ai-toolkit install --modules <name>` or enable auto-detection to select language rules based on files found in the project.
