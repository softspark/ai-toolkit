---
title: "Supported Tools Registry"
category: reference
service: ai-toolkit
tags: [editors, platforms, generators, integration, ecosystem]
version: "1.10.0"
created: "2026-04-23"
last_updated: "2026-07-14"
description: "Human-readable view of scripts/ecosystem_tools.json — the canonical list of tools ai-toolkit integrates with (Claude Code, Claude Chat/Cowork, and 11 editors), their documentation URLs, config paths, our generators, and tracked capability markers."
---

# Supported Tools Registry

The canonical data lives in **`scripts/ecosystem_tools.json`** and is consumed by `scripts/ecosystem_doctor.py`. This document is a derived view — when the JSON changes, update this table too.

## Tool Count: 13

1 primary runtime (Claude Code) + 1 Claude app target + 11 editor integrations.

---

## Primary Runtime

### Claude Code

| Field | Value |
|-------|-------|
| ID | `claude-code` |
| Docs | https://code.claude.com/docs (platform.claude.com/docs 307-redirects here) |
| Release notes | https://github.com/anthropics/claude-code/releases |
| Changelog | https://code.claude.com/docs/en/changelog; GitHub release feed is authoritative when the generated page lags (current local/release: 2.1.206, 2026-07-10) |
| Config paths | `~/.claude/settings.json`, `.claude/settings.json` (project, committed), `.claude/settings.local.json`, `CLAUDE.md`, `.claude/rules/*.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`, `~/.claude/themes/*.json` (v2.1.118+) |
| Our generators | — (Claude Code is the primary target; toolkit content ships directly as `.md` files and `settings.json` merges) |
| Tracked hook events | Core: `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `Notification`, `MessageDisplay`. Tool: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`. Turn: `Stop`, `StopFailure`, `UserPromptExpansion`. Subagent: `SubagentStart`, `SubagentStop`. Compaction: `PreCompact`, `PostCompact`. Permissions: `PermissionRequest`, `PermissionDenied`. Elicitation: `Elicitation`, `ElicitationResult`. Teams: `TaskCreated`, `TaskCompleted`, `TeammateIdle`. Worktrees/env: `WorktreeCreate`, `WorktreeRemove`, `CwdChanged`, `FileChanged`, `ConfigChange`. Setup: `Setup`, `InstructionsLoaded` |
| Tracked handler types | `command`, `prompt`, `agent`, `mcp_tool`, `http` (POST event JSON to allowlisted URLs via `allowedHttpHookUrls`) |
| Other capabilities | slash commands, MCP server/client, sub-agent, output style, `SKILL.md` (≥500 lines warn) |
| Version probe | `claude --version` |
| Notes | v2.1.169 added `disableBundledSkills` setting + `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS` env var (hides bundled skills/built-in slash commands from the model; toolkit skills in `.claude/skills/` are unaffected — useful when toolkit skills overlap built-ins) and `claude --safe-mode` / `CLAUDE_CODE_SAFE_MODE` (starts with hooks, skills, agents, and CLAUDE.md disabled — first isolation step when debugging toolkit rule enforcement). `fallbackModel` settings key (v2.1.166) noted as not-adopted (class C, no toolkit surface writes model settings). |

---

## Claude App Target

### Claude Chat / Cowork

| Field | Value |
|-------|-------|
| ID | `claude-app` |
| Docs | https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork |
| Plugin docs | https://support.claude.com/en/articles/13837440-use-plugins-in-claude |
| Config surfaces | `Settings > Cowork > Global instructions`, Cowork folder instructions, `Customize > Skills`, and `Customize > Plugins` |
| Plugin layout | `.claude-plugin/plugin.json`, `skills/*/SKILL.md`, `agents/*.md`, `hooks/hooks.json`; ai-toolkit uses manifest paths under `claude-app/` for its generated app-only rules and hooks |
| Our generator | `scripts/claude_app.py` (`ai-toolkit claude-app export`) |
| Runtime split | Skills work in Chat (web/Desktop) and Cowork. Hooks and sub-agents run only in Cowork. Claude app does **not** scan Claude Code's `~/.claude/rules/`, `CLAUDE.md`, or `~/.claude/settings.json`. |
| Install/update | Export the ZIP, upload it from `Customize > Plugins`, then paste the generated global-instructions file into `Settings > Cowork > Global instructions`. Re-export/re-upload after toolkit updates. |

---

## Editor Integrations

### Cursor

| Field | Value |
|-------|-------|
| ID | `cursor` |
| Docs | https://cursor.com/docs |
| Changelog | https://cursor.com/changelog |
| Stable docs mirror | https://cursor.com/llms.txt (all doc pages have .md twins) |
| Config paths | `.cursorrules` (**legacy** — no longer in cursor.com/docs/rules; deprecated ~0.43–0.45 in favor of `.cursor/rules/*.mdc`, still read, no removal deadline; we keep emitting for back-compat), `.cursor/rules/*.mdc` (plain `.md` files in `.cursor/rules/` are **ignored** by the rules system), `AGENTS.md`, `.cursor/mcp.json`, `~/.cursor/mcp.json`, `.cursor/hooks.json`, `~/.cursor/hooks.json` (user-level hooks scope; enterprise system paths + dashboard team hooks not adopted, class C), `.cursor/skills/*/SKILL.md`, `~/.cursor/skills/*/SKILL.md`, `.cursor/agents/*.md`, `~/.cursor/agents/*.md` |
| Compat read paths | skills: `.agents/skills/`, `~/.agents/skills/`, `.claude/skills/`, `~/.claude/skills/`, `.codex/skills/`, `~/.codex/skills/`; subagents: `.claude/agents/`, `~/.claude/agents/`, `.codex/agents/`, `~/.codex/agents/` (`.cursor/` wins on name conflicts) |
| Our generators | `scripts/generate_cursor_rules.py`, `scripts/generate_cursor_mdc.py`, `scripts/generate_cursor_hooks.py` (complete version-1 event set plus self-contained `.cursor/hooks/ai-toolkit/cursor_hook.py`; profile=full local **and** global `~/.cursor/hooks.json`), `scripts/generate_cursor_agents.py` (profile=full), `scripts/generate_cursor_skills.py` (profile=full pointer) |
| Global install | Cursor is in `GLOBAL_CAPABLE_EDITORS` for **hooks only**: `ai-toolkit install --editors cursor` writes `~/.cursor/hooks.json` (profile ≥ standard). RULES stay project-local (Cursor's only global rules surface is the Settings UI). |
| Tracked capabilities | `cursorrules`, `.cursor/rules`, `AGENTS.md`, `mcp.json`, Composer, Agent Mode, hooks.json, subagents, skills, plugins |
| Hook compatibility | Cursor 3.11 project hooks run locally and in cloud agents from repository `.cursor/hooks.json`; cloud VMs do not load `~/.cursor/hooks.json`. The generated project manifest uses only documented command-entry keys, calls a repo-relative runtime, covers conversation hooks including `afterAgentResponse` and `afterAgentThought`, preserves user entries, and caps `stop`/`subagentStop` follow-up loops at 5. |

### Windsurf

| Field | Value |
|-------|-------|
| ID | `windsurf` |
| Docs | https://docs.devin.ai/desktop (Windsurf rebranded to Devin Desktop ~2026-06-02; docs.windsurf.com resolves here) |
| Changelog | https://docs.devin.ai/desktop/changelog (windsurf.com/changelog 308-permanent-redirects here) |
| Stable docs mirror | https://docs.devin.ai/desktop/... per-page .md twins; legacy `.windsurf/`, `.windsurfrules`, `~/.codeium/windsurf/` rule paths still read as fallback (new canonical rules/hooks tree: `.devin/`) |
| Config paths | **Primary (Devin Desktop):** `.devin/rules/*.md`, `.devin/workflows/*.md`, `.devin/hooks.v1.json` (Devin CLI hooks, Claude format), `.devin/config.json`, `.devin/config.local.json`, `~/.config/devin/config.json` (Devin Local MCP/permissions). **Skills:** eight documented paths, all scanned in every repo — `.agents/skills/*/SKILL.md` (recommended), `.devin/skills`, `.github/skills`, `.claude/skills`, `.cursor/skills`, `.codex/skills`, `.cognition/skills`, and `.windsurf/skills`. ai-toolkit emits a single canonical pointer under `.windsurf/skills` to avoid duplicate registration. **Legacy fallback:** `.windsurfrules`, `.windsurf/rules/*.md`, `.windsurf/workflows/*.md`, `~/.codeium/windsurf/memories/global_rules.md`, `~/.codeium/windsurf/skills/*/SKILL.md`, `~/.codeium/windsurf/mcp_config.json`. Plus `AGENTS.md`. |
| Compat read paths | Current skill docs explicitly scan all eight paths — `.agents/skills/`, `.devin/skills/`, `.github/skills/`, `.claude/skills/`, `.cursor/skills/`, `.codex/skills/`, `.cognition/skills/`, and `.windsurf/skills/`. **Hooks:** Devin CLI reads `.claude/settings.json` + `~/.claude/settings.json` hooks when `read_config_from.claude` is enabled, so globally-installed toolkit hooks also work under Devin. |
| Our generators | `scripts/generate_windsurf.py`, `scripts/generate_windsurf_rules.py` (dual-emits `.devin/` + `.windsurf/` rules/workflows), `scripts/generate_devin_hooks.py` (profile=full; `.devin/hooks.v1.json`), `scripts/generate_windsurf_skills.py` (`.windsurf/skills` pointer) |
| Global install | `ai-toolkit install --editors windsurf` writes `~/.codeium/windsurf/memories/global_rules.md` + skills pointer **and** `~/.config/devin/AGENTS.md` (Devin CLI global rules — the Desktop `global_rules.md` path is absent from `read_config_from.windsurf`, so editor-only Devin CLI installs need this). |
| Tracked capabilities | Cascade, `windsurfrules`, `AGENTS.md`, activation triggers (`always_on`/`glob`/`model_decision`), workflows, skills, MCP, memories, hooks |
| Activation modes emitted | always_on (agents/security/quality), glob (testing + language rules), model_decision (code-style/workflow) |
| Hooks migration | **Complete.** Cascade and `.windsurf/hooks.json` ended on 2026-07-01. `generate_devin_hooks.py` is now the only Windsurf-family hook generator and emits `.devin/hooks.v1.json` with Claude-style events, Devin tool-name matchers, and the flat Devin block contract. |
| Latest upstream | Devin Desktop v3.4.27 (2026-07-07). v3.4.22 made skill `permissions:` frontmatter affect auto-approvals; ai-toolkit does not emit permissions because its pointer skill executes no privileged workflow. |

### GitHub Copilot

| Field | Value |
|-------|-------|
| ID | `github-copilot` |
| Docs | https://docs.github.com/en/copilot |
| Release notes | https://github.blog/changelog/label/copilot/ |
| Native docs | [Hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference), [skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills), [CLI config directory](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference) |
| Config paths | **Repo (`.github/`):** `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, `.github/prompts/*.prompt.md`, `.github/agents/*.agent.md`, `.github/skills/<name>/SKILL.md`, `.github/hooks/*.json`, `AGENTS.md`. **Copilot CLI user-level (`~/.copilot/`, `COPILOT_HOME` override):** `copilot-instructions.md`, `instructions/*.instructions.md`, `agents/*.agent.md`, `skills/<name>/SKILL.md`, `hooks/*.json`, `settings.json`, `mcp-config.json` below the active config root. |
| Compat read paths | Copilot also discovers project `.claude/skills` and `.agents/skills`, and personal `~/.agents/skills`. ai-toolkit nevertheless materializes self-contained native skills under `.github/skills` and the active Copilot config root so assets and helper scripts remain available and `COPILOT_HOME` sessions do not depend on fallback discovery. |
| Our generators | `scripts/generate_copilot.py` (instructions, prompts, agents, and portable skill directories), `scripts/generate_copilot_hooks.py` (native version-1 hook config plus self-contained runtime) |
| Global install | `ai-toolkit install --editors copilot` writes instructions, agents, skills, and, for profile ≥ `standard`, native hooks below `$COPILOT_HOME` when set or `~/.copilot` otherwise. VS Code Copilot and GitHub.com use repo `.github/` files, so local emission remains required. |
| Tracked capabilities | `copilot-instructions.md`, Copilot Chat, Copilot Workspace, Copilot cloud agent, `applyTo`, custom agents, prompt files, `instructions.md`, `AGENTS.md`, MCP, skills, CLI hooks, `~/.copilot/` |
| Compatibility notes | Custom agents use native `.agent.md` files with `name` and `description`; `tools` is omitted instead of guessing editor-specific aliases. Prompt and skill bodies remove Claude-only interpolation and delegation APIs. Hooks use the GitHub version-1 schema, camelCase event names, native decision payloads, and a repository/config-root-contained Python runtime instead of Claude hook scripts. Project MCP remains owned by the editor MCP sync path. Copilot code review also reads the nearest `AGENTS.md`; local install keeps its generated section separate from Codex/OpenCode sections. Surface loading semantics and the prompt/skill duplication are documented in `kb/reference/copilot-compatibility.md`. |

### Gemini CLI

| Field | Value |
|-------|-------|
| ID | `gemini-cli` |
| Docs | https://github.com/google-gemini/gemini-cli/tree/main/docs |
| Release notes | https://github.com/google-gemini/gemini-cli/releases |
| Config paths | `GEMINI.md`, `.gemini/settings.json`, `~/.gemini/settings.json`, `.gemini/commands/*.toml`, `.gemini/skills/*/SKILL.md`, `.agents/skills/*/SKILL.md`, `~/.gemini/skills/*/SKILL.md`, `~/.agents/skills/*/SKILL.md` (the `.agents/skills` alias wins over `.gemini/skills` within the same tier), `.gemini/extensions/gemini-extension.json` |
| Our generators | `scripts/generate_gemini.py`, `scripts/generate_gemini_hooks.py` (profile>=standard), `scripts/generate_gemini_commands.py` (profile=full), `scripts/generate_gemini_skills.py` (profile=full) |
| Global install | `ai-toolkit install --editors gemini` writes `~/.gemini/GEMINI.md` **plus** hooks at `~/.gemini/settings.json` (profile ≥ standard) and `~/.gemini/commands/` + `~/.gemini/skills/` pointer (profile=full) — all documented user-tier surfaces. A global-only Gemini user previously got zero hooks. |
| Tracked capabilities | `GEMINI.md`, `mcpServers`, tools, `settings.json`, `BeforeTool`, `AfterTool`, `BeforeToolSelection`, `BeforeAgent`, `AfterAgent`, `BeforeModel`, `AfterModel`, `Notification`, `PreCompress`, `SessionStart`, `SessionEnd`, `SKILL.md`, `activate_skill`, custom commands, `.gemini/agents/*.md` subagents, `gemini-extension.json` (no native `Stop` event — generator maps Stop-equivalent to `AfterAgent`; 11 documented hook events total) |
| Version probe | `gemini --version` |
| Latest upstream | v0.49.0 (2026-06-25; the stable line skipped v0.48.0 — its preview content was promoted into v0.49.0). NOTE: Gemini CLI dropped free/paid individual tiers on 2026-06-18 in favor of Antigravity CLI (we ship `generate_antigravity.py`); enterprise Code Assist and paid API keys keep Gemini CLI, so the integration stays. The 11 hook events are unchanged. v0.49.0 completed the `coreTools` → `tools.core` migration (auto-migrated; `tools.exclude` deprecated) — both are tool-allowlist keys we do not emit, so no generator change. Watch item: `.gemini/agents/*.md` / `~/.gemini/agents/*.md` native subagents are documented but we do not yet emit them (candidate `generate_gemini_agents.py`). |

### Cline

| Field | Value |
|-------|-------|
| ID | `cline` |
| Docs | https://docs.cline.bot |
| Release notes | https://github.com/cline/cline/releases |
| Config paths | **Extension:** `.clinerules/*.md`, `.clinerules/workflows/*.md`, `.clinerules/skills/*/SKILL.md`, `.clinerules/hooks/` (project), `~/Documents/Cline/Rules/Hooks/` (global hooks), `~/.cline/data/settings/cline_mcp_settings.json`. **CLI/SDK unified layout** (docs.cline.bot/getting-started/config; `.clinerules` is deprecated there): `.cline/{rules,hooks,plugins,skills}/`, `~/.cline/{rules,hooks,plugins,skills}/`, `CLINE_HOOKS_DIR` env var. **Cross-tool:** `AGENTS.md` + `~/.agents/AGENTS.md` (first-class rules sources), `.claude/skills/*/SKILL.md` (native discovery, always-on since v3.57.0). |
| Our generators | `scripts/generate_cline.py`, `scripts/generate_cline_rules.py`, `scripts/generate_cline_skills.py` |
| Tracked capabilities | `clinerules`, Plan Mode, Act Mode, MCP, custom modes, workflows, hooks, skills, subagents, conditional rules, `AGENTS.md`, plugins |
| Plugins | `.cline/plugins/` + `~/.cline/plugins/` (JS/TS), `package.json` `cline.plugins` manifest; plugins can bundle skills. Not adopted as a distribution channel yet — candidate for shipping toolkit skills to CLI/SDK users. |
| Notes | Conditional rules (`paths:` YAML frontmatter) are emitted for testing and language-specific rules since 2026-04. Project rules still use `.clinerules/` for compatibility; global rules are written to `~/Documents/Cline/Rules/` (the documented Cline global rules dir — `~/.cline/rules/` is not a Cline-read path). Skills are emitted as a pointer catalogue in `profile=full` and global installs. |
| Global install | `ai-toolkit install --editors cline` writes documented global rules under `~/Documents/Cline/Rules/` and a skill pointer under `~/.cline/skills/`; MCP remains managed by `ai-toolkit mcp install --editor cline`. |

### Roo Code

| Field | Value |
|-------|-------|
| ID | `roo-code` |
| Docs | https://roocodeinc.github.io/Roo-Code (frozen; docs.roocode.com 301-redirects here). Successor docs: https://docs.zoocode.dev |
| Release notes | https://github.com/Zoo-Code-Org/Zoo-Code/releases (authoritative). **Original RooCodeInc/Roo-Code repo ARCHIVED/read-only since 2026-05-15, frozen at v3.54.0 — its feed is dead.** Successor project by former Roo contributors: **Zoo-Code-Org/Zoo-Code** (marketplace `ZooCodeOrganization.zoo-code`), active through v3.64.0 (2026-06-26). |
| Config paths | `.roomodes` (JSON still fully supported), `.roo/rules/*.md`, `.roo/rules-{slug}/*.md`, `.roo/skills/*/SKILL.md`, `~/.roo/skills/*/SKILL.md`, `.agents/skills/*/SKILL.md`, `~/.agents/skills/*`, `.roo/commands/*.md`, `~/.roo/commands/*.md`, `.roo/mcp.json`, `~/.roo/rules/`, `mcp_settings.json` + global custom modes live in VS Code globalStorage (`<globalStorage>/rooveterinaryinc.roo-cline/settings/custom_modes.yaml`), NOT `~/.roo/custom_modes.yaml` |
| Our generators | `scripts/generate_roo_modes.py`, `scripts/generate_roo_rules.py` |
| Tracked capabilities | `roomodes`, custom modes, Code Actions, MCP, Orchestrator mode, `whenToUse`, `description`, `roleDefinition`, `groups`, skills, slash commands |
| Notes | Config compat with the Zoo fork is total, so both generators stay valid unchanged. `.roomodes` includes `description`/`whenToUse` for every mode (since 2026-04); JSON is still accepted (YAML is upstream-preferred but not emitted). Global install writes `~/.roo/rules/` plus `~/.agents/skills/*` (Roo/Zoo native skill discovery, shipped v3.46.0/v3.47.2; skipped when `codex` is also selected). `~/.roo/commands/` (global slash commands, since v3.25) is a documented surface not yet generated. |

### Aider

| Field | Value |
|-------|-------|
| ID | `aider` |
| Docs | https://aider.chat/docs |
| Changelog | https://aider.chat/HISTORY.html |
| Config paths | `.aider.conf.yml`, `CONVENTIONS.md`, `~/.aider.conf.yml` |
| Our generators | `scripts/generate_aider_conf.py`, `scripts/generate_conventions.py` |
| Tracked capabilities | `.aider.conf.yml`, `CONVENTIONS.md`, `architect`, `auto-accept-architect`, `read`, `lint-cmd`, `test-cmd`, `commit-prompt`, `attribute-co-authored-by`, `chat-language`, `commit-language`, `watch-files`, `auto-commits` |
| Global install | `ai-toolkit install --editors aider` creates `~/.aider.conf.yml` only when absent and always refreshes `~/.aider-ai-toolkit-CONVENTIONS.md`; existing YAML is preserved. |
| Version probe | `aider --version` |
| Latest upstream | v0.86.1 (Aug 2025) |

### Augment

| Field | Value |
|-------|-------|
| ID | `augment` |
| Docs | https://docs.augmentcode.com |
| Changelog | https://www.augmentcode.com/changelog |
| Config paths | `.augment/rules/*.md`, `.augment-guidelines` (workspace root, legacy single-file), `~/.augment/user-guidelines.md`, `.augment/agents/*.md`, `.augment/commands/*.md`, `.augment/skills/*/SKILL.md`, `.augment/settings.json`, `.augment/settings.local.json`, `~/.augment/rules/*.md`, `~/.augment/settings.json`, `/etc/augment/settings.json`. Auggie CLI also discovers skills/commands from `.claude/` and `.agents/` (`.augment/` wins on precedence). |
| Our generators | `scripts/generate_augment.py`, `scripts/generate_augment_rules.py`, `scripts/generate_augment_agents.py` (profile=full), `scripts/generate_augment_commands.py` (profile=full), `scripts/generate_augment_hooks.py` (profile=full, HOME-scoped), `scripts/generate_augment_skills.py` (profile=full) |
| Global install | `ai-toolkit install --editors augment` writes `~/.augment/rules/ai-toolkit.md` **plus** (profile=full) `~/.augment/agents/`, `~/.augment/commands/`, and hooks in `~/.augment/settings.json` — all documented user-tier surfaces. A global-only Augment user previously got no hooks/agents/commands. Skills need no global emission: Auggie natively reads `~/.claude/skills/`. |
| Tracked capabilities | `.augment`, Agent mode, Next Edit, MCP, context engine, Auggie CLI, `always_apply`, `agent_requested`, subagents, custom commands, `SKILL.md`, `PreToolUse`, `PostToolUse`, `SessionStart`, `SessionEnd`, `Stop`, `Notification`, ACP Mode, plugins/marketplace |
| Latest / notes | Auggie CLI v0.31.0. Since v0.30.0 (2026-06-25) `PreToolUse`/`PostToolUse` hooks fire during sub-agent sessions, so our wired hook groups now run concurrently from parallel sub-agents — hook payload identifier is `conversation_id` (not `session_id`), a concurrency note to track. `Notification` is enum-only (doctor flipped its marker) — no dedicated handler documented, so class C (do NOT wire). Plugins/marketplace (`auggie plugin marketplace add`, `.augment-plugin`/`.claude-plugin` layouts, `enabledPlugins`/`autoUpdateMarketplaces` in settings) documented but not yet a shipping target. |
| SPA caveat | Mintlify Next.js SPA; use `https://docs.augmentcode.com/<path>.md` siblings (discoverable via `/llms.txt`) for machine reads |

### Google Antigravity

| Field | Value |
|-------|-------|
| ID | `google-antigravity` |
| Docs | https://antigravity.google/docs (JavaScript SPA — use bundle strings / sitemap to verify) |
| Changelog | https://antigravity.google/changelog (SPA; changelog entries embedded in main-*.js) |
| Config paths | `.agents/rules/*.md`, `.agents/workflows/*.md` (plural is the Antigravity 2.0 default; singular `.agent/rules`, `.agent/workflows` still read as fallback), `.agent/skills/*/SKILL.md` (IDE), `.agents/skills/*/SKILL.md` (CLI), `.agents/hooks.json` (CLI hooks), `.agents/mcp_config.json` (workspace MCP), `AGENTS.md`, `GEMINI.md` |
| Global config paths | Skills: `~/.gemini/config/skills/*/SKILL.md` (shared across all Antigravity products) and `~/.gemini/antigravity-cli/skills/*/SKILL.md` (CLI-private) — both documented in the official Skills codelab. MCP: `~/.gemini/config/mcp_config.json` (shared global, resolved by CLI v1.0.14; the `~/.gemini/antigravity-cli/mcp_config.json` path is legacy). Rules: `~/.gemini/GEMINI.md` (dual-owner with Gemini CLI — Antigravity's IDE "+ Global" writes the same file; gemini-cli#16058 closed "not planned"). Hooks: `~/.gemini/config/hooks.json` (shared, since CLI v1.0.8). |
| Our generators | `scripts/generate_antigravity.py` (rules + workflows + skill pointer dual-emitted to `.agent/skills/` and `.agents/skills/`; `generate_global()` writes the pointer to the two HOME skill dirs). Native MCP project/global merge and removal are provided by `scripts/mcp_editors.py`. |
| Global install | `ai-toolkit install --editors antigravity` writes the skill pointer to `~/.gemini/config/skills/` and `~/.gemini/antigravity-cli/skills/`. Rules stay project-local (no mergeable global rules file beyond the Gemini-CLI-shared `~/.gemini/GEMINI.md`, covered by `--editors gemini`). `ai-toolkit mcp install --editor antigravity <template>` writes the global MCP config; add `--scope project --target <repo>` for `.agents/mcp_config.json`. |
| Tracked capabilities | Antigravity, agent manager, artifacts, MCP, workflows, rules, skills, hooks, `AGENTS.md`, `GEMINI.md`, agent permissions, global skills, `~/.gemini/config/mcp_config.json` |
| CLI notes | Antigravity CLI (GA 2026-05-19; latest CLI v1.0.14 2026-06-30, IDE 2.2.1). Hooks are IDE + CLI (`.agents/hooks.json` workspace, `~/.gemini/config/hooks.json` global; event set `PreToolUse`/`PostToolUse`/`PreInvocation`/`PostInvocation`/`Stop` — `PreInvocation`/`PostInvocation` have no Claude equivalent; shell tool is `run_command` with args at `.toolCall.args.CommandLine`). MCP: the official 2.1.4 changelog (2026-06-11) confirms that `url` is accepted alongside `serverUrl`; `httpUrl` is not documented and the adapter rejects it. The native adapter preserves documented `args`, `env`, `cwd`, `headers`, `authProviderType`, `oauth`, `disabled`, and `disabledTools` fields. A `generate_antigravity_hooks.py` remains backlog. |
| Doc access note | Docs are a JavaScript SPA, but the official search index exposes the current MCP guide and changelog text. Verify changelog claims against the dated official entry because the MCP guide's warning can lag schema releases. |

### Codex CLI

| Field | Value |
|-------|-------|
| ID | `codex-cli` |
| Docs | https://learn.chatgpt.com/docs/codex/cli (official Codex CLI documentation; the previous `https://developers.openai.com/codex` endpoint now redirects to the generic ChatGPT Learn overview; latest verified local/npm release: codex-cli 0.144.4, 2026-07-14) |
| Release notes | https://github.com/openai/codex/releases |
| Config paths | **Instructions:** project `AGENTS.md` (root→cwd chain, closest wins) and global `~/.codex/AGENTS.md` (`$CODEX_HOME/AGENTS.md`; `~/.codex/AGENTS.override.md` takes precedence). NOTE: `~/AGENTS.md` is NOT a global-instruction surface — Codex only reads it if a session's cwd is exactly `$HOME`. Plus `.agents/skills/*/SKILL.md`, `.codex/agents/*.toml`, `~/.codex/agents/*.toml`, `.codex/hooks.json`, `~/.codex/hooks.json`, `.codex/config.toml` (project layers, root→cwd, closest wins, trusted projects only), `~/.codex/config.toml`. |
| Our generators | `scripts/generate_codex.py`, `scripts/generate_codex_agents.py` (native custom-agent TOML), `scripts/generate_codex_hooks.py`, `scripts/generate_codex_skills.py` (opt-in via `--codex-skills`) |
| Rules delivery | Universal coding rules are inlined into `AGENTS.md` (Codex reads instructions only from AGENTS.md, not `.agents/rules/`); language rules ship as `<lang>-rules` skills under `.agents/skills/`. Global install writes `~/.codex/AGENTS.md` (not `~/AGENTS.md`, which Codex never loads globally); plugin-pack rules are marker-injected into the same file. `project_doc_max_bytes` default is 32 KiB and Codex silently truncates AGENTS.md past that (see codex-cli-compatibility.md). |
| Tracked hook events | Upstream canonical (codex-rs `HookEventName` enum): `PreToolUse`, `PostToolUse`, `PermissionRequest`, `PreCompact`, `PostCompact`, `SessionStart`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop` (10 events). We wire 9 of these to shared toolkit hook scripts (via `generate_codex_hooks.py` AND `inject-hook` propagation, kept in sync), mirroring the Claude Code mapping in `app/hooks.json`. `PostCompact` is not wired (its only hook was the removed environment-snapshot probe). |
| Tracked handler types | `command` (emitted by default; the only handler Codex actually runs). `prompt` and `agent` are parsed by Codex but NOT yet executed, so hand-authored handlers of those types are inert. |
| Other capabilities | `AGENTS.md`, `config.toml`, `mcp_servers`, sandbox policies, `.agents/skills/*/SKILL.md` (native Codex skill discovery path), `.codex/agents/*.toml` (native custom agents) |
| Version probe | `codex --version` |

### opencode

| Field | Value |
|-------|-------|
| ID | `opencode` |
| Docs | https://opencode.ai/docs |
| Release notes | https://github.com/sst/opencode/releases (redirects to anomalyco/opencode) |
| Config paths | `opencode.json`, `.opencode/agents/*.md`, `.opencode/commands/*.md`, `.opencode/plugins/*`, `.opencode/skills/*/SKILL.md` (v1.14+), `AGENTS.md`; skill fallback discovery: `.claude/skills/`, `.agents/skills/`, `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.agents/skills/` |
| Our generators | `scripts/generate_opencode.py`, `scripts/generate_opencode_agents.py`, `scripts/generate_opencode_commands.py`, `scripts/generate_opencode_json.py`, `scripts/generate_opencode_plugin.py` |
| Tracked plugin events | `session.created`, `session.compacted`, `session.deleted`, `message.updated`, `tool.execute.before`, `tool.execute.after`, `permission.asked`, `command.executed` |
| Other capabilities | `opencode.json` config, primary + subagent modes, `@`-mention subagents, `/`-invocation commands, MCP (local + remote), plugin hooks in JS/TS, native `SKILL.md` discovery with Claude-compatible fallback, `permission.skill.*` matrix |
| Version probe | `opencode --version` |
| Watch item | v1.16.0 (2026-06-05) shipped an experimental v2 skill registry (flat-file skills, `slash` frontmatter key). As of the 2026-06-23 sync (upstream v1.17.9) it is still undocumented and not stabilized: the skills docs show only the nested `SKILL.md` layout with no `slash` key, so `generate_opencode*.py` is unchanged. Re-check next sync. |

---

## How the Registry is Consumed

```
┌─────────────────────────┐
│  ecosystem_tools.json   │  ← authoritative config (this doc mirrors it)
└──────────┬──────────────┘
           │ read
           ▼
┌─────────────────────────┐     ┌─────────────────────────────────┐
│  ecosystem_doctor.py    │◄───►│  ecosystem-doctor-snapshot.json │  (last-seen state)
└──────────┬──────────────┘     └─────────────────────────────────┘
           │ emits
           ▼
    Drift report  (JSON or text)  →  human review  →  generator updates  →  commit
```

---

## Adding a New Tool

1. Append an entry to `scripts/ecosystem_tools.json` with all required fields (schema: `schema_version: 1`).
2. Add a generator under `scripts/generate_<tool>_*.py` (or link to an existing one).
3. Update this registry doc with a new section matching the format above.
4. Baseline the snapshot: `python3 scripts/ecosystem_doctor.py --update --tool <id>`.
5. Run the doctor again to confirm clean state: `python3 scripts/ecosystem_doctor.py --tool <id> --format text`.
6. Update tool count at the top of this document.

---

## Removing a Tool

1. Delete the tool's entry from `scripts/ecosystem_tools.json`.
2. Delete its section from this document.
3. Delete its snapshot entry from `benchmarks/ecosystem-doctor-snapshot.json` (or let the next `--update` prune it — currently not pruned automatically).
4. Decide whether to keep the generator (`scripts/generate_<tool>_*.py`) for backwards compatibility or delete it.
5. Remove references from `README.md`, `manifest.json` `description` field, and `kb/procedures/maintenance-sop.md` `Supported editors` line.

---

## Related

- [Ecosystem Sync SOP](../procedures/ecosystem-sync-sop.md) — how to use the doctor
- [MCP Editor Compatibility](./mcp-editor-compatibility.md) — MCP-specific subset
- `scripts/ecosystem_tools.json` — source of truth
- `scripts/ecosystem_doctor.py` — drift detector
- `benchmarks/ecosystem-doctor-snapshot.json` — last-seen state
