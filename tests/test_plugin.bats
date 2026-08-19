#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
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

@test "plugin install --editor codex does not duplicate a core hook the pack declares" {
    # enterprise-pack declares core's session-end.sh alongside two hooks of its
    # own. A pack naming a core hook must not get a second copy of it.
    run $CLI plugin install --editor codex enterprise-pack
    [ "$status" -eq 0 ]

    run python3 - <<PY
import json
from pathlib import Path

hooks = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
assert "_source" not in json.dumps(hooks)
matches = 0
for entries in hooks["hooks"].values():
    for entry in entries:
        for hook in entry.get("hooks", []):
            if hook.get("command", "").endswith("session-end.sh\""):
                matches += 1

# Base Codex hooks already register session-end.sh. Installing a pack that
# declares the same core hook must not increase that count.
assert matches <= 1, matches
PY
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-enterprise-pack-session-end.sh" ]

    # The pack's own hooks DO land, under pack-prefixed names.
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-enterprise-pack-status-line.sh" ]
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-enterprise-pack-output-style.sh" ]
}

@test "plugin rules are marker-injected into Codex AGENTS.md, not written as files" {
    # Driven against a fixture pack: no shipped pack declares rules since the
    # nine no-op packs were removed, and creating one under app/plugins would
    # race the pack-count assertions in other files under --jobs 4.
    run python3 - <<PY
import json, pathlib, sys, tempfile
sys.path.insert(0, "$TOOLKIT_DIR/scripts")
import plugin

tmp = pathlib.Path(tempfile.mkdtemp())
pack = tmp / "fixture-pack"
(pack / "rules").mkdir(parents=True)
(pack / "rules" / "quality-gates.md").write_text("# Fixture rule\n\nBody.\n")
(pack / "plugin.json").write_text(json.dumps({
    "name": "fixture-pack",
    "description": "ships one rule",
    "version": "1.0.0",
    "domain": "testing",
    "type": "plugin-pack",
    "includes": {"agents": [], "skills": [], "rules": ["quality-gates"], "hooks": []},
}))
plugin.PLUGINS_DIR = tmp
sys.exit(0 if plugin.install_pack("fixture-pack", "codex") else 1)
PY
    [ "$status" -eq 0 ]

    # Codex reads instructions only from AGENTS.md, so pack rules are marker-
    # injected there, not written as unread ~/.agents/rules/ files.
    grep -q '<!-- TOOLKIT:plugin-fixture-pack-quality-gates START -->' "$TEST_TMP/.codex/AGENTS.md"
    [ ! -f "$TEST_TMP/.agents/rules/plugin-fixture-pack-quality-gates.md" ]
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
    # enterprise-pack puts two hooks on Stop; memory-pack adds a third from a
    # different pack, plus one on PostToolUse. Two packs writing the same event
    # must accumulate rather than overwrite each other.
    run $CLI plugin install --editor codex enterprise-pack
    [ "$status" -eq 0 ]
    run $CLI plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]

    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-enterprise-pack-status-line.sh" ]
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-enterprise-pack-output-style.sh" ]
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-session-summary.sh" ]
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh" ]

    run python3 - <<PY
import json
from pathlib import Path

data = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
enterprise = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-enterprise-pack"
memory = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack"
stop_enterprise = [
    group
    for group in data["hooks"]["Stop"]
    if any(enterprise in handler["command"] for handler in group["hooks"])
]
stop_memory = [
    group
    for group in data["hooks"]["Stop"]
    if any(memory in handler["command"] for handler in group["hooks"])
]
post_memory = [
    group
    for group in data["hooks"]["PostToolUse"]
    if any(memory in handler["command"] for handler in group["hooks"])
]
# The second pack must not clobber the first one's entries on the same event.
assert len(stop_enterprise) == 2, stop_enterprise
assert len(stop_memory) == 1, stop_memory
assert all("matcher" not in group for group in stop_enterprise + stop_memory)
assert len(post_memory) == 1, post_memory
assert "_source" not in json.dumps(data)
PY
    [ "$status" -eq 0 ]
}

# A throwaway toolkit whose only pack ships its own agent and skill, mirroring a
# self-contained plugin pack rather than one that merely references core assets.
_selfcontained_pack_toolkit() {
    local root
    root="$(mktemp -d)"
    cp -R "$TOOLKIT_DIR/bin" "$TOOLKIT_DIR/scripts" "$root/"
    mkdir -p "$root/app/agents" "$root/app/skills" "$root/app/hooks" \
             "$root/app/plugins/demo-selfcontained/agents" \
             "$root/app/plugins/demo-selfcontained/skills/demo-own-skill"

    cat > "$root/app/plugins/demo-selfcontained/plugin.json" <<'EOF'
{
  "name": "demo-selfcontained",
  "description": "Pack shipping its own agent and skill",
  "version": "1.0.0",
  "domain": "demo",
  "type": "plugin-pack",
  "status": "experimental",
  "requires": {"ai-toolkit": ">=1.0.0", "claude-code": ">=1.0.33"},
  "includes": {"agents": ["demo-own-agent"], "skills": ["demo-own-skill"], "rules": [], "hooks": []},
  "hook_events": {}
}
EOF
    cat > "$root/app/plugins/demo-selfcontained/agents/demo-own-agent.md" <<'EOF'
---
name: demo-own-agent
description: An agent shipped by the pack itself
tools: Read
model: sonnet
---
Body.
EOF
    cat > "$root/app/plugins/demo-selfcontained/skills/demo-own-skill/SKILL.md" <<'EOF'
---
name: demo-own-skill
description: "A skill shipped by the pack itself"
allowed-tools: Read
---
Body.
EOF
    echo "$root"
}

@test "plugin install links an agent the pack ships itself" {
    local root
    root="$(_selfcontained_pack_toolkit)"

    run node "$root/bin/ai-toolkit.js" plugin install --editor claude demo-selfcontained
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Linked agent: demo-own-agent"
    echo "$output" | grep -qv "WARN agent not found"

    # The link must point into the pack, not into app/agents.
    [ -L "$TEST_TMP/.claude/agents/demo-own-agent.md" ]
    run readlink "$TEST_TMP/.claude/agents/demo-own-agent.md"
    echo "$output" | grep -q "plugins/demo-selfcontained/agents/demo-own-agent.md"
    [ -e "$TEST_TMP/.claude/skills/demo-own-skill" ]

    rm -rf "$root"
}

@test "plugin remove drops the agent link the pack owns" {
    local root
    root="$(_selfcontained_pack_toolkit)"

    run node "$root/bin/ai-toolkit.js" plugin install --editor claude demo-selfcontained
    [ "$status" -eq 0 ]
    [ -L "$TEST_TMP/.claude/agents/demo-own-agent.md" ]

    run node "$root/bin/ai-toolkit.js" plugin remove --editor claude demo-selfcontained
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_TMP/.claude/agents/demo-own-agent.md" ]

    rm -rf "$root"
}

@test "pack reference validation accepts assets the pack ships itself" {
    run python3 - <<PY
import sys, tempfile
from pathlib import Path

sys.path.insert(0, "$TOOLKIT_DIR/scripts")
from plugin_schema import validate_references

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    core_agents = root / "app" / "agents"
    core_skills = root / "app" / "skills"
    pack = root / "app" / "plugins" / "demo"
    core_agents.mkdir(parents=True)
    core_skills.mkdir(parents=True)
    (pack / "agents").mkdir(parents=True)
    (pack / "skills" / "own-skill").mkdir(parents=True)
    (pack / "agents" / "own-agent.md").write_text("x", encoding="utf-8")
    (pack / "skills" / "own-skill" / "SKILL.md").write_text("x", encoding="utf-8")

    data = {"includes": {"agents": ["own-agent"], "skills": ["own-skill"]}}

    # Core dirs only: the pack's own assets are invisible — the old false errors.
    without = validate_references(data, core_agents, core_skills)
    assert len(without) == 2, without

    # With the pack dir: clean.
    with_pack = validate_references(data, core_agents, core_skills, pack_dir=pack)
    assert with_pack == [], with_pack

    # A genuinely missing reference still errors.
    missing = validate_references(
        {"includes": {"agents": ["nope"], "skills": []}},
        core_agents, core_skills, pack_dir=pack,
    )
    assert missing == ["References missing agent: nope"], missing

print("OK")
PY
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "^OK\$"
}

# A pack dropped into the user-level plugins dir, i.e. outside the npm package.
# AI_TOOLKIT_HOME points the toolkit's data dir at the test HOME, so the pack
# root under test is $TEST_TMP/.softspark/ai-toolkit/plugins.
_user_pack() {
    local dir="$TEST_TMP/.softspark/ai-toolkit/plugins/demo-user-pack"
    mkdir -p "$dir/agents" "$dir/skills/demo-user-skill"

    cat > "$dir/plugin.json" <<'EOF'
{
  "name": "demo-user-pack",
  "description": "Pack installed outside the toolkit package",
  "version": "2.0.0",
  "domain": "demo",
  "type": "plugin-pack",
  "status": "experimental",
  "requires": {"ai-toolkit": ">=1.0.0", "claude-code": ">=1.0.33"},
  "includes": {"agents": ["demo-user-agent"], "skills": ["demo-user-skill"], "rules": [], "hooks": []},
  "hook_events": {}
}
EOF
    cat > "$dir/agents/demo-user-agent.md" <<'EOF'
---
name: demo-user-agent
description: An agent from a user-installed pack
tools: Read
model: sonnet
---
Body.
EOF
    cat > "$dir/skills/demo-user-skill/SKILL.md" <<'EOF'
---
name: demo-user-skill
description: "A skill from a user-installed pack"
allowed-tools: Read
---
Body.
EOF
    echo "$dir"
}

@test "plugin list discovers a pack in the user-level plugins dir" {
    _user_pack >/dev/null

    AI_TOOLKIT_HOME="$TEST_TMP/.softspark/ai-toolkit" run $CLI plugin list
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "demo-user-pack"
    # Core packs stay visible alongside it.
    echo "$output" | grep -q "memory-pack"
}

@test "plugin install works from the user-level plugins dir" {
    local dir
    dir="$(_user_pack)"

    AI_TOOLKIT_HOME="$TEST_TMP/.softspark/ai-toolkit" run $CLI plugin install --editor claude demo-user-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Linked agent: demo-user-agent"
    echo "$output" | grep -q "Linked skill: demo-user-skill"

    # Both links resolve into the user dir, not into the toolkit package.
    run readlink "$TEST_TMP/.claude/agents/demo-user-agent.md"
    echo "$output" | grep -q "\.softspark/ai-toolkit/plugins/demo-user-pack/agents/demo-user-agent.md"
    run readlink "$TEST_TMP/.claude/skills/demo-user-skill"
    echo "$output" | grep -q "\.softspark/ai-toolkit/plugins/demo-user-pack/skills/demo-user-skill"
}

@test "a core pack wins a name collision with a user pack" {
    local dir="$TEST_TMP/.softspark/ai-toolkit/plugins/memory-pack"
    mkdir -p "$dir"
    cat > "$dir/plugin.json" <<'EOF'
{
  "name": "memory-pack",
  "description": "Shadow attempt",
  "version": "9.9.9",
  "domain": "demo",
  "type": "plugin-pack",
  "status": "experimental",
  "requires": {"ai-toolkit": ">=1.0.0", "claude-code": ">=1.0.33"},
  "includes": {"agents": [], "skills": [], "rules": [], "hooks": []},
  "hook_events": {}
}
EOF

    AI_TOOLKIT_HOME="$TEST_TMP/.softspark/ai-toolkit" run python3 -c "
import sys
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
import plugin
packs = [p for p in plugin.list_available() if p['name'] == 'memory-pack']
assert len(packs) == 1, packs
assert packs[0]['_root'] == 'core', packs[0]['_root']
assert packs[0]['version'] != '9.9.9', packs[0]['version']
print('OK')
"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "^OK\$"
}

@test "plugin install repairs a dangling link left by a toolkit upgrade" {
    _user_pack >/dev/null
    export AI_TOOLKIT_HOME="$TEST_TMP/.softspark/ai-toolkit"

    # The state a toolkit upgrade leaves behind: links into the old npm package
    # path, which the upgrade deleted. The pack now lives somewhere else.
    mkdir -p "$TEST_TMP/.claude/agents" "$TEST_TMP/.claude/skills"
    ln -s "$TEST_TMP/gone/plugins/demo-user-pack/agents/demo-user-agent.md" \
          "$TEST_TMP/.claude/agents/demo-user-agent.md"
    ln -s "$TEST_TMP/gone/plugins/demo-user-pack/skills/demo-user-skill" \
          "$TEST_TMP/.claude/skills/demo-user-skill"
    [ -L "$TEST_TMP/.claude/agents/demo-user-agent.md" ]
    [ ! -e "$TEST_TMP/.claude/agents/demo-user-agent.md" ]   # dangling

    run $CLI plugin install --editor claude demo-user-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Dangling agent link removed"
    echo "$output" | grep -q "Dangling skill link removed"
    echo "$output" | grep -q "Linked agent: demo-user-agent"
    echo "$output" | grep -q "Linked skill: demo-user-skill"

    # Both links resolve again, into the pack root that actually exists.
    [ -e "$TEST_TMP/.claude/agents/demo-user-agent.md" ]
    [ -e "$TEST_TMP/.claude/skills/demo-user-skill/SKILL.md" ]
    run readlink "$TEST_TMP/.claude/agents/demo-user-agent.md"
    echo "$output" | grep -q "\.softspark/ai-toolkit/plugins/demo-user-pack/agents/demo-user-agent.md"
}

@test "plugin install leaves a live link and a real file alone" {
    _user_pack >/dev/null
    export AI_TOOLKIT_HOME="$TEST_TMP/.softspark/ai-toolkit"

    # A real file the user owns, sitting on the agent name.
    mkdir -p "$TEST_TMP/.claude/agents"
    printf 'user content\n' > "$TEST_TMP/.claude/agents/demo-user-agent.md"

    run $CLI plugin install --editor claude demo-user-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "OK agent: demo-user-agent"
    [ ! -L "$TEST_TMP/.claude/agents/demo-user-agent.md" ]
    grep -q "user content" "$TEST_TMP/.claude/agents/demo-user-agent.md"

    # A second run over the now-live skill link reports OK, not a relink.
    run $CLI plugin install --editor claude demo-user-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "OK skill: demo-user-skill"
    echo "$output" | grep -qv "Dangling"
}
