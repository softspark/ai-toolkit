#!/usr/bin/env bats
# test_instructions_audit.bats — Tests for app/hooks/instructions-audit.sh
# Run with: bats tests/test_instructions_audit.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOK="$TOOLKIT_DIR/app/hooks/instructions-audit.sh"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    export TOOLKIT_HOOK_PROFILE="standard"
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "instructions-audit: appends ISO ts + memory_type + load_reason + path" {
    run bash -c "echo '{\"file_path\":\"/tmp/CLAUDE.md\",\"memory_type\":\"project\",\"load_reason\":\"session_start\"}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
    log="$HOME/.softspark/ai-toolkit/state/loaded-instructions.log"
    [ -f "$log" ]
    line=$(cat "$log")
    [[ "$line" == *"project"* ]]
    [[ "$line" == *"session_start"* ]]
    [[ "$line" == *"/tmp/CLAUDE.md"* ]]
}

@test "instructions-audit: missing file_path → no-op (exit 0)" {
    run bash -c "echo '{\"memory_type\":\"project\"}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
    log="$HOME/.softspark/ai-toolkit/state/loaded-instructions.log"
    [ ! -f "$log" ]
}

@test "instructions-audit: minimal profile skips entirely" {
    TOOLKIT_HOOK_PROFILE=minimal run bash -c "echo '{\"file_path\":\"/x\"}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
    log="$HOME/.softspark/ai-toolkit/state/loaded-instructions.log"
    [ ! -f "$log" ]
}

@test "instructions-audit: empty stdin → no-op" {
    run bash -c "echo '' | bash '$HOOK'"
    [ "$status" -eq 0 ]
}

@test "instructions-audit: log rotates at >2000 lines" {
    log="$HOME/.softspark/ai-toolkit/state/loaded-instructions.log"
    mkdir -p "$(dirname "$log")"
    seq 1 2100 | sed 's/^/2026-05-12T00:00:00Z\tproject\tsession_start\t\/old\//' > "$log"
    run bash -c "echo '{\"file_path\":\"/new\",\"memory_type\":\"project\",\"load_reason\":\"r\"}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
    count=$(wc -l < "$log" | tr -d ' ')
    [ "$count" -le 1501 ]
}
