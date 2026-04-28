#!/usr/bin/env bats
# Codex CLI generator smoke tests.
# Verifies our generators produce output shapes that match the Codex CLI
# upstream contract (codex-rs/config/src/hook_config.rs, docs/agents_md.md).
#
# Run with: bats tests/test_codex.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export CX_DIR; CX_DIR="$(mktemp -d)"
    export CX_LOG_DIR; CX_LOG_DIR="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_codex.py" > "$CX_LOG_DIR/codex-md" 2>/dev/null
    echo $? > "$CX_LOG_DIR/codex-md.status"
    python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$CX_DIR" > "$CX_LOG_DIR/codex-hooks.log" 2>/dev/null
    echo $? > "$CX_LOG_DIR/codex-hooks.status"
    python3 "$TOOLKIT_DIR/scripts/generate_codex_rules.py" "$CX_DIR" > "$CX_LOG_DIR/codex-rules.log" 2>/dev/null
    echo $? > "$CX_LOG_DIR/codex-rules.status"
}

teardown_file() {
    rm -rf "$CX_DIR" "$CX_LOG_DIR"
}

# ── generate_codex_hooks.py ─────────────────────────────────────────────────

@test "codex: hooks generator exits 0" {
    [ "$(cat "$CX_LOG_DIR/codex-hooks.status")" = "0" ]
}

@test "codex: hooks.json is valid JSON" {
    run python3 -c "import json; json.load(open('$CX_DIR/.codex/hooks.json'))"
    [ "$status" -eq 0 ]
}

@test "codex: hooks.json uses the 6 upstream-supported event names" {
    # Per codex-rs/config/src/hook_config.rs the accepted keys are
    # PreToolUse, PermissionRequest, PostToolUse, SessionStart,
    # UserPromptSubmit, Stop. We emit a subset; verify no unsupported
    # event sneaks in.
    run python3 -c "
import json
supported = {'PreToolUse','PermissionRequest','PostToolUse','SessionStart','UserPromptSubmit','Stop'}
data = json.load(open('$CX_DIR/.codex/hooks.json'))
events = set(data['hooks'].keys())
extra = events - supported
assert not extra, f'unsupported events: {extra}'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "codex: hooks.json includes PermissionRequest (Codex CLI ≥ 0.121.x)" {
    # Regression: earlier versions omitted PermissionRequest.
    run python3 -c "
import json
data = json.load(open('$CX_DIR/.codex/hooks.json'))
assert 'PermissionRequest' in data['hooks'], 'PermissionRequest missing'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "codex: every hook entry uses type=command" {
    # We deliberately only emit command handlers — prompt/agent handlers
    # require a different payload shape documented in hook_config.rs.
    run python3 -c "
import json
data = json.load(open('$CX_DIR/.codex/hooks.json'))
bad = []
for evt, entries in data['hooks'].items():
    for entry in entries:
        for h in entry.get('hooks', []):
            if h.get('type') != 'command':
                bad.append((evt, h.get('type')))
assert not bad, f'non-command handlers: {bad}'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "codex: command paths point at the shared toolkit hooks directory" {
    grep -q '.softspark/ai-toolkit/hooks' "$CX_DIR/.codex/hooks.json"
}

@test "codex: Pre/PostToolUse entries use the Bash matcher (upstream limitation)" {
    run python3 -c "
import json
data = json.load(open('$CX_DIR/.codex/hooks.json'))
for evt in ('PreToolUse', 'PostToolUse'):
    for entry in data['hooks'].get(evt, []):
        assert entry.get('matcher') == 'Bash', f'{evt} matcher != Bash: {entry}'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

# ── generate_codex.py (AGENTS.md) ───────────────────────────────────────────

@test "codex: generate_codex.py exits 0" {
    [ "$(cat "$CX_LOG_DIR/codex-md.status")" = "0" ]
}

@test "codex: AGENTS.md output includes all ai-toolkit agents" {
    missing=0
    for f in "$TOOLKIT_DIR"/app/agents/*.md; do
        agent_name="${f##*/}"; agent_name="${agent_name%.md}"
        grep -q "$agent_name" "$CX_LOG_DIR/codex-md" || missing=$((missing + 1))
    done
    [ "$missing" -eq 0 ]
}

@test "codex: AGENTS.md wraps content in TOOLKIT markers" {
    grep -q '<!-- TOOLKIT:ai-toolkit START -->' "$CX_LOG_DIR/codex-md"
    grep -q '<!-- TOOLKIT:ai-toolkit END -->' "$CX_LOG_DIR/codex-md"
}

@test "codex: AGENTS.md identifies itself as Codex CLI configuration" {
    grep -qi 'Codex CLI' "$CX_LOG_DIR/codex-md"
}

# ── generate_codex_rules.py ─────────────────────────────────────────────────

@test "codex: rules generator exits 0" {
    [ "$(cat "$CX_LOG_DIR/codex-rules.status")" = "0" ]
}

@test "codex: rules generator emits into .agents/rules/ (Codex discovery path)" {
    [ -d "$CX_DIR/.agents/rules" ]
    count=$(ls "$CX_DIR/.agents/rules"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 6 ]
}

# ── ecosystem registry integrity ────────────────────────────────────────────

@test "codex: registry declares all codex generators" {
    run python3 -c "
import json
d = json.load(open('$TOOLKIT_DIR/scripts/ecosystem_tools.json'))
entries = [t for t in d['tools'] if t['id'] == 'codex-cli']
assert len(entries) == 1
gens = set(entries[0]['our_generators'])
expected = {
    'scripts/generate_codex.py',
    'scripts/generate_codex_rules.py',
    'scripts/generate_codex_hooks.py',
    'scripts/generate_codex_skills.py',
}
missing = expected - gens
assert not missing, f'registry missing generators: {missing}'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}
