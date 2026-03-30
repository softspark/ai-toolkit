---
title: "Hooks Catalog"
category: reference
service: ai-toolkit
tags: [hooks, quality, safety, enforcement, settings.json]
version: "1.0.0"
created: "2026-03-27"
last_updated: "2026-04-02"
description: "Complete reference of all ai-toolkit hooks: events, scripts, installation, and runtime behavior."
---

# Hooks Catalog

## Overview

ai-toolkit provides 15 global hook entries across 12 lifecycle events that enforce quality, safety, and workflow rules across all Claude Code sessions. Hooks are merged into `~/.claude/settings.json` on install, with logic in standalone scripts at `~/.ai-toolkit/hooks/`.

## Installation

```bash
ai-toolkit install    # copies scripts to ~/.ai-toolkit/hooks/, merges into settings.json
ai-toolkit update     # re-copies scripts, re-merges (idempotent)
```

**File locations:**
- Scripts: `~/.ai-toolkit/hooks/*.sh`
- Config: `~/.claude/settings.json` → `hooks` key
- Source: `ai-toolkit/app/hooks/*.sh` + `app/hooks.json`

## Hook Events

### SessionStart — `session-start.sh`

| Field | Value |
|-------|-------|
| Event | `SessionStart` |
| Matcher | `startup\|compact` |
| Script | `~/.ai-toolkit/hooks/session-start.sh` |
| Fires | Session start + after context compaction |

**Actions:**
1. Injects MANDATORY reminder to follow CLAUDE.md rules
2. Injects REMINDER about tests and documentation
3. Loads session context from `.claude/session-context.md` (if exists)
4. Loads active instincts from `.claude/instincts/*.md` (if any)

### Notification — inline

| Field | Value |
|-------|-------|
| Event | `Notification` |
| Matcher | *(all)* |
| Fires | Claude Code waiting for user input |

**Action:** macOS desktop notification via `osascript`.

### PreToolUse (Bash) — `guard-destructive.sh`

| Field | Value |
|-------|-------|
| Event | `PreToolUse` |
| Matcher | `Bash` |
| Script | `~/.ai-toolkit/hooks/guard-destructive.sh` |
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
| Script | `~/.ai-toolkit/hooks/guard-path.sh` |
| Fires | Before any file access tool (including Bash, MCP filesystem) |

**Action:** Blocks (exit 2) when a path contains `/Users/<wrong>` or `/home/<wrong>` that doesn't match the actual `$HOME`. Prevents Claude from hallucinating or confusing similar usernames (common with non-ASCII names like Polish names).

**Feedback to Claude:** Tells it to use `~`, `$HOME`, or run `echo $HOME` instead of guessing.

### UserPromptSubmit — `user-prompt-submit.sh`

| Field | Value |
|-------|-------|
| Event | `UserPromptSubmit` |
| Matcher | *(all)* |
| Script | `~/.ai-toolkit/hooks/user-prompt-submit.sh` |
| Fires | Before Claude starts working on a submitted prompt |

**Action:** Adds a lightweight governance reminder: plan mode for architectural work, evidence-first debugging, KB-first research, and validation expectations.

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### UserPromptSubmit (usage tracking) — `track-usage.sh`

| Field | Value |
|-------|-------|
| Event | `UserPromptSubmit` |
| Matcher | *(all)* |
| Script | `~/.ai-toolkit/hooks/track-usage.sh` |
| Fires | Before Claude starts working on a submitted prompt |

**Action:** Records skill invocations (slash commands like `/commit`, `/review`) to `~/.ai-toolkit/stats.json` for local usage analytics. Non-slash prompts are ignored.

### PostToolUse (edit feedback) — `post-tool-use.sh`

| Field | Value |
|-------|-------|
| Event | `PostToolUse` |
| Matcher | `Edit\|MultiEdit\|Write` |
| Script | `~/.ai-toolkit/hooks/post-tool-use.sh` |
| Fires | After file edit/write tool operations |

**Action:** Adds a lightweight reminder to run relevant validation, tests, and documentation updates after edits.

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### Stop (quality check) — `quality-check.sh`

| Field | Value |
|-------|-------|
| Event | `Stop` |
| Matcher | *(all)* |
| Script | `~/.ai-toolkit/hooks/quality-check.sh` |
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
| Script | `~/.ai-toolkit/hooks/save-session.sh` |
| Fires | After every Claude response |

**Action:** Writes session context to `.claude/session-context.md` for cross-session persistence.

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### TaskCompleted — `quality-gate.sh`

| Field | Value |
|-------|-------|
| Event | `TaskCompleted` |
| Matcher | *(all)* |
| Script | `~/.ai-toolkit/hooks/quality-gate.sh` |
| Fires | When an Agent Teams task is marked complete |

**Action:** Runs lint/typecheck. **Blocks completion (exit 2)** if errors found. Strict profile also runs `mypy --strict`.

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### SubagentStart — `subagent-start.sh`

| Field | Value |
|-------|-------|
| Event | `SubagentStart` |
| Matcher | *(all)* |
| Script | `~/.ai-toolkit/hooks/subagent-start.sh` |
| Fires | When a subagent is spawned |

**Action:** Reminds subagents to stay narrow in scope, gather evidence first, and return explicit validation notes.

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### SubagentStop — `subagent-stop.sh`

| Field | Value |
|-------|-------|
| Event | `SubagentStop` |
| Matcher | *(all)* |
| Script | `~/.ai-toolkit/hooks/subagent-stop.sh` |
| Fires | When a subagent completes |

**Action:** Enforces a concise handoff checklist: findings, files touched, tests run, risks, and docs follow-up.

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### PreCompact — `pre-compact.sh`

| Field | Value |
|-------|-------|
| Event | `PreCompact` |
| Matcher | *(all)* |
| Script | `~/.ai-toolkit/hooks/pre-compact.sh` |
| Fires | Before context compaction |

**Actions:**
1. Injects reminder to re-read CLAUDE.md files after compaction
2. Preserves session context from `.claude/session-context.md` (if exists)
3. Preserves active instincts from `.claude/instincts/*.md` (if any)

Skipped when `TOOLKIT_HOOK_PROFILE=minimal`.

### SessionEnd — `session-end.sh`

| Field | Value |
|-------|-------|
| Event | `SessionEnd` |
| Matcher | *(all)* |
| Script | `~/.ai-toolkit/hooks/session-end.sh` |
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

## Architecture

```
~/.ai-toolkit/
├── rules/          # Registered rules (add-rule.sh)
└── hooks/          # Hook scripts (copied on install)
    ├── _profile-check.sh    # Shared: profile skip logic (sourced by hooks)
    ├── session-start.sh
    ├── guard-destructive.sh
    ├── guard-path.sh
    ├── user-prompt-submit.sh
    ├── post-tool-use.sh
    ├── quality-check.sh
    ├── quality-gate.sh
    ├── save-session.sh
    ├── subagent-start.sh
    ├── subagent-stop.sh
    ├── track-usage.sh
    ├── pre-compact.sh
    └── session-end.sh

~/.claude/settings.json
└── hooks:          # Hook definitions referencing ~/.ai-toolkit/hooks/
    ├── SessionStart → session-start.sh
    ├── Notification → osascript (inline)
    ├── PreToolUse   → guard-destructive.sh, guard-path.sh
    ├── UserPromptSubmit → user-prompt-submit.sh, track-usage.sh
    ├── PostToolUse  → post-tool-use.sh
    ├── Stop         → quality-check.sh, save-session.sh
    ├── TaskCompleted → quality-gate.sh
    ├── TeammateIdle → echo (inline)
    ├── SubagentStart → subagent-start.sh
    ├── SubagentStop  → subagent-stop.sh
    ├── PreCompact    → pre-compact.sh
    └── SessionEnd    → session-end.sh
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
ls ~/.ai-toolkit/hooks/     # should list 12 .sh files (plus _profile-check.sh helper)
ai-toolkit update            # re-copies scripts
```

**Legacy cleanup:**
```bash
rm ~/.claude/hooks.json      # old format, no longer used
rm -rf ~/.claude/hooks       # old symlink, no longer used
```
