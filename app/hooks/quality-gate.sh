#!/usr/bin/env bash
# quality-gate.sh — Block task completion if lint/type errors found.
#
# Fires on: Stop, TaskCompleted
# Exit 2 = block completion/stop. Skipped when TOOLKIT_HOOK_PROFILE=minimal.
# Strict profile also runs mypy.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"
# shellcheck source=_locate-toolkit.sh
source "$(dirname "$0")/_locate-toolkit.sh"

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

cohesion_for_session_edits() {
    # Run cohesion-mapped tests for every path touched this session.
    # Used by projects that ship a test-cohesion-map.json (e.g. ai-toolkit).
    [ -z "$TOOLKIT_DIR" ] && return 0
    command -v python3 >/dev/null 2>&1 || return 0

    local edits
    edits=$(python3 "$TOOLKIT_DIR/scripts/session_state.py" list 2>/dev/null)
    [ -z "$edits" ] && return 0

    # shellcheck disable=SC2206  # word-splitting is intentional, paths have no spaces
    local edits_array=()
    while IFS= read -r line; do
        [ -n "$line" ] && edits_array+=("$line")
    done <<<"$edits"
    [ "${#edits_array[@]}" -eq 0 ] && return 0

    local commands
    commands=$(python3 "$TOOLKIT_DIR/scripts/test_cohesion.py" resolve \
        --changed-paths "${edits_array[@]}" --repo-root "$PWD" 2>/dev/null)
    [ -z "$commands" ] && return 0

    local tmp
    tmp="$(mktemp "${TMPDIR:-/tmp}/ai-toolkit-cohesion.XXXXXX")"
    while IFS= read -r cmd; do
        [ -z "$cmd" ] && continue
        if ! bash -c "$cmd" >"$tmp" 2>&1; then
            echo "QUALITY GATE FAILED: cohesion tests failed." >&2
            echo "Command: $cmd" >&2
            tail -25 "$tmp" >&2
            rm -f "$tmp"
            exit 2
        fi
    done <<<"$commands"
    rm -f "$tmp"
}

# Cohesion-driven branch (ai-toolkit-style repos): runs ONLY tests mapped to
# files edited in this session via .claude/test-cohesion-map.json (or the
# toolkit default at app/hooks/test-cohesion-map.json).
if [ -f .claude/test-cohesion-map.json ] || \
   { [ -f app/hooks.json ] && [ -d tests ] && [ -f scripts/validate.py ]; }; then
    cohesion_for_session_edits
fi

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
