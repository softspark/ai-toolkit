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
