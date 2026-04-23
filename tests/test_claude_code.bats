#!/usr/bin/env bats
# Claude Code integration schema tests.
#
# Verifies ai-toolkit's tracked frontmatter + hook-event surface stays in
# sync with what Claude Code currently accepts. These are pure schema
# assertions — they do not invoke Claude Code, so they run offline.
#
# Run with: bats tests/test_claude_code.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

# ── Hook event allowlist ─────────────────────────────────────────────────────

@test "claude-code: validate.py VALID_HOOK_EVENTS covers every event in the CHANGELOG tracked today" {
    # These are the events mentioned in the CHANGELOG as of 2.1.118.
    # When Anthropic ships a new hook event, add it here AND to validate.py.
    expected=(
        SessionStart SessionEnd UserPromptSubmit Notification
        PreToolUse PostToolUse
        Stop StopFailure
        SubagentStart SubagentStop
        PreCompact PostCompact
        PermissionRequest PermissionDenied
        Elicitation ElicitationResult
        TaskCreated TaskCompleted TeammateIdle
        WorktreeCreate WorktreeRemove
        CwdChanged FileChanged ConfigChange
        Setup InstructionsLoaded
    )
    missing=()
    for ev in "${expected[@]}"; do
        grep -q "\"${ev}\"" "$TOOLKIT_DIR/scripts/validate.py" || missing+=("$ev")
    done
    if [ "${#missing[@]}" -ne 0 ]; then
        echo "Missing hook events in validate.py VALID_HOOK_EVENTS: ${missing[*]}" >&2
        return 1
    fi
}

@test "claude-code: validate.py rejects a bogus hook event name" {
    # Regression: ensure the allowlist is actually enforced.
    run python3 -c "
import sys
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from validate import VALID_HOOK_EVENTS
assert 'TotallyMadeUpEvent' not in VALID_HOOK_EVENTS
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

# ── hook-creator skill ───────────────────────────────────────────────────────

@test "hook-creator SKILL.md documents the new hook events added in Claude Code 2.1.x" {
    skill="$TOOLKIT_DIR/app/skills/hook-creator/SKILL.md"
    for ev in StopFailure PostCompact PermissionDenied Elicitation ElicitationResult TaskCreated WorktreeCreate WorktreeRemove CwdChanged FileChanged ConfigChange InstructionsLoaded; do
        grep -q "\`${ev}\`" "$skill" || { echo "Missing \`${ev}\` row in hook-creator/SKILL.md" >&2; return 1; }
    done
}

@test "hook-creator SKILL.md documents every hook handler type Claude Code supports" {
    skill="$TOOLKIT_DIR/app/skills/hook-creator/SKILL.md"
    for ty in command prompt agent mcp_tool; do
        grep -q "\`${ty}\`" "$skill" || { echo "Missing handler type \`${ty}\` in hook-creator/SKILL.md" >&2; return 1; }
    done
}

# ── skill-creator frontmatter reference ─────────────────────────────────────

@test "skill-creator SKILL.md references the new frontmatter fields Claude Code accepts" {
    skill="$TOOLKIT_DIR/app/skills/skill-creator/SKILL.md"
    # xhigh effort level (Opus 4.7) — plain string, not backticked.
    grep -q 'xhigh' "$skill" || { echo "Missing xhigh effort level" >&2; return 1; }
    # Field names in the frontmatter reference table are backticked.
    for field in 'disallowedTools' 'memory' 'skills' 'maxTurns'; do
        grep -q "\`${field}\`" "$skill" || { echo "Missing \`${field}\` row in skill-creator/SKILL.md" >&2; return 1; }
    done
}

# ── registry sanity ──────────────────────────────────────────────────────────

@test "claude-code: ecosystem registry lists claude-code as kind=primary" {
    run python3 -c "
import json
d = json.load(open('$TOOLKIT_DIR/scripts/ecosystem_tools.json'))
entries = [t for t in d['tools'] if t['id'] == 'claude-code']
assert len(entries) == 1, 'claude-code missing from registry'
assert entries[0]['kind'] == 'primary'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "claude-code: existing generators keep producing the SKILL.md shipping shape" {
    # We do not ship a Claude Code generator — skills and agents ship as-is.
    # Assert the baseline directories still exist so downstream tools can consume them.
    [ -d "$TOOLKIT_DIR/app/skills" ]
    [ -d "$TOOLKIT_DIR/app/agents" ]
    [ -f "$TOOLKIT_DIR/app/hooks.json" ]
}
