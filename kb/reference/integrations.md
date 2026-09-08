---
title: "AI Toolkit - External Integrations"
category: reference
service: ai-toolkit
tags: [integrations, rules, add-rule]
version: "1.2.0"
created: "2026-03-26"
last_updated: "2026-09-08"
description: "How external repos register rules that ai-toolkit syncs into Claude Code user-level rules and other editor configs."
---

# External Integrations

Repos that register rules with ai-toolkit so they are automatically synced into Claude Code user-level rules and other editor configs on every `update`.

---

## How to Register Rules

Use `add-rule` to register a rule file globally. Every subsequent `ai-toolkit update` picks it up automatically.

```bash
cd /path/to/your-repo
ai-toolkit add-rule ./jira-rules.md
ai-toolkit update   # inject now
```

After registration, `ai-toolkit update` will always re-sync the rule. Registry location: `~/.softspark/ai-toolkit/rules/`.

For Claude Code, registered rules are written to `~/.claude/rules/ai-toolkit-registered-<name>.md`. The `ai-toolkit-*` prefix in `~/.claude/rules/` is installer-managed; use another prefix for hand-written Claude rules.

To unregister a rule (removes from `~/.softspark/ai-toolkit/rules/`, deletes the generated Claude rule file, and strips any legacy block from `CLAUDE.md`):

```bash
ai-toolkit remove-rule jira-rules
```

---

## How It Works

Claude Code uses file-based user-level rules:

```
~/.claude/rules/ai-toolkit-registered-jira-rules.md
```

Other editors receive the same registered rule through their native generated rule surfaces. Legacy `CLAUDE.md` marker sections are removed during migration, but content outside toolkit-managed markers is never touched.

---

## Adding a New Integration

1. Create `<name>-rules.md` in your repo with Claude-relevant conventions
2. Register it: `ai-toolkit add-rule ./<name>-rules.md`
3. Verify it appears in: `~/.softspark/ai-toolkit/rules/<name>-rules.md`
4. On next `install` it will be listed in: `Rules synced: ... <name>-rules`
5. Verify Claude receives it at: `~/.claude/rules/ai-toolkit-registered-<name>-rules.md`
6. Add an entry below documenting the integration

---

## Known Integrations

### rag-mcp

**Rule file:** `rag-mcp.md`
**Claude rule file:** `~/.claude/rules/ai-toolkit-registered-rag-mcp.md`

Teaches Claude Code the RAG-MCP search protocol: always call `smart_query()` before answering, `kb_id` vs `file_path` distinction, available MCP tools.

```bash
cd /path/to/rag-mcp
ai-toolkit add-rule ./rag-mcp-rules.md
```

### jira-mcp

**Rule file:** `jira-rules.md`
**Claude rule file:** `~/.claude/rules/ai-toolkit-registered-jira-rules.md`

Teaches Claude Code the Jira MCP tool set: `sync_tasks`, `read_cached_tasks`, `update_task_status`, `log_task_time`, and key rules (sync first, hours only, check transitions).

```bash
cd /path/to/jira-mcp
ai-toolkit add-rule ./jira-rules.md
```

## Autonomous delivery profile

`/autonomous-dev` can use the installed RAG and Jira connectors through an
explicit project profile. `issueTracker` identifies Jira tasks, `codeHost`
identifies the PR/CI repository and `knowledge` scopes technical KB retrieval.
The readonly config preflight validates local shape and canonical Jira task
identity; live tools remain responsible for freshness, language, transitions,
permissions and repository mapping.

The process carries a source-backed context in its hashed plan, reconciles Jira
comment receipts on retry and distinguishes a ready PR from Jira completion or
KB indexing. Connector credentials and instance routing stay in the connector's
own configuration. See [the autonomous delivery guide](../howto/autonomous-development.md)
and its shared stack contract for the maintained operational sequence.
