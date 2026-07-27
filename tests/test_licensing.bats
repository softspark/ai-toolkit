#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Licensing contract: Apache-2.0 across every surface that declares a licence,
# an SPDX header on every shipped source file, and a NOTICE that actually
# reaches the npm package.
#
# This is a test rather than an SOP line on purpose. A release SOP is only as
# good as the person remembering to run it, and this project has two
# same-day postmortems about SOPs that existed and were skipped. CI runs tests.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

# Every extension with a comment syntax that ships as source. Markdown is
# deliberately absent: SKILL.md and agent files carry parsed YAML frontmatter,
# and their descriptions load into every session's context, so a header there
# is both a parsing hazard and a permanent per-session token cost.
source_files() {
    find "$TOOLKIT_DIR/scripts" "$TOOLKIT_DIR/app" "$TOOLKIT_DIR/bin" \
         "$TOOLKIT_DIR/tests" "$TOOLKIT_DIR/benchmarks" \
         \( -name '*.py' -o -name '*.sh' -o -name '*.js' -o -name '*.bats' \) \
         -not -path '*__pycache__*' 2>/dev/null
}

@test "every shipped source file carries an SPDX header" {
    missing=""
    while IFS= read -r f; do
        [ -n "$f" ] || continue
        grep -q 'SPDX-License-Identifier' "$f" || missing="$missing$f"$'\n'
    done < <(source_files)

    if [ -n "$missing" ]; then
        echo "Files without an SPDX header:"
        echo "$missing"
        return 1
    fi
}

@test "SPDX headers name Apache-2.0 and nothing else" {
    wrong=""
    while IFS= read -r f; do
        [ -n "$f" ] || continue
        line=$(grep -m1 'SPDX-License-Identifier' "$f")
        case "$line" in
            *"Apache-2.0"*) ;;
            *) wrong="$wrong$f: $line"$'\n' ;;
        esac
    done < <(source_files)

    if [ -n "$wrong" ]; then
        echo "Headers naming a licence other than Apache-2.0:"
        echo "$wrong"
        return 1
    fi
}

@test "no markdown file carries an SPDX header" {
    # Guards the deliberate exclusion. A header in a skill or agent file would
    # sit above parsed frontmatter and bill every session for the privilege.
    #
    # Only the first few lines are inspected. An inserted header lands at the
    # very top; prose or a fenced example deeper in a document is documentation,
    # not a header — kb/reference/licensing.md quotes the convention verbatim and
    # must not trip this.
    offenders=""
    while IFS= read -r f; do
        [ -n "$f" ] || continue
        if head -5 "$f" | grep -q 'SPDX-License-Identifier'; then
            offenders="$offenders$f"$'\n'
        fi
    done < <(find "$TOOLKIT_DIR/app" "$TOOLKIT_DIR/kb" -name '*.md' 2>/dev/null)

    if [ -n "$offenders" ]; then
        echo "Markdown files with a licence header at the top:"
        echo "$offenders"
        return 1
    fi
}

@test "LICENSE is the complete Apache 2.0 text" {
    [ -f "$TOOLKIT_DIR/LICENSE" ]
    grep -q 'Apache License' "$TOOLKIT_DIR/LICENSE"
    grep -q 'Version 2.0, January 2004' "$TOOLKIT_DIR/LICENSE"
    grep -q 'END OF TERMS AND CONDITIONS' "$TOOLKIT_DIR/LICENSE"
    grep -q 'APPENDIX: How to apply the Apache License' "$TOOLKIT_DIR/LICENSE"
}

@test "NOTICE exists and carries attribution plus the source URL" {
    [ -f "$TOOLKIT_DIR/NOTICE" ]
    grep -q 'Lukasz Krzemien' "$TOOLKIT_DIR/NOTICE"
    grep -q 'github.com/softspark/ai-toolkit' "$TOOLKIT_DIR/NOTICE"
    # Section 4(d) is the whole reason this file exists; say so in it.
    grep -q '4(d)' "$TOOLKIT_DIR/NOTICE"
    # MIT-era contributions stay attributed, as MIT requires.
    grep -q 'MIT License' "$TOOLKIT_DIR/NOTICE"
}

@test "LICENSE and NOTICE both ship in the npm package" {
    # A NOTICE that does not reach the consumer cannot satisfy 4(d).
    run python3 -c "
import json, pathlib
files = json.loads(pathlib.Path('$TOOLKIT_DIR/package.json').read_text())['files']
missing = [f for f in ('LICENSE', 'NOTICE') if f not in files]
print('MISSING:' + repr(missing))
raise SystemExit(1 if missing else 0)
"
    [ "$status" -eq 0 ]
}

@test "every manifest that declares a licence declares Apache-2.0" {
    run python3 -c "
import json, pathlib
root = pathlib.Path('$TOOLKIT_DIR')
seen = {}
for rel, key in (
    ('package.json', ('license',)),
    ('manifest.json', ('license',)),
    ('app/.claude-plugin/plugin.json', ('license',)),
    ('package-lock.json', ('packages', '', 'license')),
):
    p = root / rel
    if not p.is_file():
        continue
    node = json.loads(p.read_text())
    for k in key:
        if not isinstance(node, dict) or k not in node:
            node = None
            break
        node = node[k]
    if node is not None:
        seen[rel] = node
wrong = {k: v for k, v in seen.items() if v != 'Apache-2.0'}
print('SEEN:' + repr(seen))
print('WRONG:' + repr(wrong))
raise SystemExit(1 if wrong or not seen else 0)
"
    [ "$status" -eq 0 ]
}
