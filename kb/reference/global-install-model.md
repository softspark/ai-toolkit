---
title: "Global Install Model"
category: reference
service: ai-toolkit
tags: [install, global, claude, codex, plugins, local-setup]
version: "3.3.1"
created: "2026-03-26"
last_updated: "2026-07-15"
description: "Reference description of Claude Code global install, Claude app plugin export, project-local editor setup, global Codex plugin layering, and command responsibilities in ai-toolkit."
---

# Global Install Model

## Summary

`ai-toolkit` installs globally into `~/.claude/` by default.

That means one machine-level install provides agents, skills, hooks, constitution, and rule files to every project without committing toolkit boilerplate into each repository.

Other editor targets are opt-in and only use documented file surfaces. Cursor
rules stay project-local because Cursor's global user rules are managed through
the settings UI, not a stable merge-safe file. Codex supports both project and
user installs: project files stay in the repository, while user files use the
active `CODEX_HOME` (default `~/.codex`) and shared user skills use
`$HOME/.agents/skills/`. Experimental plugin packs can add a layer to the same
Codex user surface.

Claude Chat/Desktop/Cowork is a separate runtime. It does not read the
filesystem surfaces under `~/.claude`; it receives ai-toolkit through an
uploaded plugin plus app-managed global/folder instructions.

## Command Responsibilities

| Command | Target | Purpose |
|---------|--------|---------|
| `ai-toolkit install` | `~/.claude/` | first-time machine setup |
| `ai-toolkit update` | `~/.claude/` | re-apply after package or rule changes |
| `ai-toolkit install --local` | current project | Claude Code configs only (CLAUDE.md, settings, constitution, language rules). Add `--editors all` for other tools, or `--editors cursor,aider` for specific ones. Auto-detects editors from existing project files when `--editors` is omitted. |
| `ai-toolkit install --local --lang <lang>` | current project | explicit language selection for rules (e.g. `--lang typescript`, `--lang go,python`); auto-detected when omitted |
| `ai-toolkit install --modules <list>` | `~/.claude/` | selective module install (e.g. `--modules core,agents,rules-typescript`) |
| `ai-toolkit update --local` | current project | refresh project configs; auto-detects editors from existing files |
| `ai-toolkit claude-app export` | ZIP + Markdown output | build the uploadable Claude Chat/Cowork plugin and Cowork global instructions; registered rules are included unless `--no-custom-rules` is set |
| `ai-toolkit add-rule` | `~/.softspark/ai-toolkit/rules/` | register a global rule |
| `ai-toolkit remove-rule` | `~/.softspark/ai-toolkit/rules/` | unregister a global rule |
| `ai-toolkit mcp add <name...>` | current project | merge MCP templates into `.mcp.json` |
| `ai-toolkit mcp install --editor <name...>` | editor-native config | render MCP templates into editor-specific config files |
| `ai-toolkit plugin install --editor claude|codex|all <name>` | runtime-native config | install plugin pack for selected runtime(s) |
| `ai-toolkit plugin update --editor claude|codex|all <name>` | runtime-native config | re-apply plugin pack after toolkit updates |
| `ai-toolkit plugin remove --editor claude|codex|all <name>` | runtime-native config | remove plugin pack from selected runtime(s) |

## Install Profiles (v3.0.0)

The `--profile` flag controls how much of each editor's native surface is activated.

| Profile | What runs | Use when |
|---------|-----------|----------|
| `minimal` | Smallest editor surface. Copilot still receives its root instructions, native agents, and self-contained skills; Codex still receives instructions, agents, skills, and native safety hooks. | You want the smallest supported footprint. |
| `standard` (default) | Claude Code + editor rule files. Includes Gemini hooks and native Copilot instructions, agents, portable skills, and hooks. | Day-to-day installs. Most users. |
| `strict` | Everything in `standard` plus git-hook wiring for commit-time safety checks. | Solo dev or tight team with zero tolerance for drift. |
| `full` | Every native surface across every editor: hooks, sub-agents, custom commands, skill pointers for Cursor / Windsurf / Gemini / Augment / Antigravity. | You want maximum coverage and understand that each editor will carry generated files under its own layout. |

Codex installs materialize the full skill catalog under `.agents/skills/`
regardless of profile. The legacy `--codex-skills` flag only requests an
explicit second refresh of that same mirror and is no longer required.

## Global Editor Targets

Claude Code's default global install writes these managed surfaces:

- `~/.claude/agents/*.md` — per-file symlinks to toolkit agents.
- `~/.claude/skills/*/` — per-directory symlinks to toolkit skills.
- `~/.claude/settings.json` — merged hook configuration and global settings.
- `~/.claude/constitution.md` — marker-injected safety constitution.
- `~/.claude/ARCHITECTURE.md` — marker-injected architecture reference.
- `~/.claude/rules/ai-toolkit-*.md` — toolkit rules from `app/rules/*.md`.
- `~/.claude/rules/ai-toolkit-registered-*.md` — rules registered with `ai-toolkit add-rule`.
- `~/.claude/CLAUDE.md` — compact index pointing at the managed rule files.

The `ai-toolkit-*` prefix in `~/.claude/rules/` is reserved for installer-managed files. User-authored Claude rules should use another filename prefix, or be registered through `ai-toolkit add-rule` so they are emitted as `ai-toolkit-registered-*.md`.

## Claude App Target

`~/.claude/` is a Claude Code surface, not a Claude Chat/Cowork surface. Run:

```bash
ai-toolkit claude-app export --verify
```

Upload the ZIP from `Customize > Plugins`, then paste the sibling
`*-global-instructions.md` file into `Settings > Cowork > Global instructions`.
The plugin contains the normal skills and agents, app-relative Cowork hooks,
and an `ai-toolkit-rules` skill generated from common/standalone rules.
Registered rules are embedded in a separate skill by default. Skills work in
Chat and Cowork; hooks and sub-agents are Cowork-only. The app owns its plugin
store, so toolkit updates require re-export and re-upload.

`ai-toolkit install --editors <name>` can write global files only for editors
with documented, file-based config surfaces:

- `windsurf`: `~/.codeium/windsurf/memories/global_rules.md` plus `~/.codeium/windsurf/skills/ai-toolkit-skill-catalogue/SKILL.md` plus `~/.config/devin/AGENTS.md` (Devin CLI global rules — the Desktop `global_rules.md` path is not imported by `read_config_from.windsurf`)
- `gemini`: `~/.gemini/GEMINI.md`; hooks at `~/.gemini/settings.json` (profile ≥ standard); `~/.gemini/commands/` and `~/.gemini/skills/` pointer (profile full)
- `augment`: `~/.augment/rules/ai-toolkit.md`; `~/.augment/agents/`, `~/.augment/commands/`, and hooks in `~/.augment/settings.json` (profile full)
- `cline`: `~/Documents/Cline/Rules/ai-toolkit-*.md` plus `~/.cline/skills/ai-toolkit-skill-catalogue/SKILL.md`
- `roo`: `~/.roo/rules/ai-toolkit-*.md` plus `~/.agents/skills/*` (Roo/Zoo native skill discovery; skipped when `codex` is also selected, which fills the same dir)
- `aider`: `~/.aider.conf.yml` plus `~/.aider-ai-toolkit-CONVENTIONS.md` when the YAML file does not already exist
- `codex`: `$CODEX_HOME/AGENTS.md`, `$CODEX_HOME/agents/*.toml`, `$CODEX_HOME/hooks.json`, `$CODEX_HOME/ai-toolkit-hooks/*`, plus `$HOME/.agents/skills/*`; `CODEX_HOME` defaults to `~/.codex`, and `~/AGENTS.md` is not Codex's user-instruction file
- `opencode`: `~/.config/opencode/*`

Cursor, GitHub Copilot, and Google Antigravity now have partial global support,
scoped to whatever documented HOME file surface each exposes:

- `cursor`: `~/.cursor/hooks.json` (safety/quality hooks; profile ≥ standard). Cursor RULES stay project-local — their only global surface is the Settings UI.
- `copilot`: instructions, native agents, portable skills, and native hooks under `$COPILOT_HOME` when set or `~/.copilot` otherwise. The hook config is `hooks/ai-toolkit.json`; its self-contained runtime is `hooks/ai-toolkit/copilot_hook.py`. VS Code and GitHub.com still use repo `.github/` files, which local install emits.
- `antigravity`: skill pointer at `~/.gemini/config/skills/` and `~/.gemini/antigravity-cli/skills/`. Antigravity RULES stay project-local.

Their global MCP support, where available, is handled by `ai-toolkit mcp
install`, not by the rule installer.

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
- `.roo/mcp.json`
- `.github/mcp.json`
- `.claude/constitution.md`
- project `AGENTS.md`
- project `.agents/rules/*.md`
- project `.agents/skills/*`
- project `.codex/hooks.json`
- project `.codex/hooks/*`
- project `.codex/agents/*.toml`
- project `.codex/config.toml` when Codex MCP servers are selected
- `.github/copilot-instructions.md`
- `.github/instructions/ai-toolkit-*.instructions.md`
- `.github/prompts/ai-toolkit-*.prompt.md`
- `.github/agents/ai-toolkit-*.agent.md`
- `.github/skills/ai-toolkit-*/SKILL.md` plus required assets and helper scripts
- `.github/hooks/ai-toolkit.json` plus `.github/hooks/ai-toolkit/copilot_hook.py` (profile ≥ `standard`)
- `.clinerules`
- `.roomodes`
- `.aider.conf.yml`
- `.augment/rules/ai-toolkit-*.md`
- `.agents/rules/*.md` and `.agents/workflows/*.md` (Google Antigravity; singular `.agent/` still read as fallback)
- `.git/hooks/pre-commit` (fallback)
- project-specific documentation or safety overlays

Project-local Claude Code language rules live in `.claude/rules/ai-toolkit-*.md` with `paths` frontmatter. They are separate from the global user-level `~/.claude/rules/ai-toolkit-*.md` files above.

Claude Code hooks do **not** live in project-local settings. They are merged only into global `~/.claude/settings.json`. Editor-native generators may emit project-local hook files when that editor documents them; Copilot uses `.github/hooks/*.json` and Codex uses `.codex/hooks.json`.

## Copilot Install Behavior

`ai-toolkit install --local --editors copilot` always emits root `AGENTS.md`,
`.github/copilot-instructions.md`, native `.github/agents`, and portable,
self-contained `.github/skills`. Profiles `standard`, `strict`, and `full`
add scoped `.github/instructions`, `.github/prompts`, and native version-1
`.github/hooks`. Profile `minimal` omits those three additional directories.
When an existing project moves from `standard`, `strict`, or `full` to
`minimal`, the installer removes only marked or byte-exact historical ai-toolkit
instructions, prompts, and hooks. Unmanaged project files remain in place.

Global install emits personal instructions, scoped instructions, agents, and
skills under the active Copilot config root; profile `standard` and above adds
hooks. Personal prompt files are not a documented Copilot CLI user surface and
are not generated. `COPILOT_HOME` replaces `~/.copilot` for every generated
Copilot surface, including `mcp-config.json`. Existing user files and user-added
skill assets are preserved; reserved managed-path collisions and symlinked
config roots are rejected instead of overwritten.

Codex hook bundles are self-contained. Project `.codex/hooks.json` commands
reference executable assets in `.codex/hooks/`; user `$CODEX_HOME/hooks.json`
commands reference `$CODEX_HOME/ai-toolkit-hooks/`. Neither bundle depends on
Claude's shared `~/.softspark/ai-toolkit/hooks/` installation.

## Codex Local Install Behavior

`ai-toolkit install --local --editors codex` creates:

- `AGENTS.md`
- `.agents/skills/*`
- `.codex/hooks.json`
- `.codex/hooks/*`
- `.codex/agents/*.toml`
- `.codex/config.toml` when project MCP servers are selected

Native Codex-compatible skills are linked directly. Claude-oriented skills that
depend on `Agent`, `Team*`, or `Task*` primitives are translated into generated
Codex wrappers so the project still receives the full skill catalog.

## Codex Global Plugin Layer

`ai-toolkit plugin install --editor codex <pack>` additionally targets:

- `$CODEX_HOME/AGENTS.md` (pack rules are marker-injected here)
- `$HOME/.agents/skills/*`
- `$CODEX_HOME/hooks.json`
- `$CODEX_HOME/ai-toolkit-hooks/plugin-<pack>-*`

This is an explicit, opt-in layer on top of the normal Codex user install.
Runtime state is tracked in
`~/.softspark/ai-toolkit/plugins.json` per target (`claude`, `codex`).

## MCP Local Sync Behavior

If `.mcp.json` exists in the current project, `ai-toolkit install --local` mirrors its `mcpServers` block into:
- `.claude/settings.local.json`
- `.cursor/mcp.json` when `--editors cursor` is selected
- `.github/mcp.json` when `--editors copilot` is selected
- `.roo/mcp.json` when `--editors roo` is selected
- `.codex/config.toml` when `--editors codex` is selected

Global-only editor MCP configs are not written during `install --local`. Use `ai-toolkit mcp install --editor <name...>` for those targets.

## Related Documents

- `kb/reference/distribution-model.md`
- `kb/reference/merge-friendly-install-model.md`
- `kb/reference/codex-cli-compatibility.md`
- `kb/reference/mcp-editor-compatibility.md`
