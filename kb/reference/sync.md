---
title: "AI Toolkit - Config Sync"
category: reference
service: ai-toolkit
tags: [sync, gist, portability, config, backup]
version: "1.0.0"
created: "2026-03-29"
last_updated: "2026-03-29"
description: "Sync ai-toolkit config to/from GitHub Gist for cross-machine portability."
---

# Config Sync

## Overview

`ai-toolkit sync` exports and imports your toolkit configuration (rules, stats) via GitHub Gist or local files. Zero infrastructure — uses `gh` CLI for Gist operations.

## Commands

```bash
ai-toolkit sync --export              # JSON snapshot to stdout
ai-toolkit sync --push                # Create/update secret Gist
ai-toolkit sync --pull [gist-id]      # Pull from Gist and apply
ai-toolkit sync --import <file|url>   # Import from file or URL
```

## What Gets Synced

| Data | Included | Source |
|------|----------|--------|
| Custom rules | Yes | `~/.ai-toolkit/rules/*.md` |
| Usage stats | Yes | `~/.ai-toolkit/stats.json` |
| Toolkit version | Yes (metadata) | `package.json` |
| Agents/skills | No | Installed via `npm` |
| Hooks | No | Installed via `ai-toolkit install` |

## Workflow

### First machine (export)
```bash
ai-toolkit sync --push
# Creates secret Gist, saves ID to ~/.ai-toolkit/.gist-id
```

### Second machine (import)
```bash
ai-toolkit sync --pull abc123def456   # Use gist ID from first push
# Subsequent pulls: ai-toolkit sync --pull  (uses saved ID)
```

## Requirements

- `--export` / `--import`: No external dependencies
- `--push` / `--pull`: Requires [gh CLI](https://cli.github.com) + `gh auth login`

## JSON Schema

```json
{
  "schema_version": 1,
  "exported_at": "2026-03-29T14:00:00+00:00",
  "toolkit_version": "1.0.0",
  "rules": {
    "rule-name": "# Rule content..."
  },
  "stats": {
    "commit": { "count": 42, "last_used": "..." }
  }
}
```

## Security

- Gists are created as **secret** (not discoverable, but accessible via URL)
- Rules may contain project-specific instructions — review before sharing
- No credentials or tokens are stored in the snapshot
