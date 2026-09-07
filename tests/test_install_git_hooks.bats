#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for scripts/install_git_hooks.py — the fallback pre-commit hook, and
# specifically its unresolved-merge-conflict gate.
#
# The gate used `git diff --cached -S'<<<<<<<' --name-only`, which is a
# pickaxe: it reports a blob whose *count* of the string changed, reads binary
# blobs, and does not anchor to a line. A committed WebM whose compressed bytes
# happened to contain `<<<<<<<` blocked every commit in the repo with
# "Unresolved merge conflicts found in staged files" and no file name.
#
# Assertions use POSIX `[ ]` and `grep -q`, never bare `[[ ]]`: macOS ships
# bash 3.2, where a failing bare `[[ ]]` inside a bats test is silently ignored
# and the suite goes green on a broken assertion.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
INSTALLER="$TOOLKIT_DIR/scripts/install_git_hooks.py"

# Builds a git repo with the hook installed and echoes its path.
# HOME is redirected into the fixture so the hook cannot reach the operator's
# real ~/.softspark/ai-toolkit/hooks/quality-check.sh and run their gates.
_fixture() {
    local root
    root="$(mktemp -d)"
    HOME="$root/home"
    mkdir -p "$HOME"
    git init -q "$root/repo"
    git -C "$root/repo" config user.email "test@example.com"
    git -C "$root/repo" config user.name "Test"
    python3 "$INSTALLER" "$root/repo" >/dev/null
    echo "$root/repo"
}

# Stages a first commit so the index has a HEAD to diff against.
_seed() {
    echo "seed" > "$1/seed.txt"
    git -C "$1" add seed.txt
    git -C "$1" -c core.hooksPath=/dev/null commit -qm "seed"
}

@test "installs an executable pre-commit hook" {
    repo="$(_fixture)"
    [ -x "$repo/.git/hooks/pre-commit" ]
}

@test "passes on a clean index" {
    repo="$(_fixture)"
    _seed "$repo"
    echo "hello" > "$repo/a.txt"
    git -C "$repo" add a.txt

    run env HOME="$HOME" bash -c "cd '$repo' && .git/hooks/pre-commit"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Pre-commit checks passed"
}

@test "blocks a staged text file holding conflict markers" {
    repo="$(_fixture)"
    _seed "$repo"
    printf 'a\n<<<<<<< HEAD\nb\n=======\nc\n>>>>>>> other\n' > "$repo/merged.txt"
    git -C "$repo" add merged.txt

    run env HOME="$HOME" bash -c "cd '$repo' && .git/hooks/pre-commit"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Unresolved merge conflicts"
}

@test "names the conflicted file so the alarm is actionable" {
    repo="$(_fixture)"
    _seed "$repo"
    printf 'a\n<<<<<<< HEAD\nb\n=======\nc\n>>>>>>> other\n' > "$repo/merged.txt"
    git -C "$repo" add merged.txt

    run env HOME="$HOME" bash -c "cd '$repo' && .git/hooks/pre-commit"
    echo "$output" | grep -q "merged.txt"
}

# Regression: a binary blob whose bytes contain the marker is not a conflict.
@test "ignores conflict-marker bytes inside a binary blob" {
    repo="$(_fixture)"
    _seed "$repo"
    printf '\000\001\002ftypwebm\000<<<<<<<\000>>>>>>>\000' > "$repo/media.webm"
    git -C "$repo" add media.webm

    run env HOME="$HOME" bash -c "cd '$repo' && .git/hooks/pre-commit"
    [ "$status" -eq 0 ]
}

# Regression: pickaxe -S fires on any change in occurrence count, so deleting a
# marker read as "conflict present" just as loudly as adding one.
@test "ignores a commit that removes conflict markers" {
    repo="$(_fixture)"
    printf 'a\n<<<<<<< HEAD\nb\n' > "$repo/merged.txt"
    git -C "$repo" add merged.txt
    git -C "$repo" -c core.hooksPath=/dev/null commit -qm "seed with markers"

    printf 'a\nb\n' > "$repo/merged.txt"
    git -C "$repo" add merged.txt

    run env HOME="$HOME" bash -c "cd '$repo' && .git/hooks/pre-commit"
    [ "$status" -eq 0 ]
}

# A marker only counts at the start of a line; prose about markers does not.
@test "ignores marker text that is not line-anchored" {
    repo="$(_fixture)"
    _seed "$repo"
    printf 'Resolve the <<<<<<< marker before committing.\n' > "$repo/docs.md"
    git -C "$repo" add docs.md

    run env HOME="$HOME" bash -c "cd '$repo' && .git/hooks/pre-commit"
    [ "$status" -eq 0 ]
}
