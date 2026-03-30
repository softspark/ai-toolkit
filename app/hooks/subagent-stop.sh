#!/usr/bin/env bash
# subagent-stop.sh — Enforce a concise completion checklist for subagents.
#
# Fires on: SubagentStop
# Matcher: all
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

SUBAGENT="${CLAUDE_SUBAGENT_NAME:-${CLAUDE_TOOL_INPUT_SUBAGENT_TYPE:-subagent}}"

echo "SubagentStop: ${SUBAGENT} should report findings, exact files touched, tests run, remaining risks, and any docs that must be updated by the lead agent."

exit 0

