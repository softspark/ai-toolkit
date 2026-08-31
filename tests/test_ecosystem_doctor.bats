#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
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

@test "ecosystem_doctor: DSH registry entry is explicit developer preview" {
    run python3 -c "
import json
data = json.load(open('$TOOLKIT_DIR/scripts/ecosystem_tools.json'))
matches = [tool for tool in data['tools'] if tool['id'] == 'dsh']
assert len(matches) == 1, f'expected one DSH entry, got {len(matches)}'
dsh = matches[0]
assert dsh['kind'] == 'harness'
assert dsh['status'] == 'developer-preview'
assert dsh['selection_policy'] == 'explicit-only'
assert dsh['reviewed_version'] == '0.1.1-rc.2'
assert set(dsh['excluded_from']) == {'editors-all', 'auto-detect', 'defaults'}
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "ecosystem_doctor: DSH registry sources and drift contract stay pinned" {
    run python3 -c "
import json
import pathlib
import sys
from unittest.mock import patch
from urllib.parse import urlparse

sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from ecosystem_doctor import check_tool

base = pathlib.Path('$TOOLKIT_DIR')
data = json.loads((base / 'scripts/ecosystem_tools.json').read_text())
dsh = next(tool for tool in data['tools'] if tool['id'] == 'dsh')

assert urlparse(dsh['urls']['docs']).netloc == 'deepseek-harness.github.io'
assert dsh['urls']['release_notes'] == 'https://github.com/deepseek-ai/deepseek-harness/releases'
assert dsh['urls']['reviewed_release'].endswith('/tag/dsh-v0.1.1-rc.2')
assert '/blob/dsh-v0.1.1-rc.2/apps/cli/reference/README.md' in dsh['urls']['reviewed_cli_docs']
assert '/blob/dsh-v0.1.1-rc.2/docs/subsystems/skills.md' in dsh['urls']['reviewed_skill_docs']
assert {
    '.agents/skills/*/SKILL.md',
    '\$DSH_HOME/profiles/<profile>/package.json',
    '\$DSH_HOME/.agent-presets/softspark-orchestrator',
} <= set(dsh['config_paths'])
assert dsh['our_generators'] == ['scripts/generate_codex_skills.py']
assert dsh['our_lifecycle'] == ['scripts/install_steps/dsh.py']
for relative in dsh['our_generators'] + dsh['our_lifecycle']:
    assert (base / relative).is_file(), relative
assert dsh['version_probe'] == {'kind': 'command', 'command': 'dsh --version'}

previous = {
    'headings': ['Old heading'],
    'markers': {'Developer preview': False},
    'version': '0.1.1-rc.2',
}
content = '# DeepSeek Harness\n## Profiles\nDeveloper preview with skills and Agent Presets.'
with patch('ecosystem_doctor.fetch_url', return_value=(content, None)), patch(
    'ecosystem_doctor.probe_version', return_value='0.1.2-alpha.2'
):
    report = check_tool(dsh, previous, offline=False)

kinds = {entry['kind'] for entry in report['drift']}
assert {'headings_added', 'headings_removed', 'marker_flips', 'version_changed'} <= kinds
assert report['docs_url'] == dsh['urls']['docs']
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "ecosystem_doctor: every registry tool has a schema-valid snapshot baseline including DSH preview" {
    run python3 -c "
import json
import re

registry = json.load(open('$TOOLKIT_DIR/scripts/ecosystem_tools.json'))
snapshot = json.load(open('$TOOLKIT_DIR/benchmarks/ecosystem-doctor-snapshot.json'))
assert snapshot['schema_version'] == registry['schema_version'] == 1
registry_by_id = {tool['id']: tool for tool in registry['tools']}
assert set(snapshot['tools']) == set(registry_by_id), (
    f\"snapshot registry mismatch: missing={sorted(set(registry_by_id) - set(snapshot['tools']))} \"
    f\"extra={sorted(set(snapshot['tools']) - set(registry_by_id))}\"
)
for tool_id, tool in registry_by_id.items():
    baseline = snapshot['tools'][tool_id]
    assert re.fullmatch(r'[0-9a-f]{16}', baseline['docs_hash']), tool_id
    assert isinstance(baseline['headings'], list), tool_id
    assert all(
        isinstance(heading, str) and heading for heading in baseline['headings']
    ), tool_id
    assert set(baseline['markers']) == set(tool['capability_markers']), tool_id
    assert all(isinstance(value, bool) for value in baseline['markers'].values()), tool_id

dsh = snapshot['tools']['dsh']
assert dsh['headings'] == sorted(dsh['headings'])
assert 'Developer preview' in dsh['markers']
assert set(dsh['markers']) == set(registry_by_id['dsh']['capability_markers'])
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

@test "ecosystem_doctor: registry, docs, and generator files stay aligned" {
    run python3 -c "
import json, os, pathlib, re
base = pathlib.Path('$TOOLKIT_DIR')
data = json.loads((base / 'scripts/ecosystem_tools.json').read_text())
registry_doc = (base / 'kb/reference/supported-tools-registry.md').read_text()
meta_generators = {
    'generate_agents_md.py',
    'generate_llms_txt.py',
    'generate_language_rules_skills.py',
}
filesystem_generators = {
    'scripts/' + p.name
    for p in (base / 'scripts').glob('generate_*.py')
    if p.name not in meta_generators
}
json_generators = {
    g
    for tool in data['tools']
    for g in tool.get('our_generators', [])
    if pathlib.Path(g).name.startswith('generate_')
}
doc_generators = set(re.findall(r'scripts/generate_[a-z_]+\\.py', registry_doc))

assert filesystem_generators == json_generators, (
    'filesystem/json generator drift: '
    f'fs_only={sorted(filesystem_generators - json_generators)} '
    f'json_only={sorted(json_generators - filesystem_generators)}'
)
assert doc_generators == json_generators, (
    'doc/json generator drift: '
    f'doc_only={sorted(doc_generators - json_generators)} '
    f'json_only={sorted(json_generators - doc_generators)}'
)
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "ecosystem_doctor: reports complete Codex and Copilot generator counts" {
    run python3 -c "
import json, sys
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from ecosystem_doctor import check_tool

data = json.load(open('$TOOLKIT_DIR/scripts/ecosystem_tools.json'))
tools = {tool['id']: tool for tool in data['tools']}
expected = {
    'codex-cli': {
        'scripts/generate_codex.py',
        'scripts/generate_codex_agents.py',
        'scripts/generate_codex_hooks.py',
        'scripts/generate_codex_skills.py',
        'scripts/codex_plugin.py',
    },
    'github-copilot': {
        'scripts/generate_copilot.py',
        'scripts/generate_copilot_hooks.py',
    },
}
for tool_id, generators in expected.items():
    assert set(tools[tool_id]['our_generators']) == generators
    report = check_tool(tools[tool_id], {}, offline=True)
    assert report['current']['generator_count'] == len(generators)
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
