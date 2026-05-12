#!/usr/bin/env bash
# post-tool-use.sh — Lightweight feedback after file edits.
#
# Fires on: PostToolUse
# Matcher: Edit|MultiEdit|Write
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"
# shellcheck source=_locate-toolkit.sh
source "$(dirname "$0")/_locate-toolkit.sh"
# shellcheck source=_hook-io.sh
source "$(dirname "$0")/_hook-io.sh"

# Read from stdin (Claude Code passes JSON with .tool_name, .tool_input)
INPUT=$(cat)
TOOL_NAME=$(hook_tool_name)
[ -z "$TOOL_NAME" ] && TOOL_NAME="unknown"
FILE_PATH=$(hook_file_path)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)

# Append edit to session state (used by revert-guard, test-cohesion, quality-gate).
if [ -n "$FILE_PATH" ] && [ -n "$TOOLKIT_DIR" ] && command -v python3 >/dev/null 2>&1; then
    python3 "$TOOLKIT_DIR/scripts/session_state.py" append \
        --tool "$TOOL_NAME" --path "$FILE_PATH" \
        ${SESSION_ID:+--session-id "$SESSION_ID"} >/dev/null 2>&1 || true
fi

if [ -z "$FILE_PATH" ]; then
    hook_emit_context "PostToolUse: ${TOOL_NAME} completed. Consider validating lint, tests, and docs if behavior changed."
    exit 0
fi

case "$FILE_PATH" in
    *.md|*.txt)
        hook_emit_context "PostToolUse: updated ${FILE_PATH}. If behavior or workflow changed, refresh related docs and examples."
        ;;
    *.bats|*.test.*|*.spec.*)
        hook_emit_context "PostToolUse: updated test file ${FILE_PATH}. Run the most relevant targeted test command next."
        ;;
    *.json|*.yml|*.yaml|*.toml)
        hook_emit_context "PostToolUse: updated config file ${FILE_PATH}. Validate syntax and any generated artifacts affected by this change."
        ;;
    *)
        hook_emit_context "PostToolUse: updated ${FILE_PATH}. If behavior changed, run validation, targeted tests, and update docs if needed."
        ;;
esac

exit 0
