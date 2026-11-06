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

@test "claude-code: safety guards block on hook failure in global and plugin manifests" {
    python3 - "$TOOLKIT_DIR" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "scripts"))
from claude_app import render_plugin_hooks

guards = {"guard-destructive.sh", "guard-path.sh", "guard-config.sh"}
documents = (json.loads((root / "app/hooks.json").read_text()), json.loads(render_plugin_hooks()))
for document in documents:
    protected = set()
    for event, groups in document["hooks"].items():
        for group in groups:
            for handler in group["hooks"]:
                name = handler["command"].rsplit("/", 1)[-1].strip('"')
                if event == "PreToolUse" and name in guards:
                    assert handler["onFailure"] == "block", handler
                    assert not handler.get("async"), handler
                    protected.add(name)
                else:
                    assert "onFailure" not in handler, handler
    assert protected == guards, protected
PY
}

@test "claude-code: onFailure accepts only command and HTTP policies with documented values" {
    python3 - "$TOOLKIT_DIR" <<'PY'
import contextlib
import io
import sys

sys.path.insert(0, sys.argv[1] + "/scripts")
from validate import ValidationResult, _validate_hook_handler

for hook_type in ("command", "http"):
    required = {"command": "true"} if hook_type == "command" else {"url": "https://example.com/hook"}
    for policy in ("continue", "block"):
        result = ValidationResult()
        _validate_hook_handler("PreToolUse", {"type": hook_type, "onFailure": policy, **required}, result)
        assert result.errors == 0
for handler in (
    {"type": "command", "command": "true", "onFailure": "deny"},
    {"type": "command", "command": "true", "onFailure": True},
    {"type": "command", "command": "true", "onFailure": ["block"]},
    {"type": "prompt", "prompt": "Check", "onFailure": "block"},
    {"type": "mcp_tool", "server": "policy", "tool": "check", "onFailure": "block"},
):
    result = ValidationResult()
    with contextlib.redirect_stdout(io.StringIO()):
        _validate_hook_handler("PreToolUse", handler, result)
    assert result.errors > 0, handler
PY
}

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
    'PreModelSwitch', 'PostModelSwitch',
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
    for ev in MessageDisplay DirectoryAdded StopFailure PostCompact PreModelSwitch PostModelSwitch PermissionDenied Elicitation ElicitationResult TaskCreated WorktreeCreate WorktreeRemove CwdChanged FileChanged ConfigChange InstructionsLoaded; do
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

@test "claude-code: PermissionRequest permits prompt hooks but rejects agent hooks" {
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
assert HOOK_TYPE_EVENTS['agent'] == expected - {'PermissionRequest'}

for hook_type, event in (('agent', 'PreToolUse'), ('prompt', 'TaskCreated'), ('prompt', 'PermissionRequest')):
    valid = ValidationResult()
    _validate_hook_handler(event, {'type': hook_type, 'prompt': 'Check \$ARGUMENTS'}, valid)
    assert valid.errors == 0

for hook_type, event in (('prompt', 'SessionStart'), ('agent', 'SessionStart'), ('agent', 'PermissionRequest')):
    invalid = ValidationResult()
    with contextlib.redirect_stdout(io.StringIO()):
        _validate_hook_handler(event, {'type': hook_type, 'prompt': 'No'}, invalid)
    assert invalid.errors == 1
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "claude-code: hook manifest validates model switches and optional MCP input" {
    run python3 - "$TOOLKIT_DIR/scripts" <<'PY'
import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from validate import ValidationResult, validate_hook_events

def validate(handler, event):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'app').mkdir()
        (root / 'app/hooks.json').write_text(json.dumps({
            'hooks': {event: [{'hooks': [handler]}]},
        }))
        result = ValidationResult()
        with contextlib.redirect_stdout(io.StringIO()):
            validate_hook_events(root, result)
        return result.errors

for event in ('PreModelSwitch', 'PostModelSwitch'):
    for handler in (
        {'type': 'command', 'command': 'echo reviewed'},
        {'type': 'http', 'url': 'https://hooks.example.test'},
        {'type': 'mcp_tool', 'server': 'policy', 'tool': 'check'},
        {'type': 'mcp_tool', 'server': 'policy', 'tool': 'check', 'input': {'model': '${to_model}'}},
    ):
        assert validate(handler, event) == 0, (event, handler)
    for kind in ('agent', 'prompt'):
        assert validate({'type': kind, 'prompt': 'Check policy'}, event) == 1

base = {'type': 'mcp_tool', 'server': 'policy', 'tool': 'check'}
assert validate({**base, 'arguments': {}}, 'PreToolUse') == 1
assert validate({**base, 'input': []}, 'PreToolUse') == 1
assert validate({'type': 'mcp_tool', 'server': 'policy'}, 'PreToolUse') == 1
print('ok')
PY
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

@test "skill-creator documents skill tool permissions separately from agent frontmatter" {
    skill="$TOOLKIT_DIR/app/skills/skill-creator/SKILL.md"
    # xhigh effort level (Opus 4.7) — plain string, not backticked.
    grep -q 'xhigh' "$skill" || { echo "Missing xhigh effort level" >&2; return 1; }
    # Field names in the frontmatter reference table are backticked.
    for field in 'disallowed-tools' 'arguments' 'when_to_use' 'paths' 'background'; do
        grep -q "\`${field}\`" "$skill" || { echo "Missing \`${field}\` row in skill-creator/SKILL.md" >&2; return 1; }
    done
    grep -q 'Pre-approve tools for the invoking turn' "$skill"
    for field in disallowedTools memory skills maxTurns; do
        ! grep -q "^| \`${field}\` |" "$skill"
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

@test "golden-rules output style requires English code and scopes Language Match to chat" {
    local style="$TOOLKIT_DIR/app/output-styles/golden-rules.md"
    grep -q '^## Code Language$' "$style"
    grep -q 'Code is ALWAYS written in English' "$style"
    grep -q 'This covers chat replies only; code follows `Code Language`.' "$style"
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
# save-session always exits 0 and only writes a file, so it must not hold the
# turn open.
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

@test "claude-code: Stop runs the project checker once, through quality-gate" {
    python3 - "$TOOLKIT_DIR/app/hooks.json" "$TOOLKIT_DIR/app/claude-app/hooks/hooks.json" <<'PY'
import json, sys
for path in sys.argv[1:]:
    stop = json.load(open(path))["hooks"]["Stop"]
    names = [
        handler["command"].rsplit("/", 1)[-1].strip('"')
        for group in stop
        for handler in group["hooks"]
    ]
    # quality-gate.sh runs tsc / ruff / dart analyze / go vet synchronously;
    # quality-check.sh next to it ran the same checker a second time per turn.
    assert names.count("quality-gate.sh") == 1, (path, names)
    assert "quality-check.sh" not in names, (path, names)
PY
}

@test "claude-code: idle reminder uses teammate shutdown and permits read-only completion" {
    run python3 - "$TOOLKIT_DIR/app/hooks.json" <<'PY'
import json
import subprocess
import sys

groups = json.load(open(sys.argv[1]))["hooks"]["TeammateIdle"]
handlers = [handler for group in groups for handler in group["hooks"]]
assert len(handlers) == 1
result = subprocess.run(
    ["bash", "-c", handlers[0]["command"]],
    input=json.dumps({"hook_event_name": "TeammateIdle", "teammate_name": "reviewer"}),
    text=True, capture_output=True, timeout=5, check=False,
)
assert result.returncode == 0, result.stderr
assert "shutdown request" in result.stdout, result.stdout
assert "read-only" in result.stdout, result.stdout
assert "TaskStop" not in result.stdout, result.stdout
assert "All assigned files modified" not in result.stdout, result.stdout
PY
    [ "$status" -eq 0 ]
}

@test "claude-code: global and plugin Stop run PHPStan once without blocking or duplicating TypeScript" {
    python3 - "$TOOLKIT_DIR" <<'PY'
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(sys.argv[1])
configs = (root / "app/hooks.json", root / "app/claude-app/hooks/hooks.json")
for config in configs:
    for scenario in ("php-pass", "php-fail", "typescript-fail"):
        with tempfile.TemporaryDirectory(prefix="stop-quality-") as temp:
            fixture = Path(temp)
            home = fixture / "home"
            runtime = home / ".softspark/ai-toolkit"
            plugin = fixture / "plugin with spaces"
            for destination in (runtime, plugin):
                shutil.copytree(root / "app/hooks", destination / "hooks")
            project = fixture / "project"
            project.mkdir()
            (project / "composer.json").write_text("{}")
            vendor = project / "vendor/bin"
            vendor.mkdir(parents=True)
            tools = fixture / "bin"
            tools.mkdir()
            log = fixture / "checker.log"
            for path, name in ((vendor / "phpstan", "phpstan"), (tools / "npx", "tsc")):
                code = 0 if scenario == "php-pass" else 1
                path.write_text(
                    '#!/usr/bin/env bash\n'
                    f'echo "{name}:$*" >> "$CHECKER_LOG"\n'
                    f'echo "{name} result"\nexit {code}\n'
                )
                path.chmod(0o755)
            if scenario == "typescript-fail":
                (project / "package.json").write_text("{}")
                (project / "tsconfig.json").write_text("{}")
            env = dict(os.environ, HOME=str(home), CLAUDE_PLUGIN_ROOT=str(plugin),
                       AI_TOOLKIT_DIR=str(runtime), TOOLKIT_HOOK_PROFILE="standard",
                       AI_TOOLKIT_DISABLED_HOOKS="save-session,stop-search-check",
                       AI_TOOLKIT_PHPSTAN_MEMORY="512M", CHECKER_LOG=str(log),
                       PATH=f"{tools}:{os.environ['PATH']}")
            results = [
                subprocess.run(["bash", "-c", handler["command"]], cwd=project, env=env,
                               input='{"session_id":"stop-quality"}', text=True,
                               capture_output=True, timeout=15, check=False)
                for group in json.loads(config.read_text())["hooks"]["Stop"]
                for handler in group["hooks"]
            ]
            expected = ["tsc:tsc --noEmit"] if scenario == "typescript-fail" else [
                "phpstan:analyse --memory-limit=512M"
            ]
            assert log.exists(), (config, scenario, results)
            assert log.read_text().splitlines() == expected, (config, scenario, log.read_text())
            statuses = [result.returncode for result in results]
            assert statuses.count(2) == (scenario == "typescript-fail"), (scenario, statuses)
            assert all(code in (0, 2) for code in statuses), (scenario, results)
            output = "".join(result.stdout + result.stderr for result in results)
            assert ("tsc result" if scenario == "typescript-fail" else "phpstan result") in output
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
