#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Every skill script a SKILL.md documents must answer --help with exit 0 and no
# traceback (sop-maintenance "Adding Scripts to Skills"). Mirrors Phase 4b of
# the post-release SOP, which found five scripts treating --help as a path on
# v4.32.0. Run from the working tree: the invocation is resolved the way an
# installed skill resolves ${CLAUDE_SKILL_DIR}.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

@test "skill scripts: every documented \${CLAUDE_SKILL_DIR} invocation answers --help (rc 0, no traceback)" {
    local failures=0 probed=0
    for D in "$TOOLKIT_DIR"/app/skills/*/; do
        [ -d "$D/scripts" ] || continue
        ref=$(grep -ohE '(python3?|bash|sh|node) +\$\{CLAUDE_SKILL_DIR\}/scripts/[A-Za-z0-9_.-]+' "$D/SKILL.md" | head -1)
        [ -n "$ref" ] || continue
        interp=${ref%% *}
        rel=${ref##*\$\{CLAUDE_SKILL_DIR\}/}
        [ -f "$D/$rel" ] || { echo "PATH DOES NOT RESOLVE: $(basename "$D") $rel" >&2; failures=$((failures + 1)); continue; }
        probed=$((probed + 1))
        # Capture rc explicitly: under bats' errexit a failing command
        # substitution in an assignment aborts the test before the report.
        # `timeout` is GNU coreutils and is not on the macOS CI runner (rc=127
        # for every probe on the first run); perl's alarm is on both runners.
        rc=0
        out=$(cd "$D" && CLAUDE_SKILL_DIR="$D" perl -e 'alarm shift; exec @ARGV' 20 "$interp" "$D/$rel" --help </dev/null 2>&1) || rc=$?
        if [ "$rc" -ne 0 ] || printf '%s' "$out" | grep -q 'Traceback'; then
            echo "FAIL $(basename "$D") $rel rc=$rc: $(printf '%s' "$out" | head -1 | cut -c1-80)" >&2
            failures=$((failures + 1))
        fi
    done
    echo "probed=$probed failures=$failures" >&2
    [ "$probed" -ge 20 ]
    [ "$failures" -eq 0 ]
}
