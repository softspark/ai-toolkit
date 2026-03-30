#!/usr/bin/env bats
# Tests for uninstall.py — both old-style (dir symlink) and new-style (per-file)
# Optimized: install runs once in setup_file, each test restores from snapshot.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    # Build a single install snapshot shared by all tests
    export UNINSTALL_SNAPSHOT_PROJECT
    export UNINSTALL_SNAPSHOT_HOME
    UNINSTALL_SNAPSHOT_PROJECT="$(mktemp -d)"
    UNINSTALL_SNAPSHOT_HOME="$(mktemp -d)"
    HOME="$UNINSTALL_SNAPSHOT_HOME" python3 "$TOOLKIT_DIR/scripts/install.py" "$UNINSTALL_SNAPSHOT_PROJECT" >/dev/null 2>&1
}

teardown_file() {
    rm -rf "$UNINSTALL_SNAPSHOT_PROJECT" "$UNINSTALL_SNAPSHOT_HOME"
}

setup() {
    TEST_PROJECT="$(mktemp -d)"
    TMP_HOME="$(mktemp -d)"
    cp -a "$UNINSTALL_SNAPSHOT_PROJECT/." "$TEST_PROJECT/"
    cp -a "$UNINSTALL_SNAPSHOT_HOME/." "$TMP_HOME/"
    export HOME="$TMP_HOME"
}

teardown() {
    rm -rf "$TEST_PROJECT" "$TMP_HOME"
}

@test "uninstall.py exits 0" {
    run python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
}

@test "uninstall.py removes agent symlinks" {
    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1
    found=0
    for f in "$TEST_PROJECT/.claude/agents"/*.md; do
        [ -L "$f" ] && found=$((found + 1))
    done
    [ "$found" -eq 0 ]
}

@test "uninstall.py removes skill symlinks" {
    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1
    found=0
    for d in "$TEST_PROJECT/.claude/skills"/*/; do
        [ -d "$d" ] || continue
        link="${d%/}"
        [ -L "$link" ] && found=$((found + 1))
    done
    [ "$found" -eq 0 ]
}

@test "uninstall.py removes toolkit hooks from hooks.json" {
    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1
    [ ! -f "$TEST_PROJECT/.claude/hooks.json" ]
}

@test "uninstall.py preserves user hooks in hooks.json" {
    printf '{"hooks":{"PreToolUse":[{"_source":"ai-toolkit","matcher":"Bash","command":"echo toolkit","description":"Toolkit hook"},{"matcher":"Bash","command":"echo user","description":"User custom hook"}]}}' > "$TEST_PROJECT/.claude/hooks.json"

    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1

    [ -f "$TEST_PROJECT/.claude/hooks.json" ]
    grep -q "User custom hook" "$TEST_PROJECT/.claude/hooks.json"
    ! grep -q '"_source".*"ai-toolkit"' "$TEST_PROJECT/.claude/hooks.json"
}

@test "uninstall.py removes toolkit content from constitution.md" {
    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1
    [ ! -f "$TEST_PROJECT/.claude/constitution.md" ]
}

@test "uninstall.py preserves user content in constitution.md" {
    printf "# My rules\n" > "$TEST_PROJECT/.claude/constitution.tmp"
    cat "$TEST_PROJECT/.claude/constitution.md" >> "$TEST_PROJECT/.claude/constitution.tmp"
    mv "$TEST_PROJECT/.claude/constitution.tmp" "$TEST_PROJECT/.claude/constitution.md"

    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1

    [ -f "$TEST_PROJECT/.claude/constitution.md" ]
    grep -q "My rules" "$TEST_PROJECT/.claude/constitution.md"
    ! grep -q "<!-- TOOLKIT:" "$TEST_PROJECT/.claude/constitution.md"
}

@test "uninstall.py is idempotent" {
    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1
    run python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
}

@test "uninstall.py preserves user-owned agent files" {
    echo "# My agent" > "$TEST_PROJECT/.claude/agents/my-agent.md"

    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1

    [ -f "$TEST_PROJECT/.claude/agents/my-agent.md" ]
    grep -q "My agent" "$TEST_PROJECT/.claude/agents/my-agent.md"
}

@test "uninstall.py preserves user-owned skill directories" {
    mkdir -p "$TEST_PROJECT/.claude/skills/my-skill"
    echo "# My skill" > "$TEST_PROJECT/.claude/skills/my-skill/SKILL.md"

    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1

    [ -d "$TEST_PROJECT/.claude/skills/my-skill" ]
    grep -q "My skill" "$TEST_PROJECT/.claude/skills/my-skill/SKILL.md"
}

@test "uninstall.py removes empty agents/ directory after cleanup" {
    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1
    [ ! -d "$TEST_PROJECT/.claude/agents" ]
}

@test "uninstall.py removes empty skills/ directory after cleanup" {
    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1
    [ ! -d "$TEST_PROJECT/.claude/skills" ]
}

@test "uninstall.py handles old-style directory symlink" {
    rm -rf "$TEST_PROJECT/.claude/agents" "$TEST_PROJECT/.claude/skills"
    ln -s "$TOOLKIT_DIR/app/agents" "$TEST_PROJECT/.claude/agents"
    ln -s "$TOOLKIT_DIR/app/skills" "$TEST_PROJECT/.claude/skills"

    run python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [ ! -L "$TEST_PROJECT/.claude/agents" ]
    [ ! -L "$TEST_PROJECT/.claude/skills" ]
}
