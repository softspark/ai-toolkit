#!/usr/bin/env bash
# subagent-start.sh — Remind subagents to stay scoped and evidence-driven.
#
# Fires on: SubagentStart
# Matcher: all
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"

SUBAGENT="${CLAUDE_SUBAGENT_NAME:-${CLAUDE_TOOL_INPUT_SUBAGENT_TYPE:-subagent}}"

echo "SubagentStart: ${SUBAGENT} owns a narrow scope. Read only the necessary files first, cite evidence, and return explicit validation notes with any edits."

exit 0

