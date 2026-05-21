#!/usr/bin/env bash
# session-start.sh — Inject mandatory rules reminder + session context on startup/compact.
#
# Fires on: SessionStart (startup|compact)
# Output goes to Claude's context as plain text.

# shellcheck source=_locate-toolkit.sh
source "$(dirname "$0")/_locate-toolkit.sh"

emit_context() {
    if [ "${AI_TOOLKIT_HOOK_QUIET:-0}" != "1" ]; then
        printf '%s\n' "$1"
    fi
}

# 1. Mandatory rules reminder
emit_context "MANDATORY: Before answering ANY technical question, apply ALL rules from your CLAUDE.md files (global + project). Follow the exact order of operations defined there. Do NOT skip mandatory steps even if you think you already know the answer."
emit_context "REMINDER: When writing features or fixing bugs, ensure tests cover the changes. When modifying API, config, or setup, update relevant documentation. Propose these steps to the user — do not silently skip them."

# 1a. Reset per-session edit state (used by revert-guard, test-cohesion, quality-gate)
SESSION_ID_INPUT=""
if [ ! -t 0 ]; then
    STDIN_PAYLOAD="$(cat)"
    SESSION_ID_INPUT="$(printf '%s' "$STDIN_PAYLOAD" | jq -r '.session_id // empty' 2>/dev/null)"
fi
if [ -n "$TOOLKIT_DIR" ] && command -v python3 >/dev/null 2>&1; then
    python3 "$TOOLKIT_DIR/scripts/session_state.py" reset \
        ${SESSION_ID_INPUT:+--session-id "$SESSION_ID_INPUT"} >/dev/null 2>&1 || true
fi

# 1b. GC stale per-session search-required flags (older than 60 min)
find "$HOME/.softspark/ai-toolkit/state" -maxdepth 1 -name 'search-required-*.flag' \
    -type f -mmin +60 -delete 2>/dev/null || true

# 2. Check for updates (cached, max once per 24h, non-blocking)
VERSION_MSG=$(python3 "$TOOLKIT_DIR/scripts/version_check.py" 2>/dev/null)
if [ -n "$VERSION_MSG" ]; then
    emit_context "$VERSION_MSG"
    # Strip shell/AppleScript/PowerShell metacharacters before interpolating into
    # notification commands. VERSION_MSG is version_check.py output which should
    # be plain ASCII, but sanitize anyway as defense in depth.
    VERSION_MSG_SAFE=$(printf '%s' "$VERSION_MSG" | LC_ALL=C tr -d '"'"'"'\\`$')
    # Desktop notification so user sees update before typing
    if command -v osascript >/dev/null 2>&1; then
        osascript -e "display notification \"$VERSION_MSG_SAFE\" with title \"ai-toolkit\"" 2>/dev/null &
    elif command -v notify-send >/dev/null 2>&1; then
        notify-send "ai-toolkit" "$VERSION_MSG_SAFE" 2>/dev/null &
    elif command -v powershell.exe >/dev/null 2>&1; then
        powershell.exe -Command "[void](New-Object -ComObject WScript.Shell).Popup('$VERSION_MSG_SAFE',5,'ai-toolkit',64)" 2>/dev/null &
    fi
fi

# 3. Load session context (if available)
SESSION_FILE=".claude/session-context.md"
if [ -f "$SESSION_FILE" ] && [ "${AI_TOOLKIT_HOOK_QUIET:-0}" != "1" ]; then
    printf '%s\n' "=== Session Context ==="
    cat "$SESSION_FILE"
    printf '%s\n' "====================="
fi

# 3. Load active instincts (if any)
INSTINCTS_DIR=".claude/instincts"
if [ -d "$INSTINCTS_DIR" ] && [ "${AI_TOOLKIT_HOOK_QUIET:-0}" != "1" ] && ls "$INSTINCTS_DIR"/*.md >/dev/null 2>&1; then
    printf '%s\n' "=== Active Instincts ==="
    for f in "$INSTINCTS_DIR"/*.md; do
        printf '%s\n' "- $(head -1 "$f")"
    done
    printf '%s\n' "========================"
fi

exit 0
