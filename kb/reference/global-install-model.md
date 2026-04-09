---
title: "Global Install Model"
category: reference
service: ai-toolkit
tags: [install, global, claude, local-setup]
version: "1.4.2"
created: "2026-03-26"
last_updated: "2026-04-09"
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
| `ai-toolkit install --local` | current project | Claude Code configs only (CLAUDE.md, settings, constitution, language rules). Add `--editors all` for other tools, or `--editors cursor,aider` for specific ones. Auto-detects editors from existing project files when `--editors` is omitted. |
| `ai-toolkit install --local --lang <lang>` | current project | explicit language selection for rules (e.g. `--lang typescript`, `--lang go,python`); auto-detected when omitted |
| `ai-toolkit install --modules <list>` | `~/.claude/` | selective module install (e.g. `--modules core,agents,rules-typescript`) |
| `ai-toolkit update --local` | current project | refresh project configs; auto-detects editors from existing files |
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
- `.augment/rules/ai-toolkit-*.md`
- `.agent/rules/*.md` and `.agent/workflows/*.md` (Google Antigravity)
- `.git/hooks/pre-commit` (fallback)
- project-specific documentation or safety overlays

Hooks do **not** live in project-local settings. They are merged only into global `~/.claude/settings.json`.

## Related Documents

- `kb/reference/distribution-model.md`
- `kb/reference/merge-friendly-install-model.md`
