#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Antigravity-specific tests for generate_antigravity.py.
# Verifies the canonical .agents/skills/ pointer, rule activation frontmatter,
# the 24,000-byte rule limit and MCP-gated registered rules.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
POINTER_SKILL="ai-toolkit-skill-catalogue"

setup_file() {
    export AG_TMP; AG_TMP="$(mktemp -d)"
    # Hermetic: no registered rules or MCP configs from the real home.
    export HOME="$AG_TMP/home" AI_TOOLKIT_HOME="$AG_TMP/home/.softspark/ai-toolkit"
    mkdir -p "$HOME"
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity.py" "$AG_TMP/project" >/dev/null
}

teardown_file() {
    rm -rf "$AG_TMP"
}

# ── Skill pointer ──────────────────────────────────────────────────────────

@test "antigravity: pointer SKILL.md exists in canonical .agents/skills" {
    [ -f "$AG_TMP/project/.agents/skills/$POINTER_SKILL/SKILL.md" ]
}

@test "antigravity: legacy .agent/skills copy is not written" {
    [ ! -e "$AG_TMP/project/.agent" ]
}

@test "antigravity: pointer SKILL.md has required frontmatter fields" {
    f="$AG_TMP/project/.agents/skills/$POINTER_SKILL/SKILL.md"
    head -1 "$f" | grep -q '^---$'
    head -10 "$f" | grep -c '^---$' | grep -q '^2$'
    head -5 "$f" | grep -q "^name: $POINTER_SKILL$"
    head -5 "$f" | grep -q "^description: "
}

@test "antigravity: pointer SKILL.md references installed skill paths and entries" {
    f="$AG_TMP/project/.agents/skills/$POINTER_SKILL/SKILL.md"
    grep -q '\.claude/skills' "$f"
    grep -q '~/\.claude/skills' "$f"
    count=$(grep -cE '^- \*\*' "$f")
    [ "$count" -ge 10 ]
}

@test "antigravity: reinstall removes the pointer an older release left in .agent/skills" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.agent/skills/$POINTER_SKILL" "$tmp/.agent/skills/user-skill"
    cp "$AG_TMP/project/.agents/skills/$POINTER_SKILL/SKILL.md" "$tmp/.agent/skills/$POINTER_SKILL/SKILL.md"
    echo "# mine" > "$tmp/.agent/skills/user-skill/SKILL.md"
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity.py" "$tmp" >/dev/null
    [ ! -e "$tmp/.agent/skills/$POINTER_SKILL" ]
    [ -f "$tmp/.agent/skills/user-skill/SKILL.md" ]
    [ -f "$tmp/.agents/skills/$POINTER_SKILL/SKILL.md" ]
    rm -rf "$tmp"
}

@test "antigravity: emit_skill_pointer=False suppresses pointer" {
    tmp="$(mktemp -d)"
    python3 - <<PY >/dev/null 2>&1
import sys
from pathlib import Path
sys.path.insert(0, "$TOOLKIT_DIR/scripts")
from generate_antigravity import generate
generate(Path("$tmp"), emit_skill_pointer=False)
PY
    [ ! -d "$tmp/.agents/skills" ] || {
        ! find "$tmp/.agents/skills" -name SKILL.md | grep -q .
    }
    rm -rf "$tmp"
}

@test "antigravity: pointer-only .agents/skills does not auto-detect codex" {
    run python3 - <<PY
import sys
from pathlib import Path
sys.path.insert(0, "$TOOLKIT_DIR/scripts")
from install_steps.ai_tools import _detect_editors
print(",".join(_detect_editors(Path("$AG_TMP/project"))))
PY
    [ "$status" -eq 0 ]
    [[ "$output" == *"antigravity"* ]]
    [[ "$output" != *"codex"* ]]
}

# ── Rules: activation frontmatter and size ─────────────────────────────────

@test "antigravity: every rule carries a valid trigger, always-on core is small" {
    run python3 - "$TOOLKIT_DIR/scripts" "$AG_TMP/project/.agents/rules" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from frontmatter import parse_frontmatter
rules = sorted(Path(sys.argv[2]).glob("ai-toolkit-*.md"))
assert len(rules) >= 7, rules
always_on = 0
for path in rules:
    meta = parse_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("trigger") in {"always_on", "model_decision", "glob", "manual"}, path
    assert meta.get("description"), path
    if meta["trigger"] == "always_on":
        always_on += path.stat().st_size
assert parse_frontmatter((Path(sys.argv[2]) / "ai-toolkit-agents-and-skills.md").read_text())["trigger"] == "model_decision"
# Keep the always-on core well inside the 20,000-token shared rules budget.
assert always_on < 16_000, always_on
PY
    [ "$status" -eq 0 ] || { echo "$output"; return 1; }
}

@test "antigravity: no generated rule exceeds the 24,000-byte truncation limit" {
    tmp="$(mktemp -d)"
    python3 - "$TOOLKIT_DIR/scripts" "$tmp" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from generate_antigravity import generate
generate(Path(sys.argv[2]), language_modules=[
    "rules-python", "rules-typescript", "rules-golang", "rules-rust", "rules-java",
    "rules-kotlin", "rules-swift", "rules-dart", "rules-csharp", "rules-php",
    "rules-cpp", "rules-ruby",
])
PY
    for f in "$tmp"/.agents/rules/*.md "$tmp"/.agents/skills/*/SKILL.md; do
        size=$(wc -c < "$f" | xargs)
        [ "$size" -le 24000 ] || { echo "$f: $size bytes"; rm -rf "$tmp"; return 1; }
    done
    rm -rf "$tmp"
}

@test "antigravity: language rules use quoted glob frontmatter" {
    tmp="$(mktemp -d)"
    python3 - "$TOOLKIT_DIR/scripts" "$tmp" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from generate_antigravity import generate
generate(Path(sys.argv[2]), language_modules=["rules-python"])
PY
    head -5 "$tmp/.agents/rules/ai-toolkit-lang-python.md" | grep -qx 'trigger: glob'
    head -5 "$tmp/.agents/rules/ai-toolkit-lang-python.md" | grep -qx 'globs: "\*\*/\*.py"'
    head -5 "$tmp/.agents/rules/ai-toolkit-lang-common.md" | grep -qx 'trigger: model_decision'
    rm -rf "$tmp"
}

# ── Registered rules gated on Antigravity's MCP configuration ──────────────

@test "antigravity: MCP rules follow mcp_config, legal stays opt-in, fallback is explicit" {
    tmp="$(mktemp -d)"
    rules="$tmp/rules"; home="$tmp/home"; project="$tmp/project"
    mkdir -p "$rules" "$home/.gemini/config" "$project"
    for name in rag-mcp-rules rag-mcp-legal-rules jira-mcp team-style; do
        echo "# $name" > "$rules/$name.md"
    done
    echo '{"mcpServers":{"rag-mcp":{"serverUrl":"http://x"},"rag-mcp-legal":{"serverUrl":"http://y"}}}' \
        > "$home/.gemini/config/mcp_config.json"
    run python3 - "$TOOLKIT_DIR/scripts" "$project" "$rules" "$home" <<'PY'
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
os.environ["HOME"] = sys.argv[4]
from generate_antigravity import generate
project, rules = Path(sys.argv[2]), Path(sys.argv[3])
generate(project, rules_dir=rules)
names = sorted(p.name for p in (project / ".agents/rules").glob("ai-toolkit-custom-*.md"))
assert names == ["ai-toolkit-custom-rag-mcp-rules.md", "ai-toolkit-custom-team-style.md"], names
rag = (project / ".agents/rules/ai-toolkit-custom-rag-mcp-rules.md").read_text()
assert "trigger: always_on" in rag and "is not available in this session" in rag and "`kb/`" in rag
assert "is not available" not in (project / ".agents/rules/ai-toolkit-custom-team-style.md").read_text()
generate(project, rules_dir=rules, opt_in_rules=["rag-mcp-legal-rules"])
assert (project / ".agents/rules/ai-toolkit-custom-rag-mcp-legal-rules.md").is_file()
generate(project, rules_dir=rules)
assert not (project / ".agents/rules/ai-toolkit-custom-rag-mcp-legal-rules.md").exists()
PY
    [ "$status" -eq 0 ] || { echo "$output"; rm -rf "$tmp"; return 1; }
    rm -rf "$tmp"
}

# ── Rules / workflows still emitted ────────────────────────────────────────

@test "antigravity: workflows still created alongside the skill pointer" {
    count=$(ls "$AG_TMP/project/.agents/workflows"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 10 ]
}

@test "antigravity: retired workflows keep all slash names through native skills" {
    count=0
    for workflow in "$AG_TMP"/project/.agents/workflows/ai-toolkit-*.md; do
        name="$(basename "$workflow" .md)"
        skill="$AG_TMP/project/.agents/skills/$name/SKILL.md"
        [ -f "$skill" ]
        grep -q "^name: $name$" "$skill"
        grep -q '^description: ' "$skill"
        grep -q 'ai-toolkit-managed: antigravity-workflow-skill' "$skill"
        grep -q 'DEPRECATED: workflows retire 2026-11-01' "$workflow"
        count=$((count + 1))
    done
    [ "$count" -eq 13 ]
}

@test "antigravity: regeneration is idempotent including the pointer and rules" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity.py" "$tmp" >/dev/null
    snap1=$(cat "$tmp/.agents/skills/$POINTER_SKILL/SKILL.md" "$tmp"/.agents/rules/*.md | shasum)
    python3 "$TOOLKIT_DIR/scripts/generate_antigravity.py" "$tmp" >/dev/null
    snap2=$(cat "$tmp/.agents/skills/$POINTER_SKILL/SKILL.md" "$tmp"/.agents/rules/*.md | shasum)
    [ "$snap1" = "$snap2" ]
    rm -rf "$tmp"
}

# ── doctor ─────────────────────────────────────────────────────────────────

@test "antigravity: doctor flags rules without trigger and oversized rule files" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.agents/rules" "$tmp/home/.gemini"
    printf '# no frontmatter\n' > "$tmp/.agents/rules/ai-toolkit-old.md"
    python3 -c 'print("x" * 24001)' > "$tmp/AGENTS.md"
    run python3 - "$TOOLKIT_DIR/scripts" "$tmp" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from generate_antigravity import diagnose_rules
root = Path(sys.argv[2])
problems = diagnose_rules(root, root / "home")
assert any("ai-toolkit-old.md" in p and "trigger" in p for p in problems), problems
assert any("AGENTS.md" in p and "24000" in p for p in problems), problems
PY
    [ "$status" -eq 0 ] || { echo "$output"; rm -rf "$tmp"; return 1; }
    rm -rf "$tmp"
}
