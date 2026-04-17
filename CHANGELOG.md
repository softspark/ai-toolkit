# Changelog

All notable changes to `ai-toolkit` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## v2.6.0 — opencode Integration (2026-04-15)

### Added
- **opencode editor support** — `ai-toolkit install --editors opencode` generates a full native integration: `AGENTS.md` (shared with Codex via distinct marker sections), `.opencode/agents/ai-toolkit-*.md` (44 subagents), `.opencode/commands/ai-toolkit-*.md` (62 slash commands), `.opencode/plugins/ai-toolkit-hooks.js` (JS plugin bridging Bash hooks to opencode lifecycle events), and `opencode.json` with MCP servers merged from `.mcp.json`.
- **Global opencode configs** — `ai-toolkit install --editors opencode` (without `--local`) installs the **complete surface** to `~/.config/opencode/{AGENTS.md, agents/, commands/, plugins/ai-toolkit-hooks.js, opencode.json}`. Tracked in `state.json`, auto-refreshed on `update`. (Earlier pre-release iteration shipped only AGENTS.md/agents/commands globally; plugin and opencode.json are now also installed globally so hooks and MCP work without `--local`.)
- **Expanded hook coverage** — plugin now bridges `session.compacted` → `pre-compact.sh` + `pre-compact-save.sh`, `permission.asked` → `guard-destructive.sh`, and `command.executed` → `post-tool-use.sh` on top of the original session/tool/message events. Maximises opencode lifecycle coverage without introducing new Bash hooks.
- **Auto-detection** — projects with `opencode.json` or `.opencode/` are detected by `ai-toolkit install --local` (no explicit `--editors` needed).
- **MCP translation** — `generate_opencode_json.py` translates Claude-style `.mcp.json` into opencode's `mcp` shape (local `command` + args flattened, remote `url` + headers preserved, `enabled: true` default). User-authored keys in `opencode.json` are preserved; re-runs are idempotent.
- **New CLI commands** — `ai-toolkit opencode-md`, `opencode-agents`, `opencode-commands`, `opencode-plugin`, `opencode-json`. Included in `generate-all`.
- **Skill reuse** — opencode reuses the Codex skill adapter (`codex_skill_adapter.py`) for Claude-only orchestration primitives since both lack `Agent`/`TeamCreate`/`TaskCreate` — no duplication.

### Changed
- README `What's New`, package.json description, manifest.json, and `app/.claude-plugin/plugin.json` all list opencode as a supported editor.
- **Plugin exports** — `.opencode/plugins/ai-toolkit-hooks.js` now uses a single named export (`AiToolkitHooks`) per opencode spec. The prior redundant `export default` was removed.
- **Agent frontmatter** — `model` field and source-model-hint comment are no longer emitted because opencode requires `provider/model-id` format, which ai-toolkit does not store. opencode falls back to the user's configured default model.
- **Global install layout fix** — global generators now write directly under `~/.config/opencode/{agents,commands,plugins}/` instead of the incorrect `~/.config/opencode/.opencode/…` nesting. Generators accept a `config_root` parameter to distinguish project vs global layout.
- **Test suite** — grew from 641 to 647 tests covering new event bridges, named-export invariant, missing-source-model-hint regression, and global-layout contract.

---

## v2.5.0 — Community Skills, Automated Scanners & Design Craft (2026-04-15)

### Added
- **`/seo-validate` skill** (community PR #2) — 9-category SEO scanner: W3C semantics, meta/OG tags, Schema.org, hreflang, Core Web Vitals, GEO, SPA/SSG crawlability. Framework-aware (React/Next/Nuxt/Astro/Gatsby/SvelteKit/Remix/Angular/Vue).
- **`/a11y-validate` skill** (community PR #3) — 10-category accessibility scanner: WCAG 2.1 AA, WCAG 2.2 AA, EN 301 549, European Accessibility Act (EAA). Mobile-aware (React Native/Flutter).
- **`seo-scanner.py`** — automated stdlib-only SEO scanner script (9 checks, JSON output, CI exit codes).
- **`a11y-scanner.py`** — automated stdlib-only accessibility scanner script (10 checks, WCAG criterion mapping, contrast calculation, CI exit codes).
- **`wcag-2-2-aa.md`** reference — all 9 new WCAG 2.2 success criteria with failure patterns, grep patterns, and framework notes.
- **`geo-aeo-patterns.md`** reference — Answer Engine Optimization: AI answer engines, llms.txt, robots.txt AI bot directives, E-E-A-T signals.
- **Design Craft vocabulary** (community PR #4) — 7-domain impeccable design guidance in `frontend-specialist` agent and `frontend-lead` persona: typography, OKLCH color, spatial scale, motion, interaction, responsive, UX writing. AI-Native UI patterns section.

### Changed
- **`code-reviewer` agent** — added Grep/Glob tools, rewrote Mandatory Protocol to use actual tools. Expanded review checklist: full OWASP Top 10, API/contract, concurrency/async, migration/schema.
- **`clean-code` python reference** — fixed invalid `any` type hint, modernized to PEP 604 syntax.
- **`design-engineering` skill** — fixed CSS hold-to-delete example (duplicate selector → proper `:active` override).
- **`review` skill** — fixed script path to use `CLAUDE_SKILL_DIR`.
- **`.gitattributes`** — added `merge=ours` for generated files to prevent contributor PR conflicts.
- **Misleading CLI outputs** fixed — plugin.py Codex status glob, --only help examples, install/update --local descriptions, doctor stale rules dr.warn(), config_cli phantom check.
- **`gemini` added to ALL_EDITORS** — `--editors gemini` no longer rejected by CLI validation.
- Skill count: 92 → 94 (31 task + 31 hybrid + 32 knowledge).

---

## v2.4.1 — Codex Global Install, Security Hardening & Editor Tracking (2026-04-15)

### Added
- **Codex hook propagation** — `inject-hook` auto-propagates Codex-compatible events (`SessionStart`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`) to `~/.codex/hooks.json`. `remove-hook` cleans both targets.
- **Global editor tracking** — `ai-toolkit install --editors codex` installs editors globally (opt-in). Tracked in `state.json`, auto-refreshed on `update`. Default: Claude only.
- **Per-project editor tracking** — `install --local --editors` records editors in `projects.json`. `update` re-installs saved editors per project.
- **Auto-propagation** — `add-rule`, `remove-rule`, `mcp add` auto-propagate to globally installed editors via `propagate_global.py`.
- **Doctor Check 9** — URL hook sources health check with `--fix` re-fetch support.

### Fixed
- **Tarball path traversal** — `_extract_tarball` rejects symlinks, absolute paths, and paths escaping dest directory.
- **Git clone URL validation** — `_resolve_git` enforces HTTPS-only, rejects `file://`, `ssh://`.
- **`dr.error()` crash** — `DiagResult` has no `error()` method; fixed to `dr.fail()`.
- **`refresh_url_hooks` missing timestamp update** — now calls `register_url_source` after re-fetch.
- **Defense-in-depth name validation** — `register_url_source()` rejects path traversal chars in both `hook_sources` and `rule_sources`.
- **Unused `execSync` import** — removed from CLI entry point.
- **URL truncation detection** — `url_fetch.py` raises `ValueError` when response exceeds 10MB.
- **MCP templates path** — corrected `app/plugins/mcp-templates/` → `app/mcp-templates/` in ARCHITECTURE docs.
- **MCP templates header count** — corrected 25 → 26 in `app/ARCHITECTURE.md`.

---

## v2.4.0 — URL Hook Injection & Karpathy Coding Rules (2026-04-15)

### Added
- **URL hook injection** — `ai-toolkit inject-hook https://...` fetches, caches, and injects hooks from HTTPS URLs. Cached in `~/.softspark/ai-toolkit/hooks/external/`, auto-refreshed on every `update`. `remove-hook` also unregisters URL source and cleans cache.
- **Shared URL fetch module** — extracted `url_fetch.py` from `rule_sources.py` for reuse by both rule and hook URL sources.
- **Hook URL source registry** — `hook_sources.py` tracks URL-sourced hooks in `sources.json` (analogous to `rule_sources.py`).
- **Surgical Changes rule** — orphan cleanup protocol, match existing style, don't touch adjacent code (inspired by Karpathy's LLM coding guidelines).
- **Goal-Driven Execution rule** — `step → verify: check` pattern for multi-step tasks, strong success criteria before looping.

---

## v2.3.1 — Release Quality Gate (2026-04-14)

### Fixed
- **README "What's New" section** — was stuck at v2.1.3, now auto-validated by `validate.py --strict`
- **Release SOP** — added mandatory "Update README What's New" step to Phase 3 checklist

---

## v2.3.0 — Jira MCP Template & Cross-Editor Sync (2026-04-14)

### Added
- **Jira MCP template** — `ai-toolkit mcp add jira` installs `@softspark/jira-mcp` via global binary. Templates now support `postInstall` field for first-time setup hints shown after `mcp add`, `mcp install`, and `mcp show`. MCP template count: 25 → 26.
- **MCP template tracking** — globally installed templates are recorded in `state.json`. `ai-toolkit update` automatically syncs tracked templates to Claude global config. `ai-toolkit status` shows tracked MCP templates. "Install once, sync everywhere."

### Fixed
- **Claude MCP config paths** — corrected to `~/.claude.json` (global) and `.mcp.json` (project) per official Claude Code docs. Previously wrote to `~/.claude/settings.json` and `.claude/settings.local.json`.
- **Jira MCP template uses global binary** — `jira-mcp` instead of `npx -y` for faster startup and offline support

---

## v2.2.0 — URL Rules & Registry Safety (2026-04-14)

### Added
- **URL rule registration** — `ai-toolkit add-rule https://...` registers rules from HTTPS URLs. URL-sourced rules are tracked in `rules/sources.json` and auto-refreshed on every `ai-toolkit update`. Falls back to cached local copy on network failure.
- **Version consistency validation** — `validate.py --strict` now cross-checks `package.json`, `manifest.json`, and `plugin.json` versions match

### Fixed
- **Project registry race condition** — parallel `install --local` during `ai-toolkit update` could silently drop registry entries. Fixed with `fcntl.flock` exclusive lock, atomic writes (tempfile + rename), and deferred sequential registration after parallel phase.
- **Version drift** — `manifest.json` and `plugin.json` were stuck at 1.9.0 since v2.0.0, now synced
- **Language rules count** — ARCHITECTURE.md claimed 70 files, actual is 68
- **Skills catalog tiers** — added missing Tier 1.5 (planning pipeline + design/architecture)

---

## v2.1.3 — Idempotent Update Fix (2026-04-13)

### Fixed
- **`ai-toolkit update` no longer dirties git** — `inject_with_rules()` now strips all existing TOOLKIT sections before re-injecting, and `generate_agents_md.py` includes the Codex block for format consistency. Running `update` on a clean repo leaves zero uncommitted changes.
- **Custom rules always present** — all generators (standalone and via `inject_with_rules`) emit registered custom rules in every output format

---

## v2.1.1 — Custom Rules in Generators & README Restructure (2026-04-13)

### Fixed
- **Custom rules in generators** — `generate:all` now includes registered custom rules (from `ai-toolkit add-rule`) in all single-file generators (Cursor, Windsurf, Copilot, Gemini, AGENTS.md) and directory-based generators (Cline, Roo, Codex, Augment, Antigravity, Cursor MDC). Previously custom rules were lost on regeneration.
- **AGENTS.md double generation** — `generate-all` CLI no longer generates AGENTS.md twice; uses `codex-md` (superset) only
- **CLI help completeness** — added missing `--persona` option and `codex` to `--editors` list in `ai-toolkit help`

### Changed
- **README restructured** — reduced from 951 to 292 lines with Table of Contents, "What's New" section, and links to KB docs. Detailed content moved to dedicated KB documents.
- **npm `generate:agents`** — now uses `generate_codex.py` (consistent with CLI `generate-all`)
- **Test assertions** — generator file count tests use `>= 6` to accommodate registered custom rules

### New Files
- `kb/reference/cli-reference.md` — complete CLI command reference (moved from README)
- `kb/reference/unique-features.md` — detailed differentiators documentation (moved from README)
- `kb/reference/comparison.md` — ecosystem comparison table (moved from README)

---

## v2.1.0 — Codex CLI Support & Native Editor MCP Install (2026-04-13)

### Added
- **Codex CLI as 10th editor** — full support via `--editors codex`: `AGENTS.md`, `.agents/rules/*.md`, `.agents/skills/*`, `.codex/hooks.json`
- **Codex skill translation layer** — Claude-only orchestration skills (orchestrate, workflow, swarm, teams, subagent-development) are automatically translated to Codex-native `spawn_agent`/`update_plan` wrappers; native skills are symlinked directly
- **Native editor MCP install** — `ai-toolkit mcp install --editor <name> --scope project|global` renders canonical `.mcp.json` templates into 8 editor-native config formats (Claude, Cursor, Copilot, Gemini, Windsurf, Cline, Augment, Codex)
- **MCP auto-sync on local install** — `install --local` mirrors `.mcp.json` into `.claude/settings.local.json` plus selected project editors (Cursor, Copilot)
- **`mcp editors` subcommand** — lists all supported native MCP adapters with scope/path info
- **Cross-editor verification SOP** — mandatory check against official docs before adding any component
- **Runtime-aware plugin installs** — `ai-toolkit plugin install|update|remove|status --editor claude|codex|all` now targets Claude and a global Codex plugin layer consistently
- **Global Codex plugin layer** — plugin packs can bootstrap `~/AGENTS.md`, `~/.agents/`, and `~/.codex/hooks.json` without changing the default project-local Codex core install model
- **Plugin lifecycle tests** — coverage for install/update/remove behavior across Claude and Codex runtimes, including shared asset retention
- **Safe Codex and Cline rule regeneration** — `generate_codex_rules.py` and `generate_cline_rules.py` now support `--skip-cleanup` to refresh standard generated rules without deleting custom overlays

### New Files
- `scripts/mcp_editors.py` — 8 native MCP config adapters
- `scripts/codex_skill_adapter.py` — skill translation layer for Codex
- `scripts/generate_codex.py` — AGENTS.md generator with Codex orchestration guidance
- `scripts/generate_codex_hooks.py` — `.codex/hooks.json` generator
- `scripts/generate_codex_rules.py` — `.agents/rules/*.md` generator
- `kb/reference/codex-cli-compatibility.md` — Codex mapping reference
- `kb/reference/mcp-editor-compatibility.md` — native MCP support matrix
- `tests/test_plugin.bats` — runtime-aware plugin install/remove coverage

### Changed
- **Release workflow** — `generate:all` now refreshes tracked Codex rules and uses the directory-based Cline generator that matches the current repository layout
- **Documentation** — README, KB references, maintenance SOPs, and generated artifacts now consistently describe the Claude + global Codex plugin model

---

## v2.0.2 — Clean Legacy Directory Removal (2026-04-12)

### Fixed
- **Migration cleanup** — `~/.ai-toolkit/` is now fully removed after migration instead of leaving an empty directory with a `.migrated` marker

---

## v2.0.1 — Migration Hook Path Fix (2026-04-12)

### Fixed
- **settings.json hook paths** — migration now rewrites ALL hook commands (including plugin hooks with non-toolkit `_source` tags like `memory-pack`, `enterprise-pack`) from `~/.ai-toolkit/hooks/` to `~/.softspark/ai-toolkit/hooks/`

---

## v2.0.0 — SoftSpark Namespace Migration (2026-04-12)

### BREAKING CHANGES
- **Home directory moved** — `~/.ai-toolkit/` → `~/.softspark/ai-toolkit/`. Prepares the namespace for sibling tools (`jira-mcp`, etc.) under `~/.softspark/`
- **Per-project config renamed** — `.ai-toolkit.json` → `.softspark-toolkit.json`
- **Per-project lock file renamed** — `.ai-toolkit.lock.json` → `.softspark-toolkit.lock.json`

### Added
- **Auto-migration** — on first `install`/`update` after upgrade, data is automatically migrated from legacy path. A `.migrated` marker is left in `~/.ai-toolkit/` pointing to the new location
- **`scripts/paths.py`** — centralized path constants module; all scripts import from here instead of hardcoding paths
- **`scripts/migrate.py`** — standalone migration script (`python3 scripts/migrate.py [--dry-run]`)
- **Legacy fallback** — `config_resolver` and `config_lock` transparently read old filenames (`.ai-toolkit.json`, `.ai-toolkit.lock.json`) if new ones don't exist
- **JS CLI fallback** — `ai-toolkit update` checks legacy `state.json` location for seamless first upgrade

### Changed
- All Python scripts, Bash hooks, JS CLI, hooks.json, manifest.json, tests, and documentation updated to use `~/.softspark/ai-toolkit/` paths
- `AI_TOOLKIT_HOME` env var still supported as override

---

## v1.9.0 — Project Registry & Doc Sync (2026-04-12)

### Added
- **Project registry** — `install --local` automatically registers project path in `~/.softspark/ai-toolkit/projects.json`. `ai-toolkit update` propagates updates to all registered projects in parallel via `ThreadPoolExecutor`
- **`ai-toolkit projects`** — list registered projects, `--prune` to remove stale (deleted directories), `remove <path>` to unregister specific project
- **Parallel update propagation** — `ai-toolkit update` (global) now auto-updates all registered local projects concurrently (max 8 workers)

### Fixed
- **README.md** — skill count 91→92 in comparison table, added Augment/Antigravity to cross-tool tables, fixed Notification hook description (inline→`notify-waiting.sh`)
- **README.md** — added Config Inheritance section, Project Registry section, 6 new CLI commands to reference table
- **ARCHITECTURE.md** — added Config Inheritance and Project Registry to Extension Points
- **CLAUDE.md** — added `config` and `projects` commands

---

## v1.8.0 — Enterprise Config Inheritance (2026-04-12)

### Added
- **Configuration inheritance system** — `extends` pattern (like ESLint/TypeScript) for multi-repo AI governance. Organizations define a shared base config published as npm package, git URL, or local path; projects inherit via `.softspark-toolkit.json`
- **`ai-toolkit config validate`** — schema validation + extends resolution + enforcement check
- **`ai-toolkit config diff`** — visual diff of project vs base config (profile, agents, rules, constitution, overrides)
- **`ai-toolkit config init`** — interactive or flag-driven `.softspark-toolkit.json` creation with extends validation
- **`ai-toolkit config create-base`** — scaffolds ready-to-publish npm base config package (package.json, ai-toolkit.config.json, rules/, agents/, README)
- **`ai-toolkit config check`** — CI enforcement gate with JSON output and exit codes (0=pass, 1=fail, 2=no config)
- **Merge engine** — layered deep merge (base → project) with special handling for agents (requiredAgents enforcement), rules (union), constitution (immutability), enforce blocks (cannot weaken)
- **Constitution immutability guard** — Articles I-V absolutely immutable; base config articles immutable; projects can only ADD new articles (6+)
- **Override validation** — `override: true` + justification (min 20 chars) required; `forbidOverride` enforcement
- **Enforce constraints** — 4 types: `minHookProfile`, `requiredPlugins`, `forbidOverride`, `requiredAgents`
- **Lock file** (`.softspark-toolkit.lock.json`) — pins resolved base config versions for reproducible installs across team; generated on `install --local`, updated on `update --local`
- **Audit trail** — extends metadata recorded in `state.json` and `.softspark-toolkit-extends.json`
- **Offline fallback** — uses cached configs from `~/.softspark/ai-toolkit/config-cache/` when registry unavailable
- **Cycle detection** — max 5-level extends chain with circular reference detection
- **Install integration** — `install --local` and `update --local` auto-detect `.softspark-toolkit.json`, resolve extends, merge, validate, inject rules + constitution amendments into generated files
- **New CLI flags** — `--config <path>` (explicit config file), `--refresh-base` (force re-fetch)
- **JSON Schema** — `scripts/schemas/ai-toolkit-config.schema.json` for editor autocompletion
- **Enterprise config guide** — `kb/reference/enterprise-config-guide.md` comprehensive documentation
- **52 new tests** — resolver (7), merger (13), CLI (23), install integration (9)

### Changed
- **`manifest.json`** — added `config_inheritance` section with schema references and v1 field list

---

## v1.7.0 — Offline-First SLM Compilation (2026-04-11)

### Added
- **`compile-slm` command** — compiles full toolkit (20K+ tokens) into a minimal system prompt for Small Language Models (2K-16K tokens). Supports 4 compression levels (ultra-light, light, standard, extended), 4 output formats (raw, ollama, json-string, aider), persona-aware scoring, and language-aware rule filtering. `scripts/compile_slm.py`
- **`offline-slm` profile** — `manifest.json` profile for offline/air-gapped installs
- **Post-compilation validator** — checks constitution presence, budget compliance, guard hooks, output sanity
- **Integration guides** — step-by-step setup for Ollama, LM Studio, Aider, Continue.dev printed after compilation
- **61 tests** for compile-slm (token counter, parser, compression, packer, emitter, formats, CLI, determinism, budget compliance, validator, guides)

### Fixed
- **Skill counts** — synced stale count 91 → 92 across README.md (3 locations) and manifest.json
- **KB frontmatter validation** — `kb/history/` excluded from category-dir match (archived plans keep original category)

---

## v1.6.1 — IDE Rule Format Compliance Audit (2026-04-10)

### Fixed
- **Cline rules path** — changed `.cline/rules/` to `.clinerules/` directory per official Cline 3.7+ docs. Old path was silently ignored by Cline
- **Augment frontmatter type** — changed `auto_attached` to `agent_requested` per official Augment docs
- **Aider config** — added `CONVENTIONS.md` to `read:` list in `.aider.conf.yml` so Aider auto-loads the conventions we generate

### Changed
- **`add-rule` help text** — now lists all supported editors (was missing Augment, Roo, Aider, Antigravity)
- Legacy `.clinerules` single-file is auto-migrated to `.clinerules/` directory on next install

---

## v1.6.0 — IDE Language Rules Propagation, Planning Docs, Cloud Security Pack (2026-04-10)

### Added
- **Language rules propagation to all IDE editors** — shared `dir_rules_shared.py` module now injects language-specific and registered rules into Cursor, Windsurf, Cline, Roo Code, Augment, Antigravity, and Copilot generators. All platforms receive identical rule content from a single source of truth.
- **Enterprise Config Inheritance Plan** — planning doc (`kb/planning/enterprise-config-inheritance-plan.md`) for hierarchical config system
- **Offline SLM Profile Plan** — planning doc (`kb/planning/offline-slm-profile-plan.md`) for offline small language model profiles
- **Cloud Security Pack Plan** — planning doc (`kb/planning/cloud-security-pack-plan.md`) for multi-cloud audit (GCP/AWS/Azure)
- **193 new generator tests** — language rules propagation, content verification, cross-platform parity

### Changed
- **Documentation standards** — added `planning` as a valid KB category in `validate.py`, `documenter` agent, `/docs` and `/documentation-standards` skills
- **Maintenance SOP** — updated to reflect language rules propagation workflow

---

## v1.5.1 — Security Hardening: Script Injection, XSS, Private Data Leak (2026-04-10)

### Fixed
- **`action.yml` script injection** — replaced `${{ inputs.command }}` direct interpolation with `env:` variable to prevent GitHub Actions script injection (OWASP A03)
- **`visual-server.cjs` stored XSS** — extracted inline script to `poll.js`, added `Content-Security-Policy: script-src 'self'` header to block injected scripts in PRD visual preview
- **`strip_private.py` regex** — changed `[^<]*` to `.*?` with `re.DOTALL` flag to correctly handle multi-line `<private>` blocks and inner angle brackets (was leaking private data in edge cases)

---

## v1.5.0 — HIPAA Scanner: Deterministic Script, CI Integration, Self-Exclusion (2026-04-10)

### Added
- **`scripts/hipaa_scan.py`** — deterministic Python scanner (stdlib-only) for `/hipaa-validate`. Replaces LLM-driven regex execution with a reproducible script. 8 check categories, context gate, `.hipaaignore` support, `.hipaa-config` BAA vendor list, deduplication, structured output.
- **`--output json` flag** for `/hipaa-validate` — structured JSON output for CI/CD pipeline integration. Exit code 1 on HIGH findings, 0 otherwise.
- **Self-exclusion** — scanner automatically excludes its own skill directory to prevent flagging its own regex definitions.
- **`.hipaaignore`** — project-level exclusion file (gitignore syntax) for suppressing known false positives.
- **IDE/AI config file exclusions** — `.roomodes`, `.cursorrules`, `.windsurfrules`, `llms.txt`, `llms-full.txt`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `COPILOT.md` automatically skipped (contain pattern examples, not source code).

### Changed
- **`/hipaa-validate` frontmatter** — added `user-invocable: true`, `context: fork`, `agent: security-auditor`, `Bash` in `allowed-tools`.
- **`/hipaa-validate` workflow** — pivoted from "manually execute regex patterns" to "run script, interpret results, suggest specific fixes."
- **Documentation alignment** — updated hipaa-validate descriptions in README.md, ARCHITECTURE.md, skills-catalog.md, llms-full.txt to include all 8 check categories (was missing "temp file exposure" and "missing BAA references").
- Skill count: 91 → 92 in package.json description.

---

## v1.4.2 — --local Scoping Fix, Leading Blank Lines Fix (2026-04-09)

### Fixed
- `--local` now runs only project-local install (no global re-install). Global install runs separately without `--local`.
- Fixed leading blank lines in generated files (copilot-instructions.md, etc.) caused by `inject_section` and `inject_with_rules`.
- Context-aware "Next steps" message (local vs global).

### Changed
- Updated KB docs: global-install-model.md, maintenance-sop.md to reflect `--local` scoping change.

---

## v1.4.1 — Documentation Fix: --local Behavior (2026-04-09)

### Fixed
- README Per-Project Setup, Quick Start, and CLI table now correctly state that `--local` installs Claude Code only by default, with `--editors` flag for other tools.

---

## v1.4.0 — Full Platform Parity: 11 Editors, Directory-Based Rules, --editors Flag (2026-04-09)

### Added
- **Google Antigravity support** — new editor integration with `.agent/rules/` (6 rule files) and `.agent/workflows/` (13 workflow templates with YAML frontmatter). Full agent/skill catalog parity with other platforms.
- **Directory-based rules for all editors** — every platform now gets modern directory-based configs in addition to legacy single-file formats:
  - Cursor: `.cursor/rules/*.mdc` with YAML frontmatter (`alwaysApply`, `globs`, `description`)
  - Windsurf: `.windsurf/rules/*.md`
  - Cline: `.cline/rules/*.md`
  - Roo Code: `.roo/rules/*.md` (shared rules for all modes)
  - Augment: `.augment/rules/ai-toolkit-*.md` with `auto_attached` globs per file type
  - Aider: `CONVENTIONS.md` (auto-loaded as read-only context)
- **`--editors` flag** for `install --local` — selective editor installation:
  - `--editors all` — install all 8 editors
  - `--editors cursor,aider` — install only selected
  - (no flag) — auto-detect from existing project files
  - `update --local` auto-detects editors from existing configs
- **`--lang` flag** — explicit language selection for rules (`--lang typescript`, `--lang go,python`) with aliases (`go`→`golang`, `c++`→`cpp`, `cs`→`csharp`)
- **Two-phase language detection** — marker files (package.json, go.mod, etc.) + source file extension scanning (.py, .ts, .go, etc.)
- **Shared rule content module** (`dir_rules_shared.py`) — all platforms get identical agent/skill catalog, guidelines, and rules from a single source of truth
- **7 new CLI commands**: `cursor-mdc`, `windsurf-dir-rules`, `cline-dir-rules`, `roo-dir-rules`, `augment-dir-rules`, `conventions-md`, `antigravity-rules`
- **71 generator tests** — file existence, content verification, user file preservation, idempotency, stale cleanup, cross-platform parity check

### Changed
- `install --local` now installs only Claude Code configs by default (no editor bloat); editors require `--editors` flag or auto-detect from existing files
- All directory-based generators use `ai-toolkit-` prefix to prevent overwriting user files
- Total test count: 377 → 408

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
- **Session-start hook**: `TOOLKIT_DIR` resolved via `npm root -g` instead of broken `../../` relative path from `~/.softspark/ai-toolkit/hooks/`.

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
- **Version cache**: `install` and `update` now clear `~/.softspark/ai-toolkit/version-check.json` so `status` shows correct "Latest" immediately after upgrade.

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
- **Stats not counting**: `track-usage.sh` and `user-prompt-submit.sh` now read prompt from stdin JSON (`.prompt` field) instead of non-existent `CLAUDE_USER_PROMPT` env var. Skill invocations are now properly tracked in `~/.softspark/ai-toolkit/stats.json`.

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
- **Manifest-Driven Install**: Module-level install granularity (`--modules`), language auto-detection (`--auto-detect`), install state tracking (`~/.softspark/ai-toolkit/state.json`), `status` and `update` commands.
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
- Global install into `~/.claude/` with merge-friendly propagation; hooks merged into `settings.json`, scripts copied into `~/.softspark/ai-toolkit/hooks/`
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
- **`doctor.py` stale rules detection** (Check 8) — detects rules in CLAUDE.md whose source files no longer exist in `~/.softspark/ai-toolkit/rules/`
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
