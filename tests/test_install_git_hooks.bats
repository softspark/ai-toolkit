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

# Builds a git repo with the hook installed and sets $repo to its path.
# HOME is redirected into the fixture so the hook cannot reach the operator's
# real ~/.softspark/ai-toolkit/hooks/quality-check.sh and run their gates.
# Call it directly, never as `repo="$(_fixture)"`: a command substitution runs
# in a subshell and the HOME redirect would be lost with it.
_fixture() {
    FIXTURE_ROOT="$(mktemp -d)"
    HOME="$FIXTURE_ROOT/home"
    export HOME
    mkdir -p "$HOME"
    repo="$FIXTURE_ROOT/repo"
    git init -q "$repo"
    git -C "$repo" config user.email "test@example.com"
    git -C "$repo" config user.name "Test"
    python3 "$INSTALLER" "$repo" >/dev/null
}

teardown() {
    if [ -n "${FIXTURE_ROOT:-}" ]; then
        rm -rf "$FIXTURE_ROOT"
    fi
}

# Installs a stand-in for the global quality-check.sh that exits with $1.
_stub_quality_check() {
    mkdir -p "$HOME/.softspark/ai-toolkit/hooks"
    printf '#!/usr/bin/env bash\necho "stub quality-check: $*"\nexit %s\n' "$1" \
        > "$HOME/.softspark/ai-toolkit/hooks/quality-check.sh"
    chmod +x "$HOME/.softspark/ai-toolkit/hooks/quality-check.sh"
}

# Installs the real quality-check.sh (and what it sources) into the fixture HOME.
_install_real_quality_check() {
    mkdir -p "$HOME/.softspark/ai-toolkit/hooks"
    cp "$TOOLKIT_DIR/app/hooks/_profile-check.sh" "$TOOLKIT_DIR/app/hooks/quality-check.sh" \
        "$HOME/.softspark/ai-toolkit/hooks/"
}

# Runs the installed pre-commit hook inside the fixture repo.
_run_hook() {
    run env -u AI_TOOLKIT_DISABLED_HOOKS -u TOOLKIT_HOOK_PROFILE HOME="$HOME" \
        bash -c "cd '$repo' && .git/hooks/pre-commit"
}

# Stages a first commit so the index has a HEAD to diff against.
_seed() {
    echo "seed" > "$1/seed.txt"
    git -C "$1" add seed.txt
    git -C "$1" -c core.hooksPath=/dev/null commit -qm "seed"
}

@test "installs an executable pre-commit hook" {
    _fixture
    [ -x "$repo/.git/hooks/pre-commit" ]
}

@test "passes on a clean index when the quality check passes" {
    _fixture
    _seed "$repo"
    _stub_quality_check 0
    echo "hello" > "$repo/a.txt"
    git -C "$repo" add a.txt

    _run_hook
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Pre-commit checks passed"
}

@test "blocks a staged text file holding conflict markers" {
    _fixture
    _seed "$repo"
    printf 'a\n<<<<<<< HEAD\nb\n=======\nc\n>>>>>>> other\n' > "$repo/merged.txt"
    git -C "$repo" add merged.txt

    run env HOME="$HOME" bash -c "cd '$repo' && .git/hooks/pre-commit"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Unresolved merge conflicts"
}

@test "names the conflicted file so the alarm is actionable" {
    _fixture
    _seed "$repo"
    printf 'a\n<<<<<<< HEAD\nb\n=======\nc\n>>>>>>> other\n' > "$repo/merged.txt"
    git -C "$repo" add merged.txt

    run env HOME="$HOME" bash -c "cd '$repo' && .git/hooks/pre-commit"
    echo "$output" | grep -q "merged.txt"
}

# Regression: a binary blob whose bytes contain the marker is not a conflict.
@test "ignores conflict-marker bytes inside a binary blob" {
    _fixture
    _seed "$repo"
    printf '\000\001\002ftypwebm\000<<<<<<<\000>>>>>>>\000' > "$repo/media.webm"
    git -C "$repo" add media.webm

    run env HOME="$HOME" bash -c "cd '$repo' && .git/hooks/pre-commit"
    [ "$status" -eq 0 ]
}

# Regression: pickaxe -S fires on any change in occurrence count, so deleting a
# marker read as "conflict present" just as loudly as adding one.
@test "ignores a commit that removes conflict markers" {
    _fixture
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
    _fixture
    _seed "$repo"
    printf 'Resolve the <<<<<<< marker before committing.\n' > "$repo/docs.md"
    git -C "$repo" add docs.md

    run env HOME="$HOME" bash -c "cd '$repo' && .git/hooks/pre-commit"
    [ "$status" -eq 0 ]
}

# ── Quality check: a failed, crashed or skipped checker is never a pass ───────
#
# The hook called quality-check.sh without --blocking. That script is the
# advisory Stop hook: it pipes the linter into `head` and ends in `exit 0`, so a
# PHPStan worker that died on the host's 128M memory limit still ended in
# "Pre-commit checks passed" and the commit went through.

@test "reports skipped, not passed, when quality-check.sh is not installed" {
    _fixture
    _seed "$repo"

    _run_hook
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "quality-check: skipped"
    [ -z "$(echo "$output" | grep "Pre-commit checks passed")" ]
}

@test "invokes quality-check.sh in blocking mode" {
    _fixture
    _seed "$repo"
    _stub_quality_check 0

    _run_hook
    echo "$output" | grep -q "stub quality-check: --blocking"
}

@test "blocks the commit when the quality check fails" {
    _fixture
    _seed "$repo"
    _stub_quality_check 1

    _run_hook
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Linter or type checks failed"
    [ -z "$(echo "$output" | grep "Pre-commit checks passed")" ]
}

@test "blocks the commit on any other quality-check status" {
    _fixture
    _seed "$repo"
    _stub_quality_check 127

    _run_hook
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "exit 127"
}

@test "reports skipped, not passed, when the quality check could not run" {
    _fixture
    _seed "$repo"
    _stub_quality_check 3

    _run_hook
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "quality check skipped"
    [ -z "$(echo "$output" | grep "Pre-commit checks passed")" ]
}

# The observed failure: PHPStan crashed on the host memory limit and the commit
# went through. Real hook + real quality-check.sh, only PHPStan is a stub.
@test "end to end: a PHPStan worker crash blocks the commit" {
    _fixture
    _seed "$repo"
    _install_real_quality_check
    touch "$repo/composer.json"
    mkdir -p "$repo/vendor/bin"
    printf '#!/usr/bin/env bash\necho "Child process error (exit code 255): PHPStan process crashed because it reached configured PHP memory limit: 128M"\nexit 1\n' \
        > "$repo/vendor/bin/phpstan"
    chmod +x "$repo/vendor/bin/phpstan"

    _run_hook
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "PHPStan: FAILED (exit 1)"
    echo "$output" | grep -q "Child process error"
    [ -z "$(echo "$output" | grep "Pre-commit checks passed")" ]
}

@test "end to end: a clean PHPStan run is reported as passed" {
    _fixture
    _seed "$repo"
    _install_real_quality_check
    touch "$repo/composer.json"
    mkdir -p "$repo/vendor/bin"
    printf '#!/usr/bin/env bash\nexit 0\n' > "$repo/vendor/bin/phpstan"
    chmod +x "$repo/vendor/bin/phpstan"

    _run_hook
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "PHPStan: passed"
    echo "$output" | grep -q "Pre-commit checks passed"
}
