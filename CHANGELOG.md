# Changelog

All notable changes to `ai-toolkit` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## v1.3.15 — Quality Guardrails: Anti-Rationalization, Confidence Scoring, Verification Checklists (2026-04-08)

### Added
- **Anti-rationalization tables** — 15 core skills now include `## Common Rationalizations` sections with domain-specific excuse/rebuttal tables that prevent agent drift and shortcut-taking. Inspired by [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills).
- **Confidence scoring** (`/review`) — review findings now include per-issue confidence scores (1-10) and severity classification (critical/major/minor/nit) with a calibration guide.
- **LLM-as-Judge self-evaluation** (`/review`) — structured self-check after review: blind spot detection, anchoring bias check, and confidence calibration.
- **Agent verification checklists** — 10 key agents (`code-reviewer`, `test-engineer`, `security-auditor`, `debugger`, `backend-specialist`, `frontend-specialist`, `database-architect`, `performance-optimizer`, `devops-implementer`, `documenter`) now include `## Verification Checklist` exit criteria.
- **Skill reference routing** — 7 core skills (`/review`, `/debug`, `/plan`, `/refactor`, `/tdd`, `/docs`, `/analyze`) include `## Related Skills` sections for follow-up discoverability.
- **Intent Capture Interview** (`/onboard`) — Step 0 interview phase with 5 targeted questions to capture undocumented project intent before setup.

---

## v1.3.14 — CVE Scanner + Open Contributions (2026-04-08)

### Added
- **`/cve-scan` skill** — auto-detect project ecosystems (npm, pip, composer, cargo, go, ruby, dart) and scan dependencies for known CVEs using native audit tools. Includes `cve_scan.py` scanner script with parsers for npm and pip-audit, unified severity report, `--fix` and `--json` modes.
- **CVE scan in security-auditor agent** — `/cve-scan` is now a mandatory first step in the OWASP A06 (Vulnerable Components) checklist.
- **CVE scan in `/workflow security-audit`** — security-auditor agent runs CVE scan as part of the parallel audit phase.
- **`security-audit` CI job** — `audit_skills.py --ci` now runs in GitHub Actions pipeline.
- **`CODE_OF_CONDUCT.md` in CI** — added to required files check.
- **`.github/CODEOWNERS`** — auto-assigns maintainer for review.
- **`.github/FUNDING.yml`** — GitHub Sponsors configuration.
- **GitHub Security Advisories** — added CVE/advisory procedure to `SECURITY.md`.
- **Open contribution workflow** — full `CONTRIBUTING.md` rewrite (fork, branch naming, commit conventions, CI requirements), PR checklist template, blank issues enabled.

### Removed
- **`close-prs.yml`** — removed auto-close workflow to accept external PRs.

### Fixed
- **Copyright** — `LICENSE` updated from `2024-present` to `2024-2026`.
- **`SECURITY.md`** — removed duplicate Scope section.

---

## v1.3.13 — CLI --version flag (2026-04-08)

### Added
- **`--version` / `-v` / `version` CLI flag** — prints clean semver string and exits 0 (previously fell through to "Unknown command" with exit 1).
- **3 new CLI tests** for `--version`, `-v`, and `version` subcommand.

---

## v1.3.12 — Cross-platform notifications + version check fix (2026-04-08)

### Fixed
- **Version check**: `ai-toolkit status` and session-start hook now read installed version from `state.json` instead of `package.json`, fixing false "up to date" when npm package was upgraded but `ai-toolkit update` not yet run.
- **Version check**: `status` forces a fresh npm check (no 24h cache) so user always sees real state.
- **Session-start hook**: `TOOLKIT_DIR` resolved via `npm root -g` instead of broken `../../` relative path from `~/.ai-toolkit/hooks/`.

### Changed
- **Notification hook**: replaced inline macOS-only `osascript` with cross-platform `notify-waiting.sh` script (macOS/Linux/Windows WSL).
- **Update notification**: session-start hook now shows desktop notification (macOS/Linux/Windows) when a new version is available.

---

## v1.3.11 — Proactive Context Checkpointing + Augment CLI (2026-04-08)

### Added
- **Constitution Art. I §5: Proactive Context Checkpointing** — agents must checkpoint `.claude/session-context.md` during multi-step tasks (objective, completed/pending steps, files modified, key decisions).
- **`augment-rules` CLI command** — wired `generate_augment.py` into `bin/ai-toolkit.js` GENERATORS + COMMANDS + `generate-all`. Generates `.augment/rules/ai-toolkit.md`.
- **Augment in Platform Support** — added to README table with project scope.

### Changed
- **`save-session.sh`** — enriched with git branch, dirty count, diff stat, and agent-written checkpoint preservation.
- **Language rules count** — corrected 70→68 in README.md (13 dirs × 5 + 3 standalone).
- **Secondary docs** — removed hardcoded rule counts from `language-rules.md`, `architecture-overview.md`, `competitive-features-implementation.md`; reference README for canonical count.
- **README architecture tree** — added missing `track-usage.sh`.

---

## v1.3.10 — Patch (2026-04-07)

### Fixed
- **Version cache**: `install` and `update` now clear `~/.ai-toolkit/version-check.json` so `status` shows correct "Latest" immediately after upgrade.

---

## v1.3.9 — Single Source of Truth for Counts (2026-04-07)

### Changed
- **Counts policy**: Hardcoded skill/agent/hook/test counts removed from all secondary docs. Only README.md, manifest.json, and package.json contain counts. Rule: `kb/best-practices/no-hardcoded-counts.md`.
- **47 new tests** (327 → 374): MCP manager, language auto-detect, install state, version check, new hooks, orphan cleanup.

### Fixed
- manifest.json version synced (was 1.0.0)
- plugin.json version synced (was 1.2.1)
- agents-catalog.md version aligned
- ARCHITECTURE.md hook event multipliers corrected
- Generator scripts no longer embed counts

---

## v1.3.8 — Language Rules as References (2026-04-07)

### Changed
- **Language rules injection**: Instead of inlining full rule content (~705 lines), `install --local` now injects lightweight reference pointers (~12 lines) with absolute paths to rule files. Claude reads them on demand via Read tool, keeping CLAUDE.md compact.
- **plugin.json**: Version synced from stale 1.2.1 to 1.3.8.

---

## v1.3.7 — Update Notifications (2026-04-07)

### Added
- **Update notifications**: `session-start.sh` hook checks npm for newer versions (cached 24h, non-blocking). `ai-toolkit status` shows installed vs latest version with upgrade command.

---

## v1.3.6 — Patch (2026-04-07)

### Fixed
- **Tests updated**: All hook tests now pass stdin JSON instead of env vars (matching hook changes from v1.3.5). 327/327 tests pass.

---

## v1.3.5 — Patch (2026-04-07)

### Fixed
- **Stats not counting**: `track-usage.sh` and `user-prompt-submit.sh` now read prompt from stdin JSON (`.prompt` field) instead of non-existent `CLAUDE_USER_PROMPT` env var. Skill invocations are now properly tracked in `~/.ai-toolkit/stats.json`.

---

## v1.3.4 — Patch (2026-04-07)

### Fixed
- **skills-catalog.md**: Added 6 missing language pattern skills (rust, java, csharp, kotlin, swift, ruby) to Development section (10→16). Total now correctly sums to 90.

---

## v1.3.3 — Patch (2026-04-07)

### Fixed
- **manifest.json missing from npm package**: Added `manifest.json` to `package.json` `files` array. Without it, `--auto-detect` and `--modules` could not read module definitions from installed package.

---

## v1.3.2 — Patch (2026-04-07)

### Fixed
- **Orphaned symlinks**: `install` and `update` now auto-clean broken agent/skill symlinks when components are removed or merged. Previously required manual `doctor --fix`.
- **`--auto-detect` without `--local`**: Now auto-adds `--local` with warning instead of scanning `$HOME` for language markers.
- **Session hooks concurrency**: `session-context.sh` writes per-session file (`${SESSION_ID}.json`) instead of single `current-context.json`. `pre-compact-save.sh` includes session ID in filename to avoid collisions.
- **Language rules injection**: `install --local` now actually injects detected language rules into project `.claude/CLAUDE.md` via `<!-- TOOLKIT:language-rules -->` markers.
- **`--local` implies `--auto-detect`**: No need to pass both flags — `install --local` automatically detects project language and installs matching rules.

---

## v1.3.0 — Competitive Features Release (2026-04-07)

### Added
- **Language Rules System**: 70 language-specific coding rules across 13 languages (TypeScript, Python, Go, Rust, Java, Kotlin, Swift, Dart, C#, PHP, C++, Ruby) + 5 common rules. 5 categories per language: coding-style, testing, patterns, frameworks, security.
- **MCP Templates**: 25 ready-to-use MCP server configuration templates (GitHub, PostgreSQL, Slack, Sentry, Context7, etc.) with CLI management (`ai-toolkit mcp add/list/show/remove`).
- **Extension API**: `inject-hook` / `remove-hook` commands for external tools to inject hooks into settings.json with unique `_source` tags. Parallels existing `inject-rule` / `remove-rule`.
- **Manifest-Driven Install**: Module-level install granularity (`--modules`), language auto-detection (`--auto-detect`), install state tracking (`~/.ai-toolkit/state.json`), `status` and `update` commands.
- **6 new hooks**: `guard-config.sh` (config file protection), `mcp-health.sh` (MCP server health check), `governance-capture.sh` (security audit logging), `commit-quality.sh` (conventional commits advisory), `session-context.sh` (environment snapshot), `pre-compact-save.sh` (pre-compaction backup).
- **`/council` skill**: 4-perspective decision evaluation (Advocate, Critic, Pragmatist, User-Proxy) for architectural decisions.
- **`/introspect` skill**: Agent self-debugging with 7 failure pattern classification and recovery actions.
- **`brand-voice` knowledge skill**: Anti-trope list preventing generic LLM rhetoric, auto-loaded when writing documentation.
- **KB reference docs**: extension-api.md, language-rules.md, mcp-templates.md, manifest-install.md.

### Changed
- Agent count: 47 → 44 (merged 3 overlapping pairs: rag-engineer into ai-engineer, research-synthesizer into technical-researcher, mcp-expert + mcp-server-architect into mcp-specialist)
- Hook count: 14 → 20 global hooks across 12 lifecycle events
- Skill count: 87 → 90 (28 task + 30 hybrid + 32 knowledge)
- Updated hooks-catalog.md, skills-catalog.md with new entries

---

## [1.2.1] - 2026-04-03

### Changed
- **README.md** — added full documentation for all v1.2.0 features:
  - `/persona` runtime switching with usage examples
  - `audit_skills.py` CI pipeline integration with `--json` and `--ci` flags
  - Skill Security Auditing section (severity levels, detection patterns)
  - Persona Presets section (table with focus areas and key skills per role)
  - Smart compaction description in hooks table
  - Fixed section numbering (was duplicated at 4, skipped 10)
- **CLAUDE.md** — added CRITICAL note: documentation/count accuracy is non-negotiable, must run validate + audit before every commit
- **skills-catalog.md** — fixed stale frontmatter (was 85 skills/v1.0.0, now 87 skills/v1.2.1)
- Version bump: 1.2.0 → 1.2.1 (package.json, plugin.json)

[1.2.1]: https://github.com/softspark/ai-toolkit/releases/tag/v1.2.1

---

## [1.2.0] - 2026-04-03

### Added
- **`/skill-audit` skill** — security scanner for skills and agents: detects dangerous code patterns (`eval`, `exec`, `os.system`), hardcoded secrets (AWS keys, GitHub PATs, private keys), overly permissive `allowed-tools`, and missing safety constraints. Supports `--fix` for auto-remediation of safe issues. CI-ready (non-zero exit on HIGH findings).
- **Persona presets** (`--persona` flag) — 4 engineering personas: `backend-lead`, `frontend-lead`, `devops-eng`, `junior-dev`. Each injects role-specific communication style, preferred skills, and code review priorities into CLAUDE.md. Usage: `ai-toolkit install --persona backend-lead`.
- **`/persona` runtime switching** — new hybrid skill to switch persona at runtime without re-install. Usage: `/persona backend-lead`, `/persona --list`, `/persona --clear`. Session-scoped.
- **Augment editor support** — `scripts/generate_augment.py` generates `.augment/rules/ai-toolkit.md` with proper frontmatter (`type: always_apply`). Registered in global install.
- **`scripts/audit_skills.py`** — deterministic Python scanner for CI pipelines. Scans skills/agents for dangerous patterns, secrets, permission issues. JSON output (`--json`), non-zero exit on HIGH (`--ci`). Found 4 real HIGH findings in our own toolkit.

### Changed
- **Smart compaction** (`pre-compact.sh`) — enhanced with prioritized context preservation: instincts (with confidence scores) > session context > git state (branch, dirty files, last commit) > key decisions. Replaces flat output with structured sections.
- Editor count: 8 → 9 (added Augment)
- Skill count: 85 → 87 (added `skill-audit`, `persona`)
- Task skill count: 27 → 28 (`skill-audit`)
- Hybrid skill count: 27 → 28 (`persona`)

[1.2.0]: https://github.com/softspark/ai-toolkit/releases/tag/v1.2.0

---

## [1.1.0] - 2026-04-02

### Added
- **Agent Teams auto-enabled** — `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is now automatically set in `~/.claude/settings.json` via `env` field during `install` / `update`. No manual `export` needed.
- 2 new install tests: env var injection + user env var preservation

### Fixed
- README test badge count: 308 → 310

[1.1.0]: https://github.com/softspark/ai-toolkit/releases/tag/v1.1.0

---

## [1.0.0] - 2026-04-02

### Added
- **85 skills** across task, hybrid, and knowledge categories
  - 27 task skills including `hook-creator`, `command-creator`, `agent-creator`, `plugin-creator`, and `/repeat` (Ralph Wiggum autonomous loop)
  - 27 hybrid skills (including PRD pipeline, TDD, design-an-interface, architecture-audit, QA session, `/subagent-development` with 2-stage review, `/mem-search`)
  - 31 knowledge skills (including 6 language-specific: Rust, Java, C#, Kotlin, Swift, Ruby; plus `verification-before-completion`)
- **47 specialized agents** across architecture, development, security, infrastructure, research, AI/ML, orchestration, and operations domains
- **15 global hook entries** including `UserPromptSubmit`, `PostToolUse`, `SubagentStart`, `SubagentStop`, `PreCompact`, `SessionEnd`, `track-usage.sh`, and `guard-path.sh`
- **5 skill-scoped hooks** for commit, test, deploy, migrate, and rollback workflows
- **Output style `Golden Rules`** — enforces critical rules at system prompt level (search-first, tool discipline, path safety, git conventions, language match, minimal changes)
- **`depends-on:` frontmatter field** for skill dependency declaration with validation and metrics
- **`ai-toolkit stats`** command with local usage tracking via `UserPromptSubmit` hook
- **`guard-path.sh` PreToolUse hook** — blocks file operations with wrong-user home directory paths (prevents path hallucination)
- **11 plugin packs** — 4 domain + 6 language-specific (Rust, Java, C#, Kotlin, Swift, Ruby) + memory-pack (SQLite-based persistent memory with FTS5 search)
- **`ai-toolkit plugin` CLI** — install, remove, list, and status for plugin packs (`plugin install <name>`, `plugin install --all`, `plugin remove`, `plugin list`, `plugin status`)
- **`ai-toolkit benchmark --my-config`** — compare installed config vs toolkit defaults vs ecosystem
- **`ai-toolkit create skill --template=TYPE`** — 5 templates: linter, reviewer, generator, workflow, knowledge
- **`ai-toolkit sync`** — config portability via GitHub Gist (`--export`, `--push`, `--pull`, `--import`)
- **Reusable GitHub Action** (`action.yml`) for CI validation
- `ai-toolkit doctor` / `doctor --fix` — install health, auto-repair broken symlinks, hooks, artifacts
- `ai-toolkit eject` — standalone copy, no toolkit dependency
- `benchmark-ecosystem` CLI command plus `scripts/benchmark-ecosystem.sh`
- `scripts/harvest-ecosystem.sh` plus machine-readable benchmark artifacts in `benchmarks/`
- Plugin manifest support in `app/.claude-plugin/plugin.json`
- Cross-tool generated artifacts for Claude, Cursor, Windsurf, Copilot, Gemini, Cline, Roo Code, Aider, and llms indexes
- **Roo Code support** — `ai-toolkit roo-modes` and `generate-roo-modes.sh`
- **Aider support** — `ai-toolkit aider-conf` and `generate-aider-conf.sh`
- **Git hooks safety fallback** — pre-commit hook for non-Claude editors
- **MCP defaults** — `app/mcp-defaults.json` template for `settings.local.json`
- **Install profiles** (`--profile minimal|standard|strict`)
- **`npx @softspark/ai-toolkit install`** — zero-friction trial without global install
- `--dry-run` flag as alias for `--list` in install/update
- MIT license — full open source, use/modify/distribute freely
- Global install into `~/.claude/` with merge-friendly propagation; hooks merged into `settings.json`, scripts copied into `~/.ai-toolkit/hooks/`
- Idempotent generators with `<!-- TOOLKIT:ai-toolkit START/END -->` markers
- CI: auto-regenerate `AGENTS.md` and `llms.txt` on push to main; publish on tags
- **DRY refactoring**: `scripts/_common.py` shared library for all generators and CLI scripts; `app/hooks/_profile-check.sh` for 9 hooks; CLI uses data-driven `GENERATORS` map
- All hooks standardized to `#!/usr/bin/env bash` shebang
- 310 tests across 16 test files
- **Iron Law enforcement** in TDD, debugging, and verification skills — anti-rationalization tables prevent agents from skipping test-first, root-cause analysis, or claiming completion without evidence
- **`/subagent-development`** — 2-stage review workflow: dispatch implementer → spec compliance review → code quality review per task, with 4-status protocol (DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, BLOCKED) and prompt templates
- **`/repeat`** — Ralph Wiggum autonomous loop pattern with safety controls: max iterations (default 5), circuit breaker (3 consecutive failures → halt), min interval (1 minute), exit detection, stats logging
- **`verification-before-completion`** — knowledge skill enforcing evidence-before-claims protocol: agents must run verification commands and read output before asserting success
- **Visual companion** for `/write-a-prd` and `/design-an-interface` — ephemeral local HTTP server renders mockups, diagrams, and comparisons in browser during brainstorming
- **Memory plugin pack** (`app/plugins/memory-pack/`) — SQLite-based persistent memory across sessions with FTS5 full-text search, PostToolUse observation capture, Stop session summary, `<private>` tag privacy controls, and progressive disclosure (summary → details → full)
- **`validate.py --strict`** — CI-grade validation treating warnings as errors, plus content quality checks (name=directory, non-empty body)
- **`doctor.py` stale rules detection** (Check 8) — detects rules in CLAUDE.md whose source files no longer exist in `~/.ai-toolkit/rules/`
- **Reasoning engine template** (`app/skills/skill-creator/templates/reasoning-engine/`) — generic Python stdlib search for domain skills with >50 categorized items, anti-pattern filtering, JSON stdout
- **Dashboard template** (`app/skills/skill-creator/templates/dashboard/index.html`) — single-file HTML dashboard parsing `stats.json` with skill usage charts
- **Anti-pattern registry format** documented at `kb/reference/anti-pattern-registry-format.md` — structured JSON schema with severity, auto-fixability, and conflict rules
- **Hierarchical override pattern** documented at `kb/reference/hierarchical-override-pattern.md` — SKILL.md + reference/*.md convention with explicit override semantics
- **Constitution Article I, Section 4** — Autonomous Loop Limits (max 5 iterations, circuit breaker, min interval, mandatory logging)
- **Python type hints and docstrings** on all skill scripts + merge-hooks.py — `from __future__ import annotations`, Google-style docstrings
- **CLI refactored** to data-driven dispatch — 170-line switch/case replaced by 14-line dispatch block
- **All scripts migrated from Bash to Python** — 51 Python scripts (stdlib-only, zero pip dependencies), hooks remain in Bash for startup speed. Shared library `scripts/_common.py` replaces `_generate-common.sh` + `inject-section.sh` + `inject-rule.sh`
- **`scripts/check_deps.py`** — dependency checker detects OS (macOS/Ubuntu/Fedora/Arch/Alpine/WSL), checks python3/git/node/sqlite3/bats, outputs ready-to-copy install commands. Integrated into `install.py` (blocks on missing deps) and `doctor.py` (enhanced environment check)

[1.0.0]: https://github.com/softspark/ai-toolkit/releases/tag/v1.0.0
