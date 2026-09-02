---
title: "Plugin Pack Conventions"
category: reference
service: ai-toolkit
tags: [plugins, plugin-packs, conventions, manifests, hooks, policy-packs]
version: "1.3.0"
created: "2026-03-28"
last_updated: "2026-08-31"
description: "Conventions for experimental ai-toolkit plugin packs, policy packs, hook packs, and plugin-creator scaffolding across supported editors."
---

# Plugin Pack Conventions

## Purpose

`ai-toolkit` includes experimental plugin packs under `app/plugins/` for Claude Code, Codex, Cursor, and Gemini global layering, and discovers external packs under `~/.softspark/ai-toolkit/plugins/` (see *Where Packs Live*). These internal pack manifests are distinct from the official uploadable Claude app plugin built by `ai-toolkit claude-app export`.

## Where Packs Live

| Root | Owner | Survives `npm install -g @softspark/ai-toolkit` | Use for |
|------|-------|------------------------------------------------|---------|
| `app/plugins/<pack>/` | this repository | no — the upgrade replaces `app/` wholesale | packs shipped with the toolkit (`memory-pack`, `enterprise-pack`) |
| `~/.softspark/ai-toolkit/plugins/<pack>/` | the user | **yes** | external / private packs maintained in their own repository |

Both roots are scanned by `plugin list`, `install`, `update`, `remove` and
`status`. A **core pack wins a name collision**, so an external directory cannot
shadow shipped behaviour. `AI_TOOLKIT_HOME` moves the user root along with the
rest of the toolkit data dir, which is what the test suite uses.

Before v4.24.0 there was only the first root, so the only way to add an external
pack was to drop it inside the npm package — where the next toolkit upgrade
deleted it. That is what the user root exists to end.

### Installing an external pack

The entry may be a directory **or a symlink**, which is what gives an external
pack a versioned update path:

```bash
# Distributed as a package (private registry example)
npm install -g @softspark/<pack> --registry=https://npm.pkg.github.com
mkdir -p ~/.softspark/ai-toolkit/plugins
ln -s "$(npm root -g)/@softspark/<pack>" ~/.softspark/ai-toolkit/plugins/<pack>
ai-toolkit plugin install --editor claude <pack>

# Update later: the symlink target is rewritten in place, nothing to re-link
npm install -g @softspark/<pack>@latest --registry=https://npm.pkg.github.com
```

A plain `git clone` into the same directory works too; update it with `git pull`.

> **Scope note:** `npm` resolves a registry per **scope**, not per package. If one
> package in a scope lives on public npm and another on a private registry, the
> private one needs `--registry=` on every command — a scope-wide
> `npm config set @scope:registry` would misroute the public one.

## Pack Types

| Type | Purpose | Example |
|------|---------|---------|
| `plugin-pack` | Curated bundle of existing assets by domain | `security-pack`, `research-pack` |
| `policy-pack` | Rules / compliance / governance overlays | future enterprise policy add-ons |
| `hook-pack` | Optional hook modules or observability bundles | status line, output style |

## Directory Contract

```text
app/plugins/<pack-name>/
├── plugin.json
├── README.md
├── hooks/        # optional, executable if present
├── mcp/          # optional, pack-local MCP templates
├── rules/        # optional
├── skills/       # optional
├── agents/       # optional
└── templates/    # optional
```

## Manifest Contract

Required keys:
- `name`
- `description`
- `version`
- `domain`
- `type`
- `status`
- `requires`
- `includes`

`includes` should declare arrays for:
- `agents`
- `skills`
- `rules`
- `hooks`
- `mcp` (optional MCP template names)

An MCP reference such as `"rag-mcp-legal"` resolves first to the pack-owned
`mcp/rag-mcp-legal.json`, then to the built-in
`app/mcp-templates/rag-mcp-legal.json`. Each template must use the same `name`
as the reference and provide a non-empty `mcpServers` object. A localhost HTTP
template must also include a `postInstall` warning that the endpoint is
`unauthenticated`.

## Naming Rules

- Pack directory and `name` should use lowercase-hyphen format
- Prefer `*-pack` suffix for curated bundles
- Hook module filenames should be kebab-case and executable
- Experimental packs should declare `"status": "experimental"`

## Adoption Rules

1. Packs are opt-in and must not be auto-installed by `ai-toolkit install`
2. Reuse core agents/skills before duplicating definitions
3. Optional hooks must be documented as opt-in and non-default
4. Policy packs should be additive and marker-injected where possible
5. Keep manifests small and reviewable; use README for narrative guidance

## CLI Management

```bash
ai-toolkit plugin list               # show all available packs with install status
ai-toolkit plugin install --editor claude <name>   # Claude Code global target
ai-toolkit plugin install --editor codex <name>    # Codex global target
ai-toolkit plugin install --editor cursor <name>   # Cursor global target
ai-toolkit plugin install --editor gemini <name>   # Gemini CLI global target
ai-toolkit plugin install --editor all --all       # install all available packs for all supported editors
ai-toolkit plugin update --editor all --all        # update all installed packs
ai-toolkit plugin clean <name>       # prune data older than 90 days (default)
ai-toolkit plugin clean <name> --days 30  # prune data older than 30 days
ai-toolkit plugin remove --editor codex <name>     # remove from one runtime only
ai-toolkit plugin remove --editor all --all        # remove all installed packs everywhere
ai-toolkit plugin status --editor all              # show installed packs with runtime details
```

### What `plugin install` Does

1. **Parses** `--editor claude|codex|cursor|gemini|all` (default: `claude`)
2. **Copies** plugin-specific hooks to runtime-owned storage: Claude uses `~/.softspark/ai-toolkit/hooks/plugin-<pack>-<hook>.sh`; Codex uses `$CODEX_HOME/ai-toolkit-hooks/plugin-<pack>-<hook>.sh`
3. **Copies** shared plugin scripts to `~/.softspark/ai-toolkit/plugin-scripts/<pack>/`
4. **Runs** init scripts if present (e.g. `init_db.py` for memory-pack — safe to re-run, preserves data)
5. **Claude Code target**: links missing agents/skills into `~/.claude/`, injects plugin-local rules into `~/.claude/CLAUDE.md`, and merges plugin hook entries into `~/.claude/settings.json`
6. **Codex target**: bootstraps `$CODEX_HOME/AGENTS.md`, `$HOME/.agents/skills`, `$CODEX_HOME/hooks.json`, and self-contained `$CODEX_HOME/ai-toolkit-hooks`, then layers plugin-specific rules and hooks on top; it does not write `~/AGENTS.md` or `.agents/rules/`
7. **Cursor target**: writes each pack-owned rule as `~/.cursor/rules/plugin-<pack>-<rule>.mdc` with `alwaysApply: true`; files are exact-hash owned and collisions are rejected
8. **Gemini target**: marker-injects each pack-owned rule into `~/.gemini/GEMINI.md` as `plugin-<pack>-<rule>`, preserving all unrelated content
9. **Records** installed state per runtime in `~/.softspark/ai-toolkit/plugins.json`
10. **MCP assets**: installs `includes.mcp` into the selected editor's global MCP config, rejects unowned same-name entries, and records the exact normalized server configuration under the plugin's ownership state

### What `plugin update` Does

1. **Preflights** MCP and native-rule collisions before changing any plugin state, skill, rule, hook, or script
2. **Removes** existing plugin runtime entries for the selected editor(s) (same as `remove`)
3. **Reinstalls** from the current source (same as `install`)
4. **Preserves plugin data** (e.g. memory-pack SQLite database is never deleted)
5. Shared plugin scripts/hooks are kept if another runtime still has the same pack installed
6. `--all` updates only currently installed packs for the selected runtime(s)

### What `plugin clean` Does

1. **Prunes** old plugin data based on `--days N` (default 90)
2. For memory-pack: deletes observations older than N days, removes orphan sessions, runs VACUUM
3. Shows before/after counts and DB size

### What `plugin remove` Does

1. **Claude Code target**: strips plugin hook entries from `~/.claude/settings.json` and removes plugin-local rule sections from `~/.claude/CLAUDE.md`
2. **Codex target**: strips only command handlers carrying the exact `AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-<pack>` marker from `$CODEX_HOME/hooks.json`, removes owned `$CODEX_HOME/ai-toolkit-hooks/plugin-<pack>-*` assets, and removes the pack's marker-bounded sections from `$CODEX_HOME/AGENTS.md`
3. **Cursor/Gemini rules**: removes only exact content recorded in `rule_ownership`; foreign or user-modified files/sections are preserved with a warning
4. **Claude/shared assets** (`~/.softspark/ai-toolkit/hooks/plugin-*`, `plugin-scripts/<pack>/`) are removed only when no remaining runtime still uses that pack
5. **Updates** `plugins.json` state per runtime
6. **Leaves** core agents/skills untouched (they belong to the base install)
7. **Leaves** plugin data intact (e.g. `memory.db` — use `clean` to prune)
8. **MCP cleanup**: removes only unchanged servers recorded as owned by that plugin; user-created, foreign, or manually changed entries are preserved with a warning

### Data Retention (memory-pack)

- **Auto-retention**: `session-summary.sh` hook auto-prunes observations older than 90 days on every session end (configurable via `MEMORY_RETENTION_DAYS` env var)
- **Manual clean**: `ai-toolkit plugin clean memory-pack --days 30`
- **Status**: `ai-toolkit plugin status --editor claude|codex|all` shows runtime-specific install details plus DB size, observation count, and date range where relevant

## Current Experimental Packs

| Pack | Domain | Owns | Installs (claude / codex) | Description |
|------|--------|------|---------------------------|-------------|
| `memory-pack` | memory | 2 hooks, 2 scripts, 1 skill | 4 / 4 files | SQLite persistent memory with FTS5 search |
| `enterprise-pack` | enterprise | 2 hooks | 2 / 2 files | Status-line and output-style overlays |

Both packs ship content in this repository. Neither fetches anything at install
time.

### The rule the table now enforces

**A pack must install files the core install does not.** `ai-toolkit install`
links every core skill and agent, so a manifest naming only core assets resolves
to nothing: `plugin install` reports `(0 file items)` and no file appears on
disk. This is not a subtle degradation — it is a complete no-op, identical on
every profile (`minimal`, `standard`, `strict`) and on every supported editor.

Nine packs were removed in v4.20.0 for failing this: `csharp`, `java`, `kotlin`,
`ruby`, `rust`, `swift`, `frontend`, `research`, `security`. Every one declared
only skills and agents that already ship in core, and eight of them owned nothing
but a `README.md`. Full measurement:
[`no-op-plugin-packs-removed-20260727.md`](../history/completed/no-op-plugin-packs-removed-20260727.md).

Before adding a pack, prove it does something: install core into a throwaway
`HOME`, install the pack, and check that the reported file count is above zero.

**A pack that downloads a binary has been tried once and retired.** `rtk-pack`
(v4.18.0, removed in v4.19.0) fetched a checksum-pinned artifact in
`scripts/init.py`, declared platform assets and digests in `plugin.json`, and
rewrote commands at `PreToolUse`. Read
`kb/history/completed/rtk-pack-retirement-20260727.md` before proposing another
pack of that shape; the two defects that killed it were both invisible to
`validate.py --strict` and to the pack's own status check.

What survives from that work and applies to any pack:

- **A pack reports its own health.** `scripts/status.py` is picked up
  generically by `plugin status`, replacing what used to be a hardcoded
  `if name == "memory-pack"` branch. A status check must distinguish *installed*
  from *working*, and prove the working part by exercising it rather than by
  checking that files exist.
- **A pack may declare `supported_editors`.** Without it a pack installs on
  every runtime and silently does nothing on the ones it was never built for.
- **The manifest schema tolerates extra keys.** Anything additive is unvalidated,
  so a malformed block fails at install time rather than in `validate.py
  --strict`. Do not rely on the schema to catch it.

## Optional Hook Modules

`enterprise-pack` provides two optional hook modules:
- `hooks/status-line.sh` — status line overlay
- `hooks/output-style.sh` — enterprise reporting style

`memory-pack` provides two hooks:
- `hooks/observation-capture.sh` — captures tool actions to SQLite (PostToolUse)
- `hooks/session-summary.sh` — summarizes session on Stop

These are intentionally excluded from the default install until explicitly enabled via `ai-toolkit plugin install`.
