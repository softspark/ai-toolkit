#!/usr/bin/env bash
# session-start.sh — Inject mandatory rules reminder + session context on startup/compact.
#
# Fires on: SessionStart (startup|compact)
# Output goes to Claude's context as plain text.

# 1. Mandatory rules reminder
echo "MANDATORY: Before answering ANY technical question, apply ALL rules from your CLAUDE.md files (global + project). Follow the exact order of operations defined there. Do NOT skip mandatory steps even if you think you already know the answer."
echo "REMINDER: When writing features or fixing bugs, ensure tests cover the changes. When modifying API, config, or setup, update relevant documentation. Propose these steps to the user — do not silently skip them."

# 2. Check for updates (cached, max once per 24h, non-blocking)
TOOLKIT_DIR="$(npm root -g 2>/dev/null)/@softspark/ai-toolkit"
[ ! -d "$TOOLKIT_DIR" ] && TOOLKIT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION_MSG=$(python3 "$TOOLKIT_DIR/scripts/version_check.py" 2>/dev/null)
if [ -n "$VERSION_MSG" ]; then
    echo "$VERSION_MSG"
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
if [ -f "$SESSION_FILE" ]; then
    echo "=== Session Context ==="
    cat "$SESSION_FILE"
    echo "====================="
fi

# 3. Load active instincts (if any)
INSTINCTS_DIR=".claude/instincts"
if [ -d "$INSTINCTS_DIR" ] && ls "$INSTINCTS_DIR"/*.md >/dev/null 2>&1; then
    echo "=== Active Instincts ==="
    for f in "$INSTINCTS_DIR"/*.md; do
        echo "- $(head -1 "$f")"
    done
    echo "========================"
fi

exit 0
