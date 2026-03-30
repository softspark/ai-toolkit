#!/usr/bin/env bash
# quality-gate.sh — Block task completion if lint/type errors found.
#
# Fires on: TaskCompleted
# Exit 2 = block completion. Skipped when TOOLKIT_HOOK_PROFILE=minimal.
# Strict profile also runs mypy.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

if [ -f pyproject.toml ] || [ -f setup.py ]; then
    ruff check . 2>&1 | head -30
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "QUALITY GATE FAILED: ruff found errors. Fix them before completing." >&2
        exit 2
    fi
    if [ -d src ] && [ "$PROFILE" = "strict" ]; then
        mypy --strict src/ 2>&1 | tail -5
        exit_code=$?
        if [ $exit_code -ne 0 ]; then
            echo "QUALITY GATE FAILED: mypy found type errors." >&2
            exit 2
        fi
    fi
elif [ -f package.json ] && [ -f tsconfig.json ]; then
    npx tsc --noEmit 2>&1 | tail -10
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "QUALITY GATE FAILED: TypeScript compilation errors." >&2
        exit 2
    fi
elif [ -f pubspec.yaml ]; then
    dart analyze 2>&1 | tail -10
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "QUALITY GATE FAILED: Dart analysis issues." >&2
        exit 2
    fi
elif [ -f go.mod ]; then
    go vet ./... 2>&1 | tail -10
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "QUALITY GATE FAILED: Go vet issues." >&2
        exit 2
    fi
fi

exit 0
