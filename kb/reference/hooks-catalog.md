---
title: "Hooks Catalog"
category: reference
service: ai-toolkit
tags: [hooks, quality, safety, enforcement, settings.json]
version: "1.5.2"
created: "2026-03-27"
last_updated: "2026-05-21"
description: "Complete reference of all ai-toolkit hooks: events, scripts, installation, and runtime behavior."
---

# Hooks Catalog

## Overview

ai-toolkit provides 28 global hook entries across 14 lifecycle events that enforce quality, safety, and workflow rules across all Claude Code sessions. Hooks are merged into `~/.claude/settings.json` on install, with logic in standalone scripts at `~/.softspark/ai-toolkit/hooks/`.

## Supported Surface

`scripts/validate.py` validates both event names and handler shapes before release. The accepted lifecycle surface includes `PostToolUseFailure`, `PostToolBatch`, and `UserPromptExpansion` in addition to the installed ai-toolkit events below.

Supported handler types are `command`, `http`, `prompt`, `agent`, and `mcp_tool`. ai-toolkit ships command hooks by default; non-command handlers are validated so external consumers can safely inject richer hook definitions through `inject-hook`.

## Installation

```bash
ai-toolkit install    # copies scripts to ~/.softspark/ai-toolkit/hooks/, merges into settings.json
ai-toolkit update     # re-copies scripts, re-merges (idempotent)
```

**File locations:**
- Scripts: `~/.softspark/ai-toolkit/hooks/*.sh`
- Config: `~/.claude/settings.json` → `hooks` key
- Source: `ai-toolkit/app/hooks/*.sh` + `app/hooks.json`

## Hook Events

### SessionStart — `session-start.sh`

| Field | Value |
|-------|-------|
| Event | `SessionStart` |
| Matcher | `startup\|compact` |
| Script | `~/.softspark/ai-toolkit/hooks/session-start.sh` |
| Fires | Session start + after context compaction |

**Actions:**
1. Injects MANDATORY reminder to follow CLAUDE.md rules
2. Injects REMINDER about tests and documentation
3. Loads session context from `.claude/session-context.md` (if exists)
4. Loads active instincts from `.claude/instincts/*.md` (if any)

When `AI_TOOLKIT_HOOK_QUIET=1`, the hook still performs session-state reset,
stale search-flag cleanup, and update notification side effects, but suppresses
all informational stdout so runtimes such as Codex do not show startup hook
context in the UI.

### Notification — `notify-waiting.sh`

| Field | Value |
|-------|-------|
| Event | `Notification` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/notify-waiting.sh` |
| Fires | Claude Code waiting for user input |

**Action:** Cross-platform desktop notification ("Claude Code needs your attention"):
- macOS: `osascript` (native)
- Linux: `notify-send` (libnotify)
- Windows/WSL: `powershell.exe` WScript popup (5s auto-close)

### PreToolUse (Bash) — `guard-destructive.sh`

| Field | Value |
|-------|-------|
| Event | `PreToolUse` |
| Matcher | `Bash` |
| Script | `~/.softspark/ai-toolkit/hooks/guard-destructive.sh` |
| Fires | Before any Bash command |

**Action:** Blocks (exit 2) commands matching destructive patterns:
- `rm -rf`, `sudo rm`
- `DROP TABLE`, `DROP DATABASE`, `TRUNCATE`
- `format /`, `dd if=`
- `git push --force`
- `chmod -R 777`

### PreToolUse (file ops) — `guard-path.sh`

| Field | Value |
|-------|-------|
| Event | `PreToolUse` |
| Matcher | `Bash\|Read\|Edit\|Write\|MultiEdit\|Glob\|Grep\|NotebookEdit\|mcp__filesystem__.*` |
| Script | `~/.softspark/ai-toolkit/hooks/guard-path.sh` |
| Fires | Before any file access tool (including Bash, MCP filesystem) |

**Action:** Blocks (exit 2) when a path contains `/Users/<wrong>` or `/home/<wrong>` that doesn't match the actual `$HOME`. Prevents Claude from hallucinating or confusing similar usernames (common with non-ASCII names like Polish names).

**Feedback to Claude:** Tells it to use `~`, `$HOME`, or run `echo $HOME` instead of guessing.

### UserPromptSubmit — `user-prompt-submit.sh`

| Field | Value |
|-------|-------|
| Event | `UserPromptSubmit` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/user-prompt-submit.sh` |
| Fires | Before Claude starts working on a submitted prompt |

**Action:** Adds a lightweight governance reminder: plan mode for architectural work, evidence-first debugging, KB-first research, and validation expectations.

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`. The bundled `app/hooks.json`
registers this command with `AI_TOOLKIT_HOOK_QUIET=1`, so it still arms or
clears the per-session search-first flag but suppresses the informational
reminder output.

### UserPromptSubmit (usage tracking) — `track-usage.sh`

| Field | Value |
|-------|-------|
| Event | `UserPromptSubmit` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/track-usage.sh` |
| Fires | Before Claude starts working on a submitted prompt |

**Action:** Records skill invocations (slash commands like `/commit`, `/review`) to `~/.softspark/ai-toolkit/stats.json` for local usage analytics. Non-slash prompts are ignored.

### PostToolUse (edit feedback) — `post-tool-use.sh`

| Field | Value |
|-------|-------|
| Event | `PostToolUse` |
| Matcher | `Edit\|MultiEdit\|Write` |
| Script | `~/.softspark/ai-toolkit/hooks/post-tool-use.sh` |
| Fires | After file edit/write tool operations |

**Action:** Adds a lightweight reminder to run relevant validation, tests, and documentation updates after edits.

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### Stop (quality check) — `quality-check.sh`

| Field | Value |
|-------|-------|
| Event | `Stop` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/quality-check.sh` |
| Fires | After every Claude response |

**Action:** Runs language-appropriate linter:
- Python: `ruff check .`
- TypeScript: `npx tsc --noEmit`
- PHP: `vendor/bin/phpstan analyse`
- Dart: `dart analyze`
- Go: `go vet ./...`

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### Stop (session save) — `save-session.sh`

| Field | Value |
|-------|-------|
| Event | `Stop` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/save-session.sh` |
| Fires | After every Claude response |

**Action:** Writes enriched session context to `.claude/session-context.md` for cross-session persistence. Captures:
- Session ID and last assistant message (first 5 lines)
- Git branch, uncommitted change count, and diff stat (last 5 lines)
- Agent-written checkpoints from `.claude/session-context.md.checkpoints` (if present — written by proactive checkpointing per Constitution Art. I §5)

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### Stop (quality gate) — `quality-gate.sh`

| Field | Value |
|-------|-------|
| Event | `Stop` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/quality-gate.sh` |
| Fires | Before Claude is allowed to finish a response |

**Action:** Runs lint/typecheck. **Blocks stopping (exit 2)** if errors found, so Claude must continue and fix the issues. Missing local tooling is reported as skipped rather than blocking the session.

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### TaskCompleted — `quality-gate.sh`

| Field | Value |
|-------|-------|
| Event | `TaskCompleted` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/quality-gate.sh` |
| Fires | When an Agent Teams task is marked complete |

**Action:** Runs lint/typecheck. **Blocks completion (exit 2)** if errors found. Strict profile also runs `mypy --strict`.

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### SubagentStart — `subagent-start.sh`

| Field | Value |
|-------|-------|
| Event | `SubagentStart` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/subagent-start.sh` |
| Fires | When a subagent is spawned |

**Action:** Reminds subagents to stay narrow in scope, gather evidence first, and return explicit validation notes.

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### SubagentStop — `subagent-stop.sh`

| Field | Value |
|-------|-------|
| Event | `SubagentStop` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/subagent-stop.sh` |
| Fires | When a subagent completes |

**Action:** Enforces a concise handoff checklist: findings, files touched, tests run, risks, and docs follow-up.

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### PreCompact — `pre-compact.sh`

| Field | Value |
|-------|-------|
| Event | `PreCompact` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/pre-compact.sh` |
| Fires | Before context compaction |

**Actions (prioritized — higher priority items survive tighter token budgets):**
1. **Mandatory reload reminder** — always emitted, instructs Claude to re-read CLAUDE.md and active tasks
2. **Active instincts** — lists each instinct with confidence score and pattern name from `.claude/instincts/*.md`
3. **Session context** — preserves task state from `.claude/session-context.md` (if exists)
4. **Git working state** — branch name, uncommitted change count, last commit (if inside a git repo)
5. **Key decisions** — last 10 lines from `.claude/decisions.md` (if exists)

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### SessionEnd — `session-end.sh`

| Field | Value |
|-------|-------|
| Event | `SessionEnd` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/session-end.sh` |
| Fires | When a Claude session ends |

**Action:** Writes `.claude/session-end.md` with a lightweight handoff note for the next session and reminds the next session to review preserved context.

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### TeammateIdle — inline

| Field | Value |
|-------|-------|
| Event | `TeammateIdle` |
| Matcher | *(all)* |
| Fires | Agent Teams teammate going idle |

**Action:** Reminds teammate to verify: files modified, tests written, docs updated.

---

## New Hooks (v1.1.0)

### PreToolUse (config guard) — `guard-config.sh`

| Field | Value |
|-------|-------|
| Event | `PreToolUse` |
| Matcher | `Edit\|Write\|MultiEdit` |
| Script | `~/.softspark/ai-toolkit/hooks/guard-config.sh` |
| Fires | Before any file write/edit operation |

**Action:** Blocks (exit 2) edits to linter and formatter config files — `.eslintrc`, `.eslintrc.*`, `eslint.config.*`, `.prettierrc`, `.prettierrc.*`, `prettier.config.*`, `tsconfig.json`, `tsconfig.*.json` — unless the request contains an explicit acknowledgment phrase (e.g. "intentionally editing config"). Returns a human-readable explanation to Claude so it can ask the user for confirmation before retrying.

### SessionStart — `mcp-health.sh`

| Field | Value |
|-------|-------|
| Event | `SessionStart` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/mcp-health.sh` |
| Fires | Session start |

**Action:** Non-blocking (always exits 0). Reads MCP server definitions from `~/.claude/settings.json` and any local `.mcp.json`. For each configured server, checks whether the required runtime command (`npx`, `uvx`, `docker`, etc.) is available in `$PATH`. Emits warnings for any missing runtimes, including install hints (e.g. "npm install -g npx"). Helps surface MCP misconfiguration early without interrupting the session.

### PostToolUse (governance) — `governance-capture.sh`

| Field | Value |
|-------|-------|
| Event | `PostToolUse` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/governance-capture.sh` |
| Fires | After any tool use |

**Action:** Non-blocking (always exits 0). Logs security-sensitive operations (Bash commands, file writes to sensitive paths, large writes) to `~/.softspark/ai-toolkit/governance.log` with ISO timestamp, session ID, tool name, and a content excerpt. Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### PreCompact — `pre-compact-save.sh`

| Field | Value |
|-------|-------|
| Event | `PreCompact` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/pre-compact-save.sh` |
| Fires | Before context compaction |

**Action:** Saves a timestamped context snapshot to `~/.softspark/ai-toolkit/compactions/YYYY-MM-DD_HH-MM-SS.txt`. Captures session ID, working directory, git branch and status, and environment metadata. Provides an audit trail of what was in context at each compaction point. Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### PreToolUse (commit quality) — `commit-quality.sh`

| Field | Value |
|-------|-------|
| Event | `PreToolUse` |
| Matcher | `Bash` |
| Script | `~/.softspark/ai-toolkit/hooks/commit-quality.sh` |
| Fires | Before any Bash command |

**Action:** Non-blocking (always exits 0). Inspects Bash commands containing `git commit`. Extracts the commit message from the `-m` flag and checks it against Conventional Commits format (`type: description`, where type is one of feat/fix/docs/refactor/test/chore/ci/perf/style/revert). Emits an advisory warning if the message does not match — the commit is not blocked, only nudged. Commands without `git commit` or without a `-m` message (e.g. interactive commits) are ignored.

### SessionStart — `session-context.sh`

| Field | Value |
|-------|-------|
| Event | `SessionStart` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/session-context.sh` |
| Fires | Session start |

**Action:** Captures an environment snapshot to `~/.softspark/ai-toolkit/sessions/current-context.json`. Records working directory, git branch, git status summary, Node.js version, Python version, and timestamp. Used by other hooks and tools to access session metadata without re-running discovery commands. Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

---

## New Hooks (Constitution Art. VI Enforcement)

These six hooks turn Constitution Article VI ("Repair Discipline") from prose into executable enforcement. Each one closes a specific gap that previously relied on agent goodwill.

### PreToolUse (revert protection) — `revert-guard.sh`

| Field | Value |
|-------|-------|
| Event | `PreToolUse` |
| Matcher | `Bash` |
| Script | `~/.softspark/ai-toolkit/hooks/revert-guard.sh` |
| Fires | Before any Bash command |

**Action:** Blocks (exit 2) `git checkout/restore -- <file>`, `git reset --hard`, or `git clean -fd` when the affected files were edited in the current session (per `session_state.py` log). Forces the agent to fix root causes instead of reverting work-in-progress (Art. VI.2). Branch switches (`git checkout main`) and reverts on untouched files pass through unchanged.

**Override (one-off):** `CLAUDE_REVERT_OK=1`. Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### PostToolUse (test cohesion) — `test-cohesion.sh`

| Field | Value |
|-------|-------|
| Event | `PostToolUse` |
| Matcher | `Edit\|MultiEdit\|Write` |
| Script | `~/.softspark/ai-toolkit/hooks/test-cohesion.sh` |
| Fires | After every file edit |

**Action:** Runs the test commands mapped to the edited path via `test-cohesion-map.json`. Lookup order: project-local `.claude/test-cohesion-map.json`, then toolkit default `app/hooks/test-cohesion-map.json`. Blocks (exit 2) when the related test command fails. Runs **only** related tests, not the full suite (one of the user-stated requirements).

Map schema:
```json
[
  {
    "match": "src/auth/*.py",
    "tests": ["tests/test_auth.py"],
    "runner": "pytest",
    "command": null
  }
]
```
First-match-wins per file. Built-in runners: `bats`, `pytest`, `vitest`, `jest`. Use `"command"` for full overrides.

**Overrides:** `CLAUDE_SKIP_COHESION=1` (one-off), `CLAUDE_HOOK_BOOTSTRAP=1` (when editing the hook itself). Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### PostToolUse (search-first tracker) — `search-tracker.sh`

| Field | Value |
|-------|-------|
| Event | `PostToolUse` |
| Matcher | `mcp__.*__(smart_query\|hybrid_search_kb\|crag_search\|multi_hop_search\|verify_answer)\|WebSearch\|WebFetch` |
| Script | `~/.softspark/ai-toolkit/hooks/search-tracker.sh` |
| Fires | After any search-style tool call |

**Action:** Clears `~/.softspark/ai-toolkit/state/search-required-<session_id>.flag` (per-session, keyed by `session_id` from the hook stdin payload, falling back to `transcript_path` basename, then `default`). Pairs with `user-prompt-submit.sh` (sets the flag on long technical prompts only when a search provider is detected or strict mode is enabled) and `stop-search-check.sh` (blocks Stop if the calling session's flag is still set). Search provider detection parses actual MCP server names from `mcpServers`, `mcp_servers`, or `mcp` config blocks; hook matchers and permission allowlists do not count as providers. Together the hooks enforce the global CLAUDE.md GOLDEN RULE without breaking offline/no-RAG installs and without cross-session interference when multiple Claude Code windows run in parallel.

Non-blocking (exit 0). Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### Stop (search-first enforcement) — `stop-search-check.sh`

| Field | Value |
|-------|-------|
| Event | `Stop` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/stop-search-check.sh` |
| Fires | When Claude finishes a response |

**Action:** If `search-required-<session_id>.flag` for the calling session is still present (no search tool ran during this turn) and a search provider is still detectable, emits `{"decision":"block","reason":"..."}` to continue the conversation with a search-first reminder. If no RAG/Web provider is detected, it clears the stale flag and exits 0, so offline/no-MCP users are not blocked. On Codex, where MCP search tools may not trigger the shared `PostToolUse` tracker, the hook also checks `~/.codex/log/codex-tui.log` for search tool calls after the flag timestamp before blocking. Flags are scoped by `session_id` from the hook stdin payload so a Stop in session B never consumes session A's flag (and vice versa). Stale per-session flags older than 60 minutes are GC'd on the next `SessionStart`.

**Overrides:** `CLAUDE_SKIP_SEARCH_FIRST=1`, `AI_TOOLKIT_SEARCH_FIRST=off`, or `AI_TOOLKIT_SEARCH_FIRST=strict` to force enforcement. Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### InstructionsLoaded — `instructions-audit.sh`

| Field | Value |
|-------|-------|
| Event | `InstructionsLoaded` |
| Matcher | *(all)* |
| Script | `~/.softspark/ai-toolkit/hooks/instructions-audit.sh` |
| Fires | Whenever CLAUDE.md / `.claude/rules/*.md` is loaded into context |

**Action:** Appends `<ts>\t<memory_type>\t<load_reason>\t<file_path>` to `~/.softspark/ai-toolkit/state/loaded-instructions.log`. Provides audit visibility: when a rule does NOT enter context (silently dropped, token budget, glob miss), the absence is observable. Auto-rotates at 2000 lines.

Non-blocking (exit 0). Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### ConfigChange — `config-desync-guard.sh`

| Field | Value |
|-------|-------|
| Event | `ConfigChange` |
| Matcher | `user_settings` |
| Script | `~/.softspark/ai-toolkit/hooks/config-desync-guard.sh` |
| Fires | When `~/.claude/settings.json` changes |

**Action:** Compares `_source: ai-toolkit` entries between `~/.claude/settings.json` (installed) and the toolkit source `app/hooks.json`. If they diverge (missing/stale entries), emits an advisory to stderr suggesting `ai-toolkit update` or `ai-toolkit doctor --fix`. Non-blocking by design — user's legitimate settings edits never get rejected.

**Override (silence advisory):** `CLAUDE_SKIP_CONFIG_DESYNC=1`. Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### Supporting Infrastructure

| Component | Purpose |
|-----------|---------|
| `scripts/session_state.py` | Append-only edit log keyed by session_id. Cleared on SessionStart. Read by revert-guard, test-cohesion, quality-gate. |
| `scripts/test_cohesion.py` | Resolves changed paths → test commands via cohesion map. First-match-wins. Stdlib-only. |
| `app/hooks/test-cohesion-map.json` | Toolkit-default path → tests mapping (used when no project map exists). |
| `app/hooks/_locate-toolkit.sh` | Shared bash helper that exports `$TOOLKIT_DIR` for hooks needing scripts/. |
| `app/hooks/_hook-io.sh` | Shared bash helper that normalizes hook payloads across Claude, Augment, Gemini, Windsurf, and Cursor-style JSON. Honors `AI_TOOLKIT_HOOK_QUIET=1` for non-blocking context output. |
| `app/hooks/_search-capability.sh` | Shared bash helper that enables search-first blocking only when RAG/Web is configured or strict mode is requested. |

## Runtime Profiles

Set in `.claude/settings.local.json`:

```json
{ "env": { "TOOLKIT_HOOK_PROFILE": "standard" } }
```

| Profile | Behavior |
|---------|----------|
| `minimal` | Only destructive guard + SessionStart |
| `standard` | All hooks (default) |
| `strict` | Standard + mypy --strict on task completion |

Set `AI_TOOLKIT_HOOK_QUIET=1` on hook commands to suppress non-blocking
informational context while preserving side effects and blocking decisions.
Codex-generated hooks use this mode by default, and Claude's bundled
`UserPromptSubmit` entry uses it to avoid visible prompt hook context.

## Architecture

```
~/.softspark/ai-toolkit/
├── rules/          # Registered rules (add-rule.sh)
├── state/          # Per-session runtime state (NEW)
│   ├── session-edits.json         # Append-only edit log per session
│   ├── search-required-<sid>.flag # Per-session: set by user-prompt-submit, cleared by search-tracker/stop-search-check, GC'd at SessionStart (>60min)
│   ├── loaded-instructions.log    # Audit trail of which rules entered context
│   └── test-cohesion-last.log     # Last cohesion test command output
└── hooks/          # Hook scripts (copied on install)
    ├── _profile-check.sh         # Shared: profile skip logic (sourced by hooks)
    ├── _locate-toolkit.sh        # NEW: shared $TOOLKIT_DIR locator
    ├── _hook-io.sh               # NEW: shared multi-editor payload/output adapter
    ├── _search-capability.sh     # NEW: capability-aware search-first enforcement
    ├── session-start.sh
    ├── session-context.sh
    ├── guard-destructive.sh
    ├── guard-path.sh
    ├── guard-config.sh
    ├── revert-guard.sh           # NEW: block revert on session-edited files (Art. VI.2)
    ├── mcp-health.sh
    ├── user-prompt-submit.sh     # extended: arms search-required flag
    ├── post-tool-use.sh          # extended: appends edits to session state
    ├── governance-capture.sh
    ├── test-cohesion.sh          # NEW: runs mapped tests after edits (Art. VI.3)
    ├── test-cohesion-map.json    # NEW: path → tests mapping
    ├── search-tracker.sh         # NEW: clears search-required flag
    ├── quality-check.sh
    ├── quality-gate.sh           # extended: cohesion-tests session edits
    ├── stop-search-check.sh      # NEW: enforces search-first on Stop
    ├── save-session.sh
    ├── subagent-start.sh
    ├── subagent-stop.sh
    ├── track-usage.sh
    ├── pre-compact.sh
    ├── pre-compact-save.sh
    ├── commit-quality.sh
    ├── instructions-audit.sh     # NEW: logs CLAUDE.md / rules loads
    ├── config-desync-guard.sh    # NEW: warns on settings ↔ source drift
    └── session-end.sh

~/.claude/settings.json
└── hooks:          # Hook definitions referencing ~/.softspark/ai-toolkit/hooks/
    ├── SessionStart       → session-start.sh, mcp-health.sh, session-context.sh
    ├── Notification       → notify-waiting.sh
    ├── PreToolUse         → guard-destructive.sh, guard-path.sh, guard-config.sh, commit-quality.sh, revert-guard.sh
    ├── UserPromptSubmit   → user-prompt-submit.sh, track-usage.sh
    ├── PostToolUse        → post-tool-use.sh, governance-capture.sh, test-cohesion.sh, search-tracker.sh
    ├── Stop               → quality-check.sh, save-session.sh, quality-gate.sh, stop-search-check.sh
    ├── TaskCompleted      → quality-gate.sh
    ├── TeammateIdle       → echo (inline)
    ├── SubagentStart      → subagent-start.sh
    ├── SubagentStop       → subagent-stop.sh
    ├── PreCompact         → pre-compact.sh, pre-compact-save.sh
    ├── SessionEnd         → session-end.sh
    ├── InstructionsLoaded → instructions-audit.sh
    └── ConfigChange       → config-desync-guard.sh
```

**Key design decisions:**
- Scripts **copied** (not symlinked) — user can customize without breaking git
- Hooks in `settings.json` (not `hooks.json`) — Claude Code only reads settings files
- `_source: "ai-toolkit"` tag on every entry — allows idempotent merge/strip
- Hooks are **global only** — `--local` does not install hooks into project settings

## Troubleshooting

**Hooks not loading:**
1. Run `/hooks` in Claude Code — lists all active hooks
2. Check `claude --debug hooks` — shows matcher resolution
3. Verify JSON: `python3 -c "import json; json.load(open('$HOME/.claude/settings.json'))"`

**Hook script not found:**
```bash
ls ~/.softspark/ai-toolkit/hooks/     # should list 27 .sh files (plus _profile-check.sh + _locate-toolkit.sh + _hook-io.sh + _search-capability.sh helpers + test-cohesion-map.json)
ai-toolkit update            # re-copies scripts
```

**Legacy cleanup:**
```bash
rm ~/.claude/hooks.json      # old format, no longer used
rm -rf ~/.claude/hooks       # old symlink, no longer used
```
