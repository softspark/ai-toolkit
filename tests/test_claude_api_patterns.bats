#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

run_example_case() {
    run python3 "$TOOLKIT_DIR/tests/fixtures/claude_api_pattern_cases.py" "ClaudePatternExamples.$1"
    [ "$status" -eq 0 ]
}

@test "model routing example preserves explicit model choice" {
    run_example_case test_explicit_model_never_falls_back_to_a_route
}

@test "cache example preserves configured budget and measures writes" {
    run_example_case test_cache_example_preserves_budget_and_counts_writes
}

@test "structured JSON example rejects partial output and invalid semantics" {
    run_example_case test_native_json_rejects_incomplete_and_invalid_semantics
}

@test "moderation URL policy rejects hostname lookalikes" {
    run_example_case test_url_filter_rejects_lookalikes_and_userinfo
}

@test "moderation router sends inconsistent and invalid output to review" {
    run_example_case test_moderation_never_allows_mixed_or_unknown_categories
}

@test "moderation example uses a closed schema and handles refusal" {
    run_example_case test_moderation_uses_closed_schema_and_preserves_policy_and_budget
}
