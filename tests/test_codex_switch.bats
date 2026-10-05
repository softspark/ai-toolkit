#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    export AI_TOOLKIT_HOME="$TEST_TMP/data"
    unset CODEX_SWITCH_CONFIG CODEX_HOME CODEX_SQLITE_HOME CODEX_ACCESS_TOKEN CODEX_API_KEY OPENAI_API_KEY
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "codex-switch: canonical toolkit command rejects old alias and shell-init" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" codex-switch --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"ai-toolkit codex-switch"* ]]
    [[ "$output" != *"shell-init"* ]]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" openai-switch --help
    [ "$status" -ne 0 ]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" codex-switch shell-init
    [ "$status" -ne 0 ]
    [[ "$output" != *"codex()"* ]]
}

@test "codex-switch: default profile and dashboard use Codex home" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" codex-switch init
    [ "$status" -eq 0 ]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" codex-switch status --json
    [ "$status" -eq 0 ]
    RESULT="$output" python3 -c 'import json,os;d=json.loads(os.environ["RESULT"]);assert d["account_count"]==1;assert d["config_dir"]==os.path.realpath(os.path.join(os.environ["HOME"],".codex"))'
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" codex-switch status
    [ "$status" -eq 0 ]
    [[ "$output" == *"CODEX ACCOUNTS"* ]]
}

@test "codex-switch: routes named directories and keeps Claude registry separate" {
    mkdir -p "$TEST_TMP/project/subdir"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" codex-switch init
    [ "$status" -eq 0 ]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" codex-switch add customer
    [ "$status" -eq 0 ]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" codex-switch bind "$TEST_TMP/project" customer
    [ "$status" -eq 0 ]
    cd "$TEST_TMP/project/subdir"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" codex-switch status --json
    [ "$status" -eq 0 ]
    RESULT="$output" python3 -c 'import json,os;d=json.loads(os.environ["RESULT"]);assert d["account"]=="customer";assert d["source"]=="project"'
    [ ! -e "$AI_TOOLKIT_HOME/claude-switch.json" ]
}

@test "codex-switch: toolkit preserves native failure and signal exit codes" {
    mkdir -p "$TEST_TMP/bin"
    printf '#!/bin/sh\nif [ "$1" = "exit" ]; then exit 23; fi\nkill -TERM "$$"\n' > "$TEST_TMP/bin/codex"
    chmod +x "$TEST_TMP/bin/codex"
    export PATH="$TEST_TMP/bin:$PATH"
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" codex-switch init
    [ "$status" -eq 0 ]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" codex-switch run -- exit
    [ "$status" -eq 23 ]
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" codex-switch run
    [ "$status" -eq 143 ]
}
