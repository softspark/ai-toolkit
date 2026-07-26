#!/usr/bin/env bash
# rewrite.sh — delegate PreToolUse command rewriting to the rtk binary.
#
# Fires on: PreToolUse
# Reads the Claude Code hook JSON from stdin and hands it to `rtk hook claude`,
# which emits hookSpecificOutput with permissionDecision and updatedInput.
#
# This hook rewrites the command before it runs, so what executes is not
# literally what the model asked for. That is the pack's stated trade-off; see
# the pack README. Everything here is built so that any failure degrades to
# passthrough rather than to a broken or altered command:
#
#   no binary        -> no output, exit 0 (command runs unchanged)
#   rtk fails        -> no output, exit 0
#   rtk times out    -> no output, exit 0
#   rtk prints junk  -> no output, exit 0
#
# Emitting nothing is the safe default: Claude Code treats an empty hook
# response as "no opinion" and runs the original command.

set -u

PACK_BIN_DIR="${HOME}/.softspark/ai-toolkit/plugin-scripts/rtk-pack/bin"
TIMEOUT_SECONDS=5

# Read stdin once; it is not replayable.
INPUT=$(cat)
[ -n "$INPUT" ] || exit 0

# jq is needed both to gate on the tool name and to check rtk's reply. Without
# it we cannot do either safely, so stay out of the way entirely.
command -v jq >/dev/null 2>&1 || exit 0

# A pack hook cannot declare its own matcher: plugin.py:408 looks the basename
# up in core app/hooks.json and falls back to "", so this registers against
# every tool rather than Bash alone. Gate here instead, otherwise every Read,
# Edit and Grep would spawn a subprocess for nothing.
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[ "$TOOL" = "Bash" ] || exit 0

RTK=""
for candidate in "${PACK_BIN_DIR}/rtk" "${PACK_BIN_DIR}/rtk.exe"; do
    if [ -x "$candidate" ]; then
        RTK="$candidate"
        break
    fi
done

# Inert when init.py could not install a binary. The pack stays wired so that a
# later `ai-toolkit plugin install rtk-pack` fixes it without touching settings.
[ -n "$RTK" ] || exit 0

# GNU timeout is `timeout`, Homebrew coreutils installs it as `gtimeout`, and
# on a bare macOS it is absent. A hung rewriter would hang the session, so use
# it when we can and accept the risk when we cannot.
TIMEOUT_CMD=""
if command -v timeout >/dev/null 2>&1; then
    TIMEOUT_CMD="timeout"
elif command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_CMD="gtimeout"
fi

if [ -n "$TIMEOUT_CMD" ]; then
    OUTPUT=$(printf '%s' "$INPUT" | "$TIMEOUT_CMD" "$TIMEOUT_SECONDS" "$RTK" hook claude 2>/dev/null)
else
    OUTPUT=$(printf '%s' "$INPUT" | "$RTK" hook claude 2>/dev/null)
fi
STATUS=$?

[ "$STATUS" -eq 0 ] || exit 0
[ -n "$OUTPUT" ] || exit 0

# Only forward something that parses as JSON. A partial write or a stray
# diagnostic on stdout would otherwise reach Claude Code as a malformed hook
# response.
printf '%s' "$OUTPUT" | jq -e . >/dev/null 2>&1 || exit 0

printf '%s\n' "$OUTPUT"
exit 0
