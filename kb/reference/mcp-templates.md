---
title: "MCP Server Templates"
category: reference
service: ai-toolkit
tags: [mcp, templates, servers, configuration, editors]
version: "1.1.0"
created: "2026-04-07"
last_updated: "2026-04-12"
description: "Reference for 26 MCP server templates plus native editor MCP installation support."
---

# MCP Server Templates

## Overview

ai-toolkit ships 26 ready-to-use MCP server configuration templates in `app/mcp-templates/`. Each template is a JSON file that defines the canonical `mcpServers` block for a specific service. Templates can be merged into the project's `.mcp.json` and rendered into editor-native MCP config files via the `ai-toolkit mcp` CLI subcommand.

## CLI

```bash
ai-toolkit mcp list               # List all available templates
ai-toolkit mcp editors            # List editors with native MCP adapters
ai-toolkit mcp show <name>        # Print a template's JSON config
ai-toolkit mcp add <name>         # Merge a template into .mcp.json
ai-toolkit mcp add <n1> <n2>      # Add multiple templates at once
ai-toolkit mcp install --editor cursor --scope project github --target .
ai-toolkit mcp install --editor codex context7
ai-toolkit mcp remove <name>      # Remove from .mcp.json or native editor config
```

**Implementation:** `scripts/mcp_manager.py`

The `add` command merges the `mcpServers` block from the template into `.mcp.json`. If `.mcp.json` does not exist it is created. If the server name already exists in `.mcp.json`, the entry is overwritten with the template version.

The `install` command renders the same canonical template into an editor-native config format:
- JSON clients with `mcpServers` blocks: Claude Code, Cursor, Gemini CLI, Windsurf, Cline, Augment
- JSON clients with additional transport metadata: GitHub Copilot
- TOML clients: Codex CLI (`[mcp_servers.<name>]`)

When `install` runs with `--scope project`, ai-toolkit also updates the project's `.mcp.json` so it remains the source of truth for later syncs.

## Editor Support Matrix

| Editor | Scope | Native Config Path | Notes |
|--------|-------|--------------------|-------|
| `claude` | project + global | `.claude/settings.local.json`, `~/.claude/settings.json` | Preserves existing hooks and env keys |
| `cursor` | project + global | `.cursor/mcp.json`, `~/.cursor/mcp.json` | Mirrors canonical `mcpServers` |
| `copilot` | project + global | `.github/mcp.json`, `~/.copilot/mcp-config.json` | Adds `type` and `tools: ["*"]` automatically |
| `gemini` | project + global | `.gemini/settings.json`, `~/.gemini/settings.json` | Uses Gemini CLI `mcpServers` format |
| `windsurf` | global | `~/.codeium/windsurf/mcp_config.json` | Global-only official config |
| `cline` | global | `~/.cline/data/settings/cline_mcp_settings.json` | Global-only official config |
| `augment` | global | `~/.augment/settings.json` | Global-only settings file |
| `codex` | global | `~/.codex/config.toml` | Rendered as TOML `mcp_servers` tables |

Project-local `ai-toolkit install --local` also mirrors `.mcp.json` into Claude project settings plus selected project editors that have official repository/workspace MCP files (`cursor`, `copilot`).

## Template List

| Name | Description | Required Env Vars |
|------|-------------|-------------------|
| `brave-search` | Web and local search powered by Brave Search API | `BRAVE_API_KEY` |
| `cloudflare` | Cloudflare Workers, KV, D1, R2, and DNS management | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` |
| `context7` | Up-to-date library documentation lookup via Context7 | — |
| `custom-template` | Empty template for building a custom MCP server | `API_KEY` (placeholder) |
| `datadog` | Datadog monitoring: metrics, logs, traces, dashboard queries | `DD_API_KEY`, `DD_APP_KEY`, `DD_SITE` |
| `docker` | Docker container and image management, logs, compose operations | — |
| `fetch` | HTTP fetch for web pages and API responses as markdown or raw content | — |
| `filesystem` | Local filesystem access for reading, writing, and searching files | — |
| `git` | Git repository inspection: diffs, logs, branches | — |
| `github` | GitHub API: issues, PRs, repos, code search | `GITHUB_PERSONAL_ACCESS_TOKEN` |
| `google-drive` | Google Drive file search, reading, and management | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` |
| `google-maps` | Google Maps geocoding, directions, place search | `GOOGLE_MAPS_API_KEY` |
| `grafana` | Grafana dashboard queries, alerting, and data source management | `GRAFANA_URL`, `GRAFANA_API_KEY` |
| `linear` | Linear issue tracker: issues, projects, team workflows | `LINEAR_API_KEY` |
| `memory` | Persistent memory store using a local knowledge graph | — |
| `notion` | Notion workspace: pages, databases, content management | `NOTION_API_KEY` |
| `postgres` | PostgreSQL database access, schema inspection, analysis | — |
| `puppeteer` | Browser automation: screenshots, navigation, web scraping | — |
| `redis` | Redis cache inspection, data management, and monitoring | `REDIS_URL` |
| `sentry` | Sentry error tracking: issue search, event details, alerting | `SENTRY_AUTH_TOKEN`, `SENTRY_ORG` |
| `sequential-thinking` | Step-by-step reasoning and problem decomposition | — |
| `slack` | Slack workspace: channels, messages, users | `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID` |
| `sqlite` | SQLite database access, queries, schema management | — |
| `supabase` | Supabase project management, database queries, edge functions | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |
| `vercel` | Vercel deployment management, project settings, environment variables | `VERCEL_TOKEN` |

## Template Format

Each template is a JSON file with the following structure:

```json
{
  "name": "example",
  "description": "Human-readable description of what this server provides",
  "mcpServers": {
    "example": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-example"],
      "env": {
        "EXAMPLE_API_KEY": "${EXAMPLE_API_KEY}"
      }
    }
  }
}
```

- `name` — identifier used with `mcp add <name>`
- `description` — shown by `mcp list` and `mcp show`
- `mcpServers` — the block merged verbatim into `.mcp.json`
- `env` values use `${VAR_NAME}` placeholders that must be set in the shell environment or `.env` file before Claude Code starts

## Example: Adding GitHub and PostgreSQL

```bash
# Add templates
ai-toolkit mcp add github postgres

# Set required env vars (e.g., in .env or shell profile)
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...

# Resulting .mcp.json contains both mcpServers entries
```

## Contributing a New Template

1. Create `app/mcp-templates/<name>.json` following the format above.
2. Use `${ENV_VAR}` placeholders for secrets — never hardcode values.
3. Keep the `name` field identical to the filename stem.
4. Run `python3 scripts/validate.py` to verify the file is valid JSON.
5. Add an entry to this document's template list table.

## Related Documentation

- [PATH: kb/reference/extension-api.md] — `mcp add` as part of the extension API
- [PATH: kb/reference/architecture-overview.md] — overall install model
- [PATH: kb/reference/mcp-editor-compatibility.md] — native editor MCP support matrix
