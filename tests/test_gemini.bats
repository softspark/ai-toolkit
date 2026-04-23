#!/usr/bin/env bats
# Per-tool tests for Gemini CLI integration (generate_gemini.py).
#
# Upstream docs (as of 2026-04-23): https://github.com/google-gemini/gemini-cli
# Config surface we track:
#   - GEMINI.md (context file, hierarchical: ~/.gemini/, workspace, JIT)
#   - .gemini/settings.json (+ ~/.gemini/settings.json)
#   - .gemini/commands/*.toml (custom slash commands)
#   - .gemini/skills/  or  .agents/skills/  (SKILL.md per agentskills.io)
#   - .gemini/extensions/ (gemini-extension.json)
#   - hooks in settings.json: BeforeTool, AfterTool, BeforeAgent, AfterAgent,
#     BeforeModel, AfterModel, SessionStart, SessionEnd, Stop
# Currently the generator only emits GEMINI.md; other surfaces are tracked as
# registry capability markers and handled by other generators (or deferred).

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
