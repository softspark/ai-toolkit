# MCP Server Templates

Ready-to-use MCP (Model Context Protocol) server configurations for Claude Code and other AI assistants.

## What are these?

Each JSON file contains a preconfigured MCP server definition that can be merged into your `.mcp.json` (project-level) or `~/.claude/settings.json` (global). Templates use `${ENV_VAR}` placeholders for secrets -- set the corresponding environment variables before use.

## Quick start

### Via CLI (recommended)

```bash
# List all available templates
ai-toolkit mcp list

# Show details for a template
ai-toolkit mcp show github

# Add one or more servers to your project
ai-toolkit mcp add github fetch context7

# Add to a specific directory
ai-toolkit mcp add postgres --target /path/to/project

# Remove a server
ai-toolkit mcp remove github
```

### Manual copy

1. Open the template file (e.g., `github.json`)
2. Copy the `mcpServers` block
3. Merge it into your `.mcp.json` or `~/.claude/settings.json`

Example -- adding GitHub to `.mcp.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

## Available templates

| Template | Description |
|----------|-------------|
| `github` | GitHub API for issues, PRs, and repos |
| `filesystem` | Local file access |
| `memory` | Persistent memory via knowledge graph |
| `sequential-thinking` | Step-by-step reasoning |
| `postgres` | PostgreSQL database access |
| `sqlite` | SQLite database access |
| `brave-search` | Web search via Brave API |
| `puppeteer` | Browser automation |
| `slack` | Slack workspace integration |
| `google-drive` | Google Drive file management |
| `google-maps` | Google Maps geocoding and directions |
| `sentry` | Sentry error tracking |
| `git` | Git repository operations |
| `fetch` | HTTP fetch for web pages and APIs |
| `context7` | Up-to-date library documentation |
| `supabase` | Supabase project management |
| `linear` | Linear issue tracker |
| `notion` | Notion workspace integration |
| `redis` | Redis cache and data management |
| `docker` | Docker container management |
| `cloudflare` | Cloudflare Workers, KV, D1, R2 |
| `vercel` | Vercel deployments and settings |
| `datadog` | Datadog monitoring and metrics |
| `grafana` | Grafana dashboards and alerting |
| `custom-template` | Empty template for custom servers |

## Contributing a new template

1. Create `app/mcp-templates/<name>.json` following this structure:

```json
{
  "name": "<name>",
  "description": "Short description of what this server does",
  "mcpServers": {
    "<name>": {
      "command": "npx",
      "args": ["-y", "<npm-package-name>"],
      "env": {
        "API_KEY": "${ENV_VAR_NAME}"
      }
    }
  }
}
```

2. Use `${ENV_VAR}` syntax for any secrets or tokens
3. Keep the `name` field matching the filename (without `.json`)
4. Update this README table
5. Run `python3 scripts/validate.py` to verify
