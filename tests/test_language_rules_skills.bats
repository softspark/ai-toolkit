#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for the language-rules skills system (Option B).
#
# Per-language rules ship as `<lang>-rules` knowledge skills generated from
# `app/rules/<lang>/*.md`. Common rules ship as Claude Code path-scoped
# `ai-toolkit-*.md` rule files: user-level from the global install, and in the
# project only for a rule the global install does not provide. CLAUDE.md is
# kept as a compact index. This test guards both halves.
#
# HOME is a per-test directory: whether a project gets rule copies depends on
# what ~/.claude/rules holds, and the developer's real one must not decide it.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SKILLS_DIR="$TOOLKIT_DIR/app/skills"
RULES_DIR="$TOOLKIT_DIR/app/rules"

setup() {
    TEST_PROJECT="$(mktemp -d)"
    mkdir -p "$TEST_PROJECT/.claude"
    TEST_HOME="$(mktemp -d)"
    export HOME="$TEST_HOME"
}

teardown() {
    rm -rf "$TEST_PROJECT" "$TEST_HOME"
}

# Write the user-level common rules a global install with profile $1 writes.
_global_rules() {
    PYTHONPATH="$TOOLKIT_DIR/scripts" python3 -c "
from pathlib import Path
from install_steps.ai_tools import common_rule_sources, render_common_rule
root = Path('$TEST_HOME') / '.claude' / 'rules'
root.mkdir(parents=True, exist_ok=True)
for stem, body, paths in common_rule_sources('$1'):
    (root / f'ai-toolkit-{stem}.md').write_text(render_common_rule(body, paths))
"
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

@test "inject_language_rules: writes common rules as path-scoped Claude rules" {
    cd "$TEST_PROJECT"
    PYTHONPATH="$TOOLKIT_DIR/scripts" python3 -c "
from pathlib import Path
from install_steps.ai_tools import _inject_language_rules
_inject_language_rules(Path('$TEST_PROJECT'), ['rules-common', 'rules-python'])
"
    [ -f "$TEST_PROJECT/.claude/CLAUDE.md" ]
    [ -f "$TEST_PROJECT/.claude/rules/ai-toolkit-coding-style.md" ]
    [ -f "$TEST_PROJECT/.claude/rules/ai-toolkit-security.md" ]
    # Marker is the singular language-rules tag (not per-language)
    grep -q '<!-- TOOLKIT:language-rules START -->' "$TEST_PROJECT/.claude/CLAUDE.md"
    grep -q '<!-- TOOLKIT:language-rules END -->' "$TEST_PROJECT/.claude/CLAUDE.md"
    # CLAUDE.md stays a compact index; full common content is in path-scoped rules.
    ! grep -q '^# Universal Coding Style' "$TEST_PROJECT/.claude/CLAUDE.md"
    grep -q '^# Universal Coding Style' "$TEST_PROJECT/.claude/rules/ai-toolkit-coding-style.md"
    grep -q '^paths:$' "$TEST_PROJECT/.claude/rules/ai-toolkit-coding-style.md"
    grep -q '  - "\*\*/\*"' "$TEST_PROJECT/.claude/rules/ai-toolkit-coding-style.md"
}

@test "inject_language_rules: source paths frontmatter scopes testing/performance, others stay always-on" {
    cd "$TEST_PROJECT"
    PYTHONPATH="$TOOLKIT_DIR/scripts" python3 -c "
from pathlib import Path
from install_steps.ai_tools import _inject_language_rules
_inject_language_rules(Path('$TEST_PROJECT'), ['rules-common', 'rules-python'])
"
    # Scoped rules carry their source globs and must NOT fall back to **/*
    testing="$TEST_PROJECT/.claude/rules/ai-toolkit-testing.md"
    grep -q '  - "\*\*/tests/\*\*"' "$testing"
    grep -q '  - "\*\*/test_\*"' "$testing"
    ! grep -q '  - "\*\*/\*"$' "$testing"
    perf="$TEST_PROJECT/.claude/rules/ai-toolkit-performance.md"
    grep -q '  - "\*\*/\*\.py"' "$perf"
    ! grep -q '  - "\*\*/\*"$' "$perf"
    # Rules without a source paths block are always-on
    for name in coding-style git-workflow security; do
        f="$TEST_PROJECT/.claude/rules/ai-toolkit-$name.md"
        grep -q '  - "\*\*/\*"$' "$f" || { echo "$name must be always-on" >&2; return 1; }
    done
    # The CLAUDE.md index tells the truth about which is which
    idx="$TEST_PROJECT/.claude/CLAUDE.md"
    grep -q '^Always-on: .*ai-toolkit-security.md' "$idx"
    grep -q '^Path-scoped: .*ai-toolkit-testing.md' "$idx"
    ! grep -q 'load when project files are opened' "$idx"
}

@test "inject_language_rules: git-team ships with the strict profile only and converges on rerun" {
    cd "$TEST_PROJECT"
    _inject() {
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 -c "
from pathlib import Path
from install_steps.ai_tools import _inject_language_rules
_inject_language_rules(Path('$TEST_PROJECT'), ['rules-common'], profile='$1')
"
    }
    _inject standard
    [ ! -f "$TEST_PROJECT/.claude/rules/ai-toolkit-git-team.md" ]
    [ -f "$TEST_PROJECT/.claude/rules/ai-toolkit-git-workflow.md" ]
    # The solo-safe core must not carry team-only conventions
    ! grep -q 'Require at least one approval' "$TEST_PROJECT/.claude/rules/ai-toolkit-git-workflow.md"
    ! grep -q 'Use feature branches' "$TEST_PROJECT/.claude/rules/ai-toolkit-git-workflow.md"

    _inject strict
    [ -f "$TEST_PROJECT/.claude/rules/ai-toolkit-git-team.md" ]
    grep -q 'Require at least one approval' "$TEST_PROJECT/.claude/rules/ai-toolkit-git-team.md"
    grep -q '  - "\*\*/\*"$' "$TEST_PROJECT/.claude/rules/ai-toolkit-git-team.md"
    grep -q '^Always-on: .*ai-toolkit-git-team.md' "$TEST_PROJECT/.claude/CLAUDE.md"

    # Back to standard: the managed strict-only file is removed, user files untouched
    printf '# mine\n' > "$TEST_PROJECT/.claude/rules/my-rule.md"
    _inject standard
    [ ! -f "$TEST_PROJECT/.claude/rules/ai-toolkit-git-team.md" ]
    [ -f "$TEST_PROJECT/.claude/rules/my-rule.md" ]
    ! grep -q 'ai-toolkit-git-team.md' "$TEST_PROJECT/.claude/CLAUDE.md"
}

@test "inject_language_rules: generated frontmatter mirrors the source paths block exactly" {
    cd "$TEST_PROJECT"
    PYTHONPATH="$TOOLKIT_DIR/scripts" python3 -c "
from pathlib import Path
from install_steps.ai_tools import _inject_language_rules
_inject_language_rules(Path('$TEST_PROJECT'), ['rules-common'])
"
    for src in "$RULES_DIR"/common/*.md; do
        name="$(basename "$src" .md)"
        # Profile-gated sources (git-team) are absent under the default profile
        grep -q '^profiles:' "$src" && continue
        out="$TEST_PROJECT/.claude/rules/ai-toolkit-$name.md"
        # Source globs, in order, as the installer emits them
        expected="$(awk '/^paths:/{f=1;next} f&&/^  - /{print;next} f&&NF{exit}' "$src")"
        [ -n "$expected" ] || expected='  - "**/*"'
        actual="$(awk 'NR==1{next} /^---$/{exit} /^  - /{print}' "$out")"
        [ "$expected" = "$actual" ] || {
            echo "paths drift for $name" >&2
            echo "expected:"; echo "$expected"; echo "actual:"; echo "$actual"
            return 1
        }
    done
}

@test "inject_language_rules: keeps CLAUDE.md below Claude Code size guidance" {
    cd "$TEST_PROJECT"
    PYTHONPATH="$TOOLKIT_DIR/scripts" python3 -c "
from pathlib import Path
from install_steps.ai_tools import _inject_language_rules
_inject_language_rules(Path('$TEST_PROJECT'), ['rules-common', 'rules-python', 'rules-typescript'])
"
    line_count="$(wc -l < "$TEST_PROJECT/.claude/CLAUDE.md" | tr -d ' ')"
    [ "$line_count" -lt 200 ]
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

@test "inject_language_rules: no project copies when the global install provides them" {
    _global_rules standard
    mkdir -p "$TEST_PROJECT/.claude/rules"
    # A project installed before the move carries its own copies
    echo "old" > "$TEST_PROJECT/.claude/rules/ai-toolkit-coding-style.md"
    echo "old" > "$TEST_PROJECT/.claude/rules/ai-toolkit-testing.md"
    echo "user" > "$TEST_PROJECT/.claude/rules/team-rule.md"
    cd "$TEST_PROJECT"
    PYTHONPATH="$TOOLKIT_DIR/scripts" python3 -c "
from pathlib import Path
from install_steps.ai_tools import _inject_language_rules
_inject_language_rules(Path('$TEST_PROJECT'), ['rules-common', 'rules-python'])
"
    # Claude Code loads ~/.claude/rules and every parent .claude/rules, so a
    # project copy would load each rule twice
    [ ! -f "$TEST_PROJECT/.claude/rules/ai-toolkit-coding-style.md" ]
    [ ! -f "$TEST_PROJECT/.claude/rules/ai-toolkit-testing.md" ]
    [ -f "$TEST_PROJECT/.claude/rules/team-rule.md" ]
    idx="$TEST_PROJECT/.claude/CLAUDE.md"
    grep -q '^Always-on: .*`~/.claude/rules/ai-toolkit-security.md`' "$idx"
    grep -q '^Path-scoped: .*`~/.claude/rules/ai-toolkit-testing.md`' "$idx"
}

@test "inject_language_rules: a nested project and its parent carry no copies" {
    _global_rules standard
    mkdir -p "$TEST_PROJECT/child/.claude"
    for dir in "$TEST_PROJECT" "$TEST_PROJECT/child"; do
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 -c "
from pathlib import Path
from install_steps.ai_tools import _inject_language_rules
_inject_language_rules(Path('$dir'), ['rules-common'])
"
    done
    run find "$TEST_PROJECT" -name 'ai-toolkit-*.md'
    [ -z "$output" ]
}

@test "inject_language_rules: a strict project under a standard global install gets git-team only" {
    _global_rules standard
    cd "$TEST_PROJECT"
    PYTHONPATH="$TOOLKIT_DIR/scripts" python3 -c "
from pathlib import Path
from install_steps.ai_tools import _inject_language_rules
_inject_language_rules(Path('$TEST_PROJECT'), ['rules-common'], profile='strict')
"
    run find "$TEST_PROJECT/.claude/rules" -name 'ai-toolkit-*.md'
    [ "$output" = "$TEST_PROJECT/.claude/rules/ai-toolkit-git-team.md" ]
    grep -q '^Always-on: .*`.claude/rules/ai-toolkit-git-team.md`' "$TEST_PROJECT/.claude/CLAUDE.md"
}

@test "inject_language_rules: removes stale managed common rules only" {
    cd "$TEST_PROJECT"
    mkdir -p "$TEST_PROJECT/.claude/rules"
    echo "old" > "$TEST_PROJECT/.claude/rules/ai-toolkit-stale.md"
    echo "user" > "$TEST_PROJECT/.claude/rules/team-rule.md"
    PYTHONPATH="$TOOLKIT_DIR/scripts" python3 -c "
from pathlib import Path
from install_steps.ai_tools import _inject_language_rules
_inject_language_rules(Path('$TEST_PROJECT'), ['rules-common'])
"
    [ ! -f "$TEST_PROJECT/.claude/rules/ai-toolkit-stale.md" ]
    [ -f "$TEST_PROJECT/.claude/rules/team-rule.md" ]
}
