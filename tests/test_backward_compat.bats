#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for scripts/surface_manifest.py — the enforceable half of
# BACKWARD_COMPATIBILITY.md. Prose does not stop a rename; this does.
#
# POSIX `[ ]` and `grep -q` only. macOS ships bash 3.2, where a failing bare
# `[[ ]]` inside a bats test is silently ignored and the suite goes green.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SURFACE="$TOOLKIT_DIR/scripts/surface_manifest.py"

# A throwaway toolkit carrying one skill, one agent and a manifest.
_fixture() {
    local root
    root="$(mktemp -d)"
    mkdir -p "$root/app/skills/demo-skill" "$root/app/agents" "$root/app/hooks" \
             "$root/app/plugins/demo-pack" "$root/bin" "$root/scripts"

    cat > "$root/app/skills/demo-skill/SKILL.md" <<'EOF'
---
name: demo-skill
description: "A demo skill"
allowed-tools: Read
---
Body.
EOF
    cat > "$root/app/agents/demo-agent.md" <<'EOF'
---
name: demo-agent
description: A demo agent
tools: Read
model: sonnet
---
Body.
EOF
    printf '#!/usr/bin/env bash\necho ok\n' > "$root/app/hooks/demo-hook.sh"
    printf '{"hooks": {"SessionStart": []}}\n' > "$root/app/hooks.json"
    printf 'const COMMANDS = {\n  install: %s,\n  doctor: %s,\n};\n' "'a'" "'b'" \
        > "$root/bin/ai-toolkit.js"
    printf 'VALID_KB_CATEGORIES = frozenset({\n    "reference", "howto",\n})\n' \
        > "$root/scripts/validate.py"

    python3 "$SURFACE" --toolkit-dir "$root" --update >/dev/null
    echo "$root"
}

@test "surface manifest captures every protected category" {
    run python3 -c "
import json,sys
d = json.load(open('$TOOLKIT_DIR/app/surface.json'))
for key in ('skills','agents','skill_frontmatter_fields','agent_frontmatter_fields',
            'hook_scripts','hook_events','plugin_packs','kb_categories','cli_commands'):
    assert key in d, key
    assert d[key], f'{key} is empty'
print('OK')"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "^OK$"
}

@test "committed manifest matches the tree — nothing removed" {
    run python3 "$SURFACE" --toolkit-dir "$TOOLKIT_DIR"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "SURFACE CHECK PASSED"
}

@test "removing a skill fails the surface check" {
    local root
    root="$(_fixture)"
    rm -rf "$root/app/skills/demo-skill"
    run python3 "$SURFACE" --toolkit-dir "$root"
    rm -rf "$root"

    [ "$status" -eq 1 ]
    echo "$output" | grep -q "skills: 'demo-skill' was removed"
    echo "$output" | grep -q "SURFACE CHECK FAILED"
}

@test "removing an agent fails the surface check" {
    local root
    root="$(_fixture)"
    rm -f "$root/app/agents/demo-agent.md"
    run python3 "$SURFACE" --toolkit-dir "$root"
    rm -rf "$root"

    [ "$status" -eq 1 ]
    echo "$output" | grep -q "agents: 'demo-agent' was removed"
}

@test "removing a CLI command fails the surface check" {
    local root
    root="$(_fixture)"
    printf 'const COMMANDS = {\n  install: %s,\n};\n' "'a'" > "$root/bin/ai-toolkit.js"
    run python3 "$SURFACE" --toolkit-dir "$root"
    rm -rf "$root"

    [ "$status" -eq 1 ]
    echo "$output" | grep -q "cli_commands: 'doctor' was removed"
}

@test "dropping a KB category or a frontmatter field fails the surface check" {
    local root
    root="$(_fixture)"
    printf 'VALID_KB_CATEGORIES = frozenset({\n    "reference",\n})\n' \
        > "$root/scripts/validate.py"
    run python3 "$SURFACE" --toolkit-dir "$root"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "kb_categories: 'howto' was removed"

    printf -- '---\nname: demo-skill\ndescription: "A demo skill"\n---\nBody.\n' \
        > "$root/app/skills/demo-skill/SKILL.md"
    run python3 "$SURFACE" --toolkit-dir "$root"
    rm -rf "$root"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "skill_frontmatter_fields: 'allowed-tools' was removed"
}

@test "adding a skill passes and is reported as not yet protected" {
    local root
    root="$(_fixture)"
    mkdir -p "$root/app/skills/brand-new"
    printf -- '---\nname: brand-new\ndescription: "New"\nallowed-tools: Read\n---\nBody.\n' \
        > "$root/app/skills/brand-new/SKILL.md"
    run python3 "$SURFACE" --toolkit-dir "$root"
    rm -rf "$root"

    # Additions never fail: a surface nobody has installed has no users to break.
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "1 new entries not yet protected"
    echo "$output" | grep -q "SURFACE CHECK PASSED"
}

@test "--update rewrites the manifest and clears a previously failing removal" {
    local root
    root="$(_fixture)"
    rm -rf "$root/app/skills/demo-skill"
    run python3 "$SURFACE" --toolkit-dir "$root"
    [ "$status" -eq 1 ]

    run python3 "$SURFACE" --toolkit-dir "$root" --update
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Every line removed is a breaking change"

    run python3 "$SURFACE" --toolkit-dir "$root"
    rm -rf "$root"
    [ "$status" -eq 0 ]
}

@test "--json reports removals machine-readably" {
    local root
    root="$(_fixture)"
    rm -rf "$root/app/skills/demo-skill"
    run python3 "$SURFACE" --toolkit-dir "$root" --json
    rm -rf "$root"

    [ "$status" -eq 1 ]
    echo "$output" | python3 -c "
import json,sys
d = json.load(sys.stdin)
assert d['ok'] is False, d
assert d['removed']['skills'] == ['demo-skill'], d['removed']
print('OK')" | grep -q OK
}

@test "a missing manifest fails the check rather than passing vacuously" {
    local root
    root="$(_fixture)"
    rm -f "$root/app/surface.json"
    run python3 "$SURFACE" --toolkit-dir "$root"
    rm -rf "$root"
    [ "$status" -eq 1 ]
}

@test "README badges match ground truth" {
    run python3 "$TOOLKIT_DIR/scripts/sync_badges.py" --check --toolkit-dir "$TOOLKIT_DIR"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "OK: badges match"
}

@test "sync_badges rewrites a drifted badge and is idempotent" {
    local root
    root="$(mktemp -d)"
    mkdir -p "$root/app/agents" "$root/app/skills/one" "$root/tests"
    printf -- '---\nname: one\ndescription: d\n---\nBody.\n' > "$root/app/skills/one/SKILL.md"
    printf -- '---\nname: a\ndescription: d\n---\nBody.\n' > "$root/app/agents/a.md"
    printf '@test "x" {\n  true\n}\n' > "$root/tests/t.bats"
    printf 'skills-99 agents-99 tests-99\n' > "$root/README.md"

    run python3 "$TOOLKIT_DIR/scripts/sync_badges.py" --check --toolkit-dir "$root"
    [ "$status" -eq 1 ]

    run python3 "$TOOLKIT_DIR/scripts/sync_badges.py" --toolkit-dir "$root"
    [ "$status" -eq 0 ]
    grep -q "skills-1" "$root/README.md"
    grep -q "agents-1" "$root/README.md"
    grep -q "tests-1" "$root/README.md"

    run python3 "$TOOLKIT_DIR/scripts/sync_badges.py" --check --toolkit-dir "$root"
    rm -rf "$root"
    [ "$status" -eq 0 ]
}

@test "generate:all rewrites badges before validate reads them" {
    # prepublishOnly is `generate:all && validate.py --strict && npm test`, so the
    # badge must be corrected inside generate:all or the publish breaks on a number.
    run python3 -c "
import json
s = json.load(open('$TOOLKIT_DIR/package.json'))['scripts']
assert 'generate:badges' in s, 'missing generate:badges script'
assert s['generate:all'].rstrip().endswith('npm run generate:badges'), s['generate:all']
assert s['prepublishOnly'].startswith('npm run generate:all'), s['prepublishOnly']
print('OK')"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "^OK$"
}

@test "BACKWARD_COMPATIBILITY.md and DECISIONS.md exist and are referenced" {
    [ -f "$TOOLKIT_DIR/BACKWARD_COMPATIBILITY.md" ]
    [ -f "$TOOLKIT_DIR/DECISIONS.md" ]
    grep -q "BACKWARD_COMPATIBILITY.md" "$TOOLKIT_DIR/scripts/surface_manifest.py"
    grep -q "DECISIONS.md" "$TOOLKIT_DIR/app/surface.json"
}
