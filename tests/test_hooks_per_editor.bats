#!/usr/bin/env bats
# Per-editor hook generator contract tests (v3.0.0 Bucket A).
#
# Covers the four native-hooks generators shipped in v3.0.0:
#   scripts/generate_cursor_hooks.py    -> .cursor/hooks.json
#   scripts/generate_windsurf_hooks.py  -> .windsurf/hooks.json
#   scripts/generate_gemini_hooks.py    -> .gemini/settings.json (hooks block)
#   scripts/generate_augment_hooks.py   -> .augment/settings.json (hooks block)
#
# Contracts enforced:
#   1. Generators exit 0 on a clean target dir.
#   2. Output paths match the per-editor convention.
#   3. Idempotence: running the generator twice produces byte-identical output.
#   4. Source-tag marker (_source: ai-toolkit) is present on every managed entry
#      so that regeneration can rewrite only our block.
#   5. Prefix preservation: unrelated user keys / hook entries survive.
#   6. Shell command prefix is "$HOME/.softspark/ai-toolkit/hooks/" — not an
#      absolute /Users/... path (portability).
#
# Run with: bats tests/test_hooks_per_editor.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export HPE_DIR; HPE_DIR="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py"   "$HPE_DIR" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_windsurf_hooks.py" "$HPE_DIR" >/dev/null
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

@test "hooks: windsurf writes .windsurf/hooks.json" {
    [ -f "$HPE_DIR/.windsurf/hooks.json" ]
}

@test "hooks: gemini writes .gemini/settings.json" {
    [ -f "$HPE_DIR/.gemini/settings.json" ]
}

@test "hooks: augment writes .augment/settings.json" {
    [ -f "$HPE_DIR/.augment/settings.json" ]
}

# ── JSON validity ──────────────────────────────────────────────────────────

@test "hooks: cursor/hooks.json is valid JSON" {
    python3 -c "import json; json.load(open('$HPE_DIR/.cursor/hooks.json'))"
}

@test "hooks: windsurf/hooks.json is valid JSON" {
    python3 -c "import json; json.load(open('$HPE_DIR/.windsurf/hooks.json'))"
}

@test "hooks: gemini/settings.json is valid JSON" {
    python3 -c "import json; json.load(open('$HPE_DIR/.gemini/settings.json'))"
}

@test "hooks: augment/settings.json is valid JSON" {
    python3 -c "import json; json.load(open('$HPE_DIR/.augment/settings.json'))"
}

# ── Source tag presence ────────────────────────────────────────────────────

@test "hooks: cursor entries carry _source: ai-toolkit" {
    grep -q '"_source": "ai-toolkit"' "$HPE_DIR/.cursor/hooks.json"
}

@test "hooks: windsurf entries carry _source: ai-toolkit" {
    grep -q '"_source": "ai-toolkit"' "$HPE_DIR/.windsurf/hooks.json"
}

@test "hooks: gemini entries carry _source: ai-toolkit" {
    grep -q '"_source": "ai-toolkit"' "$HPE_DIR/.gemini/settings.json"
}

@test "hooks: augment entries carry _source: ai-toolkit" {
    grep -q '"_source": "ai-toolkit"' "$HPE_DIR/.augment/settings.json"
}

# ── HOME-relative shell paths ──────────────────────────────────────────────

@test "hooks: cursor commands use \$HOME prefix (not absolute /Users)" {
    ! grep -qE '"/Users/|"/home/' "$HPE_DIR/.cursor/hooks.json"
    grep -q '\$HOME/.softspark/ai-toolkit/hooks/' "$HPE_DIR/.cursor/hooks.json"
}

@test "hooks: windsurf commands use \$HOME prefix (not absolute /Users)" {
    ! grep -qE '"/Users/|"/home/' "$HPE_DIR/.windsurf/hooks.json"
    grep -q '\$HOME/.softspark/ai-toolkit/hooks/' "$HPE_DIR/.windsurf/hooks.json"
}

@test "hooks: gemini commands use \$HOME prefix (not absolute /Users)" {
    ! grep -qE '"/Users/|"/home/' "$HPE_DIR/.gemini/settings.json"
    grep -q '\$HOME/.softspark/ai-toolkit/hooks/' "$HPE_DIR/.gemini/settings.json"
}

@test "hooks: augment commands use \$HOME prefix (not absolute /Users)" {
    ! grep -qE '"/Users/|"/home/' "$HPE_DIR/.augment/settings.json"
    grep -q '\$HOME/.softspark/ai-toolkit/hooks/' "$HPE_DIR/.augment/settings.json"
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

@test "hooks: windsurf is idempotent (second run produces identical bytes)" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_windsurf_hooks.py" "$tmp" >/dev/null
    first_sha=$(shasum "$tmp/.windsurf/hooks.json" | awk '{print $1}')
    python3 "$TOOLKIT_DIR/scripts/generate_windsurf_hooks.py" "$tmp" >/dev/null
    second_sha=$(shasum "$tmp/.windsurf/hooks.json" | awk '{print $1}')
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
    grep -q '"_source": "ai-toolkit"' "$tmp/.cursor/hooks.json"
    rm -rf "$tmp"
}

@test "hooks: windsurf preserves user-authored entries" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.windsurf"
    cat > "$tmp/.windsurf/hooks.json" <<'EOF'
{
  "pre_read_code": [
    {"_source": "user", "command": "echo user-hook"}
  ]
}
EOF
    python3 "$TOOLKIT_DIR/scripts/generate_windsurf_hooks.py" "$tmp" >/dev/null
    grep -q '"_source": "user"' "$tmp/.windsurf/hooks.json"
    grep -q '"_source": "ai-toolkit"' "$tmp/.windsurf/hooks.json"
    rm -rf "$tmp"
}

# ── Regeneration rewrites only ai-toolkit entries ──────────────────────────

@test "hooks: cursor regeneration does not duplicate ai-toolkit entries" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    first=$(grep -c '"_source": "ai-toolkit"' "$tmp/.cursor/hooks.json" || echo 0)
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    second=$(grep -c '"_source": "ai-toolkit"' "$tmp/.cursor/hooks.json" || echo 0)
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

@test "hooks: windsurf wires pre_write_code" {
    grep -q '"pre_write_code"' "$HPE_DIR/.windsurf/hooks.json"
}

@test "hooks: gemini wires SessionStart (upstream PascalCase event name)" {
    grep -q '"SessionStart"' "$HPE_DIR/.gemini/settings.json"
}

@test "hooks: augment wires PreToolUse" {
    grep -q '"PreToolUse"' "$HPE_DIR/.augment/settings.json"
}
