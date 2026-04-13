---
title: "AI Toolkit - MCP Editor Compatibility"
category: reference
service: ai-toolkit
tags: [mcp, editors, compatibility, codex, cursor]
version: "1.0.0"
created: "2026-04-12"
last_updated: "2026-04-12"
description: "Official MCP support matrix and native config targets for editors supported by ai-toolkit."
---

# MCP Editor Compatibility

## Overview

ai-toolkit keeps `.mcp.json` as the project-level canonical template format and can render that config into native editor MCP files where the editor exposes a stable, documented configuration surface.

## Supported Native Adapters

| Editor | Scope | Native Config Path | Adapter Behavior |
|--------|-------|--------------------|------------------|
| Claude Code | project + global | `.claude/settings.local.json`, `~/.claude/settings.json` | Merges `mcpServers` while preserving other settings keys |
| Cursor | project + global | `.cursor/mcp.json`, `~/.cursor/mcp.json` | Mirrors `mcpServers` directly |
| GitHub Copilot | project + global | `.github/mcp.json`, `~/.copilot/mcp-config.json` | Adds Copilot-required `type` and `tools` fields |
| Gemini CLI | project + global | `.gemini/settings.json`, `~/.gemini/settings.json` | Merges `mcpServers` into settings JSON |
| Windsurf | global | `~/.codeium/windsurf/mcp_config.json` | Global-only JSON config |
| Cline | global | `~/.cline/data/settings/cline_mcp_settings.json` | Global-only JSON config |
| Augment | global | `~/.augment/settings.json` | Global-only JSON settings file |
| Codex CLI | global | `~/.codex/config.toml` | Renders JSON templates as TOML `mcp_servers` tables |

## Unsupported for Automatic Install

These editors are still supported by ai-toolkit for rules and instructions, but ai-toolkit does not currently auto-write MCP config because a stable official file target was not adopted:

| Editor | Reason |
|--------|--------|
| Roo Code | MCP support exists, but no verified official file path was adopted in ai-toolkit |
| Aider | No verified native MCP config surface was adopted in ai-toolkit |
| Google Antigravity | MCP can be configured via UI/import flows, but no stable file target was adopted in ai-toolkit |

## CLI

```bash
ai-toolkit mcp editors
ai-toolkit mcp install --editor cursor --scope project github --target .
ai-toolkit mcp install --editor codex context7
ai-toolkit mcp remove github --editor cursor --scope project --target .
```

## Install Flow Integration

When `.mcp.json` exists in a project, `ai-toolkit install --local` mirrors its servers into:
- `.claude/settings.local.json`
- `.cursor/mcp.json` when `--editors cursor` is selected
- `.github/mcp.json` when `--editors copilot` is selected

Global-only clients are configured explicitly via `ai-toolkit mcp install --editor ...`.

## Related

- [PATH: kb/reference/mcp-templates.md] — template catalog and CLI
- [PATH: kb/reference/extension-api.md] — extension API surface
