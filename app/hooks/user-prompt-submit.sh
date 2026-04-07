#!/usr/bin/env bash
# user-prompt-submit.sh — Lightweight prompt governance reminder before execution.
#
# Fires on: UserPromptSubmit
# Matcher: all
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

# Read prompt from stdin (Claude Code passes JSON with .prompt field)
INPUT=$(cat)
PROMPT_TEXT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
LOWERED="$(printf '%s' "$PROMPT_TEXT" | tr '[:upper:]' '[:lower:]')"

echo "STOP. Execute Step 0 before responding: check your CLAUDE.md for search-first rules. If search-first rules exist, call the required search tool NOW — before any other tool or text output. If you skip this step, the user will interrupt you."

if printf '%s' "$LOWERED" | grep -Eq 'architecture|design|migration|deploy|rollback|refactor|plugin|workflow'; then
    echo "UserPromptSubmit: task looks architectural or multi-step. Use plan mode, define success criteria, and validate before marking done."
elif printf '%s' "$LOWERED" | grep -Eq 'bug|error|fail|failing|incident|outage|debug'; then
    echo "UserPromptSubmit: debugging request detected. Gather evidence first, then propose the smallest safe fix and targeted tests."
else
    echo "UserPromptSubmit: apply KB-first research, keep changes minimal, and update tests/docs when behavior changes."
fi

exit 0

