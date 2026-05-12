#!/usr/bin/env bash
# _locate-toolkit.sh — shared toolkit-root locator for hooks needing scripts/.
#
# Source this file to get $TOOLKIT_DIR set to the ai-toolkit checkout root.
# Resolution order:
#   1. $AI_TOOLKIT_DIR env override (used by tests)
#   2. npm global install: $(npm root -g)/@softspark/ai-toolkit
#   3. Fallback: installed runtime at ~/.softspark/ai-toolkit
#   4. Fallback: parent of the hook script directory (repo checkout)
#
# Sets:
#   TOOLKIT_DIR — absolute path to toolkit root, or empty if not findable.

_ai_toolkit_hook_dir() {
    local src="${BASH_SOURCE[1]:-$0}"
    (cd "$(dirname "$src")" 2>/dev/null && pwd)
}

if [ -n "${AI_TOOLKIT_DIR:-}" ] && [ -d "$AI_TOOLKIT_DIR" ]; then
    TOOLKIT_DIR="$AI_TOOLKIT_DIR"
else
    TOOLKIT_DIR="$(npm root -g 2>/dev/null)/@softspark/ai-toolkit"
    if [ ! -d "$TOOLKIT_DIR" ]; then
        TOOLKIT_DIR="$HOME/.softspark/ai-toolkit"
    fi
    if [ ! -d "$TOOLKIT_DIR" ]; then
        _hook_dir="$(_ai_toolkit_hook_dir)"
        if [ -f "$_hook_dir/../app/hooks.json" ]; then
            TOOLKIT_DIR="$(cd "$_hook_dir/.." 2>/dev/null && pwd)"
        else
            TOOLKIT_DIR="$(cd "$_hook_dir/../.." 2>/dev/null && pwd)"
        fi
        unset _hook_dir
    fi
fi

[ -d "$TOOLKIT_DIR" ] || TOOLKIT_DIR=""
unset -f _ai_toolkit_hook_dir
export TOOLKIT_DIR
