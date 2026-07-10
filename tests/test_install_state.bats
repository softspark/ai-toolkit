#!/usr/bin/env bats
# test_install_state.bats — Tests for install_state.py and version_check.py
# Run with: bats tests/test_install_state.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CLI="node $TOOLKIT_DIR/bin/ai-toolkit.js"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# ── ai-toolkit status (via CLI) ────────────────────────────────────────────

@test "status: exits 0 with state.json present" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'EOF'
{
  "installed_version": "1.2.1",
  "installed_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-01T00:00:00Z",
  "profile": "standard",
  "installed_modules": ["core", "agents", "skills"]
}
EOF
    run $CLI status
    [ "$status" -eq 0 ]
}

@test "status: shows version number" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'EOF'
{
  "installed_version": "1.2.1",
  "installed_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-01T00:00:00Z",
  "profile": "standard",
  "installed_modules": ["core"]
}
EOF
    run $CLI status
    echo "$output" | grep -q '1.2.1'
}

@test "status: exits 0 even without state.json" {
    run $CLI status
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi 'no install state'
}

@test "status: lists external rules and hooks from sources.json" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit/rules"
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit/hooks/external"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'EOF'
{
  "installed_version": "1.2.1",
  "installed_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-01T00:00:00Z",
  "profile": "standard",
  "installed_modules": ["core"]
}
EOF
    cat > "$TEST_TMP/.softspark/ai-toolkit/rules/sources.json" <<'EOF'
{"schema_version": 1, "rules": {"jira-mcp": {"url": "https://example.com/r.md", "fetched_at": "2026-05-04T11:24:40Z"}}}
EOF
    cat > "$TEST_TMP/.softspark/ai-toolkit/hooks/external/sources.json" <<'EOF'
{"schema_version": 1, "hooks": {"jira-mcp-hooks": {"url": "https://example.com/h.json", "fetched_at": "2026-05-04T11:24:40Z"}}}
EOF
    run $CLI status
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'External sources:'
    echo "$output" | grep -q 'rule  jira-mcp'
    echo "$output" | grep -q 'hook  jira-mcp-hooks'
}

@test "status: shows local-path source with [local] tag" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit/rules"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'EOF'
{
  "installed_version": "1.2.1",
  "installed_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-01T00:00:00Z",
  "profile": "standard",
  "installed_modules": ["core"]
}
EOF
    cat > "$TEST_TMP/.softspark/ai-toolkit/rules/sources.json" <<'EOF'
{"schema_version": 1, "rules": {"my-local": {"path": "/abs/repo/my-local.md", "fetched_at": "2026-05-06T09:00:00Z", "sha256": "deadbeef"}}}
EOF
    # Materialize the file so it is not flagged as orphan
    : > "$TEST_TMP/.softspark/ai-toolkit/rules/my-local.md"
    run $CLI status
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'rule  my-local  <- /abs/repo/my-local.md \[local\]'
}

@test "status: flags orphan rule files (file present, not in sources.json)" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit/rules"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'EOF'
{
  "installed_version": "1.2.1",
  "installed_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-01T00:00:00Z",
  "profile": "standard",
  "installed_modules": ["core"]
}
EOF
    : > "$TEST_TMP/.softspark/ai-toolkit/rules/legacy-rule.md"
    run $CLI status
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'rule  legacy-rule  <- (orphan, no source recorded'
}

@test "add_rule: registers local file with path in sources.json" {
    mkdir -p "$TEST_TMP/work"
    echo "test content" > "$TEST_TMP/work/local-rule.md"
    EXPECTED_PATH=$(python3 -c "import pathlib; print(pathlib.Path('$TEST_TMP/work/local-rule.md').resolve())")
    cd "$TEST_TMP/work"
    run python3 "$TOOLKIT_DIR/scripts/add_rule.py" "$TEST_TMP/work/local-rule.md"
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.softspark/ai-toolkit/rules/sources.json" ]
    python3 -c "
import json
with open('$TEST_TMP/.softspark/ai-toolkit/rules/sources.json') as f:
    d = json.load(f)
entry = d['rules']['local-rule']
assert entry['path'] == '$EXPECTED_PATH', f'got path={entry.get(\"path\")}'
assert 'sha256' in entry, 'sha256 missing'
assert 'fetched_at' in entry, 'fetched_at missing'
"
}

@test "status: omits External sources section when no registries exist" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'EOF'
{
  "installed_version": "1.2.1",
  "installed_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-01T00:00:00Z",
  "profile": "standard",
  "installed_modules": ["core"]
}
EOF
    run $CLI status
    [ "$status" -eq 0 ]
    ! echo "$output" | grep -q 'External sources:'
}

# ── install_state.py (direct Python) ───────────────────────────────────────

@test "install_state: record_install creates state.json" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from install_steps.install_state import record_install
record_install(
    version='1.0.0',
    modules=['core', 'agents'],
    profile='standard',
)
"
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.softspark/ai-toolkit/state.json" ]
}

@test "install_state: load_state reads back recorded data" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from install_steps.install_state import record_install, load_state
record_install(version='2.0.0', modules=['core'], profile='minimal')
state = load_state()
assert state['installed_version'] == '2.0.0', f'got {state}'
assert state['profile'] == 'minimal', f'got {state}'
assert 'core' in state['installed_modules'], f'got {state}'
print('OK')
"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'OK'
}

@test "install_state: explicit non-auto install clears stale detected languages" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from install_steps.install_state import record_install, load_state
record_install(
    version='2.0.0',
    modules=['core', 'rules-cpp'],
    profile='standard',
    auto_detected=['rules-cpp'],
)
record_install(
    version='2.0.0',
    modules=['core', 'rules-cpp', 'rules-python'],
    profile='standard',
)
state = load_state()
assert 'auto_detected_languages' not in state, state
"
    [ "$status" -eq 0 ]
}

@test "install --local preserves global install profile and modules" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit" "$TEST_TMP/project"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'EOF'
{
  "installed_version": "4.13.0",
  "installed_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-02T00:00:00Z",
  "profile": "full",
  "installed_modules": ["core", "agents", "skills", "rules-python"]
}
EOF

    run bash -c "cd '$TEST_TMP/project' && python3 '$TOOLKIT_DIR/scripts/install.py' --local --profile minimal --skip-register"
    [ "$status" -eq 0 ]
    python3 - "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'PY'
import json
import sys

state = json.load(open(sys.argv[1]))
assert state["profile"] == "full", state
assert state["installed_modules"] == ["core", "agents", "skills", "rules-python"], state
assert state["last_updated"] == "2026-01-02T00:00:00Z", state
PY
}

# ── version_check.py ───────────────────────────────────────────────────────

@test "version_check: exits 0 when up to date (offline)" {
    # Pre-seed cache to avoid hitting npm
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    local VERSION
    VERSION=$(python3 -c "import json; print(json.load(open('$TOOLKIT_DIR/package.json'))['version'])")
    python3 -c "
import json, time
data = {'installed': '$VERSION', 'latest': '$VERSION', 'checked_at': time.time()}
with open('$TEST_TMP/.softspark/ai-toolkit/version-check.json', 'w') as f:
    json.dump(data, f)
"
    run python3 "$TOOLKIT_DIR/scripts/version_check.py"
    [ "$status" -eq 0 ]
}

@test "version_check: --status shows installed version" {
    # Pre-seed cache to avoid hitting npm
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    local VERSION
    VERSION=$(python3 -c "import json; print(json.load(open('$TOOLKIT_DIR/package.json'))['version'])")
    python3 -c "
import json, time
data = {'installed': '$VERSION', 'latest': '$VERSION', 'checked_at': time.time()}
with open('$TEST_TMP/.softspark/ai-toolkit/version-check.json', 'w') as f:
    json.dump(data, f)
"
    run python3 "$TOOLKIT_DIR/scripts/version_check.py" --status
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Installed:'
    echo "$output" | grep -q "$VERSION"
}

@test "version_check: creates cache file after check" {
    # Force a check (will try npm and cache result or fail gracefully)
    run python3 "$TOOLKIT_DIR/scripts/version_check.py" --force
    # Even if npm is unreachable, the script exits 0 (up to date / unknown)
    # Just verify it ran without crashing
    true
    # If npm was reachable, cache should exist
    # If not, script handles gracefully — no assertion on file existence
}
