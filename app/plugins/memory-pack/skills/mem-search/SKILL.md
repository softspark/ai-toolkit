---
name: mem-search
description: "Search past coding sessions using natural language. Finds relevant observations, decisions, and context from previous work."
effort: medium
argument-hint: "[search query]"
allowed-tools: Bash, Read
user-invocable: true
---

# Search Session Memory

Search the persistent memory database for past coding observations, decisions, and context.

$ARGUMENTS

## How It Works

This skill queries the SQLite FTS5 full-text search index at `~/.softspark/ai-toolkit/memory.db` to find relevant observations from past sessions.

## Instructions

1. **Parse the search query** from `$ARGUMENTS`. If empty, prompt the user for a query.

2. **Initialize the database** if it does not exist:
   ```bash
   python3 "$HOME/.softspark/ai-toolkit/hooks/../plugins/memory-pack/scripts/init_db.py" 2>/dev/null || true
   ```

3. **Run the FTS5 search** against the observations table:
   ```bash
   sqlite3 ~/.softspark/ai-toolkit/memory.db "
     SELECT o.id, o.session_id, o.tool_name, o.content, o.created_at,
            s.project_dir, s.summary
     FROM observations_fts fts
     JOIN observations o ON o.id = fts.rowid
     LEFT JOIN sessions s ON s.session_id = o.session_id
     WHERE observations_fts MATCH '<query>'
     ORDER BY rank
     LIMIT 10;
   "
   ```
   Replace `<query>` with the user's search terms. Escape single quotes by doubling them.

4. **Progressive disclosure** -- present results in two stages:

   **Stage 1: Summary view** (show first)
   ```markdown
   ## Memory Search: "<query>"

   Found N results across M sessions.

   | # | Session | Project | Tool | Time | Preview |
   |---|---------|---------|------|------|---------|
   | 1 | abc123  | /path   | Edit | 2025-01-15 | First 80 chars... |
   ```

   **Stage 2: Detail view** (on request)
   Show the full observation content, session summary, and related observations from the same session.

5. **If no results found**, suggest:
   - Trying broader search terms
   - Checking if memory-pack hooks are installed
   - Running `init-db.sh` if the database is missing

## Query Tips

- Use simple keywords: `mem-search database migration`
- FTS5 supports prefix matching: `migrat*` matches "migration", "migrate"
- Boolean operators: `database AND NOT test`
- Column filters: `tool_name:Edit` to search only Edit tool observations
