#!/usr/bin/env bash
# subagent-stop.sh — Enforce a concise completion checklist for subagents.
#
# Fires on: SubagentStop
# Matcher: all
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

# Read from stdin (Claude Code passes JSON with .agent_id, .agent_type)
INPUT=$(cat)
AGENT_TYPE=$(echo "$INPUT" | jq -r '.agent_type // "subagent"' 2>/dev/null)

echo "SubagentStop: ${AGENT_TYPE} should report findings, exact files touched, tests run, remaining risks, and any docs that must be updated by the lead agent."

exit 0

