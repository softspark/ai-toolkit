#!/usr/bin/env bash
# instructions-audit.sh — Log which CLAUDE.md / rules / skills loaded.
#
# Fires on: InstructionsLoaded
# Matcher: all
# Non-blocking: always exits 0.
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.
#
# Provides an audit trail so we can see whether a CLAUDE.md rule actually
# entered the agent's context (vs. silently dropped due to token budget,
# nested include limits, or path-glob misses).
#
# Output: ~/.softspark/ai-toolkit/state/loaded-instructions.log
# Schema: ISO-8601 ts \t memory_type \t load_reason \t file_path

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

INPUT=$(cat 2>/dev/null)
[ -z "$INPUT" ] && exit 0

FILE_PATH=$(echo "$INPUT" | jq -r '.file_path // empty' 2>/dev/null)
MEMORY_TYPE=$(echo "$INPUT" | jq -r '.memory_type // "unknown"' 2>/dev/null)
LOAD_REASON=$(echo "$INPUT" | jq -r '.load_reason // "unknown"' 2>/dev/null)

[ -z "$FILE_PATH" ] && exit 0

LOG_DIR="$HOME/.softspark/ai-toolkit/state"
LOG_FILE="$LOG_DIR/loaded-instructions.log"
mkdir -p "$LOG_DIR" 2>/dev/null || exit 0

TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
printf '%s\t%s\t%s\t%s\n' "$TS" "$MEMORY_TYPE" "$LOAD_REASON" "$FILE_PATH" >> "$LOG_FILE"

# Cap log at 2000 lines to avoid unbounded growth.
if [ -f "$LOG_FILE" ]; then
    line_count=$(wc -l < "$LOG_FILE" 2>/dev/null | tr -d ' ')
    if [ -n "$line_count" ] && [ "$line_count" -gt 2000 ]; then
        tail -1500 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
    fi
fi

exit 0
