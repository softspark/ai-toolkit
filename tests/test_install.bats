#!/usr/bin/env bats
# Tests for scripts/install.py — optimized: grouped assertions reduce install.py runs

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_PROJECT="$(mktemp -d)"
    TMP_HOME="$(mktemp -d)"
    export HOME="$TMP_HOME"
}

teardown() {
    rm -rf "$TEST_PROJECT" "$TMP_HOME"
}

# ── Clean install: all basic structure checks in one install ─────────────────

@test "install.py creates correct directory structure with agents, skills, hooks" {
    python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" >/dev/null 2>&1

    # .claude/ dir
    [ -d "$TEST_PROJECT/.claude" ]

    # Agents: real dir with per-file symlinks
    [ -d "$TEST_PROJECT/.claude/agents" ]
    [ ! -L "$TEST_PROJECT/.claude/agents" ]
    agent_found=0
    for f in "$TEST_PROJECT/.claude/agents"/*.md; do
        [ -L "$f" ] && agent_found=$((agent_found + 1))
    done
    [ "$agent_found" -gt 0 ]

    # Skills: real dir with per-directory symlinks
    [ -d "$TEST_PROJECT/.claude/skills" ]
    [ ! -L "$TEST_PROJECT/.claude/skills" ]
    skill_found=0
    for d in "$TEST_PROJECT/.claude/skills"/*/; do
        [ -d "$d" ] || continue
        link="${d%/}"
        [ -L "$link" ] && skill_found=$((skill_found + 1))
    done
    [ "$skill_found" -gt 0 ]

    # Hooks in settings.json (not hooks.json)
    [ -f "$TEST_PROJECT/.claude/settings.json" ]
    grep -q '"_source".*"ai-toolkit"' "$TEST_PROJECT/.claude/settings.json"
    [ ! -f "$TEST_PROJECT/.claude/hooks.json" ]

    # Constitution + ARCHITECTURE injected (not symlinked)
    [ -f "$TEST_PROJECT/.claude/constitution.md" ]
    [ ! -L "$TEST_PROJECT/.claude/constitution.md" ]
    grep -q "<!-- TOOLKIT:constitution START -->" "$TEST_PROJECT/.claude/constitution.md"
    [ -f "$TEST_PROJECT/.claude/ARCHITECTURE.md" ]
    [ ! -L "$TEST_PROJECT/.claude/ARCHITECTURE.md" ]
    grep -q "<!-- TOOLKIT:architecture START -->" "$TEST_PROJECT/.claude/ARCHITECTURE.md"

    # CLAUDE.md with toolkit rules
    [ -f "$TEST_PROJECT/.claude/CLAUDE.md" ]
    grep -q "TOOLKIT:" "$TEST_PROJECT/.claude/CLAUDE.md"

    # No legacy commands symlink
    [ ! -L "$TEST_PROJECT/.claude/commands" ]
}

# ── Hook events and scripts: one install, all checks ────────────────────────

@test "install.py installs all hook events and scripts" {
    python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" >/dev/null 2>&1
    settings="$TEST_PROJECT/.claude/settings.json"

    # Hook events in settings.json
    for event in PreCompact PostToolUse UserPromptSubmit SubagentStart SubagentStop SessionEnd; do
        grep -q "\"$event\"" "$settings" || { echo "MISSING hook event: $event"; return 1; }
    done

    # Hook scripts installed and executable
    for script in pre-compact.sh post-tool-use.sh user-prompt-submit.sh subagent-start.sh subagent-stop.sh session-end.sh; do
        [ -x "$HOME/.ai-toolkit/hooks/$script" ] || { echo "MISSING/non-executable: $script"; return 1; }
    done
}

# ── Merge behavior: user content preservation ────────────────────────────────

@test "install.py merges hooks with existing user settings" {
    mkdir -p "$TEST_PROJECT/.claude"
    cat > "$TEST_PROJECT/.claude/settings.json" << 'SETTINGS'
{
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Bash",
                "command": "echo 'my custom hook'",
                "description": "User custom hook"
            }
        ]
    }
}
SETTINGS
    python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" >/dev/null 2>&1
    grep -q "User custom hook" "$TEST_PROJECT/.claude/settings.json"
    grep -q '"_source".*"ai-toolkit"' "$TEST_PROJECT/.claude/settings.json"
}

@test "install.py removes legacy hooks.json symlink and uses settings.json" {
    mkdir -p "$TEST_PROJECT/.claude"
    ln -s "$TOOLKIT_DIR/app/hooks.json" "$TEST_PROJECT/.claude/hooks.json"
    python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" >/dev/null 2>&1
    [ ! -f "$TEST_PROJECT/.claude/hooks.json" ]
    [ ! -L "$TEST_PROJECT/.claude/hooks.json" ]
    grep -q '"_source".*"ai-toolkit"' "$TEST_PROJECT/.claude/settings.json"
}

@test "install.py preserves user content in constitution.md" {
    mkdir -p "$TEST_PROJECT/.claude"
    echo "# My custom rules" > "$TEST_PROJECT/.claude/constitution.md"
    python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" >/dev/null 2>&1
    grep -q "My custom rules" "$TEST_PROJECT/.claude/constitution.md"
    grep -q "<!-- TOOLKIT:constitution START -->" "$TEST_PROJECT/.claude/constitution.md"
}

@test "install.py upgrades old constitution.md symlink to injection" {
    mkdir -p "$TEST_PROJECT/.claude"
    ln -s "$TOOLKIT_DIR/app/constitution.md" "$TEST_PROJECT/.claude/constitution.md"
    python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" >/dev/null 2>&1
    [ -f "$TEST_PROJECT/.claude/constitution.md" ]
    [ ! -L "$TEST_PROJECT/.claude/constitution.md" ]
    grep -q "<!-- TOOLKIT:constitution START -->" "$TEST_PROJECT/.claude/constitution.md"
}

@test "install.py merges with existing agents and skills directories" {
    mkdir -p "$TEST_PROJECT/.claude/agents" "$TEST_PROJECT/.claude/skills/my-custom-skill"
    echo "# My custom agent" > "$TEST_PROJECT/.claude/agents/my-custom.md"
    echo "# My skill" > "$TEST_PROJECT/.claude/skills/my-custom-skill/SKILL.md"

    python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" >/dev/null 2>&1

    # User agent preserved
    [ -f "$TEST_PROJECT/.claude/agents/my-custom.md" ]
    [ ! -L "$TEST_PROJECT/.claude/agents/my-custom.md" ]
    grep -q "My custom agent" "$TEST_PROJECT/.claude/agents/my-custom.md"
    # User skill preserved
    [ -d "$TEST_PROJECT/.claude/skills/my-custom-skill" ]
    [ ! -L "$TEST_PROJECT/.claude/skills/my-custom-skill" ]
    # Toolkit agents also present
    found=0
    for f in "$TEST_PROJECT/.claude/agents"/*.md; do [ -L "$f" ] && found=$((found + 1)); done
    [ "$found" -gt 0 ]
}

@test "install.py skips user agent with same name as toolkit agent" {
    mkdir -p "$TEST_PROJECT/.claude/agents"
    echo "# My custom backend" > "$TEST_PROJECT/.claude/agents/backend-specialist.md"
    python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" >/dev/null 2>&1
    [ -f "$TEST_PROJECT/.claude/agents/backend-specialist.md" ]
    [ ! -L "$TEST_PROJECT/.claude/agents/backend-specialist.md" ]
    grep -q "My custom backend" "$TEST_PROJECT/.claude/agents/backend-specialist.md"
}

@test "install.py upgrades old directory symlink to per-file" {
    mkdir -p "$TEST_PROJECT/.claude"
    ln -s "$TOOLKIT_DIR/app/agents" "$TEST_PROJECT/.claude/agents"
    python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" >/dev/null 2>&1
    [ -d "$TEST_PROJECT/.claude/agents" ]
    [ ! -L "$TEST_PROJECT/.claude/agents" ]
    found=0
    for f in "$TEST_PROJECT/.claude/agents"/*.md; do [ -L "$f" ] && found=$((found + 1)); done
    [ "$found" -gt 0 ]
}

@test "install.py sets CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS env var in settings.json" {
    python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" >/dev/null 2>&1
    grep -q '"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"' "$TEST_PROJECT/.claude/settings.json"
    # Verify it's inside an "env" block with value "1"
    python3 -c "
import json, sys
with open('$TEST_PROJECT/.claude/settings.json') as f:
    d = json.load(f)
assert d.get('env', {}).get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS') == '1', 'env var not set'
"
}

@test "install.py preserves existing env vars when adding AGENT_TEAMS" {
    mkdir -p "$TEST_PROJECT/.claude"
    cat > "$TEST_PROJECT/.claude/settings.json" << 'SETTINGS'
{
    "env": {
        "MY_CUSTOM_VAR": "hello"
    }
}
SETTINGS
    python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" >/dev/null 2>&1
    python3 -c "
import json
with open('$TEST_PROJECT/.claude/settings.json') as f:
    d = json.load(f)
assert d['env']['MY_CUSTOM_VAR'] == 'hello', 'user env var lost'
assert d['env']['CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS'] == '1', 'toolkit env var not set'
"
}

@test "install.py is idempotent (re-running is safe)" {
    python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" >/dev/null 2>&1
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT"
    [ "$status" -eq 0 ]
}

# ── Local install: all checks in grouped tests ───────────────────────────────

@test "install --local creates project configs and constitution" {
    (cd "$TEST_PROJECT" && HOME="$TMP_HOME" python3 "$TOOLKIT_DIR/scripts/install.py" --local) >/dev/null 2>&1
    [ -f "$TEST_PROJECT/CLAUDE.md" ]
    [ -f "$TEST_PROJECT/.claude/settings.local.json" ]
    [ ! -f "$TEST_PROJECT/.claude/hooks.json" ]
    [ -f "$TEST_PROJECT/.claude/constitution.md" ]
    grep -q "<!-- TOOLKIT:constitution START -->" "$TEST_PROJECT/.claude/constitution.md"
}

@test "install --local removes legacy hooks.json if present" {
    mkdir -p "$TEST_PROJECT/.claude"
    printf '{"hooks":{}}' > "$TEST_PROJECT/.claude/hooks.json"
    (cd "$TEST_PROJECT" && HOME="$TMP_HOME" python3 "$TOOLKIT_DIR/scripts/install.py" --local) >/dev/null 2>&1
    [ ! -f "$TEST_PROJECT/.claude/hooks.json" ]
}

@test "install --local preserves user content in existing constitution.md" {
    mkdir -p "$TEST_PROJECT/.claude"
    echo "# My project safety rules" > "$TEST_PROJECT/.claude/constitution.md"
    (cd "$TEST_PROJECT" && HOME="$TMP_HOME" python3 "$TOOLKIT_DIR/scripts/install.py" --local) >/dev/null 2>&1
    grep -q "My project safety rules" "$TEST_PROJECT/.claude/constitution.md"
    grep -q "<!-- TOOLKIT:constitution START -->" "$TEST_PROJECT/.claude/constitution.md"
}

@test "install --local is idempotent" {
    (cd "$TEST_PROJECT" && HOME="$TMP_HOME" python3 "$TOOLKIT_DIR/scripts/install.py" --local) >/dev/null 2>&1
    run bash -c "cd '$TEST_PROJECT' && HOME='$TMP_HOME' python3 '$TOOLKIT_DIR/scripts/install.py' --local"
    [ "$status" -eq 0 ]
}

# ── Orphan cleanup ─────────────────────────────────────────────────────────────

@test "install cleans orphaned agent symlinks" {
    mkdir -p "$TEST_PROJECT/.claude/agents"
    ln -s "/nonexistent/deleted-agent.md" "$TEST_PROJECT/.claude/agents/deleted-agent.md"
    [ -L "$TEST_PROJECT/.claude/agents/deleted-agent.md" ]

    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT"
    [ "$status" -eq 0 ]

    # Broken symlink should be removed
    [ ! -L "$TEST_PROJECT/.claude/agents/deleted-agent.md" ]
}

@test "install cleans orphaned skill symlinks" {
    mkdir -p "$TEST_PROJECT/.claude/skills"
    ln -s "/nonexistent/deleted-skill" "$TEST_PROJECT/.claude/skills/deleted-skill"
    [ -L "$TEST_PROJECT/.claude/skills/deleted-skill" ]

    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT"
    [ "$status" -eq 0 ]

    # Broken symlink should be removed
    [ ! -L "$TEST_PROJECT/.claude/skills/deleted-skill" ]
}
