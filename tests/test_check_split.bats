#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for scripts/check_split.py — the split gate that proves a
# body -> reference/ refactor lost nothing.
#
# Assertions use POSIX `[ ]` and `grep -q`, never bare `[[ ]]`: macOS ships
# bash 3.2, where a failing bare `[[ ]]` inside a bats test is silently ignored
# and the suite goes green on a broken assertion.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CHECK_SPLIT="$TOOLKIT_DIR/scripts/check_split.py"

# Builds a fixture toolkit holding one correctly split skill.
# Echoes the fixture root; the pre-split body lands in $root/demo.before.
_fixture() {
    local root skill
    root="$(mktemp -d)"
    skill="$root/app/skills/demo"
    mkdir -p "$skill/reference"

    cat > "$root/demo.before" <<'EOF'
---
name: demo
description: "Demo skill. Triggers: demo."
---

# Demo

## Steps

```bash
python3 scripts/thing.py --flag
echo "second command"
```

## Rules

- **MUST** do the thing

## Gotchas

- Trap number one
EOF

    cat > "$skill/SKILL.md" <<'EOF'
---
name: demo
description: "Demo skill. Triggers: demo."
---

# Demo

## Steps

Detail: [reference/steps.md](reference/steps.md)

## Rules

- **MUST** do the thing

## Gotchas

- Trap number one
EOF

    cat > "$skill/reference/steps.md" <<'EOF'
# Steps

```bash
python3 scripts/thing.py --flag
echo "second command"
```
EOF

    echo "$root"
}

@test "check_split passes a correct body -> reference split" {
    local root
    root="$(_fixture)"
    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root" --before "$root/demo.before"
    rm -rf "$root"

    [ "$status" -eq 0 ]
    echo "$output" | grep -q "code lines lost: 0"
    echo "$output" | grep -q "SPLIT GATE PASSED"
}

@test "gate A fails when a fenced code line is dropped" {
    local root
    root="$(_fixture)"
    # Rewrite the reference without the second command — the classic silent loss.
    printf '# Steps\n\n```bash\npython3 scripts/thing.py --flag\n```\n' \
        > "$root/app/skills/demo/reference/steps.md"
    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root" --before "$root/demo.before"
    rm -rf "$root"

    [ "$status" -eq 1 ]
    echo "$output" | grep -q "code lines lost: 1"
    echo "$output" | grep -q 'LOST: echo "second command"'
    echo "$output" | grep -q "SPLIT GATE FAILED"
}

@test "gate A reports a repeated lost line once, not once per occurrence" {
    local root
    root="$(_fixture)"
    # Same command twice in the pre-split body.
    printf -- '---\nname: demo\ndescription: "Demo skill. Triggers: demo."\n---\n\n# Demo\n\n```bash\ndropped --cmd\n```\n\n```bash\ndropped --cmd\n```\n' \
        > "$root/demo.before"
    printf '# Steps\n\nno code here\n' > "$root/app/skills/demo/reference/steps.md"
    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root" --before "$root/demo.before"
    rm -rf "$root"

    [ "$status" -eq 1 ]
    echo "$output" | grep -q "code lines lost: 1"
}

@test "gate C fails when an always-loaded section moves into reference" {
    local root skill
    root="$(_fixture)"
    skill="$root/app/skills/demo"
    printf '# Steps\n\n```bash\npython3 scripts/thing.py --flag\necho "second command"\n```\n\n## Rules\n\n- **MUST** do the thing\n' \
        > "$skill/reference/steps.md"
    printf -- '---\nname: demo\ndescription: "Demo skill. Triggers: demo."\n---\n\n# Demo\n\n## Steps\n\nDetail: [reference/steps.md](reference/steps.md)\n\n## Gotchas\n\n- Trap number one\n' \
        > "$skill/SKILL.md"
    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root" --before "$root/demo.before"
    rm -rf "$root"

    [ "$status" -eq 1 ]
    echo "$output" | grep -q "always-loaded sections left the body: Rules"
}

@test "gate C only requires sections that existed before the split" {
    local root
    root="$(_fixture)"
    # Pre-split body has no Rules/Gotchas/When NOT to Use at all.
    printf -- '---\nname: demo\ndescription: "Demo skill. Triggers: demo."\n---\n\n# Demo\n\nprose only\n' \
        > "$root/demo.before"
    printf -- '---\nname: demo\ndescription: "Demo skill. Triggers: demo."\n---\n\n# Demo\n\nprose only\n' \
        > "$root/app/skills/demo/SKILL.md"
    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root" --before "$root/demo.before"
    rm -rf "$root"

    [ "$status" -eq 0 ]
    echo "$output" | grep -q "always-loaded sections intact (none present)"
}

@test "gate D fails when the frontmatter description changes" {
    local root
    root="$(_fixture)"
    printf -- '---\nname: demo\ndescription: "Demo skill, reworded. Triggers: demo, sample."\n---\n\n# Demo\n\n## Steps\n\nDetail: [reference/steps.md](reference/steps.md)\n\n## Rules\n\n- **MUST** do the thing\n\n## Gotchas\n\n- Trap number one\n' \
        > "$root/app/skills/demo/SKILL.md"
    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root" --before "$root/demo.before"
    rm -rf "$root"

    [ "$status" -eq 1 ]
    echo "$output" | grep -q "description changed"
}

@test "gate B warns on untraced prose by default and fails under --strict" {
    local root default_status strict_status default_output
    root="$(_fixture)"
    # Reword a Gotchas bullet so the original line has no home in reference/.
    printf -- '---\nname: demo\ndescription: "Demo skill. Triggers: demo."\n---\n\n# Demo\n\n## Steps\n\nDetail: [reference/steps.md](reference/steps.md)\n\n## Rules\n\n- **MUST** do the thing\n\n## Gotchas\n\n- Trap number one rewritten beyond recognition\n' \
        > "$root/app/skills/demo/SKILL.md"

    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root" --before "$root/demo.before"
    default_status="$status"
    default_output="$output"

    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root" --before "$root/demo.before" --strict
    strict_status="$status"
    rm -rf "$root"

    [ "$default_status" -eq 0 ]
    [ "$strict_status" -eq 1 ]
    echo "$default_output" | grep -q "WARN: 1 removed lines not found in reference/"
    echo "$default_output" | grep -q "UNTRACED: - Trap number one"
}

@test "--json emits a parseable report carrying the gate verdicts" {
    local root
    root="$(_fixture)"
    printf '# Steps\n\n```bash\npython3 scripts/thing.py --flag\n```\n' \
        > "$root/app/skills/demo/reference/steps.md"
    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root" --before "$root/demo.before" --json
    rm -rf "$root"

    [ "$status" -eq 1 ]
    echo "$output" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['ok'] is False, d['ok']
assert d['skill'] == 'demo', d['skill']
assert d['gates']['A_code_preservation']['code_lines_lost'] == 1, d['gates']['A_code_preservation']
assert d['gates']['D_description_stable']['status'] == 'pass', d['gates']['D_description_stable']
assert d['gates']['E_link_integrity']['status'] == 'pass', d['gates']['E_link_integrity']
print('OK')
" | grep -q OK
}

@test "gate E fails on a relative link that does not resolve from its own file" {
    local root
    root="$(_fixture)"
    # The classic split casualty: a path that was correct in the body and is wrong
    # one directory down. validate.py never looks inside reference/, so only this
    # gate sees it.
    printf '# Steps\n\nSee [reference/other.md](reference/other.md)\n\n```bash\npython3 scripts/thing.py --flag\necho "second command"\n```\n' \
        > "$root/app/skills/demo/reference/steps.md"
    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root" --before "$root/demo.before"
    rm -rf "$root"

    [ "$status" -eq 1 ]
    echo "$output" | grep -q "BROKEN: steps.md -> reference/other.md"
    echo "$output" | grep -q "SPLIT GATE FAILED"
}

@test "gate E resolves a link that points at a sibling reference file" {
    local root
    root="$(_fixture)"
    printf '# Other\n\nnothing here\n' > "$root/app/skills/demo/reference/other.md"
    printf '# Steps\n\nSee [other.md](other.md) and [anchored](other.md#section)\n\n```bash\npython3 scripts/thing.py --flag\necho "second command"\n```\n' \
        > "$root/app/skills/demo/reference/steps.md"
    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root" --before "$root/demo.before"
    rm -rf "$root"

    [ "$status" -eq 0 ]
    echo "$output" | grep -q "relative links resolve"
}

@test "gate E ignores fenced examples, inline-code regexes, URLs and anchors" {
    local root
    root="$(_fixture)"
    {
        printf '# Steps\n\n'
        printf 'External [docs](https://example.com/missing.md) and an [anchor](#somewhere).\n\n'
        # A regex in inline code that reads as a link to a naive matcher.
        printf 'Grep: `type=["'"'"']password["'"'"'](?!.*autocomplete)`\n\n'
        printf '```markdown\nSample only: [not-a-real-file.md](not-a-real-file.md)\n```\n\n'
        printf '```bash\npython3 scripts/thing.py --flag\necho "second command"\n```\n'
    } > "$root/app/skills/demo/reference/steps.md"
    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root" --before "$root/demo.before"
    rm -rf "$root"

    [ "$status" -eq 0 ]
    echo "$output" | grep -q "SPLIT GATE PASSED"
}

@test "every shipped skill has resolvable relative links" {
    # Regression guard for the whole tree, not just a skill under refactor.
    run python3 - "$TOOLKIT_DIR" <<'PY'
import importlib.util, pathlib, sys
root = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("cs", root / "scripts" / "check_split.py")
cs = importlib.util.module_from_spec(spec); spec.loader.exec_module(cs)
broken = []
for d in sorted((root / "app" / "skills").iterdir()):
    if not d.is_dir() or d.name.startswith("_") or not (d / "SKILL.md").is_file():
        continue
    _, body = cs.split_frontmatter((d / "SKILL.md").read_text(encoding="utf-8"))
    for entry in cs.gate_e_links(d, body)["broken"]:
        broken.append(f"{d.name}: {entry}")
print("\n".join(broken) if broken else "OK")
PY
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "^OK$"
}

@test "check_split exits 2 when no content source is given" {
    local root
    root="$(_fixture)"
    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root"
    rm -rf "$root"
    [ "$status" -eq 2 ]
}

@test "check_split exits 2 when both --before and --base-ref are given" {
    local root
    root="$(_fixture)"
    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root" --before "$root/demo.before" --base-ref HEAD
    rm -rf "$root"
    [ "$status" -eq 2 ]
}

@test "check_split exits 2 on an unknown skill" {
    local root
    root="$(_fixture)"
    run python3 "$CHECK_SPLIT" nosuchskill --toolkit-dir "$root" --before "$root/demo.before"
    rm -rf "$root"
    [ "$status" -eq 2 ]
}

@test "check_split exits 2 on an unreadable git ref" {
    local root
    root="$(_fixture)"
    run python3 "$CHECK_SPLIT" demo --toolkit-dir "$root" --base-ref no/such/ref
    rm -rf "$root"
    [ "$status" -eq 2 ]
}

@test "check_split handles a real toolkit skill with reference files" {
    local before
    before="$(mktemp)"
    cp "$TOOLKIT_DIR/app/skills/clean-code/SKILL.md" "$before"
    run python3 "$CHECK_SPLIT" clean-code --before "$before"
    rm -f "$before"

    [ "$status" -eq 0 ]
    echo "$output" | grep -q "code lines lost: 0"
    echo "$output" | grep -q "reference files: 5"
}
