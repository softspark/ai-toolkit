---
title: "CLI Reference"
category: reference
service: ai-toolkit
tags: [cli, commands, reference, install, update, plugin, mcp, telemetry]
created: "2026-04-13"
last_updated: "2026-10-08"
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
| `install --opt-in-rules <list>` | Enable opt-in registered rules (`rag-mcp-legal-rules` is opt-in by default; `add-rule --opt-in` marks others). Stored per project with `--local`, otherwise in `state.json`; `none` clears the list. Without the flag the stored list applies |
| `install --local` | Claude Code configs only; add `--editors all` or `--editors cursor,aider` for other tools. Keeps an `@AGENTS.md` import in `CLAUDE.md`, creates `AGENTS.md` from the template only in a project without instructions, and removes toolkit sections an older release put in `AGENTS.md` |
| `adopt-agents-md [dir] [--dry-run]` | Move the project's own `CLAUDE.md` instructions into `AGENTS.md` (read by every agent), leave `CLAUDE.md` importing it next to the toolkit sections, and drop an `AGENTS.md` entry from `.gitignore`; every file is backed up first |
| `update` | Re-apply toolkit after `npm install -g @softspark/ai-toolkit@latest` |
| `update --local` | Re-apply + auto-detect editors from existing project files |
| `reset --local` | Wipe all project-local configs and recreate from scratch (clean slate) |
| `status` | Show installed modules and version |
| `uninstall` | Remove everything the toolkit installed: every registered project, `~/.claude/` and editor surfaces, toolkit settings, and `~/.softspark/ai-toolkit/` (archived to `~/ai-toolkit-backup-<time>.tar.gz` first). `--local` removes one project and unregisters it |
| `validate` | Verify toolkit integrity (`--strict` for CI-grade, warnings = errors) |
| `doctor` | Diagnose install health, hooks, quick-win assets, artifact drift, context budget (est. resident tokens of the skill/agent listings and user rules, plus skills with zero recorded use; read-only, prints the `skillOverrides` key to paste), and permission rules (`permissions.allow` wildcards on interpreters, task runners, package installs, `gh api`, `curl`, `git fetch`, destructive commands; warns only, never edits) |
| `doctor --fix` | Auto-repair broken symlinks, missing hooks, stale artifacts |
| `eject [dir]` | Export standalone config (no symlinks, no toolkit dependency) |
| `claude-app export [--output FILE] [--no-custom-rules] [--verify]` | Writes to the directory you run the command in (relative `--output` and the default `ai-toolkit-claude-app.zip` + `*-global-instructions.md`; before v4.32.2 they landed inside `node_modules/@softspark/ai-toolkit`). Build an uploadable Claude Chat/Desktop/Cowork plugin ZIP and global-instructions file |
| `claude-app verify` | Validate a clean staged plugin with structural checks and the official Claude plugin validator |
| `codex-plugin export [--output FILE]` | Build a deterministic native Codex plugin ZIP with skills and self-contained hooks |
| `codex-plugin verify` | Validate a clean native Codex plugin stage without installing it or changing user configuration |

## Combined LLM Account Status

`ai-toolkit llm-status` displays every account registered with
`ai-toolkit claude-switch` and `ai-toolkit codex-switch`, grouped by provider. Each group retains
its own active account selected by the current directory, default marker,
usage bars, reset times and fetch age.

| Option | Behavior |
|--------|----------|
| No options | Fetch live limits for all configured Claude and Codex accounts |
| `--refresh` or `refresh` | Explicit spelling of the same live query for both providers |
| `--verbose`, `-v` | Add profile paths, project bindings and exact timestamps |
| `--json` | Return `account_count` and `providers.claude` / `providers.codex` |
| `--color auto\|always\|never` | Control terminal color; `NO_COLOR` disables it |

Each JSON provider includes `state`, `default_account`, `selected`, `accounts`
and `error`. Same-named accounts remain separate under their provider.
Unconfigured providers have `state: "not_configured"` and an empty account
list. An unreadable or invalid registry returns `state: "error"`,
`error: "invalid_configuration"`, and process exit code 1 while still showing
the other provider. No configured accounts is a successful empty result with
setup hints in terminal output. Individual refresh errors stay on the affected
account, as in `ai-toolkit codex-switch status`, without showing old readings.
A refresh failure does not make the command exit nonzero.

The command honors `CLAUDE_SWITCH_CONFIG`, `CODEX_SWITCH_CONFIG` and toolkit
data-directory overrides. It never initializes registries or changes account
bindings. Quota readings are neither cached on disk nor loaded from old cache
files. Claude uses each profile's OAuth credentials with its internal usage
endpoint; Codex uses its native app-server, which may update its own
authentication and local state. Neither reader submits a model turn.

## Claude Code Account Routing

`ai-toolkit claude-switch` manages profiles and launches the native Claude CLI.

| Command | Description |
|---------|-------------|
| `ai-toolkit claude-switch init` | Create the account registry, preserving the existing default Claude login |
| `ai-toolkit claude-switch add NAME [--share-config]` | Create a separate profile; optionally symlink selected configuration from `~/.claude/` and copy the default account's user-scope `mcpServers` into the profile's `.claude.json` |
| `ai-toolkit claude-switch bind PATH NAME` | Assign an existing project directory and its descendants to a profile |
| `ai-toolkit claude-switch default NAME` | Set the profile used outside bound projects |
| `ai-toolkit claude-switch status [--refresh] [--account NAME] [--verbose] [--color auto\|always\|never] [--json]` | Live usage bars for all profiles; `--verbose` adds paths, bindings and exact UTC timestamps; JSON retains all fields |
| `ai-toolkit claude-switch login NAME` | Run Claude's native `auth login` for that profile |
| `ai-toolkit claude-switch run [--account NAME] [--] ARGS...` | Launch Claude with the selected configuration and forward arguments |

The longest directory binding wins. Unbound linked Git worktrees inherit the
main checkout's binding. The default registry is
`~/.softspark/ai-toolkit/claude-switch.json`; `CLAUDE_SWITCH_CONFIG` can select
another file. Status counts configured profiles and preserves selected routing
fields in JSON, adding `account_count`, `default_account`, and `accounts`.
Usage is fetched live for each profile on every invocation. Missing windows
remain unknown and failures appear per account. The internal Claude usage
endpoint is not a stable public API. Status never alters account routing.
See [Claude account profiles](../howto/claude-account-profiles.md) for setup,
configuration sharing, authentication checks, and CLI-only scope.

## Codex / OpenAI Account Routing

`ai-toolkit codex-switch` manages profiles and launches the native Codex CLI.

| Command | Description |
|---------|-------------|
| `ai-toolkit codex-switch init` | Preserve the current native Codex home as the original default |
| `ai-toolkit codex-switch add NAME [--share-config]` | Create a private Codex home; optionally link reusable configuration |
| `ai-toolkit codex-switch bind PATH NAME` | Route a project, descendants and its unbound worktrees |
| `ai-toolkit codex-switch default NAME` | Set the fallback profile |
| `ai-toolkit codex-switch login NAME` | Start native Codex login in that profile |
| `ai-toolkit codex-switch run [--account NAME] [--] ARGS...` | Run Codex, honoring directory routing and native `-C`/`--cd` |
| `ai-toolkit codex-switch status [--refresh] [--verbose] [--color auto\|always\|never] [--json] [--account NAME]` | Fetch live account limits via the native app-server on every invocation |

Registry: `~/.softspark/ai-toolkit/codex-switch.json`. Override with
`CODEX_SWITCH_CONFIG`; toolkit data follows `AI_TOOLKIT_HOME`. Named profiles
use `--no-daemon`, isolated SQLite state and separate native credentials.
This command does not change ChatGPT/Desktop/IDE login or rotate accounts on
quota exhaustion. See [Codex account profiles](../howto/codex-account-profiles.md).

Account tools are subcommands of `ai-toolkit` only. Plain `claude` and
`codex` retain their native behavior. Use the matching `run` subcommand for
project routing. Older shell functions must be removed from startup files
and cleared from open terminals; see the migration steps in the account guides.

## Rule & Hook Injection

| Command | Description |
|---------|-------------|
| `add-rule <rule.md\|url> [name]` | Register rule in `~/.softspark/ai-toolkit/rules/` — auto-applied on every `update` |
| `add-rule … --requires-mcp <servers>` | Record the MCP servers the rule needs (empty = none). Files read by Antigravity, Gemini CLI, Codex, Copilot or OpenCode (`.agents/rules/`, `AGENTS.md`, `GEMINI.md`) get the rule only when one of their readers has the server configured, matched by server name or command basename. Without the flag, a rule named `<server>` or `<server>-rules` whose name has an `mcp` segment requires `<server>`. Such rules end with an explicit "server unavailable" fallback |
| `add-rule … --opt-in` / `--no-opt-in` | Emit the rule only where `install --opt-in-rules <name>` enabled it (or revert to always emitting it) |
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
| `agents-md` | Regenerate `AGENTS.md` from agent definitions (refuses to overwrite a project's own `AGENTS.md`) |
| `codex-md` | Generate `AGENTS.md` (coding rules inlined) for Codex CLI (refuses to overwrite a project's own `AGENTS.md`) |
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
