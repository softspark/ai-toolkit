#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Per-tool tests for Gemini CLI integration (generate_gemini.py).
#
# Upstream docs (as of 2026-04-23): https://github.com/google-gemini/gemini-cli
# Config surface we track:
#   - GEMINI.md (context file, hierarchical: ~/.gemini/, workspace, JIT)
#   - .gemini/settings.json (+ ~/.gemini/settings.json)
#   - .gemini/commands/*.toml (custom slash commands)
#   - .gemini/skills/  or  .agents/skills/  (SKILL.md per agentskills.io)
#   - .gemini/agents/*.md (native local subagents)
#   - extensions/<name>/gemini-extension.json (extension package root)
#   - hooks in settings.json: BeforeTool, AfterTool, BeforeToolSelection,
#     BeforeAgent, AfterAgent, BeforeModel, AfterModel, Notification,
#     PreCompress, SessionStart, SessionEnd (11 documented events; no Stop)
# Gemini surfaces are split across dedicated generators so each native schema
# can be validated independently.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export GEM_OUT; GEM_OUT="$(mktemp)"
    python3 "$TOOLKIT_DIR/scripts/generate_gemini.py" > "$GEM_OUT" 2>/dev/null
    echo $? > "$GEM_OUT.status"
}

teardown_file() {
    rm -f "$GEM_OUT" "$GEM_OUT.status"
}

@test "generate_gemini.py exits 0" {
    [ "$(cat "$GEM_OUT.status")" = "0" ]
}

@test "generate_gemini.py output is non-empty" {
    [ "$(wc -c < "$GEM_OUT" | xargs)" -gt 500 ]
}

@test "generate_gemini.py output has GEMINI.md heading conventions" {
    # Must have at least one top-level and one second-level header so the CLI
    # shows proper structure when it loads GEMINI.md into context.
    grep -qE '^# '  "$GEM_OUT"
    grep -qE '^## ' "$GEM_OUT"
}

@test "generate_gemini.py output is wrapped in TOOLKIT markers" {
    grep -q '<!-- TOOLKIT:ai-toolkit START -->' "$GEM_OUT"
    grep -q '<!-- TOOLKIT:ai-toolkit END -->'   "$GEM_OUT"
}

@test "generate_gemini.py output lists agents as bullet entries" {
    grep -q '## Available Agents' "$GEM_OUT"
    # At least one bullet with an agent name in bold.
    grep -qE '^- \*\*[a-z][a-z-]+\*\*:' "$GEM_OUT"
}

@test "generate_gemini.py output lists every agent file in app/agents/" {
    local missing=0
    for f in "$TOOLKIT_DIR"/app/agents/*.md; do
        local name="${f##*/}"; name="${name%.md}"
        grep -q "$name" "$GEM_OUT" || missing=$((missing + 1))
    done
    [ "$missing" -eq 0 ]
}

@test "generate_gemini.py output references skills section" {
    grep -q '## Available Skills' "$GEM_OUT"
}

@test "generate_gemini.py output includes guidelines (quality_standards + workflow)" {
    # generator_base injects these guideline blocks per config. Ensure they
    # made it through. Exact headings depend on emission.generate_* helpers.
    grep -qiE 'quality|standards|gates'  "$GEM_OUT"
    grep -qiE 'workflow|planning|review' "$GEM_OUT"
}

@test "generate_gemini.py references ai-toolkit attribution" {
    grep -qiE 'ai.?toolkit' "$GEM_OUT"
}

# ── Native subagents ───────────────────────────────────────────────────────────────

@test "gemini agents: emits native local-agent schema and source body" {
    tmp="$(mktemp -d)"
    run python3 "$TOOLKIT_DIR/scripts/generate_gemini_agents.py" "$tmp"
    [ "$status" -eq 0 ]

    agent="$tmp/.gemini/agents/ai-toolkit-debugger.md"
    [ -f "$agent" ]
    expected=$(find "$TOOLKIT_DIR/app/agents" -maxdepth 1 -name '*.md' -type f | wc -l | xargs)
    actual=$(find "$tmp/.gemini/agents" -maxdepth 1 -name 'ai-toolkit-*.md' -type f | wc -l | xargs)
    [ "$actual" -eq "$expected" ]
    grep -q '^name: debugger$' "$agent"
    grep -q '^description: ' "$agent"
    grep -q '^kind: local$' "$agent"
    grep -q '<!-- ai-toolkit-managed: gemini-agent -->' "$agent"
    grep -q 'Root cause analysis' "$agent"
    ! grep -qE '^(model|tools):' "$agent"

    rm -rf "$tmp"
}

@test "gemini agents: preserves user files and removes only stale managed files" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.gemini/agents"
    printf '%s\n' 'user-owned' > "$tmp/.gemini/agents/user-agent.md"
    printf '%s\n' 'user-owned collision' > "$tmp/.gemini/agents/ai-toolkit-debugger.md"
    printf '%s\n' '<!-- ai-toolkit-managed: gemini-agent -->' \
        > "$tmp/.gemini/agents/ai-toolkit-stale.md"

    run python3 "$TOOLKIT_DIR/scripts/generate_gemini_agents.py" "$tmp"
    [ "$status" -eq 0 ]
    grep -q '^user-owned$' "$tmp/.gemini/agents/user-agent.md"
    grep -q '^user-owned collision$' "$tmp/.gemini/agents/ai-toolkit-debugger.md"
    [ ! -e "$tmp/.gemini/agents/ai-toolkit-stale.md" ]

    rm -rf "$tmp"
}

@test "gemini agents: rejects symlinked output ancestors without external writes" {
    tmp="$(mktemp -d)"
    project="$tmp/project"
    external="$tmp/external"
    mkdir -p "$project/.gemini" "$external"
    ln -s "$external" "$project/.gemini/agents"

    run python3 "$TOOLKIT_DIR/scripts/generate_gemini_agents.py" "$project"
    [ "$status" -ne 0 ]
    [ -z "$(find "$external" -mindepth 1 -print -quit)" ]

    rm -rf "$tmp"
}

@test "gemini agents: invalid source fails before any output mutation" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/source"
    cat > "$tmp/source/good.md" <<'MD'
---
name: good
description: good agent
model: opus
tools: Read, Bash
---
good system prompt
MD
    cat > "$tmp/source/bad.md" <<'MD'
---
name: ../bad
description: bad agent
---
bad system prompt
MD

    run python3 - "$TOOLKIT_DIR" "$tmp" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
import generate_gemini_agents as generator
try:
    generator.generate(Path(sys.argv[2]), source_dir=Path(sys.argv[2]) / "source")
except ValueError as error:
    assert "Invalid Gemini agent name" in str(error), error
else:
    raise AssertionError("invalid Gemini agent source was accepted")
PY
    [ "$status" -eq 0 ]
    [ ! -e "$tmp/.gemini/agents/ai-toolkit-good.md" ]

    rm -rf "$tmp"
}

@test "gemini agents: duplicate source names fail during preflight" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/source"
    for file in one two; do
        cat > "$tmp/source/$file.md" <<'MD'
---
name: duplicate
description: duplicate agent
---
system prompt
MD
    done

    run python3 - "$TOOLKIT_DIR" "$tmp" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
import generate_gemini_agents as generator
try:
    generator.generate(Path(sys.argv[2]), source_dir=Path(sys.argv[2]) / "source")
except ValueError as error:
    assert "Duplicate Gemini agent name" in str(error), error
else:
    raise AssertionError("duplicate Gemini agent names were accepted")
PY
    [ "$status" -eq 0 ]
    [ ! -e "$tmp/.gemini/agents/ai-toolkit-duplicate.md" ]

    rm -rf "$tmp"
}

@test "gemini agents: generate:all includes the native agent generator" {
    run python3 - "$TOOLKIT_DIR/package.json" <<'PY'
import json
import sys
from pathlib import Path

scripts = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["scripts"]
assert scripts["generate:gemini-agents"] == (
    "python3 scripts/generate_gemini_agents.py ."
)
assert "generate:gemini-agents" in scripts["generate:all"]
PY
    [ "$status" -eq 0 ]
}

@test "gemini hooks: supported event contract stays at the documented 11 events" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from generate_gemini_hooks import GEMINI_SUPPORTED_HOOK_EVENTS

assert GEMINI_SUPPORTED_HOOK_EVENTS == (
    "BeforeTool",
    "AfterTool",
    "BeforeToolSelection",
    "BeforeAgent",
    "AfterAgent",
    "BeforeModel",
    "AfterModel",
    "Notification",
    "PreCompress",
    "SessionStart",
    "SessionEnd",
)
assert "Stop" not in GEMINI_SUPPORTED_HOOK_EVENTS
PY
    [ "$status" -eq 0 ]
}
