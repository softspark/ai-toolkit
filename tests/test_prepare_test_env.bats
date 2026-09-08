#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

setup() {
  REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
}

@test "prepare-test-env: bundled checker has a usable CLI" {
  run python3 "$REPO_ROOT/app/skills/prepare-test-env/scripts/env-check.py" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"snapshot"* ]]
  [[ "$output" == *"check"* ]]
}

@test "prepare-test-env: real Git and HTTP behavior satisfies the QA contract" {
  run python3 -m unittest discover -s "$REPO_ROOT/tests/fixtures/prepare_test_env" -p 'test_*.py' -v
  if [ "$status" -ne 0 ]; then
    printf '%s\n' "$output"
  fi
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}
