#!/usr/bin/env bash
# notify-waiting.sh — Cross-platform desktop notification when Claude is waiting.
#
# Fires on: Notification
# Non-blocking (always exits 0).

MSG="Claude Code needs your attention"
TITLE="Claude Code"

if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"$MSG\" with title \"$TITLE\"" 2>/dev/null &
elif command -v notify-send >/dev/null 2>&1; then
    notify-send "$TITLE" "$MSG" 2>/dev/null &
elif command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -Command "[void](New-Object -ComObject WScript.Shell).Popup('$MSG',5,'$TITLE',64)" 2>/dev/null &
fi

exit 0
