#!/usr/bin/env bash
# test-cohesion.sh — Run related tests after edits, block if they fail.
#
# Fires on: PostToolUse
# Matcher: Edit|MultiEdit|Write
# Skipped when TOOLKIT_HOOK_PROFILE=minimal or CLAUDE_HOOK_BOOTSTRAP=1.
#
# Constitution Art. VI.3 ("Tests and Docs Follow Behavior"): when source code
# changes, the matching tests must pass before the agent can continue. This
# hook resolves a per-project test-cohesion map and runs only the related
# test files (NOT the full suite).
#
# Map lookup (first found wins):
#   1. $PWD/.claude/test-cohesion-map.json (project-local)
#   2. $TOOLKIT_DIR/app/hooks/test-cohesion-map.json (toolkit default)
#
# Escape hatches:
#   CLAUDE_HOOK_BOOTSTRAP=1   bypass (used when editing the hook itself)
#   CLAUDE_SKIP_COHESION=1    one-off bypass
#
# Exit codes:
#   0  no map / no match / tests passed
#   2  related test command failed

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"
# shellcheck source=_locate-toolkit.sh
source "$(dirname "$0")/_locate-toolkit.sh"
# shellcheck source=_hook-io.sh
source "$(dirname "$0")/_hook-io.sh"

[ "${CLAUDE_HOOK_BOOTSTRAP:-0}" = "1" ] && exit 0
[ "${CLAUDE_SKIP_COHESION:-0}" = "1" ] && exit 0

INPUT=$(cat)
FILE_PATH=$(hook_file_path)

[ -z "$FILE_PATH" ] && exit 0
[ -z "$TOOLKIT_DIR" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0

REPO_ROOT="$PWD"
# Prefer git repo root when available; fall back to PWD.
if command -v git >/dev/null 2>&1; then
    git_root=$(git rev-parse --show-toplevel 2>/dev/null)
    [ -n "$git_root" ] && REPO_ROOT="$git_root"
fi

# Resolve symlinks on both sides so the cohesion-map glob can match files
# under symlinked roots (e.g. /tmp -> /private/tmp on macOS).
REAL_FILE=$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$FILE_PATH" 2>/dev/null)
REAL_REPO=$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$REPO_ROOT" 2>/dev/null)
[ -z "$REAL_FILE" ] && REAL_FILE="$FILE_PATH"
[ -z "$REAL_REPO" ] && REAL_REPO="$REPO_ROOT"

COMMANDS=$(python3 "$TOOLKIT_DIR/scripts/test_cohesion.py" resolve \
    --changed-paths "$REAL_FILE" --repo-root "$REAL_REPO" 2>/dev/null)
[ -z "$COMMANDS" ] && exit 0

# Run each resolved command. Block on first failure.
LOG_DIR="$HOME/.softspark/ai-toolkit/state"
mkdir -p "$LOG_DIR" 2>/dev/null
LOG_FILE="$LOG_DIR/test-cohesion-last.log"

cd "$REAL_REPO" || exit 0
FAILED=""
while IFS= read -r cmd; do
    [ -z "$cmd" ] && continue
    if ! bash -c "$cmd" >"$LOG_FILE" 2>&1; then
        FAILED="$cmd"
        break
    fi
done <<<"$COMMANDS"

if [ -n "$FAILED" ]; then
    cat >&2 <<EOF
test-cohesion: BLOCKED — tests for ${FILE_PATH} failed.
Constitution Art. VI.3: tests must pass before continuing.

Command:
    $FAILED

Last log (truncated):
$(tail -20 "$LOG_FILE")

Fix the failing test OR update it to match the new behavior (Art. VI.3).
Override (one-off): CLAUDE_SKIP_COHESION=1
EOF
    exit 2
fi

[ "${AI_TOOLKIT_HOOK_FORMAT:-}" = "json" ] || echo "test-cohesion: related tests passed for ${FILE_PATH}"
exit 0
