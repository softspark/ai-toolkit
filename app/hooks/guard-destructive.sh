#!/usr/bin/env bash
# guard-destructive.sh — Block destructive bash commands.
#
# Fires on: PreToolUse (Bash)
# Exit 2 = block the command. Stderr message goes to Claude as feedback.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

if [ -z "$COMMAND" ]; then
    # Fallback: try CLAUDE_TOOL_INPUT env var
    COMMAND="$CLAUDE_TOOL_INPUT"
fi

# Normalize command for matching: collapse whitespace, strip backslash escapes
NORMALIZED=$(printf '%s' "$COMMAND" | tr -s '[:space:]' ' ' | sed 's/\\//g')

# Destructive patterns — word-boundary aware where possible
DESTRUCTIVE_PATTERNS=(
    # rm variants (short flags, long flags, separated flags, sudo, xargs/find piped)
    'rm\s+(-[rRf]{2,}|-r\s+-f|-f\s+-r)'
    'rm\s+--recursive'
    'rm\s+--force'
    'sudo\s+rm\b'
    'xargs\s+rm\b'
    '\|\s*xargs\s+rm\b'

    # find with destructive actions
    'find\s+.*-delete'
    'find\s+.*-exec\s+rm\b'

    # SQL destructive operations
    'DROP\s+(TABLE|DATABASE|SCHEMA|INDEX)'
    'TRUNCATE\s+'
    'DELETE\s+FROM\s+\S+\s*(;|$|WHERE\s+1)'

    # Disk/filesystem destructive
    'format\s+/'
    'dd\s+if='
    'mkfs\b'
    'shred\b'

    # Git destructive operations
    'git\s+push\s+(--force|-f)\b'
    'git\s+push\s+.*--force'
    'git\s+reset\s+--hard'
    'git\s+clean\s+-[a-zA-Z]*f'
    'git\s+branch\s+-D\b'

    # Permission nuking
    'chmod\s+(-R\s+)?777'
    'chmod\s+-R\s+000'

    # Container/infra destructive
    'docker\s+system\s+prune'
    'docker\s+rm\s+-f'
    'docker\s+rmi\s+-f'
    'kubectl\s+delete\s+(namespace|ns|all|node)'
    'terraform\s+destroy'

    # System-level destructive
    'systemctl\s+(stop|disable)\s+'
    '>\s*/dev/sd[a-z]'
)

# Build combined regex
REGEX=$(IFS='|'; echo "${DESTRUCTIVE_PATTERNS[*]}")

if echo "$NORMALIZED" | grep -qEi "($REGEX)"; then
    echo "WARNING: Potentially destructive command detected. Please verify." >&2
    exit 2
fi

exit 0
