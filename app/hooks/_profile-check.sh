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
