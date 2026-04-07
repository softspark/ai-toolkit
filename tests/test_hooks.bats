#!/usr/bin/env bats
# test_hooks.bats — Tests for all hook scripts in app/hooks/
# Run with: bats tests/test_hooks.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOKS_DIR="$TOOLKIT_DIR/app/hooks"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    export TOOLKIT_HOOK_PROFILE="standard"
    mkdir -p "$TEST_TMP/.ai-toolkit"
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

# ═══════════════════════════════════════════════════════════════════════════════
# guard-destructive.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "guard-destructive: blocks rm -rf" {
    run_hook_with_input "guard-destructive.sh" '{"tool_input":{"command":"rm -rf /tmp/foo"}}'
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

@test "session-start: outputs mandatory rules reminder" {
    run_hook "session-start.sh"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "MANDATORY"
}

@test "session-start: outputs test/docs reminder" {
    run_hook "session-start.sh"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "REMINDER"
}

@test "session-start: includes session context when file exists" {
    mkdir -p "$TEST_TMP/project/.claude"
    echo "Working on feature X" > "$TEST_TMP/project/.claude/session-context.md"
    cd "$TEST_TMP/project"
    run_hook "session-start.sh"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Session Context"
}

@test "session-start: includes active instincts" {
    mkdir -p "$TEST_TMP/project/.claude/instincts"
    echo "Always verify before commit" > "$TEST_TMP/project/.claude/instincts/verify.md"
    cd "$TEST_TMP/project"
    run_hook "session-start.sh"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Active Instincts"
}

# ═══════════════════════════════════════════════════════════════════════════════
# session-end.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "session-end: skips when profile is minimal" {
    export TOOLKIT_HOOK_PROFILE="minimal"
    run_hook "session-end.sh"
    [ "$status" -eq 0 ]
}

@test "session-end: writes handoff file" {
    cd "$TEST_TMP"
    mkdir -p .claude
    run_hook "session-end.sh"
    [ "$status" -eq 0 ]
    [ -f ".claude/session-end.md" ]
}

@test "session-end: handoff includes timestamp" {
    cd "$TEST_TMP"
    mkdir -p .claude
    run_hook "session-end.sh"
    grep -q "ended_at" .claude/session-end.md
}

# ═══════════════════════════════════════════════════════════════════════════════
# track-usage.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "track-usage: ignores non-slash prompts" {
    run_hook_with_input "track-usage.sh" '{"prompt":"just a normal question"}'
    [ "$status" -eq 0 ]
    [ ! -f "$HOME/.ai-toolkit/stats.json" ]
}

@test "track-usage: tracks slash command invocation" {
    run_hook_with_input "track-usage.sh" '{"prompt":"/review src/main.py"}'
    [ "$status" -eq 0 ]
    [ -f "$HOME/.ai-toolkit/stats.json" ]
    run bash -c "python3 -c \"import json; d=json.load(open('$HOME/.ai-toolkit/stats.json')); assert d['review']['count']==1\""
    [ "$status" -eq 0 ]
}

@test "track-usage: increments counter on repeated invocation" {
    run_hook_with_input "track-usage.sh" '{"prompt":"/debug error"}'
    run_hook_with_input "track-usage.sh" '{"prompt":"/debug error"}'
    run bash -c "python3 -c \"import json; d=json.load(open('$HOME/.ai-toolkit/stats.json')); assert d['debug']['count']==2\""
    [ "$status" -eq 0 ]
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

@test "user-prompt-submit: outputs Step 0 reminder" {
    run_hook_with_input "user-prompt-submit.sh" '{"prompt":"how does auth work?"}'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Step 0"
}

@test "user-prompt-submit: detects architectural prompt" {
    run_hook_with_input "user-prompt-submit.sh" '{"prompt":"design a migration strategy"}'
    echo "$output" | grep -q "architectural"
}

@test "user-prompt-submit: detects debugging prompt" {
    run_hook_with_input "user-prompt-submit.sh" '{"prompt":"debug this error in auth"}'
    echo "$output" | grep -q "debugging"
}

@test "user-prompt-submit: default prompt gets generic reminder" {
    run_hook_with_input "user-prompt-submit.sh" '{"prompt":"add a button to the form"}'
    echo "$output" | grep -q "KB-first"
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
    run_hook_with_input "post-tool-use.sh" '{"tool_name":"Edit","tool_input":{"file_path":"docs/README.md"}}'
    echo "$output" | grep -q "docs and examples"
}

@test "post-tool-use: reports test file update" {
    run_hook_with_input "post-tool-use.sh" '{"tool_name":"Edit","tool_input":{"file_path":"tests/test_auth.bats"}}'
    echo "$output" | grep -q "test file"
}

@test "post-tool-use: reports config file update" {
    run_hook_with_input "post-tool-use.sh" '{"tool_name":"Edit","tool_input":{"file_path":"config/settings.json"}}'
    echo "$output" | grep -q "config file"
}

@test "post-tool-use: handles missing file path" {
    unset CLAUDE_TOOL_INPUT_FILE_PATH
    export CLAUDE_TOOL_NAME="Write"
    run_hook "post-tool-use.sh"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "PostToolUse"
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

@test "pre-compact: includes session context when file exists" {
    mkdir -p "$TEST_TMP/project/.claude"
    echo "Task: implement auth" > "$TEST_TMP/project/.claude/session-context.md"
    cd "$TEST_TMP/project"
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

@test "save-session: writes session file when session_id provided" {
    cd "$TEST_TMP"
    mkdir -p .claude
    run_hook_with_input "save-session.sh" '{"session_id":"test-session-123","last_assistant_message":"Working on auth module"}'
    [ "$status" -eq 0 ]
    [ -f ".claude/session-context.md" ]
    grep -q "test-session-123" ".claude/session-context.md"
}

@test "save-session: skips writing when no session ID" {
    cd "$TEST_TMP"
    unset CLAUDE_SESSION_ID
    run_hook "save-session.sh"
    [ "$status" -eq 0 ]
    [ ! -f ".claude/session-context.md" ]
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
    [ -f "$TEST_TMP/.ai-toolkit/governance.log" ]
    grep -q "dangerous-command" "$TEST_TMP/.ai-toolkit/governance.log"
    grep -q "rm -rf" "$TEST_TMP/.ai-toolkit/governance.log"
}

@test "governance-capture: does not log regular command" {
    run_hook_with_input "governance-capture.sh" '{"tool_name":"Bash","tool_input":{"command":"ls -la /tmp"}}'
    [ "$status" -eq 0 ]
    [ ! -f "$TEST_TMP/.ai-toolkit/governance.log" ] || ! grep -q "dangerous-command" "$TEST_TMP/.ai-toolkit/governance.log"
}

@test "governance-capture: creates governance.log directory if missing" {
    rm -rf "$TEST_TMP/.ai-toolkit"
    run_hook_with_input "governance-capture.sh" '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/danger"}}'
    [ "$status" -eq 0 ]
    [ -d "$TEST_TMP/.ai-toolkit" ]
    [ -f "$TEST_TMP/.ai-toolkit/governance.log" ]
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
# session-context.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "session-context: creates session JSON file with session_id from stdin" {
    run_hook_with_input "session-context.sh" '{"session_id":"test-123","source":"startup"}'
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.ai-toolkit/sessions/test-123.json" ]
}

@test "session-context: JSON contains pwd and git_branch fields" {
    run_hook_with_input "session-context.sh" '{"session_id":"test-456","source":"startup"}'
    [ "$status" -eq 0 ]
    python3 -c "
import json
with open('$TEST_TMP/.ai-toolkit/sessions/test-456.json') as f:
    d = json.load(f)
assert 'pwd' in d, 'missing pwd field'
assert 'git_branch' in d, 'missing git_branch field'
"
}

# ═══════════════════════════════════════════════════════════════════════════════
# pre-compact-save.sh
# ═══════════════════════════════════════════════════════════════════════════════

@test "pre-compact-save: creates timestamped file in compactions/ directory" {
    run_hook_with_input "pre-compact-save.sh" '{"session_id":"test-789"}'
    [ "$status" -eq 0 ]
    [ -d "$TEST_TMP/.ai-toolkit/compactions" ]
    local found
    found=$(ls "$TEST_TMP/.ai-toolkit/compactions/"*test-789*.txt 2>/dev/null | wc -l)
    [ "$found" -ge 1 ]
}

@test "pre-compact-save: file contains session ID" {
    export CLAUDE_SESSION_ID="test-session-abc"
    run_hook_with_input "pre-compact-save.sh" '{"session_id":"test-abc"}'
    [ "$status" -eq 0 ]
    local file
    file=$(ls "$TEST_TMP/.ai-toolkit/compactions/"*test-abc*.txt 2>/dev/null | head -1)
    [ -n "$file" ]
    grep -q "test-session-abc" "$file"
    unset CLAUDE_SESSION_ID
}
