#!/usr/bin/env bats
# test_test_cohesion_hook.bats — Tests for app/hooks/test-cohesion.sh
# Run with: bats tests/test_test_cohesion_hook.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOK="$TOOLKIT_DIR/app/hooks/test-cohesion.sh"

setup() {
    TEST_TMP="$(mktemp -d)"
    REPO="$TEST_TMP/repo"
    mkdir -p "$REPO/.claude" "$REPO/src" "$REPO/tests"
    cd "$REPO"
    git init -q . 2>/dev/null
    export HOME="$TEST_TMP"
    export TOOLKIT_HOOK_PROFILE="standard"
    export AI_TOOLKIT_DIR="$TOOLKIT_DIR"
    unset CLAUDE_HOOK_BOOTSTRAP CLAUDE_SKIP_COHESION
}

teardown() {
    rm -rf "$TEST_TMP"
}

write_map() {
    cat > "$REPO/.claude/test-cohesion-map.json"
}

call_hook() {
    local path="$1"
    run bash -c "cd '$REPO' && echo '{\"tool_input\":{\"file_path\":\"$path\"}}' | bash '$HOOK'"
}

@test "test-cohesion: no map → no-op (exit 0)" {
    rm -f "$REPO/.claude/test-cohesion-map.json"
    AI_TOOLKIT_DIR="$REPO" call_hook "$REPO/src/foo.py"
    [ "$status" -eq 0 ]
}

@test "test-cohesion: changed path not matching map → exit 0" {
    write_map <<'EOF'
[{"match":"app/*.sh","tests":["tests/none.bats"],"runner":"bats","command":"true"}]
EOF
    call_hook "$REPO/src/foo.py"
    [ "$status" -eq 0 ]
}

@test "test-cohesion: passing related command → exit 0" {
    write_map <<'EOF'
[{"match":"src/*.py","tests":[],"runner":"custom","command":"true"}]
EOF
    call_hook "$REPO/src/foo.py"
    [ "$status" -eq 0 ]
}

@test "test-cohesion: failing related command → exit 2 (BLOCK)" {
    write_map <<'EOF'
[{"match":"src/*.py","tests":[],"runner":"custom","command":"false"}]
EOF
    call_hook "$REPO/src/foo.py"
    [ "$status" -eq 2 ]
}

@test "test-cohesion: CLAUDE_SKIP_COHESION=1 bypasses" {
    write_map <<'EOF'
[{"match":"src/*.py","tests":[],"runner":"custom","command":"false"}]
EOF
    CLAUDE_SKIP_COHESION=1 run bash -c "cd '$REPO' && echo '{\"tool_input\":{\"file_path\":\"$REPO/src/foo.py\"}}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
}

@test "test-cohesion: CLAUDE_HOOK_BOOTSTRAP=1 bypasses (for hook self-edits)" {
    write_map <<'EOF'
[{"match":"src/*.py","tests":[],"runner":"custom","command":"false"}]
EOF
    CLAUDE_HOOK_BOOTSTRAP=1 run bash -c "cd '$REPO' && echo '{\"tool_input\":{\"file_path\":\"$REPO/src/foo.py\"}}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
}

@test "test-cohesion: minimal profile skips entirely" {
    write_map <<'EOF'
[{"match":"src/*.py","tests":[],"runner":"custom","command":"false"}]
EOF
    TOOLKIT_HOOK_PROFILE=minimal run bash -c "cd '$REPO' && echo '{\"tool_input\":{\"file_path\":\"$REPO/src/foo.py\"}}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
}

@test "test-cohesion: paths outside repo root are ignored" {
    write_map <<'EOF'
[{"match":"src/*.py","tests":[],"runner":"custom","command":"false"}]
EOF
    call_hook "/tmp/outside/foo.py"
    [ "$status" -eq 0 ]
}
