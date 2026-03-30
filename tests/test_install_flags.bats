#!/usr/bin/env bats
# Tests for install.py flags: --list, --only, --skip

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_PROJECT="$(mktemp -d)"
    TMP_HOME="$(mktemp -d)"
    export HOME="$TMP_HOME"
}

teardown() {
    rm -rf "$TEST_PROJECT" "$TMP_HOME"
}

@test "install.py --list shows dry-run output without changes" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --list
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "dry-run\|would"
    # Should NOT create any symlinks in dry-run mode
    [ ! -d "$TEST_PROJECT/.claude/agents" ] || {
        found=0
        for f in "$TEST_PROJECT/.claude/agents"/*.md; do
            [ -L "$f" ] && found=$((found + 1))
        done
        [ "$found" -eq 0 ]
    }
}

@test "install.py --only agents installs only agents" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --only agents
    [ "$status" -eq 0 ]
    # Agents should be present (as individual symlinks)
    [ -d "$TEST_PROJECT/.claude/agents" ]
    found=0
    for f in "$TEST_PROJECT/.claude/agents"/*.md; do
        [ -L "$f" ] && found=$((found + 1))
    done
    [ "$found" -gt 0 ]
    # Skills should NOT be present
    [ ! -d "$TEST_PROJECT/.claude/skills" ] || {
        skill_found=0
        for d in "$TEST_PROJECT/.claude/skills"/*/; do
            [ -d "$d" ] || continue
            link="${d%/}"
            [ -L "$link" ] && skill_found=$((skill_found + 1))
        done
        [ "$skill_found" -eq 0 ]
    }
}

@test "install.py --only=skills installs only skills" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --only=skills
    [ "$status" -eq 0 ]
    # Skills should be present
    [ -d "$TEST_PROJECT/.claude/skills" ]
    found=0
    for d in "$TEST_PROJECT/.claude/skills"/*/; do
        [ -d "$d" ] || continue
        link="${d%/}"
        [ -L "$link" ] && found=$((found + 1))
    done
    [ "$found" -gt 0 ]
    # Agents should NOT be present
    [ ! -d "$TEST_PROJECT/.claude/agents" ]
}

@test "install.py --skip hooks installs everything except hooks" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --skip hooks
    [ "$status" -eq 0 ]
    [ -d "$TEST_PROJECT/.claude/agents" ]
    [ -d "$TEST_PROJECT/.claude/skills" ]
    [ ! -f "$TEST_PROJECT/.claude/hooks.json" ]
}

@test "install.py --skip=agents,hooks skips multiple components" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --skip=agents,hooks
    [ "$status" -eq 0 ]
    [ ! -d "$TEST_PROJECT/.claude/agents" ]
    [ ! -f "$TEST_PROJECT/.claude/hooks.json" ]
    [ -d "$TEST_PROJECT/.claude/skills" ]
}

@test "install.py --dry-run is an alias for --list" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "dry-run\|would"
}

@test "install.py --dry-run creates no symlinks" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --dry-run
    [ "$status" -eq 0 ]
    [ ! -d "$TEST_PROJECT/.claude/agents" ] || {
        found=0
        for f in "$TEST_PROJECT/.claude/agents"/*.md; do
            [ -L "$f" ] && found=$((found + 1))
        done
        [ "$found" -eq 0 ]
    }
}

@test "install.py --dry-run works with --only" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --dry-run --only agents
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "dry-run\|would"
}

@test "install.py --only agents,skills installs only listed" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --only agents,skills
    [ "$status" -eq 0 ]
    [ -d "$TEST_PROJECT/.claude/agents" ]
    [ -d "$TEST_PROJECT/.claude/skills" ]
    [ ! -f "$TEST_PROJECT/.claude/hooks.json" ]
    [ ! -f "$TEST_PROJECT/.claude/constitution.md" ]
}
