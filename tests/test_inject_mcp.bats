#!/usr/bin/env bats
# Tests for scripts/inject_mcp_cli.py (inject-mcp / remove-mcp)

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_DIR="$(mktemp -d)"
    export HOME="$TEST_DIR"
    export SOFTSPARK_HOME="$TEST_DIR/.softspark"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# ── Helper: create an MCP template JSON file ──────────────────────────────

_make_template_file() {
    # Usage: _make_template_file <path> <server-name> <url-or-command>
    local path="$1"
    local server_name="${2:-test-server}"
    local url="${3:-http://localhost:9999/mcp/sse}"
    cat > "$path" <<ENDJSON
{
    "name": "${server_name}",
    "description": "test template",
    "mcpServers": {
        "${server_name}": {
            "type": "http",
            "url": "${url}"
        }
    }
}
ENDJSON
}

_read_mcp_servers() {
    python3 -c "
import json
with open('$TEST_DIR/.mcp.json') as f:
    print(json.dumps(json.load(f)['mcpServers']))
"
}

# ── inject-mcp: basic injection ───────────────────────────────────────────

@test "inject_mcp_cli.py creates .mcp.json if missing" {
    _make_template_file "$TEST_DIR/rag-mcp.json" "rag-mcp"
    run python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" "$TEST_DIR/rag-mcp.json" "$TEST_DIR"
    [ "$status" -eq 0 ]
    [ -f "$TEST_DIR/.mcp.json" ]
}

@test "inject_mcp_cli.py tags every server with _source from filename stem" {
    _make_template_file "$TEST_DIR/rag-mcp-template.json" "rag-mcp"
    python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" \
        "$TEST_DIR/rag-mcp-template.json" "$TEST_DIR"
    python3 -c "
import json
with open('$TEST_DIR/.mcp.json') as f:
    data = json.load(f)
assert data['mcpServers']['rag-mcp']['_source'] == 'rag-mcp-template', data
"
}

@test "inject_mcp_cli.py --name overrides source for local files" {
    _make_template_file "$TEST_DIR/mcp-template.json" "rag-mcp"
    python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" \
        "$TEST_DIR/mcp-template.json" "$TEST_DIR" --name rag-mcp
    python3 -c "
import json
with open('$TEST_DIR/.mcp.json') as f:
    data = json.load(f)
assert data['mcpServers']['rag-mcp']['_source'] == 'rag-mcp', data
p = '$TEST_DIR/.softspark/ai-toolkit/mcp-templates/external/sources.json'
with open(p) as f:
    sources = json.load(f)
assert 'rag-mcp' in sources['templates'], sources
"
}

@test "inject_mcp_cli.py supports --force to overwrite different _source" {
    # First template adds 'shared' under source 'one'
    _make_template_file "$TEST_DIR/one.json" "shared" "http://a"
    python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" "$TEST_DIR/one.json" "$TEST_DIR"

    # Second template wants same key 'shared' under source 'two' -- collision
    _make_template_file "$TEST_DIR/two.json" "shared" "http://b"
    run python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" "$TEST_DIR/two.json" "$TEST_DIR"
    [ "$status" -eq 3 ]  # collision rejected

    # With --force succeeds
    run python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" \
        "$TEST_DIR/two.json" "$TEST_DIR" --force
    [ "$status" -eq 0 ]

    python3 -c "
import json
with open('$TEST_DIR/.mcp.json') as f:
    data = json.load(f)
assert data['mcpServers']['shared']['_source'] == 'two', data
assert data['mcpServers']['shared']['url'] == 'http://b', data
"
}

@test "inject_mcp_cli.py is idempotent (re-running same source overwrites cleanly)" {
    _make_template_file "$TEST_DIR/p.json" "alpha" "http://v1"
    python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" "$TEST_DIR/p.json" "$TEST_DIR"

    _make_template_file "$TEST_DIR/p.json" "alpha" "http://v2"
    python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" "$TEST_DIR/p.json" "$TEST_DIR"

    python3 -c "
import json
with open('$TEST_DIR/.mcp.json') as f:
    data = json.load(f)
servers = data['mcpServers']
assert servers['alpha']['url'] == 'http://v2', servers
# Only one server entry exists for source 'p'
sources = [s.get('_source') for s in servers.values()]
assert sources.count('p') == 1, sources
"
}

# ── inject-mcp: ai-toolkit protection ─────────────────────────────────────

@test "inject_mcp_cli.py refuses to overwrite ai-toolkit _source even with --force" {
    cat > "$TEST_DIR/.mcp.json" <<'JSON'
{
    "mcpServers": {
        "github": {
            "_source": "ai-toolkit",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"]
        }
    }
}
JSON
    _make_template_file "$TEST_DIR/conflict.json" "github" "http://attacker"
    run python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" \
        "$TEST_DIR/conflict.json" "$TEST_DIR" --force
    [ "$status" -eq 3 ]

    python3 -c "
import json
with open('$TEST_DIR/.mcp.json') as f:
    data = json.load(f)
assert data['mcpServers']['github']['_source'] == 'ai-toolkit', data
assert data['mcpServers']['github']['command'] == 'npx', data
"
}

@test "inject_mcp_cli.py rejects template named ai-toolkit.json" {
    _make_template_file "$TEST_DIR/ai-toolkit.json" "x"
    run python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" \
        "$TEST_DIR/ai-toolkit.json" "$TEST_DIR"
    [ "$status" -ne 0 ]
}

# ── inject-mcp: editor propagation ────────────────────────────────────────

@test "inject_mcp_cli.py propagates to cursor global config" {
    _make_template_file "$TEST_DIR/rag-mcp.json" "rag-mcp"
    python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" "$TEST_DIR/rag-mcp.json" "$TEST_DIR"
    [ -f "$TEST_DIR/.cursor/mcp.json" ]
    python3 -c "
import json
with open('$TEST_DIR/.cursor/mcp.json') as f:
    data = json.load(f)
assert 'rag-mcp' in data['mcpServers'], data
# _source MUST be stripped from native editor config
assert '_source' not in data['mcpServers']['rag-mcp'], data
"
}

@test "inject_mcp_cli.py propagates to codex global TOML" {
    _make_template_file "$TEST_DIR/rag-mcp.json" "rag-mcp"
    python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" "$TEST_DIR/rag-mcp.json" "$TEST_DIR"
    [ -f "$TEST_DIR/.codex/config.toml" ]
    grep -q "mcp_servers" "$TEST_DIR/.codex/config.toml"
    grep -q "rag-mcp" "$TEST_DIR/.codex/config.toml"
    # _source must not appear in native TOML
    ! grep -q "_source" "$TEST_DIR/.codex/config.toml"
}

# ── inject-mcp: sources registry ──────────────────────────────────────────

@test "inject_mcp_cli.py registers local-file source in sources.json" {
    _make_template_file "$TEST_DIR/myrag.json" "myrag"
    python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" "$TEST_DIR/myrag.json" "$TEST_DIR"
    [ -f "$TEST_DIR/.softspark/ai-toolkit/mcp-templates/external/sources.json" ]
    python3 -c "
import json
p = '$TEST_DIR/.softspark/ai-toolkit/mcp-templates/external/sources.json'
with open(p) as f:
    data = json.load(f)
assert 'myrag' in data['templates'], data
assert data['templates']['myrag']['path'].endswith('myrag.json'), data
"
}

# ── remove-mcp ────────────────────────────────────────────────────────────

@test "inject_mcp_cli.py --remove strips entries by source name" {
    _make_template_file "$TEST_DIR/tmpl.json" "removable"
    python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" "$TEST_DIR/tmpl.json" "$TEST_DIR"

    python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" --remove tmpl "$TEST_DIR"

    python3 -c "
import json
with open('$TEST_DIR/.mcp.json') as f:
    data = json.load(f)
assert 'removable' not in data['mcpServers'], data
"
    # editor configs cleaned too
    python3 -c "
import json
with open('$TEST_DIR/.cursor/mcp.json') as f:
    data = json.load(f)
assert 'removable' not in data.get('mcpServers', {}), data
"
}

@test "inject_mcp_cli.py --remove unregisters URL source from sources.json" {
    _make_template_file "$TEST_DIR/cached.json" "cached"
    python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" "$TEST_DIR/cached.json" "$TEST_DIR"
    python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" --remove cached "$TEST_DIR"

    python3 -c "
import json, os
p = '$TEST_DIR/.softspark/ai-toolkit/mcp-templates/external/sources.json'
if os.path.exists(p):
    with open(p) as f:
        data = json.load(f)
    assert 'cached' not in data.get('templates', {}), data
"
}

@test "inject_mcp_cli.py --remove refuses ai-toolkit source" {
    run python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" --remove ai-toolkit "$TEST_DIR"
    [ "$status" -ne 0 ]
}

# ── URL fetch via fixture map ─────────────────────────────────────────────

@test "inject_mcp_cli.py fetches HTTPS URL via test fixture and caches it" {
    _make_template_file "$TEST_DIR/remote-template.json" "remoterag"
    export AI_TOOLKIT_TEST_MODE=1
    export AI_TOOLKIT_TEST_URL_FIXTURE_MAP="{\"https://example.com/remote-template.json\": \"$TEST_DIR/remote-template.json\"}"

    run python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" \
        "https://example.com/remote-template.json" "$TEST_DIR"
    [ "$status" -eq 0 ]

    [ -f "$TEST_DIR/.softspark/ai-toolkit/mcp-templates/external/remote-template.json" ]

    python3 -c "
import json
with open('$TEST_DIR/.mcp.json') as f:
    data = json.load(f)
assert 'remoterag' in data['mcpServers'], data
assert data['mcpServers']['remoterag']['_source'] == 'remote-template', data
p = '$TEST_DIR/.softspark/ai-toolkit/mcp-templates/external/sources.json'
with open(p) as f:
    sources = json.load(f)
assert sources['templates']['remote-template']['url'] == 'https://example.com/remote-template.json', sources
"
}

@test "inject_mcp_cli.py rejects http:// URLs (HTTPS only)" {
    run python3 "$TOOLKIT_DIR/scripts/inject_mcp_cli.py" \
        "http://example.com/template.json" "$TEST_DIR"
    [ "$status" -ne 0 ]
}
