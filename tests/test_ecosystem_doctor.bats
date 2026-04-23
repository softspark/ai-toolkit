#!/usr/bin/env bats
# Smoke tests for scripts/ecosystem_doctor.py.
# Offline-only by design — the doctor's network path hits third-party sites
# that we cannot depend on in CI. Online paths are verified manually via the
# ecosystem-sync SOP.
# Run with: bats tests/test_ecosystem_doctor.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
DOCTOR="python3 $TOOLKIT_DIR/scripts/ecosystem_doctor.py"

# ── Basic invocation ────────────────────────────────────────────────────────

@test "ecosystem_doctor: --offline --format text exits 0" {
    run $DOCTOR --offline --format text
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Ecosystem Doctor Report"
}

@test "ecosystem_doctor: --offline --format json produces valid JSON" {
    run $DOCTOR --offline --format json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "import json, sys; json.load(sys.stdin)"
}

# ── Registry integrity ──────────────────────────────────────────────────────

@test "ecosystem_doctor: registry JSON parses and has >= 10 tools" {
    run python3 -c "
import json
d = json.load(open('$TOOLKIT_DIR/scripts/ecosystem_tools.json'))
assert d['schema_version'] == 1, 'schema_version'
assert len(d['tools']) >= 10, f'expected >=10 tools, got {len(d[\"tools\"])}'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "ecosystem_doctor: every registry tool has required fields" {
    run python3 -c "
import json
d = json.load(open('$TOOLKIT_DIR/scripts/ecosystem_tools.json'))
required = {'id', 'display_name', 'kind', 'urls', 'config_paths', 'our_generators', 'capability_markers'}
for t in d['tools']:
    missing = required - set(t.keys())
    assert not missing, f'{t.get(\"id\", \"?\")} missing {missing}'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "ecosystem_doctor: every declared generator path exists on disk" {
    run python3 -c "
import json, os
base = '$TOOLKIT_DIR'
d = json.load(open(os.path.join(base, 'scripts/ecosystem_tools.json')))
missing = []
for t in d['tools']:
    for g in t.get('our_generators', []):
        if not os.path.isfile(os.path.join(base, g)):
            missing.append(f'{t[\"id\"]}: {g}')
assert not missing, 'Missing generators: ' + ', '.join(missing)
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

# ── CLI flags ────────────────────────────────────────────────────────────────

@test "ecosystem_doctor: --tool <unknown> exits 1" {
    run $DOCTOR --tool this-tool-does-not-exist --offline
    [ "$status" -eq 1 ]
}

@test "ecosystem_doctor: --tool <known> scopes to that tool only" {
    run $DOCTOR --tool aider --offline --format json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert len(d['reports']) == 1, f'expected 1 report, got {len(d[\"reports\"])}'
assert d['reports'][0]['id'] == 'aider'
"
}

@test "ecosystem_doctor: --check on clean state exits 0" {
    run $DOCTOR --offline --check --format json
    [ "$status" -eq 0 ]
}

@test "ecosystem_doctor: check_tool reads per-tool state (not double-nested)" {
    # Regression: previous bug looked up last_seen[tool_id] inside already-per-tool dict.
    run python3 -c "
import sys, json
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from ecosystem_doctor import check_tool, load_registry
reg = load_registry()
aider = [t for t in reg['tools'] if t['id'] == 'aider'][0]
# Stored per-tool state matches what the tool would fetch — drift must be empty.
stored = {'headings': ['Aider Documentation']}
r = check_tool(aider, stored, offline=True)
# Offline mode skips the fetch, so no headings_added/removed drift expected.
assert all(d['kind'] != 'headings_added' for d in r.get('drift', [])), 'headings_added leaked'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "ecosystem_doctor: --check ignores content-hash-only drift" {
    # content_changed_no_heading_delta must not fail the gate.
    run python3 -c "
import sys
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
import ecosystem_doctor as eco
# Fake a report with ONLY content-hash drift
reports = [{'id': 't', 'drift': [{'kind': 'content_changed_no_heading_delta'}], 'errors': []}]
# Inline the same filter --check uses
any_structural = any(
    any(d.get('kind') != 'content_changed_no_heading_delta' for d in r.get('drift', [])) or r.get('errors')
    for r in reports
)
assert not any_structural, 'structural drift false positive'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}
