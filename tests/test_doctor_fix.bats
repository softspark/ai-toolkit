#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for doctor --fix auto-repair mode
# Optimized: install runs once in setup_file, each test restores from snapshot.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export DOCTOR_SNAPSHOT
    DOCTOR_SNAPSHOT="$(mktemp -d)"
    export HOME="$DOCTOR_SNAPSHOT"
    python3 "$TOOLKIT_DIR/scripts/install.py" "$DOCTOR_SNAPSHOT" >/dev/null 2>&1
}

teardown_file() {
    rm -rf "$DOCTOR_SNAPSHOT"
}

setup() {
    TEST_TMP="$(mktemp -d)"
    cp -a "$DOCTOR_SNAPSHOT/." "$TEST_TMP/"
    export HOME="$TEST_TMP"
}

teardown() {
    rm -rf "$TEST_TMP"
}

check_single_runtime() {
    env PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - "$1" "${2:-5}" <<'PY'
import sys
from unittest.mock import patch

import doctor

runtime, timeout = sys.argv[1:]
doctor.AI_RUNTIME_BINARIES = (("dsh", "DSH"),)
doctor.AI_RUNTIME_VERSION_TIMEOUT_SECONDS = float(timeout)
result = doctor.DiagResult()
discovered = None if runtime == "MISSING" else runtime
with patch.object(doctor.shutil, "which", return_value=discovered):
    doctor.check_ai_runtimes(result)
print(f"warnings={result.warnings} errors={result.errors}")
PY
}

@test "doctor --fix repairs broken agent symlink" {
    ln -sf "/nonexistent/agent.md" "$TEST_TMP/.claude/agents/test-broken.md"
    [ -L "$TEST_TMP/.claude/agents/test-broken.md" ]
    [ ! -e "$TEST_TMP/.claude/agents/test-broken.md" ]
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED"
    [ ! -L "$TEST_TMP/.claude/agents/test-broken.md" ]
}

@test "doctor --fix repairs broken skill symlink" {
    ln -sf "/nonexistent/skill" "$TEST_TMP/.claude/skills/test-broken"
    [ -L "$TEST_TMP/.claude/skills/test-broken" ]
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED"
    [ ! -L "$TEST_TMP/.claude/skills/test-broken" ]
}

@test "doctor --fix makes non-executable hook executable" {
    chmod -x "$TEST_TMP/.softspark/ai-toolkit/hooks/guard-destructive.sh"
    [ ! -x "$TEST_TMP/.softspark/ai-toolkit/hooks/guard-destructive.sh" ]
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED.*executable"
    [ -x "$TEST_TMP/.softspark/ai-toolkit/hooks/guard-destructive.sh" ]
}

@test "doctor --fix restores missing hook script" {
    rm "$TEST_TMP/.softspark/ai-toolkit/hooks/guard-destructive.sh"
    [ ! -f "$TEST_TMP/.softspark/ai-toolkit/hooks/guard-destructive.sh" ]
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED.*restored"
    [ -x "$TEST_TMP/.softspark/ai-toolkit/hooks/guard-destructive.sh" ]
}

@test "doctor --fix regenerates missing llms-full.txt" {
    # Runs against a private copy of the toolkit, not the shared checkout.
    # doctor resolves its toolkit root from its own file path, so deleting
    # llms-full.txt in the checkout and asserting on the FIXED line is a race:
    # bats parallelizes across files, test_doctor_plugin_double_load.bats also
    # runs doctor --fix, and that run regenerates the artifact between this
    # test's delete and its assertion. The old version also left a
    # llms-full.txt.test-bak behind in the repo whenever it lost that race,
    # because the restoring mv never ran.
    local tk="$TEST_TMP/toolkit-copy"
    mkdir -p "$tk"
    tar -cf - -C "$TOOLKIT_DIR" --exclude=.git --exclude=node_modules . | tar -xf - -C "$tk"
    [ -f "$tk/llms-full.txt" ]
    rm -f "$tk/llms-full.txt"
    run python3 "$tk/scripts/doctor.py" --fix
    echo "$output" | grep -q "FIXED.*llms-full.txt"
    [ -f "$tk/llms-full.txt" ]
    [ ! -e "$TOOLKIT_DIR/llms-full.txt.test-bak" ]
}

@test "doctor without --fix does not modify anything" {
    ln -sf "/nonexistent/agent.md" "$TEST_TMP/.claude/agents/test-broken.md"
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    [ -L "$TEST_TMP/.claude/agents/test-broken.md" ]
    echo "$output" | grep -q "WARN.*broken"
    ! echo "$output" | grep -q "FIXED"
}

@test "doctor recognizes canonical toolkit hooks without private source tags" {
    python3 - "$TEST_TMP/.claude/settings.json" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
for entries in data.get("hooks", {}).values():
    for entry in entries:
        entry.pop("_source", None)
        for hook in entry.get("hooks", []):
            hook.pop("_source", None)
with open(path, "w") as f:
    json.dump(data, f)
PY
    run python3 "$TOOLKIT_DIR/scripts/doctor.py"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "settings.json: 28/28 toolkit hook entries"
    ! echo "$output" | grep -q "no toolkit hooks"
}

@test "doctor --fix shows fix mode in summary" {
    run python3 "$TOOLKIT_DIR/scripts/doctor.py" --fix
    echo "$output" | grep -q "auto-repair"
}

@test "cli: help lists --fix option for doctor" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" help
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '\-\-fix'
}

# ── Language rules drift (project-local check 10) ─────────────────────────────

@test "doctor: flags a detected language missing its injected rules" {
    proj="$TEST_TMP/proj-drift"
    mkdir -p "$proj/.claude"
    printf '%s\n' '<!-- TOOLKIT:language-rules START -->' 'Detected languages: `python-rules`.' '<!-- TOOLKIT:language-rules END -->' > "$proj/.claude/CLAUDE.md"
    printf '[package]\nname = "x"\n' > "$proj/Cargo.toml"
    printf 'print(1)\n' > "$proj/main.py"
    run bash -c "cd '$proj' && python3 '$TOOLKIT_DIR/scripts/doctor.py'"
    echo "$output" | grep -q "rust-rules not injected"
}

@test "doctor: language drift passes when rules match detected languages" {
    proj="$TEST_TMP/proj-sync"
    mkdir -p "$proj/.claude"
    printf '%s\n' '<!-- TOOLKIT:language-rules START -->' 'Detected languages: `python-rules`.' '<!-- TOOLKIT:language-rules END -->' > "$proj/.claude/CLAUDE.md"
    printf 'print(1)\n' > "$proj/main.py"
    run bash -c "cd '$proj' && python3 '$TOOLKIT_DIR/scripts/doctor.py'"
    echo "$output" | grep -q "project language rules in sync"
}

@test "doctor: language drift skips a non-local-install directory" {
    proj="$TEST_TMP/proj-plain"
    mkdir -p "$proj"
    printf 'print(1)\n' > "$proj/main.py"
    run bash -c "cd '$proj' && python3 '$TOOLKIT_DIR/scripts/doctor.py'"
    echo "$output" | grep -q "not a local-install project"
}

@test "doctor: AI runtime probe executes the discovered path and preserves prerelease semver" {
    runtime="$TEST_TMP/dsh-exact"
    cat > "$runtime" <<'SH'
#!/bin/sh
printf '%s\n' 'dsh 0.1.1-rc.2+build.7'
SH
    chmod +x "$runtime"

    run env PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - "$runtime" <<'PY'
import sys
from unittest.mock import patch

import doctor

doctor.AI_RUNTIME_BINARIES = (("dsh", "DSH"),)
result = doctor.DiagResult()
with patch.object(doctor.shutil, "which", return_value=sys.argv[1]):
    doctor.check_ai_runtimes(result)
PY
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'OK: DSH (dsh) 0.1.1-rc.2+build.7'
}

@test "doctor: AI runtime probe reports a stable SemVer" {
    runtime="$TEST_TMP/dsh-stable"
    printf '%s\n' '#!/bin/sh' "printf '%s\\n' 'dsh 1.2.3'" > "$runtime"
    chmod +x "$runtime"

    run check_single_runtime "$runtime"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'OK: DSH (dsh) 1.2.3'
    echo "$output" | grep -q 'warnings=0 errors=0'
}

@test "doctor: AI runtime probe enforces complete SemVer tokens" {
    for version in \
        '1.2.3.4' \
        '1.2.3rc1' \
        '01.2.3' \
        '1.2.3-01' \
        '1.2.3-rc..2' \
        '1.2.3+build..7'; do
        runtime="$TEST_TMP/dsh-invalid-semver"
        printf '%s\n' '#!/bin/sh' "printf '%s\\n' 'dsh $version'" > "$runtime"
        chmod +x "$runtime"

        run check_single_runtime "$runtime"
        [ "$status" -eq 0 ]
        echo "$output" | grep -q \
            'WARN: DSH (dsh) detected but version output contained invalid SemVer'
        ! echo "$output" | grep -q 'OK: DSH'
    done

    for version in '1.2.3' '0.1.1-rc.2' '1.2.3+build.7'; do
        runtime="$TEST_TMP/dsh-valid-semver"
        printf '%s\n' '#!/bin/sh' "printf '%s\\n' 'dsh $version'" > "$runtime"
        chmod +x "$runtime"

        run check_single_runtime "$runtime"
        [ "$status" -eq 0 ]
        echo "$output" | grep -q "OK: DSH (dsh) $version"
        echo "$output" | grep -q 'warnings=0 errors=0'
    done
}

@test "doctor: missing AI runtime is skipped without probing" {
    run check_single_runtime MISSING
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'SKIP: DSH (dsh) not found'
    echo "$output" | grep -q 'warnings=0 errors=0'
}

@test "doctor: nonzero AI runtime version command is never reported OK" {
    runtime="$TEST_TMP/dsh-nonzero"
    printf '%s\n' '#!/bin/sh' 'exit 7' > "$runtime"
    chmod +x "$runtime"

    run check_single_runtime "$runtime"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'WARN: DSH (dsh) detected but version command exited with status 7'
    ! echo "$output" | grep -q 'OK: DSH'
}

@test "doctor: malformed AI runtime executable is never reported OK" {
    runtime="$TEST_TMP/dsh-malformed"
    printf '%s\n' 'not an executable image' > "$runtime"
    chmod +x "$runtime"

    run check_single_runtime "$runtime"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'WARN: DSH (dsh) detected but version check failed:'
    ! echo "$output" | grep -q 'OK: DSH'
}

@test "doctor: disappearing AI runtime executable is never reported OK" {
    run check_single_runtime "$TEST_TMP/dsh-disappeared"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'WARN: DSH (dsh) detected but executable disappeared'
    ! echo "$output" | grep -q 'OK: DSH'
}

@test "doctor: invalid-text AI runtime output is never reported OK" {
    runtime="$TEST_TMP/dsh-invalid-text"
    printf '%s\n' '#!/bin/sh' "printf '\\377'" > "$runtime"
    chmod +x "$runtime"

    run check_single_runtime "$runtime"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'WARN: DSH (dsh) detected but version output is not valid text'
    ! echo "$output" | grep -q 'OK: DSH'
}

@test "doctor: unknown AI runtime version output is never reported OK" {
    runtime="$TEST_TMP/dsh-unknown"
    printf '%s\n' '#!/bin/sh' "printf '%s\\n' 'dsh development snapshot'" > "$runtime"
    chmod +x "$runtime"

    run check_single_runtime "$runtime"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'WARN: DSH (dsh) detected but version output did not contain SemVer'
    ! echo "$output" | grep -q 'OK: DSH'
}

@test "doctor: timed-out AI runtime version command is never reported OK" {
    runtime="$TEST_TMP/dsh-timeout"
    printf '%s\n' '#!/bin/sh' 'sleep 1' > "$runtime"
    chmod +x "$runtime"

    run check_single_runtime "$runtime" 0.05
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'WARN: DSH (dsh) detected but version check timed out'
    ! echo "$output" | grep -q 'OK: DSH'
}
