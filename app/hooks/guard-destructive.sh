#!/usr/bin/env bash
# guard-destructive.sh — Block destructive bash commands.
#
# Fires on: PreToolUse (Bash)
# Exit 2 = block the command. Stderr message goes to Claude as feedback.

# shellcheck disable=SC2034  # INPUT is consumed via sourced _hook-io.sh
INPUT=$(cat)
# shellcheck source=_hook-io.sh
source "$(dirname "$0")/_hook-io.sh"
COMMAND=$(hook_command)

if [ -z "$COMMAND" ]; then
    # Fallback: try CLAUDE_TOOL_INPUT env var
    COMMAND="$CLAUDE_TOOL_INPUT"
fi

# Normalize command for matching: collapse whitespace, strip backslash escapes
NORMALIZED=$(printf '%s' "$COMMAND" | tr -s '[:space:]' ' ' | sed 's/\\//g')

# Benign data contexts: a single, non-chained command whose program only PRINTS
# or RECORDS text (echo/printf) or writes a commit/tag message (git commit/tag)
# cannot itself execute a destructive op — the dangerous tokens are data, not
# actions. Skip matching so "git commit -m 'fix DROP TABLE race'" is not blocked.
# Bail out of the allowlist when a command separator is present (&&, ||, ;, |) so
# chained commands like `git commit -m x && rm -rf /tmp` are still inspected.
if ! printf '%s' "$NORMALIZED" | grep -qE '(&&|\|\||;|\|)'; then
    if printf '%s' "$NORMALIZED" | grep -qE '^[[:space:]]*(echo|printf|git[[:space:]]+(commit|tag))([[:space:]]|$)'; then
        exit 0
    fi
fi

# Safe git force variants (--force-with-lease / --force-if-includes) are the
# recommended way to force-push without clobbering others' work. Strip them
# before matching so they do not trip the broad --force patterns; a bare
# --force or -f left behind still blocks.
SAFE_STRIPPED=$(printf '%s' "$NORMALIZED" | sed -E 's/--force-with-lease(=[^ ]*)?//g; s/--force-if-includes//g')

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

if echo "$SAFE_STRIPPED" | grep -qEi "($REGEX)"; then
    echo "WARNING: Potentially destructive command detected. Please verify." >&2
    exit 2
fi

exit 0
