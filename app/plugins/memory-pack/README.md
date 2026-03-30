# memory-pack

Persistent session memory with SQLite storage and full-text search.

## Includes
- Skills: `/mem-search` (FTS5 search across past sessions)
- Hooks: `observation-capture.sh` (PostToolUse), `session-summary.sh` (Stop)
- Scripts: `init_db.py` (database setup), `strip_private.py` (privacy filter)

## How It Works
1. **Capture**: Every tool use is recorded to `~/.ai-toolkit/memory.db` (PostToolUse hook)
2. **Summarize**: Session summary generated on each Stop hook (tools used, observation count, time range)
3. **Search**: `/mem-search <query>` runs FTS5 full-text search with progressive disclosure
4. **Privacy**: Content between `<private>...</private>` tags is stripped before storage

## Database Schema
- `sessions` — one row per Claude Code session (id, project_dir, started_at, ended_at, summary)
- `observations` — captured tool actions (session_id, tool_name, content, created_at)
- `observations_fts` — FTS5 virtual table for full-text search (auto-synced via triggers)

## Use When
- searching for past decisions, code changes, or debugging sessions,
- resuming work across sessions without losing context,
- reviewing what tools were used in a previous session.
