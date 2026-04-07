#!/usr/bin/env bats
# test_mcp_manager.bats — Tests for scripts/mcp_manager.py
# Run with: bats tests/test_mcp_manager.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
MCP_MANAGER="python3 $TOOLKIT_DIR/scripts/mcp_manager.py"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# ── list ────────────────────────────────────────────────────────────────────

@test "mcp list: exits 0" {
    run $MCP_MANAGER list
    [ "$status" -eq 0 ]
}

@test "mcp list: shows 25 templates" {
    run $MCP_MANAGER list
    echo "$output" | grep -q '25 templates available'
}

@test "mcp list: output contains github" {
    run $MCP_MANAGER list
    echo "$output" | grep -q 'github'
}

@test "mcp list: output contains postgres" {
    run $MCP_MANAGER list
    echo "$output" | grep -q 'postgres'
}

@test "mcp list: output contains slack" {
    run $MCP_MANAGER list
    echo "$output" | grep -q 'slack'
}

# ── show ────────────────────────────────────────────────────────────────────

@test "mcp show github: exits 0 and shows mcpServers config" {
    run $MCP_MANAGER show github
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'mcpServers'
}

@test "mcp show github: shows required env vars" {
    run $MCP_MANAGER show github
    echo "$output" | grep -q 'GITHUB_PERSONAL_ACCESS_TOKEN'
}

@test "mcp show nonexistent: exits non-zero" {
    run $MCP_MANAGER show nonexistent-server-xyz
    [ "$status" -ne 0 ]
}

# ── add ─────────────────────────────────────────────────────────────────────

@test "mcp add github: creates .mcp.json with github config" {
    run $MCP_MANAGER add github --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.mcp.json" ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.mcp.json'))
assert 'github' in cfg['mcpServers'], 'github not in mcpServers'
"
    [ "$status" -eq 0 ]
}

@test "mcp add github postgres: adds both servers" {
    run $MCP_MANAGER add github postgres --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.mcp.json'))
assert 'github' in cfg['mcpServers'], 'github missing'
assert 'postgres' in cfg['mcpServers'], 'postgres missing'
"
    [ "$status" -eq 0 ]
}

@test "mcp add github: is idempotent (re-running does not duplicate)" {
    run $MCP_MANAGER add github --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    run $MCP_MANAGER add github --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.mcp.json'))
# Only one 'github' key should exist (dict keys are unique)
assert list(cfg['mcpServers'].keys()).count('github') == 1
"
    [ "$status" -eq 0 ]
}

# ── remove ──────────────────────────────────────────────────────────────────

@test "mcp remove github: removes server from .mcp.json" {
    # First add github
    run $MCP_MANAGER add github --target "$TEST_TMP"
    [ "$status" -eq 0 ]

    # Then remove it
    run $MCP_MANAGER remove github --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.mcp.json'))
assert 'github' not in cfg['mcpServers'], 'github still present after remove'
"
    [ "$status" -eq 0 ]
}

@test "mcp remove nonexistent: exits non-zero" {
    # Create a valid .mcp.json first
    run $MCP_MANAGER add github --target "$TEST_TMP"
    [ "$status" -eq 0 ]

    run $MCP_MANAGER remove nonexistent-server-xyz --target "$TEST_TMP"
    [ "$status" -ne 0 ]
}

# ── error handling ──────────────────────────────────────────────────────────

@test "mcp: without subcommand exits non-zero" {
    run $MCP_MANAGER
    [ "$status" -ne 0 ]
}

# ── template validation ────────────────────────────────────────────────────

@test "mcp: all template JSON files are valid" {
    run python3 -c "
import json, sys
from pathlib import Path
templates_dir = Path('$TOOLKIT_DIR/app/mcp-templates')
errors = []
for p in sorted(templates_dir.glob('*.json')):
    try:
        data = json.load(open(p, encoding='utf-8'))
        assert 'name' in data, f'{p.name}: missing name'
        assert 'mcpServers' in data, f'{p.name}: missing mcpServers'
    except Exception as e:
        errors.append(f'{p.name}: {e}')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
"
    [ "$status" -eq 0 ]
}
