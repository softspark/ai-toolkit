#!/usr/bin/env bash
# commit-quality.sh — Advisory commit message quality check.
#
# Fires on: PreToolUse (Bash)
# Non-blocking: always exits 0 (warnings only).

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

if [ -z "$COMMAND" ]; then
    exit 0
fi

# Only check commands that contain "git commit"
printf '%s' "$COMMAND" | grep -q 'git commit' || exit 0

# Extract commit message from -m flag
# Handles: git commit -m "msg", git commit -m 'msg', git commit -am "msg"
MSG=$(printf '%s' "$COMMAND" | grep -oE '\-m\s+["'"'"']([^"'"'"']*)["'"'"']' | head -1 | sed "s/^-m[[:space:]]*[\"']//" | sed "s/[\"']$//")

# Also handle heredoc-style: -m "$(cat <<'EOF' ... EOF )"
if [ -z "$MSG" ]; then
    MSG=$(printf '%s' "$COMMAND" | grep -oE '\-m\s+"[^"]*"' | head -1 | sed 's/^-m[[:space:]]*//' | tr -d '"')
fi

# No message found (might be --amend or interactive) — skip
if [ -z "$MSG" ]; then
    exit 0
fi

WARNINGS=""

# Check message length (first line only)
FIRST_LINE=$(printf '%s' "$MSG" | head -1)
if [ ${#FIRST_LINE} -lt 10 ]; then
    WARNINGS="${WARNINGS}\n- Commit message is very short (${#FIRST_LINE} chars). Aim for >10 characters."
fi

# Check for conventional commits prefix
if ! printf '%s' "$FIRST_LINE" | grep -qE '^(feat|fix|docs|refactor|test|chore|style|perf|ci|build|revert)(\(.+\))?:'; then
    WARNINGS="${WARNINGS}\n- Missing conventional commit prefix (feat:|fix:|docs:|refactor:|test:|chore:|style:|perf:|ci:|build:|revert:)."
fi

# Check for WIP/temp markers
if printf '%s' "$FIRST_LINE" | grep -qEi '\b(WIP|temp|tmp|fixme|todo)\b'; then
    WARNINGS="${WARNINGS}\n- Commit message contains WIP/temp marker. Consider a more descriptive message."
fi

if [ -n "$WARNINGS" ]; then
    printf 'Commit quality advisory:%b\n' "$WARNINGS"
fi

exit 0
