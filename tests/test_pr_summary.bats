#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../app/skills/pr/scripts/pr-summary.py"
    export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
    git init --quiet --initial-branch=develop "$BATS_TEST_TMPDIR/repository"
    cd "$BATS_TEST_TMPDIR/repository" || return
    git config user.name "PR Summary Test"
    git config user.email "pr-summary@example.invalid"
    git config commit.gpgsign false
    git config core.hooksPath /dev/null
    git commit --quiet --allow-empty -m "chore: initial fixture"
}

commit_file() {
    local filename="$1" message="$2"
    mkdir -p "$(dirname "$filename")"
    printf '%s\n' "fixture content" > "$filename"
    git add -- "$filename"
    git commit --quiet -m "$message"
}

@test "pr-summary: help succeeds outside a repository without parsing a base" {
    cd "$BATS_TEST_TMPDIR"
    run python3 "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"usage:"* ]]
    [[ "$output" == *"base_branch"* ]]
    [[ "$output" != *'"error"'* ]]
}

@test "pr-summary: explicit develop base preserves the summary fields" {
    git switch --quiet -c feature
    commit_file "feature.txt" "feat(api): expose endpoint"
    run python3 "$SCRIPT" develop
    [ "$status" -eq 0 ]
    python3 -c '
import json, sys
d = json.loads(sys.argv[1])
assert d["base"] == "develop"
assert d["total_commits"] == 1 and d["files_changed"] == 1
assert d["title_suggestion"] == "feat(api): expose endpoint"
assert d["groups"] == {"Features": ["expose endpoint"]}
assert d["commits"][0]["scope"] == "api"
assert not d["has_breaking"] and not d["has_tests"]
' "$output"
}

@test "pr-summary: default prefers cached remote develop over local main" {
    git update-ref refs/remotes/origin/develop HEAD
    git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/develop
    git switch --quiet -c feature
    commit_file "feature.txt" "feat: feature"
    git branch main
    run python3 "$SCRIPT"
    [ "$status" -eq 0 ]
    python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["base"] == "origin/HEAD" and d["total_commits"] == 1' "$output"
}

@test "pr-summary: default retains local main fallback" {
    git branch main
    commit_file "feature.txt" "fix: feature"
    run python3 "$SCRIPT"
    [ "$status" -eq 0 ]
    python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["base"] == "main" and d["total_commits"] == 1' "$output"
}

@test "pr-summary: missing default explains how to supply the target" {
    run python3 "$SCRIPT"
    [ "$status" -eq 1 ]
    python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert "pr-summary.py develop" in d["error"]' "$output"
}

@test "pr-summary: invalid ref is an error instead of an empty range" {
    run python3 "$SCRIPT" missing-branch
    [ "$status" -eq 1 ]
    python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert "missing-branch" in d["error"] and "total_commits" not in d' "$output"
}

@test "pr-summary: commit-ish refs resolve literally and option injection is rejected" {
    commit_file "feature.txt" "feat: feature"
    run python3 "$SCRIPT" "HEAD~1"
    [ "$status" -eq 0 ]
    python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["base"] == "HEAD~1" and d["total_commits"] == 1' "$output"
    run python3 "$SCRIPT" -- "--output=INJECTED"
    [ "$status" -eq 1 ]
    [ ! -e INJECTED ]
    run python3 "$SCRIPT" 'develop --output=INJECTED'
    [ "$status" -eq 1 ]
    [ ! -e INJECTED ]
    # shellcheck disable=SC2016 # Deliberately pass shell syntax as literal input.
    run python3 "$SCRIPT" 'develop; $(touch INJECTED)'
    [ "$status" -eq 1 ]
    [ ! -e INJECTED ]
}

@test "pr-summary: legitimate empty range returns zero counts and an empty title" {
    run python3 "$SCRIPT" develop
    [ "$status" -eq 0 ]
    python3 -c '
import json, sys
d = json.loads(sys.argv[1])
assert "error" not in d and d["total_commits"] == 0
assert d["commits"] == [] and d["groups"] == {} and d["summary_bullets"] == []
assert d["title_suggestion"] == "" and d["files_changed"] == 0
assert d["test_files_changed"] == 0 and not d["has_tests"]
assert d["breaking_changes"] == [] and not d["has_breaking"]
' "$output"
}

@test "pr-summary: breaking subjects and bodies survive former separator text" {
    git switch --quiet -c feature
    commit_file "feature.txt" $'feat(api)!: replace endpoint\n\nBREAKING CHANGE: clients need ---COMMIT_SEP--- v2\n\nBREAKING-CHANGE: old route removed'
    run python3 "$SCRIPT" develop
    [ "$status" -eq 0 ]
    python3 -c '
import json, sys
d = json.loads(sys.argv[1])
assert d["has_breaking"] and d["commits"][0]["breaking"]
assert d["breaking_changes"] == ["clients need ---COMMIT_SEP--- v2", "old route removed", "replace endpoint"]
' "$output"
}

@test "pr-summary: NUL names count paths with spaces pipes and newlines correctly" {
    git switch --quiet -c feature
    commit_file "docs/space | name.txt" "docs: document behavior"
    commit_file $'nested dir/line\nunit.test.py' "test: cover behavior"
    commit_file "nested dir/unit_test.py" "test: expand coverage"
    run python3 "$SCRIPT" develop
    [ "$status" -eq 0 ]
    python3 -c '
import json, sys
d = json.loads(sys.argv[1])
assert d["files_changed"] == 3 and d["test_files_changed"] == 2 and d["has_tests"]
assert d["total_commits"] == 3 and d["title_suggestion"] == "test: expand coverage"
assert "Tests: 2 changes" in d["summary_bullets"]
' "$output"
}

@test "pr-summary: unrelated histories report the Git diff failure" {
    git checkout --quiet --orphan unrelated
    git commit --quiet --allow-empty -m "feat: unrelated history"
    run python3 "$SCRIPT" develop
    [ "$status" -eq 1 ]
    python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert "Git command failed" in d["error"]' "$output"
}

@test "pr-summary: unborn HEAD reports the missing commit" {
    git checkout --quiet --orphan unborn
    run python3 "$SCRIPT" develop
    [ "$status" -eq 1 ]
    python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert "HEAD has no commit" in d["error"]' "$output"
}

@test "pr-summary: non-repository failures are actionable JSON with nonzero status" {
    cd "$BATS_TEST_TMPDIR"
    run python3 "$SCRIPT" develop
    [ "$status" -eq 1 ]
    python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert "not a git repository" in d["error"]' "$output"
}
