#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Dedicated tests for previously untested competitive-analysis skills.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

@test "council skill defines all four decision perspectives" {
    skill="$TOOLKIT_DIR/app/skills/council/SKILL.md"
    for perspective in Advocate Critic Pragmatist User-Proxy; do
        grep -q "$perspective" "$skill" || {
            echo "Missing council perspective: $perspective" >&2
            return 1
        }
    done
}

@test "brand-voice skill contains anti-trope guardrails" {
    skill="$TOOLKIT_DIR/app/skills/brand-voice/SKILL.md"
    grep -qi "anti" "$skill"
    grep -qi "trope" "$skill"
    grep -q "game-changer" "$skill"
}

@test "introspect skill enumerates recovery-oriented failure patterns" {
    skill="$TOOLKIT_DIR/app/skills/introspect/SKILL.md"
    grep -qi "failure pattern" "$skill"
    grep -qi "smallest recovery action" "$skill"
    grep -qi "loop" "$skill"
}
