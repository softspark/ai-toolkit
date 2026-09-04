#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for doctor check 12 (Context Budget): resident-context estimates and
# the zero-use skill inventory. Runs against a fabricated HOME so the real
# ~/.claude.json (which holds secrets next to the usage counters) is never read.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    export SOFTSPARK_HOME="$TEST_TMP/.softspark"
    mkdir -p "$HOME/.claude/skills" "$HOME/.claude/agents" "$HOME/.claude/rules" "$SOFTSPARK_HOME/ai-toolkit"

    _skill used-skill "Used often" ""
    _skill idle-skill "Never dispatched, still listed every session" ""
    _skill python-rules "Python knowledge skill" ""
    _skill task-skill "Slash-only task skill" "disable-model-invocation: true"
    _skill off-skill "Turned off via skillOverrides" ""

    printf -- '---\nname: helper\ndescription: An agent\n---\nBody.\n' > "$HOME/.claude/agents/helper.md"
    printf '# Global\n' > "$HOME/.claude/CLAUDE.md"
    printf '# Rule\n' > "$HOME/.claude/rules/ai-toolkit-one.md"
    printf '{"skillOverrides": {"off-skill": "off"}}\n' > "$HOME/.claude/settings.json"
}

teardown() {
    rm -rf "$TEST_TMP"
}

_skill() {
    local name="$1" desc="$2" extra="$3"
    mkdir -p "$HOME/.claude/skills/$name"
    {
        printf -- '---\nname: %s\ndescription: "%s"\n' "$name" "$desc"
        [ -n "$extra" ] && printf '%s\n' "$extra"
        printf -- '---\nBody.\n'
    } > "$HOME/.claude/skills/$name/SKILL.md"
}

_write_claude_json() {
    # numStartups + skillUsage only; a real file carries far more, none of it needed.
    printf '{"numStartups": %s, "skillUsage": {"used-skill": {"usageCount": 7, "lastUsedAt": 1}}, "oauthAccount": {"token": "MUST-NOT-APPEAR"}}\n' "$1" \
        > "$HOME/.claude.json"
}

@test "doctor context budget: counts only model-invocable, non-overridden skills in the listing" {
    _write_claude_json 500
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q '## 12. Context Budget'
    # 5 skills on disk: task-skill (disable-model-invocation) and off-skill (override) are excluded
    echo "$output" | grep -q 'skill listing: 3 model-invocable skills'
    echo "$output" | grep -q 'agents listing: 1 agents'
    echo "$output" | grep -q 'user memory: 2 always-loaded files'
}

@test "doctor context budget: lists zero-use skills, splits language skills, names the override key" {
    _write_claude_json 500
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q 'usage evidence: 500 startups, 1 of 3 listed skills ever dispatched'
    echo "$output" | grep -q '2 listed skills have zero recorded use over 500 startups'
    echo "$output" | grep -q 'language skills .*: python-rules'
    echo "$output" | grep -q 'other zero-use skills .*: idle-skill'
    ! echo "$output" | grep -q 'other zero-use skills .*used-skill'
    echo "$output" | grep -q 'skillOverrides'
    # Secrets that share the file with the counters never reach the report
    ! echo "$output" | grep -q 'MUST-NOT-APPEAR'
}

@test "doctor context budget: toolkit stats.json counts as usage evidence" {
    _write_claude_json 500
    printf '{"idle-skill": {"count": 3, "last_used": "2026-09-01"}}\n' > "$SOFTSPARK_HOME/ai-toolkit/stats.json"
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q 'usage evidence: 500 startups, 2 of 3 listed skills ever dispatched'
    ! echo "$output" | grep -q 'other zero-use skills'
}

@test "doctor context budget: withholds the unused verdict on thin evidence" {
    _write_claude_json 12
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q 'SKIP: usage evidence: 12 startups recorded (need 200'
    ! echo "$output" | grep -q 'zero recorded use'
}

@test "doctor context budget: reports sizes but skips the verdict without ~/.claude.json" {
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q 'skill listing: 3 model-invocable skills'
    echo "$output" | grep -q 'SKIP: usage evidence: ~/.claude.json not found'
}

@test "doctor context budget: warns when the listing exceeds the configured budget fraction" {
    _write_claude_json 500
    # 0.0001 of 200k = 20 tokens; three descriptions exceed that.
    printf '{"skillListingBudgetFraction": 0.0001}\n' > "$HOME/.claude/settings.json"
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q 'WARN: skill listing: .* over budget'
}

@test "doctor context budget: never writes settings or overrides" {
    _write_claude_json 500
    before="$(cat "$HOME/.claude/settings.json")"
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    [ "$before" = "$(cat "$HOME/.claude/settings.json")" ]
}
