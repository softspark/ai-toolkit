#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    export CLINE_HOOK_TMP
    CLINE_HOOK_TMP="$(mktemp -d)"
    export CLINE_HOOK_OUTSIDE
    CLINE_HOOK_OUTSIDE="$(mktemp -d)"
}

teardown() {
    rm -rf "$CLINE_HOOK_TMP"
    rm -rf "$CLINE_HOOK_OUTSIDE"
}

generate_hooks() {
    python3 "$TOOLKIT_DIR/scripts/generate_cline_hooks.py" "$CLINE_HOOK_TMP" >/dev/null
}

@test "cline hooks: emits the exact eight executable native hook files" {
    generate_hooks

    run python3 - "$CLINE_HOOK_TMP/.cline/hooks" <<'PY'
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1])
expected = {
    "TaskStart",
    "TaskResume",
    "TaskCancel",
    "TaskComplete",
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "PreCompact",
}

assert {path.name for path in root.iterdir()} == expected
for path in root.iterdir():
    assert path.is_file()
    assert not path.is_symlink()
    assert stat.S_IMODE(path.stat().st_mode) == 0o755
    assert path.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3\n")
PY
    [ "$status" -eq 0 ]
}

@test "cline hooks: project generation dual-emits CLI and extension roots" {
    generate_hooks

    for event in TaskStart TaskResume TaskCancel TaskComplete PreToolUse PostToolUse UserPromptSubmit PreCompact; do
        [ -x "$CLINE_HOOK_TMP/.cline/hooks/$event" ]
        [ -x "$CLINE_HOOK_TMP/.clinerules/hooks/$event" ]
        cmp "$CLINE_HOOK_TMP/.cline/hooks/$event" \
            "$CLINE_HOOK_TMP/.clinerules/hooks/$event"
    done
}

@test "cline hooks: legacy .clinerules file is preserved while CLI hooks emit" {
    printf '%s\n' '# Team legacy rules' 'Keep these bytes.' \
        > "$CLINE_HOOK_TMP/.clinerules"
    cp "$CLINE_HOOK_TMP/.clinerules" "$CLINE_HOOK_TMP/before.clinerules"

    generate_hooks

    cmp "$CLINE_HOOK_TMP/before.clinerules" "$CLINE_HOOK_TMP/.clinerules"
    [ -x "$CLINE_HOOK_TMP/.cline/hooks/PreToolUse" ]
    [ ! -e "$CLINE_HOOK_TMP/.clinerules/hooks" ]
}

@test "cline hooks: PreToolUse blocks destructive commands and allows benign ones" {
    generate_hooks
    hook="$CLINE_HOOK_TMP/.cline/hooks/PreToolUse"

    run bash -c "printf '%s' '{\"preToolUse\":{\"toolName\":\"bash\",\"parameters\":{\"command\":\"git reset --hard HEAD\"}}}' | '$hook'"
    [ "$status" -eq 0 ]
    run python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["cancel"] is True; assert d["errorMessage"]' "$output"
    [ "$status" -eq 0 ]

    run bash -c "printf '%s' '{\"preToolUse\":{\"toolName\":\"bash\",\"parameters\":{\"command\":\"git status --short\"}}}' | '$hook'"
    [ "$status" -eq 0 ]
    run python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d == {"cancel":False}' "$output"
    [ "$status" -eq 0 ]
}

@test "cline hooks: documented run_commands payload cancels destructive CLI commands" {
    generate_hooks
    hook="$CLINE_HOOK_TMP/.cline/hooks/PreToolUse"
    payload='{"preToolUse":{"toolName":"run_commands","parameters":{"commands":["git status --short","git reset --hard HEAD"]}}}'

    run bash -c "printf '%s' '$payload' | '$hook'"

    [ "$status" -eq 0 ]
    run python3 -c '
import json, sys
value = json.loads(sys.argv[1])
assert value["cancel"] is True
assert value["errorMessage"]
' "$output"
    [ "$status" -eq 0 ]
}

@test "cline hooks: malformed hook-specific command data fails closed" {
    generate_hooks
    hook="$CLINE_HOOK_TMP/.cline/hooks/PreToolUse"
    payload='{"preToolUse":{"toolName":"run_commands","parameters":{"commands":[""]}}}'

    run bash -c "printf '%s' '$payload' | '$hook'"

    [ "$status" -eq 0 ]
    run python3 -c '
import json, sys
value = json.loads(sys.argv[1])
assert value["cancel"] is True
assert value["errorMessage"]
' "$output"
    [ "$status" -eq 0 ]
}

@test "cline hooks: PreToolUse covers elevated and infrastructure destruction" {
    generate_hooks
    hook="$CLINE_HOOK_TMP/.cline/hooks/PreToolUse"

    for command in \
        "sudo rm -rf /var/tmp/release" \
        "rm --recursive --force build" \
        "terraform destroy -auto-approve"; do
        payload="$(python3 -c 'import json,sys; print(json.dumps({"preToolUse":{"toolName":"bash","parameters":{"command":sys.argv[1]}}}))' "$command")"
        run bash -c "printf '%s' '$payload' | '$hook'"
        [ "$status" -eq 0 ]
        run python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["cancel"] is True; assert d["errorMessage"]' "$output"
        [ "$status" -eq 0 ]
    done
}

@test "cline hooks: lifecycle adapters use only native context output fields" {
    generate_hooks

    for event in TaskStart TaskResume UserPromptSubmit PreCompact; do
        run bash -c "printf '%s' '{}' | '$CLINE_HOOK_TMP/.cline/hooks/$event'"
        [ "$status" -eq 0 ]
        run python3 -c '
import json, sys
value = json.loads(sys.argv[1])
assert set(value) == {"cancel", "contextModification", "errorMessage"}
assert value["cancel"] is False
assert isinstance(value["contextModification"], str) and value["contextModification"]
assert value["errorMessage"] == ""
' "$output"
        [ "$status" -eq 0 ]
    done

    for event in TaskCancel TaskComplete PostToolUse; do
        run bash -c "printf '%s' '{}' | '$CLINE_HOOK_TMP/.cline/hooks/$event'"
        [ "$status" -eq 0 ]
        [ "$output" = '{"cancel":false}' ]
    done
}

@test "cline hooks: generation removes only stale managed hooks" {
    mkdir -p "$CLINE_HOOK_TMP/.cline/hooks"
    printf '%s\n' '#!/bin/sh' '# ai-toolkit-managed: cline-hook' > "$CLINE_HOOK_TMP/.cline/hooks/OldToolkitHook"
    printf '%s\n' '#!/bin/sh' '# user hook' > "$CLINE_HOOK_TMP/.cline/hooks/TeamPolicy"

    generate_hooks

    [ ! -e "$CLINE_HOOK_TMP/.cline/hooks/OldToolkitHook" ]
    grep -q '^# user hook$' "$CLINE_HOOK_TMP/.cline/hooks/TeamPolicy"
}

@test "cline hooks: user-owned event conflict rejects the whole transaction" {
    mkdir -p "$CLINE_HOOK_TMP/.cline/hooks"
    printf '%s\n' '#!/bin/sh' 'echo team-policy' > "$CLINE_HOOK_TMP/.cline/hooks/PreToolUse"

    run python3 "$TOOLKIT_DIR/scripts/generate_cline_hooks.py" "$CLINE_HOOK_TMP"

    [ "$status" -ne 0 ]
    grep -q '^echo team-policy$' "$CLINE_HOOK_TMP/.cline/hooks/PreToolUse"
    [ ! -e "$CLINE_HOOK_TMP/.cline/hooks/TaskStart" ]
}

@test "cline hooks: malformed and oversized inputs fail closed with native JSON" {
    generate_hooks
    hook="$CLINE_HOOK_TMP/.cline/hooks/PreToolUse"

    run bash -c "printf '%s' '{bad-json' | '$hook'"
    [ "$status" -eq 0 ]
    run python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["cancel"] is True; assert d["errorMessage"]' "$output"
    [ "$status" -eq 0 ]

    run bash -c "python3 -c 'import sys; sys.stdout.write(\"x\" * (1024 * 1024 + 1))' | '$hook'"
    [ "$status" -eq 0 ]
    run python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["cancel"] is True; assert d["errorMessage"]' "$output"
    [ "$status" -eq 0 ]
}

@test "cline hooks: cleanup removes only managed hook files" {
    generate_hooks
    printf '%s\n' '#!/bin/sh' '# ai-toolkit-managed: cline-hook' \
        > "$CLINE_HOOK_TMP/.cline/hooks/RetiredToolkitEvent"
    printf '%s\n' '#!/bin/sh' '# team policy' > "$CLINE_HOOK_TMP/.cline/hooks/TeamPolicy"
    printf '%s\n' '#!/bin/sh' '# extension team policy' \
        > "$CLINE_HOOK_TMP/.clinerules/hooks/TeamPolicy"

    run python3 - "$TOOLKIT_DIR" "$CLINE_HOOK_TMP" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from generate_cline_hooks import cleanup

cleanup(Path(sys.argv[2]))
PY
    [ "$status" -eq 0 ]
    [ ! -e "$CLINE_HOOK_TMP/.cline/hooks/RetiredToolkitEvent" ]
    [ -f "$CLINE_HOOK_TMP/.cline/hooks/TeamPolicy" ]
    [ -f "$CLINE_HOOK_TMP/.clinerules/hooks/TeamPolicy" ]
    for event in TaskStart TaskResume TaskCancel TaskComplete PreToolUse PostToolUse UserPromptSubmit PreCompact; do
        [ ! -e "$CLINE_HOOK_TMP/.cline/hooks/$event" ]
        [ ! -e "$CLINE_HOOK_TMP/.clinerules/hooks/$event" ]
    done
}

@test "cline hooks: global mode writes the same native surface under the supplied home" {
    run python3 - "$TOOLKIT_DIR" "$CLINE_HOOK_TMP" <<'PY'
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from generate_cline_hooks import HOOK_EVENTS, generate_global

root = generate_global(Path(sys.argv[2]))
assert root == Path(os.path.abspath(sys.argv[2])) / ".cline" / "hooks"
assert {path.name for path in root.iterdir()} == set(HOOK_EVENTS)
PY
    [ "$status" -eq 0 ]
}

@test "cline hooks: extension global mode uses Documents Cline Hooks compatibility root" {
    run python3 - "$TOOLKIT_DIR" "$CLINE_HOOK_TMP" <<'PY'
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from generate_cline_hooks import HOOK_EVENTS, generate_extension_global

root = generate_extension_global(Path(sys.argv[2]))
expected = Path(os.path.abspath(sys.argv[2])) / "Documents" / "Cline" / "Hooks"
assert root == expected
assert {path.name for path in root.iterdir()} == set(HOOK_EVENTS)
PY
    [ "$status" -eq 0 ]
}

@test "cline hooks: generation is idempotent" {
    generate_hooks
    first="$(shasum "$CLINE_HOOK_TMP/.cline/hooks"/*)"
    generate_hooks
    second="$(shasum "$CLINE_HOOK_TMP/.cline/hooks"/*)"
    [ "$first" = "$second" ]
}

@test "cline hooks: rejects symlinked hook output without touching its target" {
    mkdir -p "$CLINE_HOOK_TMP/.cline/hooks" "$CLINE_HOOK_TMP/external"
    printf '%s\n' '#!/bin/sh' 'echo external' > "$CLINE_HOOK_TMP/external/PreToolUse"
    ln -s "$CLINE_HOOK_TMP/external/PreToolUse" "$CLINE_HOOK_TMP/.cline/hooks/PreToolUse"

    run python3 "$TOOLKIT_DIR/scripts/generate_cline_hooks.py" "$CLINE_HOOK_TMP"

    [ "$status" -ne 0 ]
    grep -q '^echo external$' "$CLINE_HOOK_TMP/external/PreToolUse"
    [ ! -e "$CLINE_HOOK_TMP/.cline/hooks/TaskStart" ]
}

@test "cline hooks: cleanup rejects a symlinked global ancestor before discovery" {
    mkdir -p "$CLINE_HOOK_OUTSIDE/Cline/Hooks"
    printf '%s\n' '#!/bin/sh' '# ai-toolkit-managed: cline-hook' \
        > "$CLINE_HOOK_OUTSIDE/Cline/Hooks/TaskStart"
    before="$(cksum "$CLINE_HOOK_OUTSIDE/Cline/Hooks/TaskStart")"
    ln -s "$CLINE_HOOK_OUTSIDE" "$CLINE_HOOK_TMP/Documents"

    run python3 - "$TOOLKIT_DIR" "$CLINE_HOOK_TMP" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
import generate_cline_hooks as hooks

def unexpected_discovery(_root):
    raise AssertionError("cleanup traversed a symlink before ancestry rejection")

hooks._stale_candidates = unexpected_discovery
home = Path(sys.argv[2])
try:
    hooks.cleanup(
        home,
        hooks_root=home / "Documents" / "Cline" / "Hooks",
    )
except RuntimeError as error:
    assert "symlinked Cline hooks ancestor" in str(error), error
else:
    raise AssertionError("symlinked Cline hooks ancestor was accepted")
PY

    [ "$status" -eq 0 ]
    [ "$(cksum "$CLINE_HOOK_OUTSIDE/Cline/Hooks/TaskStart")" = "$before" ]
}
