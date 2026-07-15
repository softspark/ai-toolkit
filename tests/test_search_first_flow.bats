#!/usr/bin/env bats
# test_search_first_flow.bats — End-to-end test of the search-first enforcement
# trio: user-prompt-submit.sh (set flag) + search-tracker.sh (clear flag)
# + stop-search-check.sh (block Stop when flag is set).

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOKS="$TOOLKIT_DIR/app/hooks"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    export TOOLKIT_HOOK_PROFILE="standard"
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit/state"
    unset CODEX_HOME CLAUDE_SKIP_SEARCH_FIRST AI_TOOLKIT_SEARCH_FIRST AI_TOOLKIT_SEARCH_PROVIDER CLAUDE_SEARCH_PROVIDER
}

teardown() {
    rm -rf "$TEST_TMP"
}

FLAG_PATH() {
    local sid="${1:-default}"
    echo "$HOME/.softspark/ai-toolkit/state/search-required-${sid}.flag"
}

@test "search-first: long technical prompt without provider does NOT set flag" {
    run bash -c "echo '{\"prompt\":\"how does the merge-hooks dedup logic work and is it tested?\"}' | bash '$HOOKS/user-prompt-submit.sh'"
    [ "$status" -eq 0 ]
    [ ! -f "$(FLAG_PATH)" ]
}

@test "search-first: hook matcher and permissions alone do NOT count as provider" {
    mkdir -p "$TEST_TMP/.claude"
    cat > "$TEST_TMP/.claude/settings.json" <<'JSON'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "mcp__rag-mcp__smart_query|WebSearch|WebFetch",
        "hooks": [{"type": "command", "command": "search-tracker.sh"}]
      }
    ]
  },
  "permissions": {
    "allow": ["mcp__customer-rag__smart_query", "WebSearch"]
  }
}
JSON
    cd "$TEST_TMP"
    run bash -c "echo '{\"prompt\":\"how does the merge-hooks dedup logic work and is it tested?\"}' | bash '$HOOKS/user-prompt-submit.sh'"
    [ "$status" -eq 0 ]
    [ ! -f "$(FLAG_PATH)" ]
}

@test "search-first: long technical prompt with strict mode sets flag" {
    AI_TOOLKIT_SEARCH_FIRST=strict run bash -c "echo '{\"prompt\":\"how does the merge-hooks dedup logic work and is it tested?\"}' | bash '$HOOKS/user-prompt-submit.sh'"
    [ "$status" -eq 0 ]
    [ -f "$(FLAG_PATH)" ]
}

@test "search-first: long technical prompt with rag mcp config sets flag" {
    printf '{"mcpServers":{"rag-mcp":{"command":"rag-mcp"}}}\n' > "$TEST_TMP/.mcp.json"
    cd "$TEST_TMP"
    run bash -c "echo '{\"prompt\":\"how does the merge-hooks dedup logic work and is it tested?\"}' | bash '$HOOKS/user-prompt-submit.sh'"
    [ "$status" -eq 0 ]
    [ -f "$(FLAG_PATH)" ]
}

@test "search-first: project settings.local mcpServers provider sets flag" {
    mkdir -p "$TEST_TMP/.claude"
    printf '{"mcpServers":{"customer-rag":{"command":"customer-rag"}}}\n' > "$TEST_TMP/.claude/settings.local.json"
    cd "$TEST_TMP"
    run bash -c "echo '{\"prompt\":\"how does the merge-hooks dedup logic work and is it tested?\"}' | bash '$HOOKS/user-prompt-submit.sh'"
    [ "$status" -eq 0 ]
    [ -f "$(FLAG_PATH)" ]
}

@test "search-first: global mcp config provider sets flag" {
    printf '{"mcpServers":{"rag-mcp":{"command":"rag-mcp"}}}\n' > "$TEST_TMP/.mcp.json"
    run bash -c "echo '{\"prompt\":\"how does the merge-hooks dedup logic work and is it tested?\"}' | bash '$HOOKS/user-prompt-submit.sh'"
    [ "$status" -eq 0 ]
    [ -f "$(FLAG_PATH)" ]
}

@test "search-first: custom CODEX_HOME config provider sets flag" {
    local codex_home="$TEST_TMP/custom-codex-home"
    mkdir -p "$codex_home"
    cat > "$codex_home/config.toml" <<'TOML'
[mcp_servers.rag-mcp]
command = "rag-mcp"
TOML
    cd "$TEST_TMP"
    CODEX_HOME="$codex_home" run bash -c "echo '{\"prompt\":\"how does the merge-hooks dedup logic work and is it tested?\"}' | bash '$HOOKS/user-prompt-submit.sh'"
    [ "$status" -eq 0 ]
    [ -f "$(FLAG_PATH)" ]
}

@test "search-first: short prompt does NOT set flag" {
    run bash -c "echo '{\"prompt\":\"thanks\"}' | bash '$HOOKS/user-prompt-submit.sh'"
    [ "$status" -eq 0 ]
    [ ! -f "$(FLAG_PATH)" ]
}

@test "search-first: CLAUDE_SKIP_SEARCH_FIRST=1 prevents flag" {
    CLAUDE_SKIP_SEARCH_FIRST=1 AI_TOOLKIT_SEARCH_FIRST=strict run bash -c "echo '{\"prompt\":\"long technical prompt about hooks dedup logic and tests\"}' | bash '$HOOKS/user-prompt-submit.sh'"
    [ "$status" -eq 0 ]
    [ ! -f "$(FLAG_PATH)" ]
}

@test "search-first: search-tracker clears flag" {
    touch "$(FLAG_PATH)"
    run bash "$HOOKS/search-tracker.sh"
    [ "$status" -eq 0 ]
    [ ! -f "$(FLAG_PATH)" ]
}

@test "search-first: Stop check clears stale flag without provider" {
    printf '%s\n%s\n' "$(date +%s)" "what is the merge-hooks dedup logic and tests around it" > "$(FLAG_PATH)"
    run bash "$HOOKS/stop-search-check.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -f "$(FLAG_PATH)" ]
}

@test "search-first: Stop check blocks when flag set and provider exists" {
    printf '%s\n%s\n' "$(date +%s)" "what is the merge-hooks dedup logic and tests around it" > "$(FLAG_PATH)"
    AI_TOOLKIT_SEARCH_FIRST=strict run bash "$HOOKS/stop-search-check.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"decision"* ]]
    [[ "$output" == *"block"* ]]
    [[ "$output" == *"smart_query"* ]]
    [ ! -f "$(FLAG_PATH)" ]
}

@test "search-first: Stop check allows when Codex log shows search after flag" {
    mkdir -p "$TEST_TMP/.codex/log"
    printf '%s\n%s\n' "100" "what is the merge-hooks dedup logic and tests around it" > "$(FLAG_PATH)"
    cat > "$TEST_TMP/.codex/log/codex-tui.log" <<'LOG'
1970-01-01T00:02:00Z INFO ToolCall: mcp__rag_mcp__smart_query {"query":"hooks"}
LOG
    AI_TOOLKIT_SEARCH_FIRST=strict run bash "$HOOKS/stop-search-check.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -f "$(FLAG_PATH)" ]
}

@test "search-first: Stop check reads log from custom CODEX_HOME" {
    local codex_home="$TEST_TMP/custom-codex-home"
    mkdir -p "$codex_home/log"
    printf '%s\n%s\n' "100" "what is the merge-hooks dedup logic and tests around it" > "$(FLAG_PATH)"
    cat > "$codex_home/log/codex-tui.log" <<'LOG'
1970-01-01T00:02:00Z INFO ToolCall: mcp__rag_mcp__smart_query {"query":"hooks"}
LOG
    CODEX_HOME="$codex_home" AI_TOOLKIT_SEARCH_FIRST=strict run \
        bash "$HOOKS/stop-search-check.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -f "$(FLAG_PATH)" ]
}

@test "search-first: Stop check scans enough Codex log to survive noisy output" {
    mkdir -p "$TEST_TMP/.codex/log"
    printf '%s\n%s\n' "100" "what is the merge-hooks dedup logic and tests around it" > "$(FLAG_PATH)"
    {
        printf '%s\n' '1970-01-01T00:02:00Z INFO ToolCall: mcp__rag_mcp__smart_query {"query":"hooks"}'
        python3 - <<'PY'
print("x" * 3_000_000)
PY
    } > "$TEST_TMP/.codex/log/codex-tui.log"
    AI_TOOLKIT_SEARCH_FIRST=strict run bash "$HOOKS/stop-search-check.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -f "$(FLAG_PATH)" ]
}

@test "search-first: Stop check recognizes Codex mcp tool.name log shape" {
    mkdir -p "$TEST_TMP/.codex/log"
    printf '%s\n%s\n' "100" "what is the merge-hooks dedup logic and tests around it" > "$(FLAG_PATH)"
    cat > "$TEST_TMP/.codex/log/codex-tui.log" <<'LOG'
1970-01-01T00:02:00Z INFO mcp.tools.call{tool.name="smart_query" tool.call_id="call_123"}: codex_core::mcp_tool_call: new
LOG
    AI_TOOLKIT_SEARCH_FIRST=strict run bash "$HOOKS/stop-search-check.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -f "$(FLAG_PATH)" ]
}

@test "search-first: Stop check ignores Codex searches older than flag" {
    mkdir -p "$TEST_TMP/.codex/log"
    printf '%s\n%s\n' "200" "what is the merge-hooks dedup logic and tests around it" > "$(FLAG_PATH)"
    cat > "$TEST_TMP/.codex/log/codex-tui.log" <<'LOG'
1970-01-01T00:02:00Z INFO ToolCall: mcp__rag_mcp__smart_query {"query":"old hooks"}
LOG
    AI_TOOLKIT_SEARCH_FIRST=strict run bash "$HOOKS/stop-search-check.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"block"* ]]
    [ ! -f "$(FLAG_PATH)" ]
}

@test "search-first: Stop check no-op when flag absent" {
    run bash "$HOOKS/stop-search-check.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "search-first: CLAUDE_SKIP_SEARCH_FIRST=1 bypasses Stop check" {
    touch "$(FLAG_PATH)"
    CLAUDE_SKIP_SEARCH_FIRST=1 run bash "$HOOKS/stop-search-check.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "search-first: full cycle prompt → search → stop allows" {
    # 1. Submit long prompt → flag set
    AI_TOOLKIT_SEARCH_FIRST=strict bash -c "echo '{\"prompt\":\"long question about hooks dedup behavior and the tests around it\"}' | bash '$HOOKS/user-prompt-submit.sh'" >/dev/null
    [ -f "$(FLAG_PATH)" ]
    # 2. Run search → flag cleared
    bash "$HOOKS/search-tracker.sh"
    [ ! -f "$(FLAG_PATH)" ]
    # 3. Stop check passes
    run bash "$HOOKS/stop-search-check.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "search-first: per-session flags isolated between sessions" {
    # Session A submits a long prompt → flag set for session A only.
    AI_TOOLKIT_SEARCH_FIRST=strict bash -c "echo '{\"session_id\":\"sessA\",\"prompt\":\"long question about hooks dedup behavior and tests\"}' | bash '$HOOKS/user-prompt-submit.sh'" >/dev/null
    [ -f "$(FLAG_PATH sessA)" ]
    [ ! -f "$(FLAG_PATH sessB)" ]

    # Session B Stop check must NOT find a flag and must NOT block.
    AI_TOOLKIT_SEARCH_FIRST=strict run bash -c "echo '{\"session_id\":\"sessB\"}' | bash '$HOOKS/stop-search-check.sh'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]

    # Session A flag still present (B did not consume it).
    [ -f "$(FLAG_PATH sessA)" ]

    # Session A Stop check (still no search) blocks A using A's prompt.
    AI_TOOLKIT_SEARCH_FIRST=strict run bash -c "echo '{\"session_id\":\"sessA\"}' | bash '$HOOKS/stop-search-check.sh'"
    [ "$status" -eq 0 ]
    [[ "$output" == *"block"* ]]
    [[ "$output" == *"hooks dedup behavior"* ]]
    [ ! -f "$(FLAG_PATH sessA)" ]
}

@test "search-first: search-tracker clears only the calling session's flag" {
    touch "$(FLAG_PATH sessA)" "$(FLAG_PATH sessB)"
    run bash -c "echo '{\"session_id\":\"sessA\"}' | bash '$HOOKS/search-tracker.sh'"
    [ "$status" -eq 0 ]
    [ ! -f "$(FLAG_PATH sessA)" ]
    [ -f "$(FLAG_PATH sessB)" ]
}
