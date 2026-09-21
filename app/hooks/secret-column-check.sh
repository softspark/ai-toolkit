#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# secret-column-check.sh — Advisory: a secret-looking column stored in plaintext.
#
# Fires on: PostToolUse (Edit|MultiEdit|Write)
# Never blocks. When an edit to a schema, model or migration file declares a
# column whose name looks like a token, secret, password or key, and nothing on
# or right above it marks it encrypted or hashed, it reminds the agent of the
# secrets-at-rest rule (app/rules/common/security.md). Detection lives in
# scripts/secret_column_check.py. Each file + column is reported once per
# session, so rewriting a file does not repeat the reminder.
#
# Skipped in minimal profile; honours AI_TOOLKIT_DISABLED_HOOKS.
# One-off silence: CLAUDE_SKIP_SECRET_COLUMNS=1.

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"
# shellcheck source=_locate-toolkit.sh
source "$(dirname "$0")/_locate-toolkit.sh"
# shellcheck source=_hook-io.sh
source "$(dirname "$0")/_hook-io.sh"

[ "${CLAUDE_SKIP_SECRET_COLUMNS:-0}" = "1" ] && exit 0

# shellcheck disable=SC2034  # INPUT is consumed via sourced _hook-io.sh
INPUT=$(cat)
FILE_PATH=$(hook_file_path)
[ -z "$FILE_PATH" ] && exit 0

# Only the text this edit wrote: new_string, a whole-file content, every
# MultiEdit hunk, or the file_changes shape some editors send.
CONTENT=$(hook_json '[
    .tool_input.new_string?, .tool_input.content?, (.tool_input.edits[]?.new_string),
    .tool_info.new_string?, .tool_info.content?, (.tool_info.edits[]?.new_string),
    (.file_changes[]?.content)
] | map(select(type == "string")) | join("\n")')
[ -z "$CONTENT" ] && exit 0

# Cheap prefilter before starting Python.
printf '%s' "$CONTENT" | grep -qiE 'token|secret|passw|api_?key|private_?key|licen[cs]e_?key|credential|signing_?key|access_?key|client_?key' || exit 0

[ -z "$TOOLKIT_DIR" ] && exit 0
SCANNER="$TOOLKIT_DIR/scripts/secret_column_check.py"
[ -f "$SCANNER" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

FINDINGS=$(printf '%s' "$CONTENT" | python3 "$SCANNER" "$FILE_PATH" 2>/dev/null)
[ -z "$FINDINGS" ] && exit 0

SID=$(hook_session_id)
STATE_DIR="${HOME}/.softspark/ai-toolkit/sessions"
mkdir -p "$STATE_DIR" 2>/dev/null
SEEN="${STATE_DIR}/${SID}-secret-columns.log"

NEW=""
while IFS=$'\t' read -r name kind; do
    [ -z "$name" ] && continue
    # Store only a short hash of file + column, never the path or the name.
    key=$(printf '%s|%s' "$FILE_PATH" "$name" | { shasum -a 256 2>/dev/null || sha256sum 2>/dev/null; } | cut -c1-16)
    if [ -n "$key" ] && grep -qxF "$key" "$SEEN" 2>/dev/null; then
        continue
    fi
    [ -n "$key" ] && printf '%s\n' "$key" >> "$SEEN" 2>/dev/null
    NEW="${NEW:+$NEW, }\`${name}\` (${kind})"
done <<< "$FINDINGS"
[ -z "$NEW" ] && exit 0

hook_emit_context "PostToolUse" \
    "Secrets at rest: $(basename "$FILE_PATH") declares ${NEW} with nothing marking it encrypted or hashed. A token, password or key must not sit in the database in plaintext: store a keyed HMAC when the code only compares the value, encrypt it when the code reads it back, and add a test that reads the raw stored value (security-patterns skill, reference/secrets-at-rest.md). If the column holds no credential, ignore this."
exit 0
