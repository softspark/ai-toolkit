#!/usr/bin/env bash
# session-end.sh — Persist a lightweight handoff note when a Claude session ends.
#
# Fires on: SessionEnd
# Matcher: all
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

STATE_DIR=".claude"
SESSION_FILE="$STATE_DIR/session-context.md"
HANDOFF_FILE="$STATE_DIR/session-end.md"
STAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date)"

mkdir -p "$STATE_DIR"

{
    echo "# Session End Snapshot"
    echo ""
    echo "- ended_at: $STAMP"
    if [ -f "$SESSION_FILE" ]; then
        echo "- session_context: present"
    else
        echo "- session_context: missing"
    fi
    echo "- next_start: re-read CLAUDE.md, open tasks, and validation state"
} > "$HANDOFF_FILE"

if [ -f "$SESSION_FILE" ]; then
    echo "SessionEnd: wrote .claude/session-end.md and preserved existing .claude/session-context.md for the next session."
else
    echo "SessionEnd: wrote .claude/session-end.md. Consider persisting open tasks in .claude/session-context.md before ending long workstreams."
fi

exit 0

