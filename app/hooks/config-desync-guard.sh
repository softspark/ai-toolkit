#!/usr/bin/env bash
# config-desync-guard.sh — Warn when ~/.claude/settings.json drifts from
# the ai-toolkit source manifest (app/hooks.json).
#
# Fires on: ConfigChange
# Matcher: user_settings
# Non-blocking by design: exits 0 even on drift. We never want to block a
# user's legitimate settings edit. Output goes to stderr so Claude Code
# surfaces it as a notice.
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.
#
# Override (silence advisory): CLAUDE_SKIP_CONFIG_DESYNC=1

# shellcheck source=_profile-check.sh
source "$(dirname "$0")/_profile-check.sh"
# shellcheck source=_locate-toolkit.sh
source "$(dirname "$0")/_locate-toolkit.sh"

[ "${CLAUDE_SKIP_CONFIG_DESYNC:-0}" = "1" ] && exit 0
[ -z "$TOOLKIT_DIR" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0

SETTINGS="$HOME/.claude/settings.json"
SOURCE="$TOOLKIT_DIR/app/hooks.json"
[ -f "$SETTINGS" ] || exit 0
[ -f "$SOURCE" ] || exit 0

# Compare canonical behavior, accepting older/current settings where Claude has
# rewritten the JSON without preserving the private `_source` marker.
DIFF_STATUS=0
DIFF=$(python3 - "$SETTINGS" "$SOURCE" <<'PY'
import json
import sys


def without_source(value):
    if isinstance(value, dict):
        return {
            key: without_source(item)
            for key, item in value.items()
            if key != "_source"
        }
    if isinstance(value, list):
        return [without_source(item) for item in value]
    return value


def signature(entry):
    return json.dumps(without_source(entry), sort_keys=True, separators=(",", ":"))


def load_hooks(path):
    try:
        data = json.load(open(path))
    except Exception:
        return {}
    return data.get("hooks", {}) if isinstance(data, dict) else {}


def entry_commands(event, entry):
    out = set()
    for hook in entry.get("hooks", []):
        if isinstance(hook, dict):
            out.add((event, entry.get("matcher", ""), hook.get("command", "")))
    return out


installed_hooks = load_hooks(sys.argv[1])
source_hooks = load_hooks(sys.argv[2])
source_signatures = {
    event: {
        signature(entry)
        for entry in entries
        if isinstance(entry, dict)
    }
    for event, entries in source_hooks.items()
    if isinstance(entries, list)
}

source = set()
for event, entries in source_hooks.items():
    if not isinstance(entries, list):
        continue
    for entry in entries:
        if isinstance(entry, dict):
            source.update(entry_commands(event, entry))

installed = set()
for event, entries in installed_hooks.items():
    if not isinstance(entries, list):
        continue
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        tagged = entry.get("_source") == "ai-toolkit" or any(
            isinstance(hook, dict) and hook.get("_source") == "ai-toolkit"
            for hook in entry.get("hooks", [])
        )
        if tagged or signature(entry) in source_signatures.get(event, set()):
            installed.update(entry_commands(event, entry))

missing = source - installed  # in source, not installed (toolkit got new hooks)
extra = installed - source    # in installed, not source (stale toolkit hook)

if not (missing or extra):
    sys.exit(0)

if missing:
    print(f"  Missing from settings.json ({len(missing)}):")
    for event, matcher, cmd in sorted(missing):
        print(f"    - [{event}] {cmd}")
if extra:
    print(f"  Stale in settings.json ({len(extra)}):")
    for event, matcher, cmd in sorted(extra):
        print(f"    - [{event}] {cmd}")
sys.exit(1)
PY
) || DIFF_STATUS=$?

if [ "$DIFF_STATUS" -ne 0 ] && [ -n "$DIFF" ]; then
    cat >&2 <<EOF
config-desync-guard: ai-toolkit hooks drifted from source manifest.

$DIFF

Fix: re-install canonical state:
    ai-toolkit update
or auto-repair:
    ai-toolkit doctor --fix

Silence advisory (one-off): CLAUDE_SKIP_CONFIG_DESYNC=1
EOF
fi

exit 0
