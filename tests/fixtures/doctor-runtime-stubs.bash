# shellcheck shell=bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

# Doctor fixtures must not start the maintainer's native CLI updaters.
# Runtime-probe tests still execute their explicitly supplied binaries.
create_doctor_runtime_stubs() {
    local fixture_root="$1" binary
    export DOCTOR_RUNTIME_BIN="$fixture_root/ai-runtime-bin"
    mkdir -p "$DOCTOR_RUNTIME_BIN"
    for binary in claude codex copilot; do
        # Positional parameters must expand in the generated executable, not here.
        # shellcheck disable=SC2016
        printf '%s\n' '#!/bin/sh' \
            '[ "$#" -eq 1 ] && [ "$1" = "--version" ] || exit 64' \
            'printf "%s\n" "99.0.0"' > "$DOCTOR_RUNTIME_BIN/$binary"
        chmod +x "$DOCTOR_RUNTIME_BIN/$binary"
    done
    export PATH="$DOCTOR_RUNTIME_BIN:$PATH"
}
