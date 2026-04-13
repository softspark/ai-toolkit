---
title: "Extension API Reference"
category: reference
service: ai-toolkit
tags: [extension-api, inject-rule, inject-hook, mcp-templates, integration, editors]
version: "1.3.9"
created: "2026-04-07"
last_updated: "2026-04-12"
description: "Reference for ai-toolkit's extension API: inject-rule, inject-hook, remove-rule, remove-hook, and editor-aware MCP template management."
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
| `inject-hook <file.json>` | `~/.claude/settings.json` | JSON `_source` tag per entry | Yes |
| `remove-hook <name>` | `~/.claude/settings.json` | Strip all entries with matching `_source` | Yes |
| `add-rule <file.md>` | `~/.softspark/ai-toolkit/rules/` | File copy + re-inject all rules on next `update` | Yes |
| `mcp add <name...>` | `.mcp.json` | Merge `mcpServers` block from template | Yes |
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

Injects hook entries from a JSON file into `~/.claude/settings.json`. Every injected entry is tagged with `"_source": "<source-name>"` where the source name is derived from the filename stem.

```bash
npx @softspark/ai-toolkit inject-hook ./my-tool-hooks.json
```

**Implementation:** `scripts/inject_hook_cli.py`.

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

**Source name derivation:** `my-tool-hooks.json` → source name `"my-tool-hooks"`. All entries are tagged `"_source": "my-tool-hooks"` in settings.json.

**Idempotency:** Re-running strips all existing entries with the same source name, then appends the new ones. No duplicates accumulate.

**Safety:** Entries tagged `"_source": "ai-toolkit"` are never modified or removed by this command. External tools cannot affect the toolkit's own hooks.

## remove-hook

Strips all hook entries from `~/.claude/settings.json` that carry a given `_source` tag.

```bash
npx @softspark/ai-toolkit remove-hook my-tool-hooks
```

The argument is the source name (file stem used during `inject-hook`). If no entries with that source are present, the command exits 0 silently.

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
│    inject-hook  <file.json>   → settings.json        │
│    remove-hook  <name>        → settings.json        │
│    add-rule     <file.md>     → rules/ registry      │
│    mcp add      <template>    → .mcp.json            │
│    mcp install  <template>    → editor-native MCP    │
│                                                      │
│  Idempotent: markers (rules) / _source tags (hooks)  │
│  ai-toolkit NEVER calls external services            │
└──────────────────────────────────────────────────────┘
                        ▲
                        │ uses API
        ┌───────────────┼───────────────┐
        │               │               │
   rag-mcp          custom-tool     ci-system
   (consumer)       (consumer)      (consumer)
```

## Example: Registering Rules and Hooks from an External Tool

An external tool's install script would call:

```bash
# Register rules into CLAUDE.md
npx @softspark/ai-toolkit inject-rule ./rules/my-tool-rules.md

# Register hooks into settings.json
npx @softspark/ai-toolkit inject-hook ./hooks/my-tool-hooks.json

# Add an MCP server template
npx @softspark/ai-toolkit mcp add github

# Render the same template into Cursor project config
npx @softspark/ai-toolkit mcp install --editor cursor --scope project github --target .
```

To uninstall:

```bash
npx @softspark/ai-toolkit remove-rule my-tool-rules
npx @softspark/ai-toolkit remove-hook my-tool-hooks
```

All operations are idempotent — safe to run on every install or update.

## Related Documentation

- [PATH: kb/reference/hooks-catalog.md] — built-in hooks reference
- [PATH: kb/reference/mcp-templates.md] — available MCP server templates
- [PATH: kb/reference/mcp-editor-compatibility.md] — native editor MCP support matrix
- [PATH: kb/reference/architecture-overview.md] — overall install model
