#!/usr/bin/env bash
# guard-config.sh — Block edits to linter/formatter config files unless explicitly requested.
#
# Fires on: PreToolUse (Edit|Write|MultiEdit)
# Exit 2 = block the tool call. Stderr message goes to Claude as feedback.

INPUT=$(cat)
# shellcheck source=_hook-io.sh
source "$(dirname "$0")/_hook-io.sh"
FILE_PATH=$(hook_file_path)

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

BASENAME=$(basename "$FILE_PATH")

# Protected config file patterns
BLOCKED=0
case "$BASENAME" in
    .eslintrc|.eslintrc.*|eslint.config.*)
        BLOCKED=1 ;;
    .prettierrc|.prettierrc.*|prettier.config.*)
        BLOCKED=1 ;;
    tsconfig.json|tsconfig.*.json)
        BLOCKED=1 ;;
    .stylelintrc|.stylelintrc.*)
        BLOCKED=1 ;;
    biome.json|biome.jsonc)
        BLOCKED=1 ;;
    ruff.toml)
        BLOCKED=1 ;;
    pyproject.toml)
        # Only block if editing [tool.ruff] section — check new_string/content for ruff markers
        CONTENT=$(hook_new_content)
        OLD=$(hook_old_content)
        if printf '%s\n%s' "$OLD" "$CONTENT" | grep -qi '\[tool\.ruff'; then
            BLOCKED=1
        fi
        ;;
esac

if [ "$BLOCKED" -eq 1 ]; then
    echo "Config file protection: ${BASENAME} is protected. Use explicit instruction to modify config files." >&2
    exit 2
fi

exit 0
