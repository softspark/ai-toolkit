#!/usr/bin/env bash
# session-end.sh — Persist a lightweight handoff note when a Claude session ends.
#
# Fires on: SessionEnd
# Matcher: all
# The handoff snapshot is skipped for the minimal profile. Owned recovery
# cleanup still runs for every profile.

# shellcheck source=_session-paths.sh
source "$(dirname "$0")/_session-paths.sh"
# shellcheck source=_hook-io.sh
source "$(dirname "$0")/_hook-io.sh"

# Cleanup must run before _profile-check.sh can exit for the minimal profile.
INPUT=""
if [ ! -t 0 ]; then
    # shellcheck disable=SC2034  # INPUT is consumed via sourced _hook-io.sh
    INPUT=$(cat)
fi
SESSION_ID=$(hook_session_id)
RECOVERY_ROOT="$SESSION_DIR/output-filter"
OUTPUT_FILTER_CLI="${AI_TOOLKIT_OUTPUT_FILTER_CLI:-$HOME/.softspark/ai-toolkit/scripts/output_filter_cli.py}"
if [ "$SESSION_ID" != "default" ] &&
   [ -d "$RECOVERY_ROOT" ] &&
   [ ! -L "$RECOVERY_ROOT" ] &&
   [ -f "$OUTPUT_FILTER_CLI" ] &&
   [ ! -L "$OUTPUT_FILTER_CLI" ] &&
   command -v python3 >/dev/null 2>&1; then
    python3 -S "$OUTPUT_FILTER_CLI" clean \
        --base-directory "$SESSION_DIR" \
        --session-id "$SESSION_ID" >/dev/null 2>&1 || true
fi

SESSION_STATE_CLI="${AI_TOOLKIT_SESSION_STATE_CLI:-$HOME/.softspark/ai-toolkit/scripts/session_state.py}"
if [ "$SESSION_ID" != "default" ] &&
   [ -f "$SESSION_STATE_CLI" ] &&
   [ ! -L "$SESSION_STATE_CLI" ] &&
   command -v python3 >/dev/null 2>&1; then
    python3 -S "$SESSION_STATE_CLI" clean \
        --session-id "$SESSION_ID" >/dev/null 2>&1 || true
fi

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

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
