#!/usr/bin/env bats
# Tests for scripts/inject_rule_cli.py and scripts/inject_section_cli.py

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_DIR="$(mktemp -d)"
    mkdir -p "$TEST_DIR/.claude"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# ── inject_rule_cli.py ──────────────────────────────────────────────────

@test "inject_rule_cli.py injects a rule into CLAUDE.md" {
    echo "# My Rule" > "$TEST_DIR/my-rule.md"
    echo "Some content" >> "$TEST_DIR/my-rule.md"
    run python3 "$TOOLKIT_DIR/scripts/inject_rule_cli.py" "$TEST_DIR/my-rule.md" "$TEST_DIR"
    [ "$status" -eq 0 ]
    grep -q "TOOLKIT:my-rule START" "$TEST_DIR/.claude/CLAUDE.md"
    grep -q "Some content" "$TEST_DIR/.claude/CLAUDE.md"
    grep -q "TOOLKIT:my-rule END" "$TEST_DIR/.claude/CLAUDE.md"
}

@test "inject_rule_cli.py is idempotent (re-running updates, not duplicates)" {
    echo "# Version 1" > "$TEST_DIR/my-rule.md"
    python3 "$TOOLKIT_DIR/scripts/inject_rule_cli.py" "$TEST_DIR/my-rule.md" "$TEST_DIR" >/dev/null 2>&1
    echo "# Version 2" > "$TEST_DIR/my-rule.md"
    python3 "$TOOLKIT_DIR/scripts/inject_rule_cli.py" "$TEST_DIR/my-rule.md" "$TEST_DIR" >/dev/null 2>&1
    count=$(grep -c "TOOLKIT:my-rule START" "$TEST_DIR/.claude/CLAUDE.md")
    [ "$count" -eq 1 ]
    grep -q "Version 2" "$TEST_DIR/.claude/CLAUDE.md"
}

@test "inject_rule_cli.py fails on missing source file" {
    run python3 "$TOOLKIT_DIR/scripts/inject_rule_cli.py" "$TEST_DIR/nonexistent.md" "$TEST_DIR"
    [ "$status" -ne 0 ]
}

@test "inject_rule_cli.py creates CLAUDE.md if missing" {
    rm -f "$TEST_DIR/.claude/CLAUDE.md"
    echo "# Rule" > "$TEST_DIR/new-rule.md"
    run python3 "$TOOLKIT_DIR/scripts/inject_rule_cli.py" "$TEST_DIR/new-rule.md" "$TEST_DIR"
    [ "$status" -eq 0 ]
    [ -f "$TEST_DIR/.claude/CLAUDE.md" ]
}

@test "inject_rule_cli.py --remove removes a rule" {
    echo "# Rule to remove" > "$TEST_DIR/temp-rule.md"
    python3 "$TOOLKIT_DIR/scripts/inject_rule_cli.py" "$TEST_DIR/temp-rule.md" "$TEST_DIR" >/dev/null 2>&1
    grep -q "TOOLKIT:temp-rule START" "$TEST_DIR/.claude/CLAUDE.md"
    run python3 "$TOOLKIT_DIR/scripts/inject_rule_cli.py" --remove temp-rule "$TEST_DIR"
    [ "$status" -eq 0 ]
    ! grep -q "TOOLKIT:temp-rule" "$TEST_DIR/.claude/CLAUDE.md"
}

@test "inject_rule_cli.py multiple rules coexist" {
    echo "# Rule A" > "$TEST_DIR/rule-a.md"
    echo "# Rule B" > "$TEST_DIR/rule-b.md"
    python3 "$TOOLKIT_DIR/scripts/inject_rule_cli.py" "$TEST_DIR/rule-a.md" "$TEST_DIR" >/dev/null 2>&1
    python3 "$TOOLKIT_DIR/scripts/inject_rule_cli.py" "$TEST_DIR/rule-b.md" "$TEST_DIR" >/dev/null 2>&1
    grep -q "TOOLKIT:rule-a START" "$TEST_DIR/.claude/CLAUDE.md"
    grep -q "TOOLKIT:rule-b START" "$TEST_DIR/.claude/CLAUDE.md"
}

@test "inject_rule_cli.py preserves user content outside markers" {
    echo "# My custom content" > "$TEST_DIR/.claude/CLAUDE.md"
    echo "# Rule" > "$TEST_DIR/a-rule.md"
    python3 "$TOOLKIT_DIR/scripts/inject_rule_cli.py" "$TEST_DIR/a-rule.md" "$TEST_DIR" >/dev/null 2>&1
    grep -q "My custom content" "$TEST_DIR/.claude/CLAUDE.md"
}

@test "inject_rule_cli.py shows usage without arguments" {
    run python3 "$TOOLKIT_DIR/scripts/inject_rule_cli.py"
    [ "$status" -ne 0 ]
}

# ── inject_section_cli.py ───────────────────────────────────────────────

@test "inject_section_cli.py injects content into a target file" {
    echo "Generated content" > "$TEST_DIR/content.txt"
    run python3 "$TOOLKIT_DIR/scripts/inject_section_cli.py" "$TEST_DIR/content.txt" "$TEST_DIR/target.md" "my-section"
    [ "$status" -eq 0 ]
    grep -q "TOOLKIT:my-section START" "$TEST_DIR/target.md"
    grep -q "Generated content" "$TEST_DIR/target.md"
}

@test "inject_section_cli.py is idempotent" {
    echo "V1" > "$TEST_DIR/content.txt"
    python3 "$TOOLKIT_DIR/scripts/inject_section_cli.py" "$TEST_DIR/content.txt" "$TEST_DIR/target.md" "sect" >/dev/null 2>&1
    echo "V2" > "$TEST_DIR/content.txt"
    python3 "$TOOLKIT_DIR/scripts/inject_section_cli.py" "$TEST_DIR/content.txt" "$TEST_DIR/target.md" "sect" >/dev/null 2>&1
    count=$(grep -c "TOOLKIT:sect START" "$TEST_DIR/target.md")
    [ "$count" -eq 1 ]
    grep -q "V2" "$TEST_DIR/target.md"
}

@test "inject_section_cli.py creates target file if missing" {
    echo "Content" > "$TEST_DIR/content.txt"
    run python3 "$TOOLKIT_DIR/scripts/inject_section_cli.py" "$TEST_DIR/content.txt" "$TEST_DIR/new-file.md" "test"
    [ "$status" -eq 0 ]
    [ -f "$TEST_DIR/new-file.md" ]
}

@test "inject_section_cli.py multiple sections coexist" {
    echo "Section A content" > "$TEST_DIR/a.txt"
    echo "Section B content" > "$TEST_DIR/b.txt"
    python3 "$TOOLKIT_DIR/scripts/inject_section_cli.py" "$TEST_DIR/a.txt" "$TEST_DIR/target.md" "section-a" >/dev/null 2>&1
    python3 "$TOOLKIT_DIR/scripts/inject_section_cli.py" "$TEST_DIR/b.txt" "$TEST_DIR/target.md" "section-b" >/dev/null 2>&1
    grep -q "TOOLKIT:section-a START" "$TEST_DIR/target.md"
    grep -q "TOOLKIT:section-b START" "$TEST_DIR/target.md"
    grep -q "Section A content" "$TEST_DIR/target.md"
    grep -q "Section B content" "$TEST_DIR/target.md"
}

@test "inject_section_cli.py defaults section name to ai-toolkit" {
    echo "Default content" > "$TEST_DIR/content.txt"
    run python3 "$TOOLKIT_DIR/scripts/inject_section_cli.py" "$TEST_DIR/content.txt" "$TEST_DIR/target.md"
    [ "$status" -eq 0 ]
    grep -q "TOOLKIT:ai-toolkit START" "$TEST_DIR/target.md"
}
