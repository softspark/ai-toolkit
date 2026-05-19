#!/usr/bin/env bash
# search-tracker.sh — Clear search-required flag when a search tool runs.
#
# Fires on: PostToolUse
# Matcher: mcp__rag-mcp__smart_query|mcp__rag-mcp__hybrid_search_kb|mcp__rag-mcp__crag_search|mcp__rag-mcp__multi_hop_search|WebSearch|WebFetch
# Non-blocking: always exits 0.
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.
#
# Paired with user-prompt-submit.sh (sets the flag) and stop-search-check.sh
# (blocks Stop when flag still present). Together they implement the Step 0
# "search before answering" rule from global CLAUDE.md.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"
# shellcheck source=_hook-io.sh
source "$(dirname "$0")/_hook-io.sh"

# shellcheck disable=SC2034  # INPUT is consumed via sourced _hook-io.sh
INPUT=$(cat 2>/dev/null || true)
FLAG="$HOME/.softspark/ai-toolkit/state/search-required-$(hook_session_id).flag"
rm -f "$FLAG" 2>/dev/null
exit 0
