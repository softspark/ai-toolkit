#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
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

@test "update_projects: explicit editors override saved project subset" {
    mkdir -p "$TEST_DIR/proj-override"
    register="$AI_TOOLKIT_HOME/projects.json"
    printf '{"projects":[{"path":"%s","profile":"full","editors":["codex"]}]}' \
        "$TEST_DIR/proj-override" > "$register"

    run python3 "$TOOLKIT_DIR/scripts/update_projects.py" \
        --editors windsurf --skip agents,skills,hooks
    [ "$status" -eq 0 ]
    [ -f "$TEST_DIR/proj-override/.windsurfrules" ]
    [ -f "$TEST_DIR/proj-override/.devin/hooks.v1.json" ]
}

@test "update_projects: retired dsh editor is dropped and its skill surfaces converge" {
    local root
    root="$(cd "$TEST_DIR" && pwd -P)"
    for spec in 'proj-dsh:dsh' 'proj-shared:shared'; do
        local project="$root/${spec%%:*}"
        mkdir -p "$project"
        python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$project" --enable >/dev/null
        # Rewrite into the layout releases with DSH support left behind.
        python3 - "$project" "${spec#*:}" <<'PY'
import sys
from pathlib import Path

agents = Path(sys.argv[1]) / ".agents"
kind = sys.argv[2]
marker = {"dsh": ".ai-toolkit-dsh-adapted", "shared": ".ai-toolkit-shared-adapted"}[kind]
for codex_marker in (agents / "skills").glob("*/.ai-toolkit-codex-adapted"):
    codex_marker.rename(codex_marker.with_name(marker))
(agents / ".ai-toolkit-skill-owners").write_text("dsh\n" if kind == "dsh" else "codex\ndsh\n")
PY
    done
    printf '{"projects":[{"path":"%s","profile":"standard","editors":["dsh"]},{"path":"%s","profile":"standard","editors":["codex","dsh"]}]}' \
        "$root/proj-dsh" "$root/proj-shared" > "$AI_TOOLKIT_HOME/projects.json"

    run python3 "$TOOLKIT_DIR/scripts/update_projects.py" --skip agents,skills,hooks
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Updated: 2/2'
    [ ! -e "$root/proj-dsh/.agents/.ai-toolkit-skill-owners" ]
    [ ! -e "$root/proj-dsh/.agents/skills/orchestrate" ]
    [ "$(cat "$root/proj-shared/.agents/.ai-toolkit-skill-owners")" = 'codex' ]
    [ -f "$root/proj-shared/.agents/skills/orchestrate/.ai-toolkit-codex-adapted" ]
    python3 - "$AI_TOOLKIT_HOME/projects.json" "$root" <<'PY'
import json
import sys

projects = json.load(open(sys.argv[1]))["projects"]
editors = {entry["path"]: entry["editors"] for entry in projects}
assert editors == {
    f"{sys.argv[2]}/proj-dsh": [],
    f"{sys.argv[2]}/proj-shared": ["codex"],
}, editors
PY
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

@test "registry: --skip-register prevents registration" {
    mkdir -p "$TEST_DIR/proj-skip"
    cd "$TEST_DIR/proj-skip"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip agents,skills,hooks --skip-register
    [ "$status" -eq 0 ]
    # projects.json should not exist (no registration happened)
    [ ! -f "$AI_TOOLKIT_HOME/projects.json" ]
}

@test "registry: concurrent register_project does not lose entries" {
    # Simulate the race condition that caused projects to disappear:
    # multiple threads calling register_project() simultaneously.
    python3 -c "
import sys, os, tempfile, json
from pathlib import Path
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
os.environ['HOME'] = '$TMP_HOME'
from install_steps.project_registry import register_project, load_registry

# Create 8 project directories (resolve symlinks for macOS /var -> /private/var)
dirs = []
for i in range(8):
    d = str(Path(tempfile.mkdtemp(prefix=f'proj-{i}-')).resolve())
    dirs.append(d)

# Register all concurrently
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(register_project, dirs))

# All 8 must survive
projects = load_registry()
paths = {p['path'] for p in projects}
for d in dirs:
    assert d in paths, f'Missing: {d}, got: {paths}'
assert len(projects) == 8, f'Expected 8, got {len(projects)}'
print('OK: all 8 entries survived concurrent registration')
"
}

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
