#!/usr/bin/env bash
# loop-guard.sh — Advisory detection of repeated identical actions (stuck loops).
#
# Fires on: PostToolUse (Bash|Edit|MultiEdit|Write)
# Never blocks. Emits an advisory when the SAME tool action repeats at least
# THRESHOLD times within a short window — catching successful-but-identical
# loops that the /repeat circuit breaker (which only counts FAILURES) misses.
# Skipped in minimal profile; honours AI_TOOLKIT_DISABLED_HOOKS.
#
# Tunables: AI_TOOLKIT_LOOP_WINDOW (default 6), AI_TOOLKIT_LOOP_THRESHOLD (3).

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"
# shellcheck source=_hook-io.sh
source "$(dirname "$0")/_hook-io.sh"

INPUT=$(cat)
TOOL_NAME=$(hook_tool_name)
[ -z "$TOOL_NAME" ] && exit 0

# Build an identity for the action. For Bash it is the command; for edits it is
# file + new content, so normal iterative editing of one file does NOT trip the
# guard — only re-applying an IDENTICAL change does.
CMD=$(hook_command)
if [ -n "$CMD" ]; then
    IDENT="$CMD"
else
    FILE=$(hook_file_path)
    [ -z "$FILE" ] && exit 0
    IDENT="${FILE}::$(hook_new_content)"
fi

SID=$(hook_session_id)
STATE_DIR="${HOME}/.softspark/ai-toolkit/sessions"
mkdir -p "$STATE_DIR" 2>/dev/null || exit 0
LOG="${STATE_DIR}/${SID}-actions.log"

WINDOW="${AI_TOOLKIT_LOOP_WINDOW:-6}"
THRESHOLD="${AI_TOOLKIT_LOOP_THRESHOLD:-3}"

# Store only a short hash of "tool|identity" — never the raw payload.
HASH=$(printf '%s|%s' "$TOOL_NAME" "$IDENT" | { shasum -a 256 2>/dev/null || sha256sum 2>/dev/null; } | cut -c1-16)
[ -z "$HASH" ] && exit 0
printf '%s\n' "$HASH" >> "$LOG" 2>/dev/null || exit 0

# Keep only the last WINDOW entries so the file stays tiny.
lines=$(wc -l < "$LOG" 2>/dev/null | tr -d ' ')
if [ -n "$lines" ] && [ "$lines" -gt "$WINDOW" ]; then
    tail -n "$WINDOW" "$LOG" > "${LOG}.tmp" 2>/dev/null && mv "${LOG}.tmp" "$LOG" 2>/dev/null
fi

COUNT=$(grep -cxF "$HASH" "$LOG" 2>/dev/null | tr -d ' ')
[ -z "$COUNT" ] && COUNT=0
if [ "$COUNT" -ge "$THRESHOLD" ]; then
    AI_TOOLKIT_HOOK_FORMAT=json
    hook_emit_context "PostToolUse" \
        "Loop guard: the same ${TOOL_NAME} action has repeated ${COUNT}x within the last ${WINDOW} steps. If you are not making progress, stop and reassess — try a different approach or ask the user — instead of retrying the identical action."
fi
exit 0
