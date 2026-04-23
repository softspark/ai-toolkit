#!/usr/bin/env bats
# Dedicated tests for scripts/generate_copilot.py.
#
# Covers the three Copilot surfaces the generator now emits:
#   1. .github/copilot-instructions.md (stdout, legacy)
#   2. .github/instructions/*.instructions.md (path-specific)
#   3. .github/prompts/*.prompt.md (prompt files / slash commands)
#
# Features gated behind Copilot Pro/Business/Enterprise (custom agents,
# repo-level MCP, organization-wide instructions) are intentionally not
# exercised here — they are classified as class C in the ecosystem-sync
# SOP and live outside the OSS surface this generator targets.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export COPILOT_TMP; COPILOT_TMP="$(mktemp -d)"
    export COPILOT_STDOUT="$COPILOT_TMP/copilot-instructions.md"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" > "$COPILOT_STDOUT" 2>/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$COPILOT_TMP" >/dev/null 2>&1
}

teardown_file() {
    rm -rf "$COPILOT_TMP"
}

# ── Legacy stdout mode ─────────────────────────────────────────────────────

@test "generate_copilot.py stdout mode produces copilot-instructions markdown" {
    [ -s "$COPILOT_STDOUT" ]
    grep -q '^# GitHub Copilot Instructions' "$COPILOT_STDOUT"
}

@test "generate_copilot.py stdout output references agents and skills" {
    grep -qi 'agent' "$COPILOT_STDOUT"
    grep -qi 'skill' "$COPILOT_STDOUT"
}

@test "generate_copilot.py stdout wraps output in toolkit markers" {
    grep -q 'TOOLKIT:ai-toolkit START' "$COPILOT_STDOUT"
    grep -q 'TOOLKIT:ai-toolkit END' "$COPILOT_STDOUT"
}

# ── Path-specific .instructions.md files ───────────────────────────────────

@test "generate_copilot.py creates .github/instructions/ directory" {
    [ -d "$COPILOT_TMP/.github/instructions" ]
}

@test "generate_copilot.py emits at least 5 instruction files" {
    count=$(ls "$COPILOT_TMP/.github/instructions"/ai-toolkit-*.instructions.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 5 ]
}

@test "generate_copilot.py instruction files have applyTo frontmatter" {
    for f in "$COPILOT_TMP/.github/instructions"/ai-toolkit-*.instructions.md; do
        head -1 "$f" | grep -q '^---' || { echo "No frontmatter: $f"; return 1; }
        grep -q '^applyTo: ' "$f" || { echo "No applyTo: $f"; return 1; }
    done
}

@test "generate_copilot.py scopes testing rule to test-file globs" {
    f="$COPILOT_TMP/.github/instructions/ai-toolkit-testing.instructions.md"
    [ -f "$f" ]
    grep -q 'applyTo: ".*test' "$f"
    grep -q '# Testing' "$f"
}

@test "generate_copilot.py applies security rule to all files (applyTo **)" {
    f="$COPILOT_TMP/.github/instructions/ai-toolkit-security.instructions.md"
    [ -f "$f" ]
    grep -q 'applyTo: "\*\*"' "$f"
}

# ── Prompt files (slash commands for VS Code Copilot) ──────────────────────

@test "generate_copilot.py creates .github/prompts/ directory" {
    [ -d "$COPILOT_TMP/.github/prompts" ]
}

@test "generate_copilot.py emits at least 10 prompt files" {
    count=$(ls "$COPILOT_TMP/.github/prompts"/ai-toolkit-*.prompt.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 10 ]
}

@test "generate_copilot.py prompt files have description frontmatter" {
    for f in "$COPILOT_TMP/.github/prompts"/ai-toolkit-*.prompt.md; do
        head -1 "$f" | grep -q '^---' || { echo "No frontmatter: $f"; return 1; }
        grep -q '^description: ' "$f" || { echo "No description: $f"; return 1; }
    done
}

@test "generate_copilot.py emits a debug prompt file" {
    [ -f "$COPILOT_TMP/.github/prompts/ai-toolkit-debug.prompt.md" ]
}

@test "generate_copilot.py excludes knowledge-only skills from prompts" {
    # Skills with user-invocable: false (e.g. rag-patterns) must NOT appear
    # as slash commands — they are knowledge-only.
    [ ! -f "$COPILOT_TMP/.github/prompts/ai-toolkit-rag-patterns.prompt.md" ]
}

# ── Language-specific instructions ─────────────────────────────────────────

@test "generate_copilot.py honors language_modules via generate()" {
    local tmp; tmp="$(mktemp -d)"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_copilot import generate
generate(Path('$tmp'), language_modules=['rules-python'], emit_prompts=False)
" >/dev/null 2>&1
    [ -f "$tmp/.github/instructions/ai-toolkit-lang-common.instructions.md" ]
    [ -f "$tmp/.github/instructions/ai-toolkit-lang-python.instructions.md" ]
    grep -q '\*\*/\*.py' "$tmp/.github/instructions/ai-toolkit-lang-python.instructions.md"
    rm -rf "$tmp"
}

# ── Registered custom rules ────────────────────────────────────────────────

@test "generate_copilot.py wraps registered custom rules as always-on instructions" {
    local tmp; tmp="$(mktemp -d)"
    local rules_tmp; rules_tmp="$(mktemp -d)"
    echo "# Team Standards" > "$rules_tmp/team-standards.md"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_copilot import generate
generate(Path('$tmp'), rules_dir=Path('$rules_tmp'), emit_prompts=False)
" >/dev/null 2>&1
    [ -f "$tmp/.github/instructions/ai-toolkit-custom-team-standards.instructions.md" ]
    grep -q 'applyTo: "\*\*"' "$tmp/.github/instructions/ai-toolkit-custom-team-standards.instructions.md"
    grep -q 'Team Standards' "$tmp/.github/instructions/ai-toolkit-custom-team-standards.instructions.md"
    rm -rf "$tmp" "$rules_tmp"
}

# ── Idempotency and cleanup ────────────────────────────────────────────────

@test "generate_copilot.py is idempotent across reruns" {
    local tmp; tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1
    count1=$(ls "$tmp/.github/instructions"/ai-toolkit-*.instructions.md | wc -l | xargs)
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1
    count2=$(ls "$tmp/.github/instructions"/ai-toolkit-*.instructions.md | wc -l | xargs)
    [ "$count1" -eq "$count2" ]
    rm -rf "$tmp"
}

@test "generate_copilot.py cleans stale ai-toolkit-* files" {
    local tmp; tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1
    # Inject a stale file
    echo "stale" > "$tmp/.github/instructions/ai-toolkit-obsolete.instructions.md"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1
    [ ! -f "$tmp/.github/instructions/ai-toolkit-obsolete.instructions.md" ]
    rm -rf "$tmp"
}

@test "generate_copilot.py preserves user files in instructions/ and prompts/" {
    local tmp; tmp="$(mktemp -d)"
    mkdir -p "$tmp/.github/instructions" "$tmp/.github/prompts"
    echo "user" > "$tmp/.github/instructions/my-custom.instructions.md"
    echo "user" > "$tmp/.github/prompts/my-shortcut.prompt.md"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1
    grep -q '^user$' "$tmp/.github/instructions/my-custom.instructions.md"
    grep -q '^user$' "$tmp/.github/prompts/my-shortcut.prompt.md"
    rm -rf "$tmp"
}
