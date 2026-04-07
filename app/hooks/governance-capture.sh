#!/usr/bin/env bash
# governance-capture.sh — Log security-sensitive operations to governance log.
#
# Fires on: PostToolUse
# Non-blocking: always exits 0 (logging only).
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

LOG_DIR="$HOME/.ai-toolkit"
LOG_FILE="$LOG_DIR/governance.log"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SESSION="${CLAUDE_SESSION_ID:-unknown}"

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)

if [ -z "$TOOL_NAME" ]; then
    TOOL_NAME="${CLAUDE_TOOL_NAME:-unknown}"
fi

log_event() {
    local EVENT="$1"
    local DETAIL="$2"
    mkdir -p "$LOG_DIR"
    if command -v jq >/dev/null 2>&1; then
        jq -nc --arg ts "$TIMESTAMP" --arg ev "$EVENT" --arg tl "$TOOL_NAME" --arg dt "$DETAIL" --arg ss "$SESSION" \
            '{"timestamp":$ts,"event":$ev,"tool":$tl,"detail":$dt,"session":$ss}' >> "$LOG_FILE"
    else
        # Escape double quotes in variable fields for basic JSON safety
        local SAFE_DETAIL="${DETAIL//\"/\\\"}"
        local SAFE_TOOL="${TOOL_NAME//\"/\\\"}"
        local SAFE_SESSION="${SESSION//\"/\\\"}"
        printf '{"timestamp":"%s","event":"%s","tool":"%s","detail":"%s","session":"%s"}\n' \
            "$TIMESTAMP" "$EVENT" "$SAFE_TOOL" "$SAFE_DETAIL" "$SAFE_SESSION" >> "$LOG_FILE"
    fi
}

case "$TOOL_NAME" in
    Bash)
        COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
        [ -z "$COMMAND" ] && exit 0

        # Check for dangerous command patterns
        if printf '%s' "$COMMAND" | grep -qEi 'rm\s+-rf'; then
            log_event "dangerous-command" "rm -rf"
        fi
        if printf '%s' "$COMMAND" | grep -qEi 'chmod\s+777'; then
            log_event "dangerous-command" "chmod 777"
        fi
        if printf '%s' "$COMMAND" | grep -qEi 'curl\s.*\|\s*bash'; then
            log_event "dangerous-command" "curl pipe bash"
        fi
        if printf '%s' "$COMMAND" | grep -qEi '\beval\b'; then
            log_event "dangerous-command" "eval"
        fi
        if printf '%s' "$COMMAND" | grep -qEi '\-\-no-verify'; then
            log_event "dangerous-command" "--no-verify"
        fi
        if printf '%s' "$COMMAND" | grep -qEi '(password|secret|token|api.key)='; then
            log_event "secrets-in-args" "possible credentials in command"
        fi
        ;;

    Write|Edit|MultiEdit)
        FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
        [ -z "$FILE_PATH" ] && exit 0

        BASENAME=$(basename "$FILE_PATH")
        MATCHED=""
        case "$BASENAME" in
            .env|.env.*) MATCHED=".env" ;;
            *credentials*) MATCHED="credentials file" ;;
            *secret*) MATCHED="secret file" ;;
            *.pem) MATCHED="PEM certificate" ;;
            *.key) MATCHED="private key" ;;
        esac

        if [ -n "$MATCHED" ]; then
            log_event "security-sensitive-file" "$FILE_PATH"
        fi
        ;;
esac

exit 0
