#!/usr/bin/env bats
# Workstream 3: Generator contract tests — cached to temp files (avoids env size limits)
# Each generator runs ONCE in setup_file, output written to temp files.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export GEN_DIR; GEN_DIR="$(mktemp -d)"
    export AG_DIR; AG_DIR="$(mktemp -d)"
    export CURSOR_DIR; CURSOR_DIR="$(mktemp -d)"
    export WS_DIR; WS_DIR="$(mktemp -d)"
    export CL_DIR; CL_DIR="$(mktemp -d)"
    export ROO_DIR; ROO_DIR="$(mktemp -d)"
    export AUG_DIR; AUG_DIR="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity.py" "$AG_DIR" > "$GEN_DIR/antigravity.log" 2>/dev/null; echo $? > "$GEN_DIR/antigravity.status"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_mdc.py" "$CURSOR_DIR" > "$GEN_DIR/cursor-mdc.log" 2>/dev/null; echo $? > "$GEN_DIR/cursor-mdc.status"
    python3 "$TOOLKIT_DIR/scripts/generate_windsurf_rules.py" "$WS_DIR" > "$GEN_DIR/windsurf-rules.log" 2>/dev/null; echo $? > "$GEN_DIR/windsurf-rules.status"
    python3 "$TOOLKIT_DIR/scripts/generate_cline_rules.py" "$CL_DIR" > "$GEN_DIR/cline-rules.log" 2>/dev/null; echo $? > "$GEN_DIR/cline-rules.status"
    python3 "$TOOLKIT_DIR/scripts/generate_roo_rules.py" "$ROO_DIR" > "$GEN_DIR/roo-rules.log" 2>/dev/null; echo $? > "$GEN_DIR/roo-rules.status"
    python3 "$TOOLKIT_DIR/scripts/generate_augment_rules.py" "$AUG_DIR" > "$GEN_DIR/augment-rules.log" 2>/dev/null; echo $? > "$GEN_DIR/augment-rules.status"
    python3 "$TOOLKIT_DIR/scripts/generate_conventions.py" > "$GEN_DIR/conventions" 2>/dev/null; echo $? > "$GEN_DIR/conventions.status"
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
    rm -rf "$GEN_DIR" "$AG_DIR" "$CURSOR_DIR" "$WS_DIR" "$CL_DIR" "$ROO_DIR" "$AUG_DIR"
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

# ── generate_antigravity.py ─────────────────────────────────────────────────

@test "generate_antigravity.py exits 0" {
    [ "$(cat "$GEN_DIR/antigravity.status")" = "0" ]
}

@test "generate_antigravity.py creates .agent/rules/ directory" {
    [ -d "$AG_DIR/.agent/rules" ]
}

@test "generate_antigravity.py creates .agent/workflows/ directory" {
    [ -d "$AG_DIR/.agent/workflows" ]
}

@test "generate_antigravity.py creates all 6 rule files" {
    expected="ai-toolkit-agents-and-skills.md ai-toolkit-code-style.md ai-toolkit-quality-standards.md ai-toolkit-security.md ai-toolkit-testing.md ai-toolkit-workflow.md"
    missing=0
    for f in $expected; do
        [ -f "$AG_DIR/.agent/rules/$f" ] || missing=$((missing + 1))
    done
    [ "$missing" -eq 0 ]
}

@test "generate_antigravity.py creates all 13 workflow files" {
    expected="ai-toolkit-api-design.md ai-toolkit-code-review.md ai-toolkit-codebase-onboarding.md ai-toolkit-database-migration.md ai-toolkit-debug.md ai-toolkit-docs.md ai-toolkit-feature-development.md ai-toolkit-incident-response.md ai-toolkit-performance-optimization.md ai-toolkit-refactor.md ai-toolkit-security-audit.md ai-toolkit-tdd.md ai-toolkit-test-coverage.md"
    missing=0
    for f in $expected; do
        [ -f "$AG_DIR/.agent/workflows/$f" ] || missing=$((missing + 1))
    done
    [ "$missing" -eq 0 ]
}

@test "generate_antigravity.py rule files are non-empty markdown" {
    for f in "$AG_DIR"/.agent/rules/ai-toolkit-*.md; do
        [ -s "$f" ] || { echo "Empty: $f"; return 1; }
        grep -q '^# ' "$f" || { echo "No heading: $f"; return 1; }
    done
}

@test "generate_antigravity.py workflow files have YAML frontmatter" {
    for f in "$AG_DIR"/.agent/workflows/ai-toolkit-*.md; do
        head -1 "$f" | grep -q '^---' || { echo "No frontmatter: $f"; return 1; }
        grep -q '^description:' "$f" || { echo "No description: $f"; return 1; }
    done
}

@test "generate_antigravity.py agents-and-skills file contains all agents" {
    missing=0
    for f in "$TOOLKIT_DIR"/app/agents/*.md; do
        agent_name="${f##*/}"; agent_name="${agent_name%.md}"
        grep -q "$agent_name" "$AG_DIR/.agent/rules/ai-toolkit-agents-and-skills.md" || missing=$((missing + 1))
    done
    [ "$missing" -eq 0 ]
}

@test "generate_antigravity.py agents-and-skills file references skills" {
    grep -qiE 'skill' "$AG_DIR/.agent/rules/ai-toolkit-agents-and-skills.md"
}

@test "generate_antigravity.py preserves user files" {
    # Create user files
    echo "* My rule" > "$AG_DIR/.agent/rules/my-custom.md"
    echo "* My flow" > "$AG_DIR/.agent/workflows/deploy.md"
    # Re-run generator
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity.py" "$AG_DIR" >/dev/null 2>&1
    # Verify user files untouched
    grep -q "My rule" "$AG_DIR/.agent/rules/my-custom.md"
    grep -q "My flow" "$AG_DIR/.agent/workflows/deploy.md"
}

@test "generate_antigravity.py is idempotent" {
    # Run twice, count files — should be same
    count1=$(ls "$AG_DIR/.agent/rules"/ai-toolkit-*.md | wc -l | xargs)
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity.py" "$AG_DIR" >/dev/null 2>&1
    count2=$(ls "$AG_DIR/.agent/rules"/ai-toolkit-*.md | wc -l | xargs)
    [ "$count1" -eq "$count2" ]
}

@test "generate_antigravity.py cleans stale toolkit files" {
    # Create a fake stale toolkit file
    echo "stale" > "$AG_DIR/.agent/rules/ai-toolkit-obsolete.md"
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity.py" "$AG_DIR" >/dev/null 2>&1
    # Stale file should be removed
    [ ! -f "$AG_DIR/.agent/rules/ai-toolkit-obsolete.md" ]
}

# ── generate_cursor_mdc.py ──────────────────────────────────────────────────

@test "generate_cursor_mdc.py exits 0" {
    [ "$(cat "$GEN_DIR/cursor-mdc.status")" = "0" ]
}

@test "generate_cursor_mdc.py creates .cursor/rules/ with 6 .mdc files" {
    count=$(ls "$CURSOR_DIR/.cursor/rules"/ai-toolkit-*.mdc 2>/dev/null | wc -l | xargs)
    [ "$count" -eq 6 ]
}

@test "generate_cursor_mdc.py .mdc files have YAML frontmatter with alwaysApply" {
    for f in "$CURSOR_DIR"/.cursor/rules/ai-toolkit-*.mdc; do
        head -1 "$f" | grep -q '^---' || { echo "No frontmatter: $f"; return 1; }
        grep -q 'alwaysApply:' "$f" || { echo "No alwaysApply: $f"; return 1; }
    done
}

@test "generate_cursor_mdc.py testing.mdc has globs for test files" {
    grep -q 'globs:' "$CURSOR_DIR/.cursor/rules/ai-toolkit-testing.mdc"
}

@test "generate_cursor_mdc.py agents-and-skills.mdc contains agent names" {
    missing=0
    for f in "$TOOLKIT_DIR"/app/agents/*.md; do
        agent_name="${f##*/}"; agent_name="${agent_name%.md}"
        grep -q "$agent_name" "$CURSOR_DIR/.cursor/rules/ai-toolkit-agents-and-skills.mdc" || missing=$((missing + 1))
    done
    [ "$missing" -eq 0 ]
}

# ── generate_windsurf_rules.py ──────────────────────────────────────────────

@test "generate_windsurf_rules.py exits 0" {
    [ "$(cat "$GEN_DIR/windsurf-rules.status")" = "0" ]
}

@test "generate_windsurf_rules.py creates 6 rule files" {
    count=$(ls "$WS_DIR/.windsurf/rules"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -eq 6 ]
}

# ── generate_cline_rules.py ────────────────────────────────────────────────

@test "generate_cline_rules.py exits 0" {
    [ "$(cat "$GEN_DIR/cline-rules.status")" = "0" ]
}

@test "generate_cline_rules.py creates 6 rule files" {
    count=$(ls "$CL_DIR/.clinerules"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -eq 6 ]
}

# ── generate_roo_rules.py ──────────────────────────────────────────────────

@test "generate_roo_rules.py exits 0" {
    [ "$(cat "$GEN_DIR/roo-rules.status")" = "0" ]
}

@test "generate_roo_rules.py creates 6 rule files" {
    count=$(ls "$ROO_DIR/.roo/rules"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -eq 6 ]
}

# ── generate_augment_rules.py ──────────────────────────────────────────────

@test "generate_augment_rules.py exits 0" {
    [ "$(cat "$GEN_DIR/augment-rules.status")" = "0" ]
}

@test "generate_augment_rules.py creates 6 rule files" {
    count=$(ls "$AUG_DIR/.augment/rules"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -eq 6 ]
}

@test "generate_augment_rules.py testing.md has agent_requested type" {
    grep -q 'type: agent_requested' "$AUG_DIR/.augment/rules/ai-toolkit-testing.md"
}

@test "generate_augment_rules.py agents-and-skills.md has always_apply type" {
    grep -q 'type: always_apply' "$AUG_DIR/.augment/rules/ai-toolkit-agents-and-skills.md"
}

# ── generate_conventions.py ────────────────────────────────────────────────

@test "generate_conventions.py exits 0" {
    [ "$(cat "$GEN_DIR/conventions.status")" = "0" ]
}

@test "generate_conventions.py output contains agents and skills" {
    grep -qi 'agent' "$GEN_DIR/conventions"
    grep -qi 'skill' "$GEN_DIR/conventions"
}

@test "generate_conventions.py output has TOOLKIT markers" {
    grep -q 'TOOLKIT:ai-toolkit START' "$GEN_DIR/conventions"
}

# ── cross-platform: all dir-rules generators produce same file count ────────

@test "all directory-based generators produce 6 rule files" {
    for dir in "$AG_DIR/.agent/rules" "$CURSOR_DIR/.cursor/rules" "$WS_DIR/.windsurf/rules" "$CL_DIR/.clinerules" "$ROO_DIR/.roo/rules" "$AUG_DIR/.augment/rules"; do
        count=$(ls "$dir"/ai-toolkit-*.* 2>/dev/null | wc -l | xargs)
        [ "$count" -eq 6 ] || { echo "Expected 6 in $dir, got $count"; return 1; }
    done
}

# ── cross-generator: all outputs mention ai-toolkit ──────────────────────────

@test "all generators mention ai-toolkit in output" {
    failed=0
    for name in cursor copilot cline windsurf gemini aider; do
        grep -qiE 'ai.toolkit' "$GEN_DIR/$name" || failed=$((failed+1))
    done
    [ "$failed" -eq 0 ]
}

# ── language rules: directory-based generators emit lang files ────────────────

@test "windsurf generates language rule files when language_modules set" {
    local tmp; tmp="$(mktemp -d)"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_windsurf_rules import generate
generate(Path('$tmp'), language_modules=['rules-python'])
" >/dev/null 2>&1
    [ -f "$tmp/.windsurf/rules/ai-toolkit-lang-common.md" ]
    [ -f "$tmp/.windsurf/rules/ai-toolkit-lang-python.md" ]
    # Standard rules still present
    [ -f "$tmp/.windsurf/rules/ai-toolkit-code-style.md" ]
    # Total: 6 standard + 2 lang = 8
    count=$(ls "$tmp/.windsurf/rules"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -eq 8 ]
    rm -rf "$tmp"
}

@test "cline generates language rule files when language_modules set" {
    local tmp; tmp="$(mktemp -d)"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_cline_rules import generate
generate(Path('$tmp'), language_modules=['rules-typescript'])
" >/dev/null 2>&1
    [ -f "$tmp/.clinerules/ai-toolkit-lang-common.md" ]
    [ -f "$tmp/.clinerules/ai-toolkit-lang-typescript.md" ]
    rm -rf "$tmp"
}

@test "roo generates language rule files when language_modules set" {
    local tmp; tmp="$(mktemp -d)"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_roo_rules import generate
generate(Path('$tmp'), language_modules=['rules-python', 'rules-golang'])
" >/dev/null 2>&1
    [ -f "$tmp/.roo/rules/ai-toolkit-lang-common.md" ]
    [ -f "$tmp/.roo/rules/ai-toolkit-lang-python.md" ]
    [ -f "$tmp/.roo/rules/ai-toolkit-lang-golang.md" ]
    rm -rf "$tmp"
}

@test "antigravity generates language rule files when language_modules set" {
    local tmp; tmp="$(mktemp -d)"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_antigravity import generate
generate(Path('$tmp'), language_modules=['rules-rust'])
" >/dev/null 2>&1
    [ -f "$tmp/.agent/rules/ai-toolkit-lang-common.md" ]
    [ -f "$tmp/.agent/rules/ai-toolkit-lang-rust.md" ]
    rm -rf "$tmp"
}

@test "cursor mdc generates language .mdc files with frontmatter" {
    local tmp; tmp="$(mktemp -d)"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_cursor_mdc import generate
generate(Path('$tmp'), language_modules=['rules-python'])
" >/dev/null 2>&1
    [ -f "$tmp/.cursor/rules/ai-toolkit-lang-python.mdc" ]
    [ -f "$tmp/.cursor/rules/ai-toolkit-lang-common.mdc" ]
    # Python mdc has globs for *.py
    grep -q 'globs:' "$tmp/.cursor/rules/ai-toolkit-lang-python.mdc"
    grep -q '"\*\*/\*.py"' "$tmp/.cursor/rules/ai-toolkit-lang-python.mdc"
    # Common mdc has alwaysApply: true (no globs)
    grep -q 'alwaysApply: true' "$tmp/.cursor/rules/ai-toolkit-lang-common.mdc"
    rm -rf "$tmp"
}

@test "augment generates language files with agent_requested frontmatter" {
    local tmp; tmp="$(mktemp -d)"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_augment_rules import generate
generate(Path('$tmp'), language_modules=['rules-python'])
" >/dev/null 2>&1
    [ -f "$tmp/.augment/rules/ai-toolkit-lang-python.md" ]
    grep -q 'type: agent_requested' "$tmp/.augment/rules/ai-toolkit-lang-python.md"
    grep -q '"\*\*/\*.py"' "$tmp/.augment/rules/ai-toolkit-lang-python.md"
    # Common has always_apply
    grep -q 'type: always_apply' "$tmp/.augment/rules/ai-toolkit-lang-common.md"
    rm -rf "$tmp"
}

@test "language rule files contain actual rule content (not pointers)" {
    local tmp; tmp="$(mktemp -d)"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_windsurf_rules import generate
generate(Path('$tmp'), language_modules=['rules-python'])
" >/dev/null 2>&1
    # Python rules should contain type hints section
    grep -q 'Type Hints' "$tmp/.windsurf/rules/ai-toolkit-lang-python.md"
    # Common rules should contain naming section
    grep -q 'Naming' "$tmp/.windsurf/rules/ai-toolkit-lang-common.md"
    rm -rf "$tmp"
}

@test "language rule files strip YAML frontmatter from source" {
    local tmp; tmp="$(mktemp -d)"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_windsurf_rules import generate
generate(Path('$tmp'), language_modules=['rules-python'])
" >/dev/null 2>&1
    # Should NOT contain source frontmatter fields like 'language: python'
    ! grep -q '^language: python' "$tmp/.windsurf/rules/ai-toolkit-lang-python.md"
    ! grep -q '^category: coding-style' "$tmp/.windsurf/rules/ai-toolkit-lang-python.md"
    rm -rf "$tmp"
}

# ── registered rules: directory-based generators emit custom files ────────────

@test "windsurf generates registered rule files from rules_dir" {
    local tmp; tmp="$(mktemp -d)"
    local rules_tmp; rules_tmp="$(mktemp -d)"
    echo "# My Custom Rule" > "$rules_tmp/my-team-rules.md"
    echo "# Another Rule" > "$rules_tmp/code-ownership.md"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_windsurf_rules import generate
generate(Path('$tmp'), rules_dir=Path('$rules_tmp'))
" >/dev/null 2>&1
    [ -f "$tmp/.windsurf/rules/ai-toolkit-custom-my-team-rules.md" ]
    [ -f "$tmp/.windsurf/rules/ai-toolkit-custom-code-ownership.md" ]
    grep -q 'My Custom Rule' "$tmp/.windsurf/rules/ai-toolkit-custom-my-team-rules.md"
    rm -rf "$tmp" "$rules_tmp"
}

@test "cursor mdc wraps registered rules with alwaysApply frontmatter" {
    local tmp; tmp="$(mktemp -d)"
    local rules_tmp; rules_tmp="$(mktemp -d)"
    echo "# Team Standards" > "$rules_tmp/team-standards.md"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_cursor_mdc import generate
generate(Path('$tmp'), rules_dir=Path('$rules_tmp'))
" >/dev/null 2>&1
    [ -f "$tmp/.cursor/rules/ai-toolkit-custom-team-standards.mdc" ]
    grep -q 'alwaysApply: true' "$tmp/.cursor/rules/ai-toolkit-custom-team-standards.mdc"
    grep -q 'Team Standards' "$tmp/.cursor/rules/ai-toolkit-custom-team-standards.mdc"
    rm -rf "$tmp" "$rules_tmp"
}

@test "stale lang/custom files are cleaned up on re-run" {
    local tmp; tmp="$(mktemp -d)"
    # First run: with python
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_windsurf_rules import generate
generate(Path('$tmp'), language_modules=['rules-python'])
" >/dev/null 2>&1
    [ -f "$tmp/.windsurf/rules/ai-toolkit-lang-python.md" ]
    # Second run: without python — stale lang file should be removed
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_windsurf_rules import generate
generate(Path('$tmp'))
" >/dev/null 2>&1
    [ ! -f "$tmp/.windsurf/rules/ai-toolkit-lang-python.md" ]
    [ ! -f "$tmp/.windsurf/rules/ai-toolkit-lang-common.md" ]
    rm -rf "$tmp"
}

@test "generators without language_modules produce only 6 standard files" {
    local tmp; tmp="$(mktemp -d)"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_windsurf_rules import generate
generate(Path('$tmp'))
" >/dev/null 2>&1
    count=$(ls "$tmp/.windsurf/rules"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -eq 6 ]
    rm -rf "$tmp"
}
