#!/usr/bin/env bats
# Tests for app/hooks/ai-toolkit-statusline.sh — comprehensive Claude Code status line.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOK="$TOOLKIT_DIR/app/hooks/ai-toolkit-statusline.sh"
FIXTURES="$TOOLKIT_DIR/tests/fixtures/session-jsonl"

setup() {
    TEST_TMP="$(mktemp -d)"
    mkdir -p "$TEST_TMP/.claude/projects/-tmp-fakeproj"
    cp "$FIXTURES/three-messages.jsonl" "$TEST_TMP/.claude/projects/-tmp-fakeproj/sess.jsonl"
    export AI_TOOLKIT_DIR="$TOOLKIT_DIR"
    export AI_TOOLKIT_STATUSLINE_NO_COLOR=1
    export HOME="$TEST_TMP"
}

teardown() {
    rm -rf "$TEST_TMP"
    unset AI_TOOLKIT_STATUSLINE_DISABLE
    unset AI_TOOLKIT_STATUSLINE_BASELINE
    unset AI_TOOLKIT_STATUSLINE_NO_TOKENS
    unset AI_TOOLKIT_STATUSLINE_NO_GIT
}

# ── Existence ────────────────────────────────────────────────────────────────

@test "statusline: hook script exists and is executable" {
    [ -f "$HOOK" ]
    [ -x "$HOOK" ]
}

# ── Basic rendering ──────────────────────────────────────────────────────────

@test "statusline: emits one line for valid input" {
    run bash -c 'echo "{\"cwd\":\"/tmp/fakeproj\",\"model\":{\"display_name\":\"claude-opus-4-7\"},\"context_window\":{\"used_percentage\":24.5}}" | bash "'"$HOOK"'"'
    [ "$status" -eq 0 ]
    line_count=$(printf '%s' "$output" | wc -l | xargs)
    [ "$line_count" -le 1 ]
}

@test "statusline: shows directory basename" {
    run bash -c 'echo "{\"cwd\":\"/tmp/fakeproj\",\"model\":{\"display_name\":\"claude-opus-4-7\"}}" | bash "'"$HOOK"'"'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'fakeproj'
}

@test "statusline: shows model name" {
    run bash -c 'echo "{\"cwd\":\"/tmp/fakeproj\",\"model\":{\"display_name\":\"claude-opus-4-7\"}}" | bash "'"$HOOK"'"'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'claude-opus-4-7'
}

@test "statusline: shows context window percentage when given" {
    run bash -c 'echo "{\"cwd\":\"/tmp/fakeproj\",\"model\":{\"display_name\":\"claude-opus-4-7\"},\"context_window\":{\"used_percentage\":42}}" | bash "'"$HOOK"'"'
    [ "$status" -eq 0 ]
    echo "$output" | grep -qE 'ctx:42%'
}

@test "statusline: shows token count when session JSONL exists" {
    run bash -c 'echo "{\"cwd\":\"/tmp/fakeproj\",\"model\":{\"display_name\":\"claude-opus-4-7\"}}" | bash "'"$HOOK"'"'
    [ "$status" -eq 0 ]
    echo "$output" | grep -qE 'tok:750'
}

@test "statusline: shows cost estimate when tokens exist" {
    run bash -c 'echo "{\"cwd\":\"/tmp/fakeproj\",\"model\":{\"display_name\":\"claude-opus-4-7\"}}" | bash "'"$HOOK"'"'
    [ "$status" -eq 0 ]
    echo "$output" | grep -qE '\$[0-9]+\.[0-9]{2}'
}

# ── Opt-out flags ────────────────────────────────────────────────────────────

@test "statusline: AI_TOOLKIT_STATUSLINE_DISABLE=1 silences output" {
    export AI_TOOLKIT_STATUSLINE_DISABLE=1
    run bash -c 'echo "{\"cwd\":\"/tmp/fakeproj\"}" | bash "'"$HOOK"'"'
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "statusline: AI_TOOLKIT_STATUSLINE_NO_TOKENS=1 hides token segment" {
    export AI_TOOLKIT_STATUSLINE_NO_TOKENS=1
    run bash -c 'echo "{\"cwd\":\"/tmp/fakeproj\",\"model\":{\"display_name\":\"claude-opus-4-7\"}}" | bash "'"$HOOK"'"'
    [ "$status" -eq 0 ]
    ! echo "$output" | grep -qE 'tok:'
}

@test "statusline: AI_TOOLKIT_STATUSLINE_NO_GIT=1 hides git segment" {
    export AI_TOOLKIT_STATUSLINE_NO_GIT=1
    run bash -c 'cd "'"$TOOLKIT_DIR"'" && echo "{\"cwd\":\"'"$TOOLKIT_DIR"'\",\"model\":{\"display_name\":\"claude-opus-4-7\"}}" | bash "'"$HOOK"'"'
    [ "$status" -eq 0 ]
    ! echo "$output" | grep -qE 'git:'
}

# ── Soft-fail behavior ───────────────────────────────────────────────────────

@test "statusline: soft-fails when no session exists" {
    rm -rf "$TEST_TMP/.claude"
    run bash -c 'echo "{\"cwd\":\"/tmp/missing\",\"model\":{\"display_name\":\"claude-opus-4-7\"}}" | bash "'"$HOOK"'"'
    [ "$status" -eq 0 ]
    # still renders dir + model, just no token segment
    echo "$output" | grep -q 'missing'
    echo "$output" | grep -q 'claude-opus-4-7'
    ! echo "$output" | grep -qE 'tok:'
}

@test "statusline: handles empty stdin without crash" {
    run bash -c 'echo "" | bash "'"$HOOK"'"'
    [ "$status" -eq 0 ]
}

@test "statusline: handles malformed JSON stdin without crash" {
    run bash -c 'echo "not json at all" | bash "'"$HOOK"'"'
    [ "$status" -eq 0 ]
}

# ── Pricing ──────────────────────────────────────────────────────────────────

@test "statusline: opus pricing differs from haiku for same tokens" {
    run bash -c 'echo "{\"cwd\":\"/tmp/fakeproj\",\"model\":{\"display_name\":\"claude-opus-4-7\"}}" | bash "'"$HOOK"'"'
    opus_cost=$(echo "$output" | grep -oE '\$[0-9]+\.[0-9]{2}' | head -1)
    run bash -c 'echo "{\"cwd\":\"/tmp/fakeproj\",\"model\":{\"display_name\":\"claude-haiku-4-5\"}}" | bash "'"$HOOK"'"'
    haiku_cost=$(echo "$output" | grep -oE '\$[0-9]+\.[0-9]{2}' | head -1)
    [ "$opus_cost" != "$haiku_cost" ]
}
