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

## Example

```bash
/mem-search "postgres migration rollback"
```

Typical output:

```
## Memory Search: "postgres migration rollback"
Found 3 results across 2 sessions.

| # | Session | Project          | Tool | Time       | Preview                              |
|---|---------|------------------|------|------------|--------------------------------------|
| 1 | abc123  | magento2-os      | Edit | 2026-03-12 | Rolled back 0042_add_tax_col...      |
| 2 | def456  | magento2-b2b     | Bash | 2026-02-28 | pg_dump before schema migration...   |
| 3 | abc123  | magento2-os      | Read | 2026-03-12 | Reviewed migration safety checklist  |
```

## Rules

- **MUST** escape single quotes in queries by doubling (`it''s`) — SQL injection into the FTS5 call will break the query
- **NEVER** return the raw database path — treat `~/.softspark/ai-toolkit/memory.db` as internal
- **CRITICAL**: if the database does not exist, initialize it silently and return zero results — do not fail the skill
- **MANDATORY**: present Stage 1 (summary table) first; only expand to Stage 2 on follow-up

## Gotchas

- FTS5 `MATCH` is picky: hyphens, slashes, and dots are parsed as operator separators and will reject queries like `mem-search api/v1` with a cryptic `malformed MATCH expression`. Wrap multi-token phrases with double-quotes: `"api/v1"` or `"mem-search"`.
- Results are ordered by `rank` (FTS5 relevance), **not** by `created_at`. A stale but high-ranked match outranks a fresh but weak one — include the `created_at` column and consider `ORDER BY rank, created_at DESC` for time-sensitive queries.
- The database path is static at `~/.softspark/ai-toolkit/memory.db`. If the user runs from a container, `~` resolves to the container's home, not the host's — the observation list will look empty. Check the env var `SOFTSPARK_HOME` before assuming the DB is missing.
- `observations_fts` is a separate virtual table; when observations are deleted directly (not via the SDK) the FTS index can drift. If counts between `observations` and `observations_fts` differ, rebuild with `INSERT INTO observations_fts(observations_fts) VALUES('rebuild');`.

## When NOT to Use

- To search the KB or documentation — use `/search` or `smart_query()`
- To find a specific commit — use `git log --grep` or `/git-mastery`
- To list agent tasks — use `TaskList` or `/plan`
- When memory-pack hooks are not installed — direct the user to install them first
