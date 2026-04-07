#!/usr/bin/env bash
# mcp-health.sh — Check MCP server health at session start.
#
# Fires on: SessionStart
# Non-blocking: always exits 0 (warnings only).

# Common install hints for known MCP servers
get_install_hint() {
    case "$1" in
        npx)   echo "npm install -g npx" ;;
        uvx)   echo "pip install uv" ;;
        node)  echo "https://nodejs.org/" ;;
        python3|python) echo "https://python.org/" ;;
        docker) echo "https://docs.docker.com/get-docker/" ;;
        *)     echo "check the MCP server documentation" ;;
    esac
}

# Check both global and local MCP config files
CONFIG_FILES=()
[ -f "$HOME/.claude/settings.json" ] && CONFIG_FILES+=("$HOME/.claude/settings.json")
[ -f ".mcp.json" ] && CONFIG_FILES+=(".mcp.json")

if [ ${#CONFIG_FILES[@]} -eq 0 ]; then
    exit 0
fi

# Verify jq is available
if ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

for CONFIG in "${CONFIG_FILES[@]}"; do
    # Extract server names and their commands from mcpServers config
    SERVERS=$(jq -r '
        (.mcpServers // .mcp_servers // {})
        | to_entries[]
        | select(.value.command != null)
        | "\(.key)\t\(.value.command)"
    ' "$CONFIG" 2>/dev/null)

    [ -z "$SERVERS" ] && continue

    while IFS=$'\t' read -r SERVER_NAME CMD; do
        [ -z "$CMD" ] && continue
        if ! command -v "$CMD" >/dev/null 2>&1; then
            HINT=$(get_install_hint "$CMD")
            echo "MCP health: ${SERVER_NAME} command not found (${CMD}). Install with: ${HINT}"
        fi
    done <<< "$SERVERS"
done

exit 0
