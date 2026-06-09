---
title: "Supported Tools Registry"
category: reference
service: ai-toolkit
tags: [editors, platforms, generators, integration, ecosystem]
version: "1.5.0"
created: "2026-04-23"
last_updated: "2026-06-09"
description: "Human-readable view of scripts/ecosystem_tools.json — the canonical list of tools ai-toolkit integrates with (Claude Code + 11 editors), their documentation URLs, config paths, our generators, and tracked capability markers."
---

# Supported Tools Registry

The canonical data lives in **`scripts/ecosystem_tools.json`** and is consumed by `scripts/ecosystem_doctor.py`. This document is a derived view — when the JSON changes, update this table too.

## Tool Count: 12

1 primary runtime (Claude Code) + 11 editor integrations.

---

## Primary Runtime

### Claude Code

| Field | Value |
|-------|-------|
| ID | `claude-code` |
| Docs | https://code.claude.com/docs (platform.claude.com/docs 307-redirects here) |
| Release notes | https://github.com/anthropics/claude-code/releases |
| Changelog | https://code.claude.com/docs/en/changelog (lists current 2.1.170) |
| Config paths | `~/.claude/settings.json`, `.claude/settings.json` (project, committed), `.claude/settings.local.json`, `CLAUDE.md`, `.claude/rules/*.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`, `~/.claude/themes/*.json` (v2.1.118+) |
| Our generators | — (Claude Code is the primary target; toolkit content ships directly as `.md` files and `settings.json` merges) |
| Tracked hook events | Core: `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `Notification`, `MessageDisplay`. Tool: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`. Turn: `Stop`, `StopFailure`, `UserPromptExpansion`. Subagent: `SubagentStart`, `SubagentStop`. Compaction: `PreCompact`, `PostCompact`. Permissions: `PermissionRequest`, `PermissionDenied`. Elicitation: `Elicitation`, `ElicitationResult`. Teams: `TaskCreated`, `TaskCompleted`, `TeammateIdle`. Worktrees/env: `WorktreeCreate`, `WorktreeRemove`, `CwdChanged`, `FileChanged`, `ConfigChange`. Setup: `Setup`, `InstructionsLoaded` |
| Tracked handler types | `command`, `prompt`, `agent`, `mcp_tool`, `http` (POST event JSON to allowlisted URLs via `allowedHttpHookUrls`) |
| Other capabilities | slash commands, MCP server/client, sub-agent, output style, `SKILL.md` (≥500 lines warn) |
| Version probe | `claude --version` |
| Notes | v2.1.169 added `disableBundledSkills` setting + `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS` env var (hides bundled skills/built-in slash commands from the model; toolkit skills in `.claude/skills/` are unaffected — useful when toolkit skills overlap built-ins) and `claude --safe-mode` / `CLAUDE_CODE_SAFE_MODE` (starts with hooks, skills, agents, and CLAUDE.md disabled — first isolation step when debugging toolkit rule enforcement). `fallbackModel` settings key (v2.1.166) noted as not-adopted (class C, no toolkit surface writes model settings). |

---

## Editor Integrations

### Cursor

| Field | Value |
|-------|-------|
| ID | `cursor` |
| Docs | https://cursor.com/docs |
| Changelog | https://cursor.com/changelog |
| Stable docs mirror | https://cursor.com/llms.txt (all doc pages have .md twins) |
| Config paths | `.cursorrules`, `.cursor/rules/*.mdc` (plain `.md` files in `.cursor/rules/` are **ignored** by the rules system), `AGENTS.md`, `.cursor/mcp.json`, `~/.cursor/mcp.json`, `.cursor/skills/*/SKILL.md`, `~/.cursor/skills/*/SKILL.md`, `.cursor/agents/*.md`, `~/.cursor/agents/*.md`, `.cursor/hooks.json` |
| Compat read paths | skills: `.agents/skills/`, `~/.agents/skills/`, `.claude/skills/`, `~/.claude/skills/`, `.codex/skills/`, `~/.codex/skills/`; subagents: `.claude/agents/`, `~/.claude/agents/`, `.codex/agents/`, `~/.codex/agents/` (`.cursor/` wins on name conflicts) |
| Our generators | `scripts/generate_cursor_rules.py`, `scripts/generate_cursor_mdc.py`, `scripts/generate_cursor_hooks.py` (profile=full), `scripts/generate_cursor_agents.py` (profile=full), `scripts/generate_cursor_skills.py` (profile=full pointer) |
| Tracked capabilities | `cursorrules`, `.cursor/rules`, `AGENTS.md`, `mcp.json`, Composer, Agent Mode, hooks.json, subagents, skills, plugins |

### Windsurf

| Field | Value |
|-------|-------|
| ID | `windsurf` |
| Docs | https://docs.devin.ai/desktop (Windsurf rebranded to Devin Desktop ~2026-06-02; docs.windsurf.com resolves here) |
| Changelog | https://docs.devin.ai/desktop/changelog (windsurf.com/changelog 308-permanent-redirects here) |
| Stable docs mirror | https://docs.devin.ai/desktop/... per-page .md twins; legacy `.windsurf/`, `.windsurfrules`, `~/.codeium/windsurf/` paths still read as fallback (new canonical: `.devin/`) |
| Config paths | **Primary (Devin Desktop):** `.devin/rules/*.md`, `.devin/workflows/*.md`, `.devin/skills/*/SKILL.md`, `.devin/config.json`, `.devin/config.local.json`, `~/.config/devin/config.json` (Devin Local MCP/permissions). **Legacy fallback:** `.windsurfrules`, `.windsurf/rules/*.md`, `.windsurf/workflows/*.md`, `.windsurf/skills/*/SKILL.md`, `~/.codeium/windsurf/memories/global_rules.md`, `~/.codeium/windsurf/skills/*/SKILL.md`, `~/.codeium/windsurf/mcp_config.json`. Plus `AGENTS.md`. |
| Compat read paths | `.agents/skills/`, `~/.agents/skills/`, (with Claude Code config-reading) `.claude/skills/`, `~/.claude/skills/` |
| Our generators | `scripts/generate_windsurf.py`, `scripts/generate_windsurf_rules.py` (dual-emits `.devin/` + `.windsurf/`), `scripts/generate_windsurf_hooks.py` (profile=full; **Cascade-scoped, deprecated**), `scripts/generate_windsurf_skills.py` (global + profile=full pointer, dual-emits) |
| Tracked capabilities | Cascade, `windsurfrules`, `AGENTS.md`, activation triggers (`always_on`/`glob`/`model_decision`), workflows, skills, MCP, memories, hooks |
| Activation modes emitted | always_on (agents/security/quality), glob (testing + language rules), model_decision (code-style/workflow) |
| Sunset notes | Cascade agent is available only through **2026-07-01**; Devin Local is the default agent since 2026-06-02. The `.windsurf/hooks.json` surface dies with Cascade — migrate to Devin CLI lifecycle hooks (docs.devin.ai/cli/extensibility/hooks/\*) before that date. Devin CLI ("Devin for Terminal") shares the Devin Local harness, reads `AGENTS.md` and the standard `SKILL.md` format; not yet a separate registry entry. |

### GitHub Copilot

| Field | Value |
|-------|-------|
| ID | `github-copilot` |
| Docs | https://docs.github.com/en/copilot |
| Release notes | https://github.blog/changelog/label/copilot/ |
| Config paths | `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, `.github/prompts/*.prompt.md`, `AGENTS.md` |
| Our generators | `scripts/generate_copilot.py` |
| Tracked capabilities | `copilot-instructions.md`, Copilot Chat, Copilot Workspace, Copilot cloud agent, `applyTo`, custom agents, prompt files, `instructions.md`, MCP |
| Tier notes | Custom agents (`.github/agents/*.agent.md`) and repo-level MCP config are Pro/Pro+/Business/Enterprise only and intentionally not integrated (class C per ecosystem-sync SOP). |

### Gemini CLI

| Field | Value |
|-------|-------|
| ID | `gemini-cli` |
| Docs | https://github.com/google-gemini/gemini-cli/tree/main/docs |
| Release notes | https://github.com/google-gemini/gemini-cli/releases |
| Config paths | `GEMINI.md`, `.gemini/settings.json`, `~/.gemini/settings.json`, `.gemini/commands/*.toml`, `.gemini/skills/*/SKILL.md`, `.agents/skills/*/SKILL.md`, `~/.gemini/skills/*/SKILL.md`, `~/.agents/skills/*/SKILL.md` (the `.agents/skills` alias wins over `.gemini/skills` within the same tier), `.gemini/extensions/gemini-extension.json` |
| Our generators | `scripts/generate_gemini.py`, `scripts/generate_gemini_hooks.py` (profile>=standard), `scripts/generate_gemini_commands.py` (profile=full), `scripts/generate_gemini_skills.py` (profile=full) |
| Tracked capabilities | `GEMINI.md`, `mcpServers`, tools, `settings.json`, `BeforeTool`, `AfterTool`, `BeforeToolSelection`, `BeforeAgent`, `AfterAgent`, `BeforeModel`, `AfterModel`, `Notification`, `PreCompress`, `SessionStart`, `SessionEnd`, `SKILL.md`, `activate_skill`, custom commands, `gemini-extension.json` (no native `Stop` event — generator maps Stop-equivalent to `AfterAgent`; 11 documented hook events total) |
| Version probe | `gemini --version` |
| Latest upstream | v0.45.2 (2026-06-05). NOTE: Gemini CLI drops free/paid tiers 2026-06-18 in favor of Antigravity CLI (we ship `generate_antigravity.py`); enterprise Code Assist keeps Gemini CLI. |

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
| Docs | https://roocodeinc.github.io/Roo-Code (docs.roocode.com 301-redirects here) |
| Release notes | https://github.com/RooCodeInc/Roo-Code/releases (**ARCHIVED** — repo read-only since 2026-05-15, frozen at v3.54.0; community fork reportedly continues) |
| Config paths | `.roomodes`, `.roo/rules/*.md`, `.roo/rules-{slug}/*.md`, `.roo/mcp.json`, `~/.roo/rules/`, `~/.roo/custom_modes.yaml`, `mcp_settings.json` (global via Roo settings UI) |
| Our generators | `scripts/generate_roo_modes.py`, `scripts/generate_roo_rules.py` |
| Tracked capabilities | `roomodes`, custom modes, Code Actions, MCP, Orchestrator mode, `whenToUse`, `description`, `roleDefinition`, `groups` |
| Notes | `.roomodes` now includes `description` and `whenToUse` for every mode (since 2026-04). YAML `.roomodes` is upstream-preferred but not yet emitted — JSON is still accepted by Roo. Global install writes only `~/.roo/rules/` because the exact global MCP settings path is UI-managed. |

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
| Tracked capabilities | `.augment`, Agent mode, Next Edit, MCP, context engine, Auggie CLI, `always_apply`, `agent_requested`, subagents, custom commands, `SKILL.md`, `PreToolUse`, `PostToolUse`, `SessionStart`, `SessionEnd`, `Stop`, `Notification`, ACP Mode |
| SPA caveat | Mintlify Next.js SPA; use `https://docs.augmentcode.com/<path>.md` siblings (discoverable via `/llms.txt`) for machine reads |

### Google Antigravity

| Field | Value |
|-------|-------|
| ID | `google-antigravity` |
| Docs | https://antigravity.google/docs (JavaScript SPA — use bundle strings / sitemap to verify) |
| Changelog | https://antigravity.google/changelog (SPA; changelog entries embedded in main-*.js) |
| Config paths | `.agents/rules/*.md`, `.agents/workflows/*.md` (plural is the Antigravity 2.0 default; singular `.agent/rules`, `.agent/workflows` still read as fallback), `.agent/skills/*/SKILL.md` (IDE), `.agents/skills/*/SKILL.md` (CLI), `.agents/hooks.json` (CLI hooks), `.agents/mcp_config.json` (CLI MCP), `AGENTS.md`, `GEMINI.md` |
| Our generators | `scripts/generate_antigravity.py` (rules + workflows + skill pointer dual-emitted to `.agent/skills/` and `.agents/skills/`) |
| Tracked capabilities | Antigravity, agent manager, artifacts, MCP, workflows, rules, skills, hooks, `AGENTS.md`, `GEMINI.md`, agent permissions |
| CLI notes | Antigravity CLI (GA 2026-05-19): hooks in `.agents/hooks.json` use Claude-style event names (`PreToolUse`, not Gemini's `BeforeTool`) with a JSON stdin/stdout decision contract; MCP config `.agents/mcp_config.json` requires `serverUrl` (legacy `url`/`httpUrl` fail silently). Global MCP config path is inconsistently reported across sources (`~/.gemini/antigravity-cli/` vs `~/.gemini/config/`) — only the workspace path is registered until verified via `agy inspect`. |
| Doc access note | Docs are JS-SPA — verify via `main-*.js` bundle strings or community skill repos. `WebFetch` returns an empty shell. The sitemap.xml is stale (omits the `cli-*` doc pages), so sitemap-based monitoring misses CLI doc additions. |

### Codex CLI

| Field | Value |
|-------|-------|
| ID | `codex-cli` |
| Docs | https://developers.openai.com/codex (live docs site; config pages split into `/codex/config-basic`, `/codex/config-reference`, `/codex/config-advanced` plus `/codex/hooks`, `/codex/skills`; latest stable codex-cli 0.138.0, 2026-06) |
| Release notes | https://github.com/openai/codex/releases |
| Config paths | `AGENTS.md`, `.agents/skills/*/SKILL.md`, `.codex/hooks.json`, `.codex/config.toml` (project layers, root→cwd, closest wins, trusted projects only), `~/.codex/config.toml` |
| Our generators | `scripts/generate_codex.py`, `scripts/generate_codex_hooks.py`, `scripts/generate_codex_skills.py` (opt-in via `--codex-skills`) |
| Rules delivery | Universal coding rules are inlined into `AGENTS.md` (Codex reads instructions only from AGENTS.md, not `.agents/rules/`); language rules ship as `<lang>-rules` skills under `.agents/skills/`. |
| Tracked hook events | Upstream canonical (codex-rs `HookEventName` enum): `PreToolUse`, `PostToolUse`, `PermissionRequest`, `PreCompact`, `PostCompact`, `SessionStart`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop` (10 events). We wire all 10 to shared toolkit hook scripts, mirroring the Claude Code mapping in `app/hooks.json`. |
| Tracked handler types | `command` (emitted by default); `prompt` and `agent` available upstream but authored by hand |
| Other capabilities | `AGENTS.md`, `config.toml`, `mcp_servers`, sandbox policies, `.agents/skills/*/SKILL.md` (native Codex skill discovery path) |
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
| Watch item | v1.16.0 (2026-06-05) ships an experimental v2 skill registry (flat-file skills, `slash` frontmatter key) — undocumented as of 2026-06-09; re-check next sync before touching `generate_opencode*.py`. |

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
