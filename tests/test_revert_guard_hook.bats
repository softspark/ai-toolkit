#!/usr/bin/env bats
# test_revert_guard_hook.bats — Tests for app/hooks/revert-guard.sh
# Run with: bats tests/test_revert_guard_hook.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOK="$TOOLKIT_DIR/app/hooks/revert-guard.sh"
STATE_CMD="python3 $TOOLKIT_DIR/scripts/session_state.py"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    export TOOLKIT_HOOK_PROFILE="standard"
    export AI_TOOLKIT_DIR="$TOOLKIT_DIR"
    unset CLAUDE_REVERT_OK
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
}

teardown() {
    rm -rf "$TEST_TMP"
}

call_hook() {
    local cmd="$1"
    run bash -c "echo '{\"tool_input\":{\"command\":\"$cmd\"}}' | bash '$HOOK'"
}

@test "revert-guard: allows non-git commands" {
    $STATE_CMD reset --session-id s1
    $STATE_CMD append --tool Edit --path "$TEST_TMP/foo.py" --session-id s1
    call_hook "ls -la"
    [ "$status" -eq 0 ]
}

@test "revert-guard: allows git checkout branch (no -- separator)" {
    $STATE_CMD reset --session-id s1
    $STATE_CMD append --tool Edit --path "$TEST_TMP/foo.py" --session-id s1
    call_hook "git checkout main"
    [ "$status" -eq 0 ]
}

@test "revert-guard: BLOCKS git checkout -- <edited-file>" {
    $STATE_CMD reset --session-id s1
    $STATE_CMD append --tool Edit --path "$TEST_TMP/foo.py" --session-id s1
    cd "$TEST_TMP"
    call_hook "git checkout -- foo.py"
    [ "$status" -eq 2 ]
    [[ "$stderr" == *"BLOCKED"* ]] || [[ "$output" == *"BLOCKED"* ]]
}

@test "revert-guard: allows git checkout -- <unrelated-file>" {
    $STATE_CMD reset --session-id s1
    $STATE_CMD append --tool Edit --path "$TEST_TMP/foo.py" --session-id s1
    cd "$TEST_TMP"
    call_hook "git checkout -- bar.py"
    [ "$status" -eq 0 ]
}

@test "revert-guard: BLOCKS git reset hard when session has edits" {
    $STATE_CMD reset --session-id s1
    $STATE_CMD append --tool Edit --path "$TEST_TMP/foo.py" --session-id s1
    call_hook "git reset --hard"
    [ "$status" -eq 2 ]
}

@test "revert-guard: allows git reset hard when session has no edits" {
    $STATE_CMD reset --session-id s1
    call_hook "git reset --hard"
    [ "$status" -eq 0 ]
}

@test "revert-guard: BLOCKS git clean -fd with session edits" {
    $STATE_CMD reset --session-id s1
    $STATE_CMD append --tool Edit --path "$TEST_TMP/foo.py" --session-id s1
    call_hook "git clean -fd"
    [ "$status" -eq 2 ]
}

@test "revert-guard: escape hatch CLAUDE_REVERT_OK=1 bypasses" {
    $STATE_CMD reset --session-id s1
    $STATE_CMD append --tool Edit --path "$TEST_TMP/foo.py" --session-id s1
    CLAUDE_REVERT_OK=1 run bash -c "echo '{\"tool_input\":{\"command\":\"git reset --hard\"}}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
}

@test "revert-guard: minimal profile skips entirely" {
    $STATE_CMD reset --session-id s1
    $STATE_CMD append --tool Edit --path "$TEST_TMP/foo.py" --session-id s1
    TOOLKIT_HOOK_PROFILE=minimal run bash -c "echo '{\"tool_input\":{\"command\":\"git reset --hard\"}}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
}

@test "revert-guard: BLOCKS git restore on edited file" {
    $STATE_CMD reset --session-id s1
    $STATE_CMD append --tool Edit --path "$TEST_TMP/foo.py" --session-id s1
    cd "$TEST_TMP"
    call_hook "git restore -- foo.py"
    [ "$status" -eq 2 ]
}
