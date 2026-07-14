# ai-toolkit

> Professional-grade AI coding toolkit with multi-platform support. Machine-enforced safety, 108 skills, 44 agents, expanded lifecycle hooks, persona presets, experimental opt-in plugin packs, and benchmark tooling — works with Claude Code, Claude Chat/Cowork, Cursor, Devin, Copilot, Gemini, Cline, Roo/Zoo Code, Aider, Augment, Google Antigravity, Codex CLI, and opencode.

[![CI](https://github.com/softspark/ai-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/softspark/ai-toolkit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-108-brightgreen)](app/skills/)
[![Agents](https://img.shields.io/badge/agents-44-blue)](app/agents/)
[![Tests](https://img.shields.io/badge/tests-1228%20passing-success)](tests/)

## What's New in v4.14.1

v4.14.1 refreshes Claude model IDs to the current generation, makes model routing effort-aware, and tunes agent model tiers.

- **Current model IDs**: `scripts/_common.py` now resolves `opus → claude-opus-4-8` and `sonnet → claude-sonnet-5` (the single source of truth generators emit); stale `claude-opus-4-7` samples across skills refreshed.
- **Effort-aware routing**: `model-routing-patterns` gains an Effort section — tuning `output_config.effort` is the cheaper lever before swapping models, and it does not invalidate the prompt cache the way a mid-session model swap does.
- **Fable 5 tier documented**: added to the routing table with pricing and a "not the default best model" caveat — for "strongest model", the target stays `claude-opus-4-8`.
- **Agent tiers tuned**: `explorer-agent` (pure read/search) runs on `model: haiku`; `fact-checker` stays on `model: sonnet` — accuracy over cost for claim verification.

See [CHANGELOG.md](CHANGELOG.md) for full history.

---

## Table of Contents

- [Install](#install)
- [Platform Support](#platform-support)
- [What You Get](#what-you-get)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [Key Slash Commands](#key-slash-commands)
- [Getting Started](#getting-started)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)
- [Changelog](#changelog)

---

## Install

```bash
# Option A: install globally (once per machine)
npm install -g @softspark/ai-toolkit
ai-toolkit install

# Option B: try without installing (npx)
npx @softspark/ai-toolkit install
```

**That's it.** Claude Code picks up 108 skills, 44 agents, quality hooks, and the safety constitution automatically.

**Windows:** WSL is the recommended runtime. Native Windows works when Git Bash is available for hook scripts; dependency hints cover `winget`, Chocolatey, and Scoop. See [Windows Support](kb/reference/windows-support.md).

### Update

```bash
npm install -g @softspark/ai-toolkit@latest && ai-toolkit update
```

### Per-Project Setup

```bash
cd your-project/
ai-toolkit install --local                        # Claude Code only
ai-toolkit install --local --editors all          # + all editors
ai-toolkit install --local --editors cursor,aider # + specific editors
ai-toolkit update --local                         # auto-detects editors
```

### Plugin Management

```bash
ai-toolkit plugin list                            # show available packs
ai-toolkit plugin install --editor all --all      # install all for Claude Code + Codex
ai-toolkit plugin status --editor all             # show what's installed
```

### Claude Chat / Desktop / Cowork

The Claude app does not read Claude Code's `~/.claude/rules/` or `CLAUDE.md`.
Export and upload the app-native plugin instead:

```bash
ai-toolkit claude-app export --verify
# Claude > Customize > Plugins > + > Upload plugin
# Paste the generated *-global-instructions.md into:
# Settings > Cowork > Global instructions
```

Re-export and re-upload after toolkit or registered-rule updates. Skills work
in Chat and Cowork; hooks and sub-agents are active only in Cowork.

### Install Profiles

```bash
ai-toolkit install --profile minimal    # agents + skills only
ai-toolkit install --profile standard   # full install (default)
ai-toolkit install --profile strict     # full + git hooks
```

### Verify & Repair

```bash
ai-toolkit validate          # check integrity
ai-toolkit doctor --fix      # auto-repair
```

See [CLI Reference](kb/reference/cli-reference.md) for all commands and options.

---

## Platform Support

| Platform | Config Files | Hooks | Scope |
|----------|-------------|:-----:|-------|
| Claude Code | `~/.claude/agents`, `~/.claude/skills`, `~/.claude/rules/*.md`, `~/.claude/settings.json` | ✅ | global |
| Claude Chat / Cowork | uploaded plugin ZIP + UI global/folder instructions | Cowork only | account/app |
| Cursor | `.cursor/rules/*.mdc` + `.cursor/mcp.json` + `.cursor/skills/*` | ✅ | project (`~/.cursor/mcp.json` for MCP only) |
| Windsurf (Devin Desktop) | `~/.config/devin/AGENTS.md` + `.devin/rules/*.md` + `.devin/hooks.v1.json` + `.windsurf/skills/*` | ✅ | global + project |
| Gemini CLI | `~/.gemini/GEMINI.md` | ✅ | global |
| GitHub Copilot | `.github/copilot-instructions.md` + `.github/instructions/*` + `.github/prompts/*` + `AGENTS.md` | — | project |
| Cline | `~/Documents/Cline/Rules/*.md` + `~/.cline/skills/*` + `.clinerules/*.md` | — | global + project |
| Roo Code | `~/.roo/rules/*.md` + `.roomodes` + `.roo/rules/*.md` | — | global rules + project |
| Aider | `~/.aider.conf.yml` + `.aider.conf.yml` + `CONVENTIONS.md` | — | global + project |
| Augment | `~/.augment/rules/*.md` + `.augment/rules/ai-toolkit-*.md` | ✅ | global + project |
| Google Antigravity | `.agents/rules/*.md` + `.agents/workflows/*.md` + skill pointer in `.agent/skills/*` (IDE) and `.agents/skills/*` (CLI) | — | project |
| Codex CLI | `AGENTS.md` (coding rules inlined) + `.agents/skills/*` + `.codex/hooks.json` | ✅ | project + global plugin |
| opencode | `AGENTS.md` + `.opencode/{agents,commands,plugins}/*` + `opencode.json` | ✅ | project + global (`~/.config/opencode/`) |

> Claude Code is always installed (primary platform). Other editors are selected with `--editors`; the Claude app uses the separate `claude-app export` flow because its customization store is UI/plugin-managed. The **Hooks** column marks platforms with lifecycle enforcement. Platforms marked — receive guidance without blocking hooks.

---

## What You Get

| Component | Count | Description |
|-----------|-------|-------------|
| `skills/` (task) | 32 | Slash commands: `/commit`, `/build`, `/deploy`, `/test`, `/mcp-builder`, ... |
| `skills/` (hybrid) | 30 | Slash commands with agent knowledge base |
| `skills/` (knowledge) | 46 | Domain knowledge auto-loaded by agents (includes 13 `<lang>-rules` skills) |
| `agents/` | 44 | Specialized agents across 10 categories |
| `hooks/` | 28 entries / 14 events + statusLine | Quality gates, path safety, prompt governance, loop guard, session lifecycle |
| `plugins/` | 11 packs | Opt-in domain bundles (security, research, frontend, enterprise, 6 language packs) |
| `constitution.md` | 7 articles | Machine-enforced safety rules |
| `rules/` | auto-synced | Global/project rule files for Claude and other editors |
| `kb/` | reference docs | Architecture, procedures, and best practices |

---

## Architecture

```
ai-toolkit/
├── app/
│   ├── agents/          # 44 agent definitions
│   ├── skills/          # 108 skills (task / hybrid / knowledge)
│   ├── rules/           # Source rules synced into Claude/editor rule files
│   ├── hooks/           # Hook scripts (28 entries, 14 lifecycle events)
│   ├── claude-app/      # Generated Chat/Cowork plugin rules, hooks, instructions
│   ├── plugins/         # 11 experimental plugin packs (opt-in)
│   ├── output-styles/   # System prompt output style overrides
│   ├── constitution.md  # 7 immutable safety articles
│   └── ARCHITECTURE.md  # Full system design
├── kb/                  # Reference docs, procedures, plans
├── scripts/             # Validation, install, evaluation scripts
├── tests/               # Bats test suite (1228 tests)
└── CHANGELOG.md
```

**Distribution:** Symlink-based for agents/skills, copy-based for hooks. Run `ai-toolkit update` after `npm install` — all projects pick up changes instantly. See [Distribution Model](kb/reference/distribution-model.md).

---

## Key Features

**Machine-enforced constitution** — 7-article safety constitution enforced via `PreToolUse` hooks that actually block `rm -rf`, `DROP TABLE`, and irreversible operations. Not just documentation.

**29 lifecycle hooks** — Executable scripts across 14 events (SessionStart → SessionEnd, plus InstructionsLoaded + ConfigChange). Guards, governance, quality gates, session persistence, MCP health checks, revert protection, test-cohesion enforcement, loop guard, search-first discipline. See [Hooks Catalog](kb/reference/hooks-catalog.md).

**Security scanning** — `/skill-audit` for code-level risks, `/cve-scan` for dependency CVEs. Both CI-ready with exit codes.

**Iron Law enforcement** — `/tdd`, `debugging-tactics`, and `verification-before-completion` enforce non-negotiable gates with anti-rationalization tables. 15 skills total include rationalization resistance.

**Multi-language quality gates** — `Stop` hook runs lint + type checks across Python, TypeScript, PHP, Dart, Go after every response.

**Agent verification checklists** — 10 agents include exit criteria that must be met before presenting results.

**Two-stage review** — `/subagent-development` runs Implementer → Spec Review → Quality Review per task.

**Persistent memory** — `memory-pack` plugin: SQLite + FTS5 search across past sessions.

**Local product telemetry** — `ai-toolkit stats --summary` reports total invocations, skill coverage, unused catalog skills, recent activity, and top skills from local usage data.

**Persona presets** — 4 roles (backend-lead, frontend-lead, devops-eng, junior-dev) adjust style and priorities.

**Config inheritance** — Enterprise `extends` system with constitution immutability and enforcement constraints. See [Enterprise Config Guide](kb/reference/enterprise-config-guide.md).

**70 language rules** — 13 languages + common, 5 categories each. Auto-detected or explicit `--lang`. See [Language Rules](kb/reference/language-rules.md).

**26 MCP templates** — Ready-to-use configs for GitHub, PostgreSQL, Slack, Jira, Sentry, and more. See [MCP Templates](kb/reference/mcp-templates.md).

See [Unique Features](kb/reference/unique-features.md) for detailed descriptions of all differentiators.

---

## Key Slash Commands

| Command | Purpose | Effort |
|---------|---------|--------|
| `/workflow <type>` | Pre-defined multi-agent workflow (15 types) | max |
| `/orchestrate` | Custom multi-agent coordination (3–6 agents) | max |
| `/swarm` | Parallel Agent Teams: `map-reduce`, `consensus`, `relay` | max |
| `/plan` | Implementation plan with task breakdown | high |
| `/review` | Code review: quality, security, performance | high |
| `/debug` | Systematic debugging with diagnostics | medium |
| `/refactor` | Safe refactoring with pattern analysis | high |
| `/tdd` | Test-driven development with red-green-refactor | high |
| `/commit` | Structured commit with linting | medium |
| `/pr` | Pull request with generated checklist | medium |
| `/docs` | Generate README, API docs, architecture notes | high |
| `/explore` | Interactive codebase visualization | medium |
| `/write-a-prd` | Create PRD through interactive interview | high |
| `/prd-to-plan` | Convert PRD into vertical-slice implementation plan | high |
| `/design-an-interface` | Generate 3+ radically different interface designs | high |
| `/grill-me` | Stress-test a plan through Socratic questioning | medium |
| `/triage-issue` | Triage bug with deep investigation and TDD fix plan | high |
| `/architecture-audit` | Discover shallow modules, propose refactors | high |
| `/council` | 4-perspective decision evaluation | high |
| `/cve-scan` | Scan dependencies for known CVEs | medium |
| `/skill-audit` | Scan skills/agents for security risks | medium |
| `/repeat` | Autonomous loop with safety controls | medium |
| `/persona` | Switch engineering persona at runtime | low |

### `/workflow` Types

```
feature-development    backend-feature       frontend-feature
api-design             database-evolution    test-coverage
security-audit         codebase-onboarding   spike
debugging              incident-response     performance-optimization
infrastructure-change  application-deploy    proactive-troubleshooting
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

## Getting Started

1. **Customize CLAUDE.md** — add your project's tech stack, commands, and conventions at the top (above toolkit markers).

2. **Start using skills:**
   ```
   /onboard     # guided setup interview
   /explore     # understand your codebase
   /plan        # plan a feature
   ```

3. **Verify your install:**
   ```bash
   ai-toolkit validate
   ```

---

## Documentation

| Topic | Link |
|-------|------|
| CLI Reference | [kb/reference/cli-reference.md](kb/reference/cli-reference.md) |
| Unique Features | [kb/reference/unique-features.md](kb/reference/unique-features.md) |
| Architecture Overview | [kb/reference/architecture-overview.md](kb/reference/architecture-overview.md) |
| Hooks Catalog | [kb/reference/hooks-catalog.md](kb/reference/hooks-catalog.md) |
| Language Rules | [kb/reference/language-rules.md](kb/reference/language-rules.md) |
| MCP Templates | [kb/reference/mcp-templates.md](kb/reference/mcp-templates.md) |
| Extension API | [kb/reference/extension-api.md](kb/reference/extension-api.md) |
| Manifest Install | [kb/reference/manifest-install.md](kb/reference/manifest-install.md) |
| Plugin Packs | [kb/reference/plugin-pack-conventions.md](kb/reference/plugin-pack-conventions.md) |
| Enterprise Config | [kb/reference/enterprise-config-guide.md](kb/reference/enterprise-config-guide.md) |
| Distribution Model | [kb/reference/distribution-model.md](kb/reference/distribution-model.md) |
| Ecosystem Comparison | [kb/reference/comparison.md](kb/reference/comparison.md) |
| Codex CLI Compatibility | [kb/reference/codex-cli-compatibility.md](kb/reference/codex-cli-compatibility.md) |
| opencode Compatibility | [kb/reference/opencode-compatibility.md](kb/reference/opencode-compatibility.md) |
| Maintenance SOP | [kb/procedures/maintenance-sop.md](kb/procedures/maintenance-sop.md) |

---

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md) for responsible disclosure policy.

## License

MIT — see [LICENSE](LICENSE).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

*Extracted from production use at SoftSpark. Built to be the toolkit we wished existed.*
