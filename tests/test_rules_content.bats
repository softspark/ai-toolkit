#!/usr/bin/env bats
# Smoke tests for language rules content — guards against accidental removal of
# canonical sections from app/rules/*.md. Intentionally non-brittle: checks
# section headings only, not exact wording.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
RULES_DIR="$TOOLKIT_DIR/app/rules"

@test "common/coding-style.md has JSON Wire Format Conventions section" {
    file="$RULES_DIR/common/coding-style.md"
    [ -f "$file" ]
    grep -q '^## JSON Wire Format Conventions$' "$file"
}

@test "php/frameworks.md has Symfony Serializer section" {
    file="$RULES_DIR/php/frameworks.md"
    [ -f "$file" ]
    grep -q '^## Symfony Serializer$' "$file"
}

@test "dart/frameworks.md has JSON Serialization section" {
    file="$RULES_DIR/dart/frameworks.md"
    [ -f "$file" ]
    grep -q '^## JSON Serialization$' "$file"
}
