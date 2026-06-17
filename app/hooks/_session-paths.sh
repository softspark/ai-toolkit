#!/usr/bin/env bash
# _session-paths.sh — shared per-repo session storage paths for lifecycle hooks.
#
# All auto-generated session artifacts live OUTSIDE the project repo, under a
# per-repo subdirectory of ~/.softspark/ai-toolkit/sessions/. This keeps generated
# files (session context, handoff note, checkpoints, decisions) from polluting
# every project's .claude/ directory.
#
# Usage (in a hook script):
#   source "$(dirname "$0")/_session-paths.sh"
# Then use the exported SESSION_* paths.
#
# Repo key: the git work-tree root (fallback: cwd) with "/" replaced by "-",
# mirroring Claude Code's own ~/.claude/projects/<encoded-path> convention so the
# location is derivable by an agent, not an opaque hash.

_session_repo_root() {
    if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        local top
        top="$(git rev-parse --show-toplevel 2>/dev/null)"
        if [ -n "$top" ]; then
            printf '%s' "$top"
            return 0
        fi
    fi
    pwd
}

SESSION_REPO_ROOT="$(_session_repo_root)"
SESSION_REPO_KEY="${SESSION_REPO_ROOT//\//-}"
SESSION_DIR="$HOME/.softspark/ai-toolkit/sessions/$SESSION_REPO_KEY"
SESSION_CONTEXT_FILE="$SESSION_DIR/session-context.md"
SESSION_CHECKPOINTS_FILE="$SESSION_DIR/session-context.md.checkpoints"
SESSION_END_FILE="$SESSION_DIR/session-end.md"
SESSION_DECISIONS_FILE="$SESSION_DIR/decisions.md"

export SESSION_REPO_ROOT SESSION_REPO_KEY SESSION_DIR
export SESSION_CONTEXT_FILE SESSION_CHECKPOINTS_FILE SESSION_END_FILE SESSION_DECISIONS_FILE

unset -f _session_repo_root
