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
    local mode codex_home
    mode="$(ai_toolkit_search_first_mode)"
    codex_home="${CODEX_HOME:-$HOME/.codex}"
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

    local json_candidates=(
        "$PWD/.mcp.json"
        "$PWD/.claude/settings.local.json"
        "$PWD/.claude/settings.json"
        "$PWD/.claude/mcp.json"
        "$PWD/.cursor/mcp.json"
        "$PWD/.gemini/settings.json"
        "$HOME/.mcp.json"
        "$HOME/.claude.json"
        "$HOME/.claude/settings.json"
        "$HOME/.cursor/mcp.json"
        "$HOME/.gemini/settings.json"
    )
    local path
    for path in "${json_candidates[@]}"; do
        [ -f "$path" ] || continue
        if ai_toolkit_json_has_search_provider "$path"; then
            return 0
        fi
    done

    local toml_candidates=(
        "$codex_home/config.toml"
    )
    for path in "${toml_candidates[@]}"; do
        [ -f "$path" ] || continue
        if ai_toolkit_toml_has_search_provider "$path"; then
            return 0
        fi
    done

    return 1
}

ai_toolkit_search_provider_pattern() {
    printf '%s\n' '(^|[^[:alnum:]])(([^[:space:]]*[-_])?rag([-_][^[:space:]]*)?|rag[-_]?mcp|web[-_]?search|search)([^[:alnum:]]|$)'
}

ai_toolkit_json_has_search_provider() {
    local path="$1"
    local pattern
    pattern="$(ai_toolkit_search_provider_pattern)"

    command -v jq >/dev/null 2>&1 || return 1
    jq -er '
        [
            (.mcpServers // {} | to_entries[]? | .key),
            (.mcp_servers // {} | to_entries[]? | .key),
            (.mcp // {} | to_entries[]? | .key)
        ] | join(" ")
    ' "$path" 2>/dev/null | grep -Eiq "$pattern"
}

ai_toolkit_toml_has_search_provider() {
    local path="$1"
    local pattern
    pattern="$(ai_toolkit_search_provider_pattern)"

    awk '
        /^\[mcp_servers[."]/ {
            line=$0
            sub(/^\[mcp_servers[."]?/, "", line)
            sub(/"\]$/, "", line)
            sub(/\]$/, "", line)
            print line
        }
    ' "$path" 2>/dev/null | grep -Eiq "$pattern"
}
