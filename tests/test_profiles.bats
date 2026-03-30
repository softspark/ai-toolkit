#!/usr/bin/env bats
# Tests for install --profile minimal|standard|strict

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_PROJECT="$(mktemp -d)"
    TMP_HOME="$(mktemp -d)"
    export HOME="$TMP_HOME"
}

teardown() {
    rm -rf "$TEST_PROJECT" "$TMP_HOME"
}

@test "install --profile minimal installs only agents and skills" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --profile minimal
    [ "$status" -eq 0 ]
    # Agents should be present
    [ -d "$TEST_PROJECT/.claude/agents" ]
    found=0
    for f in "$TEST_PROJECT/.claude/agents"/*.md; do
        [ -L "$f" ] && found=$((found + 1))
    done
    [ "$found" -gt 0 ]
    # Skills should be present
    [ -d "$TEST_PROJECT/.claude/skills" ]
    skill_found=0
    for d in "$TEST_PROJECT/.claude/skills"/*/; do
        [ -d "$d" ] || continue
        link="${d%/}"
        [ -L "$link" ] && skill_found=$((skill_found + 1))
    done
    [ "$skill_found" -gt 0 ]
    # Constitution should NOT be present (not in minimal)
    [ ! -f "$TEST_PROJECT/.claude/constitution.md" ]
}

@test "install --profile minimal does not install hooks" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --profile minimal
    [ "$status" -eq 0 ]
    # settings.json should not have toolkit hooks
    if [ -f "$TEST_PROJECT/.claude/settings.json" ]; then
        ! grep -q '"_source".*"ai-toolkit"' "$TEST_PROJECT/.claude/settings.json"
    fi
}

@test "install --profile standard installs everything (same as default)" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --profile standard
    [ "$status" -eq 0 ]
    [ -d "$TEST_PROJECT/.claude/agents" ]
    [ -d "$TEST_PROJECT/.claude/skills" ]
    [ -f "$TEST_PROJECT/.claude/constitution.md" ]
}

@test "install --profile strict installs everything" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --profile strict
    [ "$status" -eq 0 ]
    [ -d "$TEST_PROJECT/.claude/agents" ]
    [ -d "$TEST_PROJECT/.claude/skills" ]
    [ -f "$TEST_PROJECT/.claude/constitution.md" ]
}

@test "install --profile strict installs git hooks when .git exists" {
    mkdir -p "$TEST_PROJECT/.git/hooks"
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --profile strict
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "git hooks\|strict"
}

@test "install --profile unknown exits with error" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --profile bogus
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Unknown profile"
}

@test "install --profile minimal --only agents respects explicit --only" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --profile minimal --only agents
    [ "$status" -eq 0 ]
    [ -d "$TEST_PROJECT/.claude/agents" ]
    # Skills should NOT be present because --only agents overrides minimal preset
    [ ! -d "$TEST_PROJECT/.claude/skills" ]
}

@test "cli: help lists --profile option" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" help
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '\-\-profile'
}
