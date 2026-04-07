#!/usr/bin/env bash
# subagent-start.sh — Remind subagents to stay scoped and evidence-driven.
#
# Fires on: SubagentStart
# Matcher: all
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

# Read from stdin (Claude Code passes JSON with .agent_id, .agent_type)
INPUT=$(cat)
AGENT_TYPE=$(echo "$INPUT" | jq -r '.agent_type // "subagent"' 2>/dev/null)

echo "SubagentStart: ${AGENT_TYPE} owns a narrow scope. Read only the necessary files first, cite evidence, and return explicit validation notes with any edits."

exit 0

