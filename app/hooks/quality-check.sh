#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# quality-check.sh — Multi-language lint check.
#
# Fires on: Stop (advisory) and the git pre-commit fallback (--blocking).
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.
#
# Modes:
#   (default)   Advisory, for the Stop hook. Surfaces the first 15 lines of the
#               checker output and always exits 0: it must not block Claude from
#               returning a response. The checker's status is dropped on purpose.
#   --blocking  Gate, for the git pre-commit hook. Exit codes:
#                 0  the checker ran and passed
#                 1  the checker failed or crashed (its name and exit code are printed)
#                 3  nothing ran: no supported project, tool missing, checker not
#                    configured, or hook disabled. The reason is printed as
#                    "skipped (reason)". A skip is never a pass.
#
# Env:
#   AI_TOOLKIT_PHPSTAN_MEMORY  --memory-limit for host PHPStan (default 1G). The
#                              host php.ini default (128M) crashes parallel workers.

BLOCKING=0
if [ "${1:-}" = "--blocking" ]; then
    BLOCKING=1
fi

if [ "$BLOCKING" -eq 1 ]; then
    # _profile-check.sh ends the shell to skip. Probe it in a subshell so a
    # skipped gate is reported as skipped instead of exiting 0 without a word.
    # shellcheck source=_profile-check.sh
    if [ "$(source "$(dirname "$0")/_profile-check.sh" && echo run)" != "run" ]; then
        echo "[ai-toolkit] quality-check: skipped (TOOLKIT_HOOK_PROFILE=minimal or quality-check listed in AI_TOOLKIT_DISABLED_HOOKS)"
        exit 3
    fi
fi

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

# PHPStan prints these when a parallel worker dies (memory limit, fatal error).
# Safety net for a crash that still ends with exit 0.
PHPSTAN_CRASH_RE='Child process error|PHPStan process crashed|reached configured PHP memory limit'

say() {
    echo "[ai-toolkit] $*"
}

# First of php-stan / phpstan / stan that the Makefile defines. A repo that names
# its PHPStan target owns the memory limit and, in container setups, the PHP
# binary; the host's php.ini is the wrong authority.
phpstan_make_target() {
    local target
    [ -f Makefile ] || return 1
    for target in php-stan phpstan stan; do
        if grep -q "^${target}:" Makefile; then
            echo "$target"
            return 0
        fi
    done
    return 1
}

# Prints the whole file when short, otherwise its head and tail: a crash
# message is at the end of the output as often as at the start.
show_output() {
    local file="$1" total
    total="$(wc -l <"$file" | tr -d ' ')"
    if [ "$total" -le 30 ]; then
        cat "$file"
    else
        head -20 "$file"
        echo "... ($((total - 30)) lines omitted)"
        tail -10 "$file"
    fi
}

# run_checker <label> <crash-regex|""> <command> [args...]
# Advisory: prints the first 15 lines and returns. Blocking: exits the script
# with 0 (passed), 1 (failed or crashed) or 3 (could not run).
run_checker() {
    local label="$1" crash_re="$2"
    shift 2

    if [ "$BLOCKING" -eq 0 ]; then
        "$@" 2>&1 | head -15
        return 0
    fi

    if ! command -v "$1" >/dev/null 2>&1; then
        say "$label: skipped ($1 not found or not executable)"
        exit 3
    fi

    local out rc
    out="$(mktemp "${TMPDIR:-/tmp}/ai-toolkit-quality-check.XXXXXX")" || {
        say "$label: FAILED (cannot create a temp file)"
        exit 1
    }
    "$@" >"$out" 2>&1
    rc=$?

    if [ "$rc" -ne 0 ]; then
        show_output "$out"
        rm -f "$out"
        say "$label: FAILED (exit $rc)"
        exit 1
    fi
    if [ -n "$crash_re" ] && grep -Eq "$crash_re" "$out"; then
        show_output "$out"
        rm -f "$out"
        say "$label: FAILED (crash reported in the output, although the exit code was 0)"
        exit 1
    fi
    rm -f "$out"
    say "$label: passed"
    exit 0
}

if [ -f pyproject.toml ] || [ -f setup.py ]; then
    # Gate only on what the project configured: a bare pyproject.toml says
    # nothing about ruff, and `ruff check .` under whatever config the machine
    # resolves would block commits on findings the project never signed up for
    # (same rule as quality-gate.sh, v4.32.0 postmortem).
    if [ "$BLOCKING" -eq 1 ] && ! { [ -f ruff.toml ] || [ -f .ruff.toml ] || grep -qs '^\[tool\.ruff' pyproject.toml; }; then
        say "ruff: skipped (not configured: no ruff.toml, .ruff.toml or [tool.ruff] in pyproject.toml)"
        exit 3
    fi
    run_checker "ruff" "" ruff check .
elif [ -f package.json ] && [ -f tsconfig.json ]; then
    run_checker "tsc" "" npx tsc --noEmit
elif [ -f composer.json ] && { PHPSTAN_TARGET="$(phpstan_make_target)" || [ -f vendor/bin/phpstan ]; }; then
    if [ -n "$PHPSTAN_TARGET" ]; then
        run_checker "PHPStan (make $PHPSTAN_TARGET)" "$PHPSTAN_CRASH_RE" make -s "$PHPSTAN_TARGET"
    else
        run_checker "PHPStan" "$PHPSTAN_CRASH_RE" \
            vendor/bin/phpstan analyse "--memory-limit=${AI_TOOLKIT_PHPSTAN_MEMORY:-1G}"
    fi
elif [ -f pubspec.yaml ]; then
    run_checker "dart analyze" "" dart analyze
elif [ -f go.mod ]; then
    run_checker "go vet" "" go vet ./...
fi

if [ "$BLOCKING" -eq 1 ]; then
    say "quality-check: skipped (no supported checker: needs pyproject.toml/setup.py, package.json + tsconfig.json, composer.json + PHPStan, pubspec.yaml or go.mod)"
    exit 3
fi

exit 0
