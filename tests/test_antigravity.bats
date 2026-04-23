#!/usr/bin/env bats
# Antigravity-specific tests for generate_antigravity.py.
# Verifies the new .agent/skills/ pointer emission alongside rules/workflows.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
POINTER_SKILL="ai-toolkit-skill-catalogue"

setup_file() {
    export AG_TMP; AG_TMP="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity.py" "$AG_TMP" >/dev/null
}

teardown_file() {
    rm -rf "$AG_TMP"
}

# ── Skill pointer ──────────────────────────────────────────────────────────

@test "antigravity: .agent/skills/ directory is created" {
    [ -d "$AG_TMP/.agent/skills" ]
}

@test "antigravity: pointer skill directory exists" {
    [ -d "$AG_TMP/.agent/skills/$POINTER_SKILL" ]
}

@test "antigravity: SKILL.md exists inside pointer skill" {
    [ -f "$AG_TMP/.agent/skills/$POINTER_SKILL/SKILL.md" ]
}

@test "antigravity: pointer SKILL.md has required frontmatter fields" {
    f="$AG_TMP/.agent/skills/$POINTER_SKILL/SKILL.md"
    head -5 "$f" | grep -q "^name: $POINTER_SKILL$"
    head -5 "$f" | grep -q "^description: "
}

@test "antigravity: pointer SKILL.md frontmatter is valid YAML block" {
    f="$AG_TMP/.agent/skills/$POINTER_SKILL/SKILL.md"
    head -1 "$f" | grep -q '^---$'
    # Second frontmatter fence must appear in first 10 lines
    head -10 "$f" | grep -c '^---$' | grep -q '^2$'
}

@test "antigravity: pointer SKILL.md references installed skill paths" {
    f="$AG_TMP/.agent/skills/$POINTER_SKILL/SKILL.md"
    grep -q '\.claude/skills' "$f"
    grep -q '~/\.claude/skills' "$f"
}

@test "antigravity: pointer SKILL.md includes at least 10 catalogue entries" {
    f="$AG_TMP/.agent/skills/$POINTER_SKILL/SKILL.md"
    count=$(grep -cE '^- \*\*' "$f")
    [ "$count" -ge 10 ]
}

# ── Skill pointer opt-out ──────────────────────────────────────────────────

@test "antigravity: emit_skill_pointer=False suppresses pointer" {
    tmp="$(mktemp -d)"
    python3 - <<PY >/dev/null 2>&1
import sys
from pathlib import Path
sys.path.insert(0, "$TOOLKIT_DIR/scripts")
from generate_antigravity import generate
generate(Path("$tmp"), emit_skill_pointer=False)
PY
    [ ! -d "$tmp/.agent/skills" ] || {
        # Accept empty directory, reject any SKILL.md.
        ! find "$tmp/.agent/skills" -name SKILL.md | grep -q .
    }
    rm -rf "$tmp"
}

# ── Rules / workflows still emitted ────────────────────────────────────────

@test "antigravity: rules still created alongside the skill pointer" {
    count=$(ls "$AG_TMP/.agent/rules"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 6 ]
}

@test "antigravity: workflows still created alongside the skill pointer" {
    count=$(ls "$AG_TMP/.agent/workflows"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 10 ]
}

@test "antigravity: regeneration is idempotent including the pointer" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity.py" "$tmp" >/dev/null
    snap1=$(shasum "$tmp/.agent/skills/$POINTER_SKILL/SKILL.md" | awk '{print $1}')
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity.py" "$tmp" >/dev/null
    snap2=$(shasum "$tmp/.agent/skills/$POINTER_SKILL/SKILL.md" | awk '{print $1}')
    [ "$snap1" = "$snap2" ]
    rm -rf "$tmp"
}
