---
title: "Global Install Model"
category: reference
service: ai-toolkit
tags: [install, global, claude, codex, plugins, local-setup]
version: "1.4.4"
created: "2026-03-26"
last_updated: "2026-04-13"
description: "Reference description of the global install target, project-local editor setup, global Codex plugin layering, and command responsibilities in ai-toolkit."
---

# Global Install Model

## Summary

`ai-toolkit` installs globally into `~/.claude/` by default.

That means one machine-level install provides agents, skills, hooks, and rules to every project without committing toolkit boilerplate into each repository.

Codex remains project-local for the core toolkit install, but experimental
plugin packs can now layer a global Codex target in `HOME` when explicitly
installed with `ai-toolkit plugin install --editor codex`.

## Command Responsibilities

| Command | Target | Purpose |
|---------|--------|---------|
| `ai-toolkit install` | `~/.claude/` | first-time machine setup |
| `ai-toolkit update` | `~/.claude/` | re-apply after package or rule changes |
| `ai-toolkit install --local` | current project | Claude Code configs only (CLAUDE.md, settings, constitution, language rules). Add `--editors all` for other tools, or `--editors cursor,aider` for specific ones. Auto-detects editors from existing project files when `--editors` is omitted. |
| `ai-toolkit install --local --lang <lang>` | current project | explicit language selection for rules (e.g. `--lang typescript`, `--lang go,python`); auto-detected when omitted |
| `ai-toolkit install --modules <list>` | `~/.claude/` | selective module install (e.g. `--modules core,agents,rules-typescript`) |
| `ai-toolkit update --local` | current project | refresh project configs; auto-detects editors from existing files |
| `ai-toolkit add-rule` | `~/.softspark/ai-toolkit/rules/` | register a global rule |
| `ai-toolkit remove-rule` | `~/.softspark/ai-toolkit/rules/` | unregister a global rule |
| `ai-toolkit mcp add <name...>` | current project | merge MCP templates into `.mcp.json` |
| `ai-toolkit mcp install --editor <name...>` | editor-native config | render MCP templates into editor-specific config files |
| `ai-toolkit plugin install --editor claude|codex|all <name>` | runtime-native config | install plugin pack for selected runtime(s) |
| `ai-toolkit plugin update --editor claude|codex|all <name>` | runtime-native config | re-apply plugin pack after toolkit updates |
| `ai-toolkit plugin remove --editor claude|codex|all <name>` | runtime-native config | remove plugin pack from selected runtime(s) |

## Why global install is the default

- less setup friction,
- no repeated per-project install step,
- easier machine-level upgrades,
- correct alignment with Claude Code user-level paths.

## What remains project-local

These files still stay local to a repository as part of the core install model:
- `CLAUDE.md`
- `.claude/settings.local.json`
- `.mcp.json`
- `.cursor/mcp.json`
- `.github/mcp.json`
- `.claude/constitution.md`
- project `AGENTS.md`
- project `.agents/rules/*.md`
- project `.agents/skills/*`
- project `.codex/hooks.json`
- `.github/copilot-instructions.md`
- `.clinerules`
- `.roomodes`
- `.aider.conf.yml`
- `.augment/rules/ai-toolkit-*.md`
- `.agent/rules/*.md` and `.agent/workflows/*.md` (Google Antigravity)
- `.git/hooks/pre-commit` (fallback)
- project-specific documentation or safety overlays

Hooks do **not** live in project-local settings. They are merged only into global `~/.claude/settings.json`.

Codex is the exception in terms of file location, not hook ownership: its local
`.codex/hooks.json` points to hook scripts already installed globally in
`~/.softspark/ai-toolkit/hooks/`.

## Codex Local Install Behavior

`ai-toolkit install --local --editors codex` creates:

- `AGENTS.md`
- `.agents/rules/*.md`
- `.agents/skills/*`
- `.codex/hooks.json`

Native Codex-compatible skills are linked directly. Claude-oriented skills that
depend on `Agent`, `Team*`, or `Task*` primitives are translated into generated
Codex wrappers so the project still receives the full skill catalog.

## Codex Global Plugin Layer

`ai-toolkit plugin install --editor codex <pack>` additionally targets:

- `~/AGENTS.md`
- `~/.agents/rules/*.md`
- `~/.agents/skills/*`
- `~/.codex/hooks.json`

This is not the default core install path. It is an explicit, opt-in plugin
layer used only for plugin packs. Runtime state is tracked in
`~/.softspark/ai-toolkit/plugins.json` per target (`claude`, `codex`).

## MCP Local Sync Behavior

If `.mcp.json` exists in the current project, `ai-toolkit install --local` mirrors its `mcpServers` block into:
- `.claude/settings.local.json`
- `.cursor/mcp.json` when `--editors cursor` is selected
- `.github/mcp.json` when `--editors copilot` is selected

Global-only editor MCP configs are not written during `install --local`. Use `ai-toolkit mcp install --editor <name...>` for those targets.

## Related Documents

- `kb/reference/distribution-model.md`
- `kb/reference/merge-friendly-install-model.md`
- `kb/reference/codex-cli-compatibility.md`
- `kb/reference/mcp-editor-compatibility.md`
