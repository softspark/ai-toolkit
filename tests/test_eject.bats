#!/usr/bin/env bats
# Tests for ai-toolkit eject command
# Optimized: eject runs once in setup_file, most assertions reuse the output.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export EJECT_TMP
    export EJECT_OUTPUT
    export EJECT_STATUS
    EJECT_TMP="$(mktemp -d)"
    HOME="$EJECT_TMP" EJECT_OUTPUT="$(python3 "$TOOLKIT_DIR/scripts/eject.py" "$EJECT_TMP" 2>&1)"
    EJECT_STATUS=$?
}

teardown_file() {
    rm -rf "$EJECT_TMP"
}

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "eject creates .claude directory" {
    [ "$EJECT_STATUS" -eq 0 ]
    [ -d "$EJECT_TMP/.claude" ]
}

@test "eject copies agents as real files (not symlinks)" {
    [ -d "$EJECT_TMP/.claude/agents" ]
    found=0
    for f in "$EJECT_TMP/.claude/agents"/*.md; do
        [ -f "$f" ] || continue
        [ ! -L "$f" ]
        found=$((found + 1))
    done
    [ "$found" -gt 0 ]
}

@test "eject copies skills as real directories (not symlinks)" {
    [ -d "$EJECT_TMP/.claude/skills" ]
    found=0
    for d in "$EJECT_TMP/.claude/skills"/*/; do
        [ -d "$d" ] || continue
        [ ! -L "${d%/}" ]
        found=$((found + 1))
    done
    [ "$found" -gt 0 ]
}

@test "eject copies constitution.md" {
    [ -f "$EJECT_TMP/.claude/constitution.md" ]
    [ ! -L "$EJECT_TMP/.claude/constitution.md" ]
}

@test "eject copies ARCHITECTURE.md" {
    [ -f "$EJECT_TMP/.claude/ARCHITECTURE.md" ]
    [ ! -L "$EJECT_TMP/.claude/ARCHITECTURE.md" ]
}

@test "eject inlines rules into CLAUDE.md" {
    [ -f "$EJECT_TMP/.claude/CLAUDE.md" ]
    grep -q "TOOLKIT:" "$EJECT_TMP/.claude/CLAUDE.md"
}

@test "eject replaces existing symlinks with real files" {
    # This test needs its own fresh run with pre-installed symlinks
    python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_TMP" --only agents,skills >/dev/null 2>&1
    found_symlink=false
    for f in "$TEST_TMP/.claude/agents"/*.md; do
        [ -L "$f" ] && found_symlink=true && break
    done
    [ "$found_symlink" = true ]
    run python3 "$TOOLKIT_DIR/scripts/eject.py" "$TEST_TMP"
    [ "$status" -eq 0 ]
    for f in "$TEST_TMP/.claude/agents"/*.md; do
        [ -f "$f" ] || continue
        [ ! -L "$f" ]
    done
}

@test "eject agent count matches toolkit" {
    expected=$(ls "$TOOLKIT_DIR/app/agents"/*.md 2>/dev/null | wc -l | xargs)
    actual=$(ls "$EJECT_TMP/.claude/agents"/*.md 2>/dev/null | wc -l | xargs)
    [ "$expected" -eq "$actual" ]
}

@test "eject skill count matches toolkit" {
    expected=$(ls -d "$TOOLKIT_DIR/app/skills"/*/ 2>/dev/null | wc -l | xargs)
    actual=$(ls -d "$EJECT_TMP/.claude/skills"/*/ 2>/dev/null | wc -l | xargs)
    [ "$expected" -eq "$actual" ]
}

@test "eject output shows summary counts" {
    echo "$EJECT_OUTPUT" | grep -q "Ejected:"
    echo "$EJECT_OUTPUT" | grep -q "agents"
    echo "$EJECT_OUTPUT" | grep -q "skills"
}

@test "cli: help lists eject command" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" help
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'eject'
}

@test "cli: eject exits 0" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" eject "$TEST_TMP"
    [ "$status" -eq 0 ]
}
