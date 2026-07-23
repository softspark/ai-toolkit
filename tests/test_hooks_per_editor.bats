#!/usr/bin/env bats
# Per-editor hook generator contract tests (v3.0.0 Bucket A).
#
# Covers the native-hooks generators shipped by ai-toolkit:
#   scripts/generate_cursor_hooks.py    -> .cursor/hooks.json
#   scripts/generate_devin_hooks.py     -> .devin/hooks.v1.json (Devin CLI, Claude format)
#   scripts/generate_gemini_hooks.py    -> .gemini/settings.json (hooks block)
#   scripts/generate_augment_hooks.py   -> .augment/settings.json (hooks block)
#
# Contracts enforced:
#   1. Generators exit 0 on a clean target dir.
#   2. Output paths match the per-editor convention.
#   3. Idempotence: running the generator twice produces byte-identical output.
#   4. Each generator has an ownership marker so regeneration rewrites only its
#      managed block. Cursor uses its documented command field rather than an
#      unsupported custom entry key.
#   5. Prefix preservation: unrelated user keys / hook entries survive.
#   6. Commands use portable paths. Cursor project hooks use a repo-vendored
#      runtime for cloud-agent compatibility; other editors use the installed
#      "$HOME/.softspark/ai-toolkit/hooks/" runtime.
#
# Run with: bats tests/test_hooks_per_editor.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export HPE_DIR; HPE_DIR="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py"   "$HPE_DIR" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_devin_hooks.py"    "$HPE_DIR" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_gemini_hooks.py"   "$HPE_DIR" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_augment_hooks.py"  "$HPE_DIR" >/dev/null
}

teardown_file() {
    rm -rf "$HPE_DIR"
}

# ── Output paths ───────────────────────────────────────────────────────────

@test "hooks: cursor writes .cursor/hooks.json" {
    [ -f "$HPE_DIR/.cursor/hooks.json" ]
}

@test "hooks: devin writes .devin/hooks.v1.json" {
    [ -f "$HPE_DIR/.devin/hooks.v1.json" ]
}

@test "hooks: gemini writes .gemini/settings.json" {
    [ -f "$HPE_DIR/.gemini/settings.json" ]
}

@test "hooks: no editor surface exports the Claude-only output filter" {
    for surface in "$HPE_DIR/.gemini/settings.json" \
        "$HPE_DIR/.cursor/hooks.json" \
        "$HPE_DIR/.devin/hooks.v1.json" \
        "$HPE_DIR/.augment/settings.json"; do
        [ -f "$surface" ]
        ! grep -q "filter-tool-output" "$surface"
    done
}

@test "hooks: augment writes .augment/settings.json" {
    [ -f "$HPE_DIR/.augment/settings.json" ]
}

# ── JSON validity ──────────────────────────────────────────────────────────

@test "hooks: cursor/hooks.json is valid JSON" {
    python3 -c "import json; json.load(open('$HPE_DIR/.cursor/hooks.json'))"
}

@test "hooks: devin/hooks.v1.json is valid JSON" {
    python3 -c "import json; json.load(open('$HPE_DIR/.devin/hooks.v1.json'))"
}

@test "hooks: devin/hooks.v1.json has no top-level hooks wrapper (standalone format)" {
    python3 -c "
import json
data = json.load(open('$HPE_DIR/.devin/hooks.v1.json'))
assert 'hooks' not in data, 'standalone .devin/hooks.v1.json must NOT wrap under a hooks key'
assert 'PreToolUse' in data, 'events live at the top level'
"
}

@test "hooks: gemini/settings.json is valid JSON" {
    python3 -c "import json; json.load(open('$HPE_DIR/.gemini/settings.json'))"
}

@test "hooks: augment/settings.json is valid JSON" {
    python3 -c "import json; json.load(open('$HPE_DIR/.augment/settings.json'))"
}

# ── Source tag presence ────────────────────────────────────────────────────

@test "hooks: cursor entries carry the managed runtime command marker" {
    grep -q 'cursor_hook.py' "$HPE_DIR/.cursor/hooks.json"
    ! grep -q '"_source": "ai-toolkit"' "$HPE_DIR/.cursor/hooks.json"
}

@test "hooks: devin entries carry _source: ai-toolkit" {
    grep -q '"_source": "ai-toolkit"' "$HPE_DIR/.devin/hooks.v1.json"
}

@test "hooks: gemini entries carry _source: ai-toolkit" {
    grep -q '"_source": "ai-toolkit"' "$HPE_DIR/.gemini/settings.json"
}

@test "hooks: augment entries carry _source: ai-toolkit" {
    grep -q '"_source": "ai-toolkit"' "$HPE_DIR/.augment/settings.json"
}

# ── HOME-relative shell paths ──────────────────────────────────────────────

@test "hooks: cursor commands use the repo-vendored runtime (not host HOME)" {
    ! grep -qE '"/Users/|"/home/' "$HPE_DIR/.cursor/hooks.json"
    ! grep -q '\$HOME/.softspark/ai-toolkit/hooks/' "$HPE_DIR/.cursor/hooks.json"
    grep -q '\.cursor/hooks/ai-toolkit/cursor_hook.py' "$HPE_DIR/.cursor/hooks.json"
    [ -x "$HPE_DIR/.cursor/hooks/ai-toolkit/cursor_hook.py" ]
}

@test "hooks: devin commands use \$HOME prefix (not absolute /Users)" {
    ! grep -qE '"/Users/|"/home/' "$HPE_DIR/.devin/hooks.v1.json"
    grep -q '\$HOME/.softspark/ai-toolkit/hooks/' "$HPE_DIR/.devin/hooks.v1.json"
}

@test "hooks: devin runs plain (no AI_TOOLKIT_HOOK_FORMAT=json; Devin uses flat decision shape)" {
    ! grep -q 'AI_TOOLKIT_HOOK_FORMAT=json' "$HPE_DIR/.devin/hooks.v1.json"
}

@test "hooks: gemini commands use \$HOME prefix (not absolute /Users)" {
    ! grep -qE '"/Users/|"/home/' "$HPE_DIR/.gemini/settings.json"
    grep -q '\$HOME/.softspark/ai-toolkit/hooks/' "$HPE_DIR/.gemini/settings.json"
}

@test "hooks: gemini commands request JSON-safe hook output" {
    grep -q 'AI_TOOLKIT_HOOK_FORMAT=json' "$HPE_DIR/.gemini/settings.json"
}

@test "hooks: augment commands use \$HOME prefix (not absolute /Users)" {
    ! grep -qE '"/Users/|"/home/' "$HPE_DIR/.augment/settings.json"
    grep -q '\$HOME/.softspark/ai-toolkit/hooks/' "$HPE_DIR/.augment/settings.json"
}

@test "hooks: augment commands request JSON-safe hook output" {
    grep -q 'AI_TOOLKIT_HOOK_FORMAT=json' "$HPE_DIR/.augment/settings.json"
}

# ── Idempotence ────────────────────────────────────────────────────────────

@test "hooks: cursor is idempotent (second run produces identical bytes)" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    first_sha=$(shasum "$tmp/.cursor/hooks.json" | awk '{print $1}')
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    second_sha=$(shasum "$tmp/.cursor/hooks.json" | awk '{print $1}')
    rm -rf "$tmp"
    [ "$first_sha" = "$second_sha" ]
}

@test "hooks: devin is idempotent (second run produces identical bytes)" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_devin_hooks.py" "$tmp" >/dev/null
    first_sha=$(shasum "$tmp/.devin/hooks.v1.json" | awk '{print $1}')
    python3 "$TOOLKIT_DIR/scripts/generate_devin_hooks.py" "$tmp" >/dev/null
    second_sha=$(shasum "$tmp/.devin/hooks.v1.json" | awk '{print $1}')
    rm -rf "$tmp"
    [ "$first_sha" = "$second_sha" ]
}

@test "hooks: gemini is idempotent (second run produces identical bytes)" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_gemini_hooks.py" "$tmp" >/dev/null
    first_sha=$(shasum "$tmp/.gemini/settings.json" | awk '{print $1}')
    python3 "$TOOLKIT_DIR/scripts/generate_gemini_hooks.py" "$tmp" >/dev/null
    second_sha=$(shasum "$tmp/.gemini/settings.json" | awk '{print $1}')
    rm -rf "$tmp"
    [ "$first_sha" = "$second_sha" ]
}

@test "hooks: augment is idempotent (second run produces identical bytes)" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_augment_hooks.py" "$tmp" >/dev/null
    first_sha=$(shasum "$tmp/.augment/settings.json" | awk '{print $1}')
    python3 "$TOOLKIT_DIR/scripts/generate_augment_hooks.py" "$tmp" >/dev/null
    second_sha=$(shasum "$tmp/.augment/settings.json" | awk '{print $1}')
    rm -rf "$tmp"
    [ "$first_sha" = "$second_sha" ]
}

# ── User content preservation ──────────────────────────────────────────────

@test "hooks: gemini preserves user top-level keys outside hooks block" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.gemini"
    printf '{"theme":"dark","telemetry":false}\n' > "$tmp/.gemini/settings.json"
    python3 "$TOOLKIT_DIR/scripts/generate_gemini_hooks.py" "$tmp" >/dev/null
    python3 -c "
import json
data = json.load(open('$tmp/.gemini/settings.json'))
assert data.get('theme') == 'dark', f'lost theme: {data}'
assert data.get('telemetry') is False, f'lost telemetry: {data}'
assert 'hooks' in data, 'hooks block missing'
"
    rm -rf "$tmp"
}

@test "hooks: gemini leaves malformed settings untouched" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.gemini"
    printf '{"theme": invalid json\n' > "$tmp/.gemini/settings.json"
    before_sha=$(shasum "$tmp/.gemini/settings.json" | awk '{print $1}')

    run python3 "$TOOLKIT_DIR/scripts/generate_gemini_hooks.py" "$tmp"
    [ "$status" -ne 0 ]
    after_sha=$(shasum "$tmp/.gemini/settings.json" | awk '{print $1}')
    [ "$before_sha" = "$after_sha" ]
    rm -rf "$tmp"
}

@test "hooks: gemini atomic replace failure preserves existing settings" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.gemini"
    printf '{"theme":"dark"}\n' > "$tmp/.gemini/settings.json"

    run python3 - "$TOOLKIT_DIR" "$tmp" <<'PY'
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import generate_gemini_hooks

settings = target / ".gemini" / "settings.json"
original = settings.read_bytes()
with mock.patch("os.replace", side_effect=OSError("replace failed")):
    try:
        generate_gemini_hooks.generate(target)
    except OSError:
        pass
    else:
        raise AssertionError("generator did not use atomic replacement")

assert settings.read_bytes() == original
assert not list(settings.parent.glob(".settings.json.*"))
PY
    [ "$status" -eq 0 ]
    rm -rf "$tmp"
}

@test "hooks: gemini rejects a symlinked settings file" {
    tmp="$(mktemp -d)"
    external="$tmp/external-settings.json"
    mkdir -p "$tmp/.gemini"
    printf '{"theme":"dark"}\n' > "$external"
    ln -s "$external" "$tmp/.gemini/settings.json"

    run python3 "$TOOLKIT_DIR/scripts/generate_gemini_hooks.py" "$tmp"

    [ "$status" -ne 0 ]
    [ -L "$tmp/.gemini/settings.json" ]
    [ "$(cat "$external")" = '{"theme":"dark"}' ]
    rm -rf "$tmp"
}

@test "hooks: augment preserves user top-level keys outside hooks block" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.augment"
    printf '{"user_id":"alice","autoApprove":true}\n' > "$tmp/.augment/settings.json"
    python3 "$TOOLKIT_DIR/scripts/generate_augment_hooks.py" "$tmp" >/dev/null
    python3 -c "
import json
data = json.load(open('$tmp/.augment/settings.json'))
assert data.get('user_id') == 'alice', f'lost user_id: {data}'
assert data.get('autoApprove') is True, f'lost autoApprove: {data}'
assert 'hooks' in data, 'hooks block missing'
"
    rm -rf "$tmp"
}

@test "hooks: cursor preserves user-authored entries (non-ai-toolkit _source)" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.cursor"
    cat > "$tmp/.cursor/hooks.json" <<'EOF'
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      {"_source": "user", "command": "echo user-hook"}
    ]
  }
}
EOF
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    grep -q '"_source": "user"' "$tmp/.cursor/hooks.json"
    grep -q 'cursor_hook.py' "$tmp/.cursor/hooks.json"
    rm -rf "$tmp"
}

@test "hooks: devin preserves user-authored entries" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.devin"
    cat > "$tmp/.devin/hooks.v1.json" <<'EOF'
{
  "PreToolUse": [
    {"_source": "user", "matcher": "^exec$", "hooks": [{"type": "command", "command": "echo user-hook"}]}
  ]
}
EOF
    python3 "$TOOLKIT_DIR/scripts/generate_devin_hooks.py" "$tmp" >/dev/null
    grep -q '"_source": "user"' "$tmp/.devin/hooks.v1.json"
    grep -q '"_source": "ai-toolkit"' "$tmp/.devin/hooks.v1.json"
    rm -rf "$tmp"
}

# ── Regeneration rewrites only ai-toolkit entries ──────────────────────────

@test "hooks: cursor regeneration does not duplicate ai-toolkit entries" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    first=$(grep -c 'cursor_hook.py' "$tmp/.cursor/hooks.json" || echo 0)
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    second=$(grep -c 'cursor_hook.py' "$tmp/.cursor/hooks.json" || echo 0)
    rm -rf "$tmp"
    [ "$first" -eq "$second" ]
    [ "$first" -gt 0 ]
}

@test "hooks: gemini regeneration does not duplicate ai-toolkit entries" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_gemini_hooks.py" "$tmp" >/dev/null
    first=$(grep -c '"_source": "ai-toolkit"' "$tmp/.gemini/settings.json" || echo 0)
    python3 "$TOOLKIT_DIR/scripts/generate_gemini_hooks.py" "$tmp" >/dev/null
    second=$(grep -c '"_source": "ai-toolkit"' "$tmp/.gemini/settings.json" || echo 0)
    rm -rf "$tmp"
    [ "$first" -eq "$second" ]
    [ "$first" -gt 0 ]
}

# ── Event coverage sanity ──────────────────────────────────────────────────

@test "hooks: cursor wires sessionStart" {
    grep -q '"sessionStart"' "$HPE_DIR/.cursor/hooks.json"
}

@test "hooks: devin wires Claude-style PreToolUse with a Devin exec matcher" {
    python3 -c "
import json
data = json.load(open('$HPE_DIR/.devin/hooks.v1.json'))
assert 'PreToolUse' in data, 'missing PreToolUse'
matchers = {g.get('matcher') for g in data['PreToolUse']}
assert '^exec$' in matchers, f'expected ^exec\$ matcher (Devin tool name), got {matchers}'
# Devin tool names, not Claude's Bash/Edit:
assert not any('Bash' in (m or '') for m in matchers), 'must not use Claude Bash matcher'
"
}

@test "hooks: gemini wires SessionStart (upstream PascalCase event name)" {
    grep -q '"SessionStart"' "$HPE_DIR/.gemini/settings.json"
}

@test "hooks: augment wires PreToolUse" {
    grep -q '"PreToolUse"' "$HPE_DIR/.augment/settings.json"
}
