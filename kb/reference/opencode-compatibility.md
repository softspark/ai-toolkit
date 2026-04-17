---
title: "AI Toolkit - opencode Compatibility"
category: reference
service: ai-toolkit
tags: [opencode, compatibility, install, skills, hooks, mcp, plugins]
version: "1.0.0"
created: "2026-04-16"
last_updated: "2026-04-16"
description: "Reference for how ai-toolkit integrates with opencode — AGENTS.md, subagents, slash commands, JS plugin hook bridge, and MCP merge into opencode.json."
---

# AI Toolkit - opencode Compatibility

## Summary

opencode (https://opencode.ai) is the 11th supported editor. `ai-toolkit install --editors opencode` (or `--editors all`) lays down a full native integration: shared `AGENTS.md`, per-agent `.opencode/agents/` files, per-command `.opencode/commands/` files, a JS plugin bridging toolkit Bash hooks to opencode lifecycle events, and MCP server merge into `opencode.json`.

opencode also reads `CLAUDE.md` as a fallback, so a user without the native integration still gets baseline rules. The native path adds subagents, slash commands, hooks, and MCP.

## Local Install Outputs

`ai-toolkit install --local --editors opencode` generates:

- `AGENTS.md` (shared with Codex CLI via distinct marker sections)
- `.opencode/agents/ai-toolkit-*.md` (one per ai-toolkit agent, `mode: subagent`)
- `.opencode/commands/ai-toolkit-*.md` (one per user-invocable skill, required `template: |` frontmatter field)
- `.opencode/plugins/ai-toolkit-hooks.js` (JS plugin bridging Bash hooks)
- `opencode.json` (MCP key merged from `.mcp.json`, user keys preserved)

## Global Install Outputs

`ai-toolkit install --editors opencode` (no `--local`) lays down:

- `~/.config/opencode/AGENTS.md`
- `~/.config/opencode/agents/ai-toolkit-*.md`
- `~/.config/opencode/commands/ai-toolkit-*.md`
- `~/.config/opencode/plugins/ai-toolkit-hooks.js`
- `~/.config/opencode/opencode.json` (MCP merge, user keys preserved)

Files land directly under `~/.config/opencode/` (no `.opencode/` nesting) because that is the global layout opencode expects per https://opencode.ai/docs/config/. Shared hook scripts stay in `~/.softspark/ai-toolkit/hooks/` and are referenced by the global JS plugin.

## Editor Surface Comparison

| Feature            | Claude Code | Codex CLI       | opencode                                  |
|--------------------|-------------|-----------------|-------------------------------------------|
| Rules file         | `CLAUDE.md` | `AGENTS.md`     | `AGENTS.md` + `CLAUDE.md` fallback        |
| Subagents          | Yes         | No              | Yes (`mode: subagent`)                    |
| Slash commands     | Skills      | Adapted skills  | Native commands with frontmatter          |
| MCP                | Yes         | Yes             | Yes (`opencode.json`)                     |
| Lifecycle hooks    | JSON config | `.codex/hooks`  | JS/TS plugins (~30+ events)               |
| Global config dir  | `~/.claude` | `~/.codex`      | `~/.config/opencode`                      |
| Project config dir | `.claude`   | `.agents`       | `.opencode`                               |

## Shared AGENTS.md

opencode and Codex CLI both read `AGENTS.md`. The toolkit emits two distinct marker-bounded sections in a single file, so installing both editors does not clobber either. The Codex section is produced by `generate_codex.py`; the opencode section is produced by `generate_opencode.py`. Both sections reuse `codex_skill_adapter.py` because both editors lack Claude-only orchestration primitives (`Agent`, `TeamCreate`, `TaskCreate`).

## Subagent Translation Model

Each file in `app/agents/*.md` emits a corresponding `.opencode/agents/ai-toolkit-<name>.md` with:

- `description` — copied from the source agent frontmatter
- `mode: subagent` (required)
- `color` — copied when present

The `model` field is deliberately omitted. opencode requires the `provider/model-id` form; ai-toolkit only stores a short alias (`opus`/`sonnet`/`haiku`) which cannot be mapped without assuming a provider. opencode falls back to the user's `default_agent` / top-level `model` config.

Opencode treats these files as auto-completable with `@` and can delegate to them from the primary agent.

## Slash Command Translation Model

Only user-invocable skills (`user-invocable: true` or no `disable-model-invocation`) emit to `.opencode/commands/`. Knowledge skills (`user-invocable: false`) are intentionally skipped — they are not intended as commands.

Each command file carries opencode's required `template: |` frontmatter field, built from the SKILL.md body.

## Hook Bridge (JS Plugin)

`.opencode/plugins/ai-toolkit-hooks.js` is a single-file plugin that maps opencode events to the shared Bash hooks in `~/.softspark/ai-toolkit/hooks/`:

| opencode event             | Bash hook(s)                                                       |
|----------------------------|--------------------------------------------------------------------|
| `session.created`          | `session-start.sh` + `session-context.sh` + `mcp-health.sh`        |
| `session.compacted`        | `pre-compact.sh` + `pre-compact-save.sh` (PreCompact equivalent)   |
| `session.deleted`          | `session-end.sh` + `save-session.sh`                               |
| `message.updated`          | `user-prompt-submit.sh` + `track-usage.sh`                         |
| `message.part.updated`     | `user-prompt-submit.sh` + `track-usage.sh`                         |
| `tool.execute.before` (bash) | `guard-destructive.sh` + `commit-quality.sh`                     |
| `tool.execute.after`       | `post-tool-use.sh`                                                 |
| `permission.asked`         | `guard-destructive.sh` (approval-gate bridge)                      |
| `command.executed`         | `post-tool-use.sh`                                                 |

Plugin exports a single named export `AiToolkitHooks` — per opencode docs, named exports only (no default export). Hook scripts are invoked via Bun's `$` with the script path bound as a JS constant; opencode event payloads are passed as JSON on stdin, never interpolated into the shell command, so payload data cannot inject shell metacharacters. The toolkit's `exit 2` semantics for PreToolUse guards are preserved and bubble up as the plugin's return code.

**Intentionally unmapped events**: `tui.*`, `lsp.*`, `installation.*`, `session.idle/status/updated/error/diff`, `file.edited`, `file.watcher.updated`, `todo.updated`, `shell.env`, `server.connected`, `message.*.removed`, `experimental.*` — no matching Bash hook in the toolkit, or the event is opencode-UI-only.

## MCP Merge (opencode.json)

`generate_opencode_json.py` reads `.mcp.json` and merges its servers under the `mcp` key in `opencode.json`:

- `local` shape entries are translated to opencode's local command shape.
- `remote` shape entries are translated to opencode's remote URL shape.
- User-authored keys in `opencode.json` (outside `mcp`) are preserved.
- Re-running the generator is idempotent.

## Auto-Detection

The installer detects opencode as configured when any of these markers exist:

- `opencode.json`
- `.opencode/` directory
- `.opencode/agents/`
- `.opencode/commands/`
- `~/.config/opencode/`

`ai-toolkit update` picks up opencode automatically when detection fires.

## Uninstall & Reset

`scripts/install_steps/ai_tools.py` cleanup only removes ai-toolkit-marked artifacts:

- Generated `.opencode/agents/ai-toolkit-*.md`
- Generated `.opencode/commands/ai-toolkit-*.md`
- Generated `.opencode/plugins/ai-toolkit-hooks.js`
- Managed markers from `AGENTS.md`
- `mcp` key entries injected by the toolkit (user keys preserved)

User-authored opencode files and user-authored `opencode.json` keys are never deleted.

## Behavioral Limits

- opencode does not expose the full Claude hook event surface; only the events in the mapping table above are bridged. Claude-only events (`TaskCompleted`, `TeammateIdle`, `SubagentStart`, `SubagentStop`, `PreCompact`) are silently skipped.
- Multi-agent orchestration skills (`/orchestrate`, `/workflow`, `/swarm`, `/teams`, `/subagent-development`) run through the Codex adaptation layer — they use opencode subagents and explicit file ownership instead of Claude's `Agent`/`TaskCreate` primitives.

## Verification

The opencode integration is verified by:

1. Generator contract tests for the five `generate_opencode*.py` scripts (bats)
2. MCP merge idempotency and user-key preservation tests
3. Plugin export shape and event coverage tests
4. Auto-detection tests for install / update flow
5. `validate.py --strict` + `audit_skills.py --ci` in CI

## CLI Commands

| Command | Description |
|---------|-------------|
| `ai-toolkit opencode-md` | Generate `AGENTS.md` body for opencode |
| `ai-toolkit opencode-agents` | Generate `.opencode/agents/ai-toolkit-*.md` |
| `ai-toolkit opencode-commands` | Generate `.opencode/commands/ai-toolkit-*.md` |
| `ai-toolkit opencode-plugin` | Generate `.opencode/plugins/ai-toolkit-hooks.js` |
| `ai-toolkit opencode-json` | Merge MCP servers into `opencode.json` |

## Related

- `kb/reference/skills-catalog.md`
- `kb/reference/agents-catalog.md`
- `kb/reference/codex-cli-compatibility.md`
- `kb/reference/architecture-overview.md`
- `kb/reference/global-install-model.md`
- `kb/reference/mcp-editor-compatibility.md`
