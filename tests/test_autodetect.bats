#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# test_autodetect.bats — Tests for scripts/install_steps/detect_language.py
# Run with: bats tests/test_autodetect.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_TMP="$(mktemp -d)"
    export PYTHONPATH="$TOOLKIT_DIR/scripts"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# Helper: run detect_languages and print comma-separated result
detect() {
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from install_steps.detect_language import detect_languages
from pathlib import Path
result = detect_languages(Path('$TEST_TMP'), Path('$TOOLKIT_DIR'))
print(','.join(result))
"
}

# ── single language detection ───────────────────────────────────────────────

@test "autodetect: detects TypeScript from package.json" {
    echo '{}' > "$TEST_TMP/package.json"
    run detect
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'rules-typescript'
}

@test "autodetect: detects TypeScript from tsconfig.json" {
    echo '{}' > "$TEST_TMP/tsconfig.json"
    run detect
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'rules-typescript'
}

@test "autodetect: detects Python from pyproject.toml" {
    touch "$TEST_TMP/pyproject.toml"
    run detect
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'rules-python'
}

@test "autodetect: detects Python from requirements.txt" {
    touch "$TEST_TMP/requirements.txt"
    run detect
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'rules-python'
}

@test "autodetect: detects Go from go.mod" {
    touch "$TEST_TMP/go.mod"
    run detect
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'rules-golang'
}

@test "autodetect: detects Rust from Cargo.toml" {
    touch "$TEST_TMP/Cargo.toml"
    run detect
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'rules-rust'
}

@test "autodetect: detects Dart from pubspec.yaml" {
    touch "$TEST_TMP/pubspec.yaml"
    run detect
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'rules-dart'
}

@test "autodetect: detects PHP from composer.json" {
    echo '{}' > "$TEST_TMP/composer.json"
    run detect
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'rules-php'
}

# ── multi-language detection ────────────────────────────────────────────────

@test "autodetect: detects multiple languages (package.json + go.mod)" {
    echo '{}' > "$TEST_TMP/package.json"
    touch "$TEST_TMP/go.mod"
    run detect
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'rules-golang'
    echo "$output" | grep -q 'rules-typescript'
}

# ── empty directory ─────────────────────────────────────────────────────────

@test "autodetect: empty directory returns empty list" {
    run detect
    [ "$status" -eq 0 ]
    # Output should be empty (no languages detected)
    [ -z "$output" ]
}

@test "autodetect: legacy and explicitly Codex-owned skill surfaces still detect Codex" {
    mkdir -p "$TEST_TMP/.agents/skills/example"
    printf '%s\n' '---' 'name: example' 'description: Example.' '---' 'Body.' \
        > "$TEST_TMP/.agents/skills/example/SKILL.md"

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from install_steps.ai_tools import _detect_editors

print(",".join(_detect_editors(Path(sys.argv[2]))))
PY
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'codex'

    printf '%s\n' 'codex' > "$TEST_TMP/.agents/.ai-toolkit-skill-owners"
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from install_steps.ai_tools import _detect_editors

print(",".join(_detect_editors(Path(sys.argv[2]))))
PY
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'codex'
}
