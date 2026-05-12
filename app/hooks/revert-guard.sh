#!/usr/bin/env bash
# revert-guard.sh — Block git revert/restore on files edited in this session.
#
# Fires on: PreToolUse
# Matcher: Bash
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.
#
# Constitution Art. VI.2 ("Fix Every Found Bug"): when a session has produced
# edits, a `git checkout/restore/reset --hard/clean -fd` on those files is
# almost always discarding work-in-progress instead of fixing the root cause.
# Block it unless the user explicitly opted in.
#
# Escape hatch: set CLAUDE_REVERT_OK=1 (per-call) to bypass.
# Exit codes:
#   0  allow command
#   2  block (per Claude Code hooks spec)

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"
# shellcheck source=_locate-toolkit.sh
source "$(dirname "$0")/_locate-toolkit.sh"
# shellcheck source=_hook-io.sh
source "$(dirname "$0")/_hook-io.sh"

# shellcheck disable=SC2034  # INPUT is consumed via sourced _hook-io.sh
INPUT=$(cat)
COMMAND=$(hook_command)

[ -z "$COMMAND" ] && exit 0
[ "${CLAUDE_REVERT_OK:-0}" = "1" ] && exit 0
[ -z "$TOOLKIT_DIR" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0

# Strip leading words so we can match the git verb.
# Only act on commands whose first token is `git`.
read -r FIRST _rest <<<"$COMMAND"
[ "$FIRST" = "git" ] || exit 0

# Helper: emit block message on stderr and exit 2.
_block() {
    local reason="$1"
    local detail="$2"
    cat >&2 <<EOF
revert-guard: BLOCKED — $reason
Constitution Art. VI.2: do not revert work-in-progress. Fix the root cause instead.

Affected: $detail

If you really need to discard changes, re-run with:
    CLAUDE_REVERT_OK=1 $COMMAND
EOF
    exit 2
}

# git reset --hard / git clean -fd: clobber-style, scope = all session edits.
if printf '%s' "$COMMAND" | grep -Eq 'reset[[:space:]]+(-+[A-Za-z-]+[[:space:]]+)*--hard|clean[[:space:]]+-[A-Za-z]*[df]'; then
    edited=$(python3 "$TOOLKIT_DIR/scripts/session_state.py" list 2>/dev/null | head -10)
    if [ -n "$edited" ]; then
        _block "destructive 'git reset --hard' / 'git clean' with session edits in tree" "$edited"
    fi
    exit 0
fi

# git checkout / git restore: only block when `--` separator is present
# (file-restore form). Bare `git checkout branch-name` is allowed.
if printf '%s' "$COMMAND" | grep -Eq '(checkout|restore)([[:space:]].*)?[[:space:]]--[[:space:]]'; then
    files=$(printf '%s' "$COMMAND" | awk -F' -- ' '{print $2}')
    [ -z "$files" ] && exit 0
    blocked=""
    for f in $files; do
        # Resolve relative paths against $PWD.
        case "$f" in
            /*) abs="$f" ;;
            *)  abs="$PWD/$f" ;;
        esac
        if python3 "$TOOLKIT_DIR/scripts/session_state.py" was-edited "$abs" >/dev/null 2>&1; then
            blocked="$blocked $f"
        fi
    done
    if [ -n "$blocked" ]; then
        _block "restoring file(s) edited in this session" "$blocked"
    fi
fi

exit 0
