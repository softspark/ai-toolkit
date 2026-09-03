#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for the top-level rule skills.
#
# The rules were reachable only as Claude Code user-level files, with the
# global CLAUDE.md carrying a pointer instead of their content. DeepSeek
# Harness reads AGENTS.md / CLAUDE.md and has no rules-directory support, so
# under DSH every rule was inert. Shipping them as skills fixes that, and the
# description is what carries the obligation: the skill catalogue injects it
# into every session whether or not the body is loaded.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SKILLS_DIR="$TOOLKIT_DIR/app/skills"
RULES_DIR="$TOOLKIT_DIR/app/rules"
GENERATOR="$TOOLKIT_DIR/scripts/generate_toolkit_rules_skills.py"

# ── Generation ───────────────────────────────────────────────────────────────

@test "toolkit rules: every top-level rule file has a generated skill" {
    for rule in "$RULES_DIR"/*.md; do
        [ -f "$rule" ] || continue
        stem="$(basename "$rule" .md)"
        [ -f "$SKILLS_DIR/$stem/SKILL.md" ]
    done
}

@test "toolkit rules: the generator is idempotent" {
    run python3 "$GENERATOR" --check
    [ "$status" -eq 0 ]
}

@test "toolkit rules: a rule without a description is skipped, not invented" {
    run grep -c "no entry in DESCRIPTIONS" "$GENERATOR"
    [ "$status" -eq 0 ]
}

# ── The description is the enforcement surface ───────────────────────────────

@test "toolkit rules: every generated skill carries a non-empty description" {
    for rule in "$RULES_DIR"/*.md; do
        [ -f "$rule" ] || continue
        stem="$(basename "$rule" .md)"
        skill="$SKILLS_DIR/$stem/SKILL.md"
        run grep -E '^description: ".{40,}"$' "$skill"
        [ "$status" -eq 0 ]
    done
}

@test "toolkit rules: descriptions carry triggers so the catalogue can match" {
    for rule in "$RULES_DIR"/*.md; do
        [ -f "$rule" ] || continue
        stem="$(basename "$rule" .md)"
        run grep -q "Triggers:" "$SKILLS_DIR/$stem/SKILL.md"
        [ "$status" -eq 0 ]
    done
}

@test "toolkit rules: names are DSH-legal kebab-case with no namespace colon" {
    # DSH validates a skill name with /^[a-z0-9]+(?:-[a-z0-9]+)*$/ and refuses
    # anything else, so a colon in a name makes the skill unloadable there.
    for rule in "$RULES_DIR"/*.md; do
        [ -f "$rule" ] || continue
        stem="$(basename "$rule" .md)"
        name="$(grep -m1 '^name:' "$SKILLS_DIR/$stem/SKILL.md" | sed 's/^name: *//')"
        [[ "$name" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]
    done
}

# ── The edit-discipline rule itself ──────────────────────────────────────────

@test "edit-discipline: requires the edit and write tools over shell rewrites" {
    run grep -qi "never by rewriting them through bash" \
        "$SKILLS_DIR/edit-discipline/SKILL.md"
    [ "$status" -eq 0 ]
}

@test "edit-discipline: requires a diff before a task is reported done" {
    run grep -q "git diff" "$SKILLS_DIR/edit-discipline/SKILL.md"
    [ "$status" -eq 0 ]
}

@test "edit-discipline: keeps the shell legitimate for builds and tests" {
    run grep -qi "builds, tests, linters" "$SKILLS_DIR/edit-discipline/SKILL.md"
    [ "$status" -eq 0 ]
}

@test "edit-discipline: the rule source and the skill body agree" {
    # The skill is generated from the rule file; drift between them means the
    # generator was bypassed and a hand edit will be silently overwritten.
    run python3 "$GENERATOR" --check --rules edit-discipline
    [ "$status" -eq 0 ]
}
