#!/usr/bin/env bats
# Tests for scripts/inject_hook_cli.py (inject-hook / remove-hook)

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_DIR="$(mktemp -d)"
    mkdir -p "$TEST_DIR/.claude"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# ── Helper: create a hooks JSON file ──────────────────────────────────────

_make_hooks_file() {
    # Usage: _make_hooks_file <path> [event] [command]
    local path="$1"
    local event="${2:-PreToolUse}"
    local command="${3:-echo hello}"
    cat > "$path" <<ENDJSON
{
    "hooks": {
        "${event}": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "${command}"
                    }
                ]
            }
        ]
    }
}
ENDJSON
}

# ── inject-hook: basic injection ──────────────────────────────────────────

@test "inject_hook_cli.py creates settings.json if missing" {
    rm -f "$TEST_DIR/.claude/settings.json"
    _make_hooks_file "$TEST_DIR/my-hooks.json"
    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/my-hooks.json" "$TEST_DIR"
    [ "$status" -eq 0 ]
    [ -f "$TEST_DIR/.claude/settings.json" ]
}

@test "inject_hook_cli.py adds entries with correct _source tag" {
    _make_hooks_file "$TEST_DIR/rag-mcp-hooks.json" "PreToolUse" "echo rag"
    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/rag-mcp-hooks.json" "$TEST_DIR"
    [ "$status" -eq 0 ]
    # Verify _source tag is set to filename stem
    python3 -c "
import json, sys
with open('$TEST_DIR/.claude/settings.json') as f:
    data = json.load(f)
entries = data['hooks']['PreToolUse']
sources = [e.get('_source') for e in entries]
assert 'rag-mcp-hooks' in sources, f'Expected rag-mcp-hooks in {sources}'
"
}

@test "inject_hook_cli.py is idempotent (re-running does not duplicate)" {
    _make_hooks_file "$TEST_DIR/my-plugin.json" "Stop" "echo done"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/my-plugin.json" "$TEST_DIR"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/my-plugin.json" "$TEST_DIR"
    count=$(python3 -c "
import json
with open('$TEST_DIR/.claude/settings.json') as f:
    data = json.load(f)
print(len([e for e in data['hooks']['Stop'] if e.get('_source') == 'my-plugin']))
")
    [ "$count" -eq 1 ]
}

@test "inject_hook_cli.py updates entries on re-injection" {
    # First injection with one command
    _make_hooks_file "$TEST_DIR/updatable.json" "Stop" "echo v1"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/updatable.json" "$TEST_DIR"

    # Second injection with different command
    _make_hooks_file "$TEST_DIR/updatable.json" "Stop" "echo v2"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/updatable.json" "$TEST_DIR"

    # Verify only v2 is present
    python3 -c "
import json
with open('$TEST_DIR/.claude/settings.json') as f:
    data = json.load(f)
entries = data['hooks']['Stop']
commands = [h['command'] for e in entries for h in e.get('hooks', [])]
assert 'echo v2' in commands, f'Expected v2 in {commands}'
assert 'echo v1' not in commands, f'Did not expect v1 in {commands}'
"
}

# ── inject-hook: ai-toolkit protection ────────────────────────────────────

@test "inject_hook_cli.py does not touch ai-toolkit entries" {
    # Pre-populate with an ai-toolkit entry
    cat > "$TEST_DIR/.claude/settings.json" <<'JSON'
{
    "hooks": {
        "PreToolUse": [
            {
                "_source": "ai-toolkit",
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": "echo guard"
                    }
                ]
            }
        ]
    }
}
JSON
    _make_hooks_file "$TEST_DIR/external.json" "PreToolUse" "echo ext"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/external.json" "$TEST_DIR"

    # Both ai-toolkit and external entries should exist
    python3 -c "
import json
with open('$TEST_DIR/.claude/settings.json') as f:
    data = json.load(f)
entries = data['hooks']['PreToolUse']
sources = [e.get('_source') for e in entries]
assert 'ai-toolkit' in sources, f'ai-toolkit entry missing: {sources}'
assert 'external' in sources, f'external entry missing: {sources}'
"
}

@test "inject_hook_cli.py rejects hooks file named ai-toolkit.json" {
    _make_hooks_file "$TEST_DIR/ai-toolkit.json"
    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/ai-toolkit.json" "$TEST_DIR"
    [ "$status" -ne 0 ]
}

# ── inject-hook: preserves other settings keys ────────────────────────────

@test "inject_hook_cli.py preserves non-hooks keys in settings.json" {
    cat > "$TEST_DIR/.claude/settings.json" <<'JSON'
{
    "permissions": {
        "allow": ["Bash"]
    },
    "hooks": {}
}
JSON
    _make_hooks_file "$TEST_DIR/my-hooks.json"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/my-hooks.json" "$TEST_DIR"

    python3 -c "
import json
with open('$TEST_DIR/.claude/settings.json') as f:
    data = json.load(f)
assert 'permissions' in data, 'permissions key was lost'
assert data['permissions']['allow'] == ['Bash'], 'permissions content changed'
"
}

# ── inject-hook: multiple sources coexist ─────────────────────────────────

@test "inject_hook_cli.py multiple sources coexist" {
    _make_hooks_file "$TEST_DIR/plugin-a.json" "Stop" "echo a"
    _make_hooks_file "$TEST_DIR/plugin-b.json" "Stop" "echo b"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/plugin-a.json" "$TEST_DIR"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/plugin-b.json" "$TEST_DIR"

    python3 -c "
import json
with open('$TEST_DIR/.claude/settings.json') as f:
    data = json.load(f)
sources = [e.get('_source') for e in data['hooks']['Stop']]
assert 'plugin-a' in sources, f'plugin-a missing: {sources}'
assert 'plugin-b' in sources, f'plugin-b missing: {sources}'
"
}

# ── remove-hook: basic removal ────────────────────────────────────────────

@test "remove-hook strips only matching _source entries" {
    _make_hooks_file "$TEST_DIR/removeme.json" "Stop" "echo bye"
    _make_hooks_file "$TEST_DIR/keepme.json" "Stop" "echo keep"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/removeme.json" "$TEST_DIR"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/keepme.json" "$TEST_DIR"

    # Remove only "removeme"
    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" --remove removeme "$TEST_DIR"
    [ "$status" -eq 0 ]

    python3 -c "
import json
with open('$TEST_DIR/.claude/settings.json') as f:
    data = json.load(f)
sources = [e.get('_source') for e in data['hooks'].get('Stop', [])]
assert 'removeme' not in sources, f'removeme still present: {sources}'
assert 'keepme' in sources, f'keepme was lost: {sources}'
"
}

@test "remove-hook handles missing settings.json gracefully" {
    rm -f "$TEST_DIR/.claude/settings.json"
    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" --remove nonexistent "$TEST_DIR"
    [ "$status" -eq 0 ]
}

@test "remove-hook refuses to remove ai-toolkit entries" {
    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" --remove ai-toolkit "$TEST_DIR"
    [ "$status" -ne 0 ]
}

@test "remove-hook removes hooks key when no entries remain" {
    _make_hooks_file "$TEST_DIR/only-one.json" "Stop" "echo sole"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/only-one.json" "$TEST_DIR"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" --remove only-one "$TEST_DIR"

    python3 -c "
import json
with open('$TEST_DIR/.claude/settings.json') as f:
    data = json.load(f)
assert 'hooks' not in data, f'hooks key should be removed: {data}'
"
}

# ── Error handling ────────────────────────────────────────────────────────

@test "inject_hook_cli.py rejects malformed JSON" {
    echo "not json {{{" > "$TEST_DIR/bad.json"
    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/bad.json" "$TEST_DIR"
    [ "$status" -eq 2 ]
}

@test "inject_hook_cli.py fails on missing hooks file" {
    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/nonexistent.json" "$TEST_DIR"
    [ "$status" -ne 0 ]
}

@test "inject_hook_cli.py shows usage without arguments" {
    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py"
    [ "$status" -ne 0 ]
}

@test "inject_hook_cli.py rejects malformed target settings.json" {
    echo "broken json" > "$TEST_DIR/.claude/settings.json"
    _make_hooks_file "$TEST_DIR/my-hooks.json"
    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/my-hooks.json" "$TEST_DIR"
    [ "$status" -eq 2 ]
}

@test "--remove requires a source name argument" {
    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" --remove
    [ "$status" -ne 0 ]
}

# ── URL support ──────────────────────────────────────────────────────────

@test "inject_hook_cli.py rejects http:// URLs (HTTPS only)" {
    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "http://example.com/hooks.json" "$TEST_DIR"
    [ "$status" -ne 0 ]
    [[ "$output" == *"HTTPS"* ]]
}

@test "inject_hook_cli.py _name_from_url derives correct name" {
    python3 -c "
import sys
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from inject_hook_cli import _name_from_url
assert _name_from_url('https://example.com/my-hooks.json') == 'my-hooks'
assert _name_from_url('https://example.com/path/to/rag-mcp-hooks.json') == 'rag-mcp-hooks'
assert _name_from_url('https://example.com/hooks') == 'hooks'
"
}

@test "inject_hook_cli.py URL fetch caches file and registers source" {
    # Use a local file-based approach: start a tiny HTTP server
    _make_hooks_file "$TEST_DIR/served-hooks.json" "Stop" "echo url-test"

    # Start a local HTTPS-less server; since we can't easily do HTTPS in test,
    # test the cache + registry logic directly via Python
    export AI_TOOLKIT_HOME="$TEST_DIR/toolkit-data"
    mkdir -p "$AI_TOOLKIT_HOME/hooks/external"

    python3 -c "
import sys, json, os
os.environ['AI_TOOLKIT_HOME'] = '$TEST_DIR/toolkit-data'
sys.path.insert(0, '$TOOLKIT_DIR/scripts')

# Simulate what _fetch_and_cache does (without actual HTTP)
from hook_sources import register_url_source, load_sources, get_url_hooks
from paths import EXTERNAL_HOOKS_DIR

EXTERNAL_HOOKS_DIR.mkdir(parents=True, exist_ok=True)

# Write a cached hooks file
import shutil
shutil.copy('$TEST_DIR/served-hooks.json', str(EXTERNAL_HOOKS_DIR / 'test-remote.json'))
register_url_source(None, 'test-remote', 'https://example.com/test-remote.json')

# Verify sources.json was created
sources = load_sources()
assert 'test-remote' in sources, f'Expected test-remote in {sources}'
assert sources['test-remote']['url'] == 'https://example.com/test-remote.json'

# Verify get_url_hooks
url_hooks = get_url_hooks()
assert url_hooks == {'test-remote': 'https://example.com/test-remote.json'}
"
}

@test "remove-hook also unregisters URL source" {
    export AI_TOOLKIT_HOME="$TEST_DIR/toolkit-data"
    mkdir -p "$AI_TOOLKIT_HOME/hooks/external"

    # Register a URL source and inject its hooks
    _make_hooks_file "$AI_TOOLKIT_HOME/hooks/external/url-hook.json" "Stop" "echo url"

    python3 -c "
import sys, os
os.environ['AI_TOOLKIT_HOME'] = '$TEST_DIR/toolkit-data'
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from hook_sources import register_url_source
register_url_source(None, 'url-hook', 'https://example.com/url-hook.json')
"
    # Inject from cached file
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$AI_TOOLKIT_HOME/hooks/external/url-hook.json" "$TEST_DIR"

    # Verify it was injected
    python3 -c "
import json
with open('$TEST_DIR/.claude/settings.json') as f:
    data = json.load(f)
sources = [e.get('_source') for e in data['hooks']['Stop']]
assert 'url-hook' in sources
"

    # Remove it
    AI_TOOLKIT_HOME="$TEST_DIR/toolkit-data" \
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" --remove url-hook "$TEST_DIR"

    # Verify hook removed from settings.json
    python3 -c "
import json
with open('$TEST_DIR/.claude/settings.json') as f:
    data = json.load(f)
assert 'hooks' not in data or 'Stop' not in data.get('hooks', {})
"

    # Verify URL source unregistered
    python3 -c "
import sys, os
os.environ['AI_TOOLKIT_HOME'] = '$TEST_DIR/toolkit-data'
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from hook_sources import load_sources
sources = load_sources()
assert 'url-hook' not in sources, f'url-hook still in sources: {sources}'
"

    # Verify cached file removed
    [ ! -f "$AI_TOOLKIT_HOME/hooks/external/url-hook.json" ]
}

@test "hook_sources load_sources returns empty on missing file" {
    export AI_TOOLKIT_HOME="$TEST_DIR/toolkit-data"
    python3 -c "
import sys, os
os.environ['AI_TOOLKIT_HOME'] = '$TEST_DIR/toolkit-data'
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from hook_sources import load_sources
assert load_sources() == {}
"
}

@test "hook_sources unregister returns False for unknown name" {
    export AI_TOOLKIT_HOME="$TEST_DIR/toolkit-data"
    mkdir -p "$AI_TOOLKIT_HOME/hooks/external"
    python3 -c "
import sys, os
os.environ['AI_TOOLKIT_HOME'] = '$TEST_DIR/toolkit-data'
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from hook_sources import unregister_source
assert unregister_source(None, 'nonexistent') == False
"
}

@test "inject_hook_cli.py with source_override uses custom name" {
    _make_hooks_file "$TEST_DIR/generic.json" "Stop" "echo custom"
    # Inject with explicit hook-name (simulated by calling Python directly)
    python3 -c "
import sys
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from inject_hook_cli import inject
inject('$TEST_DIR/generic.json', '$TEST_DIR', source_override='my-custom-name')
"
    python3 -c "
import json
with open('$TEST_DIR/.claude/settings.json') as f:
    data = json.load(f)
sources = [e.get('_source') for e in data['hooks']['Stop']]
assert 'my-custom-name' in sources, f'Expected my-custom-name in {sources}'
"
}
