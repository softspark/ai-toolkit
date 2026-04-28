#!/usr/bin/env bats
# Tests for Bucket 3 — native skill surfaces across Gemini, Augment, Codex.
#
# Covers:
#   - scripts/generate_gemini_skills.py  (pointer pattern)
#   - scripts/generate_augment_skills.py (pointer pattern)
#   - scripts/generate_codex_skills.py   (.agents/skills mirror, opt-in)

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
POINTER_SKILL="ai-toolkit-skill-catalogue"

setup_file() {
    export B3_GEMINI; B3_GEMINI="$(mktemp -d)"
    export B3_AUGMENT; B3_AUGMENT="$(mktemp -d)"
    export B3_CODEX_OFF; B3_CODEX_OFF="$(mktemp -d)"
    export B3_CODEX_ON; B3_CODEX_ON="$(mktemp -d)"

    python3 "$TOOLKIT_DIR/scripts/generate_gemini_skills.py" "$B3_GEMINI" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_augment_skills.py" "$B3_AUGMENT" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$B3_CODEX_OFF" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$B3_CODEX_ON" --enable >/dev/null
}

teardown_file() {
    rm -rf "$B3_GEMINI" "$B3_AUGMENT" "$B3_CODEX_OFF" "$B3_CODEX_ON"
}

# ── Gemini pointer ────────────────────────────────────────────────────────

@test "gemini-skills: .gemini/skills/ directory is created" {
    [ -d "$B3_GEMINI/.gemini/skills" ]
}

@test "gemini-skills: pointer skill directory and SKILL.md exist" {
    [ -d "$B3_GEMINI/.gemini/skills/$POINTER_SKILL" ]
    [ -f "$B3_GEMINI/.gemini/skills/$POINTER_SKILL/SKILL.md" ]
}

@test "gemini-skills: pointer SKILL.md has valid frontmatter" {
    f="$B3_GEMINI/.gemini/skills/$POINTER_SKILL/SKILL.md"
    head -1 "$f" | grep -q '^---$'
    head -10 "$f" | grep -c '^---$' | grep -q '^2$'
    head -5 "$f" | grep -q "^name: $POINTER_SKILL$"
    head -5 "$f" | grep -q "^description: "
}

@test "gemini-skills: pointer SKILL.md references .claude/skills" {
    f="$B3_GEMINI/.gemini/skills/$POINTER_SKILL/SKILL.md"
    grep -q '\.claude/skills' "$f"
    grep -q '~/\.claude/skills' "$f"
}

@test "gemini-skills: pointer SKILL.md lists catalogue entries" {
    f="$B3_GEMINI/.gemini/skills/$POINTER_SKILL/SKILL.md"
    count=$(grep -cE '^- \*\*' "$f")
    [ "$count" -ge 10 ]
}

@test "gemini-skills: only one SKILL.md emitted (pointer pattern, not 99 files)" {
    count=$(find "$B3_GEMINI/.gemini/skills" -name SKILL.md | wc -l | xargs)
    [ "$count" -eq 1 ]
}

@test "gemini-skills: regeneration is idempotent" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_gemini_skills.py" "$tmp" >/dev/null
    h1=$(shasum "$tmp/.gemini/skills/$POINTER_SKILL/SKILL.md" | awk '{print $1}')
    python3 "$TOOLKIT_DIR/scripts/generate_gemini_skills.py" "$tmp" >/dev/null
    h2=$(shasum "$tmp/.gemini/skills/$POINTER_SKILL/SKILL.md" | awk '{print $1}')
    [ "$h1" = "$h2" ]
    rm -rf "$tmp"
}

@test "gemini-skills: emit_skill_pointer=False is a no-op" {
    tmp="$(mktemp -d)"
    python3 - <<PY >/dev/null 2>&1
import sys
from pathlib import Path
sys.path.insert(0, "$TOOLKIT_DIR/scripts")
from generate_gemini_skills import generate
generate(Path("$tmp"), emit_skill_pointer=False)
PY
    [ ! -d "$tmp/.gemini/skills" ] || ! find "$tmp/.gemini/skills" -name SKILL.md | grep -q .
    rm -rf "$tmp"
}

# ── Augment pointer ───────────────────────────────────────────────────────

@test "augment-skills: .augment/skills/ directory is created" {
    [ -d "$B3_AUGMENT/.augment/skills" ]
}

@test "augment-skills: pointer skill directory and SKILL.md exist" {
    [ -d "$B3_AUGMENT/.augment/skills/$POINTER_SKILL" ]
    [ -f "$B3_AUGMENT/.augment/skills/$POINTER_SKILL/SKILL.md" ]
}

@test "augment-skills: pointer SKILL.md has valid frontmatter" {
    f="$B3_AUGMENT/.augment/skills/$POINTER_SKILL/SKILL.md"
    head -1 "$f" | grep -q '^---$'
    head -10 "$f" | grep -c '^---$' | grep -q '^2$'
    head -5 "$f" | grep -q "^name: $POINTER_SKILL$"
}

@test "augment-skills: pointer SKILL.md references .claude/skills" {
    f="$B3_AUGMENT/.augment/skills/$POINTER_SKILL/SKILL.md"
    grep -q '\.claude/skills' "$f"
    grep -q '~/\.claude/skills' "$f"
}

@test "augment-skills: pointer lists catalogue entries (>=10)" {
    f="$B3_AUGMENT/.augment/skills/$POINTER_SKILL/SKILL.md"
    count=$(grep -cE '^- \*\*' "$f")
    [ "$count" -ge 10 ]
}

@test "augment-skills: only one SKILL.md emitted (pointer pattern)" {
    count=$(find "$B3_AUGMENT/.augment/skills" -name SKILL.md | wc -l | xargs)
    [ "$count" -eq 1 ]
}

@test "augment-skills: regeneration is idempotent" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_augment_skills.py" "$tmp" >/dev/null
    h1=$(shasum "$tmp/.augment/skills/$POINTER_SKILL/SKILL.md" | awk '{print $1}')
    python3 "$TOOLKIT_DIR/scripts/generate_augment_skills.py" "$tmp" >/dev/null
    h2=$(shasum "$tmp/.augment/skills/$POINTER_SKILL/SKILL.md" | awk '{print $1}')
    [ "$h1" = "$h2" ]
    rm -rf "$tmp"
}

# ── Codex mirror (opt-in) ─────────────────────────────────────────────────

@test "codex-skills: default is no-op — nothing written without --enable" {
    [ ! -d "$B3_CODEX_OFF/.agents" ] || [ -z "$(find "$B3_CODEX_OFF/.agents" -mindepth 1 -print -quit)" ]
}

@test "codex-skills: generate() default signature defaults to disabled" {
    tmp="$(mktemp -d)"
    python3 - <<PY >/dev/null 2>&1
import sys
from pathlib import Path
sys.path.insert(0, "$TOOLKIT_DIR/scripts")
from generate_codex_skills import generate
generate(Path("$tmp"))  # no kwargs — must stay disabled
PY
    [ ! -d "$tmp/.agents/skills" ] || [ -z "$(ls "$tmp/.agents/skills" 2>/dev/null)" ]
    rm -rf "$tmp"
}

@test "codex-skills: --enable mirrors the catalogue into .agents/skills" {
    [ -d "$B3_CODEX_ON/.agents/skills" ]
    count=$(ls "$B3_CODEX_ON/.agents/skills" | wc -l | xargs)
    [ "$count" -ge 50 ]
}

@test "codex-skills: each mirrored entry exposes SKILL.md" {
    missing=0
    for d in "$B3_CODEX_ON/.agents/skills"/*; do
        [ -f "$d/SKILL.md" ] || missing=$((missing+1))
    done
    [ "$missing" -eq 0 ]
}

@test "codex-skills: prefers symlinks for native Codex skills" {
    f="$B3_CODEX_ON/.agents/skills/clean-code"
    [ -L "$f" ] || [ -d "$f" ]  # symlink OR fallback copy
    if [ -L "$f" ]; then
        target=$(readlink "$f")
        case "$target" in
            *app/skills/clean-code) : ;;
            *) false ;;
        esac
    fi
}

@test "codex-skills: adapts Claude-only orchestration skills" {
    [ -f "$B3_CODEX_ON/.agents/skills/orchestrate/SKILL.md" ]
    grep -q 'Codex Translation Layer' "$B3_CODEX_ON/.agents/skills/orchestrate/SKILL.md"
    ! grep -q 'allowed-tools:.*Agent' "$B3_CODEX_ON/.agents/skills/orchestrate/SKILL.md"
}

@test "codex-skills: skips _lib internal directory" {
    [ ! -e "$B3_CODEX_ON/.agents/skills/_lib" ]
}

@test "codex-skills: regeneration is idempotent (symlink count stable)" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$tmp" --enable >/dev/null
    c1=$(ls "$tmp/.agents/skills" | wc -l | xargs)
    python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$tmp" --enable >/dev/null
    c2=$(ls "$tmp/.agents/skills" | wc -l | xargs)
    [ "$c1" = "$c2" ]
    rm -rf "$tmp"
}

@test "codex-skills: cleanup removes stale managed symlinks" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$tmp" --enable >/dev/null
    # Inject a fake stale symlink pointing inside our app/skills/ tree.
    ln -s "$TOOLKIT_DIR/app/skills/clean-code" "$tmp/.agents/skills/zz-stale-entry"
    python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$tmp" --enable >/dev/null
    [ ! -e "$tmp/.agents/skills/zz-stale-entry" ]
    rm -rf "$tmp"
}

@test "codex-skills: leaves user-authored entries alone" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$tmp" --enable >/dev/null
    mkdir -p "$tmp/.agents/skills/user-authored"
    echo "hello" > "$tmp/.agents/skills/user-authored/notes.txt"
    python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$tmp" --enable >/dev/null
    [ -f "$tmp/.agents/skills/user-authored/notes.txt" ]
    rm -rf "$tmp"
}

@test "codex-skills: generate() accepts enable_codex_skills kwarg" {
    tmp="$(mktemp -d)"
    python3 - <<PY >/dev/null 2>&1
import sys
from pathlib import Path
sys.path.insert(0, "$TOOLKIT_DIR/scripts")
from generate_codex_skills import generate
generate(Path("$tmp"), enable_codex_skills=True)
PY
    [ -d "$tmp/.agents/skills" ]
    count=$(ls "$tmp/.agents/skills" | wc -l | xargs)
    [ "$count" -ge 50 ]
    rm -rf "$tmp"
}
