---
title: "AI Toolkit - External Integrations"
category: reference
service: ai-toolkit
tags: [integrations, rules, add-rule]
version: "1.0.5"
created: "2026-03-26"
last_updated: "2026-03-26"
description: "How external repos inject rules into ~/.claude/CLAUDE.md via ai-toolkit"
---

# External Integrations

Repos that register rules with ai-toolkit so they are automatically injected into `~/.claude/CLAUDE.md` on every `update`.

---

## How to Register Rules

Use `add-rule` to register a rule file globally. Every subsequent `ai-toolkit update` picks it up automatically.

```bash
cd /path/to/your-repo
ai-toolkit add-rule ./jira-rules.md
ai-toolkit update   # inject now
```

After registration, `ai-toolkit update` will always re-inject the rule. Registry location: `~/.softspark/ai-toolkit/rules/`.

To unregister a rule (removes from `~/.softspark/ai-toolkit/rules/` and strips the block from `CLAUDE.md`):

```bash
ai-toolkit remove-rule jira-rules
```

---

## How It Works

Both mechanisms use marker-based idempotent injection. Rule name = filename without `.md`.

```
<!-- TOOLKIT:jira-rules START -->

...rule content...

<!-- TOOLKIT:jira-rules END -->
```

Content outside markers is never touched. Re-running updates only the marked block.

---

## Adding a New Integration

1. Create `<name>-rules.md` in your repo with Claude-relevant conventions
2. Register it: `ai-toolkit add-rule ./<name>-rules.md`
3. Verify it appears in: `~/.softspark/ai-toolkit/rules/<name>-rules.md`
4. On next `install` it will be listed in: `Rules injected: ... <name>-rules`
5. Add an entry below documenting the integration

---

## Known Integrations

### rag-mcp

**Rule file:** `rag-mcp.md`
**Marker:** `TOOLKIT:rag-mcp`

Teaches Claude Code the RAG-MCP search protocol: always call `smart_query()` before answering, `kb_id` vs `file_path` distinction, available MCP tools.

```bash
cd /path/to/rag-mcp
ai-toolkit add-rule ./rag-mcp-rules.md
```

### jira-mcp

**Rule file:** `jira-rules.md`
**Marker:** `TOOLKIT:jira-rules`

Teaches Claude Code the Jira MCP tool set: `sync_tasks`, `read_cached_tasks`, `update_task_status`, `log_task_time`, and key rules (sync first, hours only, check transitions).

```bash
cd /path/to/jira-mcp
ai-toolkit add-rule ./jira-rules.md
```
