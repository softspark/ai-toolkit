#!/usr/bin/env bats
# Tests for doctor --fix auto-repair mode
# Optimized: install runs once in setup_file, each test restores from snapshot.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export DOCTOR_SNAPSHOT
    DOCTOR_SNAPSHOT="$(mktemp -d)"
    export HOME="$DOCTOR_SNAPSHOT"
    python3 "$TOOLKIT_DIR/scripts/install.py" "$DOCTOR_SNAPSHOT" >/dev/null 2>&1
}

teardown_file() {
    rm -rf "$DOCTOR_SNAPSHOT"
}

setup() {
    TEST_TMP="$(mktemp -d)"
    cp -a "$DOCTOR_SNAPSHOT/." "$TEST_TMP/"
    export HOME="$TEST_TMP"
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "doctor --fix repairs broken agent symlink" {
    ln -sf "/nonexistent/agent.md" "$TEST_TMP/.claude/agents/test-broken.md"
    [ -L "$TEST_TMP/.claude/agents/test-broken.md" ]
    [ ! -e "$TEST_TMP/.claude/agents/test-broken.md" ]
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED"
    [ ! -L "$TEST_TMP/.claude/agents/test-broken.md" ]
}

@test "doctor --fix repairs broken skill symlink" {
    ln -sf "/nonexistent/skill" "$TEST_TMP/.claude/skills/test-broken"
    [ -L "$TEST_TMP/.claude/skills/test-broken" ]
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED"
    [ ! -L "$TEST_TMP/.claude/skills/test-broken" ]
}

@test "doctor --fix makes non-executable hook executable" {
    chmod -x "$TEST_TMP/.softspark/ai-toolkit/hooks/guard-destructive.sh"
    [ ! -x "$TEST_TMP/.softspark/ai-toolkit/hooks/guard-destructive.sh" ]
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED.*executable"
    [ -x "$TEST_TMP/.softspark/ai-toolkit/hooks/guard-destructive.sh" ]
}

@test "doctor --fix restores missing hook script" {
    rm "$TEST_TMP/.softspark/ai-toolkit/hooks/guard-destructive.sh"
    [ ! -f "$TEST_TMP/.softspark/ai-toolkit/hooks/guard-destructive.sh" ]
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED.*restored"
    [ -x "$TEST_TMP/.softspark/ai-toolkit/hooks/guard-destructive.sh" ]
}

@test "doctor --fix regenerates missing llms-full.txt" {
    [ -f "$TOOLKIT_DIR/llms-full.txt" ] && cp "$TOOLKIT_DIR/llms-full.txt" "$TOOLKIT_DIR/llms-full.txt.test-bak"
    rm -f "$TOOLKIT_DIR/llms-full.txt"
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED.*llms-full.txt"
    [ -f "$TOOLKIT_DIR/llms-full.txt" ]
    [ -f "$TOOLKIT_DIR/llms-full.txt.test-bak" ] && mv "$TOOLKIT_DIR/llms-full.txt.test-bak" "$TOOLKIT_DIR/llms-full.txt"
}

@test "doctor without --fix does not modify anything" {
    ln -sf "/nonexistent/agent.md" "$TEST_TMP/.claude/agents/test-broken.md"
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    [ -L "$TEST_TMP/.claude/agents/test-broken.md" ]
    echo "$output" | grep -q "WARN.*broken"
    ! echo "$output" | grep -q "FIXED"
}

@test "doctor recognizes canonical toolkit hooks without private source tags" {
    python3 - "$TEST_TMP/.claude/settings.json" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
for entries in data.get("hooks", {}).values():
    for entry in entries:
        entry.pop("_source", None)
        for hook in entry.get("hooks", []):
            hook.pop("_source", None)
with open(path, "w") as f:
    json.dump(data, f)
PY
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "settings.json: 29/29 toolkit hook entries"
    ! echo "$output" | grep -q "no toolkit hooks"
}

@test "doctor --fix shows fix mode in summary" {
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "auto-repair"
}

@test "cli: help lists --fix option for doctor" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" help
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '\-\-fix'
}

# ── Language rules drift (project-local check 10) ─────────────────────────────

@test "doctor: flags a detected language missing its injected rules" {
    proj="$TEST_TMP/proj-drift"
    mkdir -p "$proj/.claude"
    printf '%s\n' '<!-- TOOLKIT:language-rules START -->' 'Detected languages: `python-rules`.' '<!-- TOOLKIT:language-rules END -->' > "$proj/.claude/CLAUDE.md"
    printf '[package]\nname = "x"\n' > "$proj/Cargo.toml"
    printf 'print(1)\n' > "$proj/main.py"
    run bash -c "cd '$proj' && python3 '$TOOLKIT_DIR/scripts/doctor.py'"
    echo "$output" | grep -q "rust-rules not injected"
}

@test "doctor: language drift passes when rules match detected languages" {
    proj="$TEST_TMP/proj-sync"
    mkdir -p "$proj/.claude"
    printf '%s\n' '<!-- TOOLKIT:language-rules START -->' 'Detected languages: `python-rules`.' '<!-- TOOLKIT:language-rules END -->' > "$proj/.claude/CLAUDE.md"
    printf 'print(1)\n' > "$proj/main.py"
    run bash -c "cd '$proj' && python3 '$TOOLKIT_DIR/scripts/doctor.py'"
    echo "$output" | grep -q "project language rules in sync"
}

@test "doctor: language drift skips a non-local-install directory" {
    proj="$TEST_TMP/proj-plain"
    mkdir -p "$proj"
    printf 'print(1)\n' > "$proj/main.py"
    run bash -c "cd '$proj' && python3 '$TOOLKIT_DIR/scripts/doctor.py'"
    echo "$output" | grep -q "not a local-install project"
}
