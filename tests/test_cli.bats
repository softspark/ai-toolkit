#!/usr/bin/env bats
# Workstream 2: CLI end-to-end coverage for bin/ai-toolkit.js
# Tests the public CLI surface: help, error handling, file-generating commands,
# and rule management (add-rule / remove-rule).
# Run with: bats tests/test_cli.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CLI="node $TOOLKIT_DIR/bin/ai-toolkit.js"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# ── Help and version ─────────────────────────────────────────────────────────

@test "cli: help exits 0" {
    run $CLI help
    [ "$status" -eq 0 ]
}

@test "cli: --help exits 0" {
    run $CLI --help
    [ "$status" -eq 0 ]
}

@test "cli: -h exits 0" {
    run $CLI -h
    [ "$status" -eq 0 ]
}

@test "cli: no command exits 0 and shows help" {
    run $CLI
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'ai-toolkit'
}

@test "cli: help lists install command" {
    run $CLI help
    echo "$output" | grep -q 'install'
}

@test "cli: help lists update command" {
    run $CLI help
    echo "$output" | grep -q 'update'
}

@test "cli: help lists add-rule command" {
    run $CLI help
    echo "$output" | grep -q 'add-rule'
}

@test "cli: help lists remove-rule command" {
    run $CLI help
    echo "$output" | grep -q 'remove-rule'
}

@test "cli: unknown command exits non-zero" {
    run $CLI totally-unknown-command-xyz
    [ "$status" -ne 0 ]
}

@test "cli: unknown command mentions the unknown command name" {
    run $CLI totally-unknown-command-xyz
    echo "$output" | grep -qi 'unknown'
}

# ── validate ─────────────────────────────────────────────────────────────────

@test "cli: validate exits 0 on clean toolkit" {
    run $CLI validate
    [ "$status" -eq 0 ]
}

# ── install --list (dry-run, no changes) ─────────────────────────────────────

@test "cli: install --list exits 0" {
    run $CLI install --list
    [ "$status" -eq 0 ]
}

@test "cli: install --list output mentions agents" {
    run $CLI install --list
    echo "$output" | grep -qi 'agents'
}

# ── update --list (alias, same behavior) ─────────────────────────────────────

@test "cli: update --list exits 0" {
    run $CLI update --list
    [ "$status" -eq 0 ]
}

@test "cli: update --list output matches install --list output" {
    run $CLI install --list
    install_out="$output"
    run $CLI update --list
    update_out="$output"
    [ "$install_out" = "$update_out" ]
}

# ── agents-md (merged: exits 0 + non-empty) ─────────────────────────────────

@test "cli: agents-md generates non-empty AGENTS.md" {
    cd "$TEST_TMP"
    run $CLI agents-md
    [ "$status" -eq 0 ]
    [ -s "$TEST_TMP/AGENTS.md" ]
}

# ── llms-txt (merged: generates files + size comparison) ─────────────────────

@test "cli: llms-txt generates llms.txt and llms-full.txt with correct sizes" {
    cd "$TEST_TMP"
    run $CLI llms-txt
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/llms.txt" ]
    [ -f "$TEST_TMP/llms-full.txt" ]
    size_index=$(wc -c < "$TEST_TMP/llms.txt" | xargs)
    size_full=$(wc -c < "$TEST_TMP/llms-full.txt" | xargs)
    [ "$size_full" -gt "$size_index" ]
}

# ── generate-all (merged: exits 0 + creates files) ──────────────────────────

@test "cli: generate-all creates all expected files" {
    cd "$TEST_TMP"
    mkdir -p "$TEST_TMP/.github"
    run $CLI generate-all
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/AGENTS.md" ]
    [ -f "$TEST_TMP/.cursorrules" ]
    [ -f "$TEST_TMP/.windsurfrules" ]
    [ -f "$TEST_TMP/.github/copilot-instructions.md" ]
    [ -f "$TEST_TMP/GEMINI.md" ]
    [ -f "$TEST_TMP/.clinerules" ]
    [ -f "$TEST_TMP/.roomodes" ]
    [ -f "$TEST_TMP/.aider.conf.yml" ]
    [ -f "$TEST_TMP/llms.txt" ]
    [ -f "$TEST_TMP/llms-full.txt" ]
}

# ── platform-specific generators ─────────────────────────────────────────────

@test "cli: cursor-rules generates .cursorrules" {
    cd "$TEST_TMP"
    run $CLI cursor-rules
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.cursorrules" ]
}

@test "cli: windsurf-rules generates .windsurfrules" {
    cd "$TEST_TMP"
    run $CLI windsurf-rules
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.windsurfrules" ]
}

@test "cli: copilot-instructions generates .github/copilot-instructions.md" {
    cd "$TEST_TMP"
    run $CLI copilot-instructions
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.github/copilot-instructions.md" ]
}

@test "cli: gemini-md generates GEMINI.md" {
    cd "$TEST_TMP"
    run $CLI gemini-md
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/GEMINI.md" ]
}

@test "cli: cline-rules generates .clinerules" {
    cd "$TEST_TMP"
    run $CLI cline-rules
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.clinerules" ]
}

# ── roo-modes (merged: generates + valid JSON) ──────────────────────────────

@test "cli: roo-modes generates valid JSON .roomodes" {
    cd "$TEST_TMP"
    run $CLI roo-modes
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.roomodes" ]
    python3 -c "import json; json.load(open('$TEST_TMP/.roomodes'))"
}

# ── aider-conf (merged: generates + content check) ──────────────────────────

@test "cli: aider-conf generates .aider.conf.yml with model config" {
    cd "$TEST_TMP"
    run $CLI aider-conf
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.aider.conf.yml" ]
    grep -q 'model:' "$TEST_TMP/.aider.conf.yml"
}

@test "cli: help lists roo-modes command" {
    run $CLI help
    echo "$output" | grep -q 'roo-modes'
}

@test "cli: help lists aider-conf command" {
    run $CLI help
    echo "$output" | grep -q 'aider-conf'
}

# ── add-rule ─────────────────────────────────────────────────────────────────

@test "cli: add-rule registers rule file in ~/.ai-toolkit/rules/" {
    export HOME="$TEST_TMP"
    printf '# Test rule\nDo something.\n' > "$TEST_TMP/my-rule.md"
    run $CLI add-rule "$TEST_TMP/my-rule.md"
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.ai-toolkit/rules/my-rule.md" ]
}

@test "cli: add-rule with custom name registers under that name" {
    export HOME="$TEST_TMP"
    printf '# Test rule\nDo something.\n' > "$TEST_TMP/source.md"
    run $CLI add-rule "$TEST_TMP/source.md" custom-name
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.ai-toolkit/rules/custom-name.md" ]
}

@test "cli: add-rule without arguments exits non-zero" {
    run $CLI add-rule
    [ "$status" -ne 0 ]
}

# ── remove-rule ──────────────────────────────────────────────────────────────

@test "cli: remove-rule unregisters rule from ~/.ai-toolkit/rules/" {
    export HOME="$TEST_TMP"
    printf '# Test rule\n' > "$TEST_TMP/rm-test.md"
    run $CLI add-rule "$TEST_TMP/rm-test.md"
    [ -f "$TEST_TMP/.ai-toolkit/rules/rm-test.md" ]

    run $CLI remove-rule rm-test
    [ "$status" -eq 0 ]
    [ ! -f "$TEST_TMP/.ai-toolkit/rules/rm-test.md" ]
}

@test "cli: remove-rule also strips injected block from CLAUDE.md" {
    export HOME="$TEST_TMP"
    mkdir -p "$TEST_TMP/.claude"
    printf '# Test rule\nSome content.\n' > "$TEST_TMP/strip-test.md"
    run $CLI add-rule "$TEST_TMP/strip-test.md"

    python3 "$TOOLKIT_DIR/scripts/inject_rule_cli.py" "$TEST_TMP/.ai-toolkit/rules/strip-test.md" "$TEST_TMP"
    grep -q 'TOOLKIT:strip-test' "$TEST_TMP/.claude/CLAUDE.md"

    run $CLI remove-rule strip-test "$TEST_TMP"
    [ "$status" -eq 0 ]
    if [ -f "$TEST_TMP/.claude/CLAUDE.md" ]; then
        ! grep -q 'TOOLKIT:strip-test' "$TEST_TMP/.claude/CLAUDE.md"
    fi
}

@test "cli: remove-rule without arguments exits non-zero" {
    run $CLI remove-rule
    [ "$status" -ne 0 ]
}

# ── doctor (cached: install once, assert multiple times) ─────────────────────

@test "cli: help lists doctor command" {
    run $CLI help
    echo "$output" | grep -q 'doctor'
}

@test "cli: doctor exits 0 and includes all sections on healthy install" {
    export HOME="$TEST_TMP"
    run $CLI install
    [ "$status" -eq 0 ]
    run $CLI doctor
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '## Environment'
    echo "$output" | grep -q '## Hook Configuration'
    echo "$output" | grep -q 'PreCompact'
    echo "$output" | grep -q '## Benchmark Freshness'
}

@test "cli: doctor exits non-zero when global install is missing" {
    export HOME="$TEST_TMP"
    run $CLI doctor
    [ "$status" -ne 0 ]
}

# ── benchmark-ecosystem ─────────────────────────────────────────────────────

@test "cli: help lists benchmark-ecosystem command" {
    run $CLI help
    echo "$output" | grep -q 'benchmark-ecosystem'
}

@test "cli: benchmark-ecosystem offline exits 0" {
    run $CLI benchmark-ecosystem --offline
    [ "$status" -eq 0 ]
}

@test "cli: benchmark-ecosystem offline output contains official Claude Code repo" {
    run $CLI benchmark-ecosystem --offline
    echo "$output" | grep -q 'anthropics/claude-code'
}

@test "cli: benchmark-ecosystem dashboard-json output contains freshness field" {
    run $CLI benchmark-ecosystem --offline --dashboard-json
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '"freshness"'
}

# ── stats ────────────────────────────────────────────────────────────────────

@test "cli: help lists stats command" {
    run $CLI help
    echo "$output" | grep -q 'stats'
}

@test "cli: stats exits 0 with no stats file" {
    run $CLI stats
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi 'no usage stats'
}

@test "cli: stats --reset exits 0" {
    run $CLI stats --reset
    [ "$status" -eq 0 ]
}

# ── create skill ─────────────────────────────────────────────────────────────

@test "cli: help lists create command" {
    run $CLI help
    echo "$output" | grep -q 'create'
}

@test "cli: create skill with linter template" {
    run $CLI create skill test-linter --template=linter --output-dir="$TEST_TMP"
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/test-linter/SKILL.md" ]
    head -1 "$TEST_TMP/test-linter/SKILL.md" | grep -q '^---$'
    grep -q 'name: test-linter' "$TEST_TMP/test-linter/SKILL.md"
}

@test "cli: create skill with knowledge template" {
    run $CLI create skill test-knowledge --template=knowledge --output-dir="$TEST_TMP"
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/test-knowledge/SKILL.md" ]
    grep -q 'user-invocable: false' "$TEST_TMP/test-knowledge/SKILL.md"
}

@test "cli: create skill without template fails" {
    run $CLI create skill test-no-template --output-dir="$TEST_TMP"
    [ "$status" -ne 0 ]
}

@test "cli: create skill with invalid template fails" {
    run $CLI create skill test-bad --template=nonexistent --output-dir="$TEST_TMP"
    [ "$status" -ne 0 ]
}

@test "cli: create skill with duplicate name fails" {
    mkdir -p "$TEST_TMP/test-dup"
    run $CLI create skill test-dup --template=linter --output-dir="$TEST_TMP"
    [ "$status" -ne 0 ]
}

@test "cli: create without subcommand fails" {
    run $CLI create
    [ "$status" -ne 0 ]
}

# ── benchmark --my-config ────────────────────────────────────────────────────

@test "cli: help lists benchmark command" {
    run $CLI help
    echo "$output" | grep -q 'benchmark'
}

@test "cli: benchmark --my-config exits 0" {
    run $CLI benchmark --my-config
    [ "$status" -eq 0 ]
}

@test "cli: benchmark --my-config shows coverage section" {
    run $CLI benchmark --my-config
    echo "$output" | grep -q 'Coverage'
}

@test "cli: benchmark --my-config shows ecosystem comparison" {
    run $CLI benchmark --my-config
    echo "$output" | grep -q 'Ecosystem Comparison'
}

# ── sync ─────────────────────────────────────────────────────────────────────

@test "cli: help lists sync command" {
    run $CLI help
    echo "$output" | grep -q 'sync'
}

@test "cli: sync without flags exits non-zero" {
    run $CLI sync
    [ "$status" -ne 0 ]
}

@test "cli: sync --export exits 0" {
    run $CLI sync --export
    [ "$status" -eq 0 ]
}

@test "cli: sync --export outputs valid JSON" {
    run $CLI sync --export
    echo "$output" | python3 -c "import json,sys; json.load(sys.stdin)"
}

@test "cli: sync --export includes schema_version" {
    run $CLI sync --export
    echo "$output" | grep -q '"schema_version"'
}

# ── CI action ────────────────────────────────────────────────────────────────

@test "action.yml exists and is non-empty" {
    [ -s "$TOOLKIT_DIR/action.yml" ]
}

@test "cli: sync export+import roundtrip preserves rules" {
    mkdir -p "$TEST_TMP/.ai-toolkit/rules"
    printf '# Test Rule\nDo something.' > "$TEST_TMP/.ai-toolkit/rules/test-rule.md"

    run $CLI sync --export
    echo "$output" > "$TEST_TMP/sync-snapshot.json"

    mv "$TEST_TMP/.ai-toolkit/rules" "$TEST_TMP/.ai-toolkit/rules-bak"

    run $CLI sync --import "$TEST_TMP/sync-snapshot.json"
    [ "$status" -eq 0 ]

    [ -f "$TEST_TMP/.ai-toolkit/rules/test-rule.md" ]
    grep -q 'Test Rule' "$TEST_TMP/.ai-toolkit/rules/test-rule.md"
}

# ── track-usage hook ──────────────────────────────────────────────────────────

@test "track-usage.sh records skill invocation" {
    mkdir -p "$TEST_TMP/.ai-toolkit"
    CLAUDE_USER_PROMPT="/commit some message" HOME="$TEST_TMP" \
        bash "$TOOLKIT_DIR/app/hooks/track-usage.sh"
    [ -f "$TEST_TMP/.ai-toolkit/stats.json" ]
    grep -q '"commit"' "$TEST_TMP/.ai-toolkit/stats.json"
}

@test "track-usage.sh ignores non-slash prompts" {
    mkdir -p "$TEST_TMP/.ai-toolkit"
    CLAUDE_USER_PROMPT="just a regular question" HOME="$TEST_TMP" \
        bash "$TOOLKIT_DIR/app/hooks/track-usage.sh"
    [ ! -f "$TEST_TMP/.ai-toolkit/stats.json" ]
}

@test "cli: stats reads existing stats file" {
    mkdir -p "$TEST_TMP/.ai-toolkit"
    printf '{"commit": {"count": 5, "last_used": "2026-03-29 10:00:00"}}' > "$TEST_TMP/.ai-toolkit/stats.json"
    run $CLI stats
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'commit'
    echo "$output" | grep -q '5'
}
