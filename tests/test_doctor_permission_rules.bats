#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for doctor check 13 (Permission Rules): allow rules whose wildcard
# pre-approves code execution, network egress, or destruction are flagged;
# exact rules and read-only wildcards are not. Doctor never edits them.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP/home"
    export SOFTSPARK_HOME="$HOME/.softspark"
    PROJECT="$TEST_TMP/project"
    mkdir -p "$HOME/.claude" "$PROJECT/.claude"
    cd "$PROJECT"
}

teardown() {
    rm -rf "$TEST_TMP"
}

_local_allow() {
    python3 -c "
import json, sys
rules = sys.argv[1:]
json.dump({'permissions': {'allow': rules, 'deny': ['Bash(rm -rf /)']}}, open('.claude/settings.local.json', 'w'))
" "$@"
}

@test "doctor permission rules: skips when no allow lists exist" {
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q '## 13. Permission Rules'
    echo "$output" | grep -q 'SKIP: no permissions.allow lists'
}

@test "doctor permission rules: flags wildcards on interpreters, runners, installs, gh api, fetchers, git fetch" {
    _local_allow \
        'Bash(npx bats:*)' \
        'Bash(npm run *)' \
        'Bash(npm install:*)' \
        'Bash(gh api *)' \
        'Bash(curl *)' \
        'Bash(git fetch *)' \
        'Bash(python3 *)' \
        'Bash(rm *)' \
        'Bash(find . -exec *)'
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q "WARN: .claude/settings.local.json: allow rule Bash(npx bats:\*) - wildcard on interpreter/executor 'npx'"
    echo "$output" | grep -q "allow rule Bash(npm run \*) - wildcard on task runner 'npm run'"
    echo "$output" | grep -q "allow rule Bash(npm install:\*) - wildcard on 'npm install' (package lifecycle scripts"
    echo "$output" | grep -q "allow rule Bash(gh api \*) - wildcard on 'gh api' (also matches POST/DELETE"
    echo "$output" | grep -q "allow rule Bash(curl \*) - wildcard on 'curl'"
    echo "$output" | grep -q "allow rule Bash(git fetch \*) - wildcard on 'git fetch'"
    echo "$output" | grep -q "allow rule Bash(python3 \*) - wildcard on interpreter/executor 'python3'"
    echo "$output" | grep -q "allow rule Bash(rm \*) - wildcard on 'rm' (destructive)"
    echo "$output" | grep -q "allow rule Bash(find . -exec \*) - find with -exec/-delete"
    echo "$output" | grep -q 'INFO: doctor never edits permissions'
}

@test "doctor permission rules: exact rules and read-only wildcards pass" {
    _local_allow \
        'Bash(python3 scripts/validate.py --strict)' \
        'Bash(git status *)' \
        'Bash(git log --oneline -20)' \
        'Bash(ls *)' \
        'Bash(ai-toolkit:*)' \
        'mcp__rag-mcp__smart_query' \
        'WebFetch(domain:docs.claude.com)' \
        'Read(//tmp/**)'
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q 'OK: allow rules pre-approve nothing beyond read-only commands'
    ! echo "$output" | grep -q 'WARN: .claude/settings.local.json'
}

@test "doctor permission rules: reads user-scope settings too and never flags deny rules" {
    printf '{"permissions": {"allow": ["Bash(bash *)"], "deny": ["Bash(curl *)"]}}\n' > "$HOME/.claude/settings.json"
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q "WARN: ~/.claude/settings.json: allow rule Bash(bash \*) - wildcard on interpreter/executor 'bash'"
    ! echo "$output" | grep -q 'allow rule Bash(curl'
}

@test "doctor permission rules: a bare Bash wildcard is called out" {
    _local_allow 'Bash(*)'
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q 'allow rule Bash(\*) - matches every Bash command'
}

@test "doctor permission rules: --fix leaves the settings file byte-identical" {
    _local_allow 'Bash(npm run *)' 'Bash(gh api *)'
    before="$(cat .claude/settings.local.json)"
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    [ "$before" = "$(cat .claude/settings.local.json)" ]
}
