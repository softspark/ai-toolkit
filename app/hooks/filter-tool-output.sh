#!/usr/bin/env bash
# Claude PostToolUse adapter for the native tool-output filter.

HOOK_SOURCE="${BASH_SOURCE[0]}"
HOOK_DIR="${HOOK_SOURCE%/*}"
[[ "$HOOK_DIR" == "$HOOK_SOURCE" ]] && HOOK_DIR="."
# shellcheck source=_profile-check.sh
source "$HOOK_DIR/_profile-check.sh"

OWNER_MARKER="ai-toolkit-output-filter-policy-v1"
GLOBAL_POLICY="$HOME/.softspark/ai-toolkit/hooks/output-filter-policy.json"
PROJECTS_REGISTRY="$HOME/.softspark/ai-toolkit/projects.json"

is_regular_file() {
    [[ -f "$1" && -r "$1" && ! -L "$1" ]]
}

# A project policy is trusted only for projects the user registered via
# `ai-toolkit install --local`. The owner marker alone is a public constant,
# so a cloned repo must never be able to self-enable filtering with it.
is_registered_project() {
    is_regular_file "$PROJECTS_REGISTRY" &&
        grep -qF "\"$1\"" "$PROJECTS_REGISTRY" 2>/dev/null
}

if [[ "${AI_TOOLKIT_OUTPUT_FILTER_DISABLE:-}" == "1" ]]; then
    exit 0
fi

if [[ -n "${AI_TOOLKIT_OUTPUT_FILTER_POLICY:-}" ]]; then
    POLICY_PATH="$AI_TOOLKIT_OUTPUT_FILTER_POLICY"
    if ! is_regular_file "$POLICY_PATH"; then
        exit 0
    fi
else
    PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
    PROJECT_POLICY="$PROJECT_ROOT/.claude/ai-toolkit-output-filter.json"
    PROJECT_OWNER="$PROJECT_ROOT/.claude/.ai-toolkit-output-filter.owner"
    if [[ -L "$PROJECT_ROOT" || -L "$PROJECT_ROOT/.claude" ]]; then
        exit 0
    fi
    if is_registered_project "$PROJECT_ROOT" &&
       is_regular_file "$PROJECT_OWNER" &&
       [[ "$(<"$PROJECT_OWNER")" == "$OWNER_MARKER" ]]; then
        if ! is_regular_file "$PROJECT_POLICY"; then
            exit 0
        fi
        POLICY_PATH="$PROJECT_POLICY"
    else
        POLICY_PATH="$GLOBAL_POLICY"
    fi
fi

if ! is_regular_file "$POLICY_PATH"; then
    exit 0
fi
POLICY_CONTENT="$(<"$POLICY_PATH")" || exit 0
if [[ ${#POLICY_CONTENT} -gt 65536 ]]; then
    exit 0
fi
MODE_OFF_PATTERN='"mode"[[:space:]]*:[[:space:]]*"off"'
MODE_ACTIVE_PATTERN='"mode"[[:space:]]*:[[:space:]]*"(observe|safe)"'
if [[ "$POLICY_CONTENT" =~ $MODE_OFF_PATTERN ]]; then
    exit 0
fi
if [[ ! "$POLICY_CONTENT" =~ $MODE_ACTIVE_PATTERN ]]; then
    exit 0
fi

RUNTIME_PATH="${AI_TOOLKIT_OUTPUT_FILTER_HOOK_RUNTIME:-${AI_TOOLKIT_OUTPUT_FILTER_CLI:-$HOME/.softspark/ai-toolkit/scripts/output_filter_hook.py}}"
if ! is_regular_file "$RUNTIME_PATH"; then
    exit 0
fi
python3 -S "$RUNTIME_PATH" hook --policy "$POLICY_PATH" 2>/dev/null || true

exit 0
