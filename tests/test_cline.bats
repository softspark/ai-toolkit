#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Dedicated tests for scripts/generate_cline.py and
# scripts/generate_cline_rules.py.
#
# Covers both surfaces:
#   1. Legacy .clinerules single-file output (stdout) used by older Cline
#      versions — backwards compatibility contract.
#   2. Modern .clinerules/*.md directory layout (Cline 3.7+) with:
#        - conditional "paths:" YAML frontmatter on file-type rules
#        - .clinerules/workflows/*.md slash-invocable workflows

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export CLINE_TMP; CLINE_TMP="$(mktemp -d)"
    export CLINE_STDOUT="$CLINE_TMP/cline-legacy"
    python3 "$TOOLKIT_DIR/scripts/generate_cline.py" > "$CLINE_STDOUT" 2>/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_cline_rules.py" "$CLINE_TMP" >/dev/null 2>&1
}

teardown_file() {
    rm -rf "$CLINE_TMP"
}

# ── Legacy stdout mode (.clinerules single file) ───────────────────────────

@test "generate_cline.py produces non-empty legacy output" {
    [ -s "$CLINE_STDOUT" ]
    [ "$(wc -c < "$CLINE_STDOUT" | xargs)" -gt 500 ]
}

@test "generate_cline.py legacy output references agents and skills" {
    grep -qi 'agent' "$CLINE_STDOUT"
    grep -qi 'skill' "$CLINE_STDOUT"
}

@test "generate_cline.py legacy output has TOOLKIT markers" {
    grep -q 'TOOLKIT:ai-toolkit START' "$CLINE_STDOUT"
    grep -q 'TOOLKIT:ai-toolkit END' "$CLINE_STDOUT"
}

# ── Modern .clinerules/ directory ──────────────────────────────────────────

@test "generate_cline_rules.py emits native .cline/rules as primary plus compatibility rules" {
    [ -f "$CLINE_TMP/.cline/rules/ai-toolkit-security.md" ]
    [ -f "$CLINE_TMP/.clinerules/ai-toolkit-security.md" ]
    cmp "$CLINE_TMP/.cline/rules/ai-toolkit-security.md" \
        "$CLINE_TMP/.clinerules/ai-toolkit-security.md"
}

@test "generate_cline_rules.py creates .clinerules/ directory" {
    [ -d "$CLINE_TMP/.clinerules" ]
}

@test "generate_cline_rules.py emits at least 6 standard rule files" {
    count=$(ls "$CLINE_TMP/.clinerules"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 6 ]
}

@test "generate_cline_rules.py testing rule has conditional paths frontmatter" {
    f="$CLINE_TMP/.clinerules/ai-toolkit-testing.md"
    [ -f "$f" ]
    head -1 "$f" | grep -q '^---'
    grep -q '^paths:' "$f"
    # Must match test files
    grep -q 'tests/' "$f"
}

@test "generate_cline_rules.py security rule has no conditional paths (always-on)" {
    f="$CLINE_TMP/.clinerules/ai-toolkit-security.md"
    [ -f "$f" ]
    # Security applies everywhere; no paths: frontmatter at the top
    ! head -1 "$f" | grep -q '^---' || ! grep -q '^paths:' "$f"
}

# ── Workflows (.clinerules/workflows/) ─────────────────────────────────────

@test "generate_cline_rules.py creates .clinerules/workflows/ directory" {
    [ -d "$CLINE_TMP/.clinerules/workflows" ]
}

@test "generate_cline_rules.py emits at least 10 workflow files" {
    count=$(ls "$CLINE_TMP/.clinerules/workflows"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 10 ]
}

@test "generate_cline_rules.py workflow files have description frontmatter" {
    for f in "$CLINE_TMP/.clinerules/workflows"/ai-toolkit-*.md; do
        head -1 "$f" | grep -q '^---' || { echo "No frontmatter: $f"; return 1; }
        grep -q '^description: ' "$f" || { echo "No description: $f"; return 1; }
    done
}

@test "generate_cline_rules.py workflows cover common development lifecycle" {
    [ -f "$CLINE_TMP/.clinerules/workflows/ai-toolkit-debug.md" ]
    [ -f "$CLINE_TMP/.clinerules/workflows/ai-toolkit-feature-development.md" ]
    [ -f "$CLINE_TMP/.clinerules/workflows/ai-toolkit-refactor.md" ]
    [ -f "$CLINE_TMP/.clinerules/workflows/ai-toolkit-security-audit.md" ]
}

# ── Language rules use conditional paths scoping ───────────────────────────

@test "generate_cline_rules.py scopes language rules to their file globs" {
    local tmp; tmp="$(mktemp -d)"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_cline_rules import generate
generate(Path('$tmp'), language_modules=['rules-python'])
" >/dev/null 2>&1
    [ -f "$tmp/.clinerules/ai-toolkit-lang-python.md" ]
    grep -q '^paths:' "$tmp/.clinerules/ai-toolkit-lang-python.md"
    grep -q '\*\*/\*.py' "$tmp/.clinerules/ai-toolkit-lang-python.md"
    # Common spans all languages — no conditional scoping
    [ -f "$tmp/.clinerules/ai-toolkit-lang-common.md" ]
    ! grep -q '^paths:' "$tmp/.clinerules/ai-toolkit-lang-common.md"
    rm -rf "$tmp"
}

# ── Idempotency and user-file preservation ─────────────────────────────────

@test "generate_cline_rules.py is idempotent across reruns" {
    local tmp; tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cline_rules.py" "$tmp" >/dev/null 2>&1
    count1=$(ls "$tmp/.clinerules"/ai-toolkit-*.md | wc -l | xargs)
    wf1=$(ls "$tmp/.clinerules/workflows"/ai-toolkit-*.md | wc -l | xargs)
    python3 "$TOOLKIT_DIR/scripts/generate_cline_rules.py" "$tmp" >/dev/null 2>&1
    count2=$(ls "$tmp/.clinerules"/ai-toolkit-*.md | wc -l | xargs)
    wf2=$(ls "$tmp/.clinerules/workflows"/ai-toolkit-*.md | wc -l | xargs)
    [ "$count1" -eq "$count2" ]
    [ "$wf1" -eq "$wf2" ]
    rm -rf "$tmp"
}

@test "generate_cline_rules.py preserves user files in .clinerules and workflows" {
    local tmp; tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cline_rules.py" "$tmp" >/dev/null 2>&1
    echo "my rule" > "$tmp/.clinerules/my-team-rules.md"
    echo "my workflow" > "$tmp/.clinerules/workflows/my-deploy.md"
    python3 "$TOOLKIT_DIR/scripts/generate_cline_rules.py" "$tmp" >/dev/null 2>&1
    grep -q '^my rule$' "$tmp/.clinerules/my-team-rules.md"
    grep -q '^my workflow$' "$tmp/.clinerules/workflows/my-deploy.md"
    rm -rf "$tmp"
}

@test "generate_cline_rules.py preserves a user-owned legacy .clinerules file" {
    local tmp; tmp="$(mktemp -d)"
    printf '%s\n' '# Team Cline rules' 'Keep this byte-identical.' \
        > "$tmp/.clinerules"
    cp "$tmp/.clinerules" "$tmp/before.clinerules"
    [ -f "$tmp/.clinerules" ]
    run python3 "$TOOLKIT_DIR/scripts/generate_cline_rules.py" "$tmp"
    [ "$status" -eq 0 ]
    [ -f "$tmp/.clinerules" ]
    cmp "$tmp/before.clinerules" "$tmp/.clinerules"
    [ -f "$tmp/.cline/rules/ai-toolkit-security.md" ]
    rm -rf "$tmp"
}

@test "generate_cline_rules.py rejects a symlinked Documents ancestor without mutation" {
    local tmp outside before
    tmp="$(mktemp -d)"
    outside="$(mktemp -d)"
    mkdir -p "$outside/Cline/Rules"
    printf '%s\n' 'outside rule bytes' \
        > "$outside/Cline/Rules/ai-toolkit-security.md"
    before="$(cksum "$outside/Cline/Rules/ai-toolkit-security.md")"
    ln -s "$outside" "$tmp/Documents"

    run python3 - "$TOOLKIT_DIR" "$tmp" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from generate_cline_rules import generate

target = Path(sys.argv[2])
generate(
    target,
    output_root=target / "Documents" / "Cline" / "Rules",
    emit_workflows=False,
)
PY

    [ "$status" -ne 0 ]
    [ "$(cksum "$outside/Cline/Rules/ai-toolkit-security.md")" = "$before" ]
    rm -rf "$tmp" "$outside"
}

@test "generate_cline_skills.py rejects a symlinked .cline ancestor without mutation" {
    local tmp outside before
    tmp="$(mktemp -d)"
    outside="$(mktemp -d)"
    mkdir -p "$outside/skills/ai-toolkit-skill-catalogue"
    printf '%s\n' 'outside skill bytes' \
        > "$outside/skills/ai-toolkit-skill-catalogue/SKILL.md"
    before="$(cksum "$outside/skills/ai-toolkit-skill-catalogue/SKILL.md")"
    ln -s "$outside" "$tmp/.cline"

    run python3 "$TOOLKIT_DIR/scripts/generate_cline_skills.py" "$tmp"

    [ "$status" -ne 0 ]
    [ "$(cksum "$outside/skills/ai-toolkit-skill-catalogue/SKILL.md")" = "$before" ]
    rm -rf "$tmp" "$outside"
}

@test "Cline skill discovery rejects a symlinked ancestor before reading outside" {
    local tmp outside before
    tmp="$(mktemp -d)"
    outside="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cline_skills.py" "$outside" >/dev/null
    before="$(cksum "$outside/.cline/skills/ai-toolkit-skill-catalogue/SKILL.md")"
    ln -s "$outside/.cline" "$tmp/.cline"

    run python3 - "$TOOLKIT_DIR" "$tmp" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from generate_cline_skills import discover

try:
    discover(Path(sys.argv[2]))
except RuntimeError:
    pass
else:
    raise AssertionError("symlinked Cline skill ancestry was accepted")
PY

    [ "$status" -eq 0 ]
    [ "$(cksum "$outside/.cline/skills/ai-toolkit-skill-catalogue/SKILL.md")" = "$before" ]
    rm -rf "$tmp" "$outside"
}

@test "Cline skill cleanup rejects a symlinked ancestor without deleting outside" {
    local tmp outside before
    tmp="$(mktemp -d)"
    outside="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cline_skills.py" "$outside" >/dev/null
    before="$(cksum "$outside/.cline/skills/ai-toolkit-skill-catalogue/SKILL.md")"
    ln -s "$outside/.cline" "$tmp/.cline"

    run python3 - "$TOOLKIT_DIR" "$tmp" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from generate_cline_skills import cleanup

try:
    cleanup(Path(sys.argv[2]))
except RuntimeError:
    pass
else:
    raise AssertionError("symlinked Cline skill ancestry was accepted")
PY

    [ "$status" -eq 0 ]
    [ -f "$outside/.cline/skills/ai-toolkit-skill-catalogue/SKILL.md" ]
    [ "$(cksum "$outside/.cline/skills/ai-toolkit-skill-catalogue/SKILL.md")" = "$before" ]
    rm -rf "$tmp" "$outside"
}

@test "Cline rule discovery and cleanup reject symlink ancestry without outside mutation" {
    local tmp outside before
    tmp="$(mktemp -d)"
    outside="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cline_rules.py" "$outside" >/dev/null
    before="$(cksum "$outside/.cline/rules/ai-toolkit-security.md")"
    ln -s "$outside/.cline" "$tmp/.cline"

    run python3 - "$TOOLKIT_DIR" "$tmp" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from generate_cline_rules import cleanup, managed_files

target = Path(sys.argv[2])
for operation in (managed_files, cleanup):
    try:
        operation(target)
    except RuntimeError:
        continue
    raise AssertionError(f"{operation.__name__} accepted symlink ancestry")
PY

    [ "$status" -eq 0 ]
    [ -f "$outside/.cline/rules/ai-toolkit-security.md" ]
    [ "$(cksum "$outside/.cline/rules/ai-toolkit-security.md")" = "$before" ]
    rm -rf "$tmp" "$outside"
}
