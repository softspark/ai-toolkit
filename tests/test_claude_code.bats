#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Claude Code integration schema tests.
#
# Verifies ai-toolkit's tracked frontmatter + hook-event surface stays in
# sync with what Claude Code currently accepts. These are pure schema
# assertions — they do not invoke Claude Code, so they run offline.
#
# Run with: bats tests/test_claude_code.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

# ── Hook event allowlist ─────────────────────────────────────────────────────

@test "claude-code: hook event allowlists exactly match the current Claude Code contract" {
    run python3 -c "
import sys
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from plugin_schema import VALID_HOOK_EVENTS as PLUGIN_HOOK_EVENTS
from validate import VALID_HOOK_EVENTS

expected = frozenset({
    'SessionStart', 'SessionEnd', 'UserPromptSubmit', 'Notification',
    'MessageDisplay', 'PreToolUse', 'PostToolUse', 'PostToolUseFailure',
    'PostToolBatch', 'Stop', 'StopFailure', 'UserPromptExpansion',
    'SubagentStart', 'SubagentStop', 'PreCompact', 'PostCompact',
    'PermissionRequest', 'PermissionDenied', 'Elicitation',
    'ElicitationResult', 'TaskCreated', 'TaskCompleted', 'TeammateIdle',
    'WorktreeCreate', 'WorktreeRemove', 'CwdChanged', 'FileChanged',
    'ConfigChange', 'DirectoryAdded', 'Setup', 'InstructionsLoaded',
})
assert VALID_HOOK_EVENTS == expected
assert PLUGIN_HOOK_EVENTS == VALID_HOOK_EVENTS
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "claude-code: plugin manifest validator rejects a bogus hook event name" {
    run python3 -c "
import sys
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from plugin_schema import validate_manifest

manifest = {
    'name': 'test',
    'description': 'test plugin',
    'version': '1.0.0',
    'domain': 'test',
    'type': 'hook-pack',
    'status': 'stable',
    'requires': {'ai-toolkit': '>=1.0.0'},
    'includes': {'agents': [], 'skills': [], 'rules': [], 'hooks': []},
    'hook_events': {'bad.sh': 'TotallyMadeUpEvent'},
}
errors = validate_manifest(manifest)
assert any(\"invalid event 'TotallyMadeUpEvent'\" in error for error in errors)
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

# ── hook-creator skill ───────────────────────────────────────────────────────

@test "hook-creator SKILL.md documents the new hook events added in Claude Code 2.1.x" {
    skill="$TOOLKIT_DIR/app/skills/hook-creator/SKILL.md"
    for ev in MessageDisplay DirectoryAdded StopFailure PostCompact PermissionDenied Elicitation ElicitationResult TaskCreated WorktreeCreate WorktreeRemove CwdChanged FileChanged ConfigChange InstructionsLoaded; do
        grep -q "\`${ev}\`" "$skill" || { echo "Missing \`${ev}\` row in hook-creator/SKILL.md" >&2; return 1; }
    done
}

@test "hook-creator SKILL.md documents every hook handler type Claude Code supports" {
    skill="$TOOLKIT_DIR/app/skills/hook-creator/SKILL.md"
    for ty in command http prompt agent mcp_tool; do
        grep -q "\`${ty}\`" "$skill" || { echo "Missing handler type \`${ty}\` in hook-creator/SKILL.md" >&2; return 1; }
    done
    for field in if timeout statusMessage once args async asyncRewake shell prompt; do
        grep -q "hooks\[\]\\.${field}" "$skill" || { echo "Missing handler field \`${field}\` in hook-creator/SKILL.md" >&2; return 1; }
    done
    grep -q 'slash_command.*register_repo_root' "$skill"
    grep -q 'displayContent' "$skill"
    grep -q 'only honored.*skill frontmatter' "$skill"
}

@test "claude-code: agent hooks require prompt and reject the obsolete agent field" {
    run python3 -c "
import contextlib
import io
import sys
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from validate import HOOK_REQUIRED_FIELDS, ValidationResult, _validate_hook_handler

assert HOOK_REQUIRED_FIELDS['agent'] == ('prompt',)
valid = ValidationResult()
_validate_hook_handler('Stop', {'type': 'agent', 'prompt': 'Verify tests. \$ARGUMENTS'}, valid)
assert valid.errors == 0
invalid = ValidationResult()
with contextlib.redirect_stdout(io.StringIO()):
    _validate_hook_handler('Stop', {'type': 'agent', 'agent': 'test-engineer'}, invalid)
assert invalid.errors == 1
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "claude-code: prompt and agent hook types share the exact supported event set" {
    run python3 -c "
import contextlib
import io
import sys
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from validate import HOOK_TYPE_EVENTS, ValidationResult, _validate_hook_handler

expected = frozenset({
    'PermissionDenied', 'PermissionRequest', 'PostToolBatch', 'PostToolUse',
    'PostToolUseFailure', 'PreToolUse', 'Stop', 'SubagentStop',
    'TaskCompleted', 'TaskCreated', 'TeammateIdle', 'UserPromptExpansion',
    'UserPromptSubmit',
})
assert HOOK_TYPE_EVENTS['prompt'] == expected
assert HOOK_TYPE_EVENTS['agent'] == expected

for hook_type, event in (('agent', 'PreToolUse'), ('prompt', 'TaskCreated')):
    valid = ValidationResult()
    _validate_hook_handler(event, {'type': hook_type, 'prompt': 'Check \$ARGUMENTS'}, valid)
    assert valid.errors == 0

for hook_type in ('prompt', 'agent'):
    invalid = ValidationResult()
    with contextlib.redirect_stdout(io.StringIO()):
        _validate_hook_handler('SessionStart', {'type': hook_type, 'prompt': 'No'}, invalid)
    assert invalid.errors == 1
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "claude-code: http hooks are rejected only for SessionStart and Setup" {
    run python3 -c "
import contextlib
import io
import sys
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from validate import (
    HOOK_TYPE_EVENTS,
    HTTP_HOOK_EVENTS,
    VALID_HOOK_EVENTS,
    ValidationResult,
    _validate_hook_handler,
)

expected = VALID_HOOK_EVENTS - {'SessionStart', 'Setup'}
assert HTTP_HOOK_EVENTS == expected
assert HOOK_TYPE_EVENTS['http'] == expected

valid = ValidationResult()
_validate_hook_handler('PreToolUse', {'type': 'http', 'url': 'https://hooks.example.test'}, valid)
assert valid.errors == 0

for event in ('SessionStart', 'Setup'):
    invalid = ValidationResult()
    with contextlib.redirect_stdout(io.StringIO()):
        _validate_hook_handler(event, {'type': 'http', 'url': 'https://hooks.example.test'}, invalid)
    assert invalid.errors == 1
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

# ── skill-creator frontmatter reference ─────────────────────────────────────

@test "skill-creator SKILL.md references the new frontmatter fields Claude Code accepts" {
    skill="$TOOLKIT_DIR/app/skills/skill-creator/SKILL.md"
    # xhigh effort level (Opus 4.7) — plain string, not backticked.
    grep -q 'xhigh' "$skill" || { echo "Missing xhigh effort level" >&2; return 1; }
    # Field names in the frontmatter reference table are backticked.
    for field in 'disallowedTools' 'memory' 'skills' 'maxTurns'; do
        grep -q "\`${field}\`" "$skill" || { echo "Missing \`${field}\` row in skill-creator/SKILL.md" >&2; return 1; }
    done
}

# ── registry sanity ──────────────────────────────────────────────────────────

@test "claude-code: ecosystem registry lists claude-code as kind=primary" {
    run python3 -c "
import json
d = json.load(open('$TOOLKIT_DIR/scripts/ecosystem_tools.json'))
entries = [t for t in d['tools'] if t['id'] == 'claude-code']
assert len(entries) == 1, 'claude-code missing from registry'
entry = entries[0]
assert entry['kind'] == 'primary'
assert 'DirectoryAdded' in entry['capability_markers']
for path in (
    '.claude-plugin/plugin.json', 'skills/*/SKILL.md', 'commands/*.md',
    'agents/*.md', 'workflows/', 'output-styles/', 'themes/',
    'hooks/hooks.json', '.mcp.json', '.lsp.json', 'monitors/monitors.json',
    'bin/*', 'settings.json',
):
    assert path in entry['config_paths'], path
note = entry['status_note'].lower()
assert all(marker in note for marker in ('themes', 'experimental', 'class c', 'does not generate'))
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "claude-code: existing generators keep producing the SKILL.md shipping shape" {
    # We do not ship a Claude Code generator — skills and agents ship as-is.
    # Assert the baseline directories still exist so downstream tools can consume them.
    [ -d "$TOOLKIT_DIR/app/skills" ]
    [ -d "$TOOLKIT_DIR/app/agents" ]
    [ -f "$TOOLKIT_DIR/app/hooks.json" ]
}

@test "claude-code: only advisory Stop hooks run async, blocking ones stay synchronous" {
    python3 - "$TOOLKIT_DIR/app/hooks.json" <<'PY'
import json, sys
hooks = json.load(open(sys.argv[1]))["hooks"]
mode = {}
for group in hooks["Stop"]:
    for handler in group["hooks"]:
        name = handler["command"].rsplit("/", 1)[-1].strip('"')
        mode[name] = handler.get("async", False)
# quality-check and save-session always exit 0; their output is advisory, so
# they must not hold the turn open (measured p50 3.3 s across the chain).
assert mode["quality-check.sh"] is True, mode
assert mode["save-session.sh"] is True, mode
# quality-gate blocks with exit 2 and stop-search-check corrects the turn:
# both must stay synchronous or their verdicts would arrive after the fact.
assert mode["quality-gate.sh"] is False, mode
assert mode["stop-search-check.sh"] is False, mode
# No other event uses async: a PreToolUse guard that ran in the background
# could never block.
for event, groups in hooks.items():
    if event == "Stop":
        continue
    for group in groups:
        for handler in group["hooks"]:
            assert not handler.get("async"), (event, handler["command"])
PY
}

@test "claude-code: merge-hooks treats a legacy handler that differs only in async as the same hook" {
    tmp="$(mktemp -d)"
    cat > "$tmp/settings.json" <<'EOF'
{"hooks": {"Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "\"$HOME/.softspark/ai-toolkit/hooks/save-session.sh\"", "timeout": 30}]}]}}
EOF
    python3 "$TOOLKIT_DIR/scripts/merge-hooks.py" inject "$TOOLKIT_DIR/app/hooks.json" "$tmp/settings.json" >/dev/null
    count="$(python3 -c "
import json, sys
stop = json.load(open(sys.argv[1]))['hooks']['Stop']
print(sum(1 for g in stop for h in g['hooks'] if h['command'].endswith('save-session.sh\"')))
" "$tmp/settings.json")"
    [ "$count" -eq 1 ]
    rm -rf "$tmp"
}
