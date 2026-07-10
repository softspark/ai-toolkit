#!/usr/bin/env bats
# Claude Chat/Desktop/Cowork plugin export contract.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CLI="node $TOOLKIT_DIR/bin/ai-toolkit.js"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP/home"
    mkdir -p "$HOME/.softspark/ai-toolkit/rules"
    printf '# Team rule\nAlways verify the original symptom.\n' \
        > "$HOME/.softspark/ai-toolkit/rules/team-rule.md"
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "claude-app: committed generated assets match canonical sources" {
    run python3 - <<PY
import sys
from pathlib import Path
sys.path.insert(0, "$TOOLKIT_DIR/scripts")
import claude_app

assert claude_app.PLUGIN_HOOKS_PATH.read_text() == claude_app.render_plugin_hooks()
assert claude_app.PLUGIN_RULES_SKILL_PATH.read_text() == claude_app.render_rules_skill()
assert claude_app.GLOBAL_INSTRUCTIONS_PATH.read_text() == claude_app.render_global_instructions()
PY
    [ "$status" -eq 0 ]
}

@test "claude-app: export contains app-native rules, hooks, agents, and registered rules" {
    archive="$TEST_TMP/ai-toolkit.zip"
    run python3 "$TOOLKIT_DIR/scripts/claude_app.py" export --output "$archive"
    [ "$status" -eq 0 ]
    [ -f "$archive" ]
    [ -f "$TEST_TMP/ai-toolkit-global-instructions.md" ]

    run python3 - <<PY
import json
import zipfile

with zipfile.ZipFile("$archive") as z:
    names = set(z.namelist())
    assert ".claude-plugin/plugin.json" in names
    assert "claude-app/hooks/hooks.json" in names
    assert "claude-app/skills/ai-toolkit-rules/SKILL.md" in names
    assert "claude-app/skills/registered-rules/SKILL.md" in names
    assert "agents/backend-specialist.md" in names
    assert "skills/debug/SKILL.md" in names
    assert "scripts/session_state.py" in names
    assert not any("agents/.claude/" in name for name in names)

    manifest = json.loads(z.read(".claude-plugin/plugin.json"))
    assert isinstance(manifest["repository"], str)
    assert manifest["hooks"] == "./claude-app/hooks/hooks.json"
    assert manifest["skills"] == "./claude-app/skills/"

    hooks = z.read("claude-app/hooks/hooks.json").decode()
    assert '${CLAUDE_PLUGIN_ROOT}/hooks/' in hooks
    assert '$HOME/.softspark/ai-toolkit/hooks/' not in hooks

    rules = z.read("claude-app/skills/registered-rules/SKILL.md").decode()
    assert "Always verify the original symptom." in rules
PY
    [ "$status" -eq 0 ]
}

@test "claude-app: --no-custom-rules omits machine-local rules" {
    archive="$TEST_TMP/clean.zip"
    run python3 "$TOOLKIT_DIR/scripts/claude_app.py" export \
        --output "$archive" --no-custom-rules
    [ "$status" -eq 0 ]
    run python3 - <<PY
import zipfile
with zipfile.ZipFile("$archive") as z:
    assert "claude-app/skills/registered-rules/SKILL.md" not in z.namelist()
PY
    [ "$status" -eq 0 ]
}

@test "claude-app: archive output is deterministic" {
    first="$TEST_TMP/first.zip"
    second="$TEST_TMP/second.zip"
    python3 "$TOOLKIT_DIR/scripts/claude_app.py" export --output "$first" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/claude_app.py" export --output "$second" >/dev/null
    [ "$(shasum "$first" | awk '{print $1}')" = "$(shasum "$second" | awk '{print $1}')" ]
}

@test "claude-app: CLI dispatches export command" {
    archive="$TEST_TMP/cli.zip"
    run $CLI claude-app export --output "$archive" --no-custom-rules
    [ "$status" -eq 0 ]
    [ -f "$archive" ]
}

@test "claude-app: official validator accepts clean staged plugin when available" {
    command -v claude >/dev/null 2>&1 || skip "claude CLI not installed"
    run python3 "$TOOLKIT_DIR/scripts/claude_app.py" verify
    [ "$status" -eq 0 ]
    [[ "$output" == *"Validation passed"* ]]
}
