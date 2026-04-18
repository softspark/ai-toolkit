#!/usr/bin/env bash
# quality-check.sh — Multi-language lint check after Claude stops.
#
# Fires on: Stop
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

# All lint/typecheck invocations are advisory. They run on the Stop hook and
# must not block Claude from returning a response, hence the trailing `|| true`.
# The first 15 lines of output are surfaced to the user; further lines are
# truncated to keep the context lean.
if [ -f pyproject.toml ] || [ -f setup.py ]; then
    ruff check . 2>&1 | head -15 || true
elif [ -f package.json ] && [ -f tsconfig.json ]; then
    npx tsc --noEmit 2>&1 | head -15 || true
elif [ -f composer.json ] && [ -f vendor/bin/phpstan ]; then
    vendor/bin/phpstan analyse 2>&1 | head -15 || true
elif [ -f pubspec.yaml ]; then
    dart analyze 2>&1 | head -15 || true
elif [ -f go.mod ]; then
    go vet ./... 2>&1 | head -15 || true
fi

exit 0
