#!/usr/bin/env bats
# test_config_desync_guard.bats — Tests for app/hooks/config-desync-guard.sh
# Run with: bats tests/test_config_desync_guard.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOK="$TOOLKIT_DIR/app/hooks/config-desync-guard.sh"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    export TOOLKIT_HOOK_PROFILE="standard"
    export AI_TOOLKIT_DIR="$TEST_TMP/fake-toolkit"
    mkdir -p "$TEST_TMP/.claude" "$AI_TOOLKIT_DIR/app"
    unset CLAUDE_SKIP_CONFIG_DESYNC
}

teardown() {
    rm -rf "$TEST_TMP"
}

write_source() {
    cat > "$AI_TOOLKIT_DIR/app/hooks.json"
}

write_settings() {
    cat > "$HOME/.claude/settings.json"
}

@test "config-desync: no settings.json → exit 0 silently" {
    write_source <<'EOF'
{"hooks":{}}
EOF
    run bash "$HOOK"
    [ "$status" -eq 0 ]
}

@test "config-desync: in-sync settings → exit 0 silently" {
    write_source <<'EOF'
{"hooks":{"Stop":[{"_source":"ai-toolkit","matcher":"","hooks":[{"type":"command","command":"echo s"}]}]}}
EOF
    write_settings <<'EOF'
{"hooks":{"Stop":[{"_source":"ai-toolkit","matcher":"","hooks":[{"type":"command","command":"echo s"}]}]}}
EOF
    run bash "$HOOK"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "config-desync: canonical untagged settings are in sync" {
    write_source <<'EOF'
{"hooks":{"Stop":[{"_source":"ai-toolkit","matcher":"","hooks":[{"type":"command","command":"echo s"}]}]}}
EOF
    write_settings <<'EOF'
{"hooks":{"Stop":[{"matcher":"","hooks":[{"type":"command","command":"echo s"}]}]}}
EOF
    run bash "$HOOK"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "config-desync: missing toolkit entry → advisory, exit 0" {
    write_source <<'EOF'
{"hooks":{"Stop":[{"_source":"ai-toolkit","matcher":"","hooks":[{"type":"command","command":"echo new-hook"}]}]}}
EOF
    write_settings <<'EOF'
{"hooks":{}}
EOF
    run bash "$HOOK"
    [ "$status" -eq 0 ]
    [[ "$stderr" == *"drifted"* ]] || [[ "$output" == *"drifted"* ]]
}

@test "config-desync: stale toolkit entry in settings → advisory" {
    write_source <<'EOF'
{"hooks":{}}
EOF
    write_settings <<'EOF'
{"hooks":{"Stop":[{"_source":"ai-toolkit","matcher":"","hooks":[{"type":"command","command":"echo legacy"}]}]}}
EOF
    run bash "$HOOK"
    [ "$status" -eq 0 ]
    [[ "$stderr" == *"drifted"* ]] || [[ "$output" == *"drifted"* ]]
}

@test "config-desync: CLAUDE_SKIP_CONFIG_DESYNC=1 silences advisory" {
    write_source <<'EOF'
{"hooks":{"Stop":[{"_source":"ai-toolkit","matcher":"","hooks":[{"type":"command","command":"echo new"}]}]}}
EOF
    write_settings <<'EOF'
{"hooks":{}}
EOF
    CLAUDE_SKIP_CONFIG_DESYNC=1 run bash "$HOOK"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "config-desync: minimal profile skips entirely" {
    write_source <<'EOF'
{"hooks":{"Stop":[{"_source":"ai-toolkit","matcher":"","hooks":[{"type":"command","command":"echo new"}]}]}}
EOF
    write_settings <<'EOF'
{"hooks":{}}
EOF
    TOOLKIT_HOOK_PROFILE=minimal run bash "$HOOK"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}
