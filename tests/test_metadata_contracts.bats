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

@test "CHANGELOG.md references current package.json version" {
    version=$(python3 -c "import sys,json; d=json.load(open('$TOOLKIT_DIR/package.json')); print(d['version'])")
    grep -q "$version" "$TOOLKIT_DIR/CHANGELOG.md"
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
