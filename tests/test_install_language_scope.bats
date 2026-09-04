#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for install_steps/skill_scope.py: language knowledge skills are turned
# off (skillOverrides) for languages no registered project uses, tracked in
# state.json, restored when a project brings the language back, and left alone
# entirely under --language-skills all.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TMP_HOME="$(mktemp -d)"
    export HOME="$TMP_HOME"
    export SOFTSPARK_HOME="$TMP_HOME/.softspark"
    PY_PROJECT="$(mktemp -d)"
    touch "$PY_PROJECT/pyproject.toml"
}

teardown() {
    rm -rf "$TMP_HOME" "$PY_PROJECT" "${RS_PROJECT:-}"
}

_overrides() {
    python3 -c "
import json, os, sys
p = os.path.join(os.environ['HOME'], '.claude', 'settings.json')
d = json.load(open(p)) if os.path.exists(p) else {}
print(json.dumps(d.get('skillOverrides', {}), sort_keys=True))"
}

_state() {
    python3 -c "
import json, os
p = os.path.join(os.environ['SOFTSPARK_HOME'], 'ai-toolkit', 'state.json')
d = json.load(open(p)) if os.path.exists(p) else {}
print(d.get('language_skill_scope'), len(d.get('managed_skill_overrides', [])))"
}

@test "language scope: global install with no registered project disables nothing" {
    run python3 "$TOOLKIT_DIR/scripts/install.py"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Skipped: language skill scoping (no registered project on disk'
    [ "$(_overrides)" = "{}" ]
}

@test "language scope: local install in a python project turns off other language skills only" {
    cd "$PY_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Disabled: .* language skill(s) outside your detected stacks'
    overrides="$(_overrides)"
    echo "$overrides" | grep -q '"rust-rules": "off"'
    echo "$overrides" | grep -q '"typescript-patterns": "off"'
    ! echo "$overrides" | grep -q 'python-rules'
    # flutter-patterns has no app/rules/flutter, so it is not a language skill and is untouched
    ! echo "$overrides" | grep -q 'flutter-patterns'
    [ "$(_state)" = "detected $(echo "$overrides" | tr ',' '\n' | grep -c '"off"')" ]
}

@test "language scope: a new project in another language restores its skills on the next run" {
    cd "$PY_PROJECT"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local >/dev/null 2>&1
    echo "$(_overrides)" | grep -q '"rust-rules": "off"'

    RS_PROJECT="$(mktemp -d)"
    touch "$RS_PROJECT/Cargo.toml"
    cd "$RS_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Restored: 2 language skill(s) (rust-patterns, rust-rules)'
    ! echo "$(_overrides)" | grep -q 'rust-'
    echo "$(_overrides)" | grep -q '"golang-rules": "off"'
}

@test "language scope: a user's own override is never adopted or removed" {
    mkdir -p "$HOME/.claude"
    printf '{"skillOverrides": {"golang-rules": "off", "rust-rules": "off"}}\n' > "$HOME/.claude/settings.json"
    cd "$PY_PROJECT"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local >/dev/null 2>&1

    RS_PROJECT="$(mktemp -d)"
    touch "$RS_PROJECT/Cargo.toml"
    cd "$RS_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local
    # rust is now detected, but rust-rules was the user's entry: it stays off
    echo "$(_overrides)" | grep -q '"rust-rules": "off"'
    echo "$(_overrides)" | grep -q '"golang-rules": "off"'
    ! echo "$output" | grep -q 'Restored: .*rust-rules'
}

@test "language scope: --language-skills all restores managed entries and persists the choice" {
    cd "$PY_PROJECT"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local >/dev/null 2>&1
    run python3 "$TOOLKIT_DIR/scripts/install.py" --language-skills all
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Restored: '
    [ "$(_overrides)" = "{}" ]
    [ "$(_state)" = "all 0" ]

    # A later plain run must not prune again
    run python3 "$TOOLKIT_DIR/scripts/install.py"
    [ "$status" -eq 0 ]
    ! echo "$output" | grep -q 'Disabled: '
    [ "$(_overrides)" = "{}" ]
}

@test "language scope: --language-skills detected flips the persisted choice back" {
    cd "$PY_PROJECT"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --language-skills all >/dev/null 2>&1
    [ "$(_overrides)" = "{}" ]
    run python3 "$TOOLKIT_DIR/scripts/install.py" --language-skills detected
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Disabled: '
    echo "$(_overrides)" | grep -q '"rust-rules": "off"'
}

@test "language scope: dry-run reports but writes nothing" {
    cd "$PY_PROJECT"
    python3 "$TOOLKIT_DIR/scripts/install.py" --local --language-skills all >/dev/null 2>&1
    run python3 "$TOOLKIT_DIR/scripts/install.py" --language-skills detected --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Would disable: skill rust-rules (skillOverrides)'
    [ "$(_overrides)" = "{}" ]
    [ "$(_state)" = "all 0" ]
}

@test "language scope: --skip skills leaves overrides untouched" {
    cd "$PY_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --skip skills
    [ "$status" -eq 0 ]
    ! echo "$output" | grep -q 'Disabled: '
    [ "$(_overrides)" = "{}" ]
}

@test "language scope: rejects an unknown --language-skills value" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" --language-skills sometimes
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Unknown --language-skills value: 'sometimes' (valid: all, detected)"
}
