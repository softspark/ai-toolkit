#!/usr/bin/env bats
# Per-tool tests for Aider integration (generate_aider_conf.py).
#
# Upstream docs (as of 2026-04-23): https://aider.chat/docs/config/aider_conf.html
# Latest stable: v0.86.1 (August 2025). HISTORY.md: https://aider.chat/HISTORY.html
#
# Config surface we track in .aider.conf.yml:
#   - architect + auto-accept-architect (architect mode, 2-phase workflow)
#   - read (read-only context files: CONVENTIONS.md, AGENTS.md, .claude/*)
#   - lint-cmd / test-cmd (quality gates, aider >=0.80)
#   - model / editor-model
#   - commit-prompt, attribute-co-authored-by (git attribution policy)
#   - chat-language / commit-language (i18n, aider >=0.83)
#   - watch-files (AI coding comments, aider >=0.75)

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export AIDER_OUT; AIDER_OUT="$(mktemp)"
    python3 "$TOOLKIT_DIR/scripts/generate_aider_conf.py" > "$AIDER_OUT" 2>/dev/null
    echo $? > "$AIDER_OUT.status"
}

teardown_file() {
    rm -f "$AIDER_OUT" "$AIDER_OUT.status"
}

@test "generate_aider_conf.py exits 0" {
    [ "$(cat "$AIDER_OUT.status")" = "0" ]
}

@test "generate_aider_conf.py output is non-empty" {
    [ "$(wc -c < "$AIDER_OUT" | xargs)" -gt 500 ]
}

@test "aider conf opens with a generator attribution header" {
    head -3 "$AIDER_OUT" | grep -qiE 'ai.?toolkit'
}

@test "aider conf enables architect mode" {
    grep -qE '^architect:\s*true' "$AIDER_OUT"
}

@test "aider conf sets auto-accept-architect (Class B patch, 2026-04-23)" {
    # aider >=0.82 default is true, but we emit it explicitly so the user sees
    # the behavior without reading upstream docs.
    grep -qE '^auto-accept-architect:\s*(true|false)' "$AIDER_OUT"
}

@test "aider conf supplies a read-only context list" {
    grep -qE '^read:' "$AIDER_OUT"
    grep -q 'CONVENTIONS.md' "$AIDER_OUT"
    grep -q 'AGENTS.md'      "$AIDER_OUT"
    grep -q 'CLAUDE.md'      "$AIDER_OUT"
}

@test "aider conf emits lint-cmd list for multiple languages" {
    grep -qE '^lint-cmd:' "$AIDER_OUT"
    grep -q 'python:'     "$AIDER_OUT"
    grep -q 'typescript:' "$AIDER_OUT"
    grep -q 'javascript:' "$AIDER_OUT"
    grep -q 'php:'        "$AIDER_OUT"
    grep -q 'go:'         "$AIDER_OUT"
}

@test "aider conf documents test-cmd (commented default)" {
    # We emit it as a commented example so users have to opt in per project.
    grep -qE '^# test-cmd:' "$AIDER_OUT"
}

@test "aider conf pins model and editor-model" {
    grep -qE '^model:\s*claude-'        "$AIDER_OUT"
    grep -qE '^editor-model:\s*claude-' "$AIDER_OUT"
}

@test "aider conf uses hyphenated commit-prompt key (current aider schema)" {
    # Historical form was `commit_prompt:` (underscore); current docs use hyphen.
    grep -qE '^commit-prompt:' "$AIDER_OUT"
    ! grep -qE '^commit_prompt:' "$AIDER_OUT"
}

@test "aider conf disables AI co-author trailer by policy" {
    # ai-toolkit policy: no AI co-authorship in commits. Keep this off even
    # though aider's default is true in recent releases.
    grep -qE '^attribute-co-authored-by:\s*false' "$AIDER_OUT"
}

@test "aider conf mentions chat-language / commit-language" {
    # aider >=0.83 added commit-language; we leave them commented so the user
    # inherits system locale, but the keys are documented.
    grep -qE 'chat-language:'   "$AIDER_OUT"
    grep -qE 'commit-language:' "$AIDER_OUT"
}

@test "aider conf references watch-files flag" {
    # Opt-in because it changes buffer scanning behavior.
    grep -qE 'watch-files:' "$AIDER_OUT"
}

@test "aider conf shape parses cleanly (one colon per top-level key)" {
    python3 - "$AIDER_OUT" <<'PY'
import re, sys
content = open(sys.argv[1]).read()
top_keys = []
for line in content.splitlines():
    m = re.match(r'^([a-z][a-z0-9_-]*):', line)
    if m:
        top_keys.append(m.group(1))
# All top-level keys should have unique spelling (no accidental dupes)
assert len(top_keys) == len(set(top_keys)), f"duplicate top-level keys: {top_keys}"
# Required keys must be there
required = {"architect", "read", "lint-cmd", "model", "editor-model",
            "attribute-co-authored-by", "commit-prompt", "auto-accept-architect"}
missing = required - set(top_keys)
assert not missing, f"missing keys: {missing}"
PY
}
