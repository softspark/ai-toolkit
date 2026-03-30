#!/usr/bin/env bats
# Negative tests for validate.py — each test injects a specific defect and verifies detection.
# Uses a minimal fixture (~3 agents, ~3 skills) instead of copying the full toolkit.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

_build_minimal_fixture() {
    local dir="$1"
    mkdir -p "$dir"/{app/agents,app/skills/sample-skill,app/hooks,app/plugins,kb/reference,benchmarks,scripts}

    # Minimal agents
    for agent in alpha-agent beta-agent gamma-agent; do
        cat > "$dir/app/agents/$agent.md" <<EOF
---
name: $agent
description: Test agent $agent
tools: Read, Write
model: sonnet
---
A test agent.
EOF
    done

    # Minimal skill
    cat > "$dir/app/skills/sample-skill/SKILL.md" <<'EOF'
---
name: sample-skill
description: A sample skill for testing
---
Sample skill content.
EOF

    # Minimal hooks.json
    cat > "$dir/app/hooks.json" <<'EOF'
{
    "hooks": {
        "SessionStart": [
            {
                "_source": "ai-toolkit",
                "matcher": "startup",
                "hooks": [{ "type": "command", "command": "echo ok" }]
            }
        ]
    }
}
EOF

    # All planned assets required by validate.py
    mkdir -p "$dir/app/.claude-plugin"
    echo '{"name":"test","version":"1.0.0","description":"test"}' > "$dir/app/.claude-plugin/plugin.json"
    touch "$dir/scripts/doctor.py"
    touch "$dir/scripts/benchmark_ecosystem.py"
    touch "$dir/scripts/harvest-ecosystem.sh"
    for hook in pre-compact post-tool-use user-prompt-submit subagent-start subagent-stop session-end track-usage; do
        echo "#!/bin/bash" > "$dir/app/hooks/$hook.sh"
    done
    for skill in hook-creator command-creator agent-creator plugin-creator; do
        mkdir -p "$dir/app/skills/$skill"
        cat > "$dir/app/skills/$skill/SKILL.md" <<SKILL
---
name: $skill
description: Test skill $skill
---
Test.
SKILL
    done
    echo '{}' > "$dir/benchmarks/ecosystem-dashboard.json"
    for doc in claude-ecosystem-benchmark-snapshot plugin-pack-conventions; do
        cat > "$dir/kb/reference/$doc.md" <<DOC
---
title: "Test Doc"
category: reference
service: ai-toolkit
tags: [test]
created: "2026-03-30"
last_updated: "2026-03-30"
description: "Test doc."
---
Content.
DOC
    done

    # Copy validate script
    cp "$TOOLKIT_DIR/scripts/validate.py" "$dir/scripts/validate.py"

    # Minimal README
    echo "# Test" > "$dir/README.md"
}

setup() {
    TEST_DIR="$(mktemp -d)"
    _build_minimal_fixture "$TEST_DIR"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# ── Agent field validation ───────────────────────────────────────────────────

@test "validate.py catches agent missing name field" {
    cat > "$TEST_DIR/app/agents/no-name-agent.md" <<'EOF'
---
description: Agent without name
tools: Read, Write
model: sonnet
---
This agent has no name field.
EOF
    run python3 "$TOOLKIT_DIR/scripts/validate.py" "$TEST_DIR"
    [ "$status" -ne 0 ]
    echo "$output" | grep -qi "missing.*field.*name\|name.*missing"
}

@test "validate.py catches agent missing description field" {
    cat > "$TEST_DIR/app/agents/no-desc-agent.md" <<'EOF'
---
name: no-desc-agent
tools: Read, Write
model: sonnet
---
This agent has no description.
EOF
    run python3 "$TOOLKIT_DIR/scripts/validate.py" "$TEST_DIR"
    [ "$status" -ne 0 ]
    echo "$output" | grep -qi "missing.*field.*description\|description.*missing"
}

@test "validate.py catches agent missing tools field" {
    cat > "$TEST_DIR/app/agents/no-tools-agent.md" <<'EOF'
---
name: no-tools-agent
description: Agent without tools
model: sonnet
---
Missing tools field.
EOF
    run python3 "$TOOLKIT_DIR/scripts/validate.py" "$TEST_DIR"
    [ "$status" -ne 0 ]
    echo "$output" | grep -qi "Missing.*field.*tools\|Missing tools"
}

# ── Skill field validation ───────────────────────────────────────────────────

@test "validate.py catches skill missing name in SKILL.md" {
    mkdir -p "$TEST_DIR/app/skills/broken-skill"
    cat > "$TEST_DIR/app/skills/broken-skill/SKILL.md" <<'EOF'
---
description: A broken skill
---
No name field here.
EOF
    run python3 "$TOOLKIT_DIR/scripts/validate.py" "$TEST_DIR"
    [ "$status" -ne 0 ]
    echo "$output" | grep -qi "Missing name"
}

@test "validate.py catches missing depends-on reference" {
    mkdir -p "$TEST_DIR/app/skills/dep-test"
    cat > "$TEST_DIR/app/skills/dep-test/SKILL.md" <<'EOF'
---
name: dep-test
description: "Skill with broken dependency"
depends-on: nonexistent-skill
---
This skill depends on something that does not exist.
EOF
    run python3 "$TOOLKIT_DIR/scripts/validate.py" "$TEST_DIR"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "depends-on 'nonexistent-skill' not found"
}

# ── Hook validation ──────────────────────────────────────────────────────────

@test "validate.py catches unsupported hook event name" {
    python3 -c "
import json
with open('$TEST_DIR/app/hooks.json') as f:
    data = json.load(f)
data['hooks']['BogusEvent'] = [{'_source': 'ai-toolkit', 'matcher': '', 'hooks': [{'type': 'command', 'command': 'echo test'}]}]
with open('$TEST_DIR/app/hooks.json', 'w') as f:
    json.dump(data, f, indent=4)
"
    run python3 "$TOOLKIT_DIR/scripts/validate.py" "$TEST_DIR"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Unknown hook event.*BogusEvent"
}

# ── Planned assets ───────────────────────────────────────────────────────────

@test "validate.py catches missing planned assets" {
    rm -f "$TEST_DIR/kb/reference/claude-ecosystem-benchmark-snapshot.md"
    rm -f "$TEST_DIR/benchmarks/ecosystem-dashboard.json"
    rm -f "$TEST_DIR/app/hooks/post-tool-use.sh"
    rm -f "$TEST_DIR/app/hooks/session-end.sh"
    mkdir -p "$TEST_DIR/kb/reference" "$TEST_DIR/benchmarks"
    run python3 "$TOOLKIT_DIR/scripts/validate.py" "$TEST_DIR"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Missing or empty"
}

# ── Plugin validation ────────────────────────────────────────────────────────

@test "validate.py catches invalid plugin manifest JSON" {
    mkdir -p "$TEST_DIR/app/.claude-plugin"
    printf '{ invalid json\n' > "$TEST_DIR/app/.claude-plugin/plugin.json"
    run python3 "$TOOLKIT_DIR/scripts/validate.py" "$TEST_DIR"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Invalid plugin manifest JSON"
}

@test "validate.py catches invalid plugin pack manifest JSON" {
    mkdir -p "$TEST_DIR/app/plugins/security-pack"
    printf '{ invalid json\n' > "$TEST_DIR/app/plugins/security-pack/plugin.json"
    run python3 "$TOOLKIT_DIR/scripts/validate.py" "$TEST_DIR"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Invalid plugin pack manifest"
}

# ── KB document validation ───────────────────────────────────────────────────

@test "validate.py catches KB document with missing frontmatter" {
    mkdir -p "$TEST_DIR/kb/reference"
    printf 'No frontmatter here.\nJust content.\n' > "$TEST_DIR/kb/reference/bad-doc.md"
    run python3 "$TOOLKIT_DIR/scripts/validate.py" "$TEST_DIR"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Missing YAML frontmatter"
}

@test "validate.py catches KB document with invalid category" {
    mkdir -p "$TEST_DIR/kb/reference"
    cat > "$TEST_DIR/kb/reference/bad-category.md" <<'EOF'
---
title: "Bad Category Doc"
category: invalid-category
service: ai-toolkit
tags: [test]
created: "2026-03-30"
last_updated: "2026-03-30"
description: "Test doc."
---
Content here.
EOF
    run python3 "$TOOLKIT_DIR/scripts/validate.py" "$TEST_DIR"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Invalid category"
}

@test "validate.py catches KB document missing required field" {
    mkdir -p "$TEST_DIR/kb/reference"
    cat > "$TEST_DIR/kb/reference/missing-field.md" <<'EOF'
---
title: "Missing Service"
category: reference
tags: [test]
created: "2026-03-30"
last_updated: "2026-03-30"
description: "Test doc."
---
No service field.
EOF
    run python3 "$TOOLKIT_DIR/scripts/validate.py" "$TEST_DIR"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Missing required field: service"
}
