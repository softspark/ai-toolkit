#!/usr/bin/env bats
# Tests for Bucket 3 — native skill surfaces across Gemini, Augment, Codex.
#
# Covers:
#   - scripts/generate_gemini_skills.py  (pointer pattern)
#   - scripts/generate_augment_skills.py (pointer pattern)
#   - scripts/generate_codex_skills.py   (.agents/skills mirror, opt-in)

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
POINTER_SKILL="ai-toolkit-skill-catalogue"
ADAPTED_MARKER=".ai-toolkit-codex-adapted"

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

@test "codex-skills: adapted wrappers use native schema and semantic guidance" {
    run python3 - "$B3_CODEX_ON/.agents/skills" <<'PY'
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
for marker in root.glob("*/.ai-toolkit-codex-adapted"):
    skill_file = marker.parent / "SKILL.md"
    text = skill_file.read_text(encoding="utf-8")
    frontmatter, body = text.split("---", 2)[1:]
    keys = {
        line.split(":", 1)[0]
        for line in frontmatter.splitlines()
        if ":" in line
    }
    assert keys == {"name", "description"}, (skill_file, keys)
    forbidden = (
        "fork_context", "agent_type=", "send_input", "close_agent",
        "spawn_agent", "wait_agent", "update_plan", "Agent(",
        "TeamCreate", "TeamDelete", "SendMessage", "$ARGUMENTS",
        "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS",
    )
    assert not any(token in body for token in forbidden), skill_file
    assert not re.search(r"\bTask(?:Create|List|Update|Get|Output|Stop)\b", body), skill_file

orchestrate = (root / "orchestrate" / "SKILL.md").read_text(encoding="utf-8")
assert "Codex-native subagents" in orchestrate
assert "planning mechanism available in the current client" in orchestrate
assert "subagent controls available in the current client" in orchestrate
PY
    [ "$status" -eq 0 ]
}

@test "codex-skills: preserves user path and logical-name collisions" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$tmp" --enable >/dev/null
    mkdir -p "$tmp/.agents/skills/custom-orchestrate"
    rm "$tmp/.agents/skills/clean-code"
    mkdir -p "$tmp/.agents/skills/clean-code"
    cat > "$tmp/.agents/skills/custom-orchestrate/SKILL.md" <<'MD'
---
name: orchestrate
description: User-owned orchestrate workflow.
---
Keep this skill unchanged.
MD
    printf '%s\n' 'keep user clean-code directory' > "$tmp/.agents/skills/clean-code/notes.txt"
    run python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$tmp" --enable
    [ "$status" -eq 0 ]
    [ ! -e "$tmp/.agents/skills/orchestrate" ]
    [ ! -L "$tmp/.agents/skills/clean-code" ]
    grep -q 'Keep this skill unchanged' "$tmp/.agents/skills/custom-orchestrate/SKILL.md"
    grep -q 'keep user clean-code directory' "$tmp/.agents/skills/clean-code/notes.txt"
    rm -rf "$tmp"
}

@test "codex-skills: rejects symlinked output roots without external writes" {
    agents_target="$(mktemp -d)"
    agents_external="$(mktemp -d)"
    printf '%s\n' 'agents sentinel' > "$agents_external/sentinel.txt"
    shasum "$agents_external/sentinel.txt" > "$agents_external.before"
    ln -s "$agents_external" "$agents_target/.agents"

    run python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$agents_target" --enable
    [ "$status" -ne 0 ]
    shasum "$agents_external/sentinel.txt" > "$agents_external.after"
    cmp "$agents_external.before" "$agents_external.after"
    [ ! -e "$agents_external/skills" ]

    skills_target="$(mktemp -d)"
    skills_external="$(mktemp -d)"
    mkdir -p "$skills_target/.agents"
    printf '%s\n' 'skills sentinel' > "$skills_external/sentinel.txt"
    shasum "$skills_external/sentinel.txt" > "$skills_external.before"
    ln -s "$skills_external" "$skills_target/.agents/skills"

    run python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$skills_target" --enable
    [ "$status" -ne 0 ]
    shasum "$skills_external/sentinel.txt" > "$skills_external.after"
    cmp "$skills_external.before" "$skills_external.after"
    [ "$(find "$skills_external" -type f | wc -l | xargs)" -eq 1 ]
    rm -rf "$agents_target" "$agents_external" "$skills_target" "$skills_external"
}

@test "codex-skills: preserves user and dangling destination symlinks" {
    tmp="$(mktemp -d)"
    external="$(mktemp -d)"
    mkdir -p "$tmp/.agents/skills"
    printf '%s\n' 'external sentinel' > "$external/sentinel.txt"
    shasum "$external/sentinel.txt" > "$external.before"
    ln -s "$external" "$tmp/.agents/skills/orchestrate"
    ln -s "$external/missing-skill" "$tmp/.agents/skills/dangling-user"

    run python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$tmp" --enable
    [ "$status" -eq 0 ]
    [ -L "$tmp/.agents/skills/orchestrate" ]
    [ "$(readlink "$tmp/.agents/skills/orchestrate")" = "$external" ]
    [ -L "$tmp/.agents/skills/dangling-user" ]
    [ ! -e "$external/missing-skill" ]
    shasum "$external/sentinel.txt" > "$external.after"
    cmp "$external.before" "$external.after"
    rm -rf "$tmp" "$external"
}

@test "codex-skills: preserves auxiliary collisions and exposes support assets" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$tmp" --enable >/dev/null
    tdd="$tmp/.agents/skills/tdd"
    [ -L "$tdd/reference" ]
    rm "$tdd/reference"
    mkdir "$tdd/reference"
    printf '%s\n' 'user auxiliary' > "$tdd/reference/notes.txt"

    run python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$tmp" --enable
    [ "$status" -eq 0 ]
    [ -f "$tdd/reference/notes.txt" ]
    [ ! -L "$tdd/reference" ]

    run python3 - "$TOOLKIT_DIR/app/skills" "$tmp/.agents/skills" <<'PY'
import sys
from pathlib import Path

source_root = Path(sys.argv[1])
output_root = Path(sys.argv[2])
for marker in output_root.glob("*/.ai-toolkit-codex-adapted"):
    source = source_root / marker.parent.name
    for child in source.iterdir():
        if child.name == "SKILL.md":
            continue
        destination = marker.parent / child.name
        if destination.exists() or destination.is_symlink():
            continue
        raise AssertionError(f"missing auxiliary: {destination}")
PY
    [ "$status" -eq 0 ]
    rm -rf "$tmp"
}

@test "codex-skills: adapted writes are atomic and clean failed staging" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" "$tmp" --enable >/dev/null

    run python3 - "$TOOLKIT_DIR" "$tmp" <<'PY'
import importlib.util
import os
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
spec = importlib.util.spec_from_file_location(
    "codex_skill_adapter", toolkit / "scripts" / "codex_skill_adapter.py"
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

source = toolkit / "app" / "skills" / "orchestrate"
skills_dst = target / ".agents" / "skills"
skill_file = skills_dst / "orchestrate" / "SKILL.md"
before = skill_file.read_bytes()
real_fsync = os.fsync

def fail_fsync(fd):
    real_fsync(fd)
    raise OSError("injected adapted staging failure")

try:
    with mock.patch("os.fsync", side_effect=fail_fsync):
        module.sync_codex_skill(source, skills_dst)
except OSError as error:
    assert "injected adapted staging failure" in str(error)
else:
    raise AssertionError("expected injected adapted staging failure")

assert skill_file.read_bytes() == before
assert not list((skills_dst / "orchestrate").glob(".*.tmp"))
PY
    [ "$status" -eq 0 ]
    rm -rf "$tmp"
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
