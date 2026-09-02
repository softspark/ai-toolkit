---
title: "AI Toolkit - MCP Editor Compatibility"
category: reference
service: ai-toolkit
tags: [mcp, editors, compatibility, codex, cursor, antigravity]
version: "1.4.0"
created: "2026-04-12"
last_updated: "2026-08-21"
description: "Official MCP support matrix and native config targets for editors supported by ai-toolkit."
---

# MCP Editor Compatibility

## Overview

ai-toolkit keeps `.mcp.json` as the project-level canonical template format and can render that config into native editor MCP files where the editor exposes a stable, documented configuration surface.

## Supported Native Adapters

| Editor | Scope | Native Config Path | Adapter Behavior |
|--------|-------|--------------------|------------------|
| Claude Code | project + global | `.mcp.json`, `~/.claude.json` | Merges `mcpServers` while preserving other top-level keys |
| Claude Chat / Cowork | global | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS), `%APPDATA%/Claude/claude_desktop_config.json` (Windows), `~/.config/Claude/claude_desktop_config.json` (Linux); `CLAUDE_USER_DATA_DIR` overrides the root | Emits the app's stdio-only `{command, args, env}` schema and bridges HTTP/SSE servers through `mcp-remote`; preserves `preferences`, `coworkUserFilesPath`, and user-owned servers |
| Cursor | project + global | `.cursor/mcp.json`, `~/.cursor/mcp.json` | Mirrors `mcpServers` directly |
| GitHub Copilot | project + global | `.github/mcp.json`, `$COPILOT_HOME/mcp-config.json` (default `~/.copilot/mcp-config.json`) | Adds Copilot-required `type` and `tools` fields |
| Gemini CLI | project + global | `.gemini/settings.json`, `~/.gemini/settings.json` | Merges `mcpServers` into settings JSON |
| Google Antigravity | project + global | `.agents/mcp_config.json`, `~/.gemini/config/mcp_config.json` | Emits current `command` or `serverUrl` transports; consumes portable `transport` metadata, normalizes legacy input `url` to `serverUrl`, rejects `httpUrl`, and preserves optional authentication, disablement, and tool-filter fields |
| Roo Code | project | `.roo/mcp.json` | Mirrors `mcpServers` into the documented project-level MCP file |
| Windsurf | global | `~/.codeium/windsurf/mcp_config.json` | Global-only JSON config |
| Cline | global | `~/.cline/data/settings/cline_mcp_settings.json` | Global-only JSON config |
| Augment | global | `~/.augment/settings.json` | Global-only JSON settings file |
| Codex CLI | project + global | `.codex/config.toml`, `$CODEX_HOME/config.toml` (default `~/.codex/config.toml`) | Renders validated TOML `mcp_servers` tables inside a managed block while preserving unrelated bytes and comments |

## Unsupported for Automatic Install

These editors are still supported by ai-toolkit for rules and instructions, but ai-toolkit does not currently auto-write MCP config because a stable official file target was not adopted:

| Editor | Reason |
|--------|--------|
| Aider | No verified native MCP config surface was adopted in ai-toolkit |

## CLI

```bash
ai-toolkit mcp editors
ai-toolkit mcp install --editor cursor --scope project github --target .
ai-toolkit mcp install --editor antigravity --scope project context7 --target .
ai-toolkit mcp install --editor codex --scope project context7 --target .
ai-toolkit mcp install --editor codex context7
ai-toolkit mcp install --editor claude-app --scope global context7
ai-toolkit mcp remove github --editor cursor --scope project --target .
```

## Claude Chat / Cowork

The Claude app is the one target whose MCP surface is file-based while everything
else about it is not. Skills, agents, hooks, and rules reach Chat/Cowork only
through the uploaded plugin ZIP (`ai-toolkit claude-app export`), because the app
scans no filesystem location for them. Local MCP servers are different: the app
parses `claude_desktop_config.json` on startup and reports invalid entries in its
own warning dialog.

Two constraints shape the adapter:

- **stdio only.** Each entry is validated as `{command, args, env}`. Remote
  endpoints live in a separate `remoteMcpServers` surface that the app manages
  through its Connectors UI and does not read from this file. Portable HTTP/SSE
  templates are therefore wrapped in `mcp-remote`, which negotiates the transport
  itself, so one bridge shape covers both spellings.
- **The file is not ours.** It also holds `preferences` and `coworkUserFilesPath`,
  which the app rewrites on its own. The adapter merges only `mcpServers` and
  leaves every other key untouched.

The app must be restarted for a config change to take effect.

## Install Flow Integration

When `.mcp.json` exists in a project, `ai-toolkit install --local` mirrors its servers into:
- `.claude/settings.local.json`
- `.cursor/mcp.json` when `--editors cursor` is selected
- `.github/mcp.json` when `--editors copilot` is selected
- `.agents/mcp_config.json` when `--editors antigravity` is selected
- `.roo/mcp.json` when `--editors roo` is selected
- `.codex/config.toml` when `--editors codex` is selected; project config is
  active only after the repository `.codex` layer is trusted

Codex project and user config preserve unrelated TOML text. ai-toolkit owns only
the marker-bounded MCP block it generates. Invalid TOML, unsupported transport
fields, and symlinked config roots are rejected without rewriting the file.
Portable `type` metadata is translated only when it matches the Codex transport:
`http` requires `url`, while `local` and `stdio` require `command`. The adapter
removes that metadata from native TOML and rejects SSE, unknown types, and
conflicting transport fields before writing.

Antigravity project and global configs preserve unrelated top-level keys and
user-owned servers. The adapter accepts both `serverUrl` and `url` for remote
servers, as documented by the Antigravity 2.1.4 changelog, but rejects the
unsupported legacy `httpUrl` field before any file in the transaction changes.

`CODEX_HOME` and `COPILOT_HOME` replace their editors' default user config
roots. They never relocate project files.

Global-only clients are configured explicitly via `ai-toolkit mcp install --editor ...`.

## Related

- [PATH: kb/reference/mcp-templates.md] — template catalog and CLI
- [PATH: kb/reference/extension-api.md] — extension API surface
