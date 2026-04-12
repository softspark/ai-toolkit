#!/usr/bin/env bats
# Tests for config resolver — local path resolution, cache, cycle detection

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_DIR="$(mktemp -d)"
    TMP_HOME="$(mktemp -d)"
    export AI_TOOLKIT_HOME="$TMP_HOME/.ai-toolkit"
    mkdir -p "$AI_TOOLKIT_HOME"
}

teardown() {
    rm -rf "$TEST_DIR" "$TMP_HOME"
}

# ---------------------------------------------------------------------------
# Local path resolution
# ---------------------------------------------------------------------------

@test "resolver: resolves local path extends" {
    mkdir -p "$TEST_DIR/base-config" "$TEST_DIR/project"
    cat > "$TEST_DIR/base-config/ai-toolkit.config.json" << 'EOF'
{
  "name": "@test/base",
  "version": "1.0.0",
  "profile": "strict"
}
EOF
    cat > "$TEST_DIR/project/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config"
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_resolver.py" "$TEST_DIR/project"
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert len(data['configs']) == 1
assert data['configs'][0]['name'] == '@test/base'
assert data['configs'][0]['version'] == '1.0.0'
"
}

@test "resolver: local path not found gives error" {
    mkdir -p "$TEST_DIR/project"
    cat > "$TEST_DIR/project/.ai-toolkit.json" << 'EOF'
{
  "extends": "../nonexistent"
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_resolver.py" "$TEST_DIR/project"
    [ "$status" -eq 1 ]
    [[ "$output" == *"error"* ]]
    [[ "$output" == *"not found"* ]]
}

@test "resolver: missing config file in extends dir gives error" {
    mkdir -p "$TEST_DIR/empty-base" "$TEST_DIR/project"
    cat > "$TEST_DIR/project/.ai-toolkit.json" << 'EOF'
{
  "extends": "../empty-base"
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_resolver.py" "$TEST_DIR/project"
    [ "$status" -eq 1 ]
    [[ "$output" == *"error"* ]]
    [[ "$output" == *"not found"* ]]
}

# ---------------------------------------------------------------------------
# Chain resolution
# ---------------------------------------------------------------------------

@test "resolver: resolves extends chain (grandparent -> parent -> project)" {
    mkdir -p "$TEST_DIR/grandparent" "$TEST_DIR/parent" "$TEST_DIR/project"

    cat > "$TEST_DIR/grandparent/ai-toolkit.config.json" << 'EOF'
{
  "name": "@test/grandparent",
  "version": "0.1.0",
  "profile": "minimal"
}
EOF
    cat > "$TEST_DIR/parent/ai-toolkit.config.json" << 'EOF'
{
  "name": "@test/parent",
  "version": "1.0.0",
  "extends": "../grandparent",
  "profile": "standard"
}
EOF
    cat > "$TEST_DIR/project/.ai-toolkit.json" << 'EOF'
{
  "extends": "../parent"
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_resolver.py" "$TEST_DIR/project"
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert len(data['configs']) == 2, f'expected 2 configs, got {len(data[\"configs\"])}'
# Deepest ancestor first
assert data['configs'][0]['name'] == '@test/grandparent'
assert data['configs'][1]['name'] == '@test/parent'
"
}

# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------

@test "resolver: detects circular extends" {
    mkdir -p "$TEST_DIR/config-a" "$TEST_DIR/config-b" "$TEST_DIR/project"

    cat > "$TEST_DIR/config-a/ai-toolkit.config.json" << 'EOF'
{
  "name": "@test/config-a",
  "version": "1.0.0",
  "extends": "../config-b"
}
EOF
    cat > "$TEST_DIR/config-b/ai-toolkit.config.json" << 'EOF'
{
  "name": "@test/config-b",
  "version": "1.0.0",
  "extends": "../config-a"
}
EOF
    cat > "$TEST_DIR/project/.ai-toolkit.json" << 'EOF'
{
  "extends": "../config-a"
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_resolver.py" "$TEST_DIR/project"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Circular"* ]]
}

# ---------------------------------------------------------------------------
# No extends field
# ---------------------------------------------------------------------------

@test "resolver: config without extends returns empty" {
    mkdir -p "$TEST_DIR/project"
    cat > "$TEST_DIR/project/.ai-toolkit.json" << 'EOF'
{
  "profile": "standard"
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_resolver.py" "$TEST_DIR/project"
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert data['configs'] == []
"
}

@test "resolver: no .ai-toolkit.json returns error" {
    mkdir -p "$TEST_DIR/project"
    run python3 "$TOOLKIT_DIR/scripts/config_resolver.py" "$TEST_DIR/project"
    [ "$status" -eq 1 ]
    [[ "$output" == *"No .ai-toolkit.json"* ]]
}
