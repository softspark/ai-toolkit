#!/usr/bin/env bats
# Tests for the language-rules skills system (Option B).
#
# Per-language rules ship as `<lang>-rules` knowledge skills generated from
# `app/rules/<lang>/*.md`. Common rules are inlined into the project
# CLAUDE.md by `_inject_language_rules`. This test guards both halves.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SKILLS_DIR="$TOOLKIT_DIR/app/skills"
RULES_DIR="$TOOLKIT_DIR/app/rules"

setup() {
    TEST_PROJECT="$(mktemp -d)"
    mkdir -p "$TEST_PROJECT/.claude"
}

teardown() {
    rm -rf "$TEST_PROJECT"
}

# ── Skill presence and frontmatter ───────────────────────────────────────────

@test "language-rules skills: every per-language directory has a generated skill" {
    for dir in "$RULES_DIR"/*; do
        [ -d "$dir" ] || continue
        name="${dir##*/}"
        [ "$name" = "common" ] && continue
        skill="$SKILLS_DIR/$name-rules/SKILL.md"
        [ -f "$skill" ] || {
            echo "Missing skill: app/skills/$name-rules/SKILL.md" >&2
            return 1
        }
    done
}

@test "language-rules skills: SKILL.md frontmatter has required fields" {
    for skill in "$SKILLS_DIR"/*-rules/SKILL.md; do
        [ -f "$skill" ] || continue
        name="$(grep -E '^name: ' "$skill" | head -1 | awk '{print $2}')"
        [ -n "$name" ] || { echo "Missing name in $skill" >&2; return 1; }
        grep -q '^description: ' "$skill" || { echo "Missing description in $skill" >&2; return 1; }
        grep -q '^user-invocable: false$' "$skill" || { echo "Skill must be user-invocable: false in $skill" >&2; return 1; }
        grep -q '^allowed-tools: ' "$skill" || { echo "Missing allowed-tools in $skill" >&2; return 1; }
    done
}

@test "language-rules skills: name matches parent directory" {
    for skill in "$SKILLS_DIR"/*-rules/SKILL.md; do
        [ -f "$skill" ] || continue
        parent="$(basename "$(dirname "$skill")")"
        name="$(grep -E '^name: ' "$skill" | head -1 | awk '{print $2}')"
        [ "$parent" = "$name" ] || {
            echo "Directory $parent does not match name field $name" >&2
            return 1
        }
    done
}

@test "language-rules skills: generator --check is clean (skills up-to-date with rules)" {
    run python3 "$TOOLKIT_DIR/scripts/generate_language_rules_skills.py" --check
    [ "$status" -eq 0 ] || {
        echo "$output" >&2
        echo "Skills are out of date with app/rules/. Re-run scripts/generate_language_rules_skills.py" >&2
        return 1
    }
}

# ── _inject_language_rules behavior ──────────────────────────────────────────

@test "inject_language_rules: inlines common rules content into CLAUDE.md" {
    cd "$TEST_PROJECT"
    PYTHONPATH="$TOOLKIT_DIR/scripts" python3 -c "
from pathlib import Path
from install_steps.ai_tools import _inject_language_rules
_inject_language_rules(Path('$TEST_PROJECT'), ['rules-common', 'rules-python'])
"
    [ -f "$TEST_PROJECT/.claude/CLAUDE.md" ]
    # Marker is the singular language-rules tag (not per-language)
    grep -q '<!-- TOOLKIT:language-rules START -->' "$TEST_PROJECT/.claude/CLAUDE.md"
    grep -q '<!-- TOOLKIT:language-rules END -->' "$TEST_PROJECT/.claude/CLAUDE.md"
    # Common content is present (sample heading from common/coding-style.md)
    grep -q '^# Universal Coding Style' "$TEST_PROJECT/.claude/CLAUDE.md"
}

@test "inject_language_rules: references per-language skills by name, does not inline them" {
    cd "$TEST_PROJECT"
    PYTHONPATH="$TOOLKIT_DIR/scripts" python3 -c "
from pathlib import Path
from install_steps.ai_tools import _inject_language_rules
_inject_language_rules(Path('$TEST_PROJECT'), ['rules-common', 'rules-python', 'rules-typescript'])
"
    # Skill names are mentioned
    grep -q 'python-rules' "$TEST_PROJECT/.claude/CLAUDE.md"
    grep -q 'typescript-rules' "$TEST_PROJECT/.claude/CLAUDE.md"
    # Per-language inline content is NOT present (sample heading from
    # python/coding-style.md only appears as a category header inside the
    # generated skill, never in CLAUDE.md)
    ! grep -q '^# Python Coding Style' "$TEST_PROJECT/.claude/CLAUDE.md"
}

@test "inject_language_rules: idempotent on rerun (no duplicate markers)" {
    cd "$TEST_PROJECT"
    for _ in 1 2; do
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 -c "
from pathlib import Path
from install_steps.ai_tools import _inject_language_rules
_inject_language_rules(Path('$TEST_PROJECT'), ['rules-common', 'rules-python'])
"
    done
    count="$(grep -c '<!-- TOOLKIT:language-rules START -->' "$TEST_PROJECT/.claude/CLAUDE.md")"
    [ "$count" -eq 1 ]
}
