#!/usr/bin/env bash
# pre-compact.sh — Save critical context before conversation compaction.
#
# Fires on: PreCompact
# Outputs key context markers so they survive the compaction boundary.
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

# 1. Remind Claude to reload project rules after compaction
echo "IMPORTANT: Context was compacted. Re-read CLAUDE.md files and active tasks before continuing."

# 2. Preserve active task summary if available
if [ -f ".claude/session-context.md" ]; then
    echo "=== Pre-Compaction Context ==="
    cat ".claude/session-context.md"
    echo "=============================="
fi

# 3. Preserve active instincts
INSTINCTS_DIR=".claude/instincts"
if [ -d "$INSTINCTS_DIR" ] && ls "$INSTINCTS_DIR"/*.md >/dev/null 2>&1; then
    echo "=== Active Instincts ==="
    for f in "$INSTINCTS_DIR"/*.md; do
        echo "- $(head -1 "$f")"
    done
    echo "========================"
fi

exit 0
