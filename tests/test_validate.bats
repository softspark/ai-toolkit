#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for validate.py — cached: runs once, asserts twice

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export VALIDATE_OUTPUT
    export VALIDATE_STATUS
    VALIDATE_OUTPUT="$(python3 "$TOOLKIT_DIR/scripts/validate.py" 2>&1)"
    VALIDATE_STATUS=$?
}

@test "validate.py exits 0 on clean toolkit" {
    [ "$VALIDATE_STATUS" -eq 0 ]
}

@test "validate.py outputs no ERROR lines" {
    error_count=$(echo "$VALIDATE_OUTPUT" | grep -c "^ERROR" || true)
    [ "$error_count" -eq 0 ]
}

@test "validate.py reports the skill body budget headroom" {
    # Always-on line, not only on violation: the ratchet in validate.py can only be
    # lowered deliberately if the current headroom is visible on every run.
    echo "$VALIDATE_OUTPUT" | grep -q "Body budget: largest is .* bytes (warn 18000, error 20000)"
}

@test "no skill body exceeds the 20000-byte budget" {
    local over
    over=$(find "$TOOLKIT_DIR/app/skills" -maxdepth 2 -name SKILL.md -size +20000c | wc -l | tr -d ' ')
    [ "$over" -eq 0 ]
}
