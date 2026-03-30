#!/usr/bin/env bats
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
