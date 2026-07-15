#!/usr/bin/env bats
# Tests for scripts/inject_hook_cli.py (inject-hook / remove-hook)

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_DIR="$(mktemp -d)"
    mkdir -p "$TEST_DIR/.claude"
    # Isolate ~/.softspark/ — register_path_source writes to it under HOME
    export HOME="$TEST_DIR"
    export SOFTSPARK_HOME="$TEST_DIR/.softspark"
    unset CODEX_HOME
}

teardown() {
    rm -rf "$TEST_DIR"
}

file_mode() {
    python3 - "$1" <<'PY'
import stat
import sys
from pathlib import Path

print(format(stat.S_IMODE(Path(sys.argv[1]).stat().st_mode), "o"))
PY
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

@test "inject_hook_cli.py removes legacy untagged duplicate entries on re-injection" {
    _make_hooks_file "$TEST_DIR/jira-mcp-hooks.json" \
        "PreToolUse" "jira-mcp hook comment-approval"

    mkdir -p "$TEST_DIR/.claude"
    cat > "$TEST_DIR/.claude/settings.json" <<'EOF'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "jira-mcp hook comment-approval"
          }
        ]
      },
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "jira-mcp hook comment-approval"
          }
        ]
      }
    ]
  }
}
EOF

    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$TEST_DIR/jira-mcp-hooks.json" "$TEST_DIR"

    python3 - "$TEST_DIR/.claude/settings.json" <<'PY'
import json
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)

entries = data["hooks"]["PreToolUse"]
matching = [
    entry for entry in entries
    if entry["hooks"][0]["command"] == "jira-mcp hook comment-approval"
]
assert len(matching) == 1, matching
assert matching[0].get("_source") == "jira-mcp-hooks", matching
PY
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

# ── Codex propagation ────────────────────────────────────────────────────

@test "inject_hook_cli.py propagates native Codex command hooks without _source" {
    _make_hooks_file "$TEST_DIR/codex-test.json" "PreToolUse" "echo codex"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$TEST_DIR/codex-test.json" "$TEST_DIR"

    python3 -c "
import json
with open('$TEST_DIR/.claude/settings.json') as f:
    data = json.load(f)
assert 'codex-test' in [e.get('_source') for e in data['hooks']['PreToolUse']]
"
    [ -f "$TEST_DIR/.codex/hooks.json" ]
    python3 - "$TEST_DIR/.codex/hooks.json" "$TOOLKIT_DIR/scripts" <<'PY'
import json
import sys

sys.path.insert(0, sys.argv[2])
from generate_codex_hooks import validate_hooks_document
from inject_hook_cli import _codex_owner

with open(sys.argv[1]) as handle:
    data = json.load(handle)
validate_hooks_document(data)
assert "_source" not in json.dumps(data), data
commands = [
    hook["command"]
    for group in data["hooks"]["PreToolUse"]
    for hook in group["hooks"]
]
owner = _codex_owner("codex-test")
assert commands == [f"AI_TOOLKIT_HOOK_OWNER={owner} echo codex"], commands
PY
}

@test "inject_hook_cli.py skips unsupported Codex events without modifying hooks.json" {
    _make_hooks_file "$TEST_DIR/non-codex.json" "SessionEnd" "echo bye"
    mkdir -p "$TEST_DIR/.codex"
    cat > "$TEST_DIR/.codex/hooks.json" <<'JSON'
{
  "hooks": {
    "Stop": [
      {"hooks": [{"type": "command", "command": "echo user"}]}
    ]
  }
}
JSON
    cp "$TEST_DIR/.codex/hooks.json" "$TEST_DIR/codex.before"

    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$TEST_DIR/non-codex.json" "$TEST_DIR"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Skipped Codex hook"* ]]
    grep -q 'SessionEnd' "$TEST_DIR/.claude/settings.json"
    cmp "$TEST_DIR/codex.before" "$TEST_DIR/.codex/hooks.json"
}

@test "inject_hook_cli.py Codex propagation is idempotent" {
    _make_hooks_file "$TEST_DIR/idempotent-codex.json" "Stop" "echo once"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$TEST_DIR/idempotent-codex.json" "$TEST_DIR"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$TEST_DIR/idempotent-codex.json" "$TEST_DIR"

    count=$(python3 - "$TEST_DIR/.codex/hooks.json" "$TOOLKIT_DIR/scripts" <<'PY'
import json
import sys
sys.path.insert(0, sys.argv[2])
from inject_hook_cli import _codex_owner
with open(sys.argv[1]) as handle:
    data = json.load(handle)
owner = _codex_owner("idempotent-codex")
print(sum(
    hook["command"].startswith(f"AI_TOOLKIT_HOOK_OWNER={owner} ")
    for group in data["hooks"]["Stop"]
    for hook in group["hooks"]
))
PY
)
    [ "$count" -eq 1 ]
}

@test "remove-hook also removes exact owner from Codex hooks.json" {
    _make_hooks_file "$TEST_DIR/rm-codex.json" "PreToolUse" "echo rm"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$TEST_DIR/rm-codex.json" "$TEST_DIR"
    [ -f "$TEST_DIR/.codex/hooks.json" ]

    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        --remove rm-codex "$TEST_DIR"

    python3 - "$TEST_DIR/.codex/hooks.json" "$TOOLKIT_DIR/scripts" <<'PY'
import json
import sys
sys.path.insert(0, sys.argv[2])
from inject_hook_cli import _codex_owner
with open(sys.argv[1]) as handle:
    data = json.load(handle)
owner = _codex_owner("rm-codex")
commands = [
    hook["command"]
    for group in data.get("hooks", {}).get("PreToolUse", [])
    for hook in group["hooks"]
]
assert not any(f"AI_TOOLKIT_HOOK_OWNER={owner} " in command for command in commands)
PY
}

@test "inject_hook_cli.py preserves native ai-toolkit entries in Codex hooks.json" {
    mkdir -p "$TEST_DIR/.codex"
    cat > "$TEST_DIR/.codex/hooks.json" <<'JSON'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "AI_TOOLKIT_HOOK_OWNER=ai-toolkit echo guard"
        }]
      },
      {
        "matcher": "Read",
        "hooks": [{"type": "command", "command": "echo user"}]
      },
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-demo echo plugin"
        }]
      }
    ]
  }
}
JSON
    _make_hooks_file "$TEST_DIR/ext-codex.json" "PreToolUse" "echo ext"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$TEST_DIR/ext-codex.json" "$TEST_DIR"

    python3 - "$TEST_DIR/.codex/hooks.json" "$TOOLKIT_DIR/scripts" <<'PY'
import json
import sys
sys.path.insert(0, sys.argv[2])
from inject_hook_cli import _codex_owner
with open(sys.argv[1]) as handle:
    data = json.load(handle)
assert "_source" not in json.dumps(data), data
commands = [
    hook["command"]
    for group in data["hooks"]["PreToolUse"]
    for hook in group["hooks"]
]
assert "AI_TOOLKIT_HOOK_OWNER=ai-toolkit echo guard" in commands, commands
assert "echo user" in commands, commands
assert "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-demo echo plugin" in commands, commands
owner = _codex_owner("ext-codex")
assert f"AI_TOOLKIT_HOOK_OWNER={owner} echo ext" in commands, commands
PY
}

@test "inject_hook_cli.py honors CODEX_HOME for native hooks" {
    local custom_home="$TEST_DIR/custom-codex-home"
    mkdir -p "$custom_home"
    _make_hooks_file "$TEST_DIR/custom-home.json" "PostCompact" "echo compacted"

    CODEX_HOME="$custom_home" python3 \
        "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$TEST_DIR/custom-home.json" "$TEST_DIR"

    [ -f "$custom_home/hooks.json" ]
    [ ! -e "$TEST_DIR/.codex/hooks.json" ]
    python3 - "$custom_home/hooks.json" <<'PY'
import json
import sys
with open(sys.argv[1]) as handle:
    data = json.load(handle)
assert "PostCompact" in data["hooks"], data
assert "_source" not in json.dumps(data), data
PY
}

@test "inject_hook_cli.py rejects symlinked CODEX_HOME without writing through it" {
    local external="$TEST_DIR/external-codex-home"
    local linked="$TEST_DIR/linked-codex-home"
    mkdir -p "$external"
    ln -s "$external" "$linked"
    _make_hooks_file "$TEST_DIR/symlink-home.json" "Stop" "echo unsafe"

    run env CODEX_HOME="$linked" python3 \
        "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$TEST_DIR/symlink-home.json" "$TEST_DIR"

    [ "$status" -ne 0 ]
    [ ! -e "$external/hooks.json" ]
}

@test "inject_hook_cli.py migrates legacy Codex _source ownership" {
    mkdir -p "$TEST_DIR/.codex"
    cat > "$TEST_DIR/.codex/hooks.json" <<'JSON'
{
  "hooks": {
    "Stop": [
      {
        "_source": "legacy-source",
        "matcher": "",
        "hooks": [{"type": "command", "command": "echo legacy"}]
      }
    ]
  }
}
JSON
    _make_hooks_file "$TEST_DIR/new-source.json" "Stop" "echo current"

    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$TEST_DIR/new-source.json" "$TEST_DIR"

    python3 - "$TEST_DIR/.codex/hooks.json" "$TOOLKIT_DIR/scripts" <<'PY'
import json
import sys
sys.path.insert(0, sys.argv[2])
from generate_codex_hooks import validate_hooks_document
from inject_hook_cli import _codex_owner
with open(sys.argv[1]) as handle:
    data = json.load(handle)
validate_hooks_document(data)
assert "_source" not in json.dumps(data), data
commands = [
    hook["command"]
    for group in data["hooks"]["Stop"]
    for hook in group["hooks"]
]
assert f"AI_TOOLKIT_HOOK_OWNER={_codex_owner('legacy-source')} echo legacy" in commands
assert f"AI_TOOLKIT_HOOK_OWNER={_codex_owner('new-source')} echo current" in commands
PY
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

@test "register_path_source does NOT overwrite an existing URL entry" {
    # Regression: ai-toolkit update fetches URL hooks to a cached file then
    # calls inject() with that path. inject_hook_cli.py would otherwise demote
    # the URL entry to a local-path entry on every update.
    mkdir -p "$TEST_DIR/.softspark/ai-toolkit/hooks/external"
    cat > "$TEST_DIR/.softspark/ai-toolkit/hooks/external/sources.json" <<'EOF'
{"schema_version": 1, "hooks": {"upstream": {"url": "https://example.com/hooks.json", "fetched_at": "2026-01-01T00:00:00Z", "sha256": "abc"}}}
EOF
    _make_hooks_file "$TEST_DIR/upstream.json" "Stop" "echo cached"
    python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/upstream.json" "$TEST_DIR"
    python3 -c "
import json
with open('$TEST_DIR/.softspark/ai-toolkit/hooks/external/sources.json') as f:
    d = json.load(f)
entry = d['hooks']['upstream']
assert 'url' in entry, f'URL entry was demoted: {entry}'
assert entry['url'] == 'https://example.com/hooks.json'
assert 'path' not in entry, f'path should not be set on URL entry: {entry}'
"
}

@test "inject_hook_cli.py registers local file path in sources.json" {
    _make_hooks_file "$TEST_DIR/local-plugin.json" "Stop" "echo done"
    EXPECTED_PATH=$(python3 -c "import pathlib; print(pathlib.Path('$TEST_DIR/local-plugin.json').resolve())")
    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" "$TEST_DIR/local-plugin.json" "$TEST_DIR"
    [ "$status" -eq 0 ]
    [ -f "$TEST_DIR/.softspark/ai-toolkit/hooks/external/sources.json" ]
    python3 -c "
import json
with open('$TEST_DIR/.softspark/ai-toolkit/hooks/external/sources.json') as f:
    d = json.load(f)
entry = d['hooks']['local-plugin']
assert entry['path'] == '$EXPECTED_PATH', f'got path={entry.get(\"path\")}'
assert 'sha256' in entry, 'sha256 missing'
"
}

# ── Reviewer regressions: destination safety and transactions ─────────────

@test "inject_hook_cli.py rejects symlinked Claude settings without write-through" {
    local external="$TEST_DIR/external-settings.json"
    printf '%s\n' '{"external":"sentinel"}' > "$external"
    cp "$external" "$TEST_DIR/external.before"
    ln -s "$external" "$TEST_DIR/.claude/settings.json"
    _make_hooks_file "$TEST_DIR/symlink-settings.json" "Stop" "echo unsafe"

    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$TEST_DIR/symlink-settings.json" "$TEST_DIR"

    [ "$status" -ne 0 ]
    [[ "$output" == *"symlinked Claude settings"* ]]
    cmp "$TEST_DIR/external.before" "$external"
    [ ! -e "$TEST_DIR/.codex/hooks.json" ]
    [ ! -e "$SOFTSPARK_HOME/ai-toolkit/hooks/external/sources.json" ]
}

@test "inject_hook_cli.py rejects symlinked Claude ancestor without write-through" {
    local external="$TEST_DIR/external-claude"
    mkdir -p "$external"
    printf '%s\n' '{"external":"sentinel"}' > "$external/settings.json"
    cp "$external/settings.json" "$TEST_DIR/external.before"
    rmdir "$TEST_DIR/.claude"
    ln -s "$external" "$TEST_DIR/.claude"
    _make_hooks_file "$TEST_DIR/symlink-ancestor.json" "Stop" "echo unsafe"

    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$TEST_DIR/symlink-ancestor.json" "$TEST_DIR"

    [ "$status" -ne 0 ]
    [[ "$output" == *"symlinked Claude settings"* ]]
    cmp "$TEST_DIR/external.before" "$external/settings.json"
    [ ! -e "$TEST_DIR/.codex/hooks.json" ]
    [ ! -e "$SOFTSPARK_HOME/ai-toolkit/hooks/external/sources.json" ]
}

@test "inject_hook_cli.py preflights relative CODEX_HOME before any mutation" {
    cat > "$TEST_DIR/.claude/settings.json" <<'JSON'
{"permissions":{"allow":["Read"]}}
JSON
    mkdir -p "$SOFTSPARK_HOME/ai-toolkit/hooks/external"
    cat > "$SOFTSPARK_HOME/ai-toolkit/hooks/external/sources.json" <<'JSON'
{"schema_version":1,"hooks":{"keep":{"path":"/keep","sha256":"sentinel"}}}
JSON
    cp "$TEST_DIR/.claude/settings.json" "$TEST_DIR/settings.before"
    cp "$SOFTSPARK_HOME/ai-toolkit/hooks/external/sources.json" \
        "$TEST_DIR/sources.before"
    _make_hooks_file "$TEST_DIR/relative-home.json" "Stop" "echo unsafe"

    run env CODEX_HOME="relative-codex" python3 \
        "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$TEST_DIR/relative-home.json" "$TEST_DIR"

    [ "$status" -ne 0 ]
    [[ "$output" == *"CODEX_HOME must be an absolute path"* ]]
    cmp "$TEST_DIR/settings.before" "$TEST_DIR/.claude/settings.json"
    cmp "$TEST_DIR/sources.before" \
        "$SOFTSPARK_HOME/ai-toolkit/hooks/external/sources.json"
    [ ! -e "$TEST_DIR/.codex/hooks.json" ]
}

@test "inject_hook_cli.py rolls back Claude registry and Codex after late failure" {
    _make_hooks_file "$TEST_DIR/transaction.json" "Stop" "echo transaction"
    cat > "$TEST_DIR/.claude/settings.json" <<'JSON'
{"permissions":{"allow":["Read"]}}
JSON
    mkdir -p "$TEST_DIR/.codex"
    cat > "$TEST_DIR/.codex/hooks.json" <<'JSON'
{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo user"}]}]}}
JSON

    run python3 - "$TOOLKIT_DIR" "$TEST_DIR" <<'PY'
import os
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import generate_codex_hooks
from inject_hook_cli import inject

settings = target / ".claude" / "settings.json"
codex = target / ".codex" / "hooks.json"
sources = Path(os.environ["SOFTSPARK_HOME"]) / "ai-toolkit/hooks/external/sources.json"
before = {settings: settings.read_bytes(), codex: codex.read_bytes()}
real_write = generate_codex_hooks.write_hooks_json

def write_then_fail(path, data, **kwargs):
    real_write(path, data, **kwargs)
    raise OSError("injected late Codex failure")

with mock.patch.object(
    generate_codex_hooks,
    "write_hooks_json",
    side_effect=write_then_fail,
):
    try:
        inject(str(target / "transaction.json"), str(target))
    except OSError as error:
        assert "injected late Codex failure" in str(error)
    else:
        raise AssertionError("expected injected failure")

assert settings.read_bytes() == before[settings]
assert codex.read_bytes() == before[codex]
assert not sources.exists()
assert not list(target.rglob("*.tmp"))
PY
    [ "$status" -eq 0 ]
}

@test "inject_hook_cli.py pins all parents across ancestor swap and rollback" {
    _make_hooks_file "$TEST_DIR/ancestor-swap.json" "Stop" "echo transaction"
    cat > "$TEST_DIR/.claude/settings.json" <<'JSON'
{"permissions":{"allow":["Read"]}}
JSON
    mkdir -p "$TEST_DIR/.codex" "$TEST_DIR/external"
    cat > "$TEST_DIR/.codex/hooks.json" <<'JSON'
{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo user"}]}]}}
JSON
    printf '%s\n' 'external settings sentinel' \
        > "$TEST_DIR/external/settings.json"
    printf '%s\n' 'external sibling sentinel' \
        > "$TEST_DIR/external/sibling.txt"

    run python3 - "$TOOLKIT_DIR" "$TEST_DIR" <<'PY'
import os
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
from inject_hook_cli import inject

claude_dir = target / ".claude"
real_claude_dir = target / ".claude-real"
external = target / "external"
settings = claude_dir / "settings.json"
codex = target / ".codex" / "hooks.json"
sources = Path(os.environ["SOFTSPARK_HOME"]) / "ai-toolkit/hooks/external/sources.json"
settings_before = settings.read_bytes()
codex_before = codex.read_bytes()
external_before = {
    path.name: path.read_bytes() for path in external.iterdir() if path.is_file()
}
real_replace = os.replace
calls = 0

def swap_second_parent_then_fail(source, destination, **kwargs):
    global calls
    calls += 1
    if calls == 2:
        real_replace(claude_dir, real_claude_dir)
        os.symlink(external, claude_dir)
        real_replace(source, destination, **kwargs)
        raise OSError("injected ancestor swap failure")
    return real_replace(source, destination, **kwargs)

with mock.patch("os.replace", side_effect=swap_second_parent_then_fail):
    try:
        inject(str(target / "ancestor-swap.json"), str(target))
    except OSError as error:
        assert "ancestor swap failure" in str(error)
    else:
        raise AssertionError("expected ancestor swap failure")

assert claude_dir.is_symlink()
assert (real_claude_dir / "settings.json").read_bytes() == settings_before
assert codex.read_bytes() == codex_before
assert not sources.exists()
assert {
    path.name: path.read_bytes() for path in external.iterdir() if path.is_file()
} == external_before
assert not list(real_claude_dir.rglob("*.tmp"))
assert not list(external.rglob("*.tmp"))
assert not list(target.rglob("*.tmp"))
PY
    [ "$status" -eq 0 ]
}

@test "inject_hook_cli.py preserves concurrent settings change before transaction" {
    _make_hooks_file "$TEST_DIR/concurrent.json" "Stop" "echo injected"
    cat > "$TEST_DIR/.claude/settings.json" <<'JSON'
{"permissions":{"allow":["Read"]}}
JSON

    run python3 - "$TOOLKIT_DIR" "$TEST_DIR" <<'PY'
import json
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import inject_hook_cli as module

settings = target / ".claude/settings.json"
real_run = module._run_transaction
changed = False

def change_then_start(destinations, mutation):
    global changed
    if not changed:
        changed = True
        data = json.loads(settings.read_text(encoding="utf-8"))
        data["concurrent"] = "survives"
        settings.write_text(json.dumps(data) + "\n", encoding="utf-8")
    return real_run(destinations, mutation)

with mock.patch.object(module, "_run_transaction", side_effect=change_then_start):
    module.inject(str(target / "concurrent.json"), str(target))

data = json.loads(settings.read_text(encoding="utf-8"))
assert data["concurrent"] == "survives", data
assert data["hooks"]["Stop"][0]["_source"] == "concurrent", data
PY
    [ "$status" -eq 0 ]
}

@test "inject_hook_cli.py creates private configs under umask and preserves 0600" {
    _make_hooks_file "$TEST_DIR/private.json" "Stop" "echo private"
    cat > "$TEST_DIR/.claude/settings.json" <<'JSON'
{"permissions":{"allow":["Read"]}}
JSON
    chmod 0600 "$TEST_DIR/.claude/settings.json"

    run bash -c "umask 077; python3 '$TOOLKIT_DIR/scripts/inject_hook_cli.py' '$TEST_DIR/private.json' '$TEST_DIR' >/dev/null"
    [ "$status" -eq 0 ]
    [ "$(file_mode "$TEST_DIR/.claude/settings.json")" = "600" ]
    [ "$(file_mode "$TEST_DIR/.codex/hooks.json")" = "600" ]
    [ "$(file_mode "$SOFTSPARK_HOME/ai-toolkit/hooks/external/sources.json")" = "600" ]
}

@test "inject_hook_cli.py honors positional local hook-name and target-dir" {
    local project="$TEST_DIR/project"
    mkdir -p "$project/.claude"
    _make_hooks_file "$TEST_DIR/positional.json" "Stop" "echo positional"

    run python3 "$TOOLKIT_DIR/scripts/inject_hook_cli.py" \
        "$TEST_DIR/positional.json" "documented-name" "$project"

    [ "$status" -eq 0 ]
    python3 - "$project/.claude/settings.json" <<'PY'
import json
import sys

with open(sys.argv[1]) as handle:
    data = json.load(handle)
assert [group["_source"] for group in data["hooks"]["Stop"]] == [
    "documented-name"
]
PY
}
