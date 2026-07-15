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

# shellcheck disable=SC2034  # INPUT is consumed via sourced _hook-io.sh
INPUT=$(cat 2>/dev/null || true)
FLAG="$HOME/.softspark/ai-toolkit/state/search-required-$(hook_session_id).flag"
[ -f "$FLAG" ] || exit 0

if ! ai_toolkit_has_search_provider; then
    rm -f "$FLAG" 2>/dev/null
    exit 0
fi

ai_toolkit_codex_log_has_search_since() {
    local flag="$1"
    local codex_home="${CODEX_HOME:-$HOME/.codex}"
    local log="$codex_home/log/codex-tui.log"
    [ -f "$log" ] || return 1

    python3 - "$flag" "$log" <<'PY' 2>/dev/null
import re
import sys
from datetime import datetime
from pathlib import Path

flag_path = Path(sys.argv[1])
log_path = Path(sys.argv[2])
try:
    since = int(flag_path.read_text(encoding="utf-8").splitlines()[0])
except (OSError, ValueError, IndexError):
    sys.exit(1)

tool_pattern = re.compile(
    r"(ToolCall: (mcp__[^ ]*__(smart_query|hybrid_search_kb|crag_search|multi_hop_search|verify_answer)|web_(search|fetch))|"
    r'tool\.name="(smart_query|hybrid_search_kb|crag_search|multi_hop_search|verify_answer)")',
    re.IGNORECASE,
)

try:
    with log_path.open("rb") as handle:
        handle.seek(0, 2)
        size = handle.tell()
        # Codex logs can be noisy between the search call and Stop hook
        # execution, especially when skill loading emits repeated warnings.
        # Keep this bounded, but large enough to avoid false positives.
        handle.seek(max(0, size - 20_000_000))
        lines = handle.read().decode("utf-8", errors="replace").splitlines()
except OSError:
    sys.exit(1)

for line in lines:
    if not tool_pattern.search(line):
        continue
    raw_ts = line.split(" ", 1)[0]
    try:
        ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00")).timestamp()
    except ValueError:
        continue
    if ts >= since:
        sys.exit(0)

sys.exit(1)
PY
}

if ai_toolkit_codex_log_has_search_since "$FLAG"; then
    rm -f "$FLAG" 2>/dev/null
    exit 0
fi

# Read the original prompt (line 2 of the flag file) for the reminder.
PROMPT_PREVIEW=$(sed -n '2p' "$FLAG" 2>/dev/null | head -c 200)
rm -f "$FLAG" 2>/dev/null  # one-shot; do not loop forever

hook_emit_block "Stop" "Step 0 violated: you responded to a technical prompt without calling smart_query() or hybrid_search_kb() first. Per global CLAUDE.md GOLDEN RULE: search KB BEFORE answering. Prompt was: \"${PROMPT_PREVIEW}...\". Now: call the search tool, then continue your reply. Override (one-off): CLAUDE_SKIP_SEARCH_FIRST=1."
exit 0
