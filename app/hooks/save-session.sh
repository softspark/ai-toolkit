#!/usr/bin/env bash
# save-session.sh — Persist session context on stop for cross-session continuity.
#
# Fires on: Stop
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

SESSION_FILE=".claude/session-context.md"

if [ -n "${CLAUDE_SESSION_ID:-}" ]; then
    mkdir -p .claude
    cat > "$SESSION_FILE" << EOF
# Session Context
Updated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Session: ${CLAUDE_SESSION_ID:-unknown}

## Last Active Task
${CLAUDE_TASK_DESCRIPTION:-No task description available}
EOF
fi

exit 0
