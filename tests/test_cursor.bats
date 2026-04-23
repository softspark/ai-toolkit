#!/usr/bin/env bats
# Cursor-specific tests for generate_cursor_mdc.py and generate_cursor_rules.py.
# The bulk of Cursor coverage lives in test_generators.bats; this file adds
# activation-mode and frontmatter contract tests that the 2026-04 docs sweep
# surfaced.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export CR_TMP; CR_TMP="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_mdc.py" "$CR_TMP" >/dev/null
}

teardown_file() {
    rm -rf "$CR_TMP"
}

# ── Frontmatter contract ──────────────────────────────────────────────────

@test "cursor: every .mdc begins with a YAML frontmatter fence" {
    for f in "$CR_TMP"/.cursor/rules/ai-toolkit-*.mdc; do
        head -1 "$f" | grep -q '^---$' || {
            echo "missing frontmatter fence: $f" >&2
            return 1
        }
    done
}

@test "cursor: every .mdc declares alwaysApply (the Cursor required key)" {
    for f in "$CR_TMP"/.cursor/rules/ai-toolkit-*.mdc; do
        head -10 "$f" | grep -q '^alwaysApply: ' || {
            echo "missing alwaysApply: $f" >&2
            return 1
        }
    done
}

@test "cursor: alwaysApply is only ever true or false" {
    for f in "$CR_TMP"/.cursor/rules/ai-toolkit-*.mdc; do
        val=$(head -10 "$f" | grep -m1 '^alwaysApply: ' | awk '{print $2}')
        case "$val" in
          true|false) ;;
          *) echo "bad alwaysApply '$val' in $f" >&2; return 1 ;;
        esac
    done
}

# ── Rule type mapping ─────────────────────────────────────────────────────

@test "cursor: agents-and-skills.mdc is Always Apply" {
    grep -q '^alwaysApply: true$' \
      "$CR_TMP/.cursor/rules/ai-toolkit-agents-and-skills.mdc"
}

@test "cursor: security.mdc is Always Apply" {
    grep -q '^alwaysApply: true$' \
      "$CR_TMP/.cursor/rules/ai-toolkit-security.mdc"
}

@test "cursor: testing.mdc is Apply to Specific Files (has globs)" {
    f="$CR_TMP/.cursor/rules/ai-toolkit-testing.mdc"
    grep -q '^globs: ' "$f"
    grep -q '^alwaysApply: false$' "$f"
}

@test "cursor: testing.mdc globs target test patterns" {
    f="$CR_TMP/.cursor/rules/ai-toolkit-testing.mdc"
    grep '^globs: ' "$f" | grep -q '\*\*/\*\.test\.\*'
    grep '^globs: ' "$f" | grep -q '\*\*/tests/\*\*'
}

@test "cursor: code-style.mdc is Apply Intelligently (description, no always/globs)" {
    f="$CR_TMP/.cursor/rules/ai-toolkit-code-style.mdc"
    grep -q '^description: ' "$f"
    grep -q '^alwaysApply: false$' "$f"
    ! grep -q '^globs: ' "$f"
}

# ── Legacy .cursorrules generator ─────────────────────────────────────────

@test "cursor: generate_cursor_rules.py still produces non-empty output" {
    out="$(mktemp)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_rules.py" > "$out" 2>/dev/null
    [ "$(wc -c < "$out" | xargs)" -gt 200 ]
    rm -f "$out"
}

@test "cursor: .mdc regeneration is idempotent" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_mdc.py" "$tmp" >/dev/null
    snap1=$(find "$tmp" -type f | sort | xargs shasum | shasum | awk '{print $1}')
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_mdc.py" "$tmp" >/dev/null
    snap2=$(find "$tmp" -type f | sort | xargs shasum | shasum | awk '{print $1}')
    [ "$snap1" = "$snap2" ]
    rm -rf "$tmp"
}
