#!/usr/bin/env bats
# Tests for scripts/merge-hooks.py — statusLine handling.
#
# Confirms ai-toolkit's statusLine is installed by default but never
# overwrites a user-customized statusLine.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
MERGE="python3 $TOOLKIT_DIR/scripts/merge-hooks.py"
TOOLKIT_HOOKS="$TOOLKIT_DIR/app/hooks.json"

setup() {
    TEST_TMP="$(mktemp -d)"
    TARGET="$TEST_TMP/settings.json"
}

teardown() {
    rm -rf "$TEST_TMP"
}

read_field() {
    python3 -c "
import json, sys
with open('$TARGET') as f:
    d = json.load(f)
keys = '$1'.split('.')
for k in keys:
    if isinstance(d, dict):
        d = d.get(k)
    else:
        d = None
        break
print(d if d is not None else '')
"
}

# ── Inject ──────────────────────────────────────────────────────────────────

@test "merge-hooks: injects statusLine into empty target" {
    echo '{}' > "$TARGET"
    run $MERGE inject "$TOOLKIT_HOOKS" "$TARGET"
    [ "$status" -eq 0 ]
    src=$(read_field "statusLine._source")
    [ "$src" = "ai-toolkit" ]
    cmd=$(read_field "statusLine.command")
    echo "$cmd" | grep -q "ai-toolkit-statusline.sh"
}

@test "merge-hooks: injects statusLine into target with no statusLine key" {
    echo '{"otherKey":"value"}' > "$TARGET"
    run $MERGE inject "$TOOLKIT_HOOKS" "$TARGET"
    [ "$status" -eq 0 ]
    other=$(read_field "otherKey")
    [ "$other" = "value" ]
    src=$(read_field "statusLine._source")
    [ "$src" = "ai-toolkit" ]
}

@test "merge-hooks: replaces stale toolkit-installed statusLine" {
    cat > "$TARGET" <<'EOF'
{"statusLine":{"_source":"ai-toolkit","type":"command","command":"bash old-toolkit.sh"}}
EOF
    run $MERGE inject "$TOOLKIT_HOOKS" "$TARGET"
    [ "$status" -eq 0 ]
    cmd=$(read_field "statusLine.command")
    echo "$cmd" | grep -q "ai-toolkit-statusline.sh"
    ! echo "$cmd" | grep -q "old-toolkit.sh"
}

@test "merge-hooks: PRESERVES user-customized statusLine (no _source tag)" {
    cat > "$TARGET" <<'EOF'
{"statusLine":{"type":"command","command":"bash ~/my-custom-line.sh"}}
EOF
    run $MERGE inject "$TOOLKIT_HOOKS" "$TARGET"
    [ "$status" -eq 0 ]
    cmd=$(read_field "statusLine.command")
    echo "$cmd" | grep -q "my-custom-line.sh"
    ! echo "$cmd" | grep -q "ai-toolkit-statusline.sh"
}

@test "merge-hooks: PRESERVES user-customized statusLine even with extra fields" {
    cat > "$TARGET" <<'EOF'
{"statusLine":{"type":"command","command":"bash custom.sh","customField":"x"}}
EOF
    run $MERGE inject "$TOOLKIT_HOOKS" "$TARGET"
    [ "$status" -eq 0 ]
    custom=$(read_field "statusLine.customField")
    [ "$custom" = "x" ]
}

# ── Strip ───────────────────────────────────────────────────────────────────

@test "merge-hooks: strip removes toolkit-installed statusLine" {
    cat > "$TARGET" <<'EOF'
{"keep":"yes","statusLine":{"_source":"ai-toolkit","type":"command","command":"bash old.sh"}}
EOF
    run $MERGE strip "$TARGET"
    [ "$status" -eq 0 ]
    sl=$(read_field "statusLine")
    [ -z "$sl" ]
    keep=$(read_field "keep")
    [ "$keep" = "yes" ]
}

@test "merge-hooks: strip preserves user-customized statusLine" {
    cat > "$TARGET" <<'EOF'
{"statusLine":{"type":"command","command":"my-line.sh"}}
EOF
    run $MERGE strip "$TARGET"
    [ "$status" -eq 0 ]
    cmd=$(read_field "statusLine.command")
    [ "$cmd" = "my-line.sh" ]
}

@test "merge-hooks: strip on missing statusLine is a no-op" {
    echo '{"hooks":{}}' > "$TARGET"
    run $MERGE strip "$TARGET"
    [ "$status" -eq 0 ]
}
