#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
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

# The official Claude plugin agent only forwards one task call. File inspection
# belongs to the actual Codex worker; asking this wrapper to research conflicts
# with its contract. Native clients and all other agent types keep the reminder.
if [ "$AGENT_TYPE" = "codex:codex-rescue" ] &&
   [ -n "${CLAUDE_PROJECT_DIR:-}" ] &&
   [ -z "${CODEX_THREAD_ID:-}" ] &&
   [ "${AI_TOOLKIT_HOOK_FORMAT:-}" != "json" ]; then
    if [ "${AI_TOOLKIT_HOOK_QUIET:-0}" != "1" ]; then
        echo "SubagentStart: codex:codex-rescue is a forwarding wrapper. Preserve its one-call task forwarding contract; the delegated Codex worker performs research and verification."
    fi
    exit 0
fi

echo "SubagentStart: ${AGENT_TYPE} owns a narrow scope. Read only the necessary files first, cite evidence, and return explicit validation notes with any edits."

exit 0
