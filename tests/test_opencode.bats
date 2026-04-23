#!/usr/bin/env bats
# opencode generator contract tests.
# Consolidates assertions on all five opencode generators: AGENTS.md,
# .opencode/agents/, .opencode/commands/, .opencode/plugins/,
# opencode.json MCP merge. Cross-checks against upstream docs
# (packages/web/src/content/docs/*).
#
# Run with: bats tests/test_opencode.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export OC_DIR; OC_DIR="$(mktemp -d)"
    export OC_LOG_DIR; OC_LOG_DIR="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_opencode.py" > "$OC_LOG_DIR/agents-md" 2>/dev/null
    echo $? > "$OC_LOG_DIR/agents-md.status"
    python3 "$TOOLKIT_DIR/scripts/generate_opencode_agents.py" "$OC_DIR" > "$OC_LOG_DIR/agents.log" 2>/dev/null
    echo $? > "$OC_LOG_DIR/agents.status"
    python3 "$TOOLKIT_DIR/scripts/generate_opencode_commands.py" "$OC_DIR" > "$OC_LOG_DIR/commands.log" 2>/dev/null
    echo $? > "$OC_LOG_DIR/commands.status"
    python3 "$TOOLKIT_DIR/scripts/generate_opencode_plugin.py" "$OC_DIR" > "$OC_LOG_DIR/plugin.log" 2>/dev/null
    echo $? > "$OC_LOG_DIR/plugin.status"
    python3 "$TOOLKIT_DIR/scripts/generate_opencode_json.py" "$OC_DIR" > "$OC_LOG_DIR/json.log" 2>/dev/null
    echo $? > "$OC_LOG_DIR/json.status"
}

teardown_file() {
    rm -rf "$OC_DIR" "$OC_LOG_DIR"
}

# ── AGENTS.md (generate_opencode.py) ────────────────────────────────────────

@test "opencode: AGENTS.md generator exits 0" {
    [ "$(cat "$OC_LOG_DIR/agents-md.status")" = "0" ]
}

@test "opencode: AGENTS.md mentions the rules-file convention" {
    # opencode docs/rules.mdx documents AGENTS.md as the project rules file.
    grep -qi 'opencode' "$OC_LOG_DIR/agents-md"
}

# ── .opencode/agents/ (generate_opencode_agents.py) ─────────────────────────

@test "opencode: agents generator emits ai-toolkit-* prefix (clean-uninstall contract)" {
    count=$(ls "$OC_DIR/.opencode/agents"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 10 ]
}

@test "opencode: agent frontmatter sets mode=subagent" {
    # Upstream: packages/web/src/content/docs/agents.mdx distinguishes
    # `primary` vs `subagent`. Our generated agents are always subagents.
    for f in "$OC_DIR"/.opencode/agents/ai-toolkit-*.md; do
        grep -q '^mode: subagent$' "$f" || { echo "Missing mode: subagent in $f"; return 1; }
    done
}

@test "opencode: agent frontmatter omits invalid fields" {
    # Regression: earlier versions emitted `# source model hint ...`
    # and bare `model:` without `provider/model-id` which opencode rejects.
    ! grep -qrE '^model: (opus|sonnet|haiku)' "$OC_DIR/.opencode/agents/"
    ! grep -qr 'source model hint' "$OC_DIR/.opencode/agents/"
}

# ── .opencode/commands/ (generate_opencode_commands.py) ─────────────────────

@test "opencode: commands generator emits user-invocable skills only" {
    # debug is user-invocable → should exist
    [ -f "$OC_DIR/.opencode/commands/ai-toolkit-debug.md" ]
    # knowledge-only skills (user-invocable: false) must NOT be emitted
    [ ! -f "$OC_DIR/.opencode/commands/ai-toolkit-rag-patterns.md" ]
}

@test "opencode: command frontmatter uses the template field (not a body)" {
    # Upstream: packages/web/src/content/docs/commands.mdx — the prompt
    # lives in `template:`, the markdown body is ignored.
    for f in "$OC_DIR"/.opencode/commands/ai-toolkit-*.md; do
        grep -q '^template: |' "$f" || { echo "Missing template in $f"; return 1; }
    done
}

# ── .opencode/plugins/ (generate_opencode_plugin.py) ────────────────────────

@test "opencode: plugin file exists" {
    [ -f "$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js" ]
}

@test "opencode: plugin uses NAMED export only (opencode requirement)" {
    f="$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js"
    grep -q '^export const ' "$f"
    ! grep -q '^export default' "$f"
}

@test "opencode: plugin bridges all event families documented in packages/web/.../plugins.mdx" {
    f="$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js"
    for evt in 'session.created' 'session.compacted' 'session.deleted' 'message.updated' 'tool.execute.before' 'tool.execute.after' 'permission.asked' 'command.executed'; do
        grep -q "$evt" "$f" || { echo "plugin missing event: $evt"; return 1; }
    done
}

@test "opencode: plugin invokes shared toolkit hooks directory (no script copy)" {
    grep -q '.softspark/ai-toolkit/hooks' "$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js"
}

@test "opencode: plugin passes event payloads via stdin (no shell interpolation)" {
    # Security: prevent shell injection via event payloads.
    f="$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js"
    grep -q 'proc.stdin.write' "$f"
    grep -q 'bash \${scriptPath}' "$f"
}

# ── opencode.json (generate_opencode_json.py) ───────────────────────────────

@test "opencode: opencode.json is valid JSON with the upstream \$schema URL" {
    [ -f "$OC_DIR/opencode.json" ]
    run python3 -c "
import json
d = json.load(open('$OC_DIR/opencode.json'))
assert d['\$schema'] == 'https://opencode.ai/config.json'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "opencode: MCP merge translates command-style servers with enabled=true default" {
    tmp="$(mktemp -d)"
    cat > "$tmp/.mcp.json" <<'EOF'
{
  "mcpServers": {
    "fs": {"command": "npx", "args": ["-y", "@mcp/fs", "/tmp"]}
  }
}
EOF
    python3 "$TOOLKIT_DIR/scripts/generate_opencode_json.py" "$tmp" >/dev/null
    run python3 -c "
import json
d = json.load(open('$tmp/opencode.json'))
srv = d['mcp']['fs']
assert srv['type'] == 'local'
assert srv['command'][0] == 'npx'
assert srv['enabled'] is True
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
    rm -rf "$tmp"
}

@test "opencode: MCP merge translates remote servers and preserves headers" {
    tmp="$(mktemp -d)"
    cat > "$tmp/.mcp.json" <<'EOF'
{
  "mcpServers": {
    "gh": {"url": "https://mcp.github.com", "headers": {"Authorization": "Bearer TOKEN"}}
  }
}
EOF
    python3 "$TOOLKIT_DIR/scripts/generate_opencode_json.py" "$tmp" >/dev/null
    run python3 -c "
import json
d = json.load(open('$tmp/opencode.json'))
srv = d['mcp']['gh']
assert srv['type'] == 'remote'
assert srv['url'].startswith('https://')
assert srv['headers']['Authorization'] == 'Bearer TOKEN'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
    rm -rf "$tmp"
}

# ── Global layout (config_root override) ────────────────────────────────────

@test "opencode: global layout lays down directly under ~/.config/opencode (no .opencode/ prefix)" {
    tmp="$(mktemp -d)"
    home="$tmp/.config/opencode"
    python3 - "$TOOLKIT_DIR" "$tmp" "$home" <<'PYEOF'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_agents import generate as gen_a
from generate_opencode_commands import generate as gen_c
from generate_opencode_plugin import generate as gen_p
from generate_opencode_json import merge_into_opencode_json
target = Path(sys.argv[2]); home = Path(sys.argv[3])
gen_a(target, config_root=home)
gen_c(target, config_root=home)
gen_p(target, config_root=home)
merge_into_opencode_json(target, output_path=home / "opencode.json")
PYEOF
    [ -d "$home/agents" ]
    [ -d "$home/commands" ]
    [ -f "$home/plugins/ai-toolkit-hooks.js" ]
    [ -f "$home/opencode.json" ]
    [ ! -d "$home/.opencode" ]
    rm -rf "$tmp"
}

# ── Registry integrity ──────────────────────────────────────────────────────

@test "opencode: registry lists all five opencode generators" {
    run python3 -c "
import json
d = json.load(open('$TOOLKIT_DIR/scripts/ecosystem_tools.json'))
entries = [t for t in d['tools'] if t['id'] == 'opencode']
assert len(entries) == 1
gens = set(entries[0]['our_generators'])
expected = {
    'scripts/generate_opencode.py',
    'scripts/generate_opencode_agents.py',
    'scripts/generate_opencode_commands.py',
    'scripts/generate_opencode_json.py',
    'scripts/generate_opencode_plugin.py',
}
missing = expected - gens
assert not missing, f'missing generators in registry: {missing}'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}
