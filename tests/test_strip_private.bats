#!/usr/bin/env bats
# test_strip_private.bats — memory-pack sanitization before SQLite storage.
# Run with: bats tests/test_strip_private.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
STRIP="$TOOLKIT_DIR/app/plugins/memory-pack/scripts/strip_private.py"

@test "strip_private: removes <private> blocks (regression)" {
    run bash -c "printf '%s' 'keep <private>hide me</private> keep' | python3 '$STRIP'"
    [ "$status" -eq 0 ]
    [[ "$output" == "keep  keep" ]]
}

@test "strip_private: redacts sk- API key" {
    run bash -c "printf '%s' 'token sk-ABCDEFGHIJKLMNOPQRSTUVWX done' | python3 '$STRIP'"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[REDACTED:api-key]"* ]]
    [[ "$output" != *"sk-ABCDEFGHIJKLMNOPQRSTUVWX"* ]]
}

@test "strip_private: redacts AWS access key" {
    run bash -c "printf '%s' 'aws AKIAIOSFODNN7EXAMPLE here' | python3 '$STRIP'"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[REDACTED:aws-key]"* ]]
}

@test "strip_private: redacts GitHub token" {
    run bash -c "printf '%s' 'ghp_1234567890abcdefghijklmnopqrstuvwxyz12 end' | python3 '$STRIP'"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[REDACTED:github-token]"* ]]
}

@test "strip_private: leaves benign prose untouched (no over-redaction)" {
    run bash -c "printf '%s' 'the password policy requires rotation' | python3 '$STRIP'"
    [ "$status" -eq 0 ]
    [[ "$output" == "the password policy requires rotation" ]]
}
