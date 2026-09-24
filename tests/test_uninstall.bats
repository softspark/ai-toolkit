#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for uninstall.py — both old-style (dir symlink) and new-style (per-file)
# Optimized: install runs once in setup_file, each test restores from snapshot.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    # Build a single install snapshot shared by all tests
    export UNINSTALL_SNAPSHOT_PROJECT
    export UNINSTALL_SNAPSHOT_HOME
    UNINSTALL_SNAPSHOT_PROJECT="$(mktemp -d)"
    UNINSTALL_SNAPSHOT_HOME="$(mktemp -d)"
    HOME="$UNINSTALL_SNAPSHOT_HOME" python3 "$TOOLKIT_DIR/scripts/install.py" "$UNINSTALL_SNAPSHOT_PROJECT" >/dev/null 2>&1
}

teardown_file() {
    rm -rf "$UNINSTALL_SNAPSHOT_PROJECT" "$UNINSTALL_SNAPSHOT_HOME"
}

setup() {
    TEST_PROJECT="$(mktemp -d)"
    TMP_HOME="$(mktemp -d)"
    cp -a "$UNINSTALL_SNAPSHOT_PROJECT/." "$TEST_PROJECT/"
    cp -a "$UNINSTALL_SNAPSHOT_HOME/." "$TMP_HOME/"
    export HOME="$TMP_HOME"
}

teardown() {
    rm -rf "$TEST_PROJECT" "$TMP_HOME"
}

@test "uninstall.py exits 0" {
    run python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
}

@test "uninstall.py removes agent symlinks" {
    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1
    found=0
    for f in "$TEST_PROJECT/.claude/agents"/*.md; do
        [ -L "$f" ] && found=$((found + 1))
    done
    [ "$found" -eq 0 ]
}

@test "uninstall.py removes skill symlinks" {
    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1
    found=0
    for d in "$TEST_PROJECT/.claude/skills"/*/; do
        [ -d "$d" ] || continue
        link="${d%/}"
        [ -L "$link" ] && found=$((found + 1))
    done
    [ "$found" -eq 0 ]
}

@test "uninstall.py removes toolkit hooks from hooks.json" {
    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1
    [ ! -f "$TEST_PROJECT/.claude/hooks.json" ]
}

@test "uninstall.py preserves user hooks in hooks.json" {
    printf '{"hooks":{"PreToolUse":[{"_source":"ai-toolkit","matcher":"Bash","command":"echo toolkit","description":"Toolkit hook"},{"matcher":"Bash","command":"echo user","description":"User custom hook"}]}}' > "$TEST_PROJECT/.claude/hooks.json"

    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1

    [ -f "$TEST_PROJECT/.claude/hooks.json" ]
    grep -q "User custom hook" "$TEST_PROJECT/.claude/hooks.json"
    ! grep -q '"_source".*"ai-toolkit"' "$TEST_PROJECT/.claude/hooks.json"
}

@test "uninstall.py removes toolkit content from constitution.md" {
    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1
    [ ! -f "$TEST_PROJECT/.claude/constitution.md" ]
}

@test "uninstall.py preserves user content in a legacy constitution.md" {
    printf '%s\n' '# My rules' '<!-- TOOLKIT:constitution START -->' '# toolkit copy' \
        '<!-- TOOLKIT:constitution END -->' > "$TEST_PROJECT/.claude/constitution.md"

    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1

    [ -f "$TEST_PROJECT/.claude/constitution.md" ]
    grep -q "My rules" "$TEST_PROJECT/.claude/constitution.md"
    ! grep -q "<!-- TOOLKIT:" "$TEST_PROJECT/.claude/constitution.md"
}

@test "uninstall.py removes toolkit rule files and keeps user rules" {
    [ -f "$TEST_PROJECT/.claude/rules/ai-toolkit-constitution.md" ]
    [ -f "$TEST_PROJECT/.claude/rules/ai-toolkit-security.md" ]
    printf '# mine\n' > "$TEST_PROJECT/.claude/rules/my-rule.md"

    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1

    run find "$TEST_PROJECT/.claude/rules" -name 'ai-toolkit-*.md'
    [ -z "$output" ]
    [ -f "$TEST_PROJECT/.claude/rules/my-rule.md" ]
}

@test "uninstall.py strips the toolkit rules index from CLAUDE.md and keeps user text" {
    printf '# My notes\n\n' | cat - "$TEST_PROJECT/.claude/CLAUDE.md" > "$TEST_PROJECT/.claude/CLAUDE.tmp"
    mv "$TEST_PROJECT/.claude/CLAUDE.tmp" "$TEST_PROJECT/.claude/CLAUDE.md"
    grep -q '<!-- TOOLKIT:global-rules START -->' "$TEST_PROJECT/.claude/CLAUDE.md"

    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1

    grep -q '# My notes' "$TEST_PROJECT/.claude/CLAUDE.md"
    ! grep -q '<!-- TOOLKIT:global-rules' "$TEST_PROJECT/.claude/CLAUDE.md"
}

@test "uninstall.py is idempotent" {
    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1
    run python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
}

@test "uninstall.py preserves user-owned agent files" {
    echo "# My agent" > "$TEST_PROJECT/.claude/agents/my-agent.md"

    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1

    [ -f "$TEST_PROJECT/.claude/agents/my-agent.md" ]
    grep -q "My agent" "$TEST_PROJECT/.claude/agents/my-agent.md"
}

@test "uninstall.py removes managed Gemini agents and preserves user agents" {
    (cd "$TEST_PROJECT" && python3 "$TOOLKIT_DIR/scripts/install.py" --local \
        --editors gemini --profile full) >/dev/null 2>&1
    printf '%s\n' 'user Gemini agent' > "$TEST_PROJECT/.gemini/agents/team.md"
    printf '%s\n' 'user Gemini collision' \
        > "$TEST_PROJECT/.gemini/agents/ai-toolkit-debugger.md"

    python3 "$TOOLKIT_DIR/scripts/uninstall.py" --local \
        --target "$TEST_PROJECT" --yes >/dev/null 2>&1

    grep -q '^user Gemini agent$' "$TEST_PROJECT/.gemini/agents/team.md"
    grep -q '^user Gemini collision$' \
        "$TEST_PROJECT/.gemini/agents/ai-toolkit-debugger.md"
    [ ! -e "$TEST_PROJECT/.gemini/agents/ai-toolkit-backend-specialist.md" ]
}

@test "uninstall.py removes managed OpenCode skills and preserves user files" {
    (cd "$TEST_PROJECT" && python3 "$TOOLKIT_DIR/scripts/install.py" --local \
        --editors opencode --profile full) >/dev/null 2>&1
    echo user-extra > "$TEST_PROJECT/.opencode/skills/clean-code/user-notes.md"
    mkdir -p "$TEST_PROJECT/.opencode/skills/custom"
    cat > "$TEST_PROJECT/.opencode/skills/custom/SKILL.md" <<'EOF'
---
name: custom
description: User skill
---
user skill
EOF

    python3 "$TOOLKIT_DIR/scripts/uninstall.py" --local \
        --target "$TEST_PROJECT" --yes >/dev/null 2>&1

    [ ! -e "$TEST_PROJECT/.opencode/skills/clean-code/SKILL.md" ]
    [ "$(cat "$TEST_PROJECT/.opencode/skills/clean-code/user-notes.md")" = user-extra ]
    grep -q 'user skill' "$TEST_PROJECT/.opencode/skills/custom/SKILL.md"
}

@test "uninstall.py removes global OpenCode skills and preserves user files" {
    HOME="$TMP_HOME" python3 "$TOOLKIT_DIR/scripts/install.py" \
        --editors opencode --profile full >/dev/null 2>&1
    echo user-extra \
        > "$TMP_HOME/.config/opencode/skills/clean-code/user-notes.md"
    mkdir -p "$TMP_HOME/.config/opencode/skills/custom"
    cat > "$TMP_HOME/.config/opencode/skills/custom/SKILL.md" <<'EOF'
---
name: custom
description: User skill
---
user skill
EOF

    HOME="$TMP_HOME" python3 "$TOOLKIT_DIR/scripts/uninstall.py" --global \
        --target "$TMP_HOME" --yes >/dev/null 2>&1

    [ ! -e "$TMP_HOME/.config/opencode/skills/clean-code/SKILL.md" ]
    [ "$(cat "$TMP_HOME/.config/opencode/skills/clean-code/user-notes.md")" = user-extra ]
    grep -q 'user skill' "$TMP_HOME/.config/opencode/skills/custom/SKILL.md"
}

@test "uninstall.py discovers OpenCode skills without another toolkit surface" {
    standalone="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_opencode_skills.py" \
        "$standalone" >/dev/null

    run python3 "$TOOLKIT_DIR/scripts/uninstall.py" --local \
        --target "$standalone" --yes

    [ "$status" -eq 0 ]
    [ ! -e "$standalone/.opencode/skills/clean-code/SKILL.md" ]
    rm -rf "$standalone"
}

@test "uninstall.py rolls OpenCode skills back after a later cleanup failure" {
    (cd "$TEST_PROJECT" && python3 "$TOOLKIT_DIR/scripts/install.py" --local \
        --editors opencode --profile full) >/dev/null 2>&1
    echo user-extra > "$TEST_PROJECT/.opencode/skills/clean-code/user-notes.md"
    before="$(find "$TEST_PROJECT/.opencode/skills" -type f \
        -exec cksum {} + | sort)"

    run python3 - "$TOOLKIT_DIR" "$TEST_PROJECT" <<'PY'
import contextlib
import importlib.util
import io
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
spec = importlib.util.spec_from_file_location(
    "uninstall_opencode_rollback_test",
    toolkit / "scripts" / "uninstall.py",
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

real_cleanup = module._remove_editor_managed_surfaces

def fail_after_editor_cleanup(root, scope):
    real_cleanup(root, scope)
    raise RuntimeError("injected failure after OpenCode cleanup")

module._remove_editor_managed_surfaces = fail_after_editor_cleanup
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    try:
        module.main(["--local", "--target", str(target), "--yes"])
    except SystemExit as error:
        assert error.code == 1, error.code
    else:
        raise AssertionError("late cleanup failure did not abort uninstall")
PY

    [ "$status" -eq 0 ]
    [ "$(find "$TEST_PROJECT/.opencode/skills" -type f \
        -exec cksum {} + | sort)" = "$before" ]
    [ -f "$TEST_PROJECT/.opencode/skills/clean-code/SKILL.md" ]
    [ -f "$TEST_PROJECT/.opencode/skills/clean-code/reference/python.md" ]
    grep -q '^user-extra$' \
        "$TEST_PROJECT/.opencode/skills/clean-code/user-notes.md"
}

@test "uninstall.py removes local Cline managed rules and hooks but preserves user files" {
    (cd "$TEST_PROJECT" && python3 "$TOOLKIT_DIR/scripts/install.py" --local \
        --editors cline --profile standard) >/dev/null 2>&1
    printf '%s\n' 'user native rule' > "$TEST_PROJECT/.cline/rules/team.md"
    printf '%s\n' 'user compatibility rule' > "$TEST_PROJECT/.clinerules/team.md"
    printf '%s\n' '#!/bin/sh' '# user hook' \
        > "$TEST_PROJECT/.cline/hooks/TeamPolicy"
    printf '%s\n' '#!/bin/sh' '# extension user hook' \
        > "$TEST_PROJECT/.clinerules/hooks/TeamPolicy"

    python3 "$TOOLKIT_DIR/scripts/uninstall.py" --local \
        --target "$TEST_PROJECT" --yes >/dev/null 2>&1

    [ ! -e "$TEST_PROJECT/.cline/hooks/PreToolUse" ]
    [ ! -e "$TEST_PROJECT/.clinerules/hooks/PreToolUse" ]
    [ ! -e "$TEST_PROJECT/.cline/rules/ai-toolkit-security.md" ]
    [ ! -e "$TEST_PROJECT/.clinerules/ai-toolkit-security.md" ]
    grep -q '^# user hook$' "$TEST_PROJECT/.cline/hooks/TeamPolicy"
    grep -q '^# extension user hook$' \
        "$TEST_PROJECT/.clinerules/hooks/TeamPolicy"
    grep -q '^user native rule$' "$TEST_PROJECT/.cline/rules/team.md"
    grep -q '^user compatibility rule$' "$TEST_PROJECT/.clinerules/team.md"
}

@test "uninstall.py propagates a mid-Cline failure and rolls back every local root" {
    (cd "$TEST_PROJECT" && python3 "$TOOLKIT_DIR/scripts/install.py" --local \
        --editors cline --profile full) >/dev/null 2>&1
    printf '%s\n' 'user native rule' > "$TEST_PROJECT/.cline/rules/team.md"
    printf '%s\n' 'user compatibility rule' > "$TEST_PROJECT/.clinerules/team.md"
    printf '%s\n' '#!/bin/sh' '# user native hook' \
        > "$TEST_PROJECT/.cline/hooks/TeamPolicy"
    printf '%s\n' '#!/bin/sh' '# user extension hook' \
        > "$TEST_PROJECT/.clinerules/hooks/TeamPolicy"
    before="$(find "$TEST_PROJECT/.cline" "$TEST_PROJECT/.clinerules" -type f \
        -exec cksum {} + | sort)"

    run python3 - "$TOOLKIT_DIR" "$TEST_PROJECT" <<'PY'
import contextlib
import importlib.util
import io
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
spec = importlib.util.spec_from_file_location(
    "uninstall_cline_mid_failure_test",
    toolkit / "scripts" / "uninstall.py",
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

from generate_cline_rules import cleanup as cleanup_cline_rules

def fail_after_rules(root, scope):
    assert scope == "local"
    cleanup_cline_rules(root)
    raise RuntimeError("injected mid-Cline failure")

module._cleanup_cline_surfaces = fail_after_rules
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    try:
        module.main(["--local", "--target", str(target), "--yes"])
    except SystemExit as error:
        assert error.code == 1, error.code
    else:
        raise AssertionError("mid-Cline cleanup failure did not abort uninstall")
PY

    [ "$status" -eq 0 ]
    [ "$(find "$TEST_PROJECT/.cline" "$TEST_PROJECT/.clinerules" -type f \
        -exec cksum {} + | sort)" = "$before" ]
}

@test "uninstall.py restores Cline roots after a post-Cline failure" {
    (cd "$TEST_PROJECT" && python3 "$TOOLKIT_DIR/scripts/install.py" --local \
        --editors cline --profile full) >/dev/null 2>&1
    printf '%s\n' 'user native rule' > "$TEST_PROJECT/.cline/rules/team.md"
    printf '%s\n' 'user compatibility rule' > "$TEST_PROJECT/.clinerules/team.md"
    printf '%s\n' '#!/bin/sh' '# extension user hook' \
        > "$TEST_PROJECT/.clinerules/hooks/TeamPolicy"
    before="$(find "$TEST_PROJECT/.cline" "$TEST_PROJECT/.clinerules" -type f \
        -exec cksum {} + | sort)"

    run python3 - "$TOOLKIT_DIR" "$TEST_PROJECT" <<'PY'
import contextlib
import importlib.util
import io
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
spec = importlib.util.spec_from_file_location(
    "uninstall_cline_post_failure_test",
    toolkit / "scripts" / "uninstall.py",
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

real_cleanup = module._remove_editor_managed_surfaces

def fail_after_cline(root, scope):
    real_cleanup(root, scope)
    raise RuntimeError("injected post-Cline failure")

module._remove_editor_managed_surfaces = fail_after_cline
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    try:
        module.main(["--local", "--target", str(target), "--yes"])
    except SystemExit as error:
        assert error.code == 1, error.code
    else:
        raise AssertionError("post-Cline failure did not abort uninstall")
PY

    [ "$status" -eq 0 ]
    [ "$(find "$TEST_PROJECT/.cline" "$TEST_PROJECT/.clinerules" -type f \
        -exec cksum {} + | sort)" = "$before" ]
}

@test "uninstall.py discovers and removes standalone global Cline surfaces" {
    standalone="$(mktemp -d)"
    HOME="$standalone" python3 "$TOOLKIT_DIR/scripts/install.py" \
        --editors cline --profile standard >/dev/null 2>&1
    printf '%s\n' 'user global rule' > "$standalone/.cline/rules/team.md"
    printf '%s\n' '#!/bin/sh' '# user global hook' \
        > "$standalone/Documents/Cline/Hooks/TeamPolicy"

    run env HOME="$standalone" python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --global --target "$standalone" --yes

    [ "$status" -eq 0 ]
    [[ "$output" == *"Managed: Cline native surfaces"* ]] || return 1
    [ ! -e "$standalone/.cline/hooks/PreToolUse" ]
    [ ! -e "$standalone/Documents/Cline/Hooks/PreToolUse" ]
    [ ! -e "$standalone/.cline/rules/ai-toolkit-security.md" ]
    [ ! -e "$standalone/Documents/Cline/Rules/ai-toolkit-security.md" ]
    grep -q '^user global rule$' "$standalone/.cline/rules/team.md"
    grep -q '^# user global hook$' \
        "$standalone/Documents/Cline/Hooks/TeamPolicy"
    rm -rf "$standalone"
}

@test "uninstall.py rejects a symlinked Cline Documents root before mutation" {
    local standalone outside before_outside before_native
    standalone="$(mktemp -d)"
    outside="$(mktemp -d)"
    mkdir -p "$outside/Cline/Rules" "$standalone/.cline/hooks"
    printf '%s\n' 'outside managed-name bytes' \
        > "$outside/Cline/Rules/ai-toolkit-security.md"
    printf '%s\n' '#!/bin/sh' '# ai-toolkit-managed: cline-hook' \
        > "$standalone/.cline/hooks/PreToolUse"
    before_outside="$(cksum "$outside/Cline/Rules/ai-toolkit-security.md")"
    before_native="$(cksum "$standalone/.cline/hooks/PreToolUse")"
    ln -s "$outside" "$standalone/Documents"

    run env HOME="$standalone" python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --global --target "$standalone" --yes

    [ "$status" -ne 0 ]
    [ "$(cksum "$outside/Cline/Rules/ai-toolkit-security.md")" = \
        "$before_outside" ]
    [ "$(cksum "$standalone/.cline/hooks/PreToolUse")" = "$before_native" ]
    rm -rf "$standalone" "$outside"
}

@test "uninstall.py preserves user-owned skill directories" {
    mkdir -p "$TEST_PROJECT/.claude/skills/my-skill"
    echo "# My skill" > "$TEST_PROJECT/.claude/skills/my-skill/SKILL.md"

    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1

    [ -d "$TEST_PROJECT/.claude/skills/my-skill" ]
    grep -q "My skill" "$TEST_PROJECT/.claude/skills/my-skill/SKILL.md"
}

@test "uninstall.py removes empty agents/ directory after cleanup" {
    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1
    [ ! -d "$TEST_PROJECT/.claude/agents" ]
}

@test "uninstall.py removes empty skills/ directory after cleanup" {
    python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes >/dev/null 2>&1
    [ ! -d "$TEST_PROJECT/.claude/skills" ]
}

write_toolkit_settings() {
    mkdir -p "$TMP_HOME/.claude/output-styles"
    cp "$TOOLKIT_DIR/app/output-styles/"*.md "$TMP_HOME/.claude/output-styles/"
    printf '%s\n' '---' 'name: Mine' '---' > "$TMP_HOME/.claude/output-styles/mine.md"
    # Untagged toolkit entries: Claude Code drops "_source" when it rewrites
    # settings.json, so ownership has to come from the toolkit script path.
    cat > "$TMP_HOME/.claude/settings.json" <<'EOF'
{
    "model": "opus",
    "outputStyle": "Golden Rules",
    "skillListingBudgetFraction": 0.02,
    "env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1", "USER_VAR": "x"},
    "skillOverrides": {"php-rules": "off", "my-skill": "off"},
    "statusLine": {"type": "command", "command": "bash \"$HOME/.softspark/ai-toolkit/hooks/ai-toolkit-statusline.sh\""},
    "hooks": {
        "PreToolUse": [
            {"matcher": "Bash", "hooks": [
                {"type": "command", "command": "bash \"$HOME/.softspark/ai-toolkit/hooks/guard-destructive.sh\""},
                {"type": "command", "command": "echo user-chained"}
            ]},
            {"matcher": "Edit", "hooks": [{"type": "command", "command": "echo user"}]}
        ],
        "Stop": [
            {"_source": "ai-toolkit", "matcher": "", "hooks": [{"type": "command", "command": "echo tagged"}]}
        ]
    }
}
EOF
    python3 - "$TMP_HOME/.softspark/ai-toolkit/state.json" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
state = json.loads(path.read_text()) if path.is_file() else {}
state["managed_skill_overrides"] = ["php-rules"]
path.write_text(json.dumps(state))
PY
}

@test "uninstall --global strips every toolkit setting and keeps user settings" {
    write_toolkit_settings

    run python3 "$TOOLKIT_DIR/scripts/uninstall.py" --global --yes
    [ "$status" -eq 0 ]

    run python3 - "$TMP_HOME/.claude/settings.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
assert data == {
    "model": "opus",
    "env": {"USER_VAR": "x"},
    "skillOverrides": {"my-skill": "off"},
    "hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo user-chained"}]},
        {"matcher": "Edit", "hooks": [{"type": "command", "command": "echo user"}]},
    ]},
}, data
PY
    [ "$status" -eq 0 ]
    [ ! -e "$TMP_HOME/.claude/output-styles/golden-rules.md" ]
    [ -f "$TMP_HOME/.claude/output-styles/mine.md" ]
}

@test "uninstall --global keeps a user's own output style and budget" {
    write_toolkit_settings
    python3 - "$TMP_HOME/.claude/settings.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
data.update(outputStyle="Mine", skillListingBudgetFraction=0.05)
json.dump(data, open(sys.argv[1], "w"))
PY

    run python3 "$TOOLKIT_DIR/scripts/uninstall.py" --global --yes
    [ "$status" -eq 0 ]
    [ "$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["outputStyle"], d["skillListingBudgetFraction"])' \
        "$TMP_HOME/.claude/settings.json")" = "Mine 0.05" ]
}

@test "uninstall --global archives the data directory, then removes it" {
    mkdir -p "$TMP_HOME/.softspark/ai-toolkit/sessions/repo" "$TMP_HOME/.softspark/other-tool"
    printf '%s\n' "session history" > "$TMP_HOME/.softspark/ai-toolkit/sessions/repo/session-context.md"

    run python3 "$TOOLKIT_DIR/scripts/uninstall.py" --global --yes
    [ "$status" -eq 0 ]
    [ ! -e "$TMP_HOME/.softspark/ai-toolkit" ]
    [ -d "$TMP_HOME/.softspark/other-tool" ]
    local archive
    archive="$(ls "$TMP_HOME"/ai-toolkit-backup-*.tar.gz)"
    [ "$(python3 -c 'import os,stat,sys; print(oct(stat.S_IMODE(os.stat(sys.argv[1]).st_mode)))' "$archive")" = "0o600" ]
    [ "$(tar -xzOf "$archive" ai-toolkit/sessions/repo/session-context.md)" = "session history" ]
    tar -tzf "$archive" | grep -q '^ai-toolkit/state.json$'
}

@test "uninstall --global uninstalls every registered project, then drops the registry" {
    local project
    project="$(mktemp -d)"
    mkdir -p "$project/.git/hooks" "$project/.claude/rules"
    python3 "$TOOLKIT_DIR/scripts/install_git_hooks.py" "$project" >/dev/null
    printf '%s\n' '#!/bin/sh' 'echo user hook' > "$project/.git/hooks/pre-commit.backup"
    { cat "$TOOLKIT_DIR/app/CLAUDE.md.template"; printf '\n%s\n%s\n' '## Project Constitution' '@.claude/constitution.md'; } \
        > "$project/CLAUDE.md"
    cp "$TOOLKIT_DIR/app/mcp-defaults.json" "$project/.claude/settings.local.json"
    printf '%s\n' '{}' > "$project/.softspark-toolkit.lock.json"
    printf '%s\n' 'rule' > "$project/.claude/rules/ai-toolkit-security.md"
    printf '%s\n' 'mine' > "$project/.claude/rules/mine.md"
    printf '{"projects": [{"path": "%s"}]}\n' "$project" > "$TMP_HOME/.softspark/ai-toolkit/projects.json"

    run python3 "$TOOLKIT_DIR/scripts/uninstall.py" --global --yes
    [ "$status" -eq 0 ]
    [[ "$output" == *"Registered project: $project (local)"* ]]
    [ "$(cat "$project/.git/hooks/pre-commit")" = "$(printf '%s\n' '#!/bin/sh' 'echo user hook')" ]
    [ ! -e "$project/.git/hooks/pre-commit.backup" ]
    [ ! -e "$project/CLAUDE.md" ]
    [ ! -e "$project/.claude/settings.local.json" ]
    [ ! -e "$project/.softspark-toolkit.lock.json" ]
    [ ! -e "$project/.claude/rules/ai-toolkit-security.md" ]
    [ -f "$project/.claude/rules/mine.md" ]
    [ ! -e "$TMP_HOME/.softspark/ai-toolkit" ]
    rm -rf "$project"
}

@test "uninstall --global stops before any change when a registered project is unsafe" {
    local project outside
    project="$(mktemp -d)"
    outside="$(mktemp -d)"
    ln -s "$outside" "$project/.claude"
    printf '{"projects": [{"path": "%s"}]}\n' "$project" > "$TMP_HOME/.softspark/ai-toolkit/projects.json"
    write_toolkit_settings
    local before
    before="$(shasum "$TMP_HOME/.claude/settings.json")"

    run python3 "$TOOLKIT_DIR/scripts/uninstall.py" --global --yes
    [ "$status" -eq 1 ]
    [[ "$output" == *"Refusing symlinked Claude configuration root"* ]]
    [ "$(shasum "$TMP_HOME/.claude/settings.json")" = "$before" ]
    [ -f "$TMP_HOME/.softspark/ai-toolkit/projects.json" ]
    [ -z "$(ls "$TMP_HOME" | grep ai-toolkit-backup)" ]
    rm -rf "$project" "$outside"
}

@test "uninstall --local keeps edited project files, strips the import, and unregisters" {
    local project
    project="$(cd "$(mktemp -d)" && pwd -P)"
    mkdir -p "$project/.claude"
    printf '%s\n' '# My project' '' '## Project Constitution' '@.claude/constitution.md' > "$project/CLAUDE.md"
    printf '%s\n' '{"mcpServers": {"mine": {"command": "x"}}}' > "$project/.claude/settings.local.json"
    printf '%s\n' '{}' > "$project/.softspark-toolkit-extends.json"
    printf '{"projects": [{"path": "%s"}, {"path": "/elsewhere"}]}\n' "$project" \
        > "$TMP_HOME/.softspark/ai-toolkit/projects.json"

    run python3 "$TOOLKIT_DIR/scripts/uninstall.py" --local --yes --target "$project"
    [ "$status" -eq 0 ]
    [ "$(cat "$project/CLAUDE.md")" = "# My project" ]
    grep -q '"mine"' "$project/.claude/settings.local.json"
    [ ! -e "$project/.softspark-toolkit-extends.json" ]
    [ "$(python3 -c 'import json,sys; print([p["path"] for p in json.load(open(sys.argv[1]))["projects"]])' \
        "$TMP_HOME/.softspark/ai-toolkit/projects.json")" = "['/elsewhere']" ]
    [ -f "$TMP_HOME/.softspark/ai-toolkit/state.json" ]
    rm -rf "$project"
}

@test "uninstall.py handles old-style directory symlink" {
    rm -rf "$TEST_PROJECT/.claude/agents" "$TEST_PROJECT/.claude/skills"
    ln -s "$TOOLKIT_DIR/app/agents" "$TEST_PROJECT/.claude/agents"
    ln -s "$TOOLKIT_DIR/app/skills" "$TEST_PROJECT/.claude/skills"

    run python3 "$TOOLKIT_DIR/scripts/uninstall.py" "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [ ! -L "$TEST_PROJECT/.claude/agents" ]
    [ ! -L "$TEST_PROJECT/.claude/skills" ]
}
