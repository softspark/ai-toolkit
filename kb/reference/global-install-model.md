---
title: "Global Install Model"
category: reference
service: ai-toolkit
tags: [install, global, claude, local-setup]
version: "1.0.0"
created: "2026-03-26"
last_updated: "2026-03-28"
description: "Reference description of the global install target, local project setup, and command responsibilities in ai-toolkit."
---

# Global Install Model

## Summary

`ai-toolkit` installs globally into `~/.claude/` by default.

That means one machine-level install provides agents, skills, hooks, and rules to every project without committing toolkit boilerplate into each repository.

## Command Responsibilities

| Command | Target | Purpose |
|---------|--------|---------|
| `ai-toolkit install` | `~/.claude/` | first-time machine setup |
| `ai-toolkit update` | `~/.claude/` | re-apply after package or rule changes |
| `ai-toolkit install --local` | current project | create local `CLAUDE.md`, `.claude/settings.local.json`, and inject constitution + Copilot + Cline + Roo Code + Aider configs. Installs git hooks fallback. |
| `ai-toolkit update --local` | current project | refresh those local project files |
| `ai-toolkit add-rule` | `~/.ai-toolkit/rules/` | register a global rule |
| `ai-toolkit remove-rule` | `~/.ai-toolkit/rules/` | unregister a global rule |

## Why global install is the default

- less setup friction,
- no repeated per-project install step,
- easier machine-level upgrades,
- correct alignment with Claude Code user-level paths.

## What remains project-local

These files still stay local to a repository:
- `CLAUDE.md`
- `.claude/settings.local.json`
- `.claude/constitution.md`
- `.github/copilot-instructions.md`
- `.clinerules`
- `.roomodes`
- `.aider.conf.yml`
- `.git/hooks/pre-commit` (fallback)
- project-specific documentation or safety overlays

Hooks do **not** live in project-local settings. They are merged only into global `~/.claude/settings.json`.

## Related Documents

- `kb/reference/distribution-model.md`
- `kb/reference/merge-friendly-install-model.md`
