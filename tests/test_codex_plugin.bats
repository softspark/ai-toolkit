#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Native Codex plugin export contract.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CLI="node $TOOLKIT_DIR/bin/ai-toolkit.js"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP/home"
    mkdir -p "$HOME"
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "codex-plugin: export contains a native manifest, skills, hooks, and license" {
    archive="$TEST_TMP/ai-toolkit-codex-plugin.zip"

    run python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" export --output "$archive"
    [ "$status" -eq 0 ]
    [ -f "$archive" ]

    run python3 - "$archive" "$TOOLKIT_DIR/package.json" <<'PY'
import json
import sys
import zipfile
from pathlib import Path

archive = Path(sys.argv[1])
package = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
with zipfile.ZipFile(archive) as plugin:
    names = set(plugin.namelist())
    assert ".codex-plugin/plugin.json" in names
    assert "skills/debug/SKILL.md" in names
    assert "hooks/hooks.json" in names
    assert "hooks/guard-destructive.sh" in names
    assert "LICENSE" in names

    manifest = json.loads(plugin.read(".codex-plugin/plugin.json"))
    assert manifest["name"] == "ai-toolkit"
    assert manifest["version"] == package["version"]
    assert manifest["skills"] == "./skills/"
    assert "hooks" not in manifest
PY
    [ "$status" -eq 0 ]
}

@test "codex-plugin: verify validates a clean stage without mutating home" {
    run python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" verify
    [ "$status" -eq 0 ]
    [[ "$output" == *"Codex plugin validation passed"* ]]
    [ -z "$(find "$HOME" -mindepth 1 -print -quit)" ]
}

@test "codex-plugin: CLI dispatches export and documents the command" {
    archive="$TEST_TMP/cli.zip"

    run $CLI codex-plugin export --output "$archive"
    [ "$status" -eq 0 ]
    [ -f "$archive" ]
    [[ "$output" == *"Codex IDE does not support plugins"* ]]

    run $CLI help
    [ "$status" -eq 0 ]
    [[ "$output" == *"codex-plugin"* ]]
    [[ "$output" == *"export [--output FILE]"* ]]
    [[ "$output" == *"verify"* ]]
}

@test "codex-plugin: hooks use the exact command schema and PLUGIN_ROOT assets" {
    archive="$TEST_TMP/hooks.zip"
    python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" export --output "$archive" >/dev/null

    run python3 - "$archive" <<'PY'
import json
import re
import sys
import zipfile

expected_events = {
    "SessionStart", "PreToolUse", "PostToolUse", "PermissionRequest",
    "UserPromptSubmit", "SubagentStart", "SubagentStop", "PreCompact",
    "SessionEnd", "Stop",
}
with zipfile.ZipFile(sys.argv[1]) as plugin:
    hooks = json.loads(plugin.read("hooks/hooks.json"))["hooks"]
    assert set(hooks) == expected_events
    for event, groups in hooks.items():
        for group in groups:
            assert set(group) in ({"hooks"}, {"matcher", "hooks"})
            for handler in group["hooks"]:
                expected_keys = (
                    {"type", "command", "timeout"}
                    if event == "SessionEnd"
                    else {"type", "command"}
                )
                assert set(handler) == expected_keys, (event, handler)
                assert handler["type"] == "command"
                command = handler["command"]
                assert "${PLUGIN_ROOT}/hooks/" in command
                assert "git rev-parse" not in command
                assert "CODEX_HOME" not in command
                assert ".softspark/ai-toolkit/hooks" not in command
                asset_name = re.search(r"\$\{PLUGIN_ROOT\}/hooks/([A-Za-z0-9._-]+)", command).group(1)
                info = plugin.getinfo(f"hooks/{asset_name}")
                assert (info.external_attr >> 16) & 0o111

    session_end = hooks["SessionEnd"][0]["hooks"][0]
    assert session_end["timeout"] == 3
PY
    [ "$status" -eq 0 ]
}

@test "codex-plugin: archives are deterministic with fixed metadata and modes" {
    first="$TEST_TMP/first.zip"
    second="$TEST_TMP/second.zip"
    python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" export --output "$first" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" export --output "$second" >/dev/null
    [ "$(shasum "$first" | awk '{print $1}')" = "$(shasum "$second" | awk '{print $1}')" ]

    run python3 - "$first" <<'PY'
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as plugin:
    infos = plugin.infolist()
    assert [info.filename for info in infos] == sorted(info.filename for info in infos)
    assert all(info.date_time == (2026, 1, 1, 0, 0, 0) for info in infos)
    assert (plugin.getinfo("hooks/guard-destructive.sh").external_attr >> 16) & 0o111
    assert (plugin.getinfo(".codex-plugin/plugin.json").external_attr >> 16) & 0o777 == 0o644
PY
    [ "$status" -eq 0 ]
}

@test "codex-plugin: structural validation reports schema, mode, and symlink failures" {
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import json
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
temporary = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import codex_plugin

plugin = temporary / "invalid-plugin"
codex_plugin.stage_plugin(plugin)

manifest_path = plugin / ".codex-plugin" / "plugin.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["hooks"] = "../outside.json"
manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

guard = plugin / "hooks" / "guard-destructive.sh"
os.chmod(guard, 0o644)
(plugin / "escaped-link").symlink_to(temporary / "outside")

errors = codex_plugin.validate_staged_plugin(plugin)
assert any("default hooks/hooks.json" in error for error in errors), errors
assert any("not executable" in error for error in errors), errors
assert any("contains a symlink" in error for error in errors), errors
PY
    [ "$status" -eq 0 ]
}

@test "codex-plugin: source and output symlinks are rejected without overwrite" {
    source="$TEST_TMP/source"
    destination="$TEST_TMP/destination"
    outside="$TEST_TMP/outside.txt"
    mkdir -p "$source"
    printf 'outside sentinel\n' > "$outside"
    ln -s "$outside" "$source/linked.txt"

    run python3 - "$TOOLKIT_DIR" "$source" "$destination" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
import codex_plugin

try:
    codex_plugin._copy_tree_strict(Path(sys.argv[2]), Path(sys.argv[3]))
except ValueError as error:
    assert "source symlink is not allowed" in str(error)
else:
    raise AssertionError("source symlink was accepted")
PY
    [ "$status" -eq 0 ]

    archive="$TEST_TMP/unsafe.zip"
    ln -s "$outside" "$archive"
    run python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" export --output "$archive"
    [ "$status" -ne 0 ]
    grep -q '^outside sentinel$' "$outside"
}
