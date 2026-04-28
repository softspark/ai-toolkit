#!/usr/bin/env bats
# Install profile × editor matrix tests (v3.0.0 Bucket A).
#
# Exercises `install.py --local --editors <ed> --profile <p>` for the editors
# that actually change behavior across profiles in v3.0.0:
#   cursor  — gains .cursor/hooks.json + .cursor/agents/ at `full`
#   gemini  — gains .gemini/settings.json hooks at `standard`+; commands/skills at `full`
#   augment — gains .augment/agents/, /commands/, /skills/ at `full`;
#             $HOME/.augment/settings.json hooks at `full` only.
#
# install.py reads `Path.cwd()` for --local, so every test cd's into the temp
# project before invoking the script.
#
# Run with: bats tests/test_install_profiles.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    export TEST_PROJECT; TEST_PROJECT="$(mktemp -d)"
    export TMP_HOME; TMP_HOME="$(mktemp -d)"
    export HOME="$TMP_HOME"
}

teardown() {
    rm -rf "$TEST_PROJECT" "$TMP_HOME"
}

# Helper: run install from inside the test project and dump output on failure.
run_install() {
    (cd "$TEST_PROJECT" && python3 "$TOOLKIT_DIR/scripts/install.py" --local "$@")
    return $?
}

# ── Profile validation ─────────────────────────────────────────────────────

@test "profiles: --profile full is accepted" {
    run_install --editors cursor --profile full >/dev/null 2>&1
    [ "$?" -eq 0 ]
}

@test "profiles: --profile standard is accepted" {
    run_install --editors cursor --profile standard >/dev/null 2>&1
    [ "$?" -eq 0 ]
}

@test "profiles: --profile minimal is accepted" {
    run_install --editors cursor --profile minimal >/dev/null 2>&1
    [ "$?" -eq 0 ]
}

@test "profiles: --profile strict is accepted" {
    run_install --editors cursor --profile strict >/dev/null 2>&1
    [ "$?" -eq 0 ]
}

# ── Cursor × profile matrix ────────────────────────────────────────────────

@test "profiles: cursor + minimal does NOT emit .cursor/hooks.json or agents/" {
    run_install --editors cursor --profile minimal >/dev/null 2>&1
    [ ! -f "$TEST_PROJECT/.cursor/hooks.json" ]
    [ ! -d "$TEST_PROJECT/.cursor/agents" ]
}

@test "profiles: cursor + standard does NOT emit native surfaces" {
    run_install --editors cursor --profile standard >/dev/null 2>&1
    [ ! -f "$TEST_PROJECT/.cursor/hooks.json" ]
    [ ! -d "$TEST_PROJECT/.cursor/agents" ]
}

@test "profiles: cursor + full emits .cursor/hooks.json and .cursor/agents/" {
    run_install --editors cursor --profile full >/dev/null 2>&1
    [ -f "$TEST_PROJECT/.cursor/hooks.json" ]
    [ -d "$TEST_PROJECT/.cursor/agents" ]
    compgen -G "$TEST_PROJECT/.cursor/agents/ai-toolkit-*.md" >/dev/null
}

# ── Gemini × profile matrix ────────────────────────────────────────────────

@test "profiles: gemini + minimal does NOT emit hooks or commands" {
    run_install --editors gemini --profile minimal >/dev/null 2>&1
    # settings.json may be absent; if present, must not carry ai-toolkit hooks
    if [ -f "$TEST_PROJECT/.gemini/settings.json" ]; then
        ! grep -q '"_source": "ai-toolkit"' "$TEST_PROJECT/.gemini/settings.json"
    fi
    [ ! -d "$TEST_PROJECT/.gemini/commands" ]
    [ ! -d "$TEST_PROJECT/.gemini/skills" ]
}

@test "profiles: gemini + standard DOES emit hooks (v3.0.0 breaking change)" {
    run_install --editors gemini --profile standard >/dev/null 2>&1
    [ -f "$TEST_PROJECT/.gemini/settings.json" ]
    grep -q '"_source": "ai-toolkit"' "$TEST_PROJECT/.gemini/settings.json"
    # standard must NOT emit commands/skills (that's full-only)
    [ ! -d "$TEST_PROJECT/.gemini/commands" ]
    [ ! -d "$TEST_PROJECT/.gemini/skills" ]
}

@test "profiles: gemini + full emits hooks AND commands" {
    run_install --editors gemini --profile full >/dev/null 2>&1
    [ -f "$TEST_PROJECT/.gemini/settings.json" ]
    grep -q '"_source": "ai-toolkit"' "$TEST_PROJECT/.gemini/settings.json"
    [ -d "$TEST_PROJECT/.gemini/commands" ]
    compgen -G "$TEST_PROJECT/.gemini/commands/ai-toolkit-*.toml" >/dev/null
}

# ── Augment × profile matrix ───────────────────────────────────────────────

@test "profiles: augment + minimal does NOT emit any native surface" {
    run_install --editors augment --profile minimal >/dev/null 2>&1
    [ ! -d "$TEST_PROJECT/.augment/agents" ]
    [ ! -d "$TEST_PROJECT/.augment/commands" ]
    [ ! -d "$TEST_PROJECT/.augment/skills" ]
    [ ! -f "$TMP_HOME/.augment/settings.json" ]
}

@test "profiles: augment + standard does NOT emit native surfaces" {
    run_install --editors augment --profile standard >/dev/null 2>&1
    [ ! -d "$TEST_PROJECT/.augment/agents" ]
    [ ! -d "$TEST_PROJECT/.augment/commands" ]
    [ ! -f "$TMP_HOME/.augment/settings.json" ]
}

@test "profiles: augment + full emits agents, commands, and HOME settings.json" {
    run_install --editors augment --profile full >/dev/null 2>&1
    [ -d "$TEST_PROJECT/.augment/agents" ]
    compgen -G "$TEST_PROJECT/.augment/agents/ai-toolkit-*.md" >/dev/null
    [ -d "$TEST_PROJECT/.augment/commands" ]
    # HOME-scoped hooks file (per v3 contract: augment hooks only in HOME)
    [ -f "$TMP_HOME/.augment/settings.json" ]
    grep -q '"_source": "ai-toolkit"' "$TMP_HOME/.augment/settings.json"
}

# ── Windsurf hooks: full only ──────────────────────────────────────────────

@test "profiles: windsurf + standard does NOT emit .windsurf/hooks.json" {
    run_install --editors windsurf --profile standard >/dev/null 2>&1
    [ ! -f "$TEST_PROJECT/.windsurf/hooks.json" ]
}

@test "profiles: windsurf + full emits .windsurf/hooks.json" {
    run_install --editors windsurf --profile full >/dev/null 2>&1
    [ -f "$TEST_PROJECT/.windsurf/hooks.json" ]
    grep -q '"_source": "ai-toolkit"' "$TEST_PROJECT/.windsurf/hooks.json"
}

# ── Codex skills use upstream .agents/skills discovery path ────────────────

@test "profiles: --codex-skills without --profile full refreshes .agents/skills/" {
    run_install --editors codex --profile standard --codex-skills >/dev/null 2>&1
    [ -d "$TEST_PROJECT/.agents/skills" ]
    [ -f "$TEST_PROJECT/.agents/skills/orchestrate/SKILL.md" ]
    grep -q 'Codex Translation Layer' "$TEST_PROJECT/.agents/skills/orchestrate/SKILL.md"
}

@test "profiles: --profile full alone uses .agents/skills and does not emit .codex/skills/" {
    run_install --editors codex --profile full >/dev/null 2>&1
    [ -d "$TEST_PROJECT/.agents/skills" ]
    [ ! -d "$TEST_PROJECT/.codex/skills" ]
}
