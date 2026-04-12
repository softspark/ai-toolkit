#!/usr/bin/env bats
# Tests for config CLI subcommands (validate, diff)

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_DIR="$(mktemp -d)"
    BASE_DIR="$TEST_DIR/base-config"
    PROJECT_DIR="$TEST_DIR/project"
    TMP_HOME="$(mktemp -d)"
    export AI_TOOLKIT_HOME="$TMP_HOME/.ai-toolkit"
    mkdir -p "$AI_TOOLKIT_HOME" "$BASE_DIR/rules" "$PROJECT_DIR"

    cat > "$BASE_DIR/ai-toolkit.config.json" << 'EOF'
{
  "name": "@test/base",
  "version": "2.0.0",
  "profile": "strict",
  "agents": {
    "enabled": ["backend-specialist", "security-auditor"]
  },
  "rules": {
    "inject": ["./rules/policy.md"]
  },
  "constitution": {
    "amendments": [
      {"article": 6, "title": "Data Sovereignty", "text": "GDPR."}
    ]
  },
  "enforce": {
    "minHookProfile": "standard",
    "requiredAgents": ["security-auditor"],
    "forbidOverride": ["constitution"]
  }
}
EOF
    echo "rule" > "$BASE_DIR/rules/policy.md"
}

teardown() {
    rm -rf "$TEST_DIR" "$TMP_HOME"
}

# ---------------------------------------------------------------------------
# config validate
# ---------------------------------------------------------------------------

@test "cli validate: valid config returns 0" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "profile": "standard",
  "agents": {
    "enabled": ["frontend-specialist"]
  }
}
EOF
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config validate "$PROJECT_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Config valid"* ]]
}

@test "cli validate: missing config returns 2" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config validate "$TEST_DIR/empty-dir-$(date +%s)"
    [ "$status" -eq 2 ]
    [[ "$output" == *"No .ai-toolkit.json"* ]]
}

@test "cli validate: blocked required agent returns 1" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "agents": {
    "disabled": ["security-auditor"]
  }
}
EOF
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config validate "$PROJECT_DIR"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Cannot disable"* ]]
}

@test "cli validate: constitution modification returns 1" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "constitution": {
    "amendments": [
      {"article": 6, "title": "Weakened", "text": "No GDPR."}
    ]
  }
}
EOF
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config validate "$PROJECT_DIR"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Cannot modify"* ]]
}

@test "cli validate: forbidden override returns 1" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "overrides": {
    "constitution": {
      "override": true,
      "justification": "We really want to override this constitution for good reasons"
    }
  }
}
EOF
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config validate "$PROJECT_DIR"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Cannot override"* ]]
}

# ---------------------------------------------------------------------------
# config diff
# ---------------------------------------------------------------------------

@test "cli diff: shows profile override" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "profile": "standard"
}
EOF
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config diff "$PROJECT_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Base: @test/base"* ]]
    [[ "$output" == *"strict (base)"* ]]
    [[ "$output" == *"standard (project)"* ]]
    [[ "$output" == *"OVERRIDE"* ]]
}

@test "cli diff: shows added agents" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "agents": {
    "enabled": ["frontend-specialist"]
  }
}
EOF
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config diff "$PROJECT_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"frontend-specialist"* ]]
    [[ "$output" == *"project adds"* ]]
}

@test "cli diff: shows constitution additions" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "constitution": {
    "amendments": [
      {"article": 9, "title": "Custom Rule", "text": "Something."}
    ]
  }
}
EOF
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config diff "$PROJECT_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Article 9: Custom Rule"* ]]
    [[ "$output" == *"project adds"* ]]
    [[ "$output" == *"Article 6: Data Sovereignty"* ]]
    [[ "$output" == *"inherited"* ]]
}

@test "cli diff: no extends shows message" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "profile": "standard"
}
EOF
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config diff "$PROJECT_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"No 'extends'"* ]]
}

# ---------------------------------------------------------------------------
# config help
# ---------------------------------------------------------------------------

@test "cli config: shows help without subcommand" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config
    [ "$status" -eq 0 ]
    [[ "$output" == *"validate"* ]]
    [[ "$output" == *"diff"* ]]
    [[ "$output" == *"init"* ]]
}

# ---------------------------------------------------------------------------
# config init
# ---------------------------------------------------------------------------

@test "cli init: creates config with --extends flag" {
    INIT_DIR="$TEST_DIR/init-project"
    mkdir -p "$INIT_DIR"
    cd "$INIT_DIR"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config init --extends "../base-config" --profile strict
    [ "$status" -eq 0 ]
    [ -f "$INIT_DIR/.ai-toolkit.json" ]
    python3 -c "
import json
with open('$INIT_DIR/.ai-toolkit.json') as f:
    config = json.load(f)
assert config['extends'] == '../base-config'
assert config['profile'] == 'strict'
"
}

@test "cli init: creates minimal config with --no-extends" {
    INIT_DIR="$TEST_DIR/init-minimal"
    mkdir -p "$INIT_DIR"
    cd "$INIT_DIR"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config init --no-extends --profile standard
    [ "$status" -eq 0 ]
    [ -f "$INIT_DIR/.ai-toolkit.json" ]
    python3 -c "
import json
with open('$INIT_DIR/.ai-toolkit.json') as f:
    config = json.load(f)
assert 'extends' not in config or config.get('extends') == ''
assert config['profile'] == 'standard'
"
}

@test "cli init: refuses to overwrite without --force" {
    INIT_DIR="$TEST_DIR/init-exists"
    mkdir -p "$INIT_DIR"
    echo '{"profile":"standard"}' > "$INIT_DIR/.ai-toolkit.json"
    cd "$INIT_DIR"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config init --no-extends
    [ "$status" -eq 1 ]
    [[ "$output" == *"already exists"* ]]
}

# ---------------------------------------------------------------------------
# config create-base
# ---------------------------------------------------------------------------

@test "cli create-base: scaffolds package" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config create-base "@test/my-config" "$TEST_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Created"* ]]
    [ -f "$TEST_DIR/test-my-config/package.json" ]
    [ -f "$TEST_DIR/test-my-config/ai-toolkit.config.json" ]
    [ -f "$TEST_DIR/test-my-config/README.md" ]
    [ -d "$TEST_DIR/test-my-config/rules" ]
    [ -d "$TEST_DIR/test-my-config/agents" ]
    # Validate package.json
    python3 -c "
import json
with open('$TEST_DIR/test-my-config/package.json') as f:
    pkg = json.load(f)
assert pkg['name'] == '@test/my-config'
assert '@softspark/ai-toolkit' in pkg['peerDependencies']
"
}

@test "cli create-base: generated config is valid" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config create-base "@test/valid-config" "$TEST_DIR"
    [ "$status" -eq 0 ]
    # Validate the generated base config
    run python3 "$TOOLKIT_DIR/scripts/config_validator.py" \
        "$TEST_DIR/test-valid-config/ai-toolkit.config.json"
    [ "$status" -eq 0 ]
    [[ "$output" == *"valid"* ]]
}

# ---------------------------------------------------------------------------
# config check
# ---------------------------------------------------------------------------

@test "cli check: passes on valid config" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "profile": "standard"
}
EOF
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config check "$PROJECT_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"passed"* ]]
}

@test "cli check: returns 2 without config" {
    EMPTY_DIR="$TEST_DIR/no-config-$(date +%s)"
    mkdir -p "$EMPTY_DIR"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config check "$EMPTY_DIR"
    [ "$status" -eq 2 ]
}

@test "cli check: fails on constitution conflict" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "constitution": {
    "amendments": [
      {"article": 6, "title": "Weakened", "text": "No GDPR."}
    ]
  }
}
EOF
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config check "$PROJECT_DIR"
    [ "$status" -eq 1 ]
    [[ "$output" == *"FAILED"* ]]
}

@test "cli check: JSON output mode" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "profile": "standard"
}
EOF
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config check "$PROJECT_DIR" --json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert data['status'] == 'pass'
assert data['code'] == 0
assert len(data['checks']) >= 3
"
}

# ---------------------------------------------------------------------------
# Lock file
# ---------------------------------------------------------------------------

@test "cli validate: handles invalid JSON gracefully" {
    echo '{broken' > "$PROJECT_DIR/.ai-toolkit.json"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config validate "$PROJECT_DIR"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Invalid JSON"* ]]
}

@test "cli check: handles invalid JSON gracefully" {
    echo '{broken' > "$PROJECT_DIR/.ai-toolkit.json"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config check "$PROJECT_DIR"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Invalid JSON"* ]]
}

@test "cli diff: handles invalid JSON gracefully" {
    echo '{broken' > "$PROJECT_DIR/.ai-toolkit.json"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config diff "$PROJECT_DIR"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Invalid JSON"* ]]
}

@test "cli check: reports missing lock file" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config"
}
EOF
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" config check "$PROJECT_DIR"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Lock file"* ]]
    [[ "$output" == *"missing"* ]]
}
