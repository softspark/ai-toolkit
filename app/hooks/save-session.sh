#!/usr/bin/env bash
# save-session.sh — Persist session context on stop for cross-session continuity.
#
# Fires on: Stop
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

# Read from stdin (Claude Code passes JSON with .session_id, .last_assistant_message)
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
LAST_MSG=$(echo "$INPUT" | jq -r '.last_assistant_message // "No summary available"' 2>/dev/null | head -5)

SESSION_FILE=".claude/session-context.md"

if [ -n "$SESSION_ID" ]; then
    mkdir -p .claude
    cat > "$SESSION_FILE" << EOF
# Session Context
Updated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Session: ${SESSION_ID}

## Last Assistant Message
${LAST_MSG}
EOF
fi

exit 0
