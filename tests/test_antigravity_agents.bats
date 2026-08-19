#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    export AG_AGENT_TMP
    AG_AGENT_TMP="$(mktemp -d)"
}

teardown() {
    rm -rf "$AG_AGENT_TMP"
}

@test "antigravity agents: emits native frontmatter and explicit tool mapping" {
    run python3 "$TOOLKIT_DIR/scripts/generate_antigravity_agents.py" "$AG_AGENT_TMP"
    [ "$status" -eq 0 ]
    agent="$AG_AGENT_TMP/.agents/agents/ai-toolkit-backend-specialist/agent.md"
    [ -f "$agent" ]
    grep -q '^name: backend-specialist$' "$agent"
    grep -q '^mainAgent: false$' "$agent"
    grep -q '^subagent: true$' "$agent"
    grep -q '^model: inherit$' "$agent"
    grep -q '^commandExecutionPolicy: sandbox$' "$agent"
    grep -q '^  - view_file$' "$agent"
    grep -q '^  - write_to_file$' "$agent"
    grep -q '^  - replace_file_content$' "$agent"
    grep -q '^  - multi_replace_file_content$' "$agent"
    grep -q '^  - run_command$' "$agent"
    grep -q '^  - grep_search$' "$agent"
    grep -q '^  - find_by_name$' "$agent"
    grep -q '^  - list_dir$' "$agent"
}

@test "antigravity agents: orchestration tools map only to known native names" {
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity_agents.py" "$AG_AGENT_TMP" >/dev/null
    agent="$AG_AGENT_TMP/.agents/agents/ai-toolkit-orchestrator/agent.md"
    for tool in invoke_subagent manage_subagents send_message manage_task; do
        grep -q "^  - $tool$" "$agent"
    done
    ! grep -Eq '^  - (Agent|TeamCreate|TeamDelete|SendMessage|TaskCreate|TaskList|TaskUpdate)$' "$agent"
}

@test "antigravity agents: unknown source tool fails before output mutation" {
    mkdir -p "$AG_AGENT_TMP/source"
    cat > "$AG_AGENT_TMP/source/bad.md" <<'MD'
---
name: bad
description: bad agent
tools: Read, Teleport
---
body
MD
    run python3 - "$TOOLKIT_DIR" "$AG_AGENT_TMP" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
import generate_antigravity_agents as generator
generator.generate(Path(sys.argv[2]), source_dir=Path(sys.argv[2]) / "source")
PY
    [ "$status" -ne 0 ]
    [ ! -e "$AG_AGENT_TMP/.agents/agents/ai-toolkit-bad/agent.md" ]
}

@test "antigravity agents: preserves user agents and removes only stale managed agents" {
    mkdir -p "$AG_AGENT_TMP/.agents/agents/user-agent" "$AG_AGENT_TMP/.agents/agents/ai-toolkit-stale"
    printf '%s\n' user > "$AG_AGENT_TMP/.agents/agents/user-agent/agent.md"
    printf '%s\n' '<!-- ai-toolkit-managed: antigravity-agent -->' > "$AG_AGENT_TMP/.agents/agents/ai-toolkit-stale/agent.md"
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity_agents.py" "$AG_AGENT_TMP" >/dev/null
    grep -q user "$AG_AGENT_TMP/.agents/agents/user-agent/agent.md"
    [ ! -e "$AG_AGENT_TMP/.agents/agents/ai-toolkit-stale" ]
}

@test "antigravity agents: regeneration is idempotent and rejects symlink ancestors" {
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity_agents.py" "$AG_AGENT_TMP" >/dev/null
    before="$(find "$AG_AGENT_TMP/.agents/agents" -type f -print0 | sort -z | xargs -0 shasum)"
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity_agents.py" "$AG_AGENT_TMP" >/dev/null
    after="$(find "$AG_AGENT_TMP/.agents/agents" -type f -print0 | sort -z | xargs -0 shasum)"
    [ "$before" = "$after" ]

    project="$AG_AGENT_TMP/project"
    external="$AG_AGENT_TMP/external"
    mkdir -p "$project/.agents" "$external"
    ln -s "$external" "$project/.agents/agents"
    run python3 "$TOOLKIT_DIR/scripts/generate_antigravity_agents.py" "$project"
    [ "$status" -ne 0 ]
    [ -z "$(find "$external" -mindepth 1 -print -quit)" ]
}
