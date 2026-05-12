#!/usr/bin/env bash
# quality-gate.sh — Block task completion if lint/type errors found.
#
# Fires on: Stop, TaskCompleted
# Exit 2 = block completion/stop. Skipped when TOOLKIT_HOOK_PROFILE=minimal.
# Strict profile also runs mypy.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

run_required() {
    local label="$1"
    local preview_cmd="$2"
    shift 2

    local tmp
    tmp="$(mktemp "${TMPDIR:-/tmp}/ai-toolkit-quality.XXXXXX")"
    "$@" >"$tmp" 2>&1
    local exit_code=$?
    eval "$preview_cmd" <"$tmp"
    rm -f "$tmp"

    if [ $exit_code -ne 0 ]; then
        echo "QUALITY GATE FAILED: ${label}. Fix it before completing." >&2
        exit 2
    fi
}

require_command() {
    local command_name="$1"
    if command -v "$command_name" >/dev/null 2>&1; then
        return 0
    fi
    echo "QUALITY GATE SKIPPED: ${command_name} is not installed." >&2
    return 1
}

if [ -f pyproject.toml ] || [ -f setup.py ]; then
    if require_command ruff; then
        run_required "ruff found errors" "head -30" ruff check .
    fi
    if [ -d src ] && [ "$PROFILE" = "strict" ]; then
        if require_command mypy; then
            run_required "mypy found type errors" "tail -5" mypy --strict src/
        fi
    fi
elif [ -f package.json ] && [ -f tsconfig.json ]; then
    if require_command npx; then
        run_required "TypeScript compilation errors" "tail -10" npx tsc --noEmit
    fi
elif [ -f pubspec.yaml ]; then
    if require_command dart; then
        run_required "Dart analysis issues" "tail -10" dart analyze
    fi
elif [ -f go.mod ]; then
    if require_command go; then
        run_required "Go vet issues" "tail -10" go vet ./...
    fi
fi

exit 0
