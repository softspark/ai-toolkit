#!/usr/bin/env bats
# Tests for rtk-pack: manifest, install script, and the PreToolUse hook.
#
# Every test is offline. The install path is exercised against a file:// mirror
# via RTK_PACK_RELEASE_BASE_URL, so nothing here depends on GitHub being
# reachable or on the release still existing.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
PACK_DIR="$TOOLKIT_DIR/app/plugins/rtk-pack"
INIT="$PACK_DIR/scripts/init.py"
HOOK="$PACK_DIR/hooks/rewrite.sh"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    export AI_TOOLKIT_DATA_DIR="$TEST_TMP/.softspark/ai-toolkit"
    MIRROR="$TEST_TMP/mirror"
    mkdir -p "$MIRROR"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# Build a one-entry tar.gz mirror asset plus a manifest pinned to its digest.
# Returns the pack copy path on stdout.
make_mirror_pack() {
    local payload="${1:-#!/bin/sh
echo \"rtk 0.44.0\"}"
    local staging="$TEST_TMP/staging"
    mkdir -p "$staging"
    printf '%s\n' "$payload" > "$staging/rtk"
    chmod +x "$staging/rtk"

    local pack="$TEST_TMP/pack"
    rm -rf "$pack"
    cp -r "$PACK_DIR" "$pack"

    python3 - "$staging" "$pack" "$MIRROR" <<'PY'
import hashlib, json, pathlib, sys, tarfile
staging, pack, mirror = (pathlib.Path(a) for a in sys.argv[1:4])
manifest_path = pack / "plugin.json"
manifest = json.loads(manifest_path.read_text())
for key, asset in manifest["binary"]["assets"].items():
    name = asset["file"]
    if name.endswith(".zip"):
        import zipfile
        target = mirror / name
        with zipfile.ZipFile(target, "w") as zf:
            zf.write(staging / "rtk", arcname=asset["member"])
    else:
        target = mirror / name
        with tarfile.open(target, "w:gz") as tf:
            tf.add(staging / "rtk", arcname=asset["member"])
    asset["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
manifest_path.write_text(json.dumps(manifest, indent=2))
PY
    printf '%s' "$pack"
}

# --- manifest -------------------------------------------------------------

@test "rtk-pack manifest passes the shared plugin schema" {
    run python3 -c "
import sys, json, pathlib
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from plugin_schema import validate_manifest
d = json.load(open('$PACK_DIR/plugin.json'))
errs = validate_manifest(d, pathlib.Path('$PACK_DIR'))
print('ERRORS:' + repr(errs))
sys.exit(1 if errs else 0)
"
    [ "$status" -eq 0 ]
}

@test "rtk-pack declares its hook event so plugin.py can resolve it" {
    # resolve_hook_event falls back to a 9-entry filename map that does not
    # know rewrite.sh; without hook_events the hook is silently skipped.
    run python3 -c "
import sys, json
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from plugin_schema import resolve_hook_event
d = json.load(open('$PACK_DIR/plugin.json'))
event = resolve_hook_event('rewrite.sh', d)
print(event)
sys.exit(0 if event == 'PreToolUse' else 1)
"
    [ "$status" -eq 0 ]
}

@test "every declared asset is reachable from some supported host" {
    run python3 -c "
import json, itertools, sys
d = json.load(open('$PACK_DIR/plugin.json'))
declared = set(d['binary']['assets'])
reachable = set()
for system in ('darwin', 'linux', 'windows'):
    for machine in ('x86_64', 'amd64', 'arm64', 'aarch64'):
        arch = {'x86_64':'x86_64','amd64':'x86_64','arm64':'arm64' if system=='darwin' else 'aarch64','aarch64':'arm64' if system=='darwin' else 'aarch64'}[machine]
        reachable.add(f'{system}-{arch}')
orphans = declared - reachable
print('ORPHANS:' + repr(orphans))
sys.exit(1 if orphans else 0)
"
    [ "$status" -eq 0 ]
}

@test "every asset entry carries a 64-char sha256 and a member name" {
    run python3 -c "
import json, re, sys
d = json.load(open('$PACK_DIR/plugin.json'))
bad = [k for k, a in d['binary']['assets'].items()
       if not re.fullmatch(r'[0-9a-f]{64}', a.get('sha256','')) or not a.get('member')]
print('BAD:' + repr(bad))
sys.exit(1 if bad else 0)
"
    [ "$status" -eq 0 ]
}

# --- install --------------------------------------------------------------

@test "install fetches from a mirror, verifies the digest, and installs" {
    pack="$(make_mirror_pack)"
    run env RTK_PACK_RELEASE_BASE_URL="file://$MIRROR" python3 "$pack/scripts/init.py"
    [ "$status" -eq 0 ]
    [ -x "$AI_TOOLKIT_DATA_DIR/plugin-scripts/rtk-pack/bin/rtk" ] || \
        [ -x "$AI_TOOLKIT_DATA_DIR/plugin-scripts/rtk-pack/bin/rtk.exe" ]
    [ -f "$AI_TOOLKIT_DATA_DIR/plugin-scripts/rtk-pack/version.json" ]
}

@test "install is idempotent and does not refetch when the digest matches" {
    pack="$(make_mirror_pack)"
    run env RTK_PACK_RELEASE_BASE_URL="file://$MIRROR" python3 "$pack/scripts/init.py"
    [ "$status" -eq 0 ]

    # Remove the mirror: a second run that still succeeds cannot have fetched.
    rm -rf "$MIRROR"
    run env RTK_PACK_RELEASE_BASE_URL="file://$MIRROR" python3 "$pack/scripts/init.py"
    [ "$status" -eq 0 ]
    case "$output" in
        *"already installed"*) ;;
        *) echo "expected an already-installed message, got: $output"; return 1 ;;
    esac
}

@test "a digest mismatch aborts and installs nothing" {
    pack="$(make_mirror_pack)"
    python3 - "$pack/plugin.json" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text())
for asset in d["binary"]["assets"].values():
    asset["sha256"] = "0" * 64
p.write_text(json.dumps(d, indent=2))
PY
    run env RTK_PACK_RELEASE_BASE_URL="file://$MIRROR" python3 "$pack/scripts/init.py"
    [ "$status" -ne 0 ]
    case "$output" in
        *"digest mismatch"*) ;;
        *) echo "expected a digest mismatch message, got: $output"; return 1 ;;
    esac
    # find on a missing directory writes to stderr, which bats folds into
    # $output, so count files explicitly instead of asserting emptiness.
    run bash -c "find '$AI_TOOLKIT_DATA_DIR' -type f 2>/dev/null | wc -l | tr -d ' '"
    [ "$output" = "0" ]
}

@test "an unreachable release degrades instead of crashing" {
    run env RTK_PACK_RELEASE_BASE_URL="file://$TEST_TMP/does-not-exist" python3 "$INIT"
    [ "$status" -ne 0 ]
    case "$output" in
        *"inert"*) ;;
        *) echo "expected the inert-degradation message, got: $output"; return 1 ;;
    esac
    # find on a missing directory writes to stderr, which bats folds into
    # $output, so count files explicitly instead of asserting emptiness.
    run bash -c "find '$AI_TOOLKIT_DATA_DIR' -type f 2>/dev/null | wc -l | tr -d ' '"
    [ "$output" = "0" ]
}

@test "an archive holding more than one entry is refused" {
    pack="$(make_mirror_pack)"
    # Repack one asset with a second member; the manifest digest is updated so
    # the failure can only come from the layout check, not the digest check.
    run python3 - "$pack/plugin.json" "$MIRROR" <<'PY'
import hashlib, json, pathlib, sys, tarfile, tempfile
manifest_path, mirror = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
d = json.loads(manifest_path.read_text())
for key, asset in d["binary"]["assets"].items():
    if asset["file"].endswith(".tar.gz"):
        target = mirror / asset["file"]
        with tempfile.TemporaryDirectory() as tmp:
            extra = pathlib.Path(tmp) / "EXTRA"
            extra.write_text("x")
            member = pathlib.Path(tmp) / asset["member"]
            member.write_text("#!/bin/sh\necho hi\n")
            with tarfile.open(target, "w:gz") as tf:
                tf.add(member, arcname=asset["member"])
                tf.add(extra, arcname="EXTRA")
        asset["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
manifest_path.write_text(json.dumps(d, indent=2))
PY
    [ "$status" -eq 0 ]

    run env RTK_PACK_RELEASE_BASE_URL="file://$MIRROR" python3 "$pack/scripts/init.py"
    # Windows hosts get the zip, which this test does not repack; skip there.
    if [ "$(uname -s)" != "Darwin" ] && [ "$(uname -s)" != "Linux" ]; then
        skip "tar.gz assets are not selected on this host"
    fi
    [ "$status" -ne 0 ]
    case "$output" in
        *"expected exactly"*) ;;
        *) echo "expected the single-entry refusal, got: $output"; return 1 ;;
    esac
}

# --- hook -----------------------------------------------------------------

@test "hook is executable and uses a bash shebang" {
    [ -x "$HOOK" ]
    run head -1 "$HOOK"
    [ "$output" = "#!/usr/bin/env bash" ]
}

@test "hook stays silent for a non-Bash tool" {
    # The pack cannot declare a matcher, so plugin.py registers it against
    # every tool; the gate lives in the hook itself.
    run bash -c "printf '%s' '{\"tool_name\":\"Read\",\"tool_input\":{\"file_path\":\"/etc/hosts\"}}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "hook stays silent when no binary is installed" {
    run bash -c "printf '%s' '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"git status\"}}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "hook stays silent on empty stdin" {
    run bash -c "printf '' | bash '$HOOK'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "hook forwards a valid rewrite from the binary" {
    # Without jq the hook deliberately stays out of the way, so a test that
    # asserts a rewrite has nothing to assert. Skip rather than fail.
    command -v jq >/dev/null 2>&1 || skip "jq not installed"
    mkdir -p "$HOME/.softspark/ai-toolkit/plugin-scripts/rtk-pack/bin"
    cat > "$HOME/.softspark/ai-toolkit/plugin-scripts/rtk-pack/bin/rtk" <<'EOF'
#!/usr/bin/env bash
cat > /dev/null
printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","updatedInput":{"command":"rtk git status"}}}'
EOF
    chmod +x "$HOME/.softspark/ai-toolkit/plugin-scripts/rtk-pack/bin/rtk"

    run bash -c "printf '%s' '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"git status\"}}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
    case "$output" in
        *"rtk git status"*) ;;
        *) echo "expected the rewritten command, got: $output"; return 1 ;;
    esac
}

@test "hook drops non-JSON output from the binary" {
    mkdir -p "$HOME/.softspark/ai-toolkit/plugin-scripts/rtk-pack/bin"
    cat > "$HOME/.softspark/ai-toolkit/plugin-scripts/rtk-pack/bin/rtk" <<'EOF'
#!/usr/bin/env bash
cat > /dev/null
printf 'not json at all\n'
EOF
    chmod +x "$HOME/.softspark/ai-toolkit/plugin-scripts/rtk-pack/bin/rtk"

    run bash -c "printf '%s' '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"git status\"}}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "hook drops output when the binary exits non-zero" {
    mkdir -p "$HOME/.softspark/ai-toolkit/plugin-scripts/rtk-pack/bin"
    cat > "$HOME/.softspark/ai-toolkit/plugin-scripts/rtk-pack/bin/rtk" <<'EOF'
#!/usr/bin/env bash
cat > /dev/null
printf '%s\n' '{"hookSpecificOutput":{"updatedInput":{"command":"rm -rf /"}}}'
exit 3
EOF
    chmod +x "$HOME/.softspark/ai-toolkit/plugin-scripts/rtk-pack/bin/rtk"

    run bash -c "printf '%s' '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"git status\"}}' | bash '$HOOK'"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# --- status ---------------------------------------------------------------

@test "status reports the inert case loudly when no binary is installed" {
    run env AI_TOOLKIT_DATA_DIR="$AI_TOOLKIT_DATA_DIR" python3 "$PACK_DIR/scripts/status.py"
    [ "$status" -eq 0 ]
    case "$output" in
        *"MISSING"*"inert"*) ;;
        *) echo "expected a loud missing-binary report, got: $output"; return 1 ;;
    esac
}

@test "status reports version, digest and hook wiring once installed" {
    pack="$(make_mirror_pack)"
    run env RTK_PACK_RELEASE_BASE_URL="file://$MIRROR" python3 "$pack/scripts/init.py"
    [ "$status" -eq 0 ]

    run env AI_TOOLKIT_DATA_DIR="$AI_TOOLKIT_DATA_DIR" python3 "$PACK_DIR/scripts/status.py"
    [ "$status" -eq 0 ]
    case "$output" in
        *"upstream v0.44.0"*) ;;
        *) echo "expected the upstream version, got: $output"; return 1 ;;
    esac
    case "$output" in
        *"binary sha256"*) ;;
        *) echo "expected a binary digest line, got: $output"; return 1 ;;
    esac
    case "$output" in
        *"hook registered in settings.json"*) ;;
        *) echo "expected a hook wiring line, got: $output"; return 1 ;;
    esac
}

@test "status never fails even when the install record is gone" {
    pack="$(make_mirror_pack)"
    env RTK_PACK_RELEASE_BASE_URL="file://$MIRROR" python3 "$pack/scripts/init.py" >/dev/null 2>&1
    rm -f "$AI_TOOLKIT_DATA_DIR/plugin-scripts/rtk-pack/version.json"

    run env AI_TOOLKIT_DATA_DIR="$AI_TOOLKIT_DATA_DIR" python3 "$PACK_DIR/scripts/status.py"
    [ "$status" -eq 0 ]
    case "$output" in
        *"install record: MISSING"*) ;;
        *) echo "expected a missing-record report, got: $output"; return 1 ;;
    esac
}
