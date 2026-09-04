---
title: "CLI Reference"
category: reference
service: ai-toolkit
tags: [cli, commands, reference, install, update, plugin, mcp, telemetry]
created: "2026-04-13"
last_updated: "2026-09-04"
description: "Complete CLI reference for all ai-toolkit commands, options, and flags."
---

# CLI Reference

```
Usage: ai-toolkit <command> [options]
```

## Core Commands

| Command | Description |
|---------|-------------|
| `install` | First-time global install into `~/.claude/` + Cursor, Windsurf, Gemini |
| `install --language-skills detected\|all` | `detected` (default): turn off `<lang>-rules`/`<lang>-patterns` skills for languages no registered project uses, via `skillOverrides` in `~/.claude/settings.json` (entries are tracked in `state.json` and restored when a project brings the language back; a user's own override is never touched); `all`: keep every language skill on. The choice persists across `install`/`update` |
| `install --local` | Claude Code configs only; add `--editors all` or `--editors cursor,aider` for other tools |
| `update` | Re-apply toolkit after `npm install -g @softspark/ai-toolkit@latest` |
| `update --local` | Re-apply + auto-detect editors from existing project files |
| `reset --local` | Wipe all project-local configs and recreate from scratch (clean slate) |
| `status` | Show installed modules and version |
| `uninstall` | Remove toolkit from `~/.claude/` |
| `validate` | Verify toolkit integrity (`--strict` for CI-grade, warnings = errors) |
| `doctor` | Diagnose install health, hooks, quick-win assets, artifact drift, context budget (est. resident tokens of the skill/agent listings and user rules, plus skills with zero recorded use; read-only, prints the `skillOverrides` key to paste), and permission rules (`permissions.allow` wildcards on interpreters, task runners, package installs, `gh api`, `curl`, `git fetch`, destructive commands; warns only, never edits) |
| `doctor --fix` | Auto-repair broken symlinks, missing hooks, stale artifacts |
| `eject [dir]` | Export standalone config (no symlinks, no toolkit dependency) |
| `claude-app export [--output FILE] [--no-custom-rules] [--verify]` | Build an uploadable Claude Chat/Desktop/Cowork plugin ZIP and global-instructions file |
| `claude-app verify` | Validate a clean staged plugin with structural checks and the official Claude plugin validator |
| `codex-plugin export [--output FILE]` | Build a deterministic native Codex plugin ZIP with skills and self-contained hooks |
| `codex-plugin verify` | Validate a clean native Codex plugin stage without installing it or changing user configuration |

## Rule & Hook Injection

| Command | Description |
|---------|-------------|
| `add-rule <rule.md\|url> [name]` | Register rule in `~/.softspark/ai-toolkit/rules/` — auto-applied on every `update` |
| `remove-rule <name> [dir]` | Unregister rule and remove its block from `CLAUDE.md` |
| `inject-hook <file.json\|url> [name]` | Inject external hooks (file or URL) into settings.json (idempotent, `_source` tagged, URL hooks auto-refresh on update) |
| `remove-hook <name>` | Remove injected hooks by source name (also unregisters URL source if present) |

## MCP Management

| Command | Description |
|---------|-------------|
| `mcp list` | List available MCP server templates (28 templates) |
| `mcp editors` | List editors with native MCP config adapters and scopes |
| `mcp add <name> [names...]` | Add MCP server template(s) to `.mcp.json` |
| `mcp install --editor <name[,..]> [names...]` | Install templates into native editor MCP config |
| `mcp show <name>` | Show MCP template config details |
| `mcp remove <name>` | Remove MCP server from `.mcp.json` or editor MCP config |

## Plugin Management

`plugin ...` manages ai-toolkit's experimental runtime packs. Native Codex
plugin packaging uses the separate `codex-plugin ...` command above.

| Command | Description |
|---------|-------------|
| `plugin list` | Show available plugin packs with install status |
| `plugin install <name> [--editor claude\|codex\|all]` | Install a plugin pack for Claude Code and/or Codex (`claude` means Claude Code, not the Claude app) |
| `plugin install --all [--editor claude\|codex\|all]` | Install all 12 plugin packs |
| `plugin update <name> [--editor claude\|codex\|all]` | Update a plugin pack (remove + reinstall, preserves data) |
| `plugin update --all [--editor claude\|codex\|all]` | Update all installed plugin packs |
| `plugin clean <name> [--days N]` | Prune old plugin data (default: 90 days) |
| `plugin remove <name> [--editor claude\|codex\|all]` | Remove a plugin pack |
| `plugin status [--editor claude\|codex\|all]` | Show installed plugins with runtime-specific details |

### Native Codex plugin package

```bash
ai-toolkit codex-plugin export --output ai-toolkit-codex-plugin.zip
ai-toolkit codex-plugin verify
```

Extract the ZIP to `<marketplace-root>/plugins/ai-toolkit/`, add an entry with
`source.path: ./plugins/ai-toolkit` in
`<marketplace-root>/.agents/plugins/marketplace.json`, then run
`codex plugin marketplace add <marketplace-root>` for that non-default local
marketplace. Open `/plugins` in Codex CLI, install the plugin, review/trust the
bundled hooks, and start a new session. The ZIP includes plugin-local skill
runtime resources, including the skill-audit helper and its Python imports.
Export refuses symlinked output files and ancestors instead of resolving them
to another destination. Codex IDE does not support plugins.

## Config Inheritance

| Command | Description |
|---------|-------------|
| `config validate [path]` | Validate `.softspark-toolkit.json` schema + extends + enforcement |
| `config diff [path]` | Show project vs base config differences |
| `config init [flags]` | Create `.softspark-toolkit.json` (`--extends`, `--profile`, `--no-extends`) |
| `config create-base <name>` | Scaffold base config npm package |
| `config check [path]` | CI enforcement gate (exit 0=pass, 1=fail, 2=no config; `--json`) |

## Native Tool-Output Filter

| Command | Description |
|---------|-------------|

`AI_TOOLKIT_OUTPUT_FILTER_DISABLE=1` bypasses active filtering immediately.

## Project Registry

| Command | Description |
|---------|-------------|
| `projects` | List registered projects |
| `projects --prune` | Remove stale (deleted) entries |
| `projects remove /path` | Unregister specific project |

## Generator Commands

| Command | Description |
|---------|-------------|
| `generate-all` | Generate all platform configs at once |
| `agents-md` | Regenerate `AGENTS.md` from agent definitions |
| `codex-md` | Generate `AGENTS.md` (coding rules inlined) with marker injection for Codex CLI |
| `codex-hooks` | Generate `.codex/hooks.json` for Codex CLI |
| `cursor-rules` | Generate `.cursorrules` (legacy single file) |
| `cursor-mdc` | Generate `.cursor/rules/*.mdc` (recommended) |
| `windsurf-rules` | Generate `.windsurfrules` (legacy) |
| `windsurf-dir-rules` | Generate `.windsurf/rules/*.md` (recommended) |
| `copilot-instructions` | Generate `.github/copilot-instructions.md` |
| `gemini-md` | Generate `GEMINI.md` for Gemini CLI |
| `cline-rules` | Generate `.clinerules` (legacy) |
| `cline-dir-rules` | Generate `.cline/rules/*.md` plus `.clinerules/*.md` compatibility |
| `cline-hooks` | Generate eight executable `.cline/hooks/<Event>` files plus `.clinerules/hooks/<Event>` extension compatibility |
| `roo-modes` | Generate `.roomodes` |
| `roo-dir-rules` | Generate `.roo/rules/*.md` |
| `aider-conf` | Generate `.aider.conf.yml` |
| `conventions-md` | Generate `CONVENTIONS.md` for Aider |
| `augment-rules` | Generate `.augment/rules/ai-toolkit.md` (legacy) |
| `augment-dir-rules` | Generate `.augment/rules/ai-toolkit-*.md` (recommended) |
| `antigravity-rules` | Generate `.agents/rules/` and `.agents/workflows/` |
| `antigravity-plugin export [output]` | Export deterministic native Antigravity plugin ZIP for `.agents/plugins/<name>/`, `~/.gemini/antigravity-cli/plugins/<name>/` (CLI), or `~/.gemini/config/plugins/<name>/` (IDE/shared product) |
| `antigravity-plugin verify <archive-or-dir>` | Verify Antigravity plugin schema, paths, hooks, modes, and self-containment offline |
| `llms-txt` | Generate `llms.txt` and `llms-full.txt` |

## Other Commands

| Command | Description |
|---------|-------------|
| `stats` | Show skill usage statistics (`--summary` for product telemetry, `--reset` to clear, `--json` for raw output) |
| `benchmark --my-config` | Compare your config vs defaults vs ecosystem |
| `benchmark-ecosystem` | Generate ecosystem benchmark snapshot |
| `create skill <name>` | Scaffold new skill from template (`--template=linter\|reviewer\|generator\|workflow\|knowledge`) |
| `sync` | Config portability via GitHub Gist (`--export`, `--push`, `--pull`, `--import`) |
| `compile-slm` | Compile toolkit into minimal SLM system prompt (`--budget`, `--model-size`, `--dry-run`) |
| `evaluate` | Run skill evaluation suite |

### `stats`

```bash
ai-toolkit stats                 # table of local skill usage
ai-toolkit stats --summary       # product telemetry summary
ai-toolkit stats --summary --json  # machine-readable telemetry
ai-toolkit stats --reset         # clear local stats
```

`--summary` reports total invocations, unique skills used, catalog coverage, unused catalog skills, active skills in the last 7 days, and top skills. Data stays local in `~/.softspark/ai-toolkit/stats.json`.

## Install / Update Options

```bash
ai-toolkit install --only agents,hooks          # apply only listed components
ai-toolkit install --skip hooks                 # skip listed components
ai-toolkit install --profile minimal            # minimal | standard | strict
ai-toolkit install --persona backend-lead       # backend-lead | frontend-lead | devops-eng | junior-dev
ai-toolkit install --local --editors all        # Claude Code + all editors
ai-toolkit install --local --editors cursor,aider  # + specific editors
ai-toolkit install --local --lang typescript    # explicit language rules
ai-toolkit install --modules core,agents,rules-typescript  # selective modules
ai-toolkit install --list                       # dry-run: show what would change
ai-toolkit update --local                       # auto-detects editors from existing files
```
