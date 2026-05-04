#!/usr/bin/env bats
# Tests for brand-voice skill: structural integrity, output modes, measure.py.
#
# Covers:
#   - SKILL.md frontmatter required fields
#   - modes/ directory contains concise.md and strict.md
#   - measure.py runs against fixtures and meets budget targets
#   - measure.py JSON output is parseable
#   - measure.py exits non-zero when budget violated

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SKILL_DIR="$TOOLKIT_DIR/app/skills/brand-voice"
FIXTURES="$TOOLKIT_DIR/tests/fixtures/output-modes"
MEASURE="python3 $SKILL_DIR/scripts/measure.py"

# ── Skill structure ──────────────────────────────────────────────────────────

@test "brand-voice: SKILL.md exists" {
    [ -f "$SKILL_DIR/SKILL.md" ]
}

@test "brand-voice: SKILL.md has valid frontmatter" {
    head -1 "$SKILL_DIR/SKILL.md" | grep -q '^---$'
    head -10 "$SKILL_DIR/SKILL.md" | grep -q '^name: brand-voice$'
    head -10 "$SKILL_DIR/SKILL.md" | grep -q '^description: '
}

@test "brand-voice: SKILL.md mentions Output Modes section" {
    grep -q '^## Output Modes' "$SKILL_DIR/SKILL.md"
}

@test "brand-voice: modes directory exists with concise + strict" {
    [ -f "$SKILL_DIR/modes/concise.md" ]
    [ -f "$SKILL_DIR/modes/strict.md" ]
}

@test "brand-voice: concise mode declares ratio target" {
    grep -qE 'Token output.*60%' "$SKILL_DIR/modes/concise.md"
}

@test "brand-voice: strict mode declares ratio target" {
    grep -qE 'Token output.*40%' "$SKILL_DIR/modes/strict.md"
}

# ── Fixtures ────────────────────────────────────────────────────────────────

@test "brand-voice: fixtures directory contains at least 3 fixtures" {
    count=$(find "$FIXTURES" -mindepth 1 -maxdepth 1 -type d | wc -l | xargs)
    [ "$count" -ge 3 ]
}

@test "brand-voice: each fixture has default.md, concise.md, strict.md" {
    for d in "$FIXTURES"/*/; do
        [ -f "$d/default.md" ]
        [ -f "$d/concise.md" ]
        [ -f "$d/strict.md" ]
    done
}

# ── measure.py ──────────────────────────────────────────────────────────────

@test "brand-voice: measure.py exists and is executable" {
    [ -f "$SKILL_DIR/scripts/measure.py" ]
    [ -x "$SKILL_DIR/scripts/measure.py" ]
}

@test "brand-voice: measure.py passes default budgets on shipped fixtures" {
    run $MEASURE --fixtures "$FIXTURES"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'aggregate: concise='
    echo "$output" | grep -q 'passed=3/3'
}

@test "brand-voice: measure.py emits valid JSON with --json" {
    run $MEASURE --fixtures "$FIXTURES" --json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert "results" in d and "aggregate" in d'
}

@test "brand-voice: measure.py fails when concise budget is impossibly tight" {
    run $MEASURE --fixtures "$FIXTURES" --concise-budget 0.05
    [ "$status" -eq 1 ]
}

@test "brand-voice: measure.py errors with code 2 on missing fixtures dir" {
    run $MEASURE --fixtures /nonexistent/path
    [ "$status" -eq 2 ]
}

@test "brand-voice: measure.py reports concise ratio under 30% aggregate" {
    run $MEASURE --fixtures "$FIXTURES" --json
    [ "$status" -eq 0 ]
    ratio=$(echo "$output" | python3 -c 'import json,sys; print(json.load(sys.stdin)["aggregate"]["concise_ratio"])')
    python3 -c "import sys; sys.exit(0 if float('$ratio') <= 0.30 else 1)"
}
