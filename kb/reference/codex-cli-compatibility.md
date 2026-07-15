---
title: "AI Toolkit - Codex CLI Compatibility"
category: reference
service: ai-toolkit
tags: [codex, compatibility, install, skills, hooks]
version: "1.0.4"
created: "2026-04-12"
last_updated: "2026-07-14"
description: "Reference for how ai-toolkit maps Claude-oriented skills, hooks, and plugin packs to Codex CLI."
---

# AI Toolkit - Codex CLI Compatibility

## Summary

Codex CLI now receives the full `ai-toolkit` skill catalog during local install.

Native Codex-compatible skills are linked directly into `.agents/skills/`.
Skills that contain Claude-only tools, prompt placeholders, or skill-directory
variables are generated as Codex wrappers. The wrappers preserve workflow intent
using semantic subagent and planning guidance instead of version-specific tool
signatures.

Experimental plugin packs can also target the Codex user surface with
`ai-toolkit plugin install --editor codex`, which layers plugin-specific skills,
rules, and hooks onto the active `CODEX_HOME` without changing project-local
configuration.

## Local Install Outputs

`ai-toolkit install --local --editors codex` generates:

- `AGENTS.md` (project root; universal coding rules inlined — Codex reads instructions only from AGENTS.md, not `.agents/rules/`)
- `.agents/skills/*`
- `.codex/hooks.json`
- `.codex/hooks/*` (self-contained executable hook assets)
- `.codex/agents/*.toml`
- `.codex/config.toml` when project MCP servers are selected

Project-local Codex paths never follow `CODEX_HOME`; the variable selects the
user configuration root only.

## Global Core Install Outputs

`ai-toolkit install --editors codex` writes Codex-owned user files below the
active `CODEX_HOME` (default `~/.codex`):

- `$CODEX_HOME/AGENTS.md`
- `$CODEX_HOME/agents/*.toml`
- `$CODEX_HOME/hooks.json`
- `$CODEX_HOME/ai-toolkit-hooks/*`

The portable user skill catalog intentionally remains under
`$HOME/.agents/skills/*`. This is Codex's documented shared user-skill discovery
path, not a Codex-owned config-root path. A configured `CODEX_HOME` must be an
existing absolute directory; the installer preserves user guidance, custom
agents, and unrelated hook handlers inside it.

Sources: [Codex environment variables](https://learn.chatgpt.com/codex/config-file/environment-variables),
[AGENTS.md discovery](https://learn.chatgpt.com/codex/agent-configuration/agents-md),
[Codex skills](https://developers.openai.com/codex/skills).

## Global Plugin Outputs

`ai-toolkit plugin install --editor codex <pack>` bootstraps or reuses:

- `$CODEX_HOME/AGENTS.md` (default `~/.codex/AGENTS.md`; pack rules are marker-injected here, not written as unread `.agents/rules/` files)
- `$HOME/.agents/skills/*`
- `$CODEX_HOME/hooks.json`
- `$CODEX_HOME/ai-toolkit-hooks/*`

Plugin packs only add their own runtime-specific layer on top of the generated
Codex base. Codex hooks no longer depend on executable paths under
`~/.softspark/ai-toolkit/`; project assets live beside `.codex/hooks.json`, and
user assets live under `$CODEX_HOME/ai-toolkit-hooks/`.

## Skill Translation Model

Two delivery modes are used for Codex:

| Mode | How it is installed | Use case |
|------|----------------------|----------|
| Native | Symlink to `app/skills/<name>/` | Skills with portable tools, prompts, and paths |
| Adapted | Generated wrapper directory in `.agents/skills/<name>/` | Skills with Claude-only tools, prompt placeholders, path variables, or orchestration APIs |

Adapted skills keep the same support assets (`reference/`, `scripts/`, `assets/`)
via symlinks, but rewrite `SKILL.md` to Codex-native guidance.

## Claude-to-Codex Semantic Mapping

The adapter deliberately avoids embedding runtime function names or guessed
signatures. Generated guidance describes stable intent:

| Claude-oriented concept | Codex guidance |
|-------------------------|----------------|
| Delegated agent call | Delegate a narrow task to a suitable Codex-native subagent |
| Agent redirection | Use the subagent controls available in the current client |
| Task bookkeeping | Use the planning mechanism available in the current client or an explicit checklist |
| Waiting for a task | Wait only when the next critical-path step depends on the delegated result |
| Agent teams | Coordinate subagents with explicit, non-overlapping ownership |
| Prompt input placeholder | Use the task details supplied by the user |
| Claude skill-directory variable | Use the installed skill directory containing `SKILL.md` |

## Adapted Skill Classes

The adapted group includes multi-agent orchestration:

- `/orchestrate`
- `/workflow`
- `/swarm`
- `/subagent-development`

It also includes any skill that contains Claude-only prompt or path variables,
even when its tool list is otherwise portable. Examples include:

- `/tdd`
- `/write-a-prd`
- `/qa-session`
- `/triage-issue`
- `/architecture-audit`
- `/build`
- `/cve-scan`

## Hook Compatibility

Codex does not expose the full Claude hook event surface. Codex's
`HookEventName` enum defines 10 events; the Codex hook generator wires 9 of
them:

- `SessionStart`
- `PreToolUse`
- `PostToolUse`
- `PermissionRequest`
- `UserPromptSubmit`
- `SubagentStart`
- `SubagentStop`
- `PreCompact`
- `Stop`

`PostCompact` is the one enum event left unwired (its only hook was the removed
environment-snapshot probe). Claude-only events such as `TaskCompleted`,
`TeammateIdle`, `SessionEnd`, and `Notification` have no Codex equivalent and
are not available in `.codex/hooks.json`. Handler types: only `command` runs;
`prompt` and `agent` are parsed by Codex but not yet executed.

The generator merges these Codex-compatible events into project or user
`hooks.json`, preserving unrelated user handlers and replacing only commands
marked as ai-toolkit-owned. Project commands resolve their assets from the git
root; core user commands use `$CODEX_HOME/ai-toolkit-hooks/`.

Hook JSON is parsed from the snapshot held by the same secure transaction that
writes generated handlers, installs executable assets, and removes stale
managed assets. A failure in any of those stages rolls back the whole upgrade.
Existing file permissions are retained; new `hooks.json` files use a secure
`0600` base filtered by umask, while new executable hook assets are explicitly
installed as `0755`.

After installation or any hook change, open `/hooks` in Codex and review/trust
the exact definitions. Project hooks additionally require a trusted `.codex`
project layer. The installer never bypasses hook trust.

Generated Codex hook commands include `AI_TOOLKIT_HOOK_QUIET=1`. Native
`SessionStart`, `PreCompact`, and MCP-health adapters use Codex instruction and
config terminology (`AGENTS.md`, `.codex/config.toml`) instead of Claude-only
paths. The generated
`UserPromptSubmit` governance hook does not set `AI_TOOLKIT_HOOK_FORMAT=json`
by default because Codex currently renders `additionalContext` as visible hook
context in the TUI. This keeps prompt-submit output quiet while preserving hook
side effects and blocking decisions such as search-first Stop enforcement.

Codex hooks must not force Claude-only JSON output fields such as
`suppressOutput`. In particular, advisory `PostToolUse` hooks like
`loop-guard.sh` run in quiet/plain mode under Codex; they keep side effects but
do not emit hidden Claude-style context unless a future Codex runtime explicitly
supports that schema.

If a future Codex runtime enables JSON context output for `UserPromptSubmit`,
the output must be event-specific and include the event name alongside the
context:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "..."
  }
}
```

Older `{"hookSpecificOutput":{"additionalContext":"..."}}` output can be valid
JSON but fail newer Codex event-output validation.

Plain-text informational hook context is also silent by default in the shared
hook helper. Set `AI_TOOLKIT_HOOK_VERBOSE=1` only when debugging hook output
outside the Codex UI.

## MCP Configuration

Codex MCP servers are supported at both documented scopes:

- project: `.codex/config.toml` (trusted project layers only)
- user: `$CODEX_HOME/config.toml` (default `~/.codex/config.toml`)

The adapter renders `[mcp_servers.<name>]` for STDIO and Streamable HTTP
transports. It validates documented transport, timeout, tool-filter, and
approval fields, preserves unrelated TOML bytes/comments, and owns only its
marker-bounded block. Invalid TOML and symlinked roots are rejected unchanged.

## Behavioral Limits

Codex wrappers preserve workflow intent, but not every Claude runtime behavior
has a perfect one-to-one equivalent.

Known limits:

- No native Codex equivalent of tmux-backed Agent Teams lifecycle events
- No separate task object model equivalent to Claude `Task*` APIs
- Hook event coverage is narrower than Claude Code
- MCP search tool calls may not fire the shared `PostToolUse` search tracker,
  so `stop-search-check.sh` also checks `$CODEX_HOME/log/codex-tui.log` (default
  `~/.codex/log/codex-tui.log`) for
  `smart_query`, `hybrid_search_kb`, `crag_search`, `multi_hop_search`, and
  `verify_answer` calls after the search-first flag timestamp before blocking.
  The scan is bounded to a recent log window, but sized to tolerate noisy Codex
  skill-loader output between the search call and the Stop hook.

These are runtime platform limits, not installation defects.

## Verification

The Codex compatibility path is verified by:

1. Generator contract tests for `generate_codex.py`
2. Local install tests for `.agents/skills/` and `.codex/hooks.json`
3. Plugin install tests for global Codex rules, hooks, and cleanup paths
4. CLI tests for `codex-md` and `codex-hooks`

## Related

- `kb/reference/skills-catalog.md`
- `kb/reference/architecture-overview.md`
- `kb/reference/global-install-model.md`
