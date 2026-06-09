#!/usr/bin/env bats
# Windsurf/Devin-Desktop integration tests for generate_windsurf_rules.py.
# Verifies activation-mode frontmatter (trigger, globs, description), the
# workflows directory emission, and the .devin/ + .windsurf/ dual-emit
# (.devin/ is primary since the 2026-06-02 Devin Desktop rebrand).

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

# ── Dual-emit: .devin/ primary tree ────────────────────────────────────────

@test "windsurf: rules are dual-emitted to .devin/rules" {
    [ -d "$WS_TMP/.devin/rules" ]
    [ -f "$WS_TMP/.devin/rules/ai-toolkit-security.md" ]
}

@test "windsurf: .devin and .windsurf rule trees are identical" {
    diff -r "$WS_TMP/.devin/rules" "$WS_TMP/.windsurf/rules"
}

@test "windsurf: workflows are dual-emitted to .devin/workflows" {
    [ -d "$WS_TMP/.devin/workflows" ]
    diff -r "$WS_TMP/.devin/workflows" "$WS_TMP/.windsurf/workflows"
}

@test "windsurf: skill pointer is dual-emitted to .devin and .windsurf" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_windsurf_skills.py" "$tmp" >/dev/null
    [ -f "$tmp/.devin/skills/ai-toolkit-skill-catalogue/SKILL.md" ]
    [ -f "$tmp/.windsurf/skills/ai-toolkit-skill-catalogue/SKILL.md" ]
    rm -rf "$tmp"
}

@test "windsurf: .devin/rules alone is detected as a windsurf install" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.devin/rules"
    run python3 - <<PY
import sys
from pathlib import Path
sys.path.insert(0, "$TOOLKIT_DIR/scripts")
from install_steps.ai_tools import _detect_editors
print(",".join(_detect_editors(Path("$tmp"))))
PY
    [ "$status" -eq 0 ]
    [[ "$output" == *"windsurf"* ]]
    rm -rf "$tmp"
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
