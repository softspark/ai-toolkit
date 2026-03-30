#!/usr/bin/env bash
# session-start.sh — Inject mandatory rules reminder + session context on startup/compact.
#
# Fires on: SessionStart (startup|compact)
# Output goes to Claude's context as plain text.

# 1. Mandatory rules reminder
echo "MANDATORY: Before answering ANY technical question, apply ALL rules from your CLAUDE.md files (global + project). Follow the exact order of operations defined there. Do NOT skip mandatory steps even if you think you already know the answer."
echo "REMINDER: When writing features or fixing bugs, ensure tests cover the changes. When modifying API, config, or setup, update relevant documentation. Propose these steps to the user — do not silently skip them."

# 2. Load session context (if available)
SESSION_FILE=".claude/session-context.md"
if [ -f "$SESSION_FILE" ]; then
    echo "=== Session Context ==="
    cat "$SESSION_FILE"
    echo "====================="
fi

# 3. Load active instincts (if any)
INSTINCTS_DIR=".claude/instincts"
if [ -d "$INSTINCTS_DIR" ] && ls "$INSTINCTS_DIR"/*.md >/dev/null 2>&1; then
    echo "=== Active Instincts ==="
    for f in "$INSTINCTS_DIR"/*.md; do
        echo "- $(head -1 "$f")"
    done
    echo "========================"
fi

exit 0
