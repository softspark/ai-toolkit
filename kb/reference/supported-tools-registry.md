---
title: "Supported Tools Registry"
category: reference
service: ai-toolkit
tags: [editors, platforms, generators, integration, ecosystem]
version: "1.1.0"
created: "2026-04-23"
last_updated: "2026-04-23"
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
| Docs | https://platform.claude.com/docs/en/claude-code |
| Release notes | https://github.com/anthropics/claude-code/releases |
| Config paths | `~/.claude/settings.json`, `.claude/settings.local.json`, `CLAUDE.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`, `~/.claude/themes/*.json` (v2.1.118+) |
| Our generators | — (Claude Code is the primary target; toolkit content ships directly as `.md` files and `settings.json` merges) |
| Tracked hook events | Core: `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `Notification`. Tool: `PreToolUse`, `PostToolUse`. Turn: `Stop`, `StopFailure`. Subagent: `SubagentStart`, `SubagentStop`. Compaction: `PreCompact`, `PostCompact`. Permissions: `PermissionRequest`, `PermissionDenied`. Elicitation: `Elicitation`, `ElicitationResult`. Teams: `TaskCreated`, `TaskCompleted`, `TeammateIdle`. Worktrees/env: `WorktreeCreate`, `WorktreeRemove`, `CwdChanged`, `FileChanged`, `ConfigChange`. Setup: `Setup`, `InstructionsLoaded` |
| Tracked handler types | `command`, `prompt`, `agent`, `mcp_tool` |
| Other capabilities | slash commands, MCP server/client, sub-agent, output style, `SKILL.md` (≥500 lines warn) |
| Version probe | `claude --version` |

---

## Editor Integrations

### Cursor

| Field | Value |
|-------|-------|
| ID | `cursor` |
| Docs | https://cursor.com/docs |
| Changelog | https://cursor.com/changelog |
| Stable docs mirror | https://cursor.com/llms.txt (all doc pages have .md twins) |
| Config paths | `.cursorrules`, `.cursor/rules/*.mdc`, `.cursor/rules/*.md`, `AGENTS.md`, `.cursor/mcp.json`, `~/.cursor/mcp.json`, `.cursor/skills/*/SKILL.md`, `.cursor/agents/*.md`, `.cursor/hooks.json`, `~/.cursor/hooks.json` |
| Compat read paths | `.claude/skills/`, `.claude/agents/`, `.codex/skills/`, `.codex/agents/` (Cursor cross-reads these so ai-toolkit's Claude install works automatically) |
| Our generators | `scripts/generate_cursor_rules.py`, `scripts/generate_cursor_mdc.py` |
| Tracked capabilities | `cursorrules`, `.cursor/rules`, `AGENTS.md`, `mcp.json`, Composer, Agent Mode, hooks.json, subagents, skills, plugins |

### Windsurf

| Field | Value |
|-------|-------|
| ID | `windsurf` |
| Docs | https://docs.windsurf.com |
| Changelog | https://windsurf.com/changelog |
| Stable docs mirror | https://docs.windsurf.com/llms.txt + per-page .md twins |
| Config paths | `.windsurfrules`, `.windsurf/rules/*.md`, `.windsurf/workflows/*.md`, `AGENTS.md`, `~/.codeium/windsurf/memories/global_rules.md`, `~/.codeium/windsurf/mcp_config.json` |
| Compat read paths | `.agents/skills/`, `~/.agents/skills/`, (with Claude Code config-reading) `.claude/skills/`, `~/.claude/skills/` |
| Our generators | `scripts/generate_windsurf.py`, `scripts/generate_windsurf_rules.py` |
| Tracked capabilities | Cascade, `windsurfrules`, `AGENTS.md`, activation triggers (`always_on`/`glob`/`model_decision`), workflows, MCP, memories, hooks |
| Activation modes emitted | always_on (agents/security/quality), glob (testing + language rules), model_decision (code-style/workflow) |

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
| Config paths | `GEMINI.md`, `.gemini/settings.json`, `~/.gemini/settings.json`, `.gemini/commands/*.toml`, `.gemini/skills/*/SKILL.md`, `.agents/skills/*/SKILL.md`, `.gemini/extensions/gemini-extension.json` |
| Our generators | `scripts/generate_gemini.py` |
| Tracked capabilities | `GEMINI.md`, `mcpServers`, tools, `settings.json`, `BeforeTool`, `AfterTool`, `BeforeAgent`, `AfterAgent`, `BeforeModel`, `SessionStart`, `SessionEnd`, `Stop`, `SKILL.md`, `activate_skill`, custom commands, `gemini-extension.json` |
| Version probe | `gemini --version` |
| Latest upstream | v0.39.0 (2026-04-23) |

### Cline

| Field | Value |
|-------|-------|
| ID | `cline` |
| Docs | https://docs.cline.bot |
| Release notes | https://github.com/cline/cline/releases |
| Config paths | `.clinerules/*.md`, `.clinerules/workflows/*.md`, `.clinerules/hooks/`, `.cline/skills/`, `~/.cline/data/settings/cline_mcp_settings.json`, `~/Documents/Cline/Rules/` |
| Our generators | `scripts/generate_cline.py`, `scripts/generate_cline_rules.py` |
| Tracked capabilities | `clinerules`, Plan Mode, Act Mode, MCP, custom modes, workflows, hooks, skills, subagents, conditional rules |
| Notes | Conditional rules (`paths:` YAML frontmatter) are emitted for testing and language-specific rules since 2026-04. Skills (`.cline/skills/`) and hooks (`.clinerules/hooks/`) remain experimental upstream and are not yet generated. |

### Roo Code

| Field | Value |
|-------|-------|
| ID | `roo-code` |
| Docs | https://docs.roocode.com |
| Release notes | https://github.com/RooCodeInc/Roo-Code/releases |
| Config paths | `.roomodes`, `.roo/rules/*.md`, `.roo/rules-{slug}/*.md`, `.roo/mcp.json`, `~/.roo/rules/`, `~/.roo/settings/custom_modes.yaml`, `~/.roo/settings/mcp_settings.json` |
| Our generators | `scripts/generate_roo_modes.py`, `scripts/generate_roo_rules.py` |
| Tracked capabilities | `roomodes`, custom modes, Code Actions, MCP, Orchestrator mode, `whenToUse`, `description`, `roleDefinition`, `groups` |
| Notes | `.roomodes` now includes `description` and `whenToUse` for every mode (since 2026-04). YAML `.roomodes` is upstream-preferred but not yet emitted — JSON is still accepted by Roo. |

### Aider

| Field | Value |
|-------|-------|
| ID | `aider` |
| Docs | https://aider.chat/docs |
| Changelog | https://aider.chat/HISTORY.html |
| Config paths | `.aider.conf.yml`, `CONVENTIONS.md`, `~/.aider.conf.yml` |
| Our generators | `scripts/generate_aider_conf.py`, `scripts/generate_conventions.py` |
| Tracked capabilities | `.aider.conf.yml`, `CONVENTIONS.md`, `architect`, `auto-accept-architect`, `read`, `lint-cmd`, `test-cmd`, `commit-prompt`, `attribute-co-authored-by`, `chat-language`, `commit-language`, `watch-files`, `auto-commits` |
| Version probe | `aider --version` |
| Latest upstream | v0.86.1 (Aug 2025) |

### Augment

| Field | Value |
|-------|-------|
| ID | `augment` |
| Docs | https://docs.augmentcode.com |
| Changelog | https://www.augmentcode.com/changelog |
| Config paths | `.augment/rules/*.md`, `.augment/guidelines.md` (legacy), `.augment/agents/*.md`, `.augment/commands/*.md`, `.augment/skills/*/SKILL.md`, `~/.augment/rules/*.md`, `~/.augment/settings.json`, `/etc/augment/settings.json` |
| Our generators | `scripts/generate_augment.py`, `scripts/generate_augment_rules.py` |
| Tracked capabilities | `.augment`, Agent mode, Next Edit, MCP, context engine, Auggie CLI, `always_apply`, `agent_requested`, subagents, custom commands, `SKILL.md`, `PreToolUse`, `PostToolUse`, `SessionStart`, `SessionEnd`, `Stop`, ACP Mode |
| SPA caveat | Mintlify Next.js SPA; use `https://docs.augmentcode.com/<path>.md` siblings (discoverable via `/llms.txt`) for machine reads |

### Google Antigravity

| Field | Value |
|-------|-------|
| ID | `google-antigravity` |
| Docs | https://antigravity.google/docs (JavaScript SPA — use bundle strings / sitemap to verify) |
| Changelog | https://antigravity.google/changelog (SPA; changelog entries embedded in main-*.js) |
| Config paths | `.agent/rules/*.md`, `.agent/workflows/*.md`, `.agent/skills/*/SKILL.md`, `AGENTS.md`, `GEMINI.md` |
| Our generators | `scripts/generate_antigravity.py` (rules + workflows + skill pointer) |
| Tracked capabilities | Antigravity, agent manager, artifacts, MCP, workflows, rules, skills, `AGENTS.md`, `GEMINI.md`, agent permissions |
| Doc access note | Docs are JS-SPA — verify via `main-*.js` bundle strings or community skill repos. `WebFetch` returns an empty shell. |

### Codex CLI

| Field | Value |
|-------|-------|
| ID | `codex-cli` |
| Docs | https://github.com/openai/codex (redirects from developers.openai.com/codex) |
| Release notes | https://github.com/openai/codex/releases |
| Config paths | `AGENTS.md`, `.agents/rules/*.md`, `.codex/hooks.json`, `.codex/skills/*/SKILL.md`, `~/.codex/config.toml` |
| Our generators | `scripts/generate_codex.py`, `scripts/generate_codex_rules.py`, `scripts/generate_codex_hooks.py` |
| Tracked hook events | `PreToolUse`, `PostToolUse`, `SessionStart`, `UserPromptSubmit`, `Stop`, `PermissionRequest` (6 events supported upstream in `config.toml`) |
| Tracked handler types | `command` (emitted by default); `prompt` and `agent` available upstream but authored by hand |
| Other capabilities | `AGENTS.md`, `config.toml`, `mcp_servers`, sandbox policies, `.codex/skills/*/SKILL.md` (native discovery, not auto-emitted by ai-toolkit yet) |
| Version probe | `codex --version` |

### opencode

| Field | Value |
|-------|-------|
| ID | `opencode` |
| Docs | https://opencode.ai/docs |
| Release notes | https://github.com/sst/opencode/releases |
| Config paths | `opencode.json`, `.opencode/agents/*.md`, `.opencode/commands/*.md`, `.opencode/plugins/*`, `.opencode/skills/*/SKILL.md` (v1.14+), `AGENTS.md`, `.claude/skills/*/SKILL.md` (fallback discovery) |
| Our generators | `scripts/generate_opencode.py`, `scripts/generate_opencode_agents.py`, `scripts/generate_opencode_commands.py`, `scripts/generate_opencode_json.py`, `scripts/generate_opencode_plugin.py` |
| Tracked plugin events | `session.created`, `session.compacted`, `session.deleted`, `message.updated`, `tool.execute.before`, `tool.execute.after`, `permission.asked`, `command.executed` |
| Other capabilities | `opencode.json` config, primary + subagent modes, `@`-mention subagents, `/`-invocation commands, MCP (local + remote), plugin hooks in JS/TS, native `SKILL.md` discovery with Claude-compatible fallback, `permission.skill.*` matrix |
| Version probe | `opencode --version` |

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
