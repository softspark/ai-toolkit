#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    export TOOLKIT_HOOK_PROFILE=standard
    export AI_TOOLKIT_HOOK_FORMAT=json
    export AI_TOOLKIT_SEARCH_FIRST=off
    unset AI_TOOLKIT_DISABLED_HOOKS AI_TOOLKIT_HOOK_QUIET CLAUDE_SKIP_SEARCH_FIRST
    HOOKS="${HOOKS_DIR_OVERRIDE:-$BATS_TEST_DIRNAME/../app/hooks}"
}

teardown() {
    rm -rf "$TEST_TMP"
}

assert_intent() {
    local input context
    input="$(jq -cn --arg prompt "$1" '{prompt:$prompt,session_id:"intent-test"}')"
    run bash -c 'printf "%s" "$1" | bash "$2/user-prompt-submit.sh"' _ "$input" "$HOOKS"
    [ "$status" -eq 0 ]
    context="$(printf '%s' "$output" | jq -r '.hookSpecificOutput.additionalContext')"
    case "$2" in
        architecture) [[ "$context" == *"task looks architectural"* ]] ;;
        debug) [[ "$context" == *"debugging request detected"* ]] ;;
        none) [[ "$context" == *"apply KB-first research"* ]] ;;
        *) return 1 ;;
    esac
}

@test "prompt intent: Polish architecture request" {
    assert_intent "Zaprojektuj architekturę nowej usługi" architecture
}

@test "prompt intent: uppercase Polish debugging request" {
    assert_intent "ZNAJDŹ PRZYCZYNĘ BŁĘDU LOGOWANIA" debug
}

@test "prompt intent: Polish debugging without diacritics" {
    assert_intent "napraw blad logowania" debug
}

@test "prompt intent: ladybug is not a debugging request" {
    assert_intent "The ladybug is red" none
}

@test "prompt intent: designer is not an architecture request" {
    assert_intent "Write a poem about a designer" none
}

@test "prompt intent: retains English architecture and debug priority" {
    assert_intent "design a migration strategy" architecture
    assert_intent "debug this error in auth" debug
    assert_intent "design rollback for this outage" architecture
}

@test "prompt intent: ignores closed Markdown code fence" {
    assert_intent $'Count words in this quotation:\n```text\ndesign error debug\n```' none
}

@test "prompt intent: retains instruction outside quoted code" {
    assert_intent $'debug the error shown here:\n```text\nmigration deploy refactor\n```' debug
}

@test "prompt intent: ignores blockquote lines" {
    assert_intent $'Count words in this quotation:\n> design error debug' none
}

@test "prompt intent: unclosed fence does not become an instruction" {
    assert_intent $'Count words in this block:\n~~~text\narchitecture migration error' none
    assert_intent $'debug this output:\n```text\ndeploy migration' debug
}

@test "prompt intent: ignores notification text and does not arm search" {
    export AI_TOOLKIT_SEARCH_FIRST=strict
    assert_intent '<task-notification>error in background task</task-notification>' none
    [ ! -f "$HOME/.softspark/ai-toolkit/state/search-required-intent-test.flag" ]
}

@test "prompt intent: a user question about a notification remains debugging" {
    export AI_TOOLKIT_SEARCH_FIRST=strict
    assert_intent "the task notification said the build failed, where is that handled?" debug
    [ -f "$HOME/.softspark/ai-toolkit/state/search-required-intent-test.flag" ]
}

@test "prompt intent: standalone path carries no task category" {
    assert_intent "/tmp/debug-report.txt" none
}

@test "prompt intent: balanced quotations and inline code are treated as data" {
    assert_intent 'Count words in "design a migration" and `error debug`' none
}

@test "prompt intent: apostrophes preserve debugging intent" {
    assert_intent "don't ignore this error" debug
}

@test "prompt intent: one-word explicit debugging request is retained" {
    assert_intent "debug" debug
}

@test "prompt intent: minimal profile stays silent" {
    export TOOLKIT_HOOK_PROFILE=minimal
    input="$(jq -cn '{prompt:"Zaprojektuj architekturę nowej usługi"}')"
    run bash -c 'printf "%s" "$1" | bash "$2/user-prompt-submit.sh"' _ "$input" "$HOOKS"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "prompt intent: ignores injected Python search paths" {
    mkdir -p "$TEST_TMP/python-path"
    printf '%s\n' 'raise RuntimeError("poisoned stdlib shadow")' > "$TEST_TMP/python-path/re.py"
    export PYTHONPATH="$TEST_TMP/python-path"
    assert_intent "debug this error in auth" debug
}

@test "prompt intent: helper failure keeps valid generic output" {
    mkdir -p "$TEST_TMP/bin"
    printf '%s\n' '#!/usr/bin/env bash' 'exit 1' > "$TEST_TMP/bin/python3"
    chmod +x "$TEST_TMP/bin/python3"
    export PATH="$TEST_TMP/bin:$PATH"
    assert_intent "debug this error in auth" none
}

@test "prompt intent: terminal punctuation preserves standalone intent" {
    assert_intent "debug." debug
    assert_intent "napraw." debug
    assert_intent "wdróż." architecture
}

@test "prompt intent: ignores explicit inline pasted-text wrappers" {
    assert_intent "Count words: <pasted_text>design migration</pasted_text>" none
    assert_intent "debug this: <quoted_text>deploy migration</quoted_text>" debug
    assert_intent $'Count words: <untrusted_text>\ndesign migration\n</untrusted_text>' none
}

@test "prompt intent: matches complete inline-code delimiter runs" {
    assert_intent 'Count words: ``design migration``' none
    assert_intent 'debug this ``deploy `migration` code``' debug
}

@test "prompt intent: retains known slash command words" {
    assert_intent "/debug" debug
    assert_intent "/debug this error" debug
    assert_intent "/refactor" architecture
    assert_intent "/tmp/debug-report.txt" none
}
