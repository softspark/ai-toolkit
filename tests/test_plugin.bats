#!/usr/bin/env bats
# Tests for plugin pack installation across Claude and global Codex targets.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CLI="node $TOOLKIT_DIR/bin/ai-toolkit.js"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "plugin install --editor codex bootstraps global Codex surface and installs memory-pack hooks" {
    run $CLI plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]

    [ -f "$TEST_TMP/AGENTS.md" ]
    [ -f "$TEST_TMP/.codex/hooks.json" ]
    [ -e "$TEST_TMP/.agents/skills/mem-search" ]
    [ -f "$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-memory-pack-observation-capture.sh" ]
    [ -f "$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-memory-pack-session-summary.sh" ]

    run python3 - <<PY
import json
from pathlib import Path

hooks = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
post = hooks["hooks"]["PostToolUse"]
stop = hooks["hooks"]["Stop"]

assert any(
    entry.get("_source") == "ai-toolkit-plugin-memory-pack"
    and entry.get("matcher") == "Bash"
    and entry["hooks"][0]["command"].endswith("plugin-memory-pack-observation-capture.sh\"")
    for entry in post
), post

assert any(
    entry.get("_source") == "ai-toolkit-plugin-memory-pack"
    and entry["hooks"][0]["command"].endswith("plugin-memory-pack-session-summary.sh\"")
    for entry in stop
), stop
PY
    [ "$status" -eq 0 ]
}

@test "plugin install --editor codex installs plugin rules without duplicating base guard hook" {
    run $CLI plugin install --editor codex security-pack
    [ "$status" -eq 0 ]

    [ -f "$TEST_TMP/.agents/rules/plugin-security-pack-quality-gates.md" ]

    run python3 - <<PY
import json
from pathlib import Path

hooks = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
matches = 0
for entries in hooks["hooks"].values():
    for entry in entries:
        for hook in entry.get("hooks", []):
            if hook.get("command", "").endswith("guard-destructive.sh\""):
                matches += 1

assert matches == 1, matches
PY
    [ "$status" -eq 0 ]
}

@test "plugin remove --editor codex strips plugin hook entries and files" {
    run $CLI plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]

    run $CLI plugin remove --editor codex memory-pack
    [ "$status" -eq 0 ]

    [ ! -f "$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-memory-pack-observation-capture.sh" ]
    [ ! -f "$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-memory-pack-session-summary.sh" ]

    run python3 - <<PY
import json
from pathlib import Path

hooks = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
for entries in hooks["hooks"].values():
    for entry in entries:
        assert entry.get("_source") != "ai-toolkit-plugin-memory-pack", entry
PY
    [ "$status" -eq 0 ]
}

@test "shared plugin assets stay when removing one editor target" {
    run $CLI plugin install --editor all memory-pack
    [ "$status" -eq 0 ]

    [ -f "$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-memory-pack-observation-capture.sh" ]
    [ -f "$TEST_TMP/.claude/settings.json" ]
    [ -f "$TEST_TMP/.codex/hooks.json" ]

    run $CLI plugin remove --editor codex memory-pack
    [ "$status" -eq 0 ]

    [ -f "$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-memory-pack-observation-capture.sh" ]

    run python3 - <<PY
import json
from pathlib import Path

claude = json.loads(Path("$TEST_TMP/.claude/settings.json").read_text(encoding="utf-8"))
assert any(
    entry.get("_source") == "ai-toolkit-plugin-memory-pack"
    for entry in claude["hooks"].get("PostToolUse", [])
), claude["hooks"]

codex = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
for entries in codex["hooks"].values():
    for entry in entries:
        assert entry.get("_source") != "ai-toolkit-plugin-memory-pack", entry
PY
    [ "$status" -eq 0 ]
}
