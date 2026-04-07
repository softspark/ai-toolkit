#!/usr/bin/env bash
# track-usage.sh — Track skill invocations for usage stats.
#
# Fires on: UserPromptSubmit
# Writes to: ~/.ai-toolkit/stats.json
#
# Detects /skill-name pattern from user prompt and increments counter.
# Uses atomic write via python3 os.replace() to prevent corruption.

STATS_FILE="${HOME}/.ai-toolkit/stats.json"

# Read prompt from stdin (Claude Code passes JSON with .prompt field)
INPUT=$(cat)
PROMPT_TEXT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
[ -z "$PROMPT_TEXT" ] && exit 0

# Only track if prompt starts with a slash command
SKILL_NAME=$(printf '%s' "$PROMPT_TEXT" | grep -oE '^/[a-z][a-z0-9-]*' | head -1 | sed 's|^/||')
[ -z "$SKILL_NAME" ] && exit 0

# Ensure directory exists
mkdir -p "$(dirname "$STATS_FILE")"

# Atomic update via python3
python3 - "$STATS_FILE" "$SKILL_NAME" <<'PY'
import json
import sys
import os
from datetime import datetime, timezone

stats_file = sys.argv[1]
skill = sys.argv[2]

data = {}
if os.path.exists(stats_file):
    try:
        with open(stats_file) as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        data = {}

now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
if skill not in data:
    data[skill] = {"count": 0, "last_used": now}
data[skill]["count"] += 1
data[skill]["last_used"] = now

tmp = stats_file + ".tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)
os.replace(tmp, stats_file)
PY

exit 0
