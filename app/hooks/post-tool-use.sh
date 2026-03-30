#!/usr/bin/env bash
# post-tool-use.sh — Lightweight feedback after file edits.
#
# Fires on: PostToolUse
# Matcher: Edit|MultiEdit|Write
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

FILE_PATH="${CLAUDE_TOOL_INPUT_FILE_PATH:-}"
TOOL_NAME="${CLAUDE_TOOL_NAME:-unknown}"

if [ -z "$FILE_PATH" ]; then
    echo "PostToolUse: ${TOOL_NAME} completed. Consider validating lint, tests, and docs if behavior changed."
    exit 0
fi

case "$FILE_PATH" in
    *.md|*.txt)
        echo "PostToolUse: updated ${FILE_PATH}. If behavior or workflow changed, refresh related docs and examples."
        ;;
    *.bats|*.test.*|*.spec.*)
        echo "PostToolUse: updated test file ${FILE_PATH}. Run the most relevant targeted test command next."
        ;;
    *.json|*.yml|*.yaml|*.toml)
        echo "PostToolUse: updated config file ${FILE_PATH}. Validate syntax and any generated artifacts affected by this change."
        ;;
    *)
        echo "PostToolUse: updated ${FILE_PATH}. If behavior changed, run validation, targeted tests, and update docs if needed."
        ;;
esac

exit 0

