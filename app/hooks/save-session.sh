#!/usr/bin/env bash
# save-session.sh — Persist session context on stop for cross-session continuity.
#
# Fires on: Stop
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"
# shellcheck source=_session-paths.sh
source "$(dirname "$0")/_session-paths.sh"
# shellcheck source=_hook-io.sh
source "$(dirname "$0")/_hook-io.sh"

# Read from stdin (Claude Code passes JSON with .session_id, .last_assistant_message)
INPUT=$(cat)
SESSION_ID=$(hook_session_id)
LAST_MSG=$(echo "$INPUT" | jq -r '.last_assistant_message // "No summary available"' 2>/dev/null | head -5)

SESSION_FILE="$SESSION_CONTEXT_FILE"

if [ "$SESSION_ID" != "default" ]; then
    mkdir -p "$SESSION_DIR"

    # Gather git state for richer context
    GIT_BRANCH=""
    GIT_DIRTY="0"
    GIT_DIFF_STAT=""
    if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
        GIT_DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
        GIT_DIFF_STAT=$(git diff --stat HEAD 2>/dev/null | tail -5)
    fi

    cat > "$SESSION_FILE" << EOF
# Session Context
Updated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Session: ${SESSION_ID}

## Last Assistant Message
${LAST_MSG}

## Git State
Branch: ${GIT_BRANCH:-N/A}
Uncommitted changes: ${GIT_DIRTY}
${GIT_DIFF_STAT:+${GIT_DIFF_STAT}}
EOF

    # Preserve any agent-written checkpoints (appended by proactive checkpointing)
    if [ -f "${SESSION_FILE}.checkpoints" ]; then
        echo "" >> "$SESSION_FILE"
        cat "${SESSION_FILE}.checkpoints" >> "$SESSION_FILE"
    fi
fi

exit 0
