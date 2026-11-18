#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# save-session.sh — Persist session context on stop for cross-session continuity.
#
# Fires on: Stop
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"
# shellcheck source=_session-paths.sh
source "$(dirname "$0")/_session-paths.sh"
# shellcheck source=_hook-io.sh
source "$(dirname "$0")/_hook-io.sh"

# Extract only the runtime's session identifier from the completion event.
# shellcheck disable=SC2034  # INPUT is consumed via sourced _hook-io.sh
INPUT=$(cat)
SESSION_ID=$(hook_session_id)
[ "$SESSION_ID" != "default" ] || exit 0
unset INPUT
commit=""
dirty=""
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    commit=$(git rev-parse --short HEAD 2>/dev/null)
    dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
fi
umask 077
exec python3 -I -S "$(dirname "$0")/_session-handoff.py" "$SESSION_DIR" "$SESSION_ID" "$commit" "$dirty"
