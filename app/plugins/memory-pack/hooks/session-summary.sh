#!/usr/bin/env bash
# session-summary.sh — Summarize session observations on stop.
#
# Fires on: Stop
# Queries all observations for the current session, builds a compact summary
# (observation count, tools used, time range), and stores it in the sessions table.
# Auto-prunes observations older than RETENTION_DAYS (default 90).
# Never blocks the user — always exits 0.

DB_PATH="${HOME}/.ai-toolkit/memory.db"
RETENTION_DAYS="${MEMORY_RETENTION_DAYS:-90}"

# Read JSON input from stdin (Claude Code hook protocol)
INPUT=$(cat)

# Parse session ID from stdin JSON, fall back to env var
if command -v jq &>/dev/null && [ -n "$INPUT" ]; then
    SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty')
fi
SESSION_ID="${SESSION_ID:-${CLAUDE_SESSION_ID:-}}"

# Bail silently if database or session ID missing
if [ ! -f "$DB_PATH" ] || [ -z "$SESSION_ID" ]; then
    exit 0
fi

# Escape session ID for SQL
SAFE_SESSION_ID=$(printf '%s' "$SESSION_ID" | sed "s/'/''/g")

# Count observations for this session
OBS_COUNT=$(sqlite3 "$DB_PATH" \
    "SELECT COUNT(*) FROM observations WHERE session_id = '${SAFE_SESSION_ID}';" 2>/dev/null || echo "0")

# No observations — nothing to summarize
if [ "$OBS_COUNT" -eq 0 ] 2>/dev/null; then
    exit 0
fi

# Gather distinct tools used
TOOLS_USED=$(sqlite3 "$DB_PATH" \
    "SELECT GROUP_CONCAT(tool_name, ', ')
     FROM (SELECT DISTINCT tool_name FROM observations
           WHERE session_id = '${SAFE_SESSION_ID}' ORDER BY tool_name);" 2>/dev/null || echo "unknown")

# Get time range
FIRST_OBS=$(sqlite3 "$DB_PATH" \
    "SELECT MIN(created_at) FROM observations WHERE session_id = '${SAFE_SESSION_ID}';" 2>/dev/null || echo "")
LAST_OBS=$(sqlite3 "$DB_PATH" \
    "SELECT MAX(created_at) FROM observations WHERE session_id = '${SAFE_SESSION_ID}';" 2>/dev/null || echo "")

# Build summary text
SUMMARY="Session captured ${OBS_COUNT} observations. Tools: ${TOOLS_USED}. Time range: ${FIRST_OBS} to ${LAST_OBS}."

# Escape summary for SQL
SAFE_SUMMARY=$(printf '%s' "$SUMMARY" | sed "s/'/''/g")

# Update session with summary and end time
sqlite3 "$DB_PATH" \
    "UPDATE sessions
     SET summary = '${SAFE_SUMMARY}',
         ended_at = datetime('now')
     WHERE session_id = '${SAFE_SESSION_ID}';" 2>/dev/null || true

# Auto-prune old observations and empty sessions
sqlite3 "$DB_PATH" \
    "DELETE FROM observations WHERE created_at < datetime('now', '-${RETENTION_DAYS} days');
     DELETE FROM sessions WHERE session_id NOT IN (SELECT DISTINCT session_id FROM observations)
       AND ended_at IS NOT NULL;
     VACUUM;" 2>/dev/null || true

exit 0
