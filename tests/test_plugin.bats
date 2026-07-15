#!/usr/bin/env bats
# Tests for plugin pack installation across Claude and global Codex targets.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CLI="node $TOOLKIT_DIR/bin/ai-toolkit.js"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    unset CODEX_HOME
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "plugin install --editor codex bootstraps global Codex surface and installs memory-pack hooks" {
    run $CLI plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]

    # Global Codex instructions live at ~/.codex/AGENTS.md, not ~/AGENTS.md.
    [ -f "$TEST_TMP/.codex/AGENTS.md" ]
    [ ! -f "$TEST_TMP/AGENTS.md" ]
    [ -f "$TEST_TMP/.codex/hooks.json" ]
    [ -e "$TEST_TMP/.agents/skills/mem-search" ]
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh" ]
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-session-summary.sh" ]
    [ ! -e "$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-memory-pack-observation-capture.sh" ]

    run python3 - <<PY
import json
from pathlib import Path

hooks = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
post = hooks["hooks"]["PostToolUse"]
stop = hooks["hooks"]["Stop"]
owner = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack"

assert set(hooks) == {"hooks"}
assert "_source" not in json.dumps(hooks)
for event, groups in hooks["hooks"].items():
    for group in groups:
        assert set(group) <= {"matcher", "hooks"}, (event, group)
        for handler in group["hooks"]:
            assert set(handler) <= {
                "type", "command", "commandWindows", "timeout", "statusMessage", "async"
            }, handler

assert any(
    entry.get("matcher") == "Bash"
    and owner in entry["hooks"][0]["command"]
    and entry["hooks"][0]["command"].endswith(
        '/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh"'
    )
    for entry in post
), post

assert any(
    "matcher" not in entry
    and owner in entry["hooks"][0]["command"]
    and entry["hooks"][0]["command"].endswith(
        '/ai-toolkit-hooks/plugin-memory-pack-session-summary.sh"'
    )
    for entry in stop
), stop
plugin_commands = [
    handler["command"]
    for groups in hooks["hooks"].values()
    for entry in groups
    for handler in entry["hooks"]
    if owner in handler["command"]
]
assert len(plugin_commands) == 2, plugin_commands
assert all('\${CODEX_HOME:-\$HOME/.codex}' in command for command in plugin_commands)
PY
    [ "$status" -eq 0 ]
}

@test "plugin install --editor codex installs plugin rules without duplicating base guard hook" {
    run $CLI plugin install --editor codex security-pack
    [ "$status" -eq 0 ]

    # Codex reads instructions only from AGENTS.md, so pack rules are marker-
    # injected into ~/.codex/AGENTS.md, not written as unread ~/.agents/rules/ files.
    grep -q '<!-- TOOLKIT:plugin-security-pack-quality-gates START -->' "$TEST_TMP/.codex/AGENTS.md"
    [ ! -f "$TEST_TMP/.agents/rules/plugin-security-pack-quality-gates.md" ]

    run python3 - <<PY
import json
from pathlib import Path

hooks = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
assert "_source" not in json.dumps(hooks)
matches = 0
for entries in hooks["hooks"].values():
    for entry in entries:
        for hook in entry.get("hooks", []):
            if hook.get("command", "").endswith("guard-destructive.sh\""):
                matches += 1

# Base Codex hooks register guard-destructive.sh twice: PreToolUse + PermissionRequest.
# Plugin install must not increase that count.
assert matches == 2, matches
PY
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-security-pack-guard-destructive.sh" ]
    [ ! -e "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-security-pack-quality-gate.sh" ]
}

@test "plugin Codex install preserves user logical skill collisions" {
    mkdir -p "$TEST_TMP/.agents/skills/custom-memory"
    cat > "$TEST_TMP/.agents/skills/custom-memory/SKILL.md" <<'MD'
---
name: mem-search
description: User-owned memory search.
---
Keep this plugin collision unchanged.
MD

    run $CLI plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_TMP/.agents/skills/mem-search" ]
    grep -q 'Keep this plugin collision unchanged' \
        "$TEST_TMP/.agents/skills/custom-memory/SKILL.md"
}

@test "plugin Codex install rejects symlinked skill roots without external writes" {
    external="$(mktemp -d)"
    printf '%s\n' 'external plugin sentinel' > "$external/sentinel.txt"
    shasum "$external/sentinel.txt" > "$external.before"
    ln -s "$external" "$TEST_TMP/.agents"

    run $CLI plugin install --editor codex memory-pack
    [ "$status" -ne 0 ]
    shasum "$external/sentinel.txt" > "$external.after"
    cmp "$external.before" "$external.after"
    [ ! -e "$external/skills" ]
    rm -rf "$external"
}

@test "plugin remove --editor codex strips only owned handlers and files" {
    run $CLI plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]

    run python3 - <<PY
import json
from pathlib import Path

path = Path("$TEST_TMP/.codex/hooks.json")
data = json.loads(path.read_text(encoding="utf-8"))
owner = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack"
plugin_group = next(
    group
    for group in data["hooks"]["PostToolUse"]
    if owner in group["hooks"][0]["command"]
)
plugin_group["hooks"].append({"type": "command", "command": "echo colocated-user"})
data["hooks"]["Stop"].append({
    "hooks": [{"type": "command", "command": "echo independent-user"}]
})
path.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run $CLI plugin remove --editor codex memory-pack
    [ "$status" -eq 0 ]

    [ ! -f "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh" ]
    [ ! -f "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-session-summary.sh" ]

    run python3 - <<PY
import json
from pathlib import Path

hooks = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
commands = []
for entries in hooks["hooks"].values():
    for entry in entries:
        assert set(entry) <= {"matcher", "hooks"}, entry
        commands.extend(handler["command"] for handler in entry["hooks"])
assert not any("AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack" in c for c in commands)
assert "echo colocated-user" in commands
assert "echo independent-user" in commands
assert any("AI_TOOLKIT_HOOK_OWNER=ai-toolkit " in c for c in commands)
PY
    [ "$status" -eq 0 ]
}

@test "shared plugin assets stay when removing one editor target" {
    run $CLI plugin install --editor all memory-pack
    [ "$status" -eq 0 ]

    [ -f "$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-memory-pack-observation-capture.sh" ]
    [ -f "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh" ]
    [ -f "$TEST_TMP/.claude/settings.json" ]
    [ -f "$TEST_TMP/.codex/hooks.json" ]

    run $CLI plugin remove --editor codex memory-pack
    [ "$status" -eq 0 ]

    [ -f "$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-memory-pack-observation-capture.sh" ]
    [ ! -f "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh" ]

    run python3 - <<PY
import json
from pathlib import Path

claude = json.loads(Path("$TEST_TMP/.claude/settings.json").read_text(encoding="utf-8"))
assert any(
    entry.get("_source") == "ai-toolkit-plugin-memory-pack"
    for entry in claude["hooks"].get("PostToolUse", [])
), claude["hooks"]

codex = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
codex_commands = []
for entries in codex["hooks"].values():
    for entry in entries:
        codex_commands.extend(handler["command"] for handler in entry["hooks"])
assert not any(
    "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack" in command
    for command in codex_commands
)
assert any("AI_TOOLKIT_HOOK_OWNER=ai-toolkit " in command for command in codex_commands)
PY
    [ "$status" -eq 0 ]
}

@test "base Codex hook regeneration preserves native plugin handlers and assets" {
    run $CLI plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]

    shasum "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-"*.sh \
        > "$TEST_TMP/plugin-assets.before"
    run env HOME="$TEST_TMP" \
        python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$TEST_TMP" --global
    [ "$status" -eq 0 ]
    shasum "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-"*.sh \
        > "$TEST_TMP/plugin-assets.after"
    cmp "$TEST_TMP/plugin-assets.before" "$TEST_TMP/plugin-assets.after"

    run python3 - <<PY
import json
from pathlib import Path

data = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
commands = [
    handler["command"]
    for groups in data["hooks"].values()
    for group in groups
    for handler in group["hooks"]
]
owner = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack"
assert sum(owner in command for command in commands) == 2, commands
assert any("AI_TOOLKIT_HOOK_OWNER=ai-toolkit " in command for command in commands)
assert "_source" not in json.dumps(data)
PY
    [ "$status" -eq 0 ]
}

@test "plugin install migrates legacy Codex _source ownership to native commands" {
    mkdir -p "$TEST_TMP/.codex"
    cat > "$TEST_TMP/.codex/hooks.json" <<'JSON'
{
  "hooks": {
    "PostToolUse": [
      {
        "_source": "ai-toolkit-plugin-memory-pack",
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"$HOME/.softspark/ai-toolkit/hooks/plugin-memory-pack-observation-capture.sh\""
          }
        ]
      }
    ]
  }
}
JSON

    run $CLI plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]

    run python3 - <<PY
import json
from pathlib import Path

data = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
serialized = json.dumps(data)
assert "_source" not in serialized
assert ".softspark/ai-toolkit/hooks" not in serialized
owner = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack"
commands = [
    handler["command"]
    for groups in data["hooks"].values()
    for group in groups
    for handler in group["hooks"]
]
assert sum(owner in command for command in commands) == 2, commands
PY
    [ "$status" -eq 0 ]
}

@test "plugin Codex target honors an existing custom CODEX_HOME" {
    custom_home="$TEST_TMP/custom-codex-home"
    mkdir -p "$custom_home"

    run env CODEX_HOME="$custom_home" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]
    [ -f "$custom_home/AGENTS.md" ]
    [ -f "$custom_home/hooks.json" ]
    [ -x "$custom_home/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh" ]
    [ ! -e "$TEST_TMP/.codex/hooks.json" ]
    grep -q '\${CODEX_HOME:-\$HOME/.codex}/ai-toolkit-hooks/' "$custom_home/hooks.json"

    run env CODEX_HOME="$custom_home" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" plugin remove --editor codex memory-pack
    [ "$status" -eq 0 ]
    [ ! -e "$custom_home/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh" ]
}

@test "plugin Codex target rejects symlinked CODEX_HOME without external writes" {
    external="$TEST_TMP/external-codex"
    mkdir -p "$external"
    printf '%s\n' 'external sentinel' > "$external/sentinel.txt"
    shasum "$external/sentinel.txt" > "$TEST_TMP/external.before"
    ln -s "$external" "$TEST_TMP/.codex"

    run $CLI plugin install --editor codex memory-pack
    [ "$status" -ne 0 ]
    shasum "$external/sentinel.txt" > "$TEST_TMP/external.after"
    cmp "$TEST_TMP/external.before" "$TEST_TMP/external.after"
    [ ! -e "$external/hooks.json" ]
    [ ! -e "$external/AGENTS.md" ]
}

@test "plugin Codex target preserves a user-owned hook asset collision" {
    mkdir -p "$TEST_TMP/.codex/ai-toolkit-hooks"
    user_asset="$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh"
    printf '%s\n' '#!/usr/bin/env bash' 'echo user-owned' > "$user_asset"
    cp "$user_asset" "$TEST_TMP/user-asset.before"

    run $CLI plugin install --editor codex memory-pack
    [ "$status" -ne 0 ]
    cmp "$TEST_TMP/user-asset.before" "$user_asset"

    run python3 - <<PY
import json
from pathlib import Path

data = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
assert "ai-toolkit-plugin-memory-pack" not in json.dumps(data)
PY
    [ "$status" -eq 0 ]
}

@test "plugin Codex hook transaction rolls back assets when JSON write fails" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

pack = plugin.find_pack("memory-pack")
assert pack is not None
pack_dir = Path(pack["_dir"])
plugin._install_codex_base()
hooks_path = plugin.CODEX_HOME / "hooks.json"
before = hooks_path.read_bytes()
specs = plugin._resolve_pack_hooks(pack, pack_dir)

with mock.patch.object(plugin, "write_hooks_json", side_effect=OSError("injected")):
    try:
        plugin._install_codex_hooks("memory-pack", specs, [])
    except OSError as error:
        assert "injected" in str(error)
    else:
        raise AssertionError("expected injected JSON write failure")

assert hooks_path.read_bytes() == before
assert not list(plugin.CODEX_HOOKS_DIR.glob("plugin-memory-pack-*.sh"))
assert not list(plugin.CODEX_HOOKS_DIR.glob(".*.tmp"))
PY
    [ "$status" -eq 0 ]
}

@test "plugin Codex install keeps multiple hooks for one event across pack installs" {
    run $CLI plugin install --editor codex enterprise-pack
    [ "$status" -eq 0 ]
    run $CLI plugin install --editor codex frontend-pack
    [ "$status" -eq 0 ]

    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-enterprise-pack-status-line.sh" ]
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-enterprise-pack-output-style.sh" ]
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-frontend-pack-post-tool-use.sh" ]

    run python3 - <<PY
import json
from pathlib import Path

data = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
enterprise = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-enterprise-pack"
frontend = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-frontend-pack"
stop_groups = [
    group
    for group in data["hooks"]["Stop"]
    if any(enterprise in handler["command"] for handler in group["hooks"])
]
post_groups = [
    group
    for group in data["hooks"]["PostToolUse"]
    if any(frontend in handler["command"] for handler in group["hooks"])
]
assert len(stop_groups) == 2, stop_groups
assert all("matcher" not in group for group in stop_groups)
assert len(post_groups) == 1, post_groups
assert post_groups[0].get("matcher") == "Bash"
assert "_source" not in json.dumps(data)
PY
    [ "$status" -eq 0 ]
}
