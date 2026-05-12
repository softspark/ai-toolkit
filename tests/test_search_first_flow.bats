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
    unset CLAUDE_SKIP_SEARCH_FIRST AI_TOOLKIT_SEARCH_FIRST AI_TOOLKIT_SEARCH_PROVIDER CLAUDE_SEARCH_PROVIDER
}

teardown() {
    rm -rf "$TEST_TMP"
}

FLAG_PATH() {
    echo "$HOME/.softspark/ai-toolkit/state/search-required.flag"
}

@test "search-first: long technical prompt without provider does NOT set flag" {
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
