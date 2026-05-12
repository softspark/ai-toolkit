---
title: "Extension API Reference"
category: reference
service: ai-toolkit
tags: [extension-api, inject-rule, inject-hook, inject-mcp, mcp-templates, integration, editors]
version: "1.5.0"
created: "2026-04-07"
last_updated: "2026-05-12"
description: "Reference for ai-toolkit's extension API: inject-rule, inject-hook, inject-mcp, remove-* variants, and editor-aware MCP template management."
---

# Extension API Reference

## Overview

ai-toolkit exposes a generic extension API that lets external tools register their own rules and hooks alongside the toolkit's built-in components. The toolkit has no knowledge of any specific consumer — it only provides the injection mechanism. Consumers call the public CLI commands from their own install scripts.

This design is intentional: ai-toolkit is a generic toolkit. Consumers (MCP servers, CI systems, custom tools) use the public API to add their own rules and hooks without modifying toolkit internals.

## Commands

| Command | Target File | Mechanism | Idempotent |
|---------|-------------|-----------|------------|
| `inject-rule <file.md>` | `~/.claude/CLAUDE.md` | HTML comment markers (`<!-- TOOLKIT:name -->`) | Yes |
| `remove-rule <name>` | `~/.claude/CLAUDE.md` | Strip markers by block name | Yes |
| `inject-hook <file.json\|url> [name]` | `~/.claude/settings.json` | JSON `_source` tag per entry, URL cached + registered | Yes |
| `remove-hook <name>` | `~/.claude/settings.json` | Strip all entries with matching `_source`, unregister URL source | Yes |
| `inject-mcp <file.json\|url> [name] [--force]` | `~/.mcp.json` + every editor with `global_path` | JSON `_source` tag per server, URL cached + registered, full editor propagation | Yes |
| `remove-mcp <name>` | `~/.mcp.json` + every editor with `global_path` | Strip all servers with matching `_source`, clean editor configs, unregister URL | Yes |
| `add-rule <file.md\|url>` | `~/.softspark/ai-toolkit/rules/` | File copy + re-inject all rules on next `update` | Yes |
| `mcp add <name...>` | `.mcp.json` | Merge `mcpServers` block from built-in template | Yes |
| `mcp install --editor <name...>` | Native editor MCP config | Render canonical template into editor format | Yes |

## inject-rule

Injects a Markdown rules file into `~/.claude/CLAUDE.md` between named HTML comment markers.

```bash
npx @softspark/ai-toolkit inject-rule ./my-tool-rules.md
```

**Implementation:** `scripts/inject_rule_cli.py` (delegates to `inject_section_cli.py`).

**Markers written:**
```html
<!-- TOOLKIT:my-tool-rules START -->
... content of my-tool-rules.md ...
<!-- TOOLKIT:my-tool-rules END -->
```

The block name is derived from the file stem (`my-tool-rules.md` → `my-tool-rules`). Re-running replaces the existing block — no duplicates. Content outside these markers is never modified.

## remove-rule

Strips a previously injected rule block from `~/.claude/CLAUDE.md`.

```bash
npx @softspark/ai-toolkit remove-rule my-tool-rules
```

The argument is the block name (file stem used during `inject-rule`). If the block is not present, the command exits 0 silently.

## inject-hook

Injects hook entries from a JSON file or HTTPS URL into `~/.claude/settings.json`. Every injected entry is tagged with `"_source": "<source-name>"` where the source name is derived from the filename stem or URL last segment.

```bash
# From local file
npx @softspark/ai-toolkit inject-hook ./my-tool-hooks.json

# From URL (HTTPS only) — cached locally, auto-refreshed on update
npx @softspark/ai-toolkit inject-hook https://example.com/my-tool-hooks.json

# With explicit source name
npx @softspark/ai-toolkit inject-hook https://example.com/hooks.json my-tool-hooks
```

**Implementation:** `scripts/inject_hook_cli.py`, `scripts/hook_sources.py`, `scripts/url_fetch.py`.

**Input format:**
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "$HOME/.my-tool/hooks/on-start.sh" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "$HOME/.my-tool/hooks/on-edit.sh" }]
      }
    ]
  }
}
```

**Source name derivation:** `my-tool-hooks.json` → source name `"my-tool-hooks"`. For URLs: `https://example.com/path/my-tool-hooks.json` → `"my-tool-hooks"`. All entries are tagged `"_source": "my-tool-hooks"` in settings.json.

**URL support:** When an HTTPS URL is provided, the JSON is fetched, validated, cached in `~/.softspark/ai-toolkit/hooks/external/<name>.json`, and registered in `sources.json`. On every `ai-toolkit update`, URL-sourced hooks are re-fetched and re-injected automatically. If the fetch fails during update, the cached version is used.

**Idempotency:** Re-running strips all existing entries with the same source name, then appends the new ones. No duplicates accumulate.

**Safety:** Entries tagged `"_source": "ai-toolkit"` are never modified or removed by this command. External tools cannot affect the toolkit's own hooks. Only HTTPS URLs are accepted.

**Codex propagation:** Codex-compatible events (`SessionStart`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`) are automatically propagated to `~/.codex/hooks.json`. Non-Codex events are silently skipped. No extra flags needed.

## remove-hook

Strips all hook entries from `~/.claude/settings.json` that carry a given `_source` tag. If the hook was URL-sourced, also unregisters the URL from `sources.json` and removes the cached file.

```bash
npx @softspark/ai-toolkit remove-hook my-tool-hooks
```

The argument is the source name (file stem used during `inject-hook`). If no entries with that source are present, the command exits 0 silently.

## inject-mcp

Injects an external MCP server template into `~/.mcp.json` (toolkit source-of-truth) and propagates it to every editor that exposes a `global_path` in `EDITOR_SPECS`. Symmetric with `inject-hook` -- accepts both local file paths and HTTPS URLs, with cache + auto-refresh on `ai-toolkit update`.

```bash
# From local file
npx @softspark/ai-toolkit inject-mcp ./rag-mcp-template.json

# From URL (cached locally, auto-refreshed on update)
npx @softspark/ai-toolkit inject-mcp https://example.com/rag-mcp-template.json

# With explicit source name (preferred when filename stem is generic)
npx @softspark/ai-toolkit inject-mcp ./mcp/mcp-template.json --name rag-mcp

# With explicit target dir
npx @softspark/ai-toolkit inject-mcp ./template.json /custom/target --name my-rag

# Force overwrite of servers with a different _source (collision resolution)
npx @softspark/ai-toolkit inject-mcp ./conflict.json --force
```

**Flags:** `--name <name>` overrides the auto-derived source name (works for both local files and URLs). `--force` overwrites servers tagged with a different `_source`. Positional `template-name` is supported only for URL sources (legacy positional grammar inherited from `inject-hook`); for local files use `--name`.

**Implementation:** `scripts/inject_mcp_cli.py`, `scripts/mcp_sources.py`, `scripts/url_fetch.py`.

**Input format:** Same as built-in templates in `app/mcp-templates/`:
```json
{
  "name": "rag-mcp",
  "description": "Multi-tenant RAG over knowledge bases",
  "mcpServers": {
    "rag-mcp": {
      "type": "http",
      "url": "http://localhost:8081/mcp/sse?secret_key=${RAG_MCP_SECRET_KEY}"
    }
  }
}
```

**Source name derivation:** `rag-mcp-template.json` → `"rag-mcp-template"`. For URLs: `https://example.com/rag-mcp-template.json` → `"rag-mcp-template"`. Every server in the `mcpServers` block is tagged with `"_source": "<source-name>"` inside `~/.mcp.json` only; native editor configs receive the same servers **without** the `_source` field (some clients reject unknown keys).

**URL support:** When an HTTPS URL is provided, the JSON is fetched, validated, cached in `~/.softspark/ai-toolkit/mcp-templates/external/<name>.json`, and registered in `sources.json`. On every `ai-toolkit update`, URL-sourced templates are re-fetched and re-injected automatically. If the fetch fails during update, the cached version is used.

**Editor propagation:** Every editor with a `global_path` in `EDITOR_SPECS` is updated -- Claude (`~/.claude.json`), Cursor (`~/.cursor/mcp.json`), GitHub Copilot (`~/.copilot/mcp-config.json`), Gemini CLI (`~/.gemini/settings.json`), Windsurf (`~/.codeium/windsurf/mcp_config.json`), Cline (`~/.cline/data/settings/cline_mcp_settings.json`), Augment (`~/.augment/settings.json`), Codex CLI (`~/.codex/config.toml`). Per-editor failures are non-fatal -- the command reports a warning and continues.

**Idempotency:** Re-running with the same source overwrites entries for that source cleanly -- no duplicates accumulate.

**Collisions:** If a server name in `~/.mcp.json` already exists under a *different* `_source` tag, the command exits with code 3 unless `--force` is passed. Entries tagged `"_source": "ai-toolkit"` are protected even with `--force` -- the built-in template namespace cannot be hijacked.

**Safety:** Only HTTPS URLs are accepted. The source name `ai-toolkit` is reserved.

## remove-mcp

Strips all server entries from `~/.mcp.json` that carry a given `_source` tag, cleans the same server names from every editor `global_path`, and (if URL-sourced) unregisters from `sources.json` and removes the cached file.

```bash
npx @softspark/ai-toolkit remove-mcp rag-mcp-template
```

The argument is the source name (file stem used during `inject-mcp`). If no entries with that source are present, the command exits 0 silently. `ai-toolkit` source is reserved and cannot be removed via this command.

## mcp add / install

Merges one or more MCP server templates from `app/mcp-templates/` into the project's `.mcp.json`.

```bash
ai-toolkit mcp add github                # add a single template
ai-toolkit mcp add github postgres slack  # add multiple at once
ai-toolkit mcp list                       # list all available templates
ai-toolkit mcp editors                    # list supported native adapters
ai-toolkit mcp show github                # print a template's JSON
ai-toolkit mcp install --editor cursor --scope project github --target .
ai-toolkit mcp install --editor codex context7
ai-toolkit mcp remove github             # remove an entry from .mcp.json
ai-toolkit mcp remove github --editor cursor --scope project --target .
```

**Implementation:** `scripts/mcp_manager.py`.

The `add` command merges the `mcpServers` block from the template into `.mcp.json`. If `.mcp.json` does not exist, it is created. If the server name already exists, the entry is overwritten.

The `install` command renders the same canonical template into a native editor config format. Supported adapters currently cover:
- JSON clients with `mcpServers`: Claude Code, Cursor, Gemini CLI, Windsurf, Cline, Augment
- JSON clients with additional required metadata: GitHub Copilot
- TOML clients: Codex CLI

When `install` runs with `--scope project`, ai-toolkit also updates `.mcp.json` so the project-level config remains the source of truth for later sync and local install flows.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   ai-toolkit (generic)               │
│                                                      │
│  Public Extension API:                               │
│    inject-rule  <file.md>     → CLAUDE.md            │
│    remove-rule  <name>        → CLAUDE.md            │
│    inject-hook  <file|url>    → settings.json        │
│    remove-hook  <name>        → settings.json        │
│    inject-mcp   <file|url>    → .mcp.json + editors  │
│    remove-mcp   <name>        → .mcp.json + editors  │
│    add-rule     <file|url>    → rules/ registry      │
│    mcp add      <template>    → .mcp.json            │
│    mcp install  <template>    → editor-native MCP    │
│                                                      │
│  Idempotent: markers (rules) / _source tags (hooks)  │
│  URL sources: cached + auto-refreshed on update      │
└──────────────────────────────────────────────────────┘
                        ▲
                        │ uses API
        ┌───────────────┼───────────────┐
        │               │               │
   rag-mcp          custom-tool     ci-system
   (consumer)       (consumer)      (consumer)
```

## Example: Registering Rules, Hooks, and MCP Servers from an External Tool

An external tool's install script would call:

```bash
# Register rules into CLAUDE.md
npx @softspark/ai-toolkit inject-rule ./rules/my-tool-rules.md

# Register hooks into settings.json (auto-propagates to Codex)
npx @softspark/ai-toolkit inject-hook ./hooks/my-tool-hooks.json

# Register MCP server template into .mcp.json + all editor MCP configs
npx @softspark/ai-toolkit inject-mcp ./mcp-template.json

# Alternative: pull MCP template from a URL (auto-refreshed on update)
npx @softspark/ai-toolkit inject-mcp https://example.com/mcp-template.json
```

To uninstall:

```bash
npx @softspark/ai-toolkit remove-rule my-tool-rules
npx @softspark/ai-toolkit remove-hook my-tool-hooks
npx @softspark/ai-toolkit remove-mcp my-tool
```

All operations are idempotent — safe to run on every install or update.

## Related Documentation

- [PATH: kb/reference/hooks-catalog.md] — built-in hooks reference
- [PATH: kb/reference/mcp-templates.md] — available MCP server templates
- [PATH: kb/reference/mcp-editor-compatibility.md] — native editor MCP support matrix
- [PATH: kb/reference/architecture-overview.md] — overall install model
