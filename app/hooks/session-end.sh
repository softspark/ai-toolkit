#!/usr/bin/env bash
# session-end.sh — Persist a lightweight handoff note when a Claude session ends.
#
# Fires on: SessionEnd
# Matcher: all
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"
# shellcheck source=_session-paths.sh
source "$(dirname "$0")/_session-paths.sh"

SESSION_FILE="$SESSION_CONTEXT_FILE"
HANDOFF_FILE="$SESSION_END_FILE"
STAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date)"

mkdir -p "$SESSION_DIR"

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
    echo "SessionEnd: wrote $HANDOFF_FILE and preserved existing session-context for the next session."
else
    echo "SessionEnd: wrote $HANDOFF_FILE. Consider persisting open tasks in the session-context file before ending long workstreams."
fi

exit 0

