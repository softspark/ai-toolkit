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

@test "merge-hooks: removes legacy untagged toolkit hook duplicates" {
    cat > "$TARGET" <<'EOF'
{
    "hooks": {
        "Stop": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"$HOME/.softspark/ai-toolkit/hooks/quality-check.sh\""
                    }
                ]
            },
            {
                "_source": "ai-toolkit",
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"$HOME/.softspark/ai-toolkit/hooks/quality-check.sh\""
                    }
                ]
            },
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "bash ~/my-custom-stop.sh"
                    }
                ]
            }
        ]
    }
}
EOF
    run $MERGE inject "$TOOLKIT_HOOKS" "$TARGET"
    [ "$status" -eq 0 ]
    python3 - "$TARGET" <<'PY'
import json
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)

stop = data["hooks"]["Stop"]
quality_check = [
    entry for entry in stop
    if entry["hooks"][0]["command"] == '"$HOME/.softspark/ai-toolkit/hooks/quality-check.sh"'
]
custom = [
    entry for entry in stop
    if entry["hooks"][0]["command"] == "bash ~/my-custom-stop.sh"
]
assert len(quality_check) == 1, quality_check
assert quality_check[0].get("_source") == "ai-toolkit", quality_check
assert len(custom) == 1, custom
PY
}

@test "merge-hooks: removes legacy untagged notification command duplicates" {
    cat > "$TARGET" <<'EOF'
{
    "hooks": {
        "Notification": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "osascript -e 'display notification \"Claude Code needs your attention\" with title \"Claude Code\"'"
                    }
                ]
            },
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "osascript -e 'display notification \"Claude Code needs your attention\" with title \"Claude Code\"'"
                    }
                ]
            },
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "bash ~/my-notify.sh"
                    }
                ]
            }
        ]
    }
}
EOF
    run $MERGE inject "$TOOLKIT_HOOKS" "$TARGET"
    [ "$status" -eq 0 ]
    python3 - "$TARGET" <<'PY'
import json
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)

notifications = data["hooks"]["Notification"]
commands = [entry["hooks"][0]["command"] for entry in notifications]
assert commands.count("bash ~/.softspark/ai-toolkit/hooks/notify-waiting.sh") == 1, commands
assert all("display notification" not in command for command in commands), commands
assert "bash ~/my-notify.sh" in commands, commands
PY
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
