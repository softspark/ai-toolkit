#!/usr/bin/env bash
# stop-search-check.sh — Block Stop when search-first rule was skipped.
#
# Fires on: Stop
# Matcher: all
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.
#
# If user-prompt-submit.sh set the search-required flag and no search tool
# was invoked (search-tracker.sh would have cleared it), this hook continues
# the conversation with a JSON `decision: block` payload so Claude reads the
# reminder and calls smart_query() before the next response.
#
# Override (one-off): CLAUDE_SKIP_SEARCH_FIRST=1

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"
# shellcheck source=_hook-io.sh
source "$(dirname "$0")/_hook-io.sh"
# shellcheck source=_search-capability.sh
source "$(dirname "$0")/_search-capability.sh"

[ "${CLAUDE_SKIP_SEARCH_FIRST:-0}" = "1" ] && exit 0

FLAG="$HOME/.softspark/ai-toolkit/state/search-required.flag"
[ -f "$FLAG" ] || exit 0

if ! ai_toolkit_has_search_provider; then
    rm -f "$FLAG" 2>/dev/null
    exit 0
fi

# Read the original prompt (line 2 of the flag file) for the reminder.
PROMPT_PREVIEW=$(sed -n '2p' "$FLAG" 2>/dev/null | head -c 200)
rm -f "$FLAG" 2>/dev/null  # one-shot; do not loop forever

hook_emit_block "Stop" "Step 0 violated: you responded to a technical prompt without calling smart_query() or hybrid_search_kb() first. Per global CLAUDE.md GOLDEN RULE: search KB BEFORE answering. Prompt was: \"${PROMPT_PREVIEW}...\". Now: call the search tool, then continue your reply. Override (one-off): CLAUDE_SKIP_SEARCH_FIRST=1."
exit 0
