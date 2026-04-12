#!/usr/bin/env bats
# Tests for project registry — registration, dedup, prune, list, update propagation

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_DIR="$(mktemp -d)"
    TMP_HOME="$(mktemp -d)"
    export HOME="$TMP_HOME"
    export AI_TOOLKIT_HOME="$TMP_HOME/.softspark/ai-toolkit"
    mkdir -p "$AI_TOOLKIT_HOME" "$TMP_HOME/.claude"
}

teardown() {
    rm -rf "$TEST_DIR" "$TMP_HOME"
}

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@test "registry: install --local registers project" {
    mkdir -p "$TEST_DIR/my-project"
    cd "$TEST_DIR/my-project"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks
    [ "$status" -eq 0 ]
    [[ "$output" == *"Registered"* ]]
    # Check projects.json exists
    [ -f "$AI_TOOLKIT_HOME/projects.json" ]
    python3 -c "
import json
with open('$AI_TOOLKIT_HOME/projects.json') as f:
    data = json.load(f)
assert len(data['projects']) == 1
assert data['projects'][0]['path'].endswith('my-project')
"
}

@test "registry: second install --local is idempotent (no duplicate)" {
    mkdir -p "$TEST_DIR/my-project"
    cd "$TEST_DIR/my-project"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks >/dev/null 2>&1
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks
    [ "$status" -eq 0 ]
    python3 -c "
import json
with open('$AI_TOOLKIT_HOME/projects.json') as f:
    data = json.load(f)
assert len(data['projects']) == 1, f'expected 1, got {len(data[\"projects\"])}'
"
}

@test "registry: multiple projects registered separately" {
    mkdir -p "$TEST_DIR/proj-a" "$TEST_DIR/proj-b"
    cd "$TEST_DIR/proj-a"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks >/dev/null 2>&1
    cd "$TEST_DIR/proj-b"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks >/dev/null 2>&1
    python3 -c "
import json
with open('$AI_TOOLKIT_HOME/projects.json') as f:
    data = json.load(f)
assert len(data['projects']) == 2, f'expected 2, got {len(data[\"projects\"])}'
"
}

# ---------------------------------------------------------------------------
# Projects CLI
# ---------------------------------------------------------------------------

@test "projects cli: lists registered projects" {
    mkdir -p "$TEST_DIR/proj-x"
    cd "$TEST_DIR/proj-x"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks >/dev/null 2>&1
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" projects
    [ "$status" -eq 0 ]
    [[ "$output" == *"proj-x"* ]]
    [[ "$output" == *"Registered projects (1)"* ]]
}

@test "projects cli: shows empty message when no projects" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" projects
    [ "$status" -eq 0 ]
    [[ "$output" == *"No registered projects"* ]]
}

@test "projects cli: detects stale projects" {
    mkdir -p "$TEST_DIR/proj-gone"
    cd "$TEST_DIR/proj-gone"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks >/dev/null 2>&1
    cd "$TEST_DIR"
    rm -rf "$TEST_DIR/proj-gone"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" projects
    [ "$status" -eq 0 ]
    [[ "$output" == *"MISSING"* ]]
    [[ "$output" == *"stale"* ]]
}

@test "projects cli: prune removes stale" {
    mkdir -p "$TEST_DIR/proj-keep" "$TEST_DIR/proj-gone"
    cd "$TEST_DIR/proj-keep"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks >/dev/null 2>&1
    cd "$TEST_DIR/proj-gone"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks >/dev/null 2>&1
    cd "$TEST_DIR"
    rm -rf "$TEST_DIR/proj-gone"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" projects --prune
    [ "$status" -eq 0 ]
    [[ "$output" == *"Pruned"* ]]
    # Verify only proj-keep remains
    python3 -c "
import json
with open('$AI_TOOLKIT_HOME/projects.json') as f:
    data = json.load(f)
assert len(data['projects']) == 1
assert data['projects'][0]['path'].endswith('proj-keep')
"
}

@test "projects cli: remove specific project" {
    mkdir -p "$TEST_DIR/proj-a" "$TEST_DIR/proj-b"
    cd "$TEST_DIR/proj-a"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks >/dev/null 2>&1
    cd "$TEST_DIR/proj-b"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks >/dev/null 2>&1
    # Remove proj-a
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" projects remove "$TEST_DIR/proj-a"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Removed"* ]]
    python3 -c "
import json
with open('$AI_TOOLKIT_HOME/projects.json') as f:
    data = json.load(f)
assert len(data['projects']) == 1
assert data['projects'][0]['path'].endswith('proj-b')
"
}

# ---------------------------------------------------------------------------
# Update propagation
# ---------------------------------------------------------------------------

@test "update_projects: updates registered projects in parallel" {
    mkdir -p "$TEST_DIR/proj-1" "$TEST_DIR/proj-2"
    cd "$TEST_DIR/proj-1"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks >/dev/null 2>&1
    cd "$TEST_DIR/proj-2"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks >/dev/null 2>&1
    run python3 "$TOOLKIT_DIR/scripts/update_projects.py" --skip agents,skills,hooks
    [ "$status" -eq 0 ]
    [[ "$output" == *"Updated: 2/2"* ]]
}

@test "update_projects: skips stale projects" {
    mkdir -p "$TEST_DIR/proj-ok" "$TEST_DIR/proj-gone"
    cd "$TEST_DIR/proj-ok"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks >/dev/null 2>&1
    cd "$TEST_DIR/proj-gone"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks >/dev/null 2>&1
    cd "$TEST_DIR"
    rm -rf "$TEST_DIR/proj-gone"
    run python3 "$TOOLKIT_DIR/scripts/update_projects.py" --skip agents,skills,hooks
    [ "$status" -eq 0 ]
    [[ "$output" == *"Pruned stale"* ]]
    [[ "$output" == *"Updated: 1/1"* ]]
}

# ---------------------------------------------------------------------------
# Extends info in registry
# ---------------------------------------------------------------------------

@test "registry: records extends source" {
    mkdir -p "$TEST_DIR/base-config" "$TEST_DIR/proj-ext"
    cat > "$TEST_DIR/base-config/ai-toolkit.config.json" << 'EOF'
{"name": "@test/base", "version": "1.0.0", "profile": "standard"}
EOF
    cat > "$TEST_DIR/proj-ext/.softspark-toolkit.json" << 'EOF'
{"extends": "../base-config", "profile": "standard"}
EOF
    cd "$TEST_DIR/proj-ext"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks >/dev/null 2>&1
    python3 -c "
import json
with open('$AI_TOOLKIT_HOME/projects.json') as f:
    data = json.load(f)
proj = data['projects'][0]
assert proj['extends'] == '../base-config', f'expected extends, got {proj}'
"
}
