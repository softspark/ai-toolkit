#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    export AI_TOOLKIT_HOME="$TEST_TMP/.softspark/ai-toolkit"
    unset CLAUDE_SWITCH_CONFIG CLAUDE_CONFIG_DIR
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "claude-switch: toolkit help advertises the command" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" help
    [ "$status" -eq 0 ]
    [[ "$output" == *"claude-switch"* ]]
    [[ "$output" == *"codex-switch"* ]]
    [[ "$output" == *"llm-status"* ]]
    [[ "$output" != *"openai-switch"* ]]
}

@test "claude-switch: toolkit help exposes explicit commands and rejects shell-init" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"run"* ]]
    [[ "$output" != *"shell-init"* ]]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch shell-init
    [ "$status" -ne 0 ]
    [[ "$output" != *"claude()"* ]]
}

@test "claude-switch: toolkit init keeps default on the existing Claude directory" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch init
    [ "$status" -eq 0 ]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch status --json
    [ "$status" -eq 0 ]
    RESULT="$output" python3 -c 'import json, os; data=json.loads(os.environ["RESULT"]); assert data["account"] == "default"; assert data["config_dir"] == os.path.join(os.environ["HOME"], ".claude"); assert data["source"] == "default"'
}

@test "claude-switch: binding respects caller directory and nested paths" {
    mkdir -p "$TEST_TMP/projects/infinity/src" "$TEST_TMP/projects/infinity-other"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch init
    [ "$status" -eq 0 ]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch add infinity
    [ "$status" -eq 0 ]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch bind "$TEST_TMP/projects/infinity" infinity
    [ "$status" -eq 0 ]
    cd "$TEST_TMP/projects/infinity/src"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch status --json
    [ "$status" -eq 0 ]
    RESULT="$output" python3 -c 'import json, os; data=json.loads(os.environ["RESULT"]); assert data["account"] == "infinity"; assert data["source"] == "project"'
    cd "$TEST_TMP/projects/infinity-other"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch status --json
    [ "$status" -eq 0 ]
    RESULT="$output" python3 -c 'import json, os; assert json.loads(os.environ["RESULT"])["account"] == "default"'
}

@test "claude-switch: status override does not change the default" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch init
    [ "$status" -eq 0 ]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch add infinity
    [ "$status" -eq 0 ]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch status --account infinity --json
    [ "$status" -eq 0 ]
    RESULT="$output" python3 -c 'import json, os; data=json.loads(os.environ["RESULT"]); assert data["account"] == "infinity"; assert data["source"] == "override"'
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch status --json
    [ "$status" -eq 0 ]
    RESULT="$output" python3 -c 'import json, os; assert json.loads(os.environ["RESULT"])["account"] == "default"'
}

@test "account commands: package publishes only ai-toolkit without standalone launchers" {
    run node -e 'const p = require(process.argv[1]); if (JSON.stringify(p.bin) !== JSON.stringify({"ai-toolkit":"bin/ai-toolkit.js"})) process.exit(1)' "$TOOLKIT_DIR/package.json"
    [ "$status" -eq 0 ]
    [ ! -e "$TOOLKIT_DIR/bin/claude-switch.js" ]
    [ ! -e "$TOOLKIT_DIR/bin/codex-switch.js" ]
    [ ! -e "$TOOLKIT_DIR/bin/llm-status.js" ]
}

@test "claude-switch: toolkit preserves Claude exit codes and signals" {
    mkdir -p "$TEST_TMP/bin"
    printf '#!/bin/sh\nif [ "$1" = "exit" ]; then exit 23; fi\nkill -TERM "$$"\n' > "$TEST_TMP/bin/claude"
    chmod +x "$TEST_TMP/bin/claude"
    export PATH="$TEST_TMP/bin:$PATH"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch init
    [ "$status" -eq 0 ]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch run -- exit
    [ "$status" -eq 23 ]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" claude-switch run
    [ "$status" -eq 143 ]
}
