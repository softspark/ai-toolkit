#!/usr/bin/env bash
# _search-capability.sh — determine whether strict search-first enforcement is safe.
#
# Default is conservative: do not block users unless a search provider is
# explicitly configured or strict mode is requested.

ai_toolkit_search_first_mode() {
    printf '%s\n' "${AI_TOOLKIT_SEARCH_FIRST:-${CLAUDE_SEARCH_FIRST:-auto}}" \
        | tr '[:upper:]' '[:lower:]'
}

ai_toolkit_has_search_provider() {
    local mode
    mode="$(ai_toolkit_search_first_mode)"
    case "$mode" in
        off|false|0|disabled|none)
            return 1
            ;;
        strict|required|require|on|true|1)
            return 0
            ;;
    esac

    [ -n "${AI_TOOLKIT_SEARCH_PROVIDER:-}" ] && return 0
    [ -n "${CLAUDE_SEARCH_PROVIDER:-}" ] && return 0

    local candidates=(
        "$PWD/.mcp.json"
        "$PWD/.claude/mcp.json"
        "$PWD/.cursor/mcp.json"
        "$PWD/.gemini/settings.json"
        "$HOME/.claude.json"
        "$HOME/.claude/settings.json"
        "$HOME/.codex/config.toml"
        "$HOME/.gemini/settings.json"
    )
    local path
    for path in "${candidates[@]}"; do
        [ -f "$path" ] || continue
        if grep -Eqi 'rag[-_]?mcp|smart_query|hybrid_search_kb|crag_search|multi_hop_search|websearch|web-fetch|web_fetch|web_search' "$path"; then
            return 0
        fi
    done

    return 1
}
