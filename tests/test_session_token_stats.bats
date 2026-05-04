#!/usr/bin/env bats
# Tests for scripts/session_token_stats.py — Claude Code session JSONL parser.
#
# Covers:
#   - Aggregation across well-formed JSONL
#   - Malformed line tolerance
#   - Empty file handling
#   - --statusline output shape
#   - --json output schema
#   - Trend calculation against baseline
#   - Recency filter via --since
#   - Exit codes for missing sessions

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SCRIPT="python3 $TOOLKIT_DIR/scripts/session_token_stats.py"
FIXTURES="$TOOLKIT_DIR/tests/fixtures/session-jsonl"

setup() {
    TEST_TMP="$(mktemp -d)"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# ── Aggregation ─────────────────────────────────────────────────────────────

@test "session-stats: aggregates well-formed JSONL" {
    run $SCRIPT --session "$FIXTURES/three-messages.jsonl" --json
    [ "$status" -eq 0 ]
    total=$(echo "$output" | python3 -c 'import json,sys; print(json.load(sys.stdin)["totals"]["total"])')
    [ "$total" = "750" ]
}

@test "session-stats: counts only usage-bearing messages" {
    # Substring prefilter for "usage" skips non-token-bearing lines pre-parse
    # for performance, so messages_total reflects messages we deserialized,
    # not raw line count. The fixture has 5 lines; 3 carry token usage.
    run $SCRIPT --session "$FIXTURES/three-messages.jsonl" --json
    counted=$(echo "$output" | python3 -c 'import json,sys; print(json.load(sys.stdin)["totals"]["messages_counted"])')
    [ "$counted" = "3" ]
}

@test "session-stats: includes cache tokens in total_with_cache" {
    run $SCRIPT --session "$FIXTURES/three-messages.jsonl" --json
    with_cache=$(echo "$output" | python3 -c 'import json,sys; print(json.load(sys.stdin)["totals"]["total_with_cache"])')
    [ "$with_cache" = "7250" ]
}

# ── Malformed input ──────────────────────────────────────────────────────────

@test "session-stats: skips malformed JSON lines without crashing" {
    run $SCRIPT --session "$FIXTURES/malformed.jsonl" --json
    [ "$status" -eq 0 ]
    total=$(echo "$output" | python3 -c 'import json,sys; print(json.load(sys.stdin)["totals"]["total"])')
    [ "$total" = "150" ]
}

@test "session-stats: empty session returns zero totals" {
    run $SCRIPT --session "$FIXTURES/empty.jsonl" --json
    [ "$status" -eq 0 ]
    total=$(echo "$output" | python3 -c 'import json,sys; print(json.load(sys.stdin)["totals"]["total"])')
    [ "$total" = "0" ]
}

# ── Statusline output ────────────────────────────────────────────────────────

@test "session-stats: statusline output is one short line" {
    run $SCRIPT --session "$FIXTURES/three-messages.jsonl" --statusline
    [ "$status" -eq 0 ]
    line_count=$(printf '%s\n' "$output" | wc -l | xargs)
    [ "$line_count" = "1" ]
    char_count=$(printf '%s' "$output" | wc -c | xargs)
    [ "$char_count" -le 80 ]
}

@test "session-stats: statusline shows token count with k suffix when ≥1000" {
    # craft a fixture with >1000 tokens
    cat > "$TEST_TMP/big.jsonl" <<EOF
{"type":"assistant","message":{"usage":{"input_tokens":5000,"output_tokens":3000}}}
EOF
    run $SCRIPT --session "$TEST_TMP/big.jsonl" --statusline
    [ "$status" -eq 0 ]
    echo "$output" | grep -qE '8\.0k'
}

@test "session-stats: statusline shows raw count when <1000" {
    run $SCRIPT --session "$FIXTURES/three-messages.jsonl" --statusline
    [ "$status" -eq 0 ]
    echo "$output" | grep -qE 'session: 750'
}

# ── Baseline / trend ─────────────────────────────────────────────────────────

@test "session-stats: trend arrow shows down when current < baseline" {
    cat > "$TEST_TMP/baseline.json" <<EOF
{"total": 1500}
EOF
    run $SCRIPT --session "$FIXTURES/three-messages.jsonl" --statusline --baseline "$TEST_TMP/baseline.json"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '↓'
}

@test "session-stats: trend arrow shows up when current > baseline" {
    cat > "$TEST_TMP/baseline.json" <<EOF
{"total": 100}
EOF
    run $SCRIPT --session "$FIXTURES/three-messages.jsonl" --statusline --baseline "$TEST_TMP/baseline.json"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '↑'
}

@test "session-stats: missing baseline file is silently ignored" {
    run $SCRIPT --session "$FIXTURES/three-messages.jsonl" --statusline --baseline /nonexistent/baseline.json
    [ "$status" -eq 0 ]
    echo "$output" | grep -qE 'session: 750'
}

# ── Recency filter ───────────────────────────────────────────────────────────

@test "session-stats: --since drops messages older than window" {
    # all fixture timestamps are 2026-05-04, "1m" cutoff drops everything since now > then
    run $SCRIPT --session "$FIXTURES/three-messages.jsonl" --since 1m --json
    [ "$status" -eq 0 ]
    total=$(echo "$output" | python3 -c 'import json,sys; print(json.load(sys.stdin)["totals"]["total"])')
    [ "$total" = "0" ]
}

@test "session-stats: --since rejects bad duration" {
    run $SCRIPT --session "$FIXTURES/three-messages.jsonl" --since 7days
    [ "$status" -eq 2 ]
}

# ── Discovery / exit codes ───────────────────────────────────────────────────

@test "session-stats: exits 1 when no Claude project found" {
    run $SCRIPT --claude-dir /tmp/nonexistent-dir-xyz --cwd /tmp/foo
    [ "$status" -eq 1 ]
}

@test "session-stats: discovers latest session when --project-dir given" {
    mkdir -p "$TEST_TMP/proj"
    cp "$FIXTURES/three-messages.jsonl" "$TEST_TMP/proj/sess1.jsonl"
    sleep 0.1
    cp "$FIXTURES/three-messages.jsonl" "$TEST_TMP/proj/sess2.jsonl"
    run $SCRIPT --project-dir "$TEST_TMP/proj" --json
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'sess2.jsonl'
}
