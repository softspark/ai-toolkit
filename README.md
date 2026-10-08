# ai-toolkit

> AI coding toolkit with machine-enforced safety, 116 skills, 44 agents, lifecycle hooks, persona presets, opt-in plugin packs, and benchmark tooling.

[![Publish](https://github.com/softspark/ai-toolkit/actions/workflows/publish.yml/badge.svg)](https://github.com/softspark/ai-toolkit/actions/workflows/publish.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-116-brightgreen)](app/skills/)
[![Agents](https://img.shields.io/badge/agents-44-blue)](app/agents/)
[![Tests](https://img.shields.io/badge/tests-2008%20passing-success)](tests/)

## What's New in v5.3.3

- **The npm package no longer ships an `AGENTS.md`.** It was the toolkit's
  generated core, which nothing in the package read; `ai-toolkit agents-md`
  still prints it. This repository now keeps its own instructions in a
  committed `AGENTS.md`, like every toolkit-installed project.
- **Global first, then the project (v5.3.2).** `install --local` installs everything a
  client can load from `$HOME` before the project files, using the recorded
  global profile; `--no-global` opts out, and `update` keeps the profile.
- **Generated AGENTS.md stays out of CLAUDE.md (v5.3.1).** A toolkit-generated
  `AGENTS.md` (`# AI Toolkit Instructions`) is no longer imported, so Claude
  does not load rules from `~/.claude/rules/` twice; `adopt-agents-md` refuses
  to merge into it.
- **One AGENTS.md for every agent (v5.3.0).** Project instructions live in a committed
  `AGENTS.md` that `CLAUDE.md` imports; `ai-toolkit adopt-agents-md` moves an
  existing `CLAUDE.md` there, and nothing truncates it (Codex
  `project_doc_max_bytes` raised, 24,000-byte Antigravity warnings).
- **Working Antigravity hooks and rules.** Hooks run from the `hooks.json`
  directory and gate only `run_command`; workspace rules carry `trigger`
  frontmatter and fit Antigravity's size limits.
- **MCP rules follow the client's MCP config.** Registered rules that need an
  MCP server reach a file only when its readers have that server;
  `rag-mcp-legal-rules` is opt-in. Global Claude MCP installs reach every
  claude-switch profile.

See [CHANGELOG.md](CHANGELOG.md) for full history.

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

**Requirements:** Node.js >= 18 and Python >= 3.11.

> **macOS:** `/usr/bin/python3` is Python 3.9 and will not run the toolkit. Install a supported one with `brew install python@3.13` and make sure `which python3` no longer points at `/usr/bin/python3`.

```bash
# Option A: install globally (once per machine)
npm install -g @softspark/ai-toolkit
ai-toolkit install

# Option B: try without installing (npx)
npx @softspark/ai-toolkit install
```

**That's it.** Claude Code picks up 116 skills, 44 agents, quality hooks, and the safety constitution automatically.

Language knowledge skills (`rust-rules`, `kotlin-patterns`, ...) are scoped to the languages your registered projects use: once you have run `ai-toolkit install --local` in at least one project, the global install turns the other languages' skills off through `skillOverrides` in `~/.claude/settings.json` so their descriptions stop loading into every session. A new project in a new language turns its skills back on. `ai-toolkit install --language-skills all` keeps every language skill on and remembers that choice; `ai-toolkit doctor` shows the resulting context budget.

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

DeepSeek Harness (DSH) support is retired: `--editors dsh` is ignored with a warning and `ai-toolkit dsh ...` only prints manual cleanup steps. `ai-toolkit update --local` cleans up old DSH project skills, and DSH profiles are removed with DSH itself. See [DSH Compatibility (retired)](kb/reference/dsh-compatibility.md).

### All LLM Accounts

```bash
ai-toolkit llm-status                   # live limits for all configured Claude and Codex accounts
ai-toolkit llm-status --refresh         # same live query for both providers
ai-toolkit llm-status refresh           # equivalent spelling
ai-toolkit llm-status --verbose         # include paths, project mappings and timestamps
ai-toolkit llm-status --json            # combined provider/account data for scripts
```

The dashboard shows usage bars, reset times and active/default accounts for
each provider. It uses the
existing account registries below. Every invocation fetches current limits;
there is no disk quota cache or fallback to old readings. Failures appear on
the affected account. A failed provider configuration does not hide the other accounts.

### Claude Code Accounts per Project

Keep your existing Claude login as the default and assign separate profiles to
client directories:

```bash
ai-toolkit claude-switch init
ai-toolkit claude-switch add infinity --share-config
ai-toolkit claude-switch add play-reserve --share-config
ai-toolkit claude-switch bind /absolute/path/to/infinity infinity
ai-toolkit claude-switch bind /absolute/path/to/play-reserve play-reserve
ai-toolkit claude-switch login infinity
ai-toolkit claude-switch login play-reserve
ai-toolkit claude-switch run
```

Run `ai-toolkit claude-switch run` from a project directory to select its account.
Use `ai-toolkit claude-switch run --account infinity` for an explicit override.
Plain `claude` keeps its native behavior. Status lists all
configured profiles and live 5-hour/7-day subscription limits as usage bars
with reset countdowns and fetch timestamps. `status --verbose` adds configuration
paths, project mappings and exact timestamps. Claude limits are fetched using
each profile's OAuth credentials through Claude's internal usage endpoint,
whose availability can change. No model turn is submitted and no quota readings
are saved. `status --json` is available for scripts. Missing limits stay unknown;
authentication and network failures are shown explicitly per account.
See [Claude account profiles](kb/howto/claude-account-profiles.md) for shared
settings, authentication checks, and migration from older shell functions.

### Codex / OpenAI Accounts per Project

`ai-toolkit codex-switch` uses the same
project routing and compact status dashboard for Codex CLI accounts:

```bash
ai-toolkit codex-switch init
ai-toolkit codex-switch add infinity --share-config
ai-toolkit codex-switch bind /absolute/path/to/infinity infinity
ai-toolkit codex-switch login infinity
ai-toolkit codex-switch run
ai-toolkit codex-switch status --refresh
```

Named profiles use isolated `CODEX_HOME` directories and bypass the shared
daemon. The default keeps your existing login. Every `status` invocation reads
live account limits through the native app-server without starting a model turn. See
[Codex account profiles](kb/howto/codex-account-profiles.md) for setup,
configuration sharing, worktrees and supported CLI scope.

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
in Chat and Cowork; within the Claude app, hooks and sub-agents run in Cowork.
Account-enabled plugins also sync to Claude Code terminal sessions from 2.1.273.
The doctor reports possible collisions with the global install; required
organization plugins need an administrator decision.

### Native Codex Plugin

Build or validate the marketplace-ready Codex package without changing
`~/.agents` or `~/.codex`:

```bash
ai-toolkit codex-plugin export --output ai-toolkit-codex-plugin.zip
ai-toolkit codex-plugin verify
```

Extract the ZIP into a local marketplace under `plugins/ai-toolkit/`, add that
marketplace with `codex plugin marketplace add <marketplace-root>`, then install
from `/plugins` in Codex CLI and start a new session. Review and trust the
bundled hooks before use. The ZIP includes plugin-local persona definitions,
the briefing helper, the skill-audit helper and its local imports, and other
referenced skill resources. Export rejects symlinked output paths and ancestors.
The archive contains portable root `plugin.json` with OpenAI metadata under
`extensions.com.openai`, plus the `.codex-plugin/plugin.json` compatibility
manifest for older clients. Verification checks that both manifests agree.
Codex IDE does not support plugins.

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
| Claude Chat / Cowork | uploaded plugin ZIP + UI global/folder instructions + `claude_desktop_config.json` (MCP) | Cowork only | account/app |
| Cursor | `.cursor/rules/*.mdc` + `.cursor/mcp.json` + `.cursor/skills/*` | ✅ | project (`~/.cursor/mcp.json` for MCP only) |
| Windsurf (Devin Desktop) | `~/.config/devin/AGENTS.md` + `.devin/rules/*.md` + `.devin/hooks.v1.json` + `.windsurf/skills/*` | ✅ | global + project |
| Gemini CLI | `~/.gemini/GEMINI.md` + `.gemini/settings.json` + `.gemini/{commands,skills,agents}/` | ✅ | project + user |
| GitHub Copilot | Project: `.github/copilot-instructions.md` + `.github/{instructions,prompts,agents,skills,hooks}/` + `.github/mcp.json`; user: `$COPILOT_HOME/copilot-instructions.md` + `$COPILOT_HOME/{instructions,agents,skills,hooks}/` + `$COPILOT_HOME/mcp-config.json` | ✅ | project + user |
| Cline | Project: `.cline/{rules,hooks,skills}/` + `.clinerules/{hooks,workflows}/`; user: `~/.cline/{rules,hooks,skills}/` + `~/Documents/Cline/{Rules,Hooks}/` compatibility | ✅ | global + project |
| Roo Code / [Zoo Code](https://zoocode.dev/) | `~/.roo/rules/*.md` + `.roomodes` + `.roo/rules/*.md` | — | global rules + project |
| Aider | `~/.aider.conf.yml` + `.aider.conf.yml` + `CONVENTIONS.md` | — | global + project |
| Augment | `~/.augment/rules/*.md` + `.augment/rules/ai-toolkit-*.md` | ✅ | global + project |
| Google Antigravity | Project `.agents/{rules,workflows,skills,agents,hooks}/`; user `~/.gemini/config/{skills,agents,hooks}/`; opt-in native plugin export | ✅ | project + user |
| Codex CLI | Project: `.agents/skills/*` + `.codex/{agents,hooks}/` + `.codex/{hooks.json,config.toml}`; user: `$CODEX_HOME/{AGENTS.md,agents,hooks.json,config.toml}` + `$HOME/.agents/skills/*` | ✅ | project + user |
| opencode | `.opencode/{agents,commands,plugins,skills}/*` + `opencode.{json,jsonc}`; user `~/.config/opencode/AGENTS.md` | ✅ | project + global (`~/.config/opencode/`) |

> Claude Code is always installed (primary platform). Other editors are selected with `--editors`; the Claude app uses the separate `claude-app export` flow because its customization store is UI/plugin-managed, except for MCP servers, which `ai-toolkit mcp install --editor claude-app --scope global` writes straight to `claude_desktop_config.json`. The **Hooks** column marks platforms with lifecycle enforcement. Platforms marked — receive guidance without blocking hooks.

---

## What You Get

| Component | Count | Description |
|-----------|-------|-------------|
| `skills/` (task) | 32 | Slash commands: `/commit`, `/build`, `/deploy`, `/test`, `/mcp-builder`, ... |
| `skills/` (hybrid) | 33 | Slash commands with agent knowledge base |
| `skills/` (knowledge) | 51 | Domain knowledge auto-loaded by agents (includes 13 `<lang>-rules` skills) |
| `agents/` | 44 | Specialized agents across 10 categories |
| `hooks/` | 28 entries / 14 events + statusLine | Quality gates, path safety, prompt governance, loop guard, session lifecycle |
| `plugins/` | 2 packs | Opt-in packs that install files of their own (memory, enterprise) |
| `constitution.md` | 7 articles | Machine-enforced safety rules |
| `rules/` | auto-synced | Global/project rule files for Claude and other editors |
| `kb/` | reference docs | Architecture, procedures, and best practices |

---

## Architecture

```
ai-toolkit/
├── app/
│   ├── agents/          # 44 agent definitions
│   ├── skills/          # 116 skills (task / hybrid / knowledge)
│   ├── rules/           # Source rules synced into Claude/editor rule files
│   ├── hooks/           # Hook scripts (28 entries, 14 lifecycle events)
│   ├── claude-app/      # Generated Chat/Cowork plugin rules, hooks, instructions
│   ├── plugins/         # 2 experimental plugin packs (opt-in)
│   ├── output-styles/   # System prompt output style overrides
│   ├── constitution.md  # 7 immutable safety articles
│   └── ARCHITECTURE.md  # Full system design
├── kb/                  # Reference docs, procedures, plans
├── scripts/             # Validation, install, evaluation scripts
├── tests/               # Bats and Python test suite
└── CHANGELOG.md
```

**Distribution:** Symlink-based for agents/skills, copy-based for hooks. Run `ai-toolkit update` after `npm install` — all projects pick up changes instantly. See [Distribution Model](kb/reference/distribution-model.md).

---

## Key Features

**Machine-enforced constitution** — 7-article safety constitution enforced via `PreToolUse` hooks that actually block `rm -rf`, `DROP TABLE`, and irreversible operations. Not just documentation.

**29 lifecycle hook entries:** Executable handlers across 14 events (SessionStart → SessionEnd, plus InstructionsLoaded + ConfigChange). Guards, governance, quality gates, session persistence, MCP health checks, revert protection, test-cohesion enforcement, loop guard, secrets-at-rest reminders, and search-first discipline. See [Hooks Catalog](kb/reference/hooks-catalog.md).

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

**28 MCP templates** — Ready-to-use configs for GitHub, PostgreSQL, Slack, Jira, Sentry, general RAG, and Polish legal RAG. See [MCP Templates](kb/reference/mcp-templates.md).

See [Unique Features](kb/reference/unique-features.md) for detailed descriptions of all differentiators.

---

## Key Slash Commands

| Command | Purpose | Effort |
|---------|---------|--------|
| `/workflow <type>` | Pre-defined multi-agent workflow (16 types) | max |
| `/autonomous-dev` | Task-to-PR delivery with persistent state, review, QA and resume | high |
| `/prepare-test-env` | Prepare and verify the running app used by QA | high |
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
autonomous-development
```

### Multi-Agent Skill Selection

Claude Code uses Opus `high` for coordination, Sonnet `high` for bounded
implementation and tests, and Opus `xhigh` for hard debugging. If the official
Codex plugin is installed, enabled and available in the active agent catalog,
the supervisor can also assign work to Codex, preferring Astra `xhigh` for
security. Otherwise it keeps the available native agents and configured models.
Detection never installs or enables a plugin. See
[conditional model routing](kb/reference/model-compatibility.md#conditional-claude-to-codex-delegation).

```
Need multi-agent coordination?
├── Know your domains? → /orchestrate (ad-hoc, 3-6 agents)
├── Have a known pattern? → /workflow <type> (16 routes)
├── Need task-to-PR delivery with resume? → /autonomous-dev
├── Need consensus/map-reduce? → /swarm <mode>
├── Want Agent Teams API? → /teams (experimental)
└── Executing a plan? → /subagent-development
```

---

### Autonomous software delivery

```text
/autonomous-dev setup
/autonomous-dev run "Add CSV export for filtered orders"
/autonomous-dev run PROJ-123
/autonomous-dev list
/autonomous-dev resume <run-id>
/autonomous-dev status <run-id>
```

The process takes a brief, specification, issue or existing PR through planning,
implementation, project-specific validation, review, application QA and required
CI. It reuses the same PR and resumes from durable state. The default endpoint is
a ready PR; merge and deployment need separate authorization.

The current agent host performs the work. Bundled Python helpers maintain a
transactional run journal and check QA environment identity/readiness. They do
not launch an LLM or continue running after the host stops. Generated reports
stay outside the target repository, while `.ai-toolkit/autonomous.json` records
intentional project configuration. See the
[autonomous development guide](kb/howto/autonomous-development.md) for setup,
ownership, recovery, evidence and supported runtime boundaries.

The optional SoftSpark stack profile separates Jira task tracking, code-host
PR/CI and RAG knowledge. It refreshes task requirements and source-backed KB
context on resume, reconciles Jira comment receipts before retries and treats
Jira completion and KB indexing as explicit project lifecycle outcomes.

## Getting Started

1. **Customize AGENTS.md** — add your project's tech stack, commands, and conventions. Every coding agent reads it (Claude Code through the `@AGENTS.md` import that `install --local` keeps in `CLAUDE.md`); keep it under 24,000 bytes. An existing `CLAUDE.md` moves there with `ai-toolkit adopt-agents-md`.

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
| GitHub Copilot Compatibility | [kb/reference/copilot-compatibility.md](kb/reference/copilot-compatibility.md) |
| DSH Compatibility (retired) | [kb/reference/dsh-compatibility.md](kb/reference/dsh-compatibility.md) |
| Maintenance SOP | [kb/procedures/sop-maintenance.md](kb/procedures/sop-maintenance.md) |

---

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md) for responsible disclosure policy.

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

Fork it, modify it, ship it commercially. Three things the licence asks in return:

- **Keep the attribution.** Redistributions must carry the contents of [NOTICE](NOTICE) (§4d) — that is where the project name, copyright and source URL live.
- **Say what you changed.** Modified files must carry a prominent notice stating that you changed them (§4b).
- **Names are not included.** The licence grants no rights to the "ai-toolkit" or "SoftSpark" names or marks (§6).

Releases up to and including v4.20.0 were published under MIT and stay available under MIT; the change applies going forward and revokes nothing already granted. Contributions received while the project was MIT-licensed remain their authors' copyright and are redistributed under Apache 2.0 with the original MIT notice preserved in [NOTICE](NOTICE), as MIT requires.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

---

*Extracted from production use at SoftSpark. Built to be the toolkit we wished existed.*
