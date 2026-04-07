#!/usr/bin/env bash
# session-context.sh — Capture session context at start for later reference.
#
# Fires on: SessionStart
# Saves environment snapshot to JSON for cross-hook and cross-session use.
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

SESSION="${CLAUDE_SESSION_ID:-$$}"
SESSIONS_DIR="$HOME/.ai-toolkit/sessions"
mkdir -p "$SESSIONS_DIR"

CONTEXT_FILE="$SESSIONS_DIR/${SESSION}.json"

# Gather context
WORKDIR="$(pwd)"
GIT_BRANCH=""
GIT_STATUS=""
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
    GIT_STATUS=$(git status --short 2>/dev/null | head -20)
fi

NODE_VERSION=""
if command -v node >/dev/null 2>&1; then
    NODE_VERSION=$(node --version 2>/dev/null)
fi

PYTHON_VERSION=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version 2>/dev/null | awk '{print $2}')
fi

CURRENT_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Write JSON using python3 for proper escaping
python3 - "$CONTEXT_FILE" "$WORKDIR" "$GIT_BRANCH" "$GIT_STATUS" "$CURRENT_DATE" "$NODE_VERSION" "$PYTHON_VERSION" <<'PY'
import json
import sys
import os

context_file = sys.argv[1]
data = {
    "pwd": sys.argv[2],
    "git_branch": sys.argv[3],
    "git_status": sys.argv[4],
    "date": sys.argv[5],
    "node_version": sys.argv[6],
    "python_version": sys.argv[7],
}

tmp = context_file + ".tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)
os.replace(tmp, context_file)
PY

exit 0
