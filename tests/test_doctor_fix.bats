#!/usr/bin/env bats
# Tests for doctor --fix auto-repair mode
# Optimized: install runs once in setup_file, each test restores from snapshot.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export DOCTOR_SNAPSHOT
    DOCTOR_SNAPSHOT="$(mktemp -d)"
    export HOME="$DOCTOR_SNAPSHOT"
    python3 "$TOOLKIT_DIR/scripts/install.py" "$DOCTOR_SNAPSHOT" >/dev/null 2>&1
}

teardown_file() {
    rm -rf "$DOCTOR_SNAPSHOT"
}

setup() {
    TEST_TMP="$(mktemp -d)"
    cp -a "$DOCTOR_SNAPSHOT/." "$TEST_TMP/"
    export HOME="$TEST_TMP"
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "doctor --fix repairs broken agent symlink" {
    ln -sf "/nonexistent/agent.md" "$TEST_TMP/.claude/agents/test-broken.md"
    [ -L "$TEST_TMP/.claude/agents/test-broken.md" ]
    [ ! -e "$TEST_TMP/.claude/agents/test-broken.md" ]
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED"
    [ ! -L "$TEST_TMP/.claude/agents/test-broken.md" ]
}

@test "doctor --fix repairs broken skill symlink" {
    ln -sf "/nonexistent/skill" "$TEST_TMP/.claude/skills/test-broken"
    [ -L "$TEST_TMP/.claude/skills/test-broken" ]
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED"
    [ ! -L "$TEST_TMP/.claude/skills/test-broken" ]
}

@test "doctor --fix makes non-executable hook executable" {
    chmod -x "$TEST_TMP/.ai-toolkit/hooks/guard-destructive.sh"
    [ ! -x "$TEST_TMP/.ai-toolkit/hooks/guard-destructive.sh" ]
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED.*executable"
    [ -x "$TEST_TMP/.ai-toolkit/hooks/guard-destructive.sh" ]
}

@test "doctor --fix restores missing hook script" {
    rm "$TEST_TMP/.ai-toolkit/hooks/guard-destructive.sh"
    [ ! -f "$TEST_TMP/.ai-toolkit/hooks/guard-destructive.sh" ]
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED.*restored"
    [ -x "$TEST_TMP/.ai-toolkit/hooks/guard-destructive.sh" ]
}

@test "doctor --fix regenerates missing llms-full.txt" {
    [ -f "$TOOLKIT_DIR/llms-full.txt" ] && cp "$TOOLKIT_DIR/llms-full.txt" "$TOOLKIT_DIR/llms-full.txt.test-bak"
    rm -f "$TOOLKIT_DIR/llms-full.txt"
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED.*llms-full.txt"
    [ -f "$TOOLKIT_DIR/llms-full.txt" ]
    [ -f "$TOOLKIT_DIR/llms-full.txt.test-bak" ] && mv "$TOOLKIT_DIR/llms-full.txt.test-bak" "$TOOLKIT_DIR/llms-full.txt"
}

@test "doctor without --fix does not modify anything" {
    ln -sf "/nonexistent/agent.md" "$TEST_TMP/.claude/agents/test-broken.md"
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    [ -L "$TEST_TMP/.claude/agents/test-broken.md" ]
    echo "$output" | grep -q "WARN.*broken"
    ! echo "$output" | grep -q "FIXED"
}

@test "doctor --fix shows fix mode in summary" {
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "auto-repair"
}

@test "cli: help lists --fix option for doctor" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" help
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '\-\-fix'
}
