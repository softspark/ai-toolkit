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

# Extract commit message from -m flag. Delegated to Python for correct
# quote handling — the previous shell-regex approach broke on commit messages
# containing both " and '.
MSG=$(printf '%s' "$COMMAND" | python3 -c '
import re, sys
cmd = sys.stdin.read()
# Match -m followed by a quoted string (either " or ").
m = re.search(r"""-m\s+("((?:[^"\\]|\\.)*)"|'"'"'((?:[^'"'"'\\]|\\.)*)'"'"')""", cmd)
if m:
    print(m.group(2) if m.group(2) is not None else m.group(3))
' 2>/dev/null)

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
