#!/usr/bin/env bats
# Native-surface generator contract tests (Bucket 2 of v3.0.0).
#
# Covers the four generators that emit editor-native subagents and custom
# slash commands for editors that host them natively:
#
#   scripts/generate_augment_agents.py    -> .augment/agents/ai-toolkit-*.md
#   scripts/generate_augment_commands.py  -> .augment/commands/ai-toolkit-*.md
#   scripts/generate_cursor_agents.py     -> .cursor/agents/ai-toolkit-*.md
#   scripts/generate_gemini_commands.py   -> .gemini/commands/ai-toolkit-*.toml
#
# Design contracts the tests enforce:
#   1. Every generated file carries the ai-toolkit-* prefix (clean uninstall).
#   2. User-authored files without our prefix are never touched.
#   3. Only user-invocable skills become commands — knowledge skills stay out.
#   4. Frontmatter matches each editor's documented schema:
#        - Augment agents:   name/description/model:inherit/color/tools/disabled_tools
#        - Augment commands: markdown body, no TOML, no template:
#        - Cursor agents:    name/description/tools list (model omitted)
#        - Gemini commands:  TOML with description= and prompt=\"\"\"
#   5. Regeneration removes stale ai-toolkit-* files whose source vanished
#      without creating duplicates.
#   6. $ARGUMENTS is rewritten to {{args}} in Gemini TOML bodies.
#
# Run with: bats tests/test_native_surfaces.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export NS_DIR; NS_DIR="$(mktemp -d)"
    export NS_LOG; NS_LOG="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_augment_agents.py"   "$NS_DIR" > "$NS_LOG/aug-agents.log"   2>&1
    echo $? > "$NS_LOG/aug-agents.status"
    python3 "$TOOLKIT_DIR/scripts/generate_augment_commands.py" "$NS_DIR" > "$NS_LOG/aug-commands.log" 2>&1
    echo $? > "$NS_LOG/aug-commands.status"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_agents.py"    "$NS_DIR" > "$NS_LOG/cur-agents.log"   2>&1
    echo $? > "$NS_LOG/cur-agents.status"
    python3 "$TOOLKIT_DIR/scripts/generate_gemini_commands.py"  "$NS_DIR" > "$NS_LOG/gem-commands.log" 2>&1
    echo $? > "$NS_LOG/gem-commands.status"
}

teardown_file() {
    rm -rf "$NS_DIR" "$NS_LOG"
}

# ── Augment agents ──────────────────────────────────────────────────────────

@test "augment_agents: generator exits 0" {
    [ "$(cat "$NS_LOG/aug-agents.status")" = "0" ]
}

@test "augment_agents: mirrors every agent in app/agents/ (ai-toolkit- prefix)" {
    src_count=$(ls "$TOOLKIT_DIR"/app/agents/*.md | wc -l | xargs)
    out_count=$(ls "$NS_DIR"/.augment/agents/ai-toolkit-*.md | wc -l | xargs)
    [ "$src_count" -eq "$out_count" ]
    [ "$out_count" -ge 40 ]
}

@test "augment_agents: every file carries ai-toolkit- prefix" {
    bad=$(ls "$NS_DIR"/.augment/agents/ 2>/dev/null | grep -v '^ai-toolkit-' | wc -l | xargs)
    [ "$bad" = "0" ]
}

@test "augment_agents: frontmatter emits model: inherit (no short alias leak)" {
    # Short aliases (opus/sonnet/haiku) must not appear as model values —
    # planning doc rule 5: Augment uses model: inherit.
    for f in "$NS_DIR"/.augment/agents/ai-toolkit-*.md; do
        grep -q '^model: inherit$' "$f" || { echo "missing model: inherit in $f"; return 1; }
        ! grep -qE '^model: (opus|sonnet|haiku)$' "$f"
    done
}

@test "augment_agents: frontmatter has name, description, tools, disabled_tools" {
    for f in "$NS_DIR"/.augment/agents/ai-toolkit-*.md; do
        grep -q '^name: '            "$f" || { echo "no name in $f"; return 1; }
        grep -q '^description: "'    "$f" || { echo "no description in $f"; return 1; }
        grep -q '^tools: \['         "$f" || { echo "no tools list in $f"; return 1; }
        grep -q '^disabled_tools: \[\]$' "$f" || { echo "no disabled_tools in $f"; return 1; }
    done
}

@test "augment_agents: ai-engineer body includes expertise heading" {
    f="$NS_DIR/.augment/agents/ai-toolkit-ai-engineer.md"
    [ -f "$f" ]
    grep -q '## Expertise' "$f"
}

@test "augment_agents: regeneration cleans stale ai-toolkit-* files" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.augment/agents"
    # Pre-seed stale file (source doesn't exist) and a user file (no prefix).
    echo "stale" > "$tmp/.augment/agents/ai-toolkit-nonexistent-agent.md"
    echo "mine"  > "$tmp/.augment/agents/user-custom.md"
    python3 "$TOOLKIT_DIR/scripts/generate_augment_agents.py" "$tmp" >/dev/null
    [ ! -f "$tmp/.augment/agents/ai-toolkit-nonexistent-agent.md" ]
    [ -f   "$tmp/.augment/agents/user-custom.md" ]
    rm -rf "$tmp"
}

@test "augment_agents: global layout via config_root writes under agents/ directly" {
    tmp="$(mktemp -d)"
    home="$tmp/.augment-home"
    python3 - "$TOOLKIT_DIR" "$tmp" "$home" <<'PYEOF'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_augment_agents import generate
generate(Path(sys.argv[2]), config_root=Path(sys.argv[3]))
PYEOF
    [ -d "$home/agents" ]
    count=$(ls "$home/agents"/ai-toolkit-*.md | wc -l | xargs)
    [ "$count" -ge 40 ]
    [ ! -d "$home/.augment" ]
    rm -rf "$tmp"
}

# ── Augment commands ────────────────────────────────────────────────────────

@test "augment_commands: generator exits 0" {
    [ "$(cat "$NS_LOG/aug-commands.status")" = "0" ]
}

@test "augment_commands: emits user-invocable skills only" {
    # debug is user-invocable -> should exist
    [ -f "$NS_DIR/.augment/commands/ai-toolkit-debug.md" ]
    # rag-patterns is a knowledge skill (user-invocable: false) -> must NOT exist
    [ ! -f "$NS_DIR/.augment/commands/ai-toolkit-rag-patterns.md" ]
}

@test "augment_commands: every file carries ai-toolkit- prefix" {
    bad=$(ls "$NS_DIR"/.augment/commands/ 2>/dev/null | grep -v '^ai-toolkit-' | wc -l | xargs)
    [ "$bad" = "0" ]
}

@test "augment_commands: body is markdown (not TOML, not opencode template:)" {
    for f in "$NS_DIR"/.augment/commands/ai-toolkit-*.md; do
        # No leaked TOML-style keys at column 0
        ! grep -qE '^prompt = "' "$f"
        # No leaked opencode `template: |` block
        ! grep -q '^template: |' "$f"
    done
}

@test "augment_commands: frontmatter contains description" {
    for f in "$NS_DIR"/.augment/commands/ai-toolkit-*.md; do
        grep -q '^description: "' "$f" || { echo "missing description in $f"; return 1; }
    done
}

@test "augment_commands: agent field is prefixed when present" {
    # debug's source skill references agent: debugger -> must be rewritten
    f="$NS_DIR/.augment/commands/ai-toolkit-debug.md"
    grep -q '^agent: ai-toolkit-debugger$' "$f"
}

@test "augment_commands: regeneration cleans stale and skills-gone-private" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.augment/commands"
    echo "stale" > "$tmp/.augment/commands/ai-toolkit-nope-skill.md"
    echo "mine"  > "$tmp/.augment/commands/user-cmd.md"
    python3 "$TOOLKIT_DIR/scripts/generate_augment_commands.py" "$tmp" >/dev/null
    [ ! -f "$tmp/.augment/commands/ai-toolkit-nope-skill.md" ]
    [ -f   "$tmp/.augment/commands/user-cmd.md" ]
    rm -rf "$tmp"
}

# ── Cursor agents ───────────────────────────────────────────────────────────

@test "cursor_agents: generator exits 0" {
    [ "$(cat "$NS_LOG/cur-agents.status")" = "0" ]
}

@test "cursor_agents: mirrors every agent with ai-toolkit- prefix" {
    src_count=$(ls "$TOOLKIT_DIR"/app/agents/*.md | wc -l | xargs)
    out_count=$(ls "$NS_DIR"/.cursor/agents/ai-toolkit-*.md | wc -l | xargs)
    [ "$src_count" -eq "$out_count" ]
}

@test "cursor_agents: every file carries ai-toolkit- prefix" {
    bad=$(ls "$NS_DIR"/.cursor/agents/ 2>/dev/null | grep -v '^ai-toolkit-' | wc -l | xargs)
    [ "$bad" = "0" ]
}

@test "cursor_agents: frontmatter omits short-alias model (Cursor expects provider-qualified ids)" {
    # Regression guard: our earlier generators leaked bare opus/sonnet/haiku.
    ! grep -qrE '^model: (opus|sonnet|haiku)$' "$NS_DIR/.cursor/agents/"
}

@test "cursor_agents: frontmatter has name, description, tools list" {
    for f in "$NS_DIR"/.cursor/agents/ai-toolkit-*.md; do
        grep -q '^name: '         "$f" || { echo "no name in $f";        return 1; }
        grep -q '^description: "' "$f" || { echo "no description in $f"; return 1; }
        grep -q '^tools: \['      "$f" || { echo "no tools list in $f";  return 1; }
    done
}

@test "cursor_agents: body carries the ai-engineer persona content" {
    f="$NS_DIR/.cursor/agents/ai-toolkit-ai-engineer.md"
    [ -f "$f" ]
    grep -q '# AI Engineer' "$f"
}

@test "cursor_agents: regeneration removes stale but preserves user-authored" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.cursor/agents"
    echo "stale" > "$tmp/.cursor/agents/ai-toolkit-gone-agent.md"
    echo "mine"  > "$tmp/.cursor/agents/my-agent.md"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_agents.py" "$tmp" >/dev/null
    [ ! -f "$tmp/.cursor/agents/ai-toolkit-gone-agent.md" ]
    [ -f   "$tmp/.cursor/agents/my-agent.md" ]
    rm -rf "$tmp"
}

@test "cursor_agents: global layout via config_root writes under agents/ directly" {
    tmp="$(mktemp -d)"
    home="$tmp/.cursor-home"
    python3 - "$TOOLKIT_DIR" "$tmp" "$home" <<'PYEOF'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_cursor_agents import generate
generate(Path(sys.argv[2]), config_root=Path(sys.argv[3]))
PYEOF
    [ -d "$home/agents" ]
    [ ! -d "$home/.cursor" ]
    count=$(ls "$home/agents"/ai-toolkit-*.md | wc -l | xargs)
    [ "$count" -ge 40 ]
    rm -rf "$tmp"
}

# ── Gemini commands ─────────────────────────────────────────────────────────

@test "gemini_commands: generator exits 0" {
    [ "$(cat "$NS_LOG/gem-commands.status")" = "0" ]
}

@test "gemini_commands: emits user-invocable skills only" {
    [ -f "$NS_DIR/.gemini/commands/ai-toolkit-debug.toml" ]
    [ ! -f "$NS_DIR/.gemini/commands/ai-toolkit-rag-patterns.toml" ]
}

@test "gemini_commands: every file is .toml with ai-toolkit- prefix" {
    bad=$(ls "$NS_DIR"/.gemini/commands/ 2>/dev/null | grep -v '^ai-toolkit-.*\.toml$' | wc -l | xargs)
    [ "$bad" = "0" ]
}

@test "gemini_commands: each file is syntactically valid TOML with description + prompt" {
    # tomllib is stdlib from Python 3.11+. ai-toolkit targets >=3.11 already.
    run python3 - "$NS_DIR" <<'PYEOF'
import sys, tomllib
from pathlib import Path
root = Path(sys.argv[1]) / ".gemini" / "commands"
errs = []
for f in sorted(root.glob("ai-toolkit-*.toml")):
    try:
        with open(f, "rb") as fh:
            data = tomllib.load(fh)
    except Exception as e:
        errs.append(f"{f}: parse error: {e}")
        continue
    if "description" not in data:
        errs.append(f"{f}: missing description")
    if "prompt" not in data:
        errs.append(f"{f}: missing prompt")
if errs:
    print("\n".join(errs))
    sys.exit(1)
print("ok")
PYEOF
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "gemini_commands: bodies translate \$ARGUMENTS into {{args}}" {
    # debug source contains $ARGUMENTS — the Gemini output must not.
    f="$NS_DIR/.gemini/commands/ai-toolkit-debug.toml"
    ! grep -q '\$ARGUMENTS' "$f"
    grep -q '{{args}}' "$f"
}

@test "gemini_commands: regeneration removes stale and user files survive" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.gemini/commands"
    echo 'description="x"
prompt="""y"""' > "$tmp/.gemini/commands/ai-toolkit-ghost.toml"
    echo 'description="user"
prompt="""user"""' > "$tmp/.gemini/commands/user-cmd.toml"
    python3 "$TOOLKIT_DIR/scripts/generate_gemini_commands.py" "$tmp" >/dev/null
    [ ! -f "$tmp/.gemini/commands/ai-toolkit-ghost.toml" ]
    [ -f   "$tmp/.gemini/commands/user-cmd.toml" ]
    rm -rf "$tmp"
}

@test "gemini_commands: global layout via config_root writes under commands/ directly" {
    tmp="$(mktemp -d)"
    home="$tmp/.gemini-home"
    python3 - "$TOOLKIT_DIR" "$tmp" "$home" <<'PYEOF'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_gemini_commands import generate
generate(Path(sys.argv[2]), config_root=Path(sys.argv[3]))
PYEOF
    [ -d "$home/commands" ]
    [ ! -d "$home/.gemini" ]
    count=$(ls "$home/commands"/ai-toolkit-*.toml | wc -l | xargs)
    [ "$count" -ge 30 ]
    rm -rf "$tmp"
}

# ── Cross-generator parity ──────────────────────────────────────────────────

@test "parity: augment & gemini command counts match (both filter user-invocable)" {
    aug=$(ls "$NS_DIR"/.augment/commands/ai-toolkit-*.md | wc -l | xargs)
    gem=$(ls "$NS_DIR"/.gemini/commands/ai-toolkit-*.toml | wc -l | xargs)
    [ "$aug" = "$gem" ]
}

@test "parity: augment & cursor agent counts match (both mirror all agents)" {
    aug=$(ls "$NS_DIR"/.augment/agents/ai-toolkit-*.md | wc -l | xargs)
    cur=$(ls "$NS_DIR"/.cursor/agents/ai-toolkit-*.md | wc -l | xargs)
    [ "$aug" = "$cur" ]
}

@test "parity: generators are idempotent (second run yields identical file set)" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_augment_agents.py"   "$tmp" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_augment_commands.py" "$tmp" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_agents.py"    "$tmp" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_gemini_commands.py"  "$tmp" >/dev/null
    first=$(cd "$tmp" && find .augment .cursor .gemini -type f | sort | md5sum 2>/dev/null || \
            (cd "$tmp" && find .augment .cursor .gemini -type f | sort | shasum -a 1))
    python3 "$TOOLKIT_DIR/scripts/generate_augment_agents.py"   "$tmp" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_augment_commands.py" "$tmp" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_agents.py"    "$tmp" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_gemini_commands.py"  "$tmp" >/dev/null
    second=$(cd "$tmp" && find .augment .cursor .gemini -type f | sort | md5sum 2>/dev/null || \
             (cd "$tmp" && find .augment .cursor .gemini -type f | sort | shasum -a 1))
    [ "$first" = "$second" ]
    rm -rf "$tmp"
}
