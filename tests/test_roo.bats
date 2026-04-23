#!/usr/bin/env bats
# Dedicated tests for scripts/generate_roo_modes.py and
# scripts/generate_roo_rules.py.
#
# Roo Code is a Cline fork with a different mode system. Key surfaces:
#   - .roomodes JSON (custom modes; slug/name/description/roleDefinition/whenToUse/groups)
#   - .roo/rules/*.md (shared rules, loaded for all modes)
#
# This suite verifies the mode schema matches the current Roo docs
# (features/custom-modes) and that the rules directory mirrors the
# ai-toolkit rule catalogue.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export ROO_TMP; ROO_TMP="$(mktemp -d)"
    export ROOMODES="$ROO_TMP/roomodes.json"
    python3 "$TOOLKIT_DIR/scripts/generate_roo_modes.py" > "$ROOMODES" 2>/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_roo_rules.py" "$ROO_TMP" >/dev/null 2>&1
}

teardown_file() {
    rm -rf "$ROO_TMP"
}

# ── .roomodes JSON shape ───────────────────────────────────────────────────

@test "generate_roo_modes.py output is valid JSON" {
    python3 -c "import json; json.load(open('$ROOMODES'))"
}

@test "generate_roo_modes.py output has customModes array" {
    python3 -c "
import json
d = json.load(open('$ROOMODES'))
assert isinstance(d.get('customModes'), list), 'customModes must be a list'
assert len(d['customModes']) > 0, 'must contain at least one mode'
"
}

@test "generate_roo_modes.py every mode has required top-level fields" {
    python3 -c "
import json
d = json.load(open('$ROOMODES'))
required = {'slug', 'name', 'description', 'roleDefinition', 'groups'}
for m in d['customModes']:
    missing = required - m.keys()
    assert not missing, f'mode {m.get(\"slug\")} missing {missing}'
"
}

@test "generate_roo_modes.py every mode has whenToUse hint for orchestrator" {
    python3 -c "
import json
d = json.load(open('$ROOMODES'))
missing = [m['slug'] for m in d['customModes'] if not m.get('whenToUse')]
assert not missing, f'modes missing whenToUse: {missing}'
"
}

@test "generate_roo_modes.py slug matches Roo regex /^[a-zA-Z0-9-]+$/" {
    python3 -c "
import json, re
d = json.load(open('$ROOMODES'))
pattern = re.compile(r'^[a-zA-Z0-9-]+\$')
for m in d['customModes']:
    assert pattern.match(m['slug']), f'invalid slug: {m[\"slug\"]}'
"
}

@test "generate_roo_modes.py groups list contains expected tool buckets" {
    python3 -c "
import json
d = json.load(open('$ROOMODES'))
for m in d['customModes']:
    g = set(m['groups'])
    # Roo accepts 'read', 'edit', 'browser', 'command', 'mcp'
    assert g <= {'read', 'edit', 'browser', 'command', 'mcp'}, f'unknown group in {m[\"slug\"]}: {g}'
"
}

@test "generate_roo_modes.py roleDefinition contains the agent description prefix" {
    python3 -c "
import json
d = json.load(open('$ROOMODES'))
# First few chars of roleDefinition should match description (we prepend it)
for m in d['customModes']:
    assert m['roleDefinition'].startswith(m['description'][:30]), \
        f'{m[\"slug\"]}: roleDefinition should lead with description'
"
}

@test "generate_roo_modes.py contains at least 10 modes" {
    python3 -c "
import json
d = json.load(open('$ROOMODES'))
assert len(d['customModes']) >= 10, f'only {len(d[\"customModes\"])} modes'
"
}

# ── .roo/rules/ directory ──────────────────────────────────────────────────

@test "generate_roo_rules.py creates .roo/rules/ directory" {
    [ -d "$ROO_TMP/.roo/rules" ]
}

@test "generate_roo_rules.py emits at least 6 standard rule files" {
    count=$(ls "$ROO_TMP/.roo/rules"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 6 ]
}

@test "generate_roo_rules.py rule files are non-empty markdown" {
    for f in "$ROO_TMP/.roo/rules"/ai-toolkit-*.md; do
        [ -s "$f" ] || { echo "Empty: $f"; return 1; }
        grep -q '^#' "$f" || { echo "No heading: $f"; return 1; }
    done
}

@test "generate_roo_rules.py agents-and-skills file lists every agent" {
    missing=0
    for f in "$TOOLKIT_DIR"/app/agents/*.md; do
        agent_name="${f##*/}"; agent_name="${agent_name%.md}"
        grep -q "$agent_name" "$ROO_TMP/.roo/rules/ai-toolkit-agents-and-skills.md" || missing=$((missing + 1))
    done
    [ "$missing" -eq 0 ]
}

# ── Language rules (Roo: unconditionally loaded per rule file) ─────────────

@test "generate_roo_rules.py honors language_modules" {
    local tmp; tmp="$(mktemp -d)"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_roo_rules import generate
generate(Path('$tmp'), language_modules=['rules-typescript'])
" >/dev/null 2>&1
    [ -f "$tmp/.roo/rules/ai-toolkit-lang-common.md" ]
    [ -f "$tmp/.roo/rules/ai-toolkit-lang-typescript.md" ]
    rm -rf "$tmp"
}

# ── Idempotency ────────────────────────────────────────────────────────────

@test "generate_roo_rules.py is idempotent across reruns" {
    local tmp; tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_roo_rules.py" "$tmp" >/dev/null 2>&1
    count1=$(ls "$tmp/.roo/rules"/ai-toolkit-*.md | wc -l | xargs)
    python3 "$TOOLKIT_DIR/scripts/generate_roo_rules.py" "$tmp" >/dev/null 2>&1
    count2=$(ls "$tmp/.roo/rules"/ai-toolkit-*.md | wc -l | xargs)
    [ "$count1" -eq "$count2" ]
    rm -rf "$tmp"
}

@test "generate_roo_rules.py preserves user rule files" {
    local tmp; tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_roo_rules.py" "$tmp" >/dev/null 2>&1
    echo "user rule" > "$tmp/.roo/rules/my-team-rules.md"
    python3 "$TOOLKIT_DIR/scripts/generate_roo_rules.py" "$tmp" >/dev/null 2>&1
    grep -q '^user rule$' "$tmp/.roo/rules/my-team-rules.md"
    rm -rf "$tmp"
}
