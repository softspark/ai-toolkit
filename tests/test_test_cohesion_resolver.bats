#!/usr/bin/env bats
# test_test_cohesion_resolver.bats — Tests for scripts/test_cohesion.py
# Run with: bats tests/test_test_cohesion_resolver.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
RESOLVE="python3 $TOOLKIT_DIR/scripts/test_cohesion.py resolve"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    mkdir -p "$TEST_TMP/.claude"
}

teardown() {
    rm -rf "$TEST_TMP"
}

write_map() {
    cat > "$TEST_TMP/.claude/test-cohesion-map.json"
}

@test "resolver: project map matches exact path" {
    write_map <<'EOF'
[
    {"match": "src/foo.py", "tests": ["tests/test_foo.py"], "runner": "pytest"}
]
EOF
    run $RESOLVE --changed-paths "$TEST_TMP/src/foo.py" --repo-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" == *"tests/test_foo.py"* ]]
    [[ "$output" == *"pytest"* ]]
}

@test "resolver: glob pattern matches" {
    write_map <<'EOF'
[
    {"match": "src/*.py", "tests": ["tests/all_unit.py"], "runner": "pytest"}
]
EOF
    run $RESOLVE --changed-paths "$TEST_TMP/src/anything.py" --repo-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" == *"tests/all_unit.py"* ]]
}

@test "resolver: first-match-wins (specific before glob)" {
    write_map <<'EOF'
[
    {"match": "src/critical.py", "tests": ["tests/test_critical.py"], "runner": "pytest"},
    {"match": "src/*.py", "tests": ["tests/all.py"], "runner": "pytest"}
]
EOF
    run $RESOLVE --changed-paths "$TEST_TMP/src/critical.py" --repo-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" == *"tests/test_critical.py"* ]]
    [[ "$output" != *"tests/all.py"* ]]
}

@test "resolver: no match exits 1" {
    write_map <<'EOF'
[
    {"match": "src/*.py", "tests": ["tests/all.py"], "runner": "pytest"}
]
EOF
    run $RESOLVE --changed-paths "$TEST_TMP/docs/foo.md" --repo-root "$TEST_TMP"
    [ "$status" -eq 1 ]
}

@test "resolver: no map exits 1" {
    rm -f "$TEST_TMP/.claude/test-cohesion-map.json"
    # Also clear any default toolkit map by pointing AI_TOOLKIT_DIR elsewhere
    AI_TOOLKIT_DIR="$TEST_TMP" run $RESOLVE --changed-paths "$TEST_TMP/x.py" --repo-root "$TEST_TMP"
    [ "$status" -eq 1 ]
}

@test "resolver: installed runtime map under hooks/ is supported" {
    rm -f "$TEST_TMP/.claude/test-cohesion-map.json"
    mkdir -p "$TEST_TMP/hooks"
    cat > "$TEST_TMP/hooks/test-cohesion-map.json" <<'EOF'
[
    {"match": "src/*.py", "tests": ["tests/test_runtime.py"], "runner": "pytest"}
]
EOF
    AI_TOOLKIT_DIR="$TEST_TMP" run $RESOLVE --changed-paths "$TEST_TMP/src/x.py" --repo-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" == *"tests/test_runtime.py"* ]]
}

@test "resolver: command override bypasses runner default" {
    write_map <<'EOF'
[
    {"match": "src/*.py", "tests": [], "runner": "custom", "command": "echo CUSTOM RAN"}
]
EOF
    run $RESOLVE --changed-paths "$TEST_TMP/src/x.py" --repo-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" == *"echo CUSTOM RAN"* ]]
}

@test "resolver: multiple matching paths merge tests under same runner" {
    write_map <<'EOF'
[
    {"match": "src/a.py", "tests": ["tests/test_a.py"], "runner": "pytest"},
    {"match": "src/b.py", "tests": ["tests/test_b.py"], "runner": "pytest"}
]
EOF
    run $RESOLVE --changed-paths "$TEST_TMP/src/a.py" "$TEST_TMP/src/b.py" --repo-root "$TEST_TMP"
    [ "$status" -eq 0 ]
    [[ "$output" == *"tests/test_a.py"* ]]
    [[ "$output" == *"tests/test_b.py"* ]]
    # one command line (one runner)
    line_count=$(echo "$output" | wc -l | tr -d ' ')
    [ "$line_count" -eq 1 ]
}
