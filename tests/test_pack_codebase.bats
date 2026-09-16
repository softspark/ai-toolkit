#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for pack-codebase: codebase packer for LLM context
# Run with: bats tests/test_pack_codebase.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SCRIPT="python3 $TOOLKIT_DIR/scripts/pack_codebase.py"

setup() {
    TEST_TMP="$(mktemp -d)"
    mkdir -p "$TEST_TMP/src" "$TEST_TMP/docs" "$TEST_TMP/node_modules/foo"
    cat > "$TEST_TMP/src/main.py" <<'EOF'
def hello():
    return "world"
EOF
    cat > "$TEST_TMP/src/util.ts" <<'EOF'
export const add = (a: number, b: number) => a + b;
EOF
    cat > "$TEST_TMP/docs/README.md" <<'EOF'
# Example
This is a docstring.
EOF
    echo "binary garbage" > "$TEST_TMP/node_modules/foo/index.js"
    echo "node_modules/" > "$TEST_TMP/.gitignore"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# ── Discovery ────────────────────────────────────────────────────────────────

@test "pack-codebase: dry-run lists code, config, docs and skips node_modules" {
    run $SCRIPT --root "$TEST_TMP" --budget 50k --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"src/main.py"* ]]
    [[ "$output" == *"src/util.ts"* ]]
    [[ "$output" == *"docs/README.md"* ]]
    [[ "$output" != *"node_modules"* ]]
}

@test "pack-codebase: writes markdown output with TOC and per-file blocks" {
    run $SCRIPT --root "$TEST_TMP" --budget 50k --output "$TEST_TMP/pack.md"
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/pack.md" ]
    grep -q "^# Codebase Pack" "$TEST_TMP/pack.md"
    grep -q "## Table of Contents" "$TEST_TMP/pack.md"
    grep -q '## `src/main.py`' "$TEST_TMP/pack.md"
    grep -q "def hello" "$TEST_TMP/pack.md"
}

# ── Budget enforcement ──────────────────────────────────────────────────────

@test "pack-codebase: tiny budget drops files and reports drop count" {
    run $SCRIPT --root "$TEST_TMP" --budget 5 --output "$TEST_TMP/pack.md"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Dropped"* ]]
}

@test "pack-codebase: --include filters by glob" {
    run $SCRIPT --root "$TEST_TMP" --include "src/*.py" --budget 10k --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"src/main.py"* ]]
    [[ "$output" != *"src/util.ts"* ]]
    [[ "$output" != *"docs/README.md"* ]]
}

@test "pack-codebase: --exclude removes paths" {
    run $SCRIPT --root "$TEST_TMP" --exclude "docs/*" --budget 10k --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" != *"docs/README.md"* ]]
    [[ "$output" == *"src/main.py"* ]]
}

# ── JSON manifest ────────────────────────────────────────────────────────────

@test "pack-codebase: --json outputs valid JSON manifest" {
    run $SCRIPT --root "$TEST_TMP" --budget 10k --json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'files_included' in d and 'budget_tokens' in d"
}

@test "pack-codebase: token estimate uses the measured Claude density, not 4 chars per token" {
    # 0.44 tokens per byte, measured on Claude Code tool output under the 4.7+
    # tokenizer (kb/history/completed/token-usage-remeasurement-20260916.md).
    # Four chars per token would report 550 for 2200 bytes and let a "100k"
    # pack reach roughly 180k real tokens.
    python3 -c "open('$TEST_TMP/src/sized.py', 'w').write('x = 1\n' * 366 + 'y=2\n')"
    run $SCRIPT --root "$TEST_TMP" --include "src/sized.py" --budget 10k --json
    [ "$status" -eq 0 ]
    tokens=$(echo "$output" | python3 -c "import json,sys; print(json.load(sys.stdin)['files_included'][0]['tokens'])")
    [ "$tokens" = "968" ]
}

# ── Truncation ───────────────────────────────────────────────────────────────

@test "pack-codebase: large file gets truncated with marker" {
    python3 -c "
with open('$TEST_TMP/src/big.py', 'w') as f:
    for i in range(2000):
        f.write(f'line_{i} = {i}\n')
"
    run $SCRIPT --root "$TEST_TMP" --max-file-bytes 200 --budget 50k --output "$TEST_TMP/pack.md"
    [ "$status" -eq 0 ]
    grep -q "lines omitted" "$TEST_TMP/pack.md"
}
