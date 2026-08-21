#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for doctor check 11 -- Claude app plugin loading next to the global install.
# Optimized: install runs once in setup_file, each test restores from snapshot.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export DOUBLE_LOAD_SNAPSHOT
    DOUBLE_LOAD_SNAPSHOT="$(mktemp -d)"
    export HOME="$DOUBLE_LOAD_SNAPSHOT"
    python3 "$TOOLKIT_DIR/scripts/install.py" "$DOUBLE_LOAD_SNAPSHOT" >/dev/null 2>&1
}

teardown_file() {
    rm -rf "$DOUBLE_LOAD_SNAPSHOT"
}

setup() {
    TEST_TMP="$(mktemp -d)"
    cp -a "$DOUBLE_LOAD_SNAPSHOT/." "$TEST_TMP/"
    export HOME="$TEST_TMP"
}

teardown() {
    rm -rf "$TEST_TMP"
}

toolkit_version() {
    python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['version'])" \
        "$TOOLKIT_DIR/package.json"
}

register_plugin() {
    # Defaults to a stale version so the double-load assertions below exercise
    # the common real-world state: an upload made before the last toolkit bump.
    local version="${1:-4.26.0}"
    mkdir -p "$TEST_TMP/.claude/plugins"
    cat > "$TEST_TMP/.claude/plugins/installed_plugins.json" <<JSON
{
  "version": 2,
  "plugins": {
    "ai-toolkit@local-desktop-app-uploads": [
      {
        "scope": "user",
        "installPath": "/tmp/ai-toolkit",
        "version": "${version}"
      }
    ]
  }
}
JSON
}

enable_plugin() {
    python3 - "$TEST_TMP/.claude/settings.json" "$1" <<'PY'
import json, sys
path, state = sys.argv[1], sys.argv[2] == "true"
data = json.loads(open(path, encoding="utf-8").read())
data["enabledPlugins"] = {"ai-toolkit@local-desktop-app-uploads": state}
open(path, "w", encoding="utf-8").write(json.dumps(data, indent=2) + "\n")
PY
}

@test "doctor skips the check when no plugin registry exists" {
    rm -f "$TEST_TMP/.claude/plugins/installed_plugins.json"
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q "SKIP: no Claude Code plugin registry"
}

@test "doctor warns when the plugin is active next to the global install" {
    register_plugin
    enable_plugin true
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q "WARN: ai-toolkit@local-desktop-app-uploads is active next to the global install"
    echo "$output" | grep -q "fire twice per event"
}

@test "doctor stays quiet when the plugin is registered but disabled" {
    register_plugin
    enable_plugin false
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q "OK: ai-toolkit plugin registered but disabled for Claude Code"
    ! echo "$output" | grep -q "fire twice per event"
}

@test "doctor --fix disables the plugin and leaves the global install intact" {
    register_plugin
    enable_plugin true
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED: disabled ai-toolkit@local-desktop-app-uploads"
    run python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['enabledPlugins']['ai-toolkit@local-desktop-app-uploads'])" "$TEST_TMP/.claude/settings.json"
    [ "$output" = "False" ]
    [ -d "$TEST_TMP/.claude/skills" ]
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q "OK: ai-toolkit plugin registered but disabled for Claude Code"
}

@test "doctor warns when the uploaded plugin lags the toolkit version" {
    register_plugin 4.26.0
    enable_plugin false
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q "is v4.26.0 but the toolkit is v$(toolkit_version)"
    echo "$output" | grep -q "claude-app export"
}

@test "doctor reports version drift even while the plugin is disabled for Claude Code" {
    # The regression this closes: the disabled branch returned OK and never
    # looked at versions, so a stale upload passed silently. Chat and Cowork
    # still run the plugin, so the drift matters regardless of this flag.
    register_plugin 4.26.0
    enable_plugin false
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q "OK: ai-toolkit plugin registered but disabled for Claude Code"
    echo "$output" | grep -q "but the toolkit is v$(toolkit_version)"
}

@test "doctor stays quiet about versions when the upload is current" {
    register_plugin "$(toolkit_version)"
    enable_plugin false
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    ! echo "$output" | grep -q "but the toolkit is"
}

@test "doctor --fix cannot silence version drift" {
    register_plugin 4.26.0
    enable_plugin true
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED: disabled ai-toolkit@local-desktop-app-uploads"
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q "but the toolkit is v$(toolkit_version)"
}

@test "install re-asserts the plugin as disabled for Claude Code" {
    register_plugin
    enable_plugin true
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_TMP"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Disabled Claude app plugin for Claude Code: ai-toolkit@local-desktop-app-uploads"
    run python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['enabledPlugins']['ai-toolkit@local-desktop-app-uploads'])" "$TEST_TMP/.claude/settings.json"
    [ "$output" = "False" ]
}

@test "install says nothing when the plugin is already disabled" {
    register_plugin
    enable_plugin false
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_TMP"
    [ "$status" -eq 0 ]
    ! echo "$output" | grep -q "Disabled Claude app plugin"
}

@test "install leaves an unrelated enabled plugin alone" {
    mkdir -p "$TEST_TMP/.claude/plugins"
    printf '{"version":2,"plugins":{"frontend-design@claude-plugins-official":[{"scope":"local","version":"1"}]}}' \
        > "$TEST_TMP/.claude/plugins/installed_plugins.json"
    python3 - "$TEST_TMP/.claude/settings.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.loads(open(path, encoding="utf-8").read())
data["enabledPlugins"] = {"frontend-design@claude-plugins-official": True}
open(path, "w", encoding="utf-8").write(json.dumps(data, indent=2) + "\n")
PY
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_TMP"
    [ "$status" -eq 0 ]
    run python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['enabledPlugins']['frontend-design@claude-plugins-official'])" "$TEST_TMP/.claude/settings.json"
    [ "$output" = "True" ]
}

@test "doctor ignores unrelated plugins" {
    mkdir -p "$TEST_TMP/.claude/plugins"
    printf '{"version":2,"plugins":{"frontend-design@claude-plugins-official":[{"scope":"local"}]}}' \
        > "$TEST_TMP/.claude/plugins/installed_plugins.json"
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q "OK: no ai-toolkit plugin registered in Claude Code"
}
