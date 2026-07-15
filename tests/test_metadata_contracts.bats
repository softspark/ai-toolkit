#!/usr/bin/env bats
# Workstream 1: Metadata contracts
# Validates that public claims in README and ARCHITECTURE match actual repo state.
# Run with: bats tests/test_metadata_contracts.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

# ── Helpers ─────────────────────────────────────────────────────────────────

actual_agent_count() {
    find "$TOOLKIT_DIR/app/agents" -maxdepth 1 -name '*.md' | wc -l | xargs
}

actual_skill_count() {
    find "$TOOLKIT_DIR/app/skills" -maxdepth 1 -mindepth 1 -type d -not -name '_*' | wc -l | xargs
}

actual_task_skill_count() {
    grep -l '^disable-model-invocation: true$' "$TOOLKIT_DIR"/app/skills/*/SKILL.md | wc -l | xargs
}

actual_hybrid_skill_count() {
    local total task knowledge
    total=$(actual_skill_count)
    task=$(actual_task_skill_count)
    knowledge=$(actual_knowledge_skill_count)
    echo $((total - task - knowledge))
}

actual_knowledge_skill_count() {
    grep -l '^user-invocable: false$' "$TOOLKIT_DIR"/app/skills/*/SKILL.md | wc -l | xargs
}

actual_test_count() {
    grep -c '^@test ' "$TOOLKIT_DIR"/tests/*.bats | awk -F: '{sum+=$2} END {print sum}'
}

# ── Agent count ──────────────────────────────────────────────────────────────

@test "README agent badge matches actual agent count" {
    actual=$(actual_agent_count)
    readme_count=$(grep -oE 'agents-[0-9]+' "$TOOLKIT_DIR/README.md" | head -1 | grep -oE '[0-9]+')
    [ "$readme_count" = "$actual" ]
}

@test "README skill badge matches actual skill count" {
    actual=$(actual_skill_count)
    readme_count=$(grep -oE 'skills-[0-9]+' "$TOOLKIT_DIR/README.md" | head -1 | grep -oE '[0-9]+')
    [ "$readme_count" = "$actual" ]
}

@test "README test badge matches actual test count" {
    actual=$(actual_test_count)
    readme_count=$(grep -oE 'tests-[0-9]+' "$TOOLKIT_DIR/README.md" | head -1 | grep -oE '[0-9]+')
    [ "$readme_count" = "$actual" ]
}

@test "README What You Get table agent count matches actual" {
    actual=$(actual_agent_count)
    # Line like: | `agents/` | 44 | Specialized agents ...
    readme_count=$(grep '`agents/`' "$TOOLKIT_DIR/README.md" | grep -oE '\| [0-9]+ \|' | grep -oE '[0-9]+')
    [ "$readme_count" = "$actual" ]
}

@test "README What You Get table skill count matches actual" {
    actual=$(actual_skill_count)
    # Sum of task + hybrid + knowledge = total skills
    # Table rows: | `skills/` (task) | 21 | ... |
    task=$(grep '`skills/` (task)' "$TOOLKIT_DIR/README.md" | grep -oE '\| [0-9]+ \|' | grep -oE '[0-9]+' | head -1 || echo "0")
    hybrid=$(grep '`skills/` (hybrid)' "$TOOLKIT_DIR/README.md" | grep -oE '\| [0-9]+ \|' | grep -oE '[0-9]+' | head -1 || echo "0")
    knowledge=$(grep '`skills/` (knowledge)' "$TOOLKIT_DIR/README.md" | grep -oE '\| [0-9]+ \|' | grep -oE '[0-9]+' | head -1 || echo "0")
    total=$((task + hybrid + knowledge))
    [ "$total" = "$actual" ]
}

@test "README What You Get table task skill count matches actual" {
    actual=$(actual_task_skill_count)
    readme_count=$(grep '`skills/` (task)' "$TOOLKIT_DIR/README.md" | grep -oE '\| [0-9]+ \|' | grep -oE '[0-9]+' | head -1)
    [ "$readme_count" = "$actual" ]
}

@test "README What You Get table hybrid skill count matches actual" {
    actual=$(actual_hybrid_skill_count)
    readme_count=$(grep '`skills/` (hybrid)' "$TOOLKIT_DIR/README.md" | grep -oE '\| [0-9]+ \|' | grep -oE '[0-9]+' | head -1)
    [ "$readme_count" = "$actual" ]
}

@test "README What You Get table knowledge skill count matches actual" {
    actual=$(actual_knowledge_skill_count)
    readme_count=$(grep '`skills/` (knowledge)' "$TOOLKIT_DIR/README.md" | grep -oE '\| [0-9]+ \|' | grep -oE '[0-9]+' | head -1)
    [ "$readme_count" = "$actual" ]
}

@test "README architecture tree test count is not stale when present" {
    actual=$(actual_test_count)
    count=$(grep -oE 'Bats test suite \([0-9]+ tests\)' "$TOOLKIT_DIR/README.md" | grep -oE '[0-9]+' | head -1 || true)
    [ -z "$count" ] || [ "$count" = "$actual" ]
}

@test "ARCHITECTURE.md does not contain hardcoded agent count in headings" {
    # Secondary docs must not contain hardcoded counts (only README.md, manifest.json, package.json may)
    ! grep -qE '## Agents \([0-9]+\)' "$TOOLKIT_DIR/app/ARCHITECTURE.md"
}

@test "ARCHITECTURE.md does not contain hardcoded skill count in headings" {
    # Secondary docs must not contain hardcoded counts
    ! grep -qE '## Skills \([0-9]+\)' "$TOOLKIT_DIR/app/ARCHITECTURE.md"
}

@test "package.json version is present and non-empty" {
    version=$(python3 -c "import sys,json; d=json.load(open('$TOOLKIT_DIR/package.json')); print(d['version'])")
    [ -n "$version" ]
}

@test "package.json version follows semver (X.Y.Z)" {
    version=$(python3 -c "import sys,json; d=json.load(open('$TOOLKIT_DIR/package.json')); print(d['version'])")
    echo "$version" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'
}

@test "package.json excludes local Claude session artifacts from npm pack" {
    python3 - "$TOOLKIT_DIR/package.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    files = json.load(fh).get("files", [])

assert "!app/**/.claude" in files
assert "!app/**/.claude/**" in files
PY
}

@test "npm package excludes KB runtime logs while preserving markdown" {
    local fixture pack_status audit_status audit_output
    fixture="$(mktemp -d)"

    cp "$TOOLKIT_DIR/package.json" "$fixture/package.json"
    mkdir -p "$fixture/kb/reference"
    printf '# Reference\n' > "$fixture/kb/reference/guide.md"
    printf 'runtime entry\n' > "$fixture/kb/runtime.log"

    run env npm_config_cache="$fixture/.npm-cache" \
        npm pack --dry-run --json --pack-destination "$fixture" "$fixture"
    pack_status="$status"
    printf '%s\n' "$output" > "$fixture/pack.json"

    run python3 - "$fixture/pack.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    package = json.load(fh)[0]

paths = {entry["path"] for entry in package["files"]}
assert "kb/reference/guide.md" in paths, sorted(paths)
assert "kb/runtime.log" not in paths, sorted(paths)
PY
    audit_status="$status"
    audit_output="$output"
    rm -rf "$fixture"

    [ "$pack_status" -eq 0 ]
    [ "$audit_status" -eq 0 ] || {
        echo "$audit_output"
        return "$audit_status"
    }
}

@test "npm package KB files match the tracked release set" {
    local fixture pack_status audit_status audit_output
    fixture="$(mktemp -d)"

    run env npm_config_cache="$fixture/.npm-cache" \
        npm pack --dry-run --json --pack-destination "$fixture" "$TOOLKIT_DIR"
    pack_status="$status"
    printf '%s\n' "$output" > "$fixture/pack.json"

    run python3 - "$TOOLKIT_DIR" "$fixture/pack.json" <<'PY'
import json
import subprocess
import sys

toolkit_dir, pack_path = sys.argv[1:]
tracked = {
    path
    for path in subprocess.check_output(
        ["git", "-C", toolkit_dir, "ls-files", "-z", "kb"]
    ).decode().split("\0")
    if path
}
with open(pack_path, encoding="utf-8") as fh:
    package = json.load(fh)[0]
packed = {
    entry["path"]
    for entry in package["files"]
    if entry["path"].startswith("kb/")
}

missing = sorted(tracked - packed)
extra = sorted(packed - tracked)
assert not missing and not extra, {"missing": missing, "extra": extra}
PY
    audit_status="$status"
    audit_output="$output"
    rm -rf "$fixture"

    [ "$pack_status" -eq 0 ]
    [ "$audit_status" -eq 0 ] || {
        echo "$audit_output"
        return "$audit_status"
    }
}

@test "CHANGELOG.md references current package.json version" {
    version=$(python3 -c "import sys,json; d=json.load(open('$TOOLKIT_DIR/package.json')); print(d['version'])")
    grep -q "$version" "$TOOLKIT_DIR/CHANGELOG.md"
}

@test "publish workflow gates and generates the package before npm publish" {
    python3 - "$TOOLKIT_DIR/.github/workflows/publish.yml" \
        "$TOOLKIT_DIR/.github/workflows/ci.yml" <<'PY'
import sys
from pathlib import Path

workflow = Path(sys.argv[1]).read_text(encoding="utf-8")
ci_workflow = Path(sys.argv[2]).read_text(encoding="utf-8")
required_in_order = [
    "npm ci",
    "npm run generate:all",
    "python3 scripts/validate.py --strict",
    "python3 scripts/audit_skills.py --ci",
    "python3 scripts/audit_skills.py --sarif > audit.sarif",
    "shellcheck --severity=warning app/hooks/*.sh",
    "npm test",
    "npm publish --access public --ignore-scripts --provenance",
]
positions = [workflow.index(command) for command in required_in_order]
assert positions == sorted(positions), positions
assert "github/codeql-action/upload-sarif@" in workflow
assert "sarif_file: audit.sarif" in workflow
assert "id-token: write" in workflow
assert "fetch-depth: 0" in workflow
assert "fetch-depth: 0" in ci_workflow
PY
}

@test "architecture-overview.md does not contain hardcoded agent count in description" {
    # Secondary docs must not contain hardcoded counts like "44 specialized agents"
    ! grep -qE '[0-9]+ specialized agents' "$TOOLKIT_DIR/kb/reference/architecture-overview.md"
}

@test "architecture-overview.md does not contain hardcoded skill count in description" {
    # Secondary docs must not contain hardcoded counts like "90 skills"
    ! grep -qE '[0-9]+ skills \(slash' "$TOOLKIT_DIR/kb/reference/architecture-overview.md"
}

@test "skills-catalog.md does not contain hardcoded total skill count in heading" {
    # Secondary docs must not contain hardcoded counts
    ! grep -qE 'Skills Catalog \([0-9]+ skills\)' "$TOOLKIT_DIR/kb/reference/skills-catalog.md"
}

@test "skills-catalog.md task skill section exists" {
    grep -q '## Task Skills' "$TOOLKIT_DIR/kb/reference/skills-catalog.md"
}

@test "skills-catalog.md hybrid skill section exists" {
    grep -q '## Hybrid Skills' "$TOOLKIT_DIR/kb/reference/skills-catalog.md"
}

@test "architecture-overview.md task skill count matches actual" {
    actual=$(actual_task_skill_count)
    kb_count=$(grep '^| Task |' "$TOOLKIT_DIR/kb/reference/architecture-overview.md" | grep -oE '[0-9]+' | tail -1 || true)
    [ -n "$kb_count" ]
    [ "$kb_count" = "$actual" ]
}

@test "architecture-overview.md hybrid skill count matches actual" {
    actual=$(actual_hybrid_skill_count)
    kb_count=$(grep '^| Hybrid |' "$TOOLKIT_DIR/kb/reference/architecture-overview.md" | grep -oE '[0-9]+' | tail -1 || true)
    [ -n "$kb_count" ]
    [ "$kb_count" = "$actual" ]
}

@test "architecture-overview.md knowledge skill count matches actual" {
    actual=$(actual_knowledge_skill_count)
    kb_count=$(grep '^| Knowledge |' "$TOOLKIT_DIR/kb/reference/architecture-overview.md" | grep -oE '[0-9]+' | tail -1 || true)
    [ -n "$kb_count" ]
    [ "$kb_count" = "$actual" ]
}

@test "architecture-overview.md test count is not stale when present" {
    actual=$(actual_test_count)
    kb_count=$(grep -oE 'Bats test suite \([0-9]+ tests\)' "$TOOLKIT_DIR/kb/reference/architecture-overview.md" | grep -oE '[0-9]+' | head -1 || true)
    [ -z "$kb_count" ] || [ "$kb_count" = "$actual" ]
}

@test "all agent files have unique names" {
    total=$(actual_agent_count)
    unique=$(find "$TOOLKIT_DIR/app/agents" -maxdepth 1 -name '*.md' -exec basename {} .md \; | sort -u | wc -l | xargs)
    [ "$unique" = "$total" ]
}

@test "all skill directories have unique names" {
    total=$(actual_skill_count)
    unique=$(find "$TOOLKIT_DIR/app/skills" -maxdepth 1 -mindepth 1 -type d -not -name '_*' -exec basename {} \; | sort -u | wc -l | xargs)
    [ "$unique" = "$total" ]
}

@test "AI_TOOLKIT_NO_CUSTOM_RULES gate keeps canonical generators free of custom rules" {
    # Regression guard for the custom-rule leak fix. The canonical generators
    # (AGENTS.md / GEMINI.md / copilot-instructions.md) must emit ONLY
    # toolkit-owned TOOLKIT markers when the gate is on — never a maintainer's
    # personal registered rules from ~/.softspark/ai-toolkit/rules/.
    #
    # Tests the gate's behavior on freshly-generated stdout, NOT the committed
    # file on disk: other test files run in parallel (`bats --jobs 4`) and can
    # transiently regenerate the shared AGENTS.md, so reading the live file here
    # would be racy. Generating into a variable is deterministic on any machine,
    # with or without registered custom rules.
    for gen in generate_agents_md.py generate_gemini.py generate_copilot.py; do
        out=$(AI_TOOLKIT_NO_CUSTOM_RULES=1 python3 "$TOOLKIT_DIR/scripts/$gen" 2>/dev/null)
        bad=$(printf '%s' "$out" | grep -oE 'TOOLKIT:[a-z0-9._-]+' | sort -u \
            | grep -vE '^TOOLKIT:(ai-toolkit|output-mode)$' || true)
        [ -z "$bad" ] || { echo "$gen leaked custom rules with gate on: $bad"; false; }
    done
}
