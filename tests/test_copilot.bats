#!/usr/bin/env bats
# Dedicated tests for scripts/generate_copilot.py.
#
# Covers the four Copilot surfaces the generator now emits:
#   1. .github/copilot-instructions.md (stdout, legacy)
#   2. .github/instructions/*.instructions.md (path-specific)
#   3. .github/prompts/*.prompt.md (prompt files / slash commands)
#   4. .github/agents/*.agent.md (native Copilot custom agents)

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export COPILOT_TMP; COPILOT_TMP="$(mktemp -d)"
    export COPILOT_STDOUT="$COPILOT_TMP/copilot-instructions.md"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" > "$COPILOT_STDOUT" 2>/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$COPILOT_TMP" >/dev/null 2>&1
}

teardown_file() {
    rm -rf "$COPILOT_TMP"
}

# ── Legacy stdout mode ─────────────────────────────────────────────────────

@test "generate_copilot.py stdout mode produces copilot-instructions markdown" {
    [ -s "$COPILOT_STDOUT" ]
    grep -q '^# GitHub Copilot Instructions' "$COPILOT_STDOUT"
}

@test "generate_copilot.py stdout output references agents and skills" {
    grep -qi 'agent' "$COPILOT_STDOUT"
    grep -qi 'skill' "$COPILOT_STDOUT"
}

@test "generate_copilot.py stdout wraps output in toolkit markers" {
    grep -q 'TOOLKIT:ai-toolkit START' "$COPILOT_STDOUT"
    grep -q 'TOOLKIT:ai-toolkit END' "$COPILOT_STDOUT"
}

@test "generate_copilot.py stdout propagates the source constitution" {
    grep -q 'Article I: Safety First' "$COPILOT_STDOUT"
    grep -q 'Section 4: Autonomous Loop Limits' "$COPILOT_STDOUT"
    grep -q 'Section 5: Proactive Context Checkpointing' "$COPILOT_STDOUT"
    grep -q 'Article VII: Epistemic & Injection Integrity' "$COPILOT_STDOUT"
}

# ── Path-specific .instructions.md files ───────────────────────────────────

@test "generate_copilot.py creates .github/instructions/ directory" {
    [ -d "$COPILOT_TMP/.github/instructions" ]
}

@test "generate_copilot.py emits at least 5 instruction files" {
    count=$(ls "$COPILOT_TMP/.github/instructions"/ai-toolkit-*.instructions.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 5 ]
}

@test "generate_copilot.py instruction files have applyTo frontmatter" {
    for f in "$COPILOT_TMP/.github/instructions"/ai-toolkit-*.instructions.md; do
        head -1 "$f" | grep -q '^---' || { echo "No frontmatter: $f"; return 1; }
        grep -q '^applyTo: ' "$f" || { echo "No applyTo: $f"; return 1; }
    done
}

@test "generate_copilot.py scopes testing rule to test-file globs" {
    f="$COPILOT_TMP/.github/instructions/ai-toolkit-testing.instructions.md"
    [ -f "$f" ]
    grep -q 'applyTo: ".*test' "$f"
    grep -q '# Testing' "$f"
}

@test "generate_copilot.py applies security rule to all files (applyTo **)" {
    f="$COPILOT_TMP/.github/instructions/ai-toolkit-security.instructions.md"
    [ -f "$f" ]
    grep -q 'applyTo: "\*\*"' "$f"
}

@test "generate_copilot.py quality instructions use the source constitution" {
    f="$COPILOT_TMP/.github/instructions/ai-toolkit-quality-standards.instructions.md"
    grep -q 'Section 4: Autonomous Loop Limits' "$f"
    grep -q 'Section 5: Proactive Context Checkpointing' "$f"
    grep -q 'Article VII: Epistemic & Injection Integrity' "$f"
}

# ── Native custom agents ────────────────────────────────────────────────────

@test "generate_copilot.py emits one native custom agent per source agent" {
    [ -d "$COPILOT_TMP/.github/agents" ]
    expected=$(find "$TOOLKIT_DIR/app/agents" -maxdepth 1 -name '*.md' -type f | wc -l | xargs)
    actual=$(find "$COPILOT_TMP/.github/agents" -maxdepth 1 -name 'ai-toolkit-*.agent.md' -type f | wc -l | xargs)
    [ "$actual" -eq "$expected" ]
}

@test "generate_copilot.py custom agents use native schema and portable bodies" {
    run python3 - "$COPILOT_TMP/.github/agents" <<'PY'
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
forbidden = re.compile(
    r"\$ARGUMENTS|CLAUDE_SKILL_DIR|CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS|"
    r"\bAgent\s*\(|\bTask(?:Create|List|Update|Get|Output|Stop)\b|"
    r"\b(?:TeamCreate|TeamDelete|SendMessage)\b|"
    r"\b(?:spawn_agent|send_input|wait_agent|close_agent|update_plan|fork_context)\b|"
    r"\bview_skill\s*\(|\b(?:subagent_type|agent_type)\s*="
)
files = list(root.glob("ai-toolkit-*.agent.md"))
assert files
for path in files:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    assert len(parts) == 3, path
    frontmatter, body = parts[1:]
    keys = {
        line.split(":", 1)[0]
        for line in frontmatter.splitlines()
        if ":" in line
    }
    assert keys == {"name", "description"}, (path, keys)
    assert "<!-- ai-toolkit-managed: github-copilot -->" in body, path
    assert len(body.encode("utf-8")) <= 30_000, path
    assert not forbidden.search(body), path
PY
    [ "$status" -eq 0 ]
}

# ── Prompt files (slash commands for VS Code Copilot) ──────────────────────

@test "generate_copilot.py creates .github/prompts/ directory" {
    [ -d "$COPILOT_TMP/.github/prompts" ]
}

@test "generate_copilot.py emits at least 10 prompt files" {
    count=$(ls "$COPILOT_TMP/.github/prompts"/ai-toolkit-*.prompt.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 10 ]
}

@test "generate_copilot.py prompt files have description frontmatter" {
    for f in "$COPILOT_TMP/.github/prompts"/ai-toolkit-*.prompt.md; do
        head -1 "$f" | grep -q '^---' || { echo "No frontmatter: $f"; return 1; }
        grep -q '^description: ' "$f" || { echo "No description: $f"; return 1; }
    done
}

@test "generate_copilot.py emits a debug prompt file" {
    [ -f "$COPILOT_TMP/.github/prompts/ai-toolkit-debug.prompt.md" ]
}

@test "generate_copilot.py excludes knowledge-only skills from prompts" {
    # Skills with user-invocable: false (e.g. rag-patterns) must NOT appear
    # as slash commands — they are knowledge-only.
    [ ! -f "$COPILOT_TMP/.github/prompts/ai-toolkit-rag-patterns.prompt.md" ]
}

@test "generate_copilot.py prompt files use supported metadata and portable bodies" {
    run python3 - "$COPILOT_TMP/.github/prompts" <<'PY'
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
forbidden = re.compile(
    r"\$ARGUMENTS|CLAUDE_SKILL_DIR|CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS|"
    r"\bAgent\s*\(|\bTask(?:Create|List|Update|Get|Output|Stop)\b|"
    r"\b(?:TeamCreate|TeamDelete|SendMessage)\b|"
    r"\b(?:spawn_agent|send_input|wait_agent|close_agent|update_plan|fork_context)\b|"
    r"\bview_skill\s*\(|\b(?:subagent_type|agent_type)\s*=|!`"
)
files = list(root.glob("ai-toolkit-*.prompt.md"))
assert files
for path in files:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    assert len(parts) == 3, path
    frontmatter, body = parts[1:]
    keys = {
        line.split(":", 1)[0]
        for line in frontmatter.splitlines()
        if ":" in line
    }
    assert keys == {"description"}, (path, keys)
    assert "<!-- ai-toolkit-managed: github-copilot -->" in body, path
    assert not forbidden.search(body), path
PY
    [ "$status" -eq 0 ]
}

@test "generate_copilot.py preserves standalone markdown rules in source bodies" {
    run python3 - "$TOOLKIT_DIR" "$COPILOT_TMP/body-fixture.md" <<'PY'
import importlib.util
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
fixture = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
spec = importlib.util.spec_from_file_location(
    "generate_copilot", toolkit / "scripts" / "generate_copilot.py"
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

fixture.write_text(
    "---\nname: fixture\ndescription: fixture\n---\n"
    "first section\n\n---\n\nsecond section\n",
    encoding="utf-8",
)
assert module._read_markdown_body(fixture) == (
    "first section\n\n---\n\nsecond section"
)
PY
    [ "$status" -eq 0 ]
}

# ── Portable skills ─────────────────────────────────────────────────────────

@test "generate_copilot.py emits one portable native skill per source skill" {
    expected=$(find "$TOOLKIT_DIR/app/skills" -mindepth 2 -maxdepth 2 \
        -name SKILL.md -type f ! -path '*/_lib/*' | wc -l | xargs)
    actual=$(find "$COPILOT_TMP/.github/skills" -mindepth 2 -maxdepth 2 \
        -name SKILL.md -type f | wc -l | xargs)
    [ "$actual" -eq "$expected" ]

    run python3 - "$COPILOT_TMP/.github/skills" <<'PY'
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
forbidden = re.compile(
    r"\$ARGUMENTS|CLAUDE_SKILL_DIR|CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS|"
    r"\bAgent\s*\(|\bTask(?:Create|List|Update|Get|Output|Stop)\b|"
    r"\b(?:TeamCreate|TeamDelete|SendMessage)\b|"
    r"\b(?:spawn_agent|send_input|wait_agent|close_agent|update_plan|fork_context)\b|"
    r"\bview_skill\s*\(|\b(?:subagent_type|agent_type)\s*="
)
files = list(root.glob("ai-toolkit-*/SKILL.md"))
assert files
for path in files:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    assert len(parts) == 3, path
    keys = {
        line.split(":", 1)[0]
        for line in parts[1].splitlines()
        if ":" in line
    }
    assert keys == {"name", "description"}, (path, keys)
    assert "<!-- ai-toolkit-managed: github-copilot -->" in parts[2], path
    assert "GitHub Copilot skill execution notes" in parts[2], path
    assert not forbidden.search(parts[2]), path
assert not list(root.rglob("__pycache__"))
assert not list(root.rglob("*.pyc"))
assert not [path for path in root.rglob("*") if path.is_symlink()]
PY
    [ "$status" -eq 0 ]
}

@test "generate_copilot.py materializes skill assets and vendors shared helpers" {
    [ -f "$COPILOT_TMP/.github/skills/ai-toolkit-review/scripts/diff-analyzer.py" ]
    [ -f "$COPILOT_TMP/.github/skills/ai-toolkit-clean-code/reference/python.md" ]
    for skill in build ci lint test; do
        root="$COPILOT_TMP/.github/skills/ai-toolkit-$skill/scripts"
        [ -f "$root/detect_utils.py" ]
        grep -Rqs '^from detect_utils import' "$root"
        ! grep -Rqs '^from _lib\.detect_utils import' "$root"
    done
}

@test "generate_copilot.py keeps user skills and user-added managed-skill assets" {
    local tmp; tmp="$(mktemp -d)"
    mkdir -p "$tmp/.github/skills/custom-review"
    cat > "$tmp/.github/skills/custom-review/SKILL.md" <<'MD'
---
name: review
description: User review skill.
---
Keep this user skill.
MD
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1
    [ ! -e "$tmp/.github/skills/ai-toolkit-review" ]
    grep -q '^Keep this user skill\.$' "$tmp/.github/skills/custom-review/SKILL.md"

    printf '%s\n' 'user-added fixture' > \
        "$tmp/.github/skills/ai-toolkit-build/user-fixture.txt"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1
    grep -q '^user-added fixture$' \
        "$tmp/.github/skills/ai-toolkit-build/user-fixture.txt"
    rm -rf "$tmp"
}

@test "generate_copilot.py dynamic context conversion preserves normal bang code spans" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
import generate_copilot as module

source = "- Dynamic: !`git status`\n- Ruby: `save!`, `sort!`, `strip!`.\n"
rendered = module._replace_dynamic_context(source)
assert "Dynamic: `git status`" in rendered
assert "`save!`, `sort!`, `strip!`" in rendered
PY
    [ "$status" -eq 0 ]
}

# ── Language-specific instructions ─────────────────────────────────────────

@test "generate_copilot.py honors language_modules via generate()" {
    local tmp; tmp="$(mktemp -d)"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_copilot import generate
generate(Path('$tmp'), language_modules=['rules-python'], emit_prompts=False)
" >/dev/null 2>&1
    [ -f "$tmp/.github/instructions/ai-toolkit-lang-common.instructions.md" ]
    [ -f "$tmp/.github/instructions/ai-toolkit-lang-python.instructions.md" ]
    grep -q '\*\*/\*.py' "$tmp/.github/instructions/ai-toolkit-lang-python.instructions.md"
    rm -rf "$tmp"
}

# ── Registered custom rules ────────────────────────────────────────────────

@test "generate_copilot.py wraps registered custom rules as always-on instructions" {
    local tmp; tmp="$(mktemp -d)"
    local rules_tmp; rules_tmp="$(mktemp -d)"
    echo "# Team Standards" > "$rules_tmp/team-standards.md"
    python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_copilot import generate
generate(Path('$tmp'), rules_dir=Path('$rules_tmp'), emit_prompts=False)
" >/dev/null 2>&1
    [ -f "$tmp/.github/instructions/ai-toolkit-custom-team-standards.instructions.md" ]
    grep -q 'applyTo: "\*\*"' "$tmp/.github/instructions/ai-toolkit-custom-team-standards.instructions.md"
    grep -q 'Team Standards' "$tmp/.github/instructions/ai-toolkit-custom-team-standards.instructions.md"
    rm -rf "$tmp" "$rules_tmp"
}

# ── Idempotency and cleanup ────────────────────────────────────────────────

@test "generate_copilot.py migrates exact legacy instructions and prompts" {
    local tmp; tmp="$(mktemp -d)"
    run python3 - "$TOOLKIT_DIR" "$tmp" <<'PY'
import importlib.util
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
spec = importlib.util.spec_from_file_location(
    "generate_copilot", toolkit / "scripts" / "generate_copilot.py"
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

instructions = target / ".github" / "instructions"
prompts = target / ".github" / "prompts"
instructions.mkdir(parents=True)
prompts.mkdir(parents=True)

security = module.rule_security()
old_instruction = (
    '---\napplyTo: "**"\n'
    'description: Security rules — OWASP, secrets, input validation\n'
    f'---\n\n{security.rstrip()}\n'
)
instruction_path = instructions / "ai-toolkit-security.instructions.md"
instruction_path.write_text(old_instruction, encoding="utf-8")

skill_file = toolkit / "app" / "skills" / "fix" / "SKILL.md"
description = module.frontmatter_field(skill_file, "description")
lines = []
fence_count = 0
for line in skill_file.read_text(encoding="utf-8").splitlines():
    if line == "---":
        fence_count += 1
        continue
    if fence_count >= 2:
        lines.append(line)
while lines and not lines[-1]:
    lines.pop()
old_body = "\n".join(lines)
old_prompt = f"---\ndescription: {description}\n---\n\n{old_body}\n"
prompt_path = prompts / "ai-toolkit-fix.prompt.md"
prompt_path.write_text(old_prompt, encoding="utf-8")

module.generate(target, emit_agents=False)
instruction = instruction_path.read_text(encoding="utf-8")
prompt = prompt_path.read_text(encoding="utf-8")
assert module.MANAGED_MARKER in instruction
assert module.MANAGED_MARKER in prompt
assert instruction != old_instruction
assert prompt != old_prompt
assert prompt.count("\n---\n") >= 2
assert "$ARGUMENTS" not in prompt
PY
    [ "$status" -eq 0 ]
    rm -rf "$tmp"
}

@test "generate_copilot.py is idempotent across reruns" {
    local tmp; tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1
    find "$tmp/.github" -type f -exec shasum {} \; | sort > "$tmp/first.sha"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1
    find "$tmp/.github" -type f -exec shasum {} \; | sort > "$tmp/second.sha"
    cmp "$tmp/first.sha" "$tmp/second.sha"
    rm -rf "$tmp"
}

@test "generate_copilot.py cleans only stale managed files" {
    local tmp; tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1

    for path in \
        "$tmp/.github/instructions/ai-toolkit-obsolete.instructions.md" \
        "$tmp/.github/prompts/ai-toolkit-obsolete.prompt.md" \
        "$tmp/.github/agents/ai-toolkit-obsolete.agent.md"; do
        printf '%s\n' '<!-- ai-toolkit-managed: github-copilot -->' stale > "$path"
    done
    printf '%s\n' user > "$tmp/.github/instructions/ai-toolkit-user.instructions.md"
    printf '%s\n' user > "$tmp/.github/prompts/ai-toolkit-user.prompt.md"
    printf '%s\n' user > "$tmp/.github/agents/ai-toolkit-user.agent.md"

    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1
    [ ! -f "$tmp/.github/instructions/ai-toolkit-obsolete.instructions.md" ]
    [ ! -f "$tmp/.github/prompts/ai-toolkit-obsolete.prompt.md" ]
    [ ! -f "$tmp/.github/agents/ai-toolkit-obsolete.agent.md" ]
    grep -q '^user$' "$tmp/.github/instructions/ai-toolkit-user.instructions.md"
    grep -q '^user$' "$tmp/.github/prompts/ai-toolkit-user.prompt.md"
    grep -q '^user$' "$tmp/.github/agents/ai-toolkit-user.agent.md"
    rm -rf "$tmp"
}

@test "generate_copilot.py preserves path, logical-name, and invalid user collisions" {
    local tmp; tmp="$(mktemp -d)"
    mkdir -p "$tmp/.github/instructions" "$tmp/.github/prompts" "$tmp/.github/agents"
    printf '%s\n' user-instruction > \
        "$tmp/.github/instructions/ai-toolkit-security.instructions.md"
    printf '%s\n' user-prompt > \
        "$tmp/.github/prompts/ai-toolkit-debug.prompt.md"
    printf '%s\n' \
        '---' \
        'name: user-debugger' \
        'description: User path collision.' \
        '---' \
        'Keep this agent.' > \
        "$tmp/.github/agents/ai-toolkit-debugger.agent.md"
    printf '%s\n' \
        '---' \
        'name: backend-specialist' \
        'description: User logical-name collision.' \
        '---' \
        'Keep this logical agent.' > \
        "$tmp/.github/agents/custom-backend.agent.md"
    printf '%s\n' '---' 'description: Invalid agent without name.' > \
        "$tmp/.github/agents/invalid.agent.md"

    run python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Warning: preserving user Copilot file"* ]]
    grep -q '^user-instruction$' \
        "$tmp/.github/instructions/ai-toolkit-security.instructions.md"
    grep -q '^user-prompt$' "$tmp/.github/prompts/ai-toolkit-debug.prompt.md"
    grep -q '^Keep this agent.$' \
        "$tmp/.github/agents/ai-toolkit-debugger.agent.md"
    grep -q '^Keep this logical agent.$' \
        "$tmp/.github/agents/custom-backend.agent.md"
    [ ! -e "$tmp/.github/agents/ai-toolkit-backend-specialist.agent.md" ]
    grep -q '^description: Invalid agent without name.$' \
        "$tmp/.github/agents/invalid.agent.md"
    rm -rf "$tmp"
}

@test "generate_copilot.py rejects symlinked customization roots" {
    local tmp; tmp="$(mktemp -d)"
    local external; external="$(mktemp -d)"
    printf '%s\n' sentinel > "$external/sentinel.txt"
    shasum "$external/sentinel.txt" > "$tmp/external.before"
    ln -s "$external" "$tmp/.github"

    run python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp"
    [ "$status" -ne 0 ]
    shasum "$external/sentinel.txt" > "$tmp/external.after"
    cmp "$tmp/external.before" "$tmp/external.after"
    [ "$(find "$external" -type f | wc -l | xargs)" -eq 1 ]

    rm "$tmp/.github"
    mkdir -p "$tmp/.github"
    ln -s "$external" "$tmp/.github/agents"
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_copilot import generate
generate(Path('$tmp'), emit_instructions=False, emit_prompts=False)
"
    [ "$status" -ne 0 ]
    [ "$(find "$external" -type f | wc -l | xargs)" -eq 1 ]
    rm -rf "$tmp" "$external"
}

@test "generate_copilot.py preserves destination and stale symlinks" {
    local tmp; tmp="$(mktemp -d)"
    local external; external="$(mktemp -d)"
    local agents="$tmp/.github/agents"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1
    printf '%s\n' external-managed-looking-sentinel > "$external/sentinel.agent.md"
    shasum "$external/sentinel.agent.md" > "$tmp/external.before"

    rm "$agents/ai-toolkit-debugger.agent.md"
    ln -s "$external/missing.agent.md" "$agents/ai-toolkit-debugger.agent.md"
    ln -s "$external/sentinel.agent.md" "$agents/ai-toolkit-retired.agent.md"
    run python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp"
    [ "$status" -eq 0 ]
    [ -L "$agents/ai-toolkit-debugger.agent.md" ]
    [ -L "$agents/ai-toolkit-retired.agent.md" ]
    [ ! -e "$external/missing.agent.md" ]
    shasum "$external/sentinel.agent.md" > "$tmp/external.after"
    cmp "$tmp/external.before" "$tmp/external.after"
    rm -rf "$tmp" "$external"
}

@test "generate_copilot.py staging failure preserves prior files and skips cleanup" {
    local tmp; tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1
    printf '%s\n' '<!-- ai-toolkit-managed: github-copilot -->' stale > \
        "$tmp/.github/instructions/ai-toolkit-retired.instructions.md"

    run python3 - "$TOOLKIT_DIR" "$tmp" <<'PY'
import importlib.util
import os
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
spec = importlib.util.spec_from_file_location(
    "generate_copilot", toolkit / "scripts" / "generate_copilot.py"
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

root = target / ".github" / "instructions"
before = {path.name: path.read_bytes() for path in root.glob("*") if path.is_file()}
real_fsync = os.fsync
calls = 0

def fail_second_fsync(fd):
    global calls
    calls += 1
    if calls == 2:
        raise OSError("injected Copilot staging failure")
    return real_fsync(fd)

try:
    with mock.patch("os.fsync", side_effect=fail_second_fsync):
        module.generate(target, emit_agents=False, emit_prompts=False)
except OSError as error:
    assert "injected Copilot staging failure" in str(error)
else:
    raise AssertionError("expected injected staging failure")

after = {path.name: path.read_bytes() for path in root.glob("*") if path.is_file()}
assert after == before
assert not list(root.glob(".*.tmp"))
PY
    [ "$status" -eq 0 ]
    rm -rf "$tmp"
}

@test "generate_copilot.py global layout emits instructions, agents, and skills" {
    local tmp; tmp="$(mktemp -d)"
    local home="$tmp/copilot-home"
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from pathlib import Path
from generate_copilot import generate
generate(Path('$tmp/project'), config_root=Path('$home'), emit_prompts=False)
"
    [ "$status" -eq 0 ]
    [ -f "$home/instructions/ai-toolkit-security.instructions.md" ]
    [ -f "$home/agents/ai-toolkit-debugger.agent.md" ]
    [ -f "$home/skills/ai-toolkit-debug/SKILL.md" ]
    [ -f "$home/skills/ai-toolkit-debug/scripts/error-parser.py" ]
    [ ! -e "$tmp/project/.github" ]
    rm -rf "$tmp"
}

@test "generate_copilot.py does not guess hooks and preserves user hooks" {
    local tmp; tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1
    [ ! -e "$tmp/.github/hooks" ]
    mkdir -p "$tmp/.github/hooks"
    printf '%s\n' '{"version":1,"hooks":{}}' > "$tmp/.github/hooks/user.json"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$tmp" >/dev/null 2>&1
    grep -q '^{"version":1,"hooks":{}}$' "$tmp/.github/hooks/user.json"
    rm -rf "$tmp"
}
