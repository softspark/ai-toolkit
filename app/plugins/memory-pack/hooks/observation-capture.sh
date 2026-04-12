#!/usr/bin/env bash
# observation-capture.sh — Capture tool actions into SQLite memory database.
#
# Fires on: PostToolUse
# Reads tool name and result from JSON on stdin (Claude Code hook protocol).
# Strips private tags, truncates to 2000 chars, inserts into observations table.
# Never blocks the user — always exits 0.

DB_PATH="${HOME}/.softspark/ai-toolkit/memory.db"
STRIP_PRIVATE="${HOME}/.softspark/ai-toolkit/plugin-scripts/memory-pack/strip_private.py"
MAX_CONTENT_LENGTH=2000

# Bail silently if database does not exist
if [ ! -f "$DB_PATH" ]; then
    exit 0
fi

# Read JSON input from stdin (Claude Code hook protocol)
INPUT=$(cat)

# Check if jq is available; bail silently if not
if ! command -v jq &>/dev/null; then
    exit 0
fi

# Parse hook input
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty')
TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // "unknown"')
FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty')
TOOL_INPUT=$(printf '%s' "$INPUT" | jq -r '.tool_input | if type == "object" then (to_entries | map(.key + "=" + (.value | tostring)) | join(", ")) else tostring end // empty' 2>/dev/null)

# No session ID means we cannot associate the observation
if [ -z "$SESSION_ID" ]; then
    exit 0
fi

# Build content string
CONTENT=""
if [ -n "$FILE_PATH" ]; then
    CONTENT="${TOOL_NAME}: ${FILE_PATH}"
elif [ -n "$TOOL_INPUT" ]; then
    CONTENT="${TOOL_NAME}: ${TOOL_INPUT}"
else
    CONTENT="${TOOL_NAME}: (no input captured)"
fi

# Strip private content
if [ -f "$STRIP_PRIVATE" ]; then
    CONTENT=$(printf '%s' "$CONTENT" | python3 "$STRIP_PRIVATE")
fi

# Truncate to max length
if [ ${#CONTENT} -gt $MAX_CONTENT_LENGTH ]; then
    CONTENT="${CONTENT:0:$MAX_CONTENT_LENGTH}..."
fi

# Ensure session row exists (upsert — ignore if already present)
sqlite3 "$DB_PATH" "INSERT OR IGNORE INTO sessions (session_id, project_dir, started_at)
  VALUES ('$(printf '%s' "$SESSION_ID" | sed "s/'/''/g")', '$(pwd)', datetime('now'));" 2>/dev/null || true

# Insert observation
sqlite3 "$DB_PATH" "INSERT INTO observations (session_id, tool_name, content)
  VALUES ('$(printf '%s' "$SESSION_ID" | sed "s/'/''/g")',
          '$(printf '%s' "$TOOL_NAME" | sed "s/'/''/g")',
          '$(printf '%s' "$CONTENT" | sed "s/'/''/g")');" 2>/dev/null || true

exit 0
