#!/usr/bin/env bash
# _profile-check.sh — shared profile skip logic for hooks
# Source this file at the top of any hook that should be skipped in minimal profile.
#
# Usage (in a hook script):
#   source "$(dirname "$0")/_profile-check.sh"
#
# Sets PROFILE variable. Exits 0 (skip hook) when TOOLKIT_HOOK_PROFILE=minimal.

PROFILE="${TOOLKIT_HOOK_PROFILE:-standard}"
[ "$PROFILE" = "minimal" ] && exit 0

# Per-hook soft opt-out: AI_TOOLKIT_DISABLED_HOOKS is a comma-separated list of
# hook names (with or without the .sh suffix). A listed hook exits 0 (no-op).
# Only hooks that source this file are covered — the safety guards
# (guard-destructive/path/config) intentionally do not, and must be removed
# deliberately with `ai-toolkit remove-hook` rather than silently env-disabled.
if [ -n "${AI_TOOLKIT_DISABLED_HOOKS:-}" ]; then
    _hook_name="$(basename "${BASH_SOURCE[1]:-$0}" .sh)"
    IFS=',' read -ra _disabled_hooks <<< "$AI_TOOLKIT_DISABLED_HOOKS"
    for _d in "${_disabled_hooks[@]}"; do
        _d="${_d// /}"
        _d="${_d%.sh}"
        if [ -n "$_d" ] && [ "$_d" = "$_hook_name" ]; then
            exit 0
        fi
    done
fi
