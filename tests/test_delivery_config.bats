#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

@test "delivery config: readonly legacy and Jira/RAG preflight with canonical task identity" {
    run python3 "$TOOLKIT_DIR/tests/fixtures/delivery_config_cases.py" -v
    printf '%s\n' "$output"
    [ "$status" -eq 0 ]
}
