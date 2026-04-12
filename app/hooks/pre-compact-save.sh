#!/usr/bin/env bash
# pre-compact-save.sh — Save conversation context summary before compaction.
#
# Fires on: PreCompact
# Saves session metadata to timestamped file for audit trail.
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

SAVE_DIR="$HOME/.softspark/ai-toolkit/compactions"
mkdir -p "$SAVE_DIR"

# Read from stdin (Claude Code passes JSON with .session_id)
INPUT=$(cat)
TIMESTAMP=$(date -u +"%Y-%m-%d_%H-%M-%S")
SESSION=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[ -z "$SESSION" ] && SESSION="$$"
SAVE_FILE="$SAVE_DIR/${TIMESTAMP}_${SESSION}.txt"

# Gather context
SESSION="${CLAUDE_SESSION_ID:-unknown}"
WORKDIR="$(pwd)"
BRANCH=""
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
fi

cat > "$SAVE_FILE" << EOF
# Pre-Compaction Context
Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Session: ${SESSION}
Working Directory: ${WORKDIR}
Git Branch: ${BRANCH:-N/A}
EOF

exit 0
