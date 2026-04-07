#!/usr/bin/env bash
# pre-compact-save.sh — Save conversation context summary before compaction.
#
# Fires on: PreCompact
# Saves session metadata to timestamped file for audit trail.
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

SAVE_DIR="$HOME/.ai-toolkit/compactions"
mkdir -p "$SAVE_DIR"

TIMESTAMP=$(date -u +"%Y-%m-%d_%H-%M-%S")
SESSION="${CLAUDE_SESSION_ID:-$$}"
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
