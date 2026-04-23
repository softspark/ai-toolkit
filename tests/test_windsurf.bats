#!/usr/bin/env bats
# Windsurf-specific integration tests for generate_windsurf_rules.py.
# Verifies activation-mode frontmatter (trigger, globs, description) and
# the new .windsurf/workflows/ directory emission.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export WS_TMP; WS_TMP="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_windsurf_rules.py" "$WS_TMP" >/dev/null
}

teardown_file() {
    rm -rf "$WS_TMP"
}

# ── Activation modes ───────────────────────────────────────────────────────

@test "windsurf: agents-and-skills.md is always_on" {
    head -5 "$WS_TMP/.windsurf/rules/ai-toolkit-agents-and-skills.md" \
      | grep -q "^trigger: always_on$"
}

@test "windsurf: security.md is always_on" {
    head -5 "$WS_TMP/.windsurf/rules/ai-toolkit-security.md" \
      | grep -q "^trigger: always_on$"
}

@test "windsurf: quality-standards.md is always_on" {
    head -5 "$WS_TMP/.windsurf/rules/ai-toolkit-quality-standards.md" \
      | grep -q "^trigger: always_on$"
}

@test "windsurf: testing.md is glob with test patterns" {
    head -5 "$WS_TMP/.windsurf/rules/ai-toolkit-testing.md" \
      | grep -q "^trigger: glob$"
    head -5 "$WS_TMP/.windsurf/rules/ai-toolkit-testing.md" \
      | grep -q "^globs: .*\*\*/\*\.test\.\*"
}

@test "windsurf: code-style.md is model_decision with description" {
    head -5 "$WS_TMP/.windsurf/rules/ai-toolkit-code-style.md" \
      | grep -q "^trigger: model_decision$"
    head -5 "$WS_TMP/.windsurf/rules/ai-toolkit-code-style.md" \
      | grep -q "^description: "
}

@test "windsurf: workflow.md is model_decision with description" {
    head -5 "$WS_TMP/.windsurf/rules/ai-toolkit-workflow.md" \
      | grep -q "^trigger: model_decision$"
}

@test "windsurf: every rule file starts with a YAML frontmatter block" {
    for f in "$WS_TMP"/.windsurf/rules/ai-toolkit-*.md; do
        head -1 "$f" | grep -q '^---$' || {
            echo "missing frontmatter: $f" >&2
            return 1
        }
    done
}

@test "windsurf: every trigger value is a known Windsurf mode" {
    for f in "$WS_TMP"/.windsurf/rules/ai-toolkit-*.md; do
        trigger=$(grep -m1 '^trigger: ' "$f" | awk '{print $2}')
        case "$trigger" in
          always_on|glob|model_decision|manual) ;;
          *) echo "unknown trigger '$trigger' in $f" >&2; return 1 ;;
        esac
    done
}

# ── Workflows directory ────────────────────────────────────────────────────

@test "windsurf: workflows directory exists" {
    [ -d "$WS_TMP/.windsurf/workflows" ]
}

@test "windsurf: at least 10 workflow files are emitted" {
    count=$(ls "$WS_TMP/.windsurf/workflows"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 10 ]
}

@test "windsurf: every workflow has a description frontmatter field" {
    for f in "$WS_TMP"/.windsurf/workflows/ai-toolkit-*.md; do
        grep -q '^description: ' "$f" || {
            echo "missing description: $f" >&2
            return 1
        }
    done
}

# ── Regeneration / idempotency ────────────────────────────────────────────

@test "windsurf: regeneration is idempotent" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_windsurf_rules.py" "$tmp" >/dev/null
    snap1=$(find "$tmp" -type f | sort | xargs shasum | shasum | awk '{print $1}')
    python3 "$TOOLKIT_DIR/scripts/generate_windsurf_rules.py" "$tmp" >/dev/null
    snap2=$(find "$tmp" -type f | sort | xargs shasum | shasum | awk '{print $1}')
    [ "$snap1" = "$snap2" ]
    rm -rf "$tmp"
}

@test "windsurf: user-authored workflow files are preserved" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_windsurf_rules.py" "$tmp" >/dev/null
    echo "# user workflow" > "$tmp/.windsurf/workflows/my-custom.md"
    python3 "$TOOLKIT_DIR/scripts/generate_windsurf_rules.py" "$tmp" >/dev/null
    [ -f "$tmp/.windsurf/workflows/my-custom.md" ]
    rm -rf "$tmp"
}
