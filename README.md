# ai-toolkit

> Professional-grade AI coding toolkit with multi-platform support. Machine-enforced safety, 94 skills, 44 agents, expanded lifecycle hooks, persona presets, experimental opt-in plugin packs, and benchmark tooling — works with Claude, Cursor, Windsurf, Copilot, Gemini, Cline, Roo Code, Aider, Augment, Google Antigravity, Codex CLI, and opencode, ready in 60 seconds.

[![CI](https://github.com/softspark/ai-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/softspark/ai-toolkit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-94-brightgreen)](app/skills/)
[![Agents](https://img.shields.io/badge/agents-44-blue)](app/agents/)
[![Tests](https://img.shields.io/badge/tests-641%20passing-success)](tests/)

---

## What's New in v2.6.0

- **opencode integration** — `ai-toolkit install --editors opencode` generates `AGENTS.md`, `.opencode/agents/`, `.opencode/commands/`, plus a JS plugin bridging our Bash hooks to opencode's lifecycle events
- **opencode MCP merge** — `.mcp.json` servers are translated into `opencode.json` under the `mcp` key, preserving user-authored entries
- **Global opencode configs** — `~/.config/opencode/{AGENTS.md,agents/,commands/}` managed from `state.json`, auto-refreshed on `update`
- **Shared AGENTS.md** — opencode and Codex CLI both read the same `AGENTS.md` via distinct marker sections; installing both does not clobber either

## What's New in v2.5.0

- **`/seo-validate`** — 9-category SEO scanner with automated `seo-scanner.py` script (community contribution)
- **`/a11y-validate`** — WCAG 2.1/2.2 + EAA accessibility scanner with `a11y-scanner.py` script (community contribution)
- **Design Craft** — 7-domain impeccable design vocabulary in `frontend-specialist` + `frontend-lead` persona
- **GEO/AEO reference** — Answer Engine Optimization patterns for AI answer engines
- **94 skills** — 31 task + 31 hybrid + 32 knowledge

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

---

## Install

```bash
# Option A: install globally (once per machine)
npm install -g @softspark/ai-toolkit
ai-toolkit install

# Option B: try without installing (npx)
npx @softspark/ai-toolkit install
```

**That's it.** Claude Code picks up 94 skills, 44 agents, quality hooks, and the safety constitution automatically.

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
ai-toolkit plugin install --editor all --all      # install all for Claude + Codex
ai-toolkit plugin status --editor all             # show what's installed
```

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

| Platform | Config Files | Scope |
|----------|-------------|-------|
| Claude Code | `~/.claude/` | global |
| Cursor | `~/.cursor/rules` + `.cursor/rules/*.mdc` | global + project |
| Windsurf | `~/.codeium/.../global_rules.md` + `.windsurf/rules/*.md` | global + project |
| Gemini CLI | `~/.gemini/GEMINI.md` | global |
| GitHub Copilot | `.github/copilot-instructions.md` | project |
| Cline | `.clinerules/*.md` | project |
| Roo Code | `.roomodes` + `.roo/rules/*.md` | project |
| Aider | `.aider.conf.yml` + `CONVENTIONS.md` | project |
| Augment | `.augment/rules/ai-toolkit-*.md` | project |
| Google Antigravity | `.agent/rules/*.md` + `.agent/workflows/*.md` | project |
| Codex CLI | `AGENTS.md` + `.agents/rules/*.md` + `.agents/skills/*` + `.codex/hooks.json` | project + global plugin |

> Claude Code is always installed (primary platform). Other editors on demand with `--editors`. All platforms receive the same agent/skill catalog, guidelines, and registered custom rules.

---

## What You Get

| Component | Count | Description |
|-----------|-------|-------------|
| `skills/` (task) | 31 | Slash commands: `/commit`, `/build`, `/deploy`, `/test`, `/skill-audit`, ... |
| `skills/` (hybrid) | 31 | Slash commands with agent knowledge base |
| `skills/` (knowledge) | 32 | Domain knowledge auto-loaded by agents |
| `agents/` | 44 | Specialized agents across 10 categories |
| `hooks/` | 21 global + 5 skill-scoped | Quality gates, path safety, prompt governance, session lifecycle |
| `plugins/` | 11 packs | Opt-in domain bundles (security, research, frontend, enterprise, 6 language packs) |
| `constitution.md` | 5 articles | Machine-enforced safety rules |
| `rules/` | auto-injected | Language-specific and custom rules injected into your configs |
| `kb/` | reference docs | Architecture, procedures, and best practices |

---

## Architecture

```
ai-toolkit/
├── app/
│   ├── agents/          # 44 agent definitions
│   ├── skills/          # 94 skills (task / hybrid / knowledge)
│   ├── rules/           # Auto-injected into your CLAUDE.md
│   ├── hooks/           # Hook scripts (21 entries, 12 lifecycle events)
│   ├── plugins/         # 11 experimental plugin packs (opt-in)
│   ├── output-styles/   # System prompt output style overrides
│   ├── constitution.md  # 5 immutable safety articles
│   └── ARCHITECTURE.md  # Full system design
├── kb/                  # Reference docs, procedures, plans
├── scripts/             # Validation, install, evaluation scripts
├── tests/               # Bats test suite (641 tests)
└── CHANGELOG.md
```

**Distribution:** Symlink-based for agents/skills, copy-based for hooks. Run `ai-toolkit update` after `npm install` — all projects pick up changes instantly. See [Distribution Model](kb/reference/distribution-model.md).

---

## Key Features

**Machine-enforced constitution** — 5-article safety constitution enforced via `PreToolUse` hooks that actually block `rm -rf`, `DROP TABLE`, and irreversible operations. Not just documentation.

**21 lifecycle hooks** — Executable scripts across 12 events (SessionStart → SessionEnd). Guards, governance, quality gates, session persistence, MCP health checks. See [Hooks Catalog](kb/reference/hooks-catalog.md).

**Security scanning** — `/skill-audit` for code-level risks, `/cve-scan` for dependency CVEs. Both CI-ready with exit codes.

**Iron Law enforcement** — `/tdd`, `debugging-tactics`, and `verification-before-completion` enforce non-negotiable gates with anti-rationalization tables. 15 skills total include rationalization resistance.

**Multi-language quality gates** — `Stop` hook runs lint + type checks across Python, TypeScript, PHP, Dart, Go after every response.

**Agent verification checklists** — 10 agents include exit criteria that must be met before presenting results.

**Two-stage review** — `/subagent-development` runs Implementer → Spec Review → Quality Review per task.

**Persistent memory** — `memory-pack` plugin: SQLite + FTS5 search across past sessions.

**Persona presets** — 4 roles (backend-lead, frontend-lead, devops-eng, junior-dev) adjust style and priorities.

**Config inheritance** — Enterprise `extends` system with constitution immutability and enforcement constraints. See [Enterprise Config Guide](kb/reference/enterprise-config-guide.md).

**68 language rules** — 13 languages, 5 categories each. Auto-detected or explicit `--lang`. See [Language Rules](kb/reference/language-rules.md).

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
