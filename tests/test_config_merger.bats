#!/usr/bin/env bats
# Tests for config merger — merge engine, constitution immutability, override validation

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_DIR="$(mktemp -d)"
    BASE_DIR="$TEST_DIR/base-config"
    PROJECT_DIR="$TEST_DIR/project"
    mkdir -p "$BASE_DIR/rules" "$BASE_DIR/agents" "$PROJECT_DIR"

    # Base config
    cat > "$BASE_DIR/ai-toolkit.config.json" << 'EOF'
{
  "name": "@test/base-config",
  "version": "1.0.0",
  "profile": "strict",
  "agents": {
    "enabled": ["backend-specialist", "security-auditor", "test-engineer"]
  },
  "rules": {
    "inject": ["./rules/company-policy.md"]
  },
  "constitution": {
    "amendments": [
      {"article": 6, "title": "Data Sovereignty", "text": "GDPR compliance required."}
    ]
  },
  "enforce": {
    "minHookProfile": "standard",
    "requiredAgents": ["security-auditor"],
    "forbidOverride": ["constitution", "guard-destructive"],
    "requiredPlugins": ["security-pack"]
  }
}
EOF
    echo "rule content" > "$BASE_DIR/rules/company-policy.md"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# ---------------------------------------------------------------------------
# Merge engine: basic merge
# ---------------------------------------------------------------------------

@test "merge: project adds agents to base" {
    cat > "$PROJECT_DIR/.softspark-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "agents": {
    "enabled": ["frontend-specialist"]
  }
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" \
        "$BASE_DIR/ai-toolkit.config.json" "$PROJECT_DIR/.softspark-toolkit.json"
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "
import sys, json
data = json.load(sys.stdin)
agents = data['merged']['agents']['enabled']
assert 'frontend-specialist' in agents, f'missing frontend-specialist: {agents}'
assert 'backend-specialist' in agents, f'missing backend-specialist: {agents}'
assert 'security-auditor' in agents, f'missing security-auditor: {agents}'
"
}

@test "merge: project can disable non-required agents" {
    cat > "$PROJECT_DIR/.softspark-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "agents": {
    "disabled": ["test-engineer"]
  }
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" \
        "$BASE_DIR/ai-toolkit.config.json" "$PROJECT_DIR/.softspark-toolkit.json"
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "
import sys, json
data = json.load(sys.stdin)
agents = data['merged']['agents']['enabled']
assert 'test-engineer' not in agents, f'test-engineer should be disabled: {agents}'
assert 'security-auditor' in agents, f'security-auditor should remain: {agents}'
"
}

@test "merge: rules are unioned" {
    cat > "$PROJECT_DIR/.softspark-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "rules": {
    "inject": ["./rules/api-standards.md"]
  }
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" \
        "$BASE_DIR/ai-toolkit.config.json" "$PROJECT_DIR/.softspark-toolkit.json"
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "
import sys, json
data = json.load(sys.stdin)
rules = data['merged']['rules']['inject']
assert './rules/company-policy.md' in rules, f'missing company-policy: {rules}'
assert './rules/api-standards.md' in rules, f'missing api-standards: {rules}'
"
}

@test "merge: project profile overrides base" {
    cat > "$PROJECT_DIR/.softspark-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "profile": "standard"
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" \
        "$BASE_DIR/ai-toolkit.config.json" "$PROJECT_DIR/.softspark-toolkit.json"
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert data['merged']['profile'] == 'standard', f'expected standard, got {data[\"merged\"][\"profile\"]}'
"
}

@test "merge: project adds constitution articles" {
    cat > "$PROJECT_DIR/.softspark-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "constitution": {
    "amendments": [
      {"article": 8, "title": "API Standards", "text": "All APIs must be RESTful."}
    ]
  }
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" \
        "$BASE_DIR/ai-toolkit.config.json" "$PROJECT_DIR/.softspark-toolkit.json"
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "
import sys, json
data = json.load(sys.stdin)
articles = {a['article']: a for a in data['merged']['constitution']['amendments']}
assert 6 in articles, 'base article 6 missing'
assert 8 in articles, 'project article 8 missing'
assert articles[6]['title'] == 'Data Sovereignty', 'base article 6 modified'
assert articles[8]['title'] == 'API Standards', 'project article 8 wrong'
"
}

# ---------------------------------------------------------------------------
# Constitution immutability
# ---------------------------------------------------------------------------

@test "constitution: cannot modify base article" {
    cat > "$PROJECT_DIR/.softspark-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "constitution": {
    "amendments": [
      {"article": 6, "title": "Weakened!", "text": "No GDPR needed."}
    ]
  }
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" \
        "$BASE_DIR/ai-toolkit.config.json" "$PROJECT_DIR/.softspark-toolkit.json"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Cannot modify Constitution Article 6"* ]]
}

@test "constitution: cannot modify immutable articles I-V" {
    cat > "$PROJECT_DIR/.softspark-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "constitution": {
    "amendments": [
      {"article": 3, "title": "Hijacked", "text": "Override safety."}
    ]
  }
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" \
        "$BASE_DIR/ai-toolkit.config.json" "$PROJECT_DIR/.softspark-toolkit.json"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Cannot modify Constitution Article 3"* ]]
    [[ "$output" == *"immutable"* ]]
}

# ---------------------------------------------------------------------------
# Override validation
# ---------------------------------------------------------------------------

@test "override: forbidden override is blocked" {
    cat > "$PROJECT_DIR/.softspark-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "overrides": {
    "constitution": {
      "override": true,
      "justification": "We really need to override this for compliance reasons"
    }
  }
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" \
        "$BASE_DIR/ai-toolkit.config.json" "$PROJECT_DIR/.softspark-toolkit.json"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Cannot override 'constitution'"* ]]
    [[ "$output" == *"forbidden"* ]]
}

@test "override: missing justification is rejected" {
    cat > "$PROJECT_DIR/.softspark-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "overrides": {
    "quality-check": {
      "override": true,
      "justification": "short"
    }
  }
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" \
        "$BASE_DIR/ai-toolkit.config.json" "$PROJECT_DIR/.softspark-toolkit.json"
    [ "$status" -eq 1 ]
    [[ "$output" == *"justification"* ]]
}

@test "override: missing override:true is rejected" {
    cat > "$PROJECT_DIR/.softspark-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "overrides": {
    "quality-check": {
      "justification": "Company uses custom lint pipeline via Jenkins setup"
    }
  }
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" \
        "$BASE_DIR/ai-toolkit.config.json" "$PROJECT_DIR/.softspark-toolkit.json"
    [ "$status" -eq 1 ]
    [[ "$output" == *"override: true"* ]]
}

@test "override: valid override passes" {
    cat > "$PROJECT_DIR/.softspark-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "overrides": {
    "quality-check": {
      "override": true,
      "justification": "Company uses custom lint pipeline via Jenkins, not the toolkit default",
      "replacement": "skip"
    }
  }
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" \
        "$BASE_DIR/ai-toolkit.config.json" "$PROJECT_DIR/.softspark-toolkit.json"
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert len(data['overrides_applied']) == 1
assert data['overrides_applied'][0]['key'] == 'quality-check'
"
}

# ---------------------------------------------------------------------------
# Enforce constraints
# ---------------------------------------------------------------------------

@test "enforce: cannot disable required agent" {
    cat > "$PROJECT_DIR/.softspark-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "agents": {
    "disabled": ["security-auditor"]
  }
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" \
        "$BASE_DIR/ai-toolkit.config.json" "$PROJECT_DIR/.softspark-toolkit.json"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Cannot disable agent 'security-auditor'"* ]]
    [[ "$output" == *"required"* ]]
}

@test "enforce: enforce blocks merge (cannot weaken)" {
    # Base has minHookProfile=standard. Project enforce tries to set minimal.
    cat > "$PROJECT_DIR/.softspark-toolkit.json" << 'EOF'
{
  "extends": "../base-config",
  "enforce": {
    "minHookProfile": "minimal"
  }
}
EOF
    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" \
        "$BASE_DIR/ai-toolkit.config.json" "$PROJECT_DIR/.softspark-toolkit.json"
    [ "$status" -eq 0 ]
    # Merged enforce should keep the stricter profile
    echo "$output" | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert data['merged']['enforce']['minHookProfile'] == 'standard', \
    f'Expected standard, got {data[\"merged\"][\"enforce\"][\"minHookProfile\"]}'
"
}
