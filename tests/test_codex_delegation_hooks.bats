#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

setup() {
    TOOLKIT_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    HOOKS_DIR="$TOOLKIT_ROOT/app/hooks"
    export HOME="$BATS_TEST_TMPDIR/home"
    export CLAUDE_PROJECT_DIR="$BATS_TEST_TMPDIR/project"
    export AI_TOOLKIT_DIR="$BATS_TEST_TMPDIR/toolkit"
    export TOOLKIT_HOOK_PROFILE="standard"
    unset CODEX_THREAD_ID CLAUDE_CONFIG_DIR AI_TOOLKIT_HOOK_FORMAT
    unset AI_TOOLKIT_HOOK_VERBOSE AI_TOOLKIT_HOOK_QUIET AI_TOOLKIT_DISABLED_HOOKS
    mkdir -p "$HOME/.claude/plugins/cache/codex/agents" "$CLAUDE_PROJECT_DIR" "$AI_TOOLKIT_DIR/scripts"
    # Only detection is under test: omit session state/version helpers so no
    # network probe or write outside this test's isolated directory can occur.
    cp "$TOOLKIT_ROOT/scripts/claude_codex_capability.py" "$AI_TOOLKIT_DIR/scripts/"
    touch "$HOME/.claude/plugins/cache/codex/agents/codex-rescue.md"
    jq -n --arg path "$HOME/.claude/plugins/cache/codex" \
        '{version:2,plugins:{"codex@openai-codex":[{scope:"user",installPath:$path}]}}' \
        > "$HOME/.claude/plugins/installed_plugins.json"
    printf '%s\n' '{"enabledPlugins":{"codex@openai-codex":true}}' > "$HOME/.claude/settings.json"
}

run_session_start() {
    local payload
    payload="$(jq -nc --arg cwd "$CLAUDE_PROJECT_DIR" '{hook_event_name:"SessionStart",cwd:$cwd,source:"startup"}')"
    run bash -c 'printf "%s" "$1" | bash "$2"' _ "$payload" "$HOOKS_DIR/session-start.sh"
}

run_subagent_start() {
    local payload
    payload="$(jq -nc --arg agent "$1" '{agent_type:$agent,hook_event_name:"SubagentStart"}')"
    run bash -c 'printf "%s" "$1" | bash "$2"' _ "$payload" "$HOOKS_DIR/subagent-start.sh"
}

@test "Claude SessionStart emits installed Codex hint at normal verbosity" {
    run_session_start
    [ "$status" -eq 0 ]
    [[ "$output" == *"local metadata indicates"* ]]
    [[ "$output" == *"callable in the current Claude agent catalog"* ]]
    [[ "$output" == *"model-routing-patterns"* ]]
    [[ "$output" != *"MANDATORY:"* ]]
}

@test "Claude SessionStart preserves native selection when plugin disabled locally" {
    mkdir -p "$CLAUDE_PROJECT_DIR/.claude"
    printf '%s\n' '{"enabledPlugins":{"codex@openai-codex":false}}' > "$CLAUDE_PROJECT_DIR/.claude/settings.local.json"
    run_session_start
    [ "$status" -eq 0 ]
    [[ "$output" == *"Use available native agents and the current model selection"* ]]
    [[ "$output" != *"local metadata indicates"* ]]
}

@test "deployed SessionStart uses adjacent helper with an older toolkit package" {
    mkdir -p "$BATS_TEST_TMPDIR/deployed/hooks" "$BATS_TEST_TMPDIR/deployed/scripts" "$BATS_TEST_TMPDIR/older-package"
    cp "$HOOKS_DIR/session-start.sh" "$HOOKS_DIR/_locate-toolkit.sh" \
        "$HOOKS_DIR/_session-paths.sh" "$HOOKS_DIR/_hook-io.sh" "$BATS_TEST_TMPDIR/deployed/hooks/"
    cp "$TOOLKIT_ROOT/scripts/claude_codex_capability.py" "$BATS_TEST_TMPDIR/deployed/scripts/"
    HOOKS_DIR="$BATS_TEST_TMPDIR/deployed/hooks"
    export AI_TOOLKIT_DIR="$BATS_TEST_TMPDIR/older-package"
    run_session_start
    [ "$status" -eq 0 ]
    [[ "$output" == *"model-routing-patterns"* ]]
}

@test "Claude SessionStart tolerates absent and malformed plugin metadata" {
    mv "$HOME/.claude/plugins/installed_plugins.json" "$HOME/registry-backup.json"
    run_session_start
    [ "$status" -eq 0 ]
    [[ "$output" == *"Codex delegation is not confirmed"* ]]
    printf '%s\n' '{invalid' > "$HOME/.claude/plugins/installed_plugins.json"
    run_session_start
    [ "$status" -eq 0 ]
    [[ "$output" == *"Codex delegation is not confirmed"* ]]
}

@test "Claude SessionStart hint respects quiet and minimal profiles" {
    export AI_TOOLKIT_HOOK_QUIET=1
    run_session_start
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    unset AI_TOOLKIT_HOOK_QUIET
    export TOOLKIT_HOOK_PROFILE=minimal
    run_session_start
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "shared SessionStart does not inject Claude routes into native editors" {
    export AI_TOOLKIT_HOOK_FORMAT=json
    run_session_start
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    unset AI_TOOLKIT_HOOK_FORMAT
    export CODEX_THREAD_ID=codex-native
    run_session_start
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    unset CODEX_THREAD_ID CLAUDE_PROJECT_DIR
    run_session_start
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "Codex forwarding wrapper keeps one-call contract" {
    run_subagent_start "codex:codex-rescue"
    [ "$status" -eq 0 ]
    [[ "$output" == *"one-call task forwarding contract"* ]]
    [[ "$output" != *"Read only the necessary files first"* ]]
}

@test "ordinary and similarly named agents retain research reminder" {
    for agent in "security-auditor" "codex-rescue" "other:codex-rescue"; do
        run_subagent_start "$agent"
        [ "$status" -eq 0 ]
        [[ "$output" == *"Read only the necessary files first"* ]]
    done
}

@test "native Codex does not receive forwarding exception" {
    export CODEX_THREAD_ID=codex-native
    run_subagent_start "codex:codex-rescue"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Read only the necessary files first"* ]]
}

@test "forwarding exception respects quiet and minimal hook profiles" {
    export AI_TOOLKIT_HOOK_QUIET=1
    run_subagent_start "codex:codex-rescue"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    unset AI_TOOLKIT_HOOK_QUIET
    export TOOLKIT_HOOK_PROFILE=minimal
    run_subagent_start "codex:codex-rescue"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}
