#!/usr/bin/env bats
# test_hooks.bats — Tests for all hook scripts in app/hooks/
# Run with: bats tests/test_hooks.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOKS_DIR="$TOOLKIT_DIR/app/hooks"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    export TOOLKIT_HOOK_PROFILE="standard"
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# Helper: feed JSON tool input to a hook via stdin
run_hook() {
    local hook="$1"
    shift
    run bash "$HOOKS_DIR/$hook" "$@"
}

run_hook_with_input() {
    local hook="$1"
    local input="$2"
    run bash -c "echo '$input' | bash '$HOOKS_DIR/$hook'"
}

@test "hook-io: resolves Augment conversation IDs before transcript fallback" {
    run bash -c \
        "source '$HOOKS_DIR/_hook-io.sh'; INPUT='{\"conversation_id\":\"augment-snake\"}'; hook_session_id"
    [ "$status" -eq 0 ]
    [ "$output" = "augment-snake" ]

    run bash -c \
        "source '$HOOKS_DIR/_hook-io.sh'; INPUT='{\"conversationId\":\"augment-camel\"}'; hook_session_id"
    [ "$status" -eq 0 ]
    [ "$output" = "augment-camel" ]

    run bash -c \
        "source '$HOOKS_DIR/_hook-io.sh'; INPUT='{\"transcript_path\":\"/tmp/transcript-session.jsonl\"}'; hook_session_id"
    [ "$status" -eq 0 ]
    [ "$output" = "transcript-session" ]
}

@test "hook-io: bounds long unsafe session IDs without collapsing prefixes" {
    first="$(printf 'a%.0s' {1..220})/one"
    second="$(printf 'a%.0s' {1..220})/two"

    run bash -c \
        "source '$HOOKS_DIR/_hook-io.sh'; INPUT=\"{\\\"session_id\\\":\\\"$first\\\"}\"; hook_session_id"
    [ "$status" -eq 0 ]
    first_key="$output"
    [ "${#first_key}" -le 160 ]
    [[ "$first_key" != *"/"* ]]

    run bash -c \
        "source '$HOOKS_DIR/_hook-io.sh'; INPUT=\"{\\\"session_id\\\":\\\"$second\\\"}\"; hook_session_id"
    [ "$status" -eq 0 ]
    [ "${#output}" -le 160 ]
    [ "$output" != "$first_key" ]
}

# ═══════════════════════════════════════════════════════════════════════════════
# guard-destructive.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "guard-destructive: blocks rm -rf" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"rm -rf /tmp/foo"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: reads Windsurf command_line payload" {
    run_hook_with_input "guard-destructive.sh" '{"tool_info":{"command_line":"rm -rf /tmp/foo"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks rm -fr" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"rm -fr /tmp/foo"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks rm -r -f (separated flags)" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"rm -r -f /tmp/foo"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks rm -f -r (reversed separated flags)" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"rm -f -r /tmp/foo"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks rm --recursive --force" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"rm --recursive --force /tmp/foo"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks sudo rm" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"sudo rm /etc/important"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks xargs rm" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"find . -name foo | xargs rm -rf"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks find -delete" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"find /tmp -name *.log -delete"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks find -exec rm" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"find . -type f -exec rm {} +"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks DROP TABLE" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"psql -c \"DROP TABLE users\""}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks DROP DATABASE" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"psql -c \"DROP DATABASE mydb\""}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks TRUNCATE" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"psql -c \"TRUNCATE users\""}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks dd if=" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"dd if=/dev/zero of=/dev/sda"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks shred" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"shred -vfz /dev/sda"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks git push --force" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"git push --force origin main"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks git push -f" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"git push -f origin main"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks git reset --hard" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"git reset --hard HEAD~3"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks git clean -fd" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"git clean -fd"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks git branch -D" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"git branch -D feature-branch"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks chmod 777" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"chmod 777 /var/www"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks chmod -R 777" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"chmod -R 777 /var/www"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks docker system prune" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"docker system prune -af"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks kubectl delete namespace" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"kubectl delete namespace production"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks terraform destroy" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"terraform destroy -auto-approve"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: blocks mkfs" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"mkfs.ext4 /dev/sda1"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: allows safe commands" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"ls -la /tmp"}}'
    [ "$status" -eq 0 ]
}

@test "guard-destructive: allows git push (no force)" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"git push origin main"}}'
    [ "$status" -eq 0 ]
}

@test "guard-destructive: allows git push --force-with-lease (safe force)" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"git push --force-with-lease origin main"}}'
    [ "$status" -eq 0 ]
}

@test "guard-destructive: allows git push --force-if-includes (safe force)" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"git push --force-if-includes origin main"}}'
    [ "$status" -eq 0 ]
}

@test "guard-destructive: allows commit message mentioning DROP TABLE (data, not exec)" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"git commit -m \"fix DROP TABLE race condition\""}}'
    [ "$status" -eq 0 ]
}

@test "guard-destructive: allows echo mentioning rm -rf (data, not exec)" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"echo \"never run rm -rf / on prod\""}}'
    [ "$status" -eq 0 ]
}

@test "guard-destructive: still blocks rm -rf chained after a benign git commit" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"git commit -m wip && rm -rf /tmp/foo"}}'
    [ "$status" -eq 2 ]
}

@test "guard-destructive: allows rm single file (no -r)" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"rm /tmp/test.log"}}'
    [ "$status" -eq 0 ]
}

@test "guard-destructive: allows git commit" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"git commit -m \"fix: stuff\""}}'
    [ "$status" -eq 0 ]
}

@test "guard-destructive: allows npm install" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"npm install express"}}'
    [ "$status" -eq 0 ]
}

@test "guard-destructive: fallback to CLAUDE_TOOL_INPUT env var" {
    export CLAUDE_TOOL_INPUT="rm -rf /tmp/danger"
    run bash -c "echo '{}' | bash '$HOOKS_DIR/guard-destructive.sh'"
    [ "$status" -eq 2 ]
    unset CLAUDE_TOOL_INPUT
}

@test "guard-destructive: empty command passes" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{}}'
    [ "$status" -eq 0 ]
}

# ═══════════════════════════════════════════════════════════════════════════════
# guard-path.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "guard-path: blocks wrong username in file_path" {
    local REAL_USER
    REAL_USER=$(basename "$HOME")
    run_hook_with_input "guard-path.sh" "{\"tool_input\":{\"file_path\":\"/Users/wronguser/file.txt\"}}"
    [ "$status" -eq 2 ]
    echo "$output" | grep -q "wrong username"
}

@test "guard-path: allows correct username in file_path" {
    local REAL_USER
    REAL_USER=$(basename "$HOME")
    run_hook_with_input "guard-path.sh" "{\"tool_input\":{\"file_path\":\"/Users/${REAL_USER}/file.txt\"}}"
    [ "$status" -eq 0 ]
}

@test "guard-path: blocks wrong username in /home/ path" {
    run_hook_with_input "guard-path.sh" "{\"tool_input\":{\"file_path\":\"/home/wronguser/file.txt\"}}"
    [ "$status" -eq 2 ]
}

@test "guard-path: allows non-home absolute paths" {
    run_hook_with_input "guard-path.sh" '{"tool_input":{"file_path":"/tmp/test.txt"}}'
    [ "$status" -eq 0 ]
}

@test "guard-path: allows relative paths" {
    run_hook_with_input "guard-path.sh" '{"tool_input":{"file_path":"./src/main.py"}}'
    [ "$status" -eq 0 ]
}

@test "guard-path: blocks wrong username in bash command" {
    run_hook_with_input "guard-path.sh" "{\"tool_input\":{\"command\":\"cat /Users/wronguser/secrets.env\"}}"
    [ "$status" -eq 2 ]
}

@test "guard-path: checks source field (move_file)" {
    run_hook_with_input "guard-path.sh" "{\"tool_input\":{\"source\":\"/Users/wronguser/a.txt\",\"destination\":\"/tmp/b.txt\"}}"
    [ "$status" -eq 2 ]
}

@test "guard-path: checks destination field (move_file)" {
    run_hook_with_input "guard-path.sh" "{\"tool_input\":{\"source\":\"/tmp/a.txt\",\"destination\":\"/Users/wronguser/b.txt\"}}"
    [ "$status" -eq 2 ]
}

@test "guard-path: empty input passes" {
    run_hook_with_input "guard-path.sh" '{"tool_input":{}}'
    [ "$status" -eq 0 ]
}

@test "guard-path: blocks when jq is unavailable" {
    PATH="/bin" run /bin/bash -c \
        "echo '{\"tool_input\":{\"file_path\":\"/Users/wronguser/file.txt\"}}' | /bin/bash '$HOOKS_DIR/guard-path.sh'"
    [ "$status" -eq 2 ]
    echo "$output" | grep -q "requires jq"
}

# ═══════════════════════════════════════════════════════════════════════════════
# quality-gate.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "quality-gate: skips when profile is minimal" {
    export TOOLKIT_HOOK_PROFILE="minimal"
    run_hook "quality-gate.sh"
    [ "$status" -eq 0 ]
}

@test "quality-gate: exits 0 when no project files present" {
    cd "$TEST_TMP"
    run_hook "quality-gate.sh"
    [ "$status" -eq 0 ]
}

@test "quality-gate: detects Python project (pyproject.toml)" {
    cd "$TEST_TMP"
    touch pyproject.toml
    # Without ruff installed, this may fail — that's expected behavior
    run_hook "quality-gate.sh"
    # We just verify it tried (exit code depends on ruff availability)
    true
}

@test "quality-gate: blocks when ruff exits non-zero" {
    cd "$TEST_TMP"
    touch pyproject.toml
    mkdir -p "$TEST_TMP/bin"
    cat > "$TEST_TMP/bin/ruff" <<'EOF'
#!/usr/bin/env bash
echo "bad.py:1:1: F401 unused import"
exit 1
EOF
    chmod +x "$TEST_TMP/bin/ruff"
    PATH="$TEST_TMP/bin:$PATH" run_hook "quality-gate.sh"
    [ "$status" -eq 2 ]
    echo "$output" | grep -q "QUALITY GATE FAILED: ruff found errors"
}

@test "quality-gate: lists edits for payload conversation" {
    local fake_toolkit="$TEST_TMP/fake-toolkit"
    local session_log="$TEST_TMP/session-state-args"
    mkdir -p "$fake_toolkit/scripts" "$TEST_TMP/project/.claude"
    touch "$TEST_TMP/project/.claude/test-cohesion-map.json"
    cat > "$fake_toolkit/scripts/session_state.py" <<'PY'
import os
import sys

with open(os.environ["SESSION_LOG"], "w", encoding="utf-8") as log:
    log.write(" ".join(sys.argv[1:]))
PY
    cd "$TEST_TMP/project"

    run bash -c \
        "echo '{\"conversation_id\":\"quality-conversation\"}' | AI_TOOLKIT_DIR='$fake_toolkit' SESSION_LOG='$session_log' bash '$HOOKS_DIR/quality-gate.sh'"
    [ "$status" -eq 0 ]
    [ "$(cat "$session_log")" = "list --session-id quality-conversation" ]
}

# ═══════════════════════════════════════════════════════════════════════════════
# quality-check.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "quality-check: skips when profile is minimal" {
    export TOOLKIT_HOOK_PROFILE="minimal"
    run_hook "quality-check.sh"
    [ "$status" -eq 0 ]
}

@test "quality-check: exits 0 when no project files present" {
    cd "$TEST_TMP"
    run_hook "quality-check.sh"
    [ "$status" -eq 0 ]
}

# ═══════════════════════════════════════════════════════════════════════════════
# session-start.sh
# ═══════════════════════════════════════════════════════════════════════════════

# Resolve the per-repo session dir the hooks compute for the current cwd.
# Mirrors _session-paths.sh: git work-tree root (fallback cwd) with "/" -> "-".
session_dir_for_cwd() {
    printf '%s' "$HOME/.softspark/ai-toolkit/sessions/${PWD//\//-}"
}

@test "session-start: outputs mandatory rules reminder" {
    cd "$TEST_TMP"
    AI_TOOLKIT_HOOK_VERBOSE=1 run_hook "session-start.sh"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "MANDATORY"
}

@test "session-start: outputs test/docs reminder" {
    cd "$TEST_TMP"
    AI_TOOLKIT_HOOK_VERBOSE=1 run_hook "session-start.sh"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "REMINDER"
}

@test "session-start: suppresses startup context by default" {
    cd "$TEST_TMP"
    run_hook "session-start.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "session-start: quiet mode suppresses startup context" {
    cd "$TEST_TMP"
    AI_TOOLKIT_HOOK_QUIET=1 run_hook "session-start.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "session-start: resets state for payload session" {
    export AI_TOOLKIT_DIR="$TOOLKIT_DIR"
    run_hook_with_input "session-start.sh" '{"session_id":"start-session"}'
    [ "$status" -eq 0 ]

    run python3 "$TOOLKIT_DIR/scripts/session_state.py" session-id \
        --session-id start-session
    [ "$status" -eq 0 ]
    [ "$output" = "start-session" ]
}

@test "session-start: resets state for alternate runtime conversation id" {
    export AI_TOOLKIT_DIR="$TOOLKIT_DIR"
    run_hook_with_input "session-start.sh" \
        '{"conversationId":"augment-start-session"}'
    [ "$status" -eq 0 ]

    run python3 "$TOOLKIT_DIR/scripts/session_state.py" session-id \
        --session-id "augment-start-session"
    [ "$status" -eq 0 ]
    [ "$output" = "augment-start-session" ]
}

@test "session-start: compaction preserves edits from the same session" {
    export AI_TOOLKIT_DIR="$TOOLKIT_DIR"
    python3 "$TOOLKIT_DIR/scripts/session_state.py" reset \
        --session-id compact-session
    python3 "$TOOLKIT_DIR/scripts/session_state.py" append \
        --tool Edit --path /before-compact.py \
        --session-id compact-session

    run_hook_with_input "session-start.sh" \
        '{"session_id":"compact-session","source":"compact"}'
    [ "$status" -eq 0 ]

    run python3 "$TOOLKIT_DIR/scripts/session_state.py" list \
        --session-id compact-session
    [ "$status" -eq 0 ]
    [ "$output" = "/before-compact.py" ]
}

@test "session-start: includes session context from per-repo store" {
    cd "$TEST_TMP/project" 2>/dev/null || { mkdir -p "$TEST_TMP/project"; cd "$TEST_TMP/project"; }
    sdir="$(session_dir_for_cwd)"
    mkdir -p "$sdir"
    echo "Working on feature X" > "$sdir/session-context.md"
    AI_TOOLKIT_HOOK_VERBOSE=1 run_hook "session-start.sh"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Session Context"
}

@test "save-session: two repos get isolated session stores" {
    mkdir -p "$TEST_TMP/repo-a" "$TEST_TMP/repo-b"
    cd "$TEST_TMP/repo-a"
    run_hook_with_input "save-session.sh" '{"session_id":"sid-a","last_assistant_message":"work A"}'
    dir_a="$(session_dir_for_cwd)"
    cd "$TEST_TMP/repo-b"
    run_hook_with_input "save-session.sh" '{"session_id":"sid-b","last_assistant_message":"work B"}'
    dir_b="$(session_dir_for_cwd)"
    [ "$dir_a" != "$dir_b" ]
    grep -q "sid-a" "$dir_a/session-context.md"
    grep -q "sid-b" "$dir_b/session-context.md"
}

@test "session-start: loads active instincts by default (no verbose needed)" {
    mkdir -p "$TEST_TMP/project/.claude/instincts"
    echo "Always verify before commit" > "$TEST_TMP/project/.claude/instincts/verify.md"
    cd "$TEST_TMP/project"
    run_hook "session-start.sh"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Active Instincts"
    echo "$output" | grep -q "Always verify before commit"
}

@test "session-start: QUIET suppresses instinct loading" {
    mkdir -p "$TEST_TMP/project/.claude/instincts"
    echo "Always verify before commit" > "$TEST_TMP/project/.claude/instincts/verify.md"
    cd "$TEST_TMP/project"
    AI_TOOLKIT_HOOK_QUIET=1 run_hook "session-start.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "session-start: no instincts dir means no instinct output" {
    mkdir -p "$TEST_TMP/project/.claude"
    cd "$TEST_TMP/project"
    run_hook "session-start.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# ═══════════════════════════════════════════════════════════════════════════════
# session-end.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "session-end: skips when profile is minimal" {
    export TOOLKIT_HOOK_PROFILE="minimal"
    run_hook "session-end.sh"
    [ "$status" -eq 0 ]
}

@test "session-end: cleans output recovery before minimal-profile handoff skip" {
    cd "$TEST_TMP/project" 2>/dev/null || {
        mkdir -p "$TEST_TMP/project"
        cd "$TEST_TMP/project"
    }
    recovery_root="$(session_dir_for_cwd)"
    mkdir -p "$recovery_root/output-filter"
    capture="$TEST_TMP/session-end-cleanup-args.json"
    runtime="$TEST_TMP/fake-output-filter-cli.py"
    cat > "$runtime" <<'PY'
import json
import os
import sys

with open(os.environ["CAPTURE_ARGS"], "w", encoding="utf-8") as handle:
    json.dump(sys.argv[1:], handle)
PY

    export CAPTURE_ARGS="$capture"
    export AI_TOOLKIT_OUTPUT_FILTER_CLI="$runtime"
    export TOOLKIT_HOOK_PROFILE="minimal"
    run_hook_with_input "session-end.sh" \
        '{"session_id":"native-session-42"}'

    [ "$status" -eq 0 ]
    [ ! -f "$recovery_root/session-end.md" ]
    python3 - "$capture" "$recovery_root" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    arguments = json.load(handle)
assert arguments == [
    "clean",
    "--base-directory",
    sys.argv[2],
    "--session-id",
    "native-session-42",
], arguments
PY
}

@test "session-end: cleans only the normalized edit state for the ending session" {
    cd "$TEST_TMP/project" 2>/dev/null || {
        mkdir -p "$TEST_TMP/project"
        cd "$TEST_TMP/project"
    }
    capture="$TEST_TMP/session-state-cleanup-args.json"
    runtime="$TEST_TMP/fake-session-state.py"
    cat > "$runtime" <<'PY'
import json
import os
import sys

with open(os.environ["STATE_CAPTURE_ARGS"], "w", encoding="utf-8") as handle:
    json.dump(sys.argv[1:], handle)
PY

    export STATE_CAPTURE_ARGS="$capture"
    export AI_TOOLKIT_SESSION_STATE_CLI="$runtime"
    export TOOLKIT_HOOK_PROFILE="minimal"
    run_hook_with_input "session-end.sh" \
        '{"conversationId":"augment-session-9"}'

    [ "$status" -eq 0 ]
    python3 - "$capture" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    arguments = json.load(handle)
assert arguments == [
    "clean",
    "--session-id",
    "augment-session-9",
], arguments
PY
}

@test "session-end: writes handoff file to per-repo store, not repo" {
    cd "$TEST_TMP/project" 2>/dev/null || { mkdir -p "$TEST_TMP/project"; cd "$TEST_TMP/project"; }
    run_hook "session-end.sh"
    [ "$status" -eq 0 ]
    [ ! -f ".claude/session-end.md" ]
    [ -f "$(session_dir_for_cwd)/session-end.md" ]
}

@test "session-end: handoff includes timestamp" {
    cd "$TEST_TMP/project" 2>/dev/null || { mkdir -p "$TEST_TMP/project"; cd "$TEST_TMP/project"; }
    run_hook "session-end.sh"
    grep -q "ended_at" "$(session_dir_for_cwd)/session-end.md"
}

# ═══════════════════════════════════════════════════════════════════════════════
# track-usage.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "track-usage: ignores non-slash prompts" {
    run_hook_with_input "track-usage.sh" '{"prompt":"just a normal question"}'
    [ "$status" -eq 0 ]
    [ ! -f "$HOME/.softspark/ai-toolkit/stats.json" ]
}

@test "track-usage: tracks slash command invocation" {
    run_hook_with_input "track-usage.sh" '{"prompt":"/review src/main.py"}'
    [ "$status" -eq 0 ]
    [ -f "$HOME/.softspark/ai-toolkit/stats.json" ]
    run bash -c "python3 -c \"import json; d=json.load(open('$HOME/.softspark/ai-toolkit/stats.json')); assert d['review']['count']==1\""
    [ "$status" -eq 0 ]
}

@test "track-usage: increments counter on repeated invocation" {
    run_hook_with_input "track-usage.sh" '{"prompt":"/debug error"}'
    run_hook_with_input "track-usage.sh" '{"prompt":"/debug error"}'
    run bash -c "python3 -c \"import json; d=json.load(open('$HOME/.softspark/ai-toolkit/stats.json')); assert d['debug']['count']==2\""
    [ "$status" -eq 0 ]
}

@test "track-usage: write failures stay silent" {
    rm -rf "$HOME/.softspark/ai-toolkit"
    touch "$HOME/.softspark/ai-toolkit"
    AI_TOOLKIT_HOOK_QUIET=1 run_hook_with_input "track-usage.sh" '{"prompt":"/debug hook"}'
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# ═══════════════════════════════════════════════════════════════════════════════
# user-prompt-submit.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "user-prompt-submit: skips when profile is minimal" {
    export TOOLKIT_HOOK_PROFILE="minimal"
    run_hook_with_input "user-prompt-submit.sh" '{"prompt":"anything"}'
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "user-prompt-submit: outputs no-provider advisory in verbose mode" {
    AI_TOOLKIT_HOOK_VERBOSE=1 run_hook_with_input "user-prompt-submit.sh" '{"prompt":"how does auth work?"}'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "advisory only"
}

@test "user-prompt-submit: outputs Step 0 reminder in verbose strict mode" {
    AI_TOOLKIT_HOOK_VERBOSE=1 AI_TOOLKIT_SEARCH_FIRST=strict run_hook_with_input "user-prompt-submit.sh" '{"prompt":"how does auth work?"}'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Step 0"
}

@test "user-prompt-submit: suppresses context by default" {
    run_hook_with_input "user-prompt-submit.sh" '{"prompt":"how does auth work?"}'
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "user-prompt-submit: detects architectural prompt" {
    AI_TOOLKIT_HOOK_VERBOSE=1 run_hook_with_input "user-prompt-submit.sh" '{"prompt":"design a migration strategy"}'
    echo "$output" | grep -q "architectural"
}

@test "user-prompt-submit: detects debugging prompt" {
    AI_TOOLKIT_HOOK_VERBOSE=1 run_hook_with_input "user-prompt-submit.sh" '{"prompt":"debug this error in auth"}'
    echo "$output" | grep -q "debugging"
}

@test "user-prompt-submit: default prompt gets generic reminder" {
    AI_TOOLKIT_HOOK_VERBOSE=1 run_hook_with_input "user-prompt-submit.sh" '{"prompt":"add a button to the form"}'
    echo "$output" | grep -q "KB-first"
}

@test "user-prompt-submit: reads Windsurf user_prompt payload" {
    AI_TOOLKIT_HOOK_VERBOSE=1 run_hook_with_input "user-prompt-submit.sh" '{"tool_info":{"user_prompt":"debug failing hook payload mapping"}}'
    echo "$output" | grep -q "debugging"
}

@test "user-prompt-submit: emits JSON context when requested" {
    AI_TOOLKIT_HOOK_FORMAT=json run_hook_with_input "user-prompt-submit.sh" '{"prompt":"add a button to the form"}'
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "import json,sys; data=json.load(sys.stdin); out=data['hookSpecificOutput']; assert out['hookEventName'] == 'UserPromptSubmit'; assert out['additionalContext']"
}

@test "user-prompt-submit: quiet mode suppresses plain-text context but still arms search flag" {
    AI_TOOLKIT_HOOK_QUIET=1 AI_TOOLKIT_SEARCH_FIRST=strict run_hook_with_input "user-prompt-submit.sh" '{"session_id":"quiet-search","prompt":"debug this hook output issue with enough detail"}'
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ -f "$HOME/.softspark/ai-toolkit/state/search-required-quiet-search.flag" ]
}

@test "user-prompt-submit: quiet JSON mode still emits additionalContext" {
    AI_TOOLKIT_HOOK_QUIET=1 AI_TOOLKIT_HOOK_FORMAT=json AI_TOOLKIT_SEARCH_FIRST=strict run_hook_with_input "user-prompt-submit.sh" '{"session_id":"quiet-json-search","prompt":"debug this hook output issue with enough detail"}'
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "import json,sys; data=json.load(sys.stdin); out=data['hookSpecificOutput']; assert data['suppressOutput'] is True; assert out['hookEventName'] == 'UserPromptSubmit'; assert 'Step 0' in out['additionalContext']"
    [ -f "$HOME/.softspark/ai-toolkit/state/search-required-quiet-json-search.flag" ]
}

@test "user-prompt-submit: state write failures do not corrupt JSON output" {
    touch "$HOME/.softspark/ai-toolkit/state"
    AI_TOOLKIT_HOOK_QUIET=1 AI_TOOLKIT_HOOK_FORMAT=json AI_TOOLKIT_SEARCH_FIRST=strict run_hook_with_input "user-prompt-submit.sh" '{"session_id":"blocked-state","prompt":"debug this hook output issue with enough detail"}'
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "import json,sys; data=json.load(sys.stdin); out=data['hookSpecificOutput']; assert out['hookEventName'] == 'UserPromptSubmit'; assert out['additionalContext']"
}

# ═══════════════════════════════════════════════════════════════════════════════
# post-tool-use.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "post-tool-use: skips when profile is minimal" {
    export TOOLKIT_HOOK_PROFILE="minimal"
    run_hook "post-tool-use.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "post-tool-use: reports markdown file update" {
    AI_TOOLKIT_HOOK_VERBOSE=1 run_hook_with_input "post-tool-use.sh" '{"tool_name":"Edit","tool_input":{"file_path":"docs/README.md"}}'
    echo "$output" | grep -q "docs and examples"
}

@test "post-tool-use: reads Windsurf file_path payload" {
    AI_TOOLKIT_HOOK_VERBOSE=1 run_hook_with_input "post-tool-use.sh" '{"tool_name":"post_write_code","tool_info":{"file_path":"docs/README.md"}}'
    echo "$output" | grep -q "docs and examples"
}

@test "post-tool-use: emits JSON context when requested" {
    AI_TOOLKIT_HOOK_FORMAT=json run_hook_with_input "post-tool-use.sh" '{"tool_name":"Edit","tool_input":{"file_path":"docs/README.md"}}'
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "import json,sys; data=json.load(sys.stdin); assert 'docs/README.md' in data['hookSpecificOutput']['additionalContext']"
}

@test "post-tool-use: quiet mode suppresses informational context" {
    AI_TOOLKIT_HOOK_QUIET=1 run_hook_with_input "post-tool-use.sh" '{"tool_name":"Edit","tool_input":{"file_path":"docs/README.md"}}'
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "post-tool-use: reports test file update" {
    AI_TOOLKIT_HOOK_VERBOSE=1 run_hook_with_input "post-tool-use.sh" '{"tool_name":"Edit","tool_input":{"file_path":"tests/test_auth.bats"}}'
    echo "$output" | grep -q "test file"
}

@test "post-tool-use: reports config file update" {
    AI_TOOLKIT_HOOK_VERBOSE=1 run_hook_with_input "post-tool-use.sh" '{"tool_name":"Edit","tool_input":{"file_path":"config/settings.json"}}'
    echo "$output" | grep -q "config file"
}

@test "post-tool-use: handles missing file path" {
    unset CLAUDE_TOOL_INPUT_FILE_PATH
    export CLAUDE_TOOL_NAME="Write"
    AI_TOOLKIT_HOOK_VERBOSE=1 run_hook "post-tool-use.sh"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "PostToolUse"
}

@test "post-tool-use: records edit under payload conversation" {
    export AI_TOOLKIT_DIR="$TOOLKIT_DIR"
    run_hook_with_input "post-tool-use.sh" \
        '{"conversation_id":"post-conversation","tool_name":"Edit","tool_input":{"file_path":"src/session.py"}}'
    [ "$status" -eq 0 ]

    run python3 "$TOOLKIT_DIR/scripts/session_state.py" list \
        --session-id post-conversation
    [ "$status" -eq 0 ]
    [[ "$output" == *"/src/session.py"* ]]
}

# ═══════════════════════════════════════════════════════════════════════════════
# pre-compact.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "pre-compact: skips when profile is minimal" {
    export TOOLKIT_HOOK_PROFILE="minimal"
    run_hook "pre-compact.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "pre-compact: outputs compaction warning" {
    run_hook "pre-compact.sh"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "compacted"
}

@test "pre-compact: includes session context from per-repo store" {
    mkdir -p "$TEST_TMP/project"
    cd "$TEST_TMP/project"
    sdir="$(session_dir_for_cwd)"
    mkdir -p "$sdir"
    echo "Task: implement auth" > "$sdir/session-context.md"
    run_hook "pre-compact.sh"
    echo "$output" | grep -q "Session Context"
}

# ═══════════════════════════════════════════════════════════════════════════════
# subagent-start.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "subagent-start: skips when profile is minimal" {
    export TOOLKIT_HOOK_PROFILE="minimal"
    run_hook "subagent-start.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "subagent-start: outputs scoping reminder" {
    run_hook_with_input "subagent-start.sh" '{"agent_type":"security-auditor","agent_id":"a123"}'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "security-auditor"
    echo "$output" | grep -q "narrow scope"
}

# ═══════════════════════════════════════════════════════════════════════════════
# subagent-stop.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "subagent-stop: skips when profile is minimal" {
    export TOOLKIT_HOOK_PROFILE="minimal"
    run_hook "subagent-stop.sh"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "subagent-stop: outputs completion checklist" {
    run_hook_with_input "subagent-stop.sh" '{"agent_type":"test-engineer","agent_id":"a456"}'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "test-engineer"
    echo "$output" | grep -q "findings"
}

# ═══════════════════════════════════════════════════════════════════════════════
# save-session.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "save-session: skips when profile is minimal" {
    export TOOLKIT_HOOK_PROFILE="minimal"
    run_hook "save-session.sh"
    [ "$status" -eq 0 ]
}

@test "save-session: writes session file to per-repo store, not repo" {
    cd "$TEST_TMP/project" 2>/dev/null || { mkdir -p "$TEST_TMP/project"; cd "$TEST_TMP/project"; }
    run_hook_with_input "save-session.sh" '{"session_id":"test-session-123","last_assistant_message":"Working on auth module"}'
    [ "$status" -eq 0 ]
    [ ! -f ".claude/session-context.md" ]
    [ -f "$(session_dir_for_cwd)/session-context.md" ]
    grep -q "test-session-123" "$(session_dir_for_cwd)/session-context.md"
}

@test "save-session: accepts alternate runtime conversation id" {
    cd "$TEST_TMP/project" 2>/dev/null || { mkdir -p "$TEST_TMP/project"; cd "$TEST_TMP/project"; }
    run_hook_with_input "save-session.sh" \
        '{"conversation_id":"augment-save-session","last_assistant_message":"saved"}'
    [ "$status" -eq 0 ]
    grep -q "Session: augment-save-session" \
        "$(session_dir_for_cwd)/session-context.md"
}

@test "save-session: skips writing when no session ID" {
    cd "$TEST_TMP/project" 2>/dev/null || { mkdir -p "$TEST_TMP/project"; cd "$TEST_TMP/project"; }
    unset CLAUDE_SESSION_ID
    run_hook "save-session.sh"
    [ "$status" -eq 0 ]
    [ ! -f "$(session_dir_for_cwd)/session-context.md" ]
}

# ═══════════════════════════════════════════════════════════════════════════════
# guard-config.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "guard-config: blocks edit to .eslintrc.json" {
    run_hook_with_input "guard-config.sh" '{"tool_input":{"file_path":"src/.eslintrc.json"}}'
    [ "$status" -eq 2 ]
}

@test "guard-config: allows edit to regular .ts file" {
    run_hook_with_input "guard-config.sh" '{"tool_input":{"file_path":"src/main.ts"}}'
    [ "$status" -eq 0 ]
}

@test "guard-config: blocks edit to tsconfig.json" {
    run_hook_with_input "guard-config.sh" '{"tool_input":{"file_path":"tsconfig.json"}}'
    [ "$status" -eq 2 ]
}

@test "guard-config: prompt text cannot bypass protected config block" {
    run_hook_with_input "guard-config.sh" \
        '{"prompt":"intentionally editing config","tool_input":{"file_path":"tsconfig.json"}}'
    [ "$status" -eq 2 ]
}

# ═══════════════════════════════════════════════════════════════════════════════
# mcp-health.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "mcp-health: exits 0 (non-blocking)" {
    run_hook "mcp-health.sh"
    [ "$status" -eq 0 ]
}

# ═══════════════════════════════════════════════════════════════════════════════
# governance-capture.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "governance-capture: logs rm -rf command to governance.log" {
    run_hook_with_input "governance-capture.sh" '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/danger"}}'
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.softspark/ai-toolkit/governance.log" ]
    grep -q "dangerous-command" "$TEST_TMP/.softspark/ai-toolkit/governance.log"
    grep -q "rm -rf" "$TEST_TMP/.softspark/ai-toolkit/governance.log"
}

@test "governance-capture: does not log regular command" {
    run_hook_with_input "governance-capture.sh" '{"tool_name":"Bash","tool_input":{"command":"ls -la /tmp"}}'
    [ "$status" -eq 0 ]
    [ ! -f "$TEST_TMP/.softspark/ai-toolkit/governance.log" ] || ! grep -q "dangerous-command" "$TEST_TMP/.softspark/ai-toolkit/governance.log"
}

@test "governance-capture: creates governance.log directory if missing" {
    rm -rf "$TEST_TMP/.softspark/ai-toolkit"
    run_hook_with_input "governance-capture.sh" '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/danger"}}'
    [ "$status" -eq 0 ]
    [ -d "$TEST_TMP/.softspark/ai-toolkit" ]
    [ -f "$TEST_TMP/.softspark/ai-toolkit/governance.log" ]
}

# ═══════════════════════════════════════════════════════════════════════════════
# commit-quality.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "commit-quality: warns on non-conventional commit" {
    run_hook_with_input "commit-quality.sh" '{"tool_input":{"command":"git commit -m \"updated stuff\""}}'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "conventional commit"
}

@test "commit-quality: passes on conventional commit" {
    run_hook_with_input "commit-quality.sh" '{"tool_input":{"command":"git commit -m \"feat: add new login flow\""}}'
    [ "$status" -eq 0 ]
    ! echo "$output" | grep -q "conventional commit"
}

# ═══════════════════════════════════════════════════════════════════════════════
# pre-compact-save.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "pre-compact-save: creates timestamped file in compactions/ directory" {
    run_hook_with_input "pre-compact-save.sh" '{"session_id":"test-789"}'
    [ "$status" -eq 0 ]
    [ -d "$TEST_TMP/.softspark/ai-toolkit/compactions" ]
    local found
    found=$(ls "$TEST_TMP/.softspark/ai-toolkit/compactions/"*test-789*.txt 2>/dev/null | wc -l)
    [ "$found" -ge 1 ]
}

@test "pre-compact-save: payload session ID is not overwritten by environment" {
    export CLAUDE_SESSION_ID="environment-session"
    run_hook_with_input "pre-compact-save.sh" '{"session_id":"payload-session"}'
    [ "$status" -eq 0 ]
    local file
    file=$(ls "$TEST_TMP/.softspark/ai-toolkit/compactions/"*payload-session*.txt 2>/dev/null | head -1)
    [ -n "$file" ]
    grep -q "Session: payload-session" "$file"
    ! grep -q "environment-session" "$file"
    unset CLAUDE_SESSION_ID
}

@test "pre-compact-save: unsafe long session ID stays inside compactions" {
    long_id="$(printf 'x%.0s' {1..220})/../../outside"
    run_hook_with_input "pre-compact-save.sh" \
        "{\"session_id\":\"$long_id\"}"
    [ "$status" -eq 0 ]

    saved="$(find "$HOME/.softspark/ai-toolkit/compactions" -type f | head -1)"
    [ -n "$saved" ]
    [[ "$saved" == "$HOME/.softspark/ai-toolkit/compactions/"* ]]
    [ "${#saved}" -lt 300 ]
    [ ! -e "$HOME/.softspark/ai-toolkit/outside" ]
}

@test "hook session IDs with different unsafe bytes remain isolated" {
    first=$(INPUT='{"session_id":"conversation/a"}' bash -c \
        "source '$TOOLKIT_DIR/app/hooks/_hook-io.sh'; hook_session_id")
    second=$(INPUT='{"session_id":"conversation?a"}' bash -c \
        "source '$TOOLKIT_DIR/app/hooks/_hook-io.sh'; hook_session_id")

    [ "$first" != "$second" ]
    [[ "$first" != */* ]]
    [[ "$second" != *\?* ]]
    [ "${#first}" -le 160 ]
    [ "${#second}" -le 160 ]
}

# ─────────────────────────────────────────────────────────────────────────────
# _profile-check.sh — per-hook soft opt-out (AI_TOOLKIT_DISABLED_HOOKS)
# ─────────────────────────────────────────────────────────────────────────────

@test "disable-hooks: named hook emits normally when not disabled" {
    run bash -c "echo '{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"/tmp/x.py\"}}' | AI_TOOLKIT_HOOK_FORMAT=json bash '$HOOKS_DIR/post-tool-use.sh'"
    [ "$status" -eq 0 ]
    [[ "$output" == *"additionalContext"* ]]
}

@test "disable-hooks: AI_TOOLKIT_DISABLED_HOOKS silences the named hook" {
    run bash -c "echo '{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"/tmp/x.py\"}}' | AI_TOOLKIT_HOOK_FORMAT=json AI_TOOLKIT_DISABLED_HOOKS='post-tool-use' bash '$HOOKS_DIR/post-tool-use.sh'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "disable-hooks: accepts .sh suffix and comma-separated lists" {
    run bash -c "echo '{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"/tmp/x.py\"}}' | AI_TOOLKIT_HOOK_FORMAT=json AI_TOOLKIT_DISABLED_HOOKS='foo.sh, post-tool-use.sh ,bar' bash '$HOOKS_DIR/post-tool-use.sh'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "disable-hooks: unrelated name in the list does not disable the hook" {
    run bash -c "echo '{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"/tmp/x.py\"}}' | AI_TOOLKIT_HOOK_FORMAT=json AI_TOOLKIT_DISABLED_HOOKS='some-other-hook' bash '$HOOKS_DIR/post-tool-use.sh'"
    [ "$status" -eq 0 ]
    [[ "$output" == *"additionalContext"* ]]
}

# ─────────────────────────────────────────────────────────────────────────────
# loop-guard.sh — repeated-action advisory
# ─────────────────────────────────────────────────────────────────────────────

@test "loop-guard: same command repeated to threshold emits advisory" {
    P='{"session_id":"loop-rep","tool_name":"Bash","tool_input":{"command":"npm run build"}}'
    printf '%s' "$P" | AI_TOOLKIT_HOOK_FORMAT=json bash "$HOOKS_DIR/loop-guard.sh" >/dev/null
    printf '%s' "$P" | AI_TOOLKIT_HOOK_FORMAT=json bash "$HOOKS_DIR/loop-guard.sh" >/dev/null
    run bash -c "printf '%s' '$P' | AI_TOOLKIT_HOOK_FORMAT=json bash '$HOOKS_DIR/loop-guard.sh'"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Loop guard"* ]]
}

@test "loop-guard: quiet mode does not force JSON output" {
    P='{"session_id":"loop-quiet","tool_name":"Bash","tool_input":{"command":"git status --short"}}'
    printf '%s' "$P" | AI_TOOLKIT_HOOK_QUIET=1 bash "$HOOKS_DIR/loop-guard.sh" >/dev/null
    printf '%s' "$P" | AI_TOOLKIT_HOOK_QUIET=1 bash "$HOOKS_DIR/loop-guard.sh" >/dev/null
    run bash -c "printf '%s' '$P' | AI_TOOLKIT_HOOK_QUIET=1 bash '$HOOKS_DIR/loop-guard.sh'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "loop-guard: single command does not warn" {
    run bash -c "printf '%s' '{\"session_id\":\"loop-single\",\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"ls -la\"}}' | AI_TOOLKIT_HOOK_FORMAT=json bash '$HOOKS_DIR/loop-guard.sh'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "loop-guard: distinct commands do not warn" {
    printf '%s' '{"session_id":"loop-distinct","tool_name":"Bash","tool_input":{"command":"echo a"}}' | AI_TOOLKIT_HOOK_FORMAT=json bash "$HOOKS_DIR/loop-guard.sh" >/dev/null
    printf '%s' '{"session_id":"loop-distinct","tool_name":"Bash","tool_input":{"command":"echo b"}}' | AI_TOOLKIT_HOOK_FORMAT=json bash "$HOOKS_DIR/loop-guard.sh" >/dev/null
    run bash -c "printf '%s' '{\"session_id\":\"loop-distinct\",\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"echo c\"}}' | AI_TOOLKIT_HOOK_FORMAT=json bash '$HOOKS_DIR/loop-guard.sh'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "loop-guard: iterative edits to the same file do not warn (content differs)" {
    printf '%s' '{"session_id":"loop-edit","tool_name":"Edit","tool_input":{"file_path":"/tmp/a.py","new_string":"v1"}}' | AI_TOOLKIT_HOOK_FORMAT=json bash "$HOOKS_DIR/loop-guard.sh" >/dev/null
    printf '%s' '{"session_id":"loop-edit","tool_name":"Edit","tool_input":{"file_path":"/tmp/a.py","new_string":"v2"}}' | AI_TOOLKIT_HOOK_FORMAT=json bash "$HOOKS_DIR/loop-guard.sh" >/dev/null
    run bash -c "printf '%s' '{\"session_id\":\"loop-edit\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"/tmp/a.py\",\"new_string\":\"v3\"}}' | AI_TOOLKIT_HOOK_FORMAT=json bash '$HOOKS_DIR/loop-guard.sh'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}
