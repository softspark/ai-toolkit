#!/usr/bin/env bats
# test_session_state.bats — Tests for scripts/session_state.py
# Run with: bats tests/test_session_state.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
STATE_CMD="python3 $TOOLKIT_DIR/scripts/session_state.py"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "session_state: reset creates state file with new uuid" {
    run $STATE_CMD reset
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.softspark/ai-toolkit/state/session-edits.json" ]
    sid=$(python3 -c "import json; print(json.load(open('$TEST_TMP/.softspark/ai-toolkit/state/session-edits.json'))['session_id'])")
    [ -n "$sid" ]
}

@test "session_state: reset honors explicit --session-id" {
    run $STATE_CMD reset --session-id custom-abc
    [ "$status" -eq 0 ]
    out=$($STATE_CMD session-id)
    [ "$out" = "custom-abc" ]
}

@test "session_state: append records tool + path" {
    $STATE_CMD reset --session-id s1
    run $STATE_CMD append --tool Edit --path /foo/bar.py --session-id s1
    [ "$status" -eq 0 ]
    run $STATE_CMD list
    [[ "$output" == *"/foo/bar.py"* ]]
}

@test "session_state: append ignores empty path" {
    $STATE_CMD reset --session-id s1
    run $STATE_CMD append --tool Bash --path "" --session-id s1
    [ "$status" -eq 0 ]
    run $STATE_CMD list
    [ -z "$output" ]
}

@test "session_state: was-edited returns 0 for known path, 1 for unknown" {
    $STATE_CMD reset --session-id s1
    $STATE_CMD append --tool Edit --path /a/b.py --session-id s1
    run $STATE_CMD was-edited /a/b.py
    [ "$status" -eq 0 ]
    run $STATE_CMD was-edited /never/touched.py
    [ "$status" -eq 1 ]
}

@test "session_state: list dedupes repeated paths" {
    $STATE_CMD reset --session-id s1
    $STATE_CMD append --tool Edit --path /x.py --session-id s1
    $STATE_CMD append --tool Edit --path /x.py --session-id s1
    $STATE_CMD append --tool Write --path /y.md --session-id s1
    run $STATE_CMD list
    count=$(echo "$output" | grep -c '/x.py')
    [ "$count" -eq 1 ]
    [[ "$output" == *"/y.md"* ]]
}

@test "session_state: new session id auto-resets state" {
    $STATE_CMD reset --session-id s1
    $STATE_CMD append --tool Edit --path /old.py --session-id s1
    $STATE_CMD append --tool Edit --path /new.py --session-id s2
    run $STATE_CMD list
    [[ "$output" != *"/old.py"* ]]
    [[ "$output" == *"/new.py"* ]]
}

@test "session_state: concurrent session files remain isolated" {
    $STATE_CMD reset --session-id session-a
    $STATE_CMD append --tool Edit --path /from-a.py --session-id session-a
    $STATE_CMD reset --session-id session-b
    $STATE_CMD append --tool Edit --path /from-b.py --session-id session-b

    run $STATE_CMD list --session-id session-a
    [ "$status" -eq 0 ]
    [[ "$output" == *"/from-a.py"* ]]
    [[ "$output" != *"/from-b.py"* ]]

    run $STATE_CMD list --session-id session-b
    [ "$status" -eq 0 ]
    [[ "$output" == *"/from-b.py"* ]]
    [[ "$output" != *"/from-a.py"* ]]
}

@test "session_state: clean removes only the selected session file" {
    $STATE_CMD reset --session-id session-a
    $STATE_CMD append --tool Edit --path /from-a.py --session-id session-a
    $STATE_CMD reset --session-id session-b
    $STATE_CMD append --tool Edit --path /from-b.py --session-id session-b

    run $STATE_CMD clean --session-id session-a
    [ "$status" -eq 0 ]

    run $STATE_CMD list --session-id session-a
    [ "$status" -eq 0 ]
    [ -z "$output" ]

    run $STATE_CMD list --session-id session-b
    [ "$status" -eq 0 ]
    [ "$output" = "/from-b.py" ]

    run $STATE_CMD list
    [ "$status" -eq 0 ]
    [ "$output" = "/from-b.py" ]
}

@test "session_state: clean removes a legacy alias only for the same session" {
    $STATE_CMD reset --session-id session-a
    $STATE_CMD append --tool Edit --path /from-a.py --session-id session-a

    run $STATE_CMD clean --session-id session-a
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_TMP/.softspark/ai-toolkit/state/session-edits.json" ]

    $STATE_CMD reset --session-id session-b
    run $STATE_CMD clean --session-id session-a
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.softspark/ai-toolkit/state/session-edits.json" ]
}

@test "session_state: missing state file returns empty list (exit 0)" {
    run $STATE_CMD list
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "session_state: malformed state shape is treated as empty" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit/state"
    printf '[]\n' \
        > "$TEST_TMP/.softspark/ai-toolkit/state/session-edits.json"

    run $STATE_CMD list

    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "session_state: invalid UTF-8 alias is preserved during cleanup" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit/state"
    printf '\377' \
        > "$TEST_TMP/.softspark/ai-toolkit/state/session-edits.json"

    run $STATE_CMD clean --session-id absent-session

    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.softspark/ai-toolkit/state/session-edits.json" ]
}
