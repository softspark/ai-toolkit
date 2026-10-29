#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
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
                        "command": "\"$HOME/.softspark/ai-toolkit/hooks/save-session.sh\""
                    }
                ]
            },
            {
                "_source": "ai-toolkit",
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"$HOME/.softspark/ai-toolkit/hooks/save-session.sh\""
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
save_session = [
    entry for entry in stop
    if entry["hooks"][0]["command"] == '"$HOME/.softspark/ai-toolkit/hooks/save-session.sh"'
]
custom = [
    entry for entry in stop
    if entry["hooks"][0]["command"] == "bash ~/my-custom-stop.sh"
]
assert len(save_session) == 1, save_session
assert save_session[0].get("_source") == "ai-toolkit", save_session
assert len(custom) == 1, custom
PY
}

# Releases up to 5.4.2 wired quality-check.sh to Claude Code's Stop next to
# quality-gate.sh, which runs the same checker, so every turn type-checked twice.
@test "merge-hooks: drops the retired Stop quality-check, tagged or untagged, keeps user hooks" {
    cat > "$TARGET" <<'EOF'
{
    "hooks": {
        "Stop": [
            {
                "_source": "ai-toolkit",
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"$HOME/.softspark/ai-toolkit/hooks/quality-check.sh\"",
                        "async": true
                    }
                ]
            },
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"$HOME/.softspark/ai-toolkit/hooks/quality-check.sh\"",
                        "async": true
                    }
                ]
            },
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"$HOME/.softspark/ai-toolkit/hooks/quality-check.sh\" --blocking"
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

commands = [
    handler["command"]
    for entry in data["hooks"]["Stop"]
    for handler in entry["hooks"]
]
assert '"$HOME/.softspark/ai-toolkit/hooks/quality-check.sh"' not in commands, commands
assert commands.count('"$HOME/.softspark/ai-toolkit/hooks/quality-check.sh" --blocking') == 1, commands
assert commands.count('"$HOME/.softspark/ai-toolkit/hooks/quality-gate.sh"') == 1, commands
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
assert commands.count('"$HOME/.softspark/ai-toolkit/hooks/notify-waiting.sh"') == 1, commands
assert all("display notification" not in command for command in commands), commands
assert "bash ~/my-notify.sh" in commands, commands
PY
}

@test "merge-hooks: upgrades legacy 'bash ~' notify-waiting to '\$HOME' form" {
    cat > "$TARGET" <<'EOF'
{
    "hooks": {
        "Notification": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "bash ~/.softspark/ai-toolkit/hooks/notify-waiting.sh"
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
# Legacy 'bash ~/' toolkit form removed
assert commands.count("bash ~/.softspark/ai-toolkit/hooks/notify-waiting.sh") == 0, commands
# New '"$HOME/..."' toolkit form present exactly once
assert commands.count('"$HOME/.softspark/ai-toolkit/hooks/notify-waiting.sh"') == 1, commands
# User-custom hook with similar 'bash ~/' prefix survives
assert "bash ~/my-notify.sh" in commands, commands
# Toolkit-injected entry is tagged
toolkit_entries = [
    e for e in notifications
    if e["hooks"][0]["command"] == '"$HOME/.softspark/ai-toolkit/hooks/notify-waiting.sh"'
]
assert toolkit_entries[0].get("_source") == "ai-toolkit", toolkit_entries
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

@test "merge-hooks: replaces exact legacy idle reminders but preserves user variants" {
    run python3 - "$TOOLKIT_DIR" "$TARGET" <<'PY'
import copy
import json
from pathlib import Path
import subprocess
import sys

root, target = Path(sys.argv[1]), Path(sys.argv[2])
short = "echo 'Teammate going idle. Verify: (1) All assigned files modified, (2) Tests written for changes, (3) Documentation updated if needed.'"
long = short[:-1] + " Coordinator: once you have the last message you need from this agent (final report, any truncated tail), stop it (TaskStop) unless more work will be sent to it (constitution Article V.3).'"

def entry(command, **extra):
    return {"matcher": "", "hooks": [{"type": "command", "command": command}], **extra}

custom = [entry("echo 'my idle reminder'"), entry(short + "; echo user-tail"),
          entry(short, matcher="custom-agent")]
mixed = entry(short)
mixed["hooks"].append({"type": "command", "command": "echo user-handler"})
custom.append(mixed)
target.write_text(json.dumps({"theme": "user-theme", "hooks": {
    "TeammateIdle": [entry(short), entry(long), *copy.deepcopy(custom)],
    "Stop": [entry(short)],
}}))
command = [sys.executable, str(root / "scripts/merge-hooks.py")]
for _ in range(2):
    subprocess.run([*command, "inject", str(root / "app/hooks.json"), str(target)], check=True)
    data = json.loads(target.read_text())
    current = json.loads((root / "app/hooks.json").read_text())["hooks"]["TeammateIdle"]
    assert data["hooks"]["TeammateIdle"] == [*custom, *current]
    assert entry(short) in data["hooks"]["Stop"]
    assert data["theme"] == "user-theme"
subprocess.run([*command, "strip", str(target)], check=True)
data = json.loads(target.read_text())
assert data["hooks"]["TeammateIdle"] == custom
assert data["hooks"]["Stop"] == [entry(short)]
PY
    [ "$status" -eq 0 ]
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

@test "merge-hooks: strip removes untagged toolkit statusLine and handlers, keeps chained user handler" {
    # Claude Code drops "_source" when it rewrites settings.json.
    cat > "$TARGET" <<'EOF'
{"statusLine":{"type":"command","command":"bash \"$HOME/.softspark/ai-toolkit/hooks/ai-toolkit-statusline.sh\""},
 "hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[
   {"type":"command","command":"bash \"$HOME/.softspark/ai-toolkit/hooks/guard-destructive.sh\""},
   {"type":"command","command":"echo mine"}]}],
  "Stop":[{"matcher":"","hooks":[{"type":"command","command":"bash ~/.softspark/ai-toolkit/hooks/save-session.sh"}]}]}}
EOF
    run $MERGE strip "$TARGET"
    [ "$status" -eq 0 ]
    run python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1])), sort_keys=True))' "$TARGET"
    [ "$output" = '{"hooks": {"PreToolUse": [{"hooks": [{"command": "echo mine", "type": "command"}], "matcher": "Bash"}]}}' ]
}

@test "merge-hooks: strip on missing statusLine is a no-op" {
    echo '{"hooks":{}}' > "$TARGET"
    run $MERGE strip "$TARGET"
    [ "$status" -eq 0 ]
}
