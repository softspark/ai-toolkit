#!/usr/bin/env bats
# Tests for scripts/verify_rtk_binary.py, the Phase 1 silence verifier.
#
# The script decides whether a cross-built rtk artifact may ship, so its
# failure modes matter more than its happy path. It was committed with no
# coverage and its only caller is a manual-dispatch workflow, meaning nothing
# in `npm test` exercised it.
#
# A shell script standing in for the binary is enough: every assertion is about
# process behaviour, not machine code.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
VERIFY="$TOOLKIT_DIR/scripts/verify_rtk_binary.py"

setup() {
    TEST_TMP="$(mktemp -d)"
    # The triple this host can execute natively, taken from the script's own
    # table so the tests follow it rather than duplicating the mapping.
    NATIVE_TARGET="$(python3 -c "
import importlib.util as u, platform
s = u.spec_from_file_location('v', '$VERIFY'); m = u.module_from_spec(s); s.loader.exec_module(m)
targets = m.RUNNABLE_HERE.get((platform.system(), platform.machine()), set())
print(sorted(targets)[0] if targets else '')
")"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# A stand-in binary whose --version output is the first argument.
fake_rtk() {
    local path="$TEST_TMP/rtk"
    cat > "$path" <<EOF
#!/usr/bin/env bash
printf '%s\n' "$1"
EOF
    chmod +x "$path"
    printf '%s' "$path"
}

verdict_of() {
    python3 -c "
import json, sys
print(json.load(open('$1'))['verdict'])
"
}

@test "a binary that identifies as rtk with the expected version passes" {
    [ -n "$NATIVE_TARGET" ] || skip "no natively runnable target on this host"
    bin="$(fake_rtk 'rtk 0.44.0')"
    run python3 "$VERIFY" --binary "$bin" --target "$NATIVE_TARGET" \
        --upstream-tag v0.44.0 --out "$TEST_TMP/m.json"
    # Print the manifest on failure: a bare status assertion tells you nothing
    # about which of the four checks objected, which cost a CI round-trip once.
    [ "$status" -eq 0 ] || { cat "$TEST_TMP/m.json" 2>/dev/null; echo "$output"; return 1; }
    run verdict_of "$TEST_TMP/m.json"
    [ "$output" = "pass" ]
}

@test "a binary that does not identify as rtk fails" {
    [ -n "$NATIVE_TARGET" ] || skip "no natively runnable target on this host"
    bin="$(fake_rtk 'coreutils 9.4')"
    run python3 "$VERIFY" --binary "$bin" --target "$NATIVE_TARGET" \
        --upstream-tag v0.44.0 --out "$TEST_TMP/m.json"
    [ "$status" -eq 1 ]
    run verdict_of "$TEST_TMP/m.json"
    [ "$output" = "fail" ]
}

@test "a version that does not match the pinned tag fails" {
    [ -n "$NATIVE_TARGET" ] || skip "no natively runnable target on this host"
    bin="$(fake_rtk 'rtk 0.43.0')"
    run python3 "$VERIFY" --binary "$bin" --target "$NATIVE_TARGET" \
        --upstream-tag v0.44.0 --out "$TEST_TMP/m.json"
    [ "$status" -eq 1 ]
    run verdict_of "$TEST_TMP/m.json"
    [ "$output" = "fail" ]
}

@test "a leaked telemetry build variable fails the build gate" {
    [ -n "$NATIVE_TARGET" ] || skip "no natively runnable target on this host"
    bin="$(fake_rtk 'rtk 0.44.0')"
    run env RTK_TELEMETRY_URL=https://example.invalid python3 "$VERIFY" \
        --binary "$bin" --target "$NATIVE_TARGET" --upstream-tag v0.44.0 \
        --out "$TEST_TMP/m.json"
    [ "$status" -eq 1 ]
    run verdict_of "$TEST_TMP/m.json"
    [ "$output" = "fail" ]
}

@test "a target nobody can start here reports inconclusive, never pass" {
    bin="$(fake_rtk 'rtk 0.44.0')"
    # A triple no host in the table can execute and no emulator covers.
    run python3 "$VERIFY" --binary "$bin" --target "powerpc64-unknown-linux-gnu" \
        --upstream-tag v0.44.0 --out "$TEST_TMP/m.json"
    [ "$status" -eq 0 ]
    run verdict_of "$TEST_TMP/m.json"
    [ "$output" = "inconclusive" ]
}

@test "a binary writing telemetry state into the sandbox fails" {
    [ -n "$NATIVE_TARGET" ] || skip "no natively runnable target on this host"
    path="$TEST_TMP/rtk"
    cat > "$path" <<'EOF'
#!/usr/bin/env bash
mkdir -p "${XDG_DATA_HOME:-$HOME/.local/share}/rtk"
printf 'x' > "${XDG_DATA_HOME:-$HOME/.local/share}/rtk/telemetry-salt"
printf 'rtk 0.44.0\n'
EOF
    chmod +x "$path"
    run python3 "$VERIFY" --binary "$path" --target "$NATIVE_TARGET" \
        --upstream-tag v0.44.0 --out "$TEST_TMP/m.json"
    [ "$status" -eq 1 ]
    run python3 -c "
import json
d = json.load(open('$TEST_TMP/m.json'))
print(d['checks']['no_state']['pass'])
"
    [ "$output" = "False" ]
}

@test "the manifest records a fingerprint usable for drift detection" {
    [ -n "$NATIVE_TARGET" ] || skip "no natively runnable target on this host"
    bin="$(fake_rtk 'rtk 0.44.0')"
    run python3 "$VERIFY" --binary "$bin" --target "$NATIVE_TARGET" \
        --upstream-tag v0.44.0 --out "$TEST_TMP/m.json"
    [ "$status" -eq 0 ] || { cat "$TEST_TMP/m.json" 2>/dev/null; echo "$output"; return 1; }
    run python3 -c "
import json, re, sys
fp = json.load(open('$TEST_TMP/m.json'))['fingerprint']
ok = (re.fullmatch(r'[0-9a-f]{64}', fp['sha256'])
      and fp['size_bytes'] > 0
      and re.fullmatch(r'[0-9a-f]{64}', fp['strings_digest'])
      and isinstance(fp['tls_markers_present'], list))
sys.exit(0 if ok else 1)
"
    [ "$status" -eq 0 ]
}

@test "a missing binary is reported rather than crashing" {
    run python3 "$VERIFY" --binary "$TEST_TMP/absent" --target "$NATIVE_TARGET" \
        --upstream-tag v0.44.0
    [ "$status" -eq 2 ]
}
