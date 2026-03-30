---
title: "Plugin Pack Conventions"
category: reference
service: ai-toolkit
tags: [plugins, plugin-packs, conventions, manifests, hooks, policy-packs]
version: "1.0.0"
created: "2026-03-28"
last_updated: "2026-04-02"
description: "Conventions for experimental ai-toolkit plugin packs, policy packs, hook packs, and plugin-creator scaffolding."
---

# Plugin Pack Conventions

## Purpose

`ai-toolkit` now includes experimental plugin packs under `app/plugins/` to formalize a Claude Code-compatible plugin direction without changing the default global install surface.

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
ai-toolkit plugin list               # show all 11 packs with install status
ai-toolkit plugin install <name>     # install a single pack
ai-toolkit plugin install --all      # install all 11 packs
ai-toolkit plugin update <name>      # update a pack (remove + reinstall, preserves data)
ai-toolkit plugin update --all       # update all installed packs
ai-toolkit plugin clean <name>       # prune data older than 90 days (default)
ai-toolkit plugin clean <name> --days 30  # prune data older than 30 days
ai-toolkit plugin remove <name>      # remove a pack
ai-toolkit plugin remove --all       # remove all installed packs
ai-toolkit plugin status             # show installed packs with data stats
```

### What `plugin install` Does

1. **Verifies** referenced agents/skills exist in `~/.claude/` (links them from core if missing)
2. **Copies** plugin-specific hooks to `~/.ai-toolkit/hooks/plugin-<pack>-<hook>.sh`
3. **Copies** plugin-specific scripts to `~/.ai-toolkit/plugin-scripts/<pack>/`
4. **Runs** init scripts if present (e.g. `init_db.py` for memory-pack — safe to re-run, preserves data)
5. **Merges** plugin hooks into `~/.claude/settings.json` (tagged with `_source: ai-toolkit-plugin-<name>`)
6. **Records** installed state to `~/.ai-toolkit/plugins.json`

### What `plugin update` Does

1. **Removes** existing plugin hooks, scripts, and settings.json entries (same as `remove`)
2. **Reinstalls** from the current source (same as `install`)
3. **Preserves plugin data** (e.g. memory-pack SQLite database is never deleted)
4. `--all` updates only currently installed packs (not all available)

### What `plugin clean` Does

1. **Prunes** old plugin data based on `--days N` (default 90)
2. For memory-pack: deletes observations older than N days, removes orphan sessions, runs VACUUM
3. Shows before/after counts and DB size

### What `plugin remove` Does

1. **Removes** plugin hooks from `~/.ai-toolkit/hooks/`
2. **Removes** plugin scripts from `~/.ai-toolkit/plugin-scripts/`
3. **Strips** plugin hook entries from `settings.json` (by `_source` tag)
4. **Updates** `plugins.json` state
5. **Leaves** core agents/skills untouched (they belong to the base install)
6. **Leaves** plugin data intact (e.g. `memory.db` — use `clean` to prune)

### Data Retention (memory-pack)

- **Auto-retention**: `session-summary.sh` hook auto-prunes observations older than 90 days on every session end (configurable via `MEMORY_RETENTION_DAYS` env var)
- **Manual clean**: `ai-toolkit plugin clean memory-pack --days 30`
- **Status**: `ai-toolkit plugin status` shows DB size, observation count, date range

## Current Experimental Packs

| Pack | Domain | Agents | Skills | Hooks | Description |
|------|--------|--------|--------|-------|-------------|
| `security-pack` | security | 3 | 3 | 2 | Security auditing, threat modeling, OWASP |
| `research-pack` | research | 4 | 4 | 1 | Multi-source research, synthesis, fact-checking |
| `frontend-pack` | frontend | 3 | 3 | 1 | React/Vue/CSS, SEO, design engineering |
| `enterprise-pack` | enterprise | 3 | 3 | 3 | Executive briefings, infra architecture, status |
| `memory-pack` | memory | 0 | 1 | 2 | SQLite persistent memory with FTS5 search |
| `rust-pack` | rust | 0 | 1 | 0 | Rust patterns |
| `java-pack` | java | 0 | 1 | 0 | Java patterns |
| `csharp-pack` | csharp | 0 | 1 | 0 | C# patterns |
| `kotlin-pack` | kotlin | 0 | 1 | 0 | Kotlin patterns |
| `swift-pack` | swift | 0 | 1 | 0 | Swift patterns |
| `ruby-pack` | ruby | 0 | 1 | 0 | Ruby patterns |

## Optional Hook Modules

`enterprise-pack` provides two optional hook modules:
- `hooks/status-line.sh` — status line overlay
- `hooks/output-style.sh` — enterprise reporting style

`memory-pack` provides two hooks:
- `hooks/observation-capture.sh` — captures tool actions to SQLite (PostToolUse)
- `hooks/session-summary.sh` — summarizes session on Stop

These are intentionally excluded from the default install until explicitly enabled via `ai-toolkit plugin install`.

