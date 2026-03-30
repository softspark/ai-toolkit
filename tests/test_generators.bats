#!/usr/bin/env bats
# Workstream 3: Generator contract tests — cached to temp files (avoids env size limits)
# Each generator runs ONCE in setup_file, output written to temp files.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export GEN_DIR; GEN_DIR="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_agents_md.py" > "$GEN_DIR/agents-md" 2>/dev/null; echo $? > "$GEN_DIR/agents-md.status"
    python3 "$TOOLKIT_DIR/scripts/generate_llms_txt.py" > "$GEN_DIR/llms" 2>/dev/null; echo $? > "$GEN_DIR/llms.status"
    python3 "$TOOLKIT_DIR/scripts/generate_llms_txt.py" --full > "$GEN_DIR/llms-full" 2>/dev/null; echo $? > "$GEN_DIR/llms-full.status"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_rules.py" > "$GEN_DIR/cursor" 2>/dev/null; echo $? > "$GEN_DIR/cursor.status"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" > "$GEN_DIR/copilot" 2>/dev/null; echo $? > "$GEN_DIR/copilot.status"
    python3 "$TOOLKIT_DIR/scripts/generate_cline.py" > "$GEN_DIR/cline" 2>/dev/null; echo $? > "$GEN_DIR/cline.status"
    python3 "$TOOLKIT_DIR/scripts/generate_windsurf.py" > "$GEN_DIR/windsurf" 2>/dev/null; echo $? > "$GEN_DIR/windsurf.status"
    python3 "$TOOLKIT_DIR/scripts/generate_gemini.py" > "$GEN_DIR/gemini" 2>/dev/null; echo $? > "$GEN_DIR/gemini.status"
    python3 "$TOOLKIT_DIR/scripts/generate_roo_modes.py" > "$GEN_DIR/roo" 2>/dev/null; echo $? > "$GEN_DIR/roo.status"
    python3 "$TOOLKIT_DIR/scripts/generate_aider_conf.py" > "$GEN_DIR/aider" 2>/dev/null; echo $? > "$GEN_DIR/aider.status"
    python3 "$TOOLKIT_DIR/scripts/benchmark_ecosystem.py" --offline > "$GEN_DIR/bench" 2>/dev/null; echo $? > "$GEN_DIR/bench.status"
    python3 "$TOOLKIT_DIR/scripts/benchmark_ecosystem.py" --offline --json > "$GEN_DIR/bench-json" 2>/dev/null
    python3 "$TOOLKIT_DIR/scripts/benchmark_ecosystem.py" --offline --dashboard-json > "$GEN_DIR/bench-dash" 2>/dev/null; echo $? > "$GEN_DIR/bench-dash.status"
}

teardown_file() {
    rm -rf "$GEN_DIR"
}

# ── generate_agents_md.py ───────────────────────────────────────────────────

@test "generate_agents_md.py exits 0" {
    [ "$(cat "$GEN_DIR/agents-md.status")" = "0" ]
}

@test "generate_agents_md.py output has markdown header" {
    grep -qE '^# ' "$GEN_DIR/agents-md"
}

@test "generate_agents_md.py output contains all agent names" {
    missing=0
    for f in "$TOOLKIT_DIR"/app/agents/*.md; do
        agent_name="${f##*/}"; agent_name="${agent_name%.md}"
        grep -q "$agent_name" "$GEN_DIR/agents-md" || missing=$((missing + 1))
    done
    [ "$missing" -eq 0 ]
}

@test "generate_agents_md.py output has at least 200 lines" {
    line_count=$(wc -l < "$GEN_DIR/agents-md" | xargs)
    [ "$line_count" -ge 200 ]
}

@test "generate_agents_md.py output mentions subagent_type" {
    grep -q 'subagent_type' "$GEN_DIR/agents-md"
}

# ── generate_llms_txt.py ────────────────────────────────────────────────────

@test "generate_llms_txt.py exits 0" {
    [ "$(cat "$GEN_DIR/llms.status")" = "0" ]
}

@test "generate_llms_txt.py output has toolkit URL or title" {
    grep -qiE 'ai-toolkit|softspark' "$GEN_DIR/llms"
}

@test "generate_llms_txt.py output references skills" {
    grep -qi 'skill' "$GEN_DIR/llms"
}

@test "generate_llms_txt.py output references agents" {
    grep -qi 'agent' "$GEN_DIR/llms"
}

@test "generate_llms_txt.py --full output is larger than index output" {
    size_full=$(wc -c < "$GEN_DIR/llms-full" | xargs)
    size_index=$(wc -c < "$GEN_DIR/llms" | xargs)
    [ "$size_full" -gt "$size_index" ]
}

@test "generate_llms_txt.py --full exits 0" {
    [ "$(cat "$GEN_DIR/llms-full.status")" = "0" ]
}

# ── benchmark_ecosystem.py ──────────────────────────────────────────────────

@test "benchmark_ecosystem.py --offline exits 0" {
    [ "$(cat "$GEN_DIR/bench.status")" = "0" ]
}

@test "benchmark_ecosystem.py --offline output references official Claude Code repo" {
    grep -q 'anthropics/claude-code' "$GEN_DIR/bench"
}

@test "benchmark_ecosystem.py --json outputs JSON array" {
    grep -q '^\[' "$GEN_DIR/bench-json"
}

@test "benchmark_ecosystem.py --dashboard-json outputs freshness object" {
    [ "$(cat "$GEN_DIR/bench-dash.status")" = "0" ]
    grep -q '"freshness"' "$GEN_DIR/bench-dash"
}

@test "harvest_ecosystem.py --offline writes machine-readable JSON" {
    tmp_json="$(mktemp)"
    run python3 "$TOOLKIT_DIR/scripts/harvest_ecosystem.py" --offline --out "$tmp_json"
    [ "$status" -eq 0 ]
    python3 -c "import json; d=json.load(open('$tmp_json')); assert d['repos']; assert d['comparison_matrix']"
}

# ── generate_cursor_rules.py ────────────────────────────────────────────────

@test "generate_cursor_rules.py exits 0" {
    [ "$(cat "$GEN_DIR/cursor.status")" = "0" ]
}

@test "generate_cursor_rules.py output contains agent names" {
    found=0
    for f in "$TOOLKIT_DIR"/app/agents/*.md; do
        agent_name="${f##*/}"; agent_name="${agent_name%.md}"
        grep -q "$agent_name" "$GEN_DIR/cursor" && found=$((found+1))
    done
    [ "$found" -ge 10 ]
}

@test "generate_cursor_rules.py output has at least 50 lines" {
    line_count=$(wc -l < "$GEN_DIR/cursor" | xargs)
    [ "$line_count" -ge 50 ]
}

# ── generate_copilot.py ─────────────────────────────────────────────────────

@test "generate_copilot.py exits 0" {
    [ "$(cat "$GEN_DIR/copilot.status")" = "0" ]
}

@test "generate_copilot.py output is non-empty" {
    [ "$(wc -c < "$GEN_DIR/copilot" | xargs)" -gt 100 ]
}

@test "generate_copilot.py output references agents or skills" {
    grep -qiE 'agent|skill' "$GEN_DIR/copilot"
}

# ── generate_cline.py ──────────────────────────────────────────────────────

@test "generate_cline.py exits 0" {
    [ "$(cat "$GEN_DIR/cline.status")" = "0" ]
}

@test "generate_cline.py output is non-empty" {
    [ "$(wc -c < "$GEN_DIR/cline" | xargs)" -gt 100 ]
}

@test "generate_cline.py output references agents or skills" {
    grep -qiE 'agent|skill' "$GEN_DIR/cline"
}

# ── generate_windsurf.py ────────────────────────────────────────────────────

@test "generate_windsurf.py exits 0" {
    [ "$(cat "$GEN_DIR/windsurf.status")" = "0" ]
}

@test "generate_windsurf.py output is non-empty" {
    [ "$(wc -c < "$GEN_DIR/windsurf" | xargs)" -gt 100 ]
}

# ── generate_gemini.py ──────────────────────────────────────────────────────

@test "generate_gemini.py exits 0" {
    [ "$(cat "$GEN_DIR/gemini.status")" = "0" ]
}

@test "generate_gemini.py output is non-empty" {
    [ "$(wc -c < "$GEN_DIR/gemini" | xargs)" -gt 100 ]
}

@test "generate_gemini.py output references agents or skills" {
    grep -qiE 'agent|skill' "$GEN_DIR/gemini"
}

# ── generate_roo_modes.py ──────────────────────────────────────────────────

@test "generate_roo_modes.py exits 0" {
    [ "$(cat "$GEN_DIR/roo.status")" = "0" ]
}

@test "generate_roo_modes.py output is valid JSON with customModes" {
    python3 -c "import json; d=json.load(open('$GEN_DIR/roo')); assert 'customModes' in d"
}

@test "generate_roo_modes.py output contains agent slugs" {
    found=0
    for f in "$TOOLKIT_DIR"/app/agents/*.md; do
        agent_name="${f##*/}"; agent_name="${agent_name%.md}"
        grep -q "$agent_name" "$GEN_DIR/roo" && found=$((found+1))
    done
    [ "$found" -ge 10 ]
}

@test "generate_roo_modes.py output has roleDefinition and groups fields" {
    grep -q '"roleDefinition"' "$GEN_DIR/roo"
    grep -q '"groups"' "$GEN_DIR/roo"
}

# ── generate_aider_conf.py ────────────────────────────────────────────────

@test "generate_aider_conf.py exits 0" {
    [ "$(cat "$GEN_DIR/aider.status")" = "0" ]
}

@test "generate_aider_conf.py output is non-empty" {
    [ "$(wc -c < "$GEN_DIR/aider" | xargs)" -gt 100 ]
}

@test "generate_aider_conf.py output contains model config" {
    grep -q 'model:' "$GEN_DIR/aider"
}

@test "generate_aider_conf.py output contains lint commands" {
    grep -q 'lint-cmd' "$GEN_DIR/aider"
}

@test "generate_aider_conf.py output mentions ai-toolkit" {
    grep -qiE 'ai.toolkit' "$GEN_DIR/aider"
}

# ── cross-generator: all outputs mention ai-toolkit ──────────────────────────

@test "all generators mention ai-toolkit in output" {
    failed=0
    for name in cursor copilot cline windsurf gemini aider; do
        grep -qiE 'ai.toolkit' "$GEN_DIR/$name" || failed=$((failed+1))
    done
    [ "$failed" -eq 0 ]
}
