#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for app/hooks/ai-toolkit-statusline.sh — comprehensive Claude Code status line.
#
# The hook reads native Claude Code statusLine input on stdin (full schema:
# cwd, model, context_window.{used_percentage,total_input_tokens,
# total_output_tokens}, cost.total_cost_usd, effort.level). It does NOT parse
# session JSONL. Tests provide synthetic stdin matching that schema.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOK="$TOOLKIT_DIR/app/hooks/ai-toolkit-statusline.sh"

setup() {
    TEST_TMP="$(mktemp -d)"
    export AI_TOOLKIT_DIR="$TOOLKIT_DIR"
    export AI_TOOLKIT_STATUSLINE_NO_COLOR=1
    export HOME="$TEST_TMP"
    export AI_TOOLKIT_HOME="$TEST_TMP/.softspark/ai-toolkit"
    unset CLAUDE_CONFIG_DIR
    export COLUMNS=120
    export -f make_usage_input
}

make_usage_input() {
    printf '%s' '{"session_id":"statusline-session","cwd":"/tmp/profile-project","model":{"display_name":"Opus"},"rate_limits":{"five_hour":{"used_percentage":42,"resets_at":4102444800},"seven_day":{"used_percentage":18,"resets_at":4102531200}}}'
}

teardown() {
    rm -rf "$TEST_TMP"
    unset AI_TOOLKIT_STATUSLINE_DISABLE
    unset AI_TOOLKIT_STATUSLINE_NO_TOKENS
    unset AI_TOOLKIT_STATUSLINE_NO_GIT
    unset AI_TOOLKIT_STATUSLINE_NO_EFFORT
    unset AI_TOOLKIT_STATUSLINE_SHOW_COST
    unset AI_TOOLKIT_STATUSLINE_BASELINE
}

# Convenience: full Claude Code-shape stdin matching what 2.1.126 sends.
make_input() {
    local cwd="${1:-/tmp/fakeproj}"
    local model="${2:-Opus 4.7}"
    local ctx="${3:-42}"
    local in_tok="${4:-1500}"
    local out_tok="${5:-50000}"
    local cost="${6:-12.34}"
    local effort="${7:-medium}"
    cat <<EOF
{
  "cwd": "$cwd",
  "model": {"display_name": "$model"},
  "context_window": {
    "used_percentage": $ctx,
    "total_input_tokens": $in_tok,
    "total_output_tokens": $out_tok
  },
  "cost": {"total_cost_usd": $cost},
  "effort": {"level": "$effort"}
}
EOF
}

# ── Existence ────────────────────────────────────────────────────────────────

@test "statusline: hook script exists and is executable" {
    [ -f "$HOOK" ]
    [ -x "$HOOK" ]
}

# ── Basic rendering ──────────────────────────────────────────────────────────

@test "statusline: emits one line for valid input" {
    run bash -c "$(declare -f make_input); make_input | bash '$HOOK'"
    [ "$status" -eq 0 ]
    line_count=$(printf '%s' "$output" | wc -l | xargs)
    [ "$line_count" -le 1 ]
}

@test "statusline: shows directory basename" {
    run bash -c "$(declare -f make_input); make_input '/tmp/myproj' | bash '$HOOK'"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'myproj'
}

@test "statusline: shows model name" {
    run bash -c "$(declare -f make_input); make_input '/tmp/p' 'Opus 4.7 (1M context)' | bash '$HOOK'"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Opus 4.7'
}

@test "statusline: shows ctx as progress bar with percent" {
    run bash -c "$(declare -f make_input); make_input '/tmp/p' 'Opus' 73 | bash '$HOOK'"
    [ "$status" -eq 0 ]
    # progress bar uses unicode block + percent label
    echo "$output" | grep -qE '73%'
    echo "$output" | grep -q '█'
    echo "$output" | grep -q '░'
}

@test "statusline: progress bar fills proportionally to ctx percent" {
    # 90% should produce more █ than 20%
    high=$(bash -c "$(declare -f make_input); make_input '/tmp/p' 'Opus' 90 | bash '$HOOK'" | tr -cd '█' | wc -c | xargs)
    low=$(bash -c "$(declare -f make_input); make_input '/tmp/p' 'Opus' 20 | bash '$HOOK'" | tr -cd '█' | wc -c | xargs)
    [ "$high" -gt "$low" ]
}

@test "statusline: shows up/down arrows with token counts" {
    run bash -c "$(declare -f make_input); make_input '/tmp/p' 'Opus' 50 6466 221869 | bash '$HOOK'"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '↑6.5k'
    echo "$output" | grep -q '↓221.9k'
}

@test "statusline: shows token trend against configured baseline" {
    printf '{"total":1000}\n' > "$TEST_TMP/baseline.json"
    export AI_TOOLKIT_STATUSLINE_BASELINE="$TEST_TMP/baseline.json"

    run bash -c "$(declare -f make_input); make_input '/tmp/p' 'Opus' 50 1500 500 | bash '$HOOK'"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'trend:↑100%'
}

@test "statusline: preserves trend when optional cost and effort are absent" {
    printf '{"total":1000}\n' > "$TEST_TMP/baseline.json"
    export AI_TOOLKIT_STATUSLINE_BASELINE="$TEST_TMP/baseline.json"

    run bash -c \
        "printf '%s' '{\"cwd\":\"/tmp/p\",\"model\":{\"display_name\":\"Opus\"},\"context_window\":{\"used_percentage\":50,\"total_input_tokens\":1500,\"total_output_tokens\":500}}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'trend:↑100%'
}

@test "statusline: shows effort level" {
    run bash -c "$(declare -f make_input); make_input '/tmp/p' 'Opus' 50 1000 1000 0 xhigh | bash '$HOOK'"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'effort:xhigh'
}

# ── Cost opt-in ──────────────────────────────────────────────────────────────

@test "statusline: hides cost segment by default" {
    run bash -c "$(declare -f make_input); make_input | bash '$HOOK'"
    [ "$status" -eq 0 ]
    ! echo "$output" | grep -qE '\$[0-9]+\.[0-9]{2}'
}

@test "statusline: shows cost when AI_TOOLKIT_STATUSLINE_SHOW_COST=1" {
    export AI_TOOLKIT_STATUSLINE_SHOW_COST=1
    run bash -c "$(declare -f make_input); make_input '/tmp/p' 'Opus' 50 1000 1000 49.06 | bash '$HOOK'"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '\$49.06'
}

# ── Opt-out flags ────────────────────────────────────────────────────────────

@test "statusline: AI_TOOLKIT_STATUSLINE_DISABLE=1 silences output" {
    export AI_TOOLKIT_STATUSLINE_DISABLE=1
    run bash -c "$(declare -f make_input); make_input | bash '$HOOK'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "statusline: AI_TOOLKIT_STATUSLINE_NO_TOKENS=1 hides token arrows" {
    export AI_TOOLKIT_STATUSLINE_NO_TOKENS=1
    run bash -c "$(declare -f make_input); make_input | bash '$HOOK'"
    [ "$status" -eq 0 ]
    ! echo "$output" | grep -q '↑'
    ! echo "$output" | grep -q '↓'
}

@test "statusline: AI_TOOLKIT_STATUSLINE_NO_EFFORT=1 hides effort segment" {
    export AI_TOOLKIT_STATUSLINE_NO_EFFORT=1
    run bash -c "$(declare -f make_input); make_input | bash '$HOOK'"
    [ "$status" -eq 0 ]
    ! echo "$output" | grep -q 'effort:'
}

@test "statusline: AI_TOOLKIT_STATUSLINE_NO_GIT=1 hides git segment" {
    export AI_TOOLKIT_STATUSLINE_NO_GIT=1
    run bash -c "$(declare -f make_input); make_input '$TOOLKIT_DIR' | bash '$HOOK'"
    [ "$status" -eq 0 ]
    ! echo "$output" | grep -qE 'git:'
}

# ── Soft-fail behavior ───────────────────────────────────────────────────────

@test "statusline: handles empty stdin without crash" {
    run bash -c "echo '' | bash '$HOOK'"
    [ "$status" -eq 0 ]
}

@test "statusline: handles malformed JSON stdin without crash" {
    run bash -c "echo 'not json at all' | bash '$HOOK'"
    [ "$status" -eq 0 ]
}

@test "statusline: renders active profile without writing a quota cache" {
    export CLAUDE_CONFIG_DIR="$TEST_TMP/custom-profile"
    run bash -c 'make_usage_input | bash "$1"' -- "$HOOK"
    [ "$status" -eq 0 ]
    [[ "$output" == *"profile-project"* ]]
    [[ "$output" == *"Opus"* ]]
    [ ! -e "$AI_TOOLKIT_HOME/claude-usage" ]
}

@test "statusline: installed hook needs no quota collector and creates no cache" {
    mkdir -p "$AI_TOOLKIT_HOME/hooks"
    cp "$HOOK" "$AI_TOOLKIT_HOME/hooks/ai-toolkit-statusline.sh"
    unset AI_TOOLKIT_DIR
    run bash -c 'make_usage_input | bash "$1"' -- "$AI_TOOLKIT_HOME/hooks/ai-toolkit-statusline.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"profile-project"* ]]
    [ ! -e "$AI_TOOLKIT_HOME/claude-usage" ]
}

@test "statusline: historical quota files are preserved unchanged" {
    mkdir -p "$TEST_TMP/isolated/hooks"
    mkdir -p "$AI_TOOLKIT_HOME/claude-usage/profile"
    printf '%s' '{"historical":true}' > "$AI_TOOLKIT_HOME/claude-usage/profile/session.json"
    cp "$HOOK" "$TEST_TMP/isolated/hooks/ai-toolkit-statusline.sh"
    unset AI_TOOLKIT_DIR
    run bash -c 'make_usage_input | bash "$1"' -- "$TEST_TMP/isolated/hooks/ai-toolkit-statusline.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"profile-project"* ]]
    [[ "$output" == *"Opus"* ]]
    [ "$(cat "$AI_TOOLKIT_HOME/claude-usage/profile/session.json")" = '{"historical":true}' ]
    [ "$(find "$AI_TOOLKIT_HOME/claude-usage" -type f | wc -l | tr -d ' ')" = 1 ]
}

@test "statusline: rendering needs no writable toolkit storage" {
    touch "$TEST_TMP/blocked-cache"
    export AI_TOOLKIT_HOME="$TEST_TMP/blocked-cache"
    run bash -c 'make_usage_input | bash "$1"' -- "$HOOK"
    [ "$status" -eq 0 ]
    [[ "$output" == *"profile-project"* ]]
    [[ "$output" == *"Opus"* ]]
}

@test "statusline: disabled rendering creates no quota cache" {
    export AI_TOOLKIT_STATUSLINE_DISABLE=1
    run bash -c 'make_usage_input | bash "$1"' -- "$HOOK"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -d "$AI_TOOLKIT_HOME/claude-usage" ]
}

@test "statusline: omits token segment when both tokens are zero" {
    run bash -c "$(declare -f make_input); make_input '/tmp/p' 'Opus' 0 0 0 | bash '$HOOK'"
    [ "$status" -eq 0 ]
    ! echo "$output" | grep -q '↑'
}

# ── Right-align ──────────────────────────────────────────────────────────────

@test "statusline: trailer order is effort then model" {
    run bash -c "$(declare -f make_input); make_input '/tmp/p' 'Opus 4.7' 50 1000 50000 12 high | bash '$HOOK'"
    [ "$status" -eq 0 ]
    plain=$(echo "$output" | sed -E 's/\x1b\[[0-9;]*[a-zA-Z]//g')
    # effort: appears before the model name in the trailer
    effort_pos=$(echo "$plain" | awk '{ print index($0, "effort:") }')
    model_pos=$(echo "$plain" | awk '{ print index($0, "Opus 4.7") }')
    [ "$effort_pos" -gt 0 ]
    [ "$model_pos" -gt "$effort_pos" ]
}
