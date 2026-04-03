#!/usr/bin/env bash
# pre-compact.sh — Save critical context before conversation compaction.
#
# Fires on: PreCompact
# Outputs key context markers so they survive the compaction boundary.
# Priority order: rules > instincts > tasks > session context > git state.
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

# ---------------------------------------------------------------------------
# 1. Mandatory reload reminder (highest priority — always survives)
# ---------------------------------------------------------------------------
echo "IMPORTANT: Context was compacted. Re-read CLAUDE.md files and active tasks before continuing."

# ---------------------------------------------------------------------------
# 2. Active instincts (high priority — behavioral rules)
# ---------------------------------------------------------------------------
INSTINCTS_DIR=".claude/instincts"
if [ -d "$INSTINCTS_DIR" ] && ls "$INSTINCTS_DIR"/*.md >/dev/null 2>&1; then
    echo "=== Active Instincts ==="
    for f in "$INSTINCTS_DIR"/*.md; do
        # Extract pattern name and confidence from first two lines
        name=$(head -1 "$f" | sed 's/^# Pattern: //')
        confidence=$(grep -m1 'Confidence:' "$f" | awk '{print $2}')
        echo "- [${confidence:-?}] $name"
    done
    echo "========================"
fi

# ---------------------------------------------------------------------------
# 3. Current task state (medium priority — what we're doing)
# ---------------------------------------------------------------------------
if [ -f ".claude/session-context.md" ]; then
    echo "=== Session Context ==="
    cat ".claude/session-context.md"
    echo "======================="
fi

# ---------------------------------------------------------------------------
# 4. Git working state (low priority — quick orientation)
# ---------------------------------------------------------------------------
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    BRANCH=$(git branch --show-current 2>/dev/null)
    DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    LAST_COMMIT=$(git log -1 --oneline 2>/dev/null)
    echo "=== Git State ==="
    echo "Branch: ${BRANCH:-detached}"
    echo "Uncommitted changes: ${DIRTY}"
    echo "Last commit: ${LAST_COMMIT}"
    echo "================="
fi

# ---------------------------------------------------------------------------
# 5. Key decisions file (if user has been noting decisions this session)
# ---------------------------------------------------------------------------
if [ -f ".claude/decisions.md" ]; then
    echo "=== Key Decisions This Session ==="
    # Only show last 10 lines to keep token budget tight
    tail -10 ".claude/decisions.md"
    echo "=================================="
fi

exit 0
