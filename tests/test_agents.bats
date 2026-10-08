#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for agent definitions correctness — single-pass validation

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
AGENTS_DIR="$TOOLKIT_DIR/app/agents"

@test "at least 40 agent files exist" {
    count=$(ls "$AGENTS_DIR"/*.md 2>/dev/null | wc -l)
    [ "$count" -ge 40 ]
}

@test "all agents pass structural validation (name, description, tools, format, length, filename match)" {
    errors=0
    for f in "$AGENTS_DIR"/*.md; do
        filename=$(basename "$f" .md)
        # Single awk: extract name, description, tools in one pass (no eval — safe from injection)
        fm_name=$(awk '/^---/{fc++; next} fc==1 && /^name:/{gsub(/^name:[[:space:]]*/,""); gsub(/^"/,""); gsub(/"$/,""); print; exit}' "$f")
        fm_desc=$(awk '/^---/{fc++; next} fc==1 && /^description:/{found=1} fc>=2{exit} END{if(found) print 1}' "$f")
        fm_tools=$(awk '/^---/{fc++; next} fc==1 && /^tools:/{found=1} fc>=2{exit} END{if(found) print 1}' "$f")

        if [ -z "${fm_name:-}" ]; then
            echo "MISSING name: $f"; errors=$((errors+1))
        else
            if echo "$fm_name" | grep -qE '[^a-z0-9-]'; then
                echo "INVALID name format: $fm_name in $f"; errors=$((errors+1))
            fi
            if [ "${#fm_name}" -gt 64 ]; then
                echo "NAME TOO LONG (${#fm_name} chars): $fm_name"; errors=$((errors+1))
            fi
            if [ "$filename" != "$fm_name" ]; then
                echo "MISMATCH: file=$filename name=$fm_name"; errors=$((errors+1))
            fi
        fi
        [ -z "${fm_desc:-}" ] && { echo "MISSING description: $f"; errors=$((errors+1)); }
        [ -z "${fm_tools:-}" ] && { echo "MISSING tools: $f"; errors=$((errors+1)); }
        unset fm_name fm_desc fm_tools
    done
    [ "$errors" -eq 0 ]
}

# The repository's AGENTS.md is committed contributor instructions; the
# toolkit instruction core is generated on demand, so these tests generate it
# fresh instead of reading a repo-root file.
@test "no build step writes over the repository's own AGENTS.md" {
    python3 - "$TOOLKIT_DIR" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
package = json.loads((root / 'package.json').read_text())
for name, command in package['scripts'].items():
    assert '> AGENTS.md' not in command, f'{name} overwrites AGENTS.md'
assert 'AGENTS.md' not in package['files'], 'repo AGENTS.md shipped in the tarball'
head = (root / 'AGENTS.md').read_text(encoding='utf-8').splitlines()[0]
assert head != '# AI Toolkit Instructions', 'AGENTS.md holds the generated core'
ignore = (root / '.gitignore').read_text(encoding='utf-8').splitlines()
assert not {'AGENTS.md', '/AGENTS.md'} & set(ignore), 'AGENTS.md is gitignored'
PY
    grep -q '^@AGENTS.md$' "$TOOLKIT_DIR/CLAUDE.md"
}

@test "generate_agents_md.py produces non-empty AGENTS.md content" {
    run bash -c "cd '$TOOLKIT_DIR' && AI_TOOLKIT_NO_CUSTOM_RULES=1 python3 scripts/generate_agents_md.py"
    [ "$status" -eq 0 ]
    [ -n "$output" ]
}

@test "generated AGENTS.md keeps the agent catalog out of always-on context" {
    agents_content=$(cd "$TOOLKIT_DIR" && AI_TOOLKIT_NO_CUSTOM_RULES=1 python3 scripts/generate_agents_md.py)
    if echo "$agents_content" | grep -q '^## Available Agents'; then
        echo "agent catalog duplicated in effective AGENTS.md"
        return 1
    fi
    if echo "$agents_content" | grep -q '^## Available Skills'; then
        echo "skill catalog duplicated in effective AGENTS.md"
        return 1
    fi
    [ "$(printf '%s' "$agents_content" | wc -c | xargs)" -lt 32768 ]
}
