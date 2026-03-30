#!/usr/bin/env bash
# guard-path.sh — Prevent Claude from guessing/hallucinating user home directory paths.
#
# Fires on: PreToolUse (Bash|Read|Edit|Write|MultiEdit|Glob|Grep|NotebookEdit|mcp__filesystem__.*)
# Exit 2 = block the tool call. Stderr message goes to Claude as feedback.
#
# Problem: Claude sometimes confuses similar usernames (e.g. "bartlomiejsz" vs
# "bartlomszsz") when constructing absolute paths, especially with non-ASCII names.
# This hook detects when a path contains /Users/ or /home/ but does NOT match
# the actual $HOME, and blocks the call before it fails or hits the wrong location.

INPUT=$(cat)
REAL_HOME="$HOME"

# Verify jq is available — required for JSON parsing
if ! command -v jq >/dev/null 2>&1; then
    echo "WARNING: guard-path.sh requires jq but it is not installed. Path validation skipped." >&2
    exit 0
fi

# Collect ALL path values from tool input into a single list (one per line).
# Covers: Read/Edit/Write (file_path), Glob/Grep/mcp__filesystem (path),
#         mcp__filesystem__move_file (source, destination),
#         mcp__filesystem__read_multiple_files (paths[]), Bash (command)
ALL_PATHS=$(echo "$INPUT" | jq -r '
    [
        .tool_input.file_path,
        .tool_input.path,
        .tool_input.source,
        .tool_input.destination,
        .tool_input.command,
        (.tool_input.paths[]? // empty)
    ] | map(select(. != null and . != "")) | .[]
' 2>/dev/null)

if [ -z "$ALL_PATHS" ]; then
    exit 0
fi

REAL_USER=$(basename "$REAL_HOME")

# block_wrong_user — print error to stderr and exit 2 (blocks the tool call)
block_wrong_user() {
    echo "BLOCKED: Path contains wrong username '${1}' — actual user is '${REAL_USER}'." >&2
    echo "Use \$HOME or ~ prefix, or the correct username '${REAL_USER}' in absolute paths." >&2
    echo "Do NOT guess usernames. Run 'echo \$HOME' if unsure." >&2
    exit 2
}

# check_single_path — validate one absolute path
check_single_path() {
    local P="$1"
    echo "$P" | grep -qE '^/(Users|home)/' || return 0
    local PATH_USER
    PATH_USER=$(echo "$P" | sed 's|^/Users/||;s|^/home/||' | cut -d'/' -f1)
    [ "$PATH_USER" != "$REAL_USER" ] && block_wrong_user "$PATH_USER"
}

# Iterate without subshell (process substitution keeps exit in main shell)
while IFS= read -r P; do
    [ -z "$P" ] && continue

    # Bash commands start with a lowercase letter — extract embedded paths
    if echo "$P" | grep -qE '^[a-z]'; then
        for EMBEDDED in $(echo "$P" | grep -oE '/(Users|home)/[^ "'"'"']+'); do
            check_single_path "$EMBEDDED"
        done
    else
        check_single_path "$P"
    fi
done <<< "$ALL_PATHS"

exit 0
