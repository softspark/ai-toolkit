#!/usr/bin/env bats
# Integration tests for install --local with .ai-toolkit.json extends

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_DIR="$(mktemp -d)"
    BASE_DIR="$TEST_DIR/base-config"
    PROJECT_DIR="$TEST_DIR/project"
    TMP_HOME="$(mktemp -d)"
    export HOME="$TMP_HOME"
    mkdir -p "$TMP_HOME/.ai-toolkit" "$TMP_HOME/.claude"
    mkdir -p "$BASE_DIR/rules" "$PROJECT_DIR"

    # Base config
    cat > "$BASE_DIR/ai-toolkit.config.json" << 'EOF'
{
  "name": "@test/base",
  "version": "2.0.0",
  "profile": "standard",
  "agents": {
    "enabled": ["backend-specialist", "security-auditor"]
  },
  "rules": {
    "inject": ["./rules/company-policy.md"]
  },
  "constitution": {
    "amendments": [
      {"article": 6, "title": "Data Sovereignty", "text": "GDPR compliance."},
      {"article": 7, "title": "Audit Compliance", "text": "All changes logged."}
    ]
  },
  "enforce": {
    "requiredAgents": ["security-auditor"],
    "minHookProfile": "standard"
  }
}
EOF
    echo "No console.log" > "$BASE_DIR/rules/company-policy.md"
}

teardown() {
    rm -rf "$TEST_DIR" "$TMP_HOME"
}

# ---------------------------------------------------------------------------
# Backwards compatibility
# ---------------------------------------------------------------------------

@test "install --local: works without .ai-toolkit.json (backwards compat)" {
    cd "$PROJECT_DIR"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks
    [ "$status" -eq 0 ]
    [ -f "$PROJECT_DIR/.claude/CLAUDE.md" ] || [ -f "$PROJECT_DIR/CLAUDE.md" ]
    # No extends metadata file
    [ ! -f "$PROJECT_DIR/.ai-toolkit-extends.json" ]
}

# ---------------------------------------------------------------------------
# Basic extends integration
# ---------------------------------------------------------------------------

@test "install --local: detects .ai-toolkit.json and resolves extends" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "profile": "standard"
}
EOF
    cd "$PROJECT_DIR"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks
    [ "$status" -eq 0 ]
    [[ "$output" == *"Resolving extends"* ]]
    [[ "$output" == *"@test/base"* ]]
}

@test "install --local: generates extends metadata file" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config"
}
EOF
    cd "$PROJECT_DIR"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks
    [ "$status" -eq 0 ]
    [ -f "$PROJECT_DIR/.ai-toolkit-extends.json" ]
    # Check metadata contains base config info
    python3 -c "
import json
with open('$PROJECT_DIR/.ai-toolkit-extends.json') as f:
    meta = json.load(f)
assert meta['source'] == '../base-config'
assert len(meta['configs']) == 1
assert meta['configs'][0]['name'] == '@test/base'
assert meta['configs'][0]['version'] == '2.0.0'
"
}

# ---------------------------------------------------------------------------
# Constitution amendments from base
# ---------------------------------------------------------------------------

@test "install --local: injects constitution amendments from base" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "constitution": {
    "amendments": [
      {"article": 8, "title": "API Standards", "text": "RESTful APIs required."}
    ]
  }
}
EOF
    cd "$PROJECT_DIR"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks
    [ "$status" -eq 0 ]
    [ -f "$PROJECT_DIR/.claude/constitution.md" ]

    # Check that base articles 6, 7 AND project article 8 are present
    grep -q "Article 6" "$PROJECT_DIR/.claude/constitution.md"
    grep -q "Data Sovereignty" "$PROJECT_DIR/.claude/constitution.md"
    grep -q "Article 7" "$PROJECT_DIR/.claude/constitution.md"
    grep -q "Article 8" "$PROJECT_DIR/.claude/constitution.md"
    grep -q "API Standards" "$PROJECT_DIR/.claude/constitution.md"
}

# ---------------------------------------------------------------------------
# Rules injection from base
# ---------------------------------------------------------------------------

@test "install --local: injects rules from base config" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config"
}
EOF
    cd "$PROJECT_DIR"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks
    [ "$status" -eq 0 ]

    # Check that base rules are mentioned in CLAUDE.md
    claude_md=""
    if [ -f "$PROJECT_DIR/.claude/CLAUDE.md" ]; then
        claude_md="$PROJECT_DIR/.claude/CLAUDE.md"
    elif [ -f "$PROJECT_DIR/CLAUDE.md" ]; then
        claude_md="$PROJECT_DIR/CLAUDE.md"
    fi
    [ -n "$claude_md" ]
    grep -q "extends-rules" "$claude_md"
    grep -q "company-policy.md" "$claude_md"
}

# ---------------------------------------------------------------------------
# Enforcement: blocks constraint violations
# ---------------------------------------------------------------------------

@test "install --local: blocks disabling required agent" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "agents": {
    "disabled": ["security-auditor"]
  }
}
EOF
    cd "$PROJECT_DIR"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks
    [ "$status" -ne 0 ]
    [[ "$output" == *"Cannot disable"* ]]
}

@test "install --local: blocks constitution modification" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "constitution": {
    "amendments": [
      {"article": 6, "title": "Weakened!", "text": "No GDPR."}
    ]
  }
}
EOF
    cd "$PROJECT_DIR"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks
    [ "$status" -ne 0 ]
    [[ "$output" == *"Cannot modify"* ]]
}

# ---------------------------------------------------------------------------
# State recording
# ---------------------------------------------------------------------------

@test "install --local: records extends info in state.json" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config"
}
EOF
    cd "$PROJECT_DIR"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks
    [ "$status" -eq 0 ]

    python3 -c "
import json
with open('$TMP_HOME/.ai-toolkit/state.json') as f:
    state = json.load(f)
assert 'extends' in state, f'no extends in state: {list(state.keys())}'
assert state['extends']['source'] == '../base-config'
assert len(state['extends']['configs']) == 1
"
}

# ---------------------------------------------------------------------------
# Idempotent re-install
# ---------------------------------------------------------------------------

@test "install --local: idempotent with extends (run twice)" {
    cat > "$PROJECT_DIR/.ai-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "constitution": {
    "amendments": [
      {"article": 8, "title": "API Standards", "text": "RESTful."}
    ]
  }
}
EOF
    cd "$PROJECT_DIR"
    # First install
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks
    [ "$status" -eq 0 ]

    # Second install (idempotent)
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks
    [ "$status" -eq 0 ]

    # Constitution should have exactly one of each article (no duplicates)
    count_art6=$(grep -c "Article 6" "$PROJECT_DIR/.claude/constitution.md" || true)
    count_art8=$(grep -c "Article 8" "$PROJECT_DIR/.claude/constitution.md" || true)
    [ "$count_art6" -eq 1 ]
    [ "$count_art8" -eq 1 ]
}
