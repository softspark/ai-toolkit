#!/usr/bin/env bash
# _hook-io.sh — shared JSON input/output helpers for multi-editor hooks.
#
# Source this file from hook scripts. It expects the caller to set INPUT to the
# hook payload JSON before calling helper functions.

hook_json() {
    local filter="$1"
    echo "${INPUT:-}" | jq -r "$filter" 2>/dev/null
}

hook_tool_name() {
    local value
    value=$(hook_json '.tool_name // .toolInfo.name // .tool_info.name // .tool // empty')
    [ -n "$value" ] && [ "$value" != "null" ] && printf '%s\n' "$value"
}

hook_prompt() {
    hook_json '.prompt // .tool_info.user_prompt // .user_prompt // .input // empty'
}

hook_command() {
    hook_json '.tool_input.command // .tool_input.command_line // .tool_info.command // .tool_info.command_line // .command // empty'
}

hook_file_path() {
    hook_json '
        .tool_input.file_path //
        .tool_input.path //
        .tool_info.file_path //
        .tool_info.path //
        (.file_changes[0].path? // empty) //
        empty
    '
}

hook_old_content() {
    hook_json '(.tool_input.old_string // .tool_input.old_str_1 // .tool_info.old_string // .tool_info.old_str_1 // .tool_info.edits[0].old_string // "")'
}

hook_new_content() {
    hook_json '(.tool_input.new_string // .tool_input.new_str_1 // .tool_input.content // .tool_info.new_string // .tool_info.new_str_1 // .tool_info.content // .tool_info.edits[0].new_string // .file_changes[0].content? // "")'
}

hook_emit_context() {
    local message="$1"
    if [ "${AI_TOOLKIT_HOOK_FORMAT:-}" = "json" ]; then
        jq -nc --arg msg "$message" \
            '{"hookSpecificOutput":{"additionalContext":$msg},"suppressOutput":true}'
    else
        printf '%s\n' "$message"
    fi
}

hook_emit_block() {
    local event="$1"
    local reason="$2"
    if [ "${AI_TOOLKIT_HOOK_FORMAT:-}" = "json" ]; then
        jq -nc --arg event "$event" --arg reason "$reason" \
            '{"hookSpecificOutput":{"hookEventName":$event,"decision":"block","reason":$reason},"decision":"block","reason":$reason,"suppressOutput":false}'
    else
        jq -nc --arg reason "$reason" '{"decision":"block","reason":$reason}'
    fi
}
