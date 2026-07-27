#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Retirement cleanup for the v4.16.x native tool-output filter.
#
# v4.16.0/v4.16.1 wrote files outside the npm package; v4.17.0 removed the
# feature, so install/update must reclaim them on machines that ran those
# releases. These tests reproduce that on-disk layout and cover the three
# cases that matter: present-and-removed, absent-and-silent, foreign-preserved.
#
# Assertion rules (both silently pass otherwise):
#   * never a bare `[[ ]]` — macOS bash 3.2 ignores a failing one at the end
#     of a test body;
#   * never a bare `! cmd` mid-test — `set -e` is defined to ignore the status
#     of a pipeline that begins with `!`, so the check evaporates.
# Use the assert_* / refute_* helpers below: they fail via `return 1` inside a
# simple command, which `set -e` does honour.
#
# Run with: bats tests/test_output_filter_retirement.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    export TEST_PROJECT; TEST_PROJECT="$(mktemp -d)"
    export TMP_HOME; TMP_HOME="$(mktemp -d)"
    export HOME="$TMP_HOME"
    DATA_DIR="$TMP_HOME/.softspark/ai-toolkit"
}

teardown() {
    rm -rf "$TEST_PROJECT" "$TMP_HOME"
}

assert_output_has() {
    if ! printf '%s\n' "$output" | grep -qF -- "$1"; then
        echo "MISSING from output: $1"
        return 1
    fi
}

refute_output_has() {
    if printf '%s\n' "$output" | grep -qF -- "$1"; then
        echo "UNEXPECTED in output: $1"
        return 1
    fi
}

assert_file_has() {
    if ! grep -qF -- "$2" "$1"; then
        echo "MISSING from $1: $2"
        return 1
    fi
}

refute_file_has() {
    if grep -qF -- "$2" "$1"; then
        echo "UNEXPECTED in $1: $2"
        return 1
    fi
}

# Recreate exactly what v4.16.x left behind under ~/.softspark/ai-toolkit/.
seed_global_leftovers() {
    python3 - "$DATA_DIR" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

data = Path(sys.argv[1])
hooks = data / "hooks"
scripts = data / "scripts"
hooks.mkdir(parents=True, exist_ok=True)
scripts.mkdir(parents=True, exist_ok=True)

(hooks / "filter-tool-output.sh").write_text(
    "#!/usr/bin/env bash\n"
    "# Claude PostToolUse adapter for the native tool-output filter.\n"
    "exit 0\n",
    encoding="utf-8",
)
(hooks / "output-filter-policy.json").write_text(
    json.dumps({"mode": "safe", "recovery": {"mode": "ephemeral"}}, indent=2) + "\n",
    encoding="utf-8",
)
(scripts / "output_filter_hook.py").write_text(
    '"""Lean process entry point for the Claude output-filter hook."""\n',
    encoding="utf-8",
)
(scripts / "output_filter_cli.py").write_text(
    '"""Manual and hook entry points for native tool-output filtering."""\n',
    encoding="utf-8",
)

package = scripts / "tool_output_filter"
(package / "profiles").mkdir(parents=True, exist_ok=True)
(package / "__init__.py").write_text(
    '"""Dependency-free post-execution tool-output filtering."""\n',
    encoding="utf-8",
)
for module in (
    "contracts.py", "engine.py", "hook_runtime.py", "input.py",
    "invariants.py", "policy.py", "recovery.py", "telemetry.py",
):
    (package / module).write_text("# stub\n", encoding="utf-8")
for module in ("__init__.py", "repeat_lines.py", "tap_success.py"):
    (package / "profiles" / module).write_text("# stub\n", encoding="utf-8")
cache = package / "__pycache__"
cache.mkdir(exist_ok=True)
(cache / "engine.cpython-313.pyc").write_bytes(b"\x00pyc")

repository = data / "sessions" / "repo-a"
repository.mkdir(parents=True, exist_ok=True)
repository.chmod(0o700)
session = repository / "output-filter" / hashlib.sha256(b"s").hexdigest()[:32]
session.mkdir(mode=0o700, parents=True, exist_ok=True)
(repository / "output-filter").chmod(0o700)
session.chmod(0o700)
for name, payload in (
    ("a" * 32 + ".json", '{"stdout": "captured command output"}'),
    (".circuit-state.json", "{}"),
    (".telemetry.jsonl", "{}\n"),
):
    artifact = session / name
    artifact.write_text(payload, encoding="utf-8")
    artifact.chmod(0o600)

print(session)
PY
}

# The stale PostToolUse entry, written WITHOUT "_source" — Claude Code rewrites
# settings.json and drops the tag, which is why a tag-based strip cannot see it.
seed_stale_settings_entry() {
    mkdir -p "$TMP_HOME/.claude"
    cat > "$TMP_HOME/.claude/settings.json" <<'JSON'
{
    "hooks": {
        "PostToolUse": [
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": "\"$HOME/.softspark/ai-toolkit/hooks/filter-tool-output.sh\""
                    }
                ]
            },
            {
                "matcher": "Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": "my-own-hook.sh"
                    }
                ]
            }
        ]
    },
    "permissions": {
        "allow": [
            "Bash"
        ]
    }
}
JSON
}

# ── present-and-removed ─────────────────────────────────────────────────────

@test "retirement: global install removes every v4.16.x output-filter leftover" {
    local session
    session="$(seed_global_leftovers)"

    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TMP_HOME" --dry-run
    [ "$status" -eq 0 ]
    assert_output_has "Would migrate: remove retired output-filter hooks/filter-tool-output.sh"
    assert_output_has "Would migrate: remove retired output-filter hooks/output-filter-policy.json"
    assert_output_has "Would migrate: remove retired output-filter scripts/output_filter_hook.py"
    assert_output_has "Would migrate: remove retired output-filter scripts/output_filter_cli.py"
    assert_output_has "Would migrate: remove retired output-filter scripts/tool_output_filter/"
    assert_output_has "Would migrate: remove retired output-filter sessions/*/output-filter/ (3 files)"
    # Dry run must not touch anything.
    [ -f "$DATA_DIR/hooks/filter-tool-output.sh" ]
    [ -f "$session/.telemetry.jsonl" ]

    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TMP_HOME"
    [ "$status" -eq 0 ]
    assert_output_has "Migrated: removed retired output-filter hooks/filter-tool-output.sh"
    assert_output_has "Migrated: removed retired output-filter hooks/output-filter-policy.json"
    assert_output_has "Migrated: removed retired output-filter scripts/output_filter_hook.py"
    assert_output_has "Migrated: removed retired output-filter scripts/output_filter_cli.py"
    assert_output_has "Migrated: removed retired output-filter scripts/tool_output_filter/"
    assert_output_has "Migrated: removed retired output-filter sessions/*/output-filter/ (3 files)"

    [ ! -e "$DATA_DIR/hooks/filter-tool-output.sh" ]
    [ ! -e "$DATA_DIR/hooks/output-filter-policy.json" ]
    [ ! -e "$DATA_DIR/scripts/output_filter_hook.py" ]
    [ ! -e "$DATA_DIR/scripts/output_filter_cli.py" ]
    [ ! -e "$DATA_DIR/scripts/tool_output_filter" ]
    [ ! -e "$DATA_DIR/sessions/repo-a/output-filter" ]
    # The repo session directory itself is user data and stays.
    [ -d "$DATA_DIR/sessions/repo-a" ]
    # Neighbouring hook runtime assets are untouched.
    [ -f "$DATA_DIR/scripts/session_state.py" ]
}

@test "retirement: install strips the stale untagged PostToolUse entry" {
    seed_global_leftovers >/dev/null
    seed_stale_settings_entry
    assert_file_has "$TMP_HOME/.claude/settings.json" "filter-tool-output.sh"

    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TMP_HOME"
    [ "$status" -eq 0 ]

    refute_file_has "$TMP_HOME/.claude/settings.json" "filter-tool-output.sh"
    assert_file_has "$TMP_HOME/.claude/settings.json" "my-own-hook.sh"
    assert_file_has "$TMP_HOME/.claude/settings.json" '"permissions"'
}

@test "retirement: project install removes the owner-marked project policy" {
    mkdir -p "$TEST_PROJECT/.claude"
    printf '%s\n' '{"mode": "safe"}' \
        > "$TEST_PROJECT/.claude/ai-toolkit-output-filter.json"
    printf 'ai-toolkit-output-filter-policy-v1\n' \
        > "$TEST_PROJECT/.claude/.ai-toolkit-output-filter.owner"

    run bash -c "cd '$TEST_PROJECT' && python3 '$TOOLKIT_DIR/scripts/install.py' --local --dry-run"
    [ "$status" -eq 0 ]
    assert_output_has "Would migrate: remove retired .claude/ai-toolkit-output-filter.json"
    [ -f "$TEST_PROJECT/.claude/ai-toolkit-output-filter.json" ]

    run bash -c "cd '$TEST_PROJECT' && python3 '$TOOLKIT_DIR/scripts/install.py' --local"
    [ "$status" -eq 0 ]
    assert_output_has "Migrated: removed retired .claude/ai-toolkit-output-filter.json"
    [ ! -e "$TEST_PROJECT/.claude/ai-toolkit-output-filter.json" ]
    [ ! -e "$TEST_PROJECT/.claude/.ai-toolkit-output-filter.owner" ]
}

# ── absent-and-silent ──────────────────────────────────────────────────────

@test "retirement: install is silent when no output-filter leftovers exist" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TMP_HOME" --dry-run
    [ "$status" -eq 0 ]
    refute_output_has "output-filter"

    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TMP_HOME"
    [ "$status" -eq 0 ]
    refute_output_has "output-filter"

    run bash -c "cd '$TEST_PROJECT' && python3 '$TOOLKIT_DIR/scripts/install.py' --local"
    [ "$status" -eq 0 ]
    refute_output_has "output-filter"
}

@test "retirement: a second install run reports nothing and changes nothing" {
    seed_global_leftovers >/dev/null

    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TMP_HOME"
    [ "$status" -eq 0 ]
    assert_output_has "Migrated: removed retired output-filter"

    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TMP_HOME"
    [ "$status" -eq 0 ]
    refute_output_has "output-filter"

    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TMP_HOME" --dry-run
    [ "$status" -eq 0 ]
    refute_output_has "output-filter"
}

# ── foreign-file-preserved ─────────────────────────────────────────────────

@test "retirement: foreign files and hand-edited copies survive the cleanup" {
    local session
    session="$(seed_global_leftovers)"
    # Hand-edited hook script: the shipped marker is gone, so it is not ours.
    printf '#!/usr/bin/env bash\n# my own replacement\nexit 0\n' \
        > "$DATA_DIR/hooks/filter-tool-output.sh"
    # A policy file that is no longer a JSON object fails the ownership test.
    printf 'not json\n' > "$DATA_DIR/hooks/output-filter-policy.json"
    # Unrecognized file inside the runtime package keeps the directory.
    printf 'do not delete\n' > "$DATA_DIR/scripts/tool_output_filter/my_notes.txt"
    # Unrecognized file inside a recovery session keeps the session directory.
    printf 'user data\n' > "$session/keep.txt"

    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TMP_HOME"
    [ "$status" -eq 0 ]
    assert_output_has "Warning: output-filter retirement removed scripts/tool_output_filter/ modules but kept the directory"
    refute_output_has "Migrated: removed retired output-filter hooks/filter-tool-output.sh"
    refute_output_has "Migrated: removed retired output-filter hooks/output-filter-policy.json"

    assert_file_has "$DATA_DIR/hooks/filter-tool-output.sh" "my own replacement"
    assert_file_has "$DATA_DIR/hooks/output-filter-policy.json" "not json"
    assert_file_has "$DATA_DIR/scripts/tool_output_filter/my_notes.txt" "do not delete"
    [ ! -e "$DATA_DIR/scripts/tool_output_filter/engine.py" ]
    [ ! -e "$DATA_DIR/scripts/tool_output_filter/__init__.py" ]
    [ ! -e "$DATA_DIR/scripts/tool_output_filter/profiles" ]
    assert_file_has "$session/keep.txt" "user data"
    [ ! -e "$session/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json" ]
    [ ! -e "$session/.circuit-state.json" ]
}

@test "retirement: an unowned project policy without the marker is kept" {
    mkdir -p "$TEST_PROJECT/.claude"
    printf '%s\n' '{"mode": "safe"}' \
        > "$TEST_PROJECT/.claude/ai-toolkit-output-filter.json"
    printf 'someone-else\n' \
        > "$TEST_PROJECT/.claude/.ai-toolkit-output-filter.owner"

    run bash -c "cd '$TEST_PROJECT' && python3 '$TOOLKIT_DIR/scripts/install.py' --local"
    [ "$status" -eq 0 ]
    refute_output_has "output-filter"
    [ -f "$TEST_PROJECT/.claude/ai-toolkit-output-filter.json" ]
    [ -f "$TEST_PROJECT/.claude/.ai-toolkit-output-filter.owner" ]
}

@test "retirement: a symlinked recovery namespace blocks deletion and keeps data" {
    local outside="$TEST_PROJECT/outside-recovery"
    local repository="$DATA_DIR/sessions/repo-b"
    mkdir -p "$outside" "$repository"
    chmod 700 "$repository"
    printf 'outside user data\n' > "$outside/keep.txt"
    ln -s "$outside" "$repository/output-filter"

    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TMP_HOME"
    [ "$status" -eq 0 ]
    assert_output_has "Warning: output-filter retirement kept sessions/*/output-filter/ recovery data"

    [ -L "$repository/output-filter" ]
    assert_file_has "$outside/keep.txt" "outside user data"
}

@test "retirement: a symlinked hook leftover is never followed" {
    local outside="$TEST_PROJECT/outside-hook.sh"
    mkdir -p "$DATA_DIR/hooks"
    printf '#!/usr/bin/env bash\n# Claude PostToolUse adapter for the native tool-output filter.\n' \
        > "$outside"
    ln -s "$outside" "$DATA_DIR/hooks/filter-tool-output.sh"

    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TMP_HOME"
    [ "$status" -eq 0 ]
    refute_output_has "Migrated: removed retired output-filter hooks/filter-tool-output.sh"
    [ -f "$outside" ]
    [ -L "$DATA_DIR/hooks/filter-tool-output.sh" ]
}
