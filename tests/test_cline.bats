#!/usr/bin/env bats
# Dedicated tests for scripts/generate_cline.py and
# scripts/generate_cline_rules.py.
#
# Covers both surfaces:
#   1. Legacy .clinerules single-file output (stdout) used by older Cline
#      versions — backwards compatibility contract.
#   2. Modern .clinerules/*.md directory layout (Cline 3.7+) with:
#        - conditional "paths:" YAML frontmatter on file-type rules
#        - .clinerules/workflows/*.md slash-invocable workflows

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export CLINE_TMP; CLINE_TMP="$(mktemp -d)"
    export CLINE_STDOUT="$CLINE_TMP/cline-legacy"
    python3 "$TOOLKIT_DIR/scripts/generate_cline.py" > "$CLINE_STDOUT" 2>/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_cline_rules.py" "$CLINE_TMP" >/dev/null 2>&1
}

teardown_file() {
    rm -rf "$CLINE_TMP"
}

# ── Legacy stdout mode (.clinerules single file) ───────────────────────────

@test "generate_cline.py produces non-empty legacy output" {
    [ -s "$CLINE_STDOUT" ]
    [ "$(wc -c < "$CLINE_STDOUT" | xargs)" -gt 500 ]
}

@test "generate_cline.py legacy output references agents and skills" {
    grep -qi 'agent' "$CLINE_STDOUT"
    grep -qi 'skill' "$CLINE_STDOUT"
}

@test "generate_cline.py legacy output has TOOLKIT markers" {
    grep -q 'TOOLKIT:ai-toolkit START' "$CLINE_STDOUT"
    grep -q 'TOOLKIT:ai-toolkit END' "$CLINE_STDOUT"
}

# ── Modern .clinerules/ directory ──────────────────────────────────────────

@test "generate_cline_rules.py creates .clinerules/ directory" {
    [ -d "$CLINE_TMP/.clinerules" ]
}

@test "generate_cline_rules.py emits at least 6 standard rule files" {
    count=$(ls "$CLINE_TMP/.clinerules"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 6 ]
}

@test "generate_cline_rules.py testing rule has conditional paths frontmatter" {
    f="$CLINE_TMP/.clinerules/ai-toolkit-testing.md"
    [ -f "$f" ]
    head -1 "$f" | grep -q '^---'
    grep -q '^paths:' "$f"
    # Must match test files
    grep -q 'tests/' "$f"
}

@test "generate_cline_rules.py security rule has no conditional paths (always-on)" {
    f="$CLINE_TMP/.clinerules/ai-toolkit-security.md"
    [ -f "$f" ]
    # Security applies everywhere; no paths: frontmatter at the top
    ! head -1 "$f" | grep -q '^---' || ! grep -q '^paths:' "$f"
}

# ── Workflows (.clinerules/workflows/) ─────────────────────────────────────

@test "generate_cline_rules.py creates .clinerules/workflows/ directory" {
    [ -d "$CLINE_TMP/.clinerules/workflows" ]
}

@test "generate_cline_rules.py emits at least 10 workflow files" {
    count=$(ls "$CLINE_TMP/.clinerules/workflows"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 10 ]
}

@test "generate_cline_rules.py workflow files have description frontmatter" {
    for f in "$CLINE_TMP/.clinerules/workflows"/ai-toolkit-*.md; do
        head -1 "$f" | grep -q '^---' || { echo "No frontmatter: $f"; return 1; }
        grep -q '^description: ' "$f" || { echo "No description: $f"; return 1; }
    done
}

@test "generate_cline_rules.py workflows cover common development lifecycle" {
    [ -f "$CLINE_TMP/.clinerules/workflows/ai-toolkit-debug.md" ]
    [ -f "$CLINE_TMP/.clinerules/workflows/ai-toolkit-feature-development.md" ]
    [ -f "$CLINE_TMP/.clinerules/workflows/ai-toolkit-refactor.md" ]
    [ -f "$CLINE_TMP/.clinerules/workflows/ai-toolkit-security-audit.md" ]
}

# ── Language rules use conditional paths scoping ───────────────────────────

@test "generate_cline_rules.py scopes language rules to their file globs" {
    local tmp; tmp="$(mktemp -d)"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_cline_rules import generate
generate(Path('$tmp'), language_modules=['rules-python'])
" >/dev/null 2>&1
    [ -f "$tmp/.clinerules/ai-toolkit-lang-python.md" ]
    grep -q '^paths:' "$tmp/.clinerules/ai-toolkit-lang-python.md"
    grep -q '\*\*/\*.py' "$tmp/.clinerules/ai-toolkit-lang-python.md"
    # Common spans all languages — no conditional scoping
    [ -f "$tmp/.clinerules/ai-toolkit-lang-common.md" ]
    ! grep -q '^paths:' "$tmp/.clinerules/ai-toolkit-lang-common.md"
    rm -rf "$tmp"
}

# ── Idempotency and user-file preservation ─────────────────────────────────

@test "generate_cline_rules.py is idempotent across reruns" {
    local tmp; tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cline_rules.py" "$tmp" >/dev/null 2>&1
    count1=$(ls "$tmp/.clinerules"/ai-toolkit-*.md | wc -l | xargs)
    wf1=$(ls "$tmp/.clinerules/workflows"/ai-toolkit-*.md | wc -l | xargs)
    python3 "$TOOLKIT_DIR/scripts/generate_cline_rules.py" "$tmp" >/dev/null 2>&1
    count2=$(ls "$tmp/.clinerules"/ai-toolkit-*.md | wc -l | xargs)
    wf2=$(ls "$tmp/.clinerules/workflows"/ai-toolkit-*.md | wc -l | xargs)
    [ "$count1" -eq "$count2" ]
    [ "$wf1" -eq "$wf2" ]
    rm -rf "$tmp"
}

@test "generate_cline_rules.py preserves user files in .clinerules and workflows" {
    local tmp; tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cline_rules.py" "$tmp" >/dev/null 2>&1
    echo "my rule" > "$tmp/.clinerules/my-team-rules.md"
    echo "my workflow" > "$tmp/.clinerules/workflows/my-deploy.md"
    python3 "$TOOLKIT_DIR/scripts/generate_cline_rules.py" "$tmp" >/dev/null 2>&1
    grep -q '^my rule$' "$tmp/.clinerules/my-team-rules.md"
    grep -q '^my workflow$' "$tmp/.clinerules/workflows/my-deploy.md"
    rm -rf "$tmp"
}

@test "generate_cline_rules.py migrates legacy .clinerules file to directory" {
    local tmp; tmp="$(mktemp -d)"
    # Pre-3.7 layout: single file
    echo "# legacy" > "$tmp/.clinerules"
    [ -f "$tmp/.clinerules" ]
    python3 "$TOOLKIT_DIR/scripts/generate_cline_rules.py" "$tmp" >/dev/null 2>&1
    # Old file should be gone; directory exists
    [ -d "$tmp/.clinerules" ]
    [ -f "$tmp/.clinerules/ai-toolkit-security.md" ]
    rm -rf "$tmp"
}
