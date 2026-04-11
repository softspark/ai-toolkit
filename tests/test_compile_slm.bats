#!/usr/bin/env bats
# Tests for compile-slm: SLM system prompt compiler
# Run with: bats tests/test_compile_slm.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CLI="node $TOOLKIT_DIR/bin/ai-toolkit.js"
SCRIPT="python3 $TOOLKIT_DIR/scripts/compile_slm.py"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    mkdir -p "$TEST_TMP/.ai-toolkit/compiled"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# ── Token Counter ────────────────────────────────────────────────────────────

@test "compile-slm: token counter returns 0 for empty string" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import estimate_tokens
print(estimate_tokens(''))
"
    [ "$status" -eq 0 ]
    [ "$output" = "0" ]
}

@test "compile-slm: token counter returns positive for text" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import estimate_tokens
result = estimate_tokens('Hello world this is a test')
assert result > 0, f'Expected positive, got {result}'
print(result)
"
    [ "$status" -eq 0 ]
    [ "$output" -gt 0 ]
}

@test "compile-slm: token counter adds code block penalty" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import estimate_tokens
text = 'Some text here'
with_code = text + '\n\`\`\`python\nprint(1)\n\`\`\`'
base = estimate_tokens(text)
coded = estimate_tokens(with_code)
assert coded > base, f'Code penalty not applied: {coded} <= {base}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: token counter char-based dominates for short words" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import estimate_tokens
# A long string with no spaces should use char-based estimate
text = 'abcdefghijklmnopqrstuvwxyz' * 10  # 260 chars, 1 word
result = estimate_tokens(text)
assert result >= 260 // 4, f'Expected >= 65, got {result}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

# ── Component Parser ────────────────────────────────────────────────────────

@test "compile-slm: parser finds constitution" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components
components = parse_components()
names = [c.name for c in components]
assert 'Constitution' in names, f'Constitution not found in {names[:5]}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: constitution has score 1.0" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components
components = parse_components()
const = [c for c in components if c.name == 'Constitution'][0]
assert const.score == 1.0, f'Expected 1.0, got {const.score}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: parser finds guard hooks" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components
components = parse_components()
guards = [c for c in components if c.type == 'hook-rule']
assert len(guards) >= 1, f'Expected >= 1 guard, got {len(guards)}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: parser finds skills" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components
components = parse_components()
skills = [c for c in components if c.type == 'skill']
assert len(skills) > 10, f'Expected > 10 skills, got {len(skills)}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: parser finds agents" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components
components = parse_components()
agents = [c for c in components if c.type == 'agent']
assert len(agents) > 10, f'Expected > 10 agents, got {len(agents)}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: parser finds common rules" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components
components = parse_components()
rules = [c for c in components if c.type == 'rule' and 'common/' in c.name]
assert len(rules) == 5, f'Expected 5 common rules, got {len(rules)}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: persona boosts relevant skills" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components
comp_no_persona = parse_components()
comp_persona = parse_components(persona='backend-lead')
# Find /tdd skill score with and without persona
tdd_base = [c for c in comp_no_persona if '/tdd' in c.name]
tdd_boosted = [c for c in comp_persona if '/tdd' in c.name]
if tdd_base and tdd_boosted:
    assert tdd_boosted[0].score >= tdd_base[0].score, 'Persona did not boost /tdd'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: language filter includes matching rules" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components
components = parse_components(languages=['python'])
py_rules = [c for c in components if c.type == 'rule' and 'python/' in c.name]
assert len(py_rules) > 0, 'No Python rules found'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: no language filter excludes language-specific rules" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components
components = parse_components()
lang_rules = [c for c in components if c.type == 'rule' and 'common/' not in c.name]
assert len(lang_rules) == 0, f'Found language rules without --lang: {[c.name for c in lang_rules]}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

# ── Compression Engine ───────────────────────────────────────────────────────

@test "compile-slm: compression reduces token count" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components, compress_all
components = parse_components()
skills = [c for c in components if c.type == 'skill'][:5]
for s in skills:
    s.tokens_full = s.tokens_full  # already set
compress_all(skills, 'light')
reduced = sum(1 for s in skills if s.tokens_compressed <= s.tokens_full)
assert reduced == len(skills), 'Not all skills were compressed or equal'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: constitution is never compressed" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components, compress_all
components = parse_components()
const = [c for c in components if c.type == 'constitution']
compress_all(const, 'ultra-light')
assert const[0].compressed_text == const[0].full_text, 'Constitution was modified!'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: ultra-light strips more than extended" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components, compress_all, estimate_tokens
components = parse_components()
skills = [c for c in components if c.type == 'skill' and c.tokens_full > 200][:3]
import copy
skills_ul = copy.deepcopy(skills)
skills_ext = copy.deepcopy(skills)
compress_all(skills_ul, 'ultra-light')
compress_all(skills_ext, 'extended')
ul_tokens = sum(s.tokens_compressed for s in skills_ul)
ext_tokens = sum(s.tokens_compressed for s in skills_ext)
assert ul_tokens <= ext_tokens, f'ultra-light ({ul_tokens}) not smaller than extended ({ext_tokens})'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: all 4 compression levels are valid" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import COMPRESSION_LEVELS
levels = list(COMPRESSION_LEVELS.keys())
assert levels == ['ultra-light', 'light', 'standard', 'extended'], f'Unexpected levels: {levels}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

# ── Budget Packer ────────────────────────────────────────────────────────────

@test "compile-slm: packer respects token budget" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components, compress_all, pack_components
components = parse_components()
compress_all(components, 'light')
included, excluded = pack_components(components, 4096, 'light')
total = sum(c.tokens_compressed for c in included)
assert total <= 4096, f'Budget exceeded: {total} > 4096'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: packer always includes constitution" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components, compress_all, pack_components
components = parse_components()
compress_all(components, 'ultra-light')
included, _ = pack_components(components, 2048, 'ultra-light')
names = [c.name for c in included]
assert 'Constitution' in names, f'Constitution not in packed: {names}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: packer enforces max_skills limit" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components, compress_all, pack_components
components = parse_components()
compress_all(components, 'ultra-light')
included, _ = pack_components(components, 99999, 'ultra-light')
skill_count = sum(1 for c in included if c.type == 'skill')
assert skill_count <= 5, f'ultra-light should have max 5 skills, got {skill_count}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: packer enforces max_agents limit" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components, compress_all, pack_components
components = parse_components()
compress_all(components, 'ultra-light')
included, _ = pack_components(components, 99999, 'ultra-light')
agent_count = sum(1 for c in included if c.type == 'agent')
assert agent_count <= 0, f'ultra-light should have max 0 agents, got {agent_count}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: packer excludes rules when include_rules=False" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components, compress_all, pack_components
components = parse_components()
compress_all(components, 'ultra-light')
included, _ = pack_components(components, 99999, 'ultra-light')
rule_count = sum(1 for c in included if c.type == 'rule')
assert rule_count == 0, f'ultra-light should exclude rules, got {rule_count}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: packer includes rules for light level" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components, compress_all, pack_components
components = parse_components()
compress_all(components, 'light')
included, _ = pack_components(components, 8192, 'light')
rule_count = sum(1 for c in included if c.type == 'rule')
assert rule_count > 0, f'light should include rules, got {rule_count}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

# ── Emitter ──────────────────────────────────────────────────────────────────

@test "compile-slm: emitter produces valid markdown" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components, compress_all, pack_components, emit_markdown
components = parse_components()
compress_all(components, 'light')
included, _ = pack_components(components, 4096, 'light')
md = emit_markdown(included)
assert md.startswith('# AI Coding Assistant'), f'Bad header: {md[:50]}'
assert '## Safety Rules' in md, 'Missing Safety Rules section'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: emitter places safety first" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components, compress_all, pack_components, emit_markdown
components = parse_components()
compress_all(components, 'light')
included, _ = pack_components(components, 4096, 'light')
md = emit_markdown(included)
safety_pos = md.index('## Safety Rules')
# Safety must appear before any other section
for section in ['## Coding Standards', '## Key Skills', '## Your Identity']:
    if section in md:
        assert safety_pos < md.index(section), f'Safety not before {section}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: emitter includes constitution text" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components, compress_all, pack_components, emit_markdown
components = parse_components()
compress_all(components, 'light')
included, _ = pack_components(components, 4096, 'light')
md = emit_markdown(included)
assert 'Article I' in md, 'Constitution Article I missing from output'
assert 'No Data Loss' in md, 'Constitution safety rule missing'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

# ── Output Formats ───────────────────────────────────────────────────────────

@test "compile-slm: raw format returns plain markdown" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import format_output
result = format_output('# Test', 'raw')
assert result == '# Test', f'Expected raw output, got: {result}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: ollama format wraps in SYSTEM block" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import format_output
result = format_output('# Test', 'ollama')
assert 'FROM {}' in result, 'Missing FROM line'
assert 'SYSTEM' in result, 'Missing SYSTEM directive'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: json-string format returns valid JSON" {
    run python3 -c "
import sys, json; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import format_output
result = format_output('# Test\nLine 2', 'json-string')
parsed = json.loads(result)
assert '# Test' in parsed, f'JSON content wrong: {parsed}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: aider format returns raw markdown" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import format_output
result = format_output('# Test', 'aider')
assert result == '# Test', f'Expected raw output for aider, got: {result}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

# ── CLI Integration ──────────────────────────────────────────────────────────

@test "compile-slm: --dry-run exits 0" {
    run $SCRIPT --dry-run --model-size 14b
    [ "$status" -eq 0 ]
}

@test "compile-slm: --dry-run shows budget info" {
    run $SCRIPT --dry-run --model-size 14b
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Budget: 4096"
}

@test "compile-slm: --dry-run shows component table" {
    run $SCRIPT --dry-run --model-size 14b
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Constitution"
    echo "$output" | grep -q "YES"
}

@test "compile-slm: --model-size 8b uses 2048 budget" {
    run $SCRIPT --dry-run --model-size 8b
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Budget: 2048"
}

@test "compile-slm: --model-size 32b uses 8192 budget" {
    run $SCRIPT --dry-run --model-size 32b
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Budget: 8192"
}

@test "compile-slm: --budget overrides model-size budget" {
    run $SCRIPT --dry-run --model-size 8b --budget 6000
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Budget: 6000"
}

@test "compile-slm: writes output file" {
    run $SCRIPT --model-size 14b --output "$TEST_TMP/output.md"
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/output.md" ]
}

@test "compile-slm: output file is non-empty" {
    run $SCRIPT --model-size 14b --output "$TEST_TMP/output.md"
    [ "$status" -eq 0 ]
    [ -s "$TEST_TMP/output.md" ]
}

@test "compile-slm: output contains constitution" {
    $SCRIPT --model-size 14b --output "$TEST_TMP/output.md" 2>/dev/null
    grep -q "Article I" "$TEST_TMP/output.md"
}

@test "compile-slm: output starts with markdown header" {
    $SCRIPT --model-size 14b --output "$TEST_TMP/output.md" 2>/dev/null
    head -1 "$TEST_TMP/output.md" | grep -q "^# "
}

@test "compile-slm: --persona flag works" {
    run $SCRIPT --dry-run --model-size 14b --persona backend-lead
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Persona: backend-lead"
}

@test "compile-slm: --lang flag includes language rules" {
    run $SCRIPT --dry-run --model-size 32b --lang python
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "python/"
}

@test "compile-slm: --format ollama produces Modelfile" {
    $SCRIPT --model-size 8b --format ollama --output "$TEST_TMP/modelfile" 2>/dev/null
    head -1 "$TEST_TMP/modelfile" | grep -q "FROM"
}

@test "compile-slm: --format json-string produces valid JSON" {
    $SCRIPT --model-size 8b --format json-string --output "$TEST_TMP/output.json" 2>/dev/null
    python3 -c "import json; json.loads(open('$TEST_TMP/output.json').read())"
}

# ── Compilation Determinism ──────────────────────────────────────────────────

@test "compile-slm: deterministic output (same input = same output)" {
    $SCRIPT --model-size 14b --output "$TEST_TMP/run1.md" 2>/dev/null
    $SCRIPT --model-size 14b --output "$TEST_TMP/run2.md" 2>/dev/null
    diff "$TEST_TMP/run1.md" "$TEST_TMP/run2.md"
}

# ── Budget Compliance ────────────────────────────────────────────────────────

@test "compile-slm: 8b output fits within 2048 tokens" {
    $SCRIPT --model-size 8b --output "$TEST_TMP/output.md" 2>/dev/null
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import estimate_tokens
text = open('$TEST_TMP/output.md').read()
tokens = estimate_tokens(text)
assert tokens <= 2048, f'8b output too large: {tokens} > 2048'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: 14b output fits within 4096 tokens" {
    $SCRIPT --model-size 14b --output "$TEST_TMP/output.md" 2>/dev/null
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import estimate_tokens
text = open('$TEST_TMP/output.md').read()
tokens = estimate_tokens(text)
assert tokens <= 4096, f'14b output too large: {tokens} > 4096'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: 32b output fits within 8192 tokens" {
    $SCRIPT --model-size 32b --output "$TEST_TMP/output.md" 2>/dev/null
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import estimate_tokens
text = open('$TEST_TMP/output.md').read()
tokens = estimate_tokens(text)
assert tokens <= 8192, f'32b output too large: {tokens} > 8192'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

# ── Node CLI pass-through ───────────────────────────────────────────────────

@test "compile-slm: node cli dispatches compile-slm" {
    run $CLI compile-slm --dry-run --model-size 14b
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Budget:"
}

@test "compile-slm: compile-slm appears in help" {
    run $CLI help
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "compile-slm"
}

# ── Model Size Mapping ──────────────────────────────────────────────────────

@test "compile-slm: all model sizes have budget mappings" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import MODEL_BUDGETS
for size in ['7b', '8b', '14b', '32b', '70b']:
    assert size in MODEL_BUDGETS, f'Missing budget for {size}'
    assert 'budget' in MODEL_BUDGETS[size], f'No budget key for {size}'
    assert 'level' in MODEL_BUDGETS[size], f'No level key for {size}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: budgets increase with model size" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import MODEL_BUDGETS
sizes = ['8b', '14b', '32b', '70b']
budgets = [MODEL_BUDGETS[s]['budget'] for s in sizes]
for i in range(1, len(budgets)):
    assert budgets[i] >= budgets[i-1], f'Budget not monotonic: {budgets}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

# ── Manifest Profile ────────────────────────────────────────────────────────

@test "compile-slm: offline-slm profile exists in manifest" {
    run python3 -c "
import json
manifest = json.loads(open('$TOOLKIT_DIR/manifest.json').read())
assert 'offline-slm' in manifest['profiles'], 'offline-slm profile missing'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: offline-slm profile includes core" {
    run python3 -c "
import json
manifest = json.loads(open('$TOOLKIT_DIR/manifest.json').read())
modules = manifest['profiles']['offline-slm']
assert 'core' in modules, f'core not in offline-slm modules: {modules}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

# ── Post-Compilation Validator ───────────────────────────────────────────────

@test "compile-slm: validator passes on valid output" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import parse_components, compress_all, pack_components, emit_markdown, validate_output
components = parse_components()
compress_all(components, 'light')
included, _ = pack_components(components, 4096, 'light')
md = emit_markdown(included)
errors = validate_output(included, md, 4096)
fails = [e for e in errors if e.startswith('FAIL')]
assert len(fails) == 0, f'Unexpected failures: {fails}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: validator catches missing constitution" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import Component, validate_output
fake = [Component(name='test', type='skill', source_file='x', full_text='x', compressed_text='hello world test', tokens_compressed=5)]
errors = validate_output(fake, '# Test output with enough content to pass length check plus more text here', 4096)
assert any('Constitution missing' in e for e in errors), f'Expected constitution error, got: {errors}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: validator catches budget exceeded" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import Component, validate_output
fake = [Component(name='Constitution', type='constitution', source_file='x', full_text='x' * 1000)]
errors = validate_output(fake, 'x' * 10000, 10)
assert any('exceeds budget' in e for e in errors), f'Expected budget error, got: {errors}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: validator catches empty output" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import Component, validate_output
fake = [Component(name='Constitution', type='constitution', source_file='x', full_text='x')]
errors = validate_output(fake, 'short', 4096)
assert any('suspiciously short' in e for e in errors), f'Expected short output error, got: {errors}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

@test "compile-slm: validator warns on missing guards" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from compile_slm import Component, validate_output
fake = [Component(name='Constitution', type='constitution', source_file='x', full_text='x' * 200)]
md = '# AI Coding Assistant\n\n## Safety Rules\n\nConstitution here\n' + 'x' * 200
errors = validate_output(fake, md, 4096)
assert any('guard hooks' in e for e in errors), f'Expected guard warning, got: {errors}'
print('OK')
"
    [ "$status" -eq 0 ]
    [ "$output" = "OK" ]
}

# ── Integration Guides ──────────────────────────────────────────────────────

@test "compile-slm: integration guides print after compilation" {
    run $SCRIPT --model-size 14b --output "$TEST_TMP/output.md"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Ollama Setup"
    echo "$output" | grep -q "LM Studio Setup"
    echo "$output" | grep -q "Aider Setup"
    echo "$output" | grep -q "Continue.dev Setup"
}

@test "compile-slm: integration guides use correct model size" {
    run $SCRIPT --model-size 8b --output "$TEST_TMP/output.md"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "\-\-model-size 8b"
}
