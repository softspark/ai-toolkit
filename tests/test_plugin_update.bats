#!/usr/bin/env bats
# Tests for version-aware plugin pack updates and their wiring into
# `ai-toolkit update`.
#
# Before this, `plugin update` removed and reinstalled every pack
# unconditionally. For a pack that downloads a binary at install time that
# means refetching it on every core update, so the update path now skips a
# pack whose manifest version matches what was recorded at install.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CLI="$TOOLKIT_DIR/bin/ai-toolkit.js"
PLUGIN_PY="$TOOLKIT_DIR/scripts/plugin.py"
STATE=".softspark/ai-toolkit/plugins.json"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
}

teardown() {
    rm -rf "$TEST_TMP"
}

record_version() {
    python3 -c "
import json, pathlib
p = pathlib.Path('$TEST_TMP/$STATE')
d = json.loads(p.read_text())
d['targets']['claude']['versions']['$1'] = '$2'
p.write_text(json.dumps(d, indent=2))
"
}

recorded_version() {
    python3 -c "
import json, pathlib
d = json.loads(pathlib.Path('$TEST_TMP/$STATE').read_text())
print(d['targets']['claude']['versions'].get('$1', ''))
"
}

@test "install records the pack version in plugins.json" {
    run node "$CLI" plugin install --editor claude memory-pack
    [ "$status" -eq 0 ]
    run recorded_version memory-pack
    [ "$output" = "1.0.0" ]
}

@test "update --all is a silent no-op when nothing moved" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    run node "$CLI" plugin update --editor claude --all
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "update --all reinstalls a pack whose recorded version is stale" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    record_version memory-pack 0.9.0

    run node "$CLI" plugin update --editor claude --all
    [ "$status" -eq 0 ]
    case "$output" in
        *"0.9.0 -> 1.0.0"*) ;;
        *) echo "expected a version transition, got: $output"; return 1 ;;
    esac

    run recorded_version memory-pack
    [ "$output" = "1.0.0" ]
}

@test "update --dry-run reports the pending change without acting" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    record_version memory-pack 0.9.0

    run node "$CLI" plugin update --editor claude --all --dry-run
    [ "$status" -eq 0 ]
    case "$output" in
        *"Would update"*) ;;
        *) echo "expected a dry-run report, got: $output"; return 1 ;;
    esac

    # Untouched: the stale marker is still what it was.
    run recorded_version memory-pack
    [ "$output" = "0.9.0" ]
}

@test "update --dry-run says nothing is pending when all packs are current" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    run node "$CLI" plugin update --editor claude --all --dry-run
    [ "$status" -eq 0 ]
    case "$output" in
        *"up to date"*) ;;
        *) echo "expected an up-to-date report, got: $output"; return 1 ;;
    esac
}

@test "update --all with no packs installed does no work and stays quiet" {
    run node "$CLI" plugin update --editor claude --all
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "--force reinstalls even when the version matches" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    run node "$CLI" plugin update --editor claude --all --force
    [ "$status" -eq 0 ]
    case "$output" in
        *"Updating: memory-pack"*) ;;
        *) echo "expected a forced update, got: $output"; return 1 ;;
    esac
}

@test "remove forgets the recorded version" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    node "$CLI" plugin remove --editor claude memory-pack >/dev/null 2>&1
    run recorded_version memory-pack
    [ -z "$output" ]
}

@test "state written before versions were tracked updates each pack once" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    # Legacy shape: installed list, no versions map.
    python3 -c "
import json, pathlib
p = pathlib.Path('$TEST_TMP/$STATE')
p.write_text(json.dumps({'targets': {'claude': {'installed': ['memory-pack']}}}, indent=2))
"
    run node "$CLI" plugin update --editor claude --all --dry-run
    [ "$status" -eq 0 ]
    case "$output" in
        *"unrecorded -> 1.0.0"*) ;;
        *) echo "expected the unrecorded-version transition, got: $output"; return 1 ;;
    esac
}

@test "ai-toolkit update --local leaves plugin packs alone" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    record_version memory-pack 0.9.0

    run bash -c "cd '$TEST_TMP' && node '$CLI' update --local --dry-run 2>&1"
    [ "$status" -eq 0 ]
    # Packs are global state; --local is project-local config only.
    run recorded_version memory-pack
    [ "$output" = "0.9.0" ]
}

@test "plugin.py update tolerates a corrupt plugins.json without crashing" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    printf 'not json' > "$TEST_TMP/$STATE"
    run python3 "$PLUGIN_PY" update --editor claude --all
    [ "$status" -eq 0 ]
}

@test "plugin status dispatches to a pack's own status.py generically" {
    # memory-pack has no status.py, so its output must be unchanged and the
    # generic path must not invent lines for packs that do not opt in.
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    run node "$CLI" plugin status
    [ "$status" -eq 0 ]
    case "$output" in
        *"memory-pack"*) ;;
        *) echo "expected memory-pack in status, got: $output"; return 1 ;;
    esac
    case "$output" in
        *"status unavailable"*) echo "generic dispatch must stay silent for packs without status.py"; return 1 ;;
        *) ;;
    esac
}
