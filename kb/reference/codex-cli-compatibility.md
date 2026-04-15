---
title: "AI Toolkit - Codex CLI Compatibility"
category: reference
service: ai-toolkit
tags: [codex, compatibility, install, skills, hooks]
version: "1.0.0"
created: "2026-04-12"
last_updated: "2026-04-13"
description: "Reference for how ai-toolkit maps Claude-oriented skills, hooks, and plugin packs to Codex CLI."
---

# AI Toolkit - Codex CLI Compatibility

## Summary

Codex CLI now receives the full `ai-toolkit` skill catalog during local install.

Native Codex-compatible skills are linked directly into `.agents/skills/`. Skills
that depend on Claude-only orchestration primitives are generated as Codex
wrappers that preserve the original workflow intent while translating execution
to Codex subagents and plan tracking.

Experimental plugin packs can also target a global Codex surface with
`ai-toolkit plugin install --editor codex`, which layers plugin-specific skills,
rules, and hooks into `HOME` without changing the project-local core install
model.

## Local Install Outputs

`ai-toolkit install --local --editors codex` generates:

- `AGENTS.md`
- `.agents/rules/*.md`
- `.agents/skills/*`
- `.codex/hooks.json`

## Global Plugin Outputs

`ai-toolkit plugin install --editor codex <pack>` bootstraps or reuses:

- `~/AGENTS.md`
- `~/.agents/rules/*.md`
- `~/.agents/skills/*`
- `~/.codex/hooks.json`

Plugin packs only add their own runtime-specific layer on top of the generated
Codex base. Shared hook scripts and plugin scripts still live in
`~/.softspark/ai-toolkit/`.

## Skill Translation Model

Two delivery modes are used for Codex:

| Mode | How it is installed | Use case |
|------|----------------------|----------|
| Native | Symlink to `app/skills/<name>/` | Skills whose `allowed-tools` are already supported in Codex |
| Adapted | Generated wrapper directory in `.agents/skills/<name>/` | Skills that rely on Claude-only `Agent`, `Team*`, or `Task*` primitives |

Adapted skills keep the same support assets (`reference/`, `scripts/`, `assets/`)
via symlinks, but rewrite `SKILL.md` to Codex-native guidance.

## Claude-to-Codex Tool Mapping

The adapter rewrites Claude-specific delegation guidance to the closest Codex
runtime primitives:

| Claude-oriented primitive | Codex replacement |
|---------------------------|------------------|
| `Agent(...)` | `spawn_agent(..., fork_context=True, ...)` |
| `SendMessage` | `send_input` |
| `TaskCreate` / `TaskList` / `TaskUpdate` | `update_plan` or explicit checklist tracking |
| `TaskGet` / `TaskOutput` | `wait_agent` |
| `TaskStop` / `TeamDelete` | `close_agent` |
| Agent teams | Multiple spawned subagents with explicit file ownership |

## Adapted Skill Classes

The main adapted group is multi-agent orchestration:

- `/orchestrate`
- `/workflow`
- `/swarm`
- `/teams`
- `/subagent-development`

The adapter also covers skills that previously depended only on Claude's
`Agent` primitive, such as:

- `/tdd`
- `/write-a-prd`
- `/qa-session`
- `/triage-issue`
- `/architecture-audit`

## Hook Compatibility

Codex does not expose the full Claude hook event surface. The Codex hook
generator emits only the events supported by Codex runtime integration:

- `SessionStart`
- `PreToolUse`
- `PostToolUse`
- `UserPromptSubmit`
- `Stop`

This means Claude-only events such as `TaskCompleted`, `TeammateIdle`,
`SubagentStart`, `SubagentStop`, `PreCompact`, `SessionEnd`, and
`Notification` are not available in `.codex/hooks.json`.

`inject-hook` automatically propagates Codex-compatible events to
`~/.codex/hooks.json` (global layer). Non-Codex events are silently skipped.
`remove-hook` cleans both Claude and Codex targets.

## Behavioral Limits

Codex wrappers preserve workflow intent, but not every Claude runtime behavior
has a perfect one-to-one equivalent.

Known limits:

- No native Codex equivalent of tmux-backed Agent Teams lifecycle events
- No separate task object model equivalent to Claude `Task*` APIs
- Hook event coverage is narrower than Claude Code

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
