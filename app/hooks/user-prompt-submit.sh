#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# user-prompt-submit.sh — Lightweight prompt governance reminder before execution.
#
# Fires on: UserPromptSubmit
# Matcher: all
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"
# shellcheck source=_hook-io.sh
source "$(dirname "$0")/_hook-io.sh"
# shellcheck source=_search-capability.sh
source "$(dirname "$0")/_search-capability.sh"

# Read prompt from stdin (Claude Code passes JSON with .prompt field)
# shellcheck disable=SC2034  # INPUT is consumed via sourced _hook-io.sh
INPUT=$(cat)
PROMPT_TEXT=$(hook_prompt)
LOWERED="$(printf '%s' "$PROMPT_TEXT" | tr '[:upper:]' '[:lower:]')"

# Heuristic search-required flag (paired with search-tracker.sh + Stop check).
# Set only when a search provider is detectable or strict mode is requested.
# Cleared by search-tracker.sh after smart_query / hybrid_search_kb / web runs.
PROMPT_LEN=${#PROMPT_TEXT}
STATE_DIR="$HOME/.softspark/ai-toolkit/state"
FLAG="$STATE_DIR/search-required-$(hook_session_id).flag"
mkdir -p "$STATE_DIR" 2>/dev/null

# The flag means "somebody asked a question the KB might answer". Length alone
# does not establish that. The harness delivers background-task notifications,
# CI events and replayed slash-command output on the same channel as a prompt,
# and a 43-character API key pasted on its own line clears the length gate too.
# Both were observed in one session: the first demanded a KB search for text
# nobody asked about, the second would have sent a live credential to a
# retrieval service as the query. Neither is a prompt.
PROMPT_HEAD="${PROMPT_TEXT#"${PROMPT_TEXT%%[![:space:]]*}"}"
PROMPT_IS_QUESTION=1
case "$PROMPT_HEAD" in
    '<task-notification'*|'<ci-monitor-event'*|'<system-reminder'*|\
    '<local-command-'*|'<command-name'*|'<command-message'*) PROMPT_IS_QUESTION=0 ;;
esac
# A single opaque token — API key, hash, URL, path — carries no question. A
# genuine one-word prompt is under the length gate anyway, so nothing is lost.
if [ "$(printf '%s' "$PROMPT_TEXT" | wc -w | tr -d ' ')" -le 1 ]; then
    PROMPT_IS_QUESTION=0
fi

if [ "$PROMPT_LEN" -gt 30 ] && \
   [ "$PROMPT_IS_QUESTION" -eq 1 ] && \
   [ "${CLAUDE_SKIP_SEARCH_FIRST:-0}" != "1" ] && \
   ai_toolkit_has_search_provider; then
    { printf '%s\n%s\n' "$(date -u +%s)" "$PROMPT_TEXT" > "$FLAG"; } 2>/dev/null
else
    { rm -f "$FLAG"; } 2>/dev/null
fi

if ai_toolkit_has_search_provider; then
    CONTEXT_MSG="STOP. Execute Step 0 before responding: check your CLAUDE.md for search-first rules. If search-first rules exist and a search tool is available, call the required search tool NOW — before any other tool or text output."
else
    CONTEXT_MSG="Search-first note: no ai-toolkit search provider was detected, so search-first enforcement is advisory only. Use available local evidence; do not call unavailable RAG/MCP tools."
fi

if printf '%s' "$LOWERED" | grep -Eq 'architecture|design|migration|deploy|rollback|refactor|plugin|workflow'; then
    CONTEXT_MSG="$CONTEXT_MSG
UserPromptSubmit: task looks architectural or multi-step. Use plan mode, define success criteria, and validate before marking done."
elif printf '%s' "$LOWERED" | grep -Eq 'bug|error|fail|failing|incident|outage|debug'; then
    CONTEXT_MSG="$CONTEXT_MSG
UserPromptSubmit: debugging request detected. Gather evidence first, then propose the smallest safe fix and targeted tests."
else
    CONTEXT_MSG="$CONTEXT_MSG
UserPromptSubmit: apply KB-first research, keep changes minimal, and update tests/docs when behavior changes."
fi

hook_emit_context "UserPromptSubmit" "$CONTEXT_MSG"

exit 0
