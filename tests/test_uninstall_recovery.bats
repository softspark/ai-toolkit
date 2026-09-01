#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Global uninstall coverage for leftover v4.16.x output-filter recovery data.
# The filter itself was removed; these fixtures reproduce the on-disk layout
# those releases created, so uninstall keeps reclaiming it.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_ROOT="$BATS_TEST_TMPDIR/root"
    TEST_HOME="$TEST_ROOT/home"
    TEST_PROJECT="$TEST_ROOT/project"
    unset CODEX_HOME COPILOT_HOME
    mkdir -p "$TEST_HOME" "$TEST_PROJECT"
    local fake_pnpm_bin="$TEST_ROOT/fake-pnpm-bin"
    mkdir -p "$fake_pnpm_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_pnpm_bin/pnpm"
    chmod +x "$fake_pnpm_bin/pnpm"
    PATH="$fake_pnpm_bin:$PATH"
    export PATH
}

profile_fingerprint() {
    python3 - "$1" <<'PY'
import hashlib
import os
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1])
if not root.exists() and not root.is_symlink():
    print("ABSENT")
    raise SystemExit
pending = [root]
records = []
while pending:
    path = pending.pop()
    relative = "." if path == root else path.relative_to(root).as_posix()
    metadata = path.lstat()
    mode = stat.S_IFMT(metadata.st_mode)
    if stat.S_ISLNK(mode):
        records.append((relative, "link", os.readlink(path)))
    elif stat.S_ISDIR(mode):
        records.append((relative, "dir", ""))
        pending.extend(sorted(path.iterdir(), reverse=True))
    elif stat.S_ISREG(mode):
        records.append(
            (relative, "file", hashlib.sha256(path.read_bytes()).hexdigest())
        )
    else:
        records.append((relative, "other", oct(mode)))
for record in sorted(records):
    print("\t".join(record))
PY
}

create_recovery_session() {
    local repository="$1"
    local session_identifier="$2"
    mkdir -p "$repository"
    chmod 700 "$repository"
    python3 - "$repository" "$session_identifier" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

repository = Path(sys.argv[1])
session_identifier = sys.argv[2]

session_key = hashlib.sha256(session_identifier.encode()).hexdigest()[:32]
session_directory = repository / "output-filter" / session_key
session_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
(repository / "output-filter").chmod(0o700)
session_directory.chmod(0o700)

artifacts = {
    "a" * 32 + ".json": json.dumps({"stdout": "remove me"}),
    ".circuit-state.json": json.dumps({"failures": 2}),
    ".telemetry.jsonl": json.dumps({"outcome": "observed"}) + "\n",
}
for name, payload in artifacts.items():
    path = session_directory / name
    path.write_text(payload, encoding="utf-8")
    path.chmod(0o600)

print(session_directory)
PY
}

@test "global uninstall discovers and removes recovery as the sole component" {
    local repository="$TEST_HOME/.softspark/ai-toolkit/sessions/repo-a"
    local session_directory
    session_directory="$(create_recovery_session "$repository" "sole-component")"

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --global --yes

    [ "$status" -eq 0 ]
    [[ "$output" == *"Recovery: sessions/*/output-filter (3 owned artifacts)"* ]]
    [[ "$output" == *"Removed: 3 output-filter recovery file(s)"* ]]
    [ ! -e "$session_directory/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json" ]
    [ ! -e "$session_directory/.circuit-state.json" ]
    [ ! -e "$session_directory/.telemetry.jsonl" ]
    [ ! -d "$repository/output-filter" ]
}

@test "global uninstall preserves foreign files in a recovery session" {
    local repository="$TEST_HOME/.softspark/ai-toolkit/sessions/repo-a"
    local session_directory
    session_directory="$(create_recovery_session "$repository" "foreign-file")"
    printf '%s\n' "keep user data" > "$session_directory/keep.txt"

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --global --yes

    [ "$status" -eq 0 ]
    [ ! -e "$session_directory/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json" ]
    [ ! -e "$session_directory/.circuit-state.json" ]
    [ ! -e "$session_directory/.telemetry.jsonl" ]
    [ -f "$session_directory/keep.txt" ]
    [ "$(cat "$session_directory/keep.txt")" = "keep user data" ]
}

@test "foreign-only recovery namespace is ignored on repeated uninstall" {
    local repository="$TEST_HOME/.softspark/ai-toolkit/sessions/repo-a"
    local output_root="$repository/output-filter"
    local session_directory="$output_root/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    mkdir -p "$session_directory"
    chmod 700 "$output_root" "$session_directory"
    printf '%s\n' "keep user data" > "$session_directory/keep.txt"

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --global --yes
    [ "$status" -eq 0 ]
    [[ "$output" == *"No toolkit components found. Nothing to remove."* ]]
    [ "$(cat "$session_directory/keep.txt")" = "keep user data" ]

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --global --yes
    [ "$status" -eq 0 ]
    [[ "$output" == *"No toolkit components found. Nothing to remove."* ]]
    [ "$(cat "$session_directory/keep.txt")" = "keep user data" ]
}

@test "local uninstall never touches the global recovery tree" {
    local repository="$TEST_HOME/.softspark/ai-toolkit/sessions/repo-a"
    local session_directory
    session_directory="$(create_recovery_session "$repository" "local-scope")"
    mkdir -p "$TEST_PROJECT/.codex/agents"
    printf '%s\n' "# ai-toolkit-managed: codex-agent" > \
        "$TEST_PROJECT/.codex/agents/ai-toolkit-managed.toml"

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --local --yes --target "$TEST_PROJECT"

    [ "$status" -eq 0 ]
    [ ! -e "$TEST_PROJECT/.codex/agents/ai-toolkit-managed.toml" ]
    [ -e "$session_directory/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json" ]
    [ -e "$session_directory/.circuit-state.json" ]
    [ -e "$session_directory/.telemetry.jsonl" ]
}

@test "unsafe output-filter symlink blocks before other global surfaces change" {
    local sessions_root="$TEST_HOME/.softspark/ai-toolkit/sessions"
    local repository="$sessions_root/repo-a"
    local external="$TEST_ROOT/external-output-filter"
    local managed_agent="$TEST_HOME/.codex/agents/ai-toolkit-managed.toml"
    mkdir -p "$repository" "$external" "$(dirname "$managed_agent")"
    chmod 700 "$repository"
    printf '%s\n' "outside user data" > "$external/keep.txt"
    ln -s "$external" "$repository/output-filter"
    printf '%s\n' "# ai-toolkit-managed: codex-agent" > "$managed_agent"

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --global --yes

    [ "$status" -ne 0 ]
    [[ "$output" != *"rolled back"* ]]
    [ -f "$managed_agent" ]
    [ -L "$repository/output-filter" ]
    [ "$(cat "$external/keep.txt")" = "outside user data" ]
}

@test "owned-name symlink blocks all recovery deletion before surfaces change" {
    local sessions_root="$TEST_HOME/.softspark/ai-toolkit/sessions"
    local first_repository="$sessions_root/a-repo"
    local second_repository="$sessions_root/z-repo"
    local first_session
    local second_session
    local outside="$TEST_ROOT/outside.json"
    local managed_agent="$TEST_HOME/.codex/agents/ai-toolkit-managed.toml"
    first_session="$(create_recovery_session "$first_repository" "first")"
    second_session="$(create_recovery_session "$second_repository" "second")"
    printf '%s\n' "outside user data" > "$outside"
    ln -s "$outside" "$second_session/ffffffffffffffffffffffffffffffff.json"
    mkdir -p "$(dirname "$managed_agent")"
    printf '%s\n' "# ai-toolkit-managed: codex-agent" > "$managed_agent"

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --global --yes

    [ "$status" -ne 0 ]
    [[ "$output" != *"rolled back"* ]]
    [ -f "$managed_agent" ]
    [ -e "$first_session/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json" ]
    [ -e "$first_session/.circuit-state.json" ]
    [ -e "$first_session/.telemetry.jsonl" ]
    [ -e "$second_session/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json" ]
    [ -L "$second_session/ffffffffffffffffffffffffffffffff.json" ]
    [ "$(cat "$outside")" = "outside user data" ]
}

@test "post-preflight recovery I/O failure rolls back every other surface" {
    local repository="$TEST_HOME/.softspark/ai-toolkit/sessions/repo-a"
    local session_directory
    local managed_agent="$TEST_HOME/.codex/agents/ai-toolkit-managed.toml"
    session_directory="$(create_recovery_session "$repository" "io-failure")"
    mkdir -p "$(dirname "$managed_agent")"
    printf '%s\n' "# ai-toolkit-managed: codex-agent" > "$managed_agent"

    python3 - "$TOOLKIT_DIR" "$TEST_HOME" "$managed_agent" \
        "$session_directory" <<'PY'
import contextlib
import importlib.util
import io
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
managed_agent = Path(sys.argv[3])
session_directory = Path(sys.argv[4])
sys.path.insert(0, str(toolkit / "scripts"))
spec = importlib.util.spec_from_file_location(
    "uninstall_recovery_io_test",
    toolkit / "scripts" / "uninstall.py",
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

real_cleanup = module.clean_owned_recovery_tree

def fail_after_cleanup(sessions_root):
    real_cleanup(sessions_root)
    raise OSError("injected post-preflight failure")

module.clean_owned_recovery_tree = fail_after_cleanup
stderr = io.StringIO()
with contextlib.redirect_stderr(stderr):
    try:
        module.main(["--global", "--yes", "--target", str(home)])
    except SystemExit as error:
        assert error.code == 1, error.code
    else:
        raise AssertionError("uninstall unexpectedly succeeded")

message = stderr.getvalue()
assert "rolled back" in message, message
assert "may have left recovery cleanup partial" in message, message
assert managed_agent.is_file(), "non-recovery surface was not rolled back"
assert not (
    session_directory / ("a" * 32 + ".json")
).exists(), "test did not simulate partial recovery cleanup"
PY
}

@test "DSH update state failure restores the owned preset and shared state bytes" {
    local dsh_home="$TEST_ROOT/dsh-home"
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$dsh_home" "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"

    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
    [ "$status" -eq 0 ]
    local preset="$dsh_home/.agent-presets/softspark-orchestrator/preset.md"
    local state="$TEST_HOME/.softspark/ai-toolkit/state.json"
    local before_preset before_state
    before_preset="$(shasum "$preset")"
    before_state="$(shasum "$state")"
    printf '%s\n' '{"preset_content":"new package preset\n"}' > \
        "$dsh_home/fake-control.json"

    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

def fail_state(**_kwargs):
    raise OSError("injected DSH state failure")

dsh.record_dsh_profile = fail_state
raise SystemExit(dsh.main(["update", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"injected DSH state failure"* ]]
    [ "$(shasum "$preset")" = "$before_preset" ]
    [ "$(shasum "$state")" = "$before_state" ]
    [ ! -e "$dsh_home/.agent-presets/.softspark-orchestrator.ai-toolkit-new" ]
    [ ! -e "$dsh_home/.agent-presets/.softspark-orchestrator.ai-toolkit-backup" ]
}

@test "DSH install staging cleanup failure preserves visible recovery artifact" {
    local dsh_home="$TEST_ROOT/dsh-home"
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$dsh_home" "$fake_bin" "$TEST_HOME/.softspark/ai-toolkit"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    printf '%s\n' '{"installed_version":"4.29.2","installed_modules":["core"]}' > \
        "$TEST_HOME/.softspark/ai-toolkit/state.json"
    local state="$TEST_HOME/.softspark/ai-toolkit/state.json"
    local before_state
    before_state="$(shasum "$state")"

    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

real_cleanup = dsh._cleanup_owned_entries

def refuse_staging_cleanup(owned):
    staging = [
        entry.path for entry in owned
        if ".ai-toolkit-new" in entry.path.as_posix()
    ]
    if staging:
        return sorted(set(staging), key=str)
    return real_cleanup(owned)

dsh._cleanup_owned_entries = refuse_staging_cleanup
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"Recovery required"* ]]
    local artifact_real
    artifact_real="$(cd "$dsh_home/.agent-presets" && pwd -P)/.softspark-orchestrator.ai-toolkit-new"
    [[ "$output" == *"'$artifact_real'"* ]]
    [ -d "$artifact_real" ]
    [ ! -e "$dsh_home/.agent-presets/softspark-orchestrator" ]
    [ "$(shasum "$state")" = "$before_state" ]

    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh doctor --profile web
    [ "$status" -ne 0 ]
    [[ "$output" == *"Recovery artifact: '$artifact_real'"* ]]
    [[ "$output" == *"Recovery needed: yes"* ]]
}

@test "DSH update backup cleanup failure restores preset packages and state" {
    local dsh_home="$TEST_ROOT/dsh-home"
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$dsh_home" "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
    [ "$status" -eq 0 ]
    local preset="$dsh_home/.agent-presets/softspark-orchestrator/preset.md"
    local source="$dsh_home/profiles/web/node_modules/@softspark/dsh-orchestrator/agent-presets/softspark-orchestrator/preset.md"
    local state="$TEST_HOME/.softspark/ai-toolkit/state.json"
    local before_preset before_source before_state
    before_preset="$(shasum "$preset")"
    before_source="$(shasum "$source")"
    before_state="$(shasum "$state")"
    printf '%s\n' '{"preset_content_once":"new package preset\n"}' > \
        "$dsh_home/fake-control.json"

    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

real_cleanup = dsh._cleanup_owned_entries
failed = False

def fail_backup_once(entries):
    global failed
    is_backup = any(
        ".ai-toolkit-backup." in str(entry.path) for entry in entries
    )
    if is_backup and not failed:
        failed = True
        raise OSError("injected backup cleanup failure")
    return real_cleanup(entries)

dsh._cleanup_owned_entries = fail_backup_once
raise SystemExit(dsh.main(["update", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [ "$(shasum "$preset")" = "$before_preset" ]
    [ "$(shasum "$source")" = "$before_source" ]
    [ "$(shasum "$state")" = "$before_state" ]
    [ ! -e "$dsh_home/.agent-presets/.softspark-orchestrator.ai-toolkit-new" ]
    [ -z "$(find "$dsh_home/.agent-presets" -mindepth 1 -maxdepth 1 \
        -name '.softspark-orchestrator.ai-toolkit-backup.*' -print -quit)" ]
}

@test "DSH KeyboardInterrupt at update boundaries restores or preserves exact bytes" {
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    for boundary in first_add second_add replacement state cleanup_before cleanup_after; do
        local case_root="$TEST_ROOT/update-$boundary"
        local case_home="$case_root/home"
        local dsh_home="$case_root/dsh"
        mkdir -p "$case_home" "$dsh_home"
        HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
        [ "$status" -eq 0 ]
        local preset="$dsh_home/.agent-presets/softspark-orchestrator/preset.md"
        local source="$dsh_home/profiles/web/node_modules/@softspark/dsh-orchestrator/agent-presets/softspark-orchestrator/preset.md"
        local state="$case_home/.softspark/ai-toolkit/state.json"
        local manifest="$dsh_home/profiles/web/package.json"
        local before_preset before_source before_state before_manifest
        before_preset="$(shasum "$preset")"
        before_source="$(shasum "$source")"
        before_state="$(shasum "$state")"
        before_manifest="$(shasum "$manifest")"
        if [ "$boundary" != first_add ]; then
            printf '%s\n' '{"preset_content_once":"new package preset\n"}' > \
                "$dsh_home/fake-control.json"
        fi

        HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            run python3 - "$TOOLKIT_DIR" "$boundary" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
boundary = sys.argv[2]
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

if boundary in {"first_add", "second_add"}:
    real = dsh._run
    target = (
        "@softspark/dsh-codex@1.0.0"
        if boundary == "first_add"
        else "@softspark/dsh-orchestrator@1.0.1"
    )

    def injected(argv, *, dsh_home):
        result = real(argv, dsh_home=dsh_home)
        if "add" in argv and target in argv:
            raise KeyboardInterrupt
        return result

    dsh._run = injected
elif boundary == "replacement":
    real = dsh._replace_owned_preset

    def injected(*args, **kwargs):
        real(*args, **kwargs)
        raise KeyboardInterrupt

    dsh._replace_owned_preset = injected
elif boundary == "state":
    real = dsh.record_dsh_profile

    def injected(**kwargs):
        real(**kwargs)
        raise KeyboardInterrupt

    dsh.record_dsh_profile = injected
else:
    real = dsh._cleanup_owned_entries

    def injected(entries):
        is_backup = any(
            ".ai-toolkit-backup." in str(entry.path) for entry in entries
        )
        if is_backup:
            if boundary == "cleanup_before":
                raise KeyboardInterrupt
            result = real(entries)
            raise KeyboardInterrupt
        return real(entries)

    dsh._cleanup_owned_entries = injected

raise SystemExit(dsh.main(["update", "--profile", "web"]))
PY

        [ "$status" -ne 0 ]
        [[ "$output" == *"interrupted"* ]]
        [[ "$output" != *"Traceback"* ]]
        [ "$(shasum "$preset")" = "$before_preset" ] || {
            echo "preset mismatch at update boundary: $boundary"
            false
        }
        if [ "$boundary" = second_add ]; then
            [ "$(shasum "$source")" != "$before_source" ]
            [[ "$output" == *"run 'ai-toolkit dsh doctor --profile web'"* ]]
        else
            [ "$(shasum "$source")" = "$before_source" ]
        fi
        [ "$(shasum "$state")" = "$before_state" ]
        if [ "$boundary" != second_add ]; then
            [ "$(shasum "$manifest")" = "$before_manifest" ]
        fi
        [ ! -e "$dsh_home/.agent-presets/.softspark-orchestrator.ai-toolkit-new" ]
        [ -z "$(find "$dsh_home/.agent-presets" -mindepth 1 -maxdepth 1 \
            -name '.softspark-orchestrator.ai-toolkit-backup.*' -print -quit)" ] || {
            echo "backup recovery survived update boundary: $boundary"
            find "$dsh_home/.agent-presets" -mindepth 1 -maxdepth 2 -print
            false
        }
    done
}

@test "DSH late update failure retains owned bytes and reports package-source recovery" {
    local dsh_home="$TEST_ROOT/dsh-home"
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$dsh_home" "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
    [ "$status" -eq 0 ]
    local preset="$dsh_home/.agent-presets/softspark-orchestrator/preset.md"
    local state="$TEST_HOME/.softspark/ai-toolkit/state.json"
    local before_preset before_state
    before_preset="$(shasum "$preset")"
    before_state="$(shasum "$state")"
    cat > "$dsh_home/fake-control.json" <<'JSON'
{
  "preset_content": "mutated package source\n",
  "fail_after": "add:@softspark/dsh-orchestrator"
}
JSON
    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh update --profile web

    [ "$status" -ne 0 ]
    [[ "$output" == *"Recovery required"* ]]
    [[ "$output" == *"@softspark/dsh-orchestrator@1.0.1"* ]]
    [ "$(shasum "$preset")" = "$before_preset" ]
    [ "$(shasum "$state")" = "$before_state" ]

    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh doctor --profile web
    [ "$status" -ne 0 ]
    [[ "$output" == *"Preset source: hash drift"* ]]
    [[ "$output" == *"Recovery needed: yes"* ]]
}

@test "DSH uninstall package failure restores prior packages preset and state" {
    local dsh_home="$TEST_ROOT/dsh-home"
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$dsh_home" "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
    [ "$status" -eq 0 ]
    local preset="$dsh_home/.agent-presets/softspark-orchestrator/preset.md"
    local state="$TEST_HOME/.softspark/ai-toolkit/state.json"
    local before_preset before_state
    before_preset="$(shasum "$preset")"
    before_state="$(shasum "$state")"
    printf '%s\n' '{"fail_before":"remove:@softspark/dsh-codex"}' > \
        "$dsh_home/fake-control.json"

    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh uninstall --profile web --yes

    [ "$status" -ne 0 ]
    [[ "$output" == *"DSH command failed with exit status 70"* ]]
    [ "$(shasum "$preset")" = "$before_preset" ]
    [ "$(shasum "$state")" = "$before_state" ]
    python3 - "$dsh_home" <<'PY'
import json
import sys
from pathlib import Path

home = Path(sys.argv[1])
manifest = json.loads((home / "profiles/web/package.json").read_text())
assert manifest["dependencies"] == {
    "@softspark/dsh-codex": "1.0.0",
    "@softspark/dsh-orchestrator": "1.0.1",
}, manifest
PY
}

@test "DSH update and uninstall package failures restore exact pre-existing profile bytes" {
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    for operation in update uninstall; do
        local case_root="$TEST_ROOT/profile-prestate-$operation"
        local case_home="$case_root/home"
        local dsh_home="$case_root/dsh"
        mkdir -p "$case_home" "$dsh_home"
        HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
        [ "$status" -eq 0 ]
        python3 - "$dsh_home/profiles/web" <<'PY'
import json
import sys
from pathlib import Path

profile = Path(sys.argv[1])
manifest = profile / "package.json"
document = json.loads(manifest.read_text())
document["userMetadata"] = {"preserve": [True, None, 7]}
manifest.write_text(json.dumps(document, separators=(",", ":")) + "\n")
(profile / "user-config.json").write_text('{"keep":true}\n')
(profile / "node_modules" / "unrelated").mkdir()
(profile / "node_modules" / "unrelated" / "keep.txt").write_text("keep user\n")
for package in ("dsh-codex", "dsh-orchestrator"):
    root = profile / "node_modules" / "@softspark" / package
    (root / "pre-existing-user-note.txt").write_text(f"keep {package}\n")
PY
        local before_profile before_state before_preset
        before_profile="$(profile_fingerprint "$dsh_home/profiles/web")"
        before_state="$(shasum "$case_home/.softspark/ai-toolkit/state.json")"
        before_preset="$(profile_fingerprint "$dsh_home/.agent-presets/softspark-orchestrator")"
        if [ "$operation" = update ]; then
            printf '%s\n' '{"fail_before_once":"add:@softspark/dsh-orchestrator"}' > \
                "$dsh_home/fake-control.json"
            arguments=(update --profile web)
        else
            printf '%s\n' '{"fail_before_once":"remove:@softspark/dsh-codex"}' > \
                "$dsh_home/fake-control.json"
            arguments=(uninstall --profile web --yes)
        fi

        HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh "${arguments[@]}"

        [ "$status" -ne 0 ]
        [ "$(profile_fingerprint "$dsh_home/profiles/web")" = "$before_profile" ]
        [ "$(shasum "$case_home/.softspark/ai-toolkit/state.json")" = "$before_state" ]
        [ "$(profile_fingerprint "$dsh_home/.agent-presets/softspark-orchestrator")" = \
            "$before_preset" ]
    done
}

@test "DSH package rollback preserves a concurrent manifest and marks recovery" {
    local dsh_home="$TEST_ROOT/concurrent-manifest-dsh"
    local fake_bin="$TEST_ROOT/concurrent-manifest-bin"
    mkdir -p "$dsh_home" "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
    [ "$status" -eq 0 ]
    printf '%s\n' '{"fail_before_once":"add:@softspark/dsh-orchestrator"}' > \
        "$dsh_home/fake-control.json"
    local manifest="$dsh_home/profiles/web/package.json"
    local marker_pattern='.softspark-orchestrator.ai-toolkit-package.*'

    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run python3 - "$TOOLKIT_DIR" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

real_restore = dsh._restore_packages

def inject_concurrent_manifest(**kwargs):
    result = real_restore(**kwargs)
    manifest = kwargs["dsh_home"] / "profiles" / kwargs["profile"] / "package.json"
    document = json.loads(manifest.read_text())
    document["concurrentUserData"] = {"preserve": True}
    manifest.write_text(json.dumps(document, sort_keys=True) + "\n")
    return result

dsh._restore_packages = inject_concurrent_manifest
raise SystemExit(dsh.main(["update", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"Recovery required"* ]]
    [[ "$output" == *"'$manifest'"* ]]
    grep -q 'concurrentUserData' "$manifest"
    marker="$(find "$dsh_home/.agent-presets" -mindepth 1 -maxdepth 1 \
        -name "$marker_pattern" -print -quit)"
    [ -n "$marker" ]
    [[ "$output" == *"'$marker'"* ]]

    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh doctor --profile web
    [ "$status" -ne 0 ]
    [[ "$output" == *"Recovery artifact: '$marker'"* ]]
    [[ "$output" == *"Recovery needed: yes"* ]]
}

@test "DSH KeyboardInterrupt after completed remove preserves remaining bytes" {
    local dsh_home="$TEST_ROOT/dsh-home"
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$dsh_home" "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
    [ "$status" -eq 0 ]
    local preset="$dsh_home/.agent-presets/softspark-orchestrator"
    local state="$TEST_HOME/.softspark/ai-toolkit/state.json"
    local before_preset before_state before_manifest
    before_preset="$(find "$preset" -type f -exec shasum {} +)"
    before_state="$(shasum "$state")"
    before_manifest="$(shasum "$dsh_home/profiles/web/package.json")"

    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

real_run = dsh._run

def interrupt_after_first_remove(argv, *, dsh_home):
    result = real_run(argv, dsh_home=dsh_home)
    if "remove" in argv and "@softspark/dsh-orchestrator" in argv:
        raise KeyboardInterrupt
    return result

dsh._run = interrupt_after_first_remove
raise SystemExit(dsh.main(["uninstall", "--profile", "web", "--yes"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"interrupted"* ]]
    [[ "$output" != *"Traceback"* ]]
    [ "$(find "$preset" -type f -exec shasum {} +)" = "$before_preset" ]
    [ "$(shasum "$state")" = "$before_state" ]
    [ "$(shasum "$dsh_home/profiles/web/package.json")" != "$before_manifest" ]
    [ ! -e "$dsh_home/profiles/web/node_modules/@softspark/dsh-orchestrator" ]
    [[ "$output" == *"run 'ai-toolkit dsh doctor --profile web'"* ]]
}

@test "DSH uninstall state failure restores packages preset and prior state" {
    local dsh_home="$TEST_ROOT/dsh-home"
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$dsh_home" "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
    [ "$status" -eq 0 ]
    local preset="$dsh_home/.agent-presets/softspark-orchestrator/preset.md"
    local state="$TEST_HOME/.softspark/ai-toolkit/state.json"
    local before_preset before_state
    before_preset="$(shasum "$preset")"
    before_state="$(shasum "$state")"

    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

def fail_state(_profile, **_kwargs):
    raise OSError("injected DSH uninstall state failure")

dsh.remove_dsh_profile = fail_state
raise SystemExit(dsh.main(["uninstall", "--profile", "web", "--yes"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"injected DSH uninstall state failure"* ]]
    [ "$(shasum "$preset")" = "$before_preset" ]
    [ "$(shasum "$state")" = "$before_state" ]
    python3 - "$dsh_home" <<'PY'
import json
import sys
from pathlib import Path

home = Path(sys.argv[1])
manifest = json.loads((home / "profiles/web/package.json").read_text())
assert manifest["dependencies"] == {
    "@softspark/dsh-codex": "1.0.0",
    "@softspark/dsh-orchestrator": "1.0.1",
}, manifest
PY
}

@test "DSH uninstall backup cleanup failure restores packages preset and state" {
    local dsh_home="$TEST_ROOT/dsh-home"
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$dsh_home" "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
    [ "$status" -eq 0 ]
    local preset="$dsh_home/.agent-presets/softspark-orchestrator/preset.md"
    local state="$TEST_HOME/.softspark/ai-toolkit/state.json"
    local manifest="$dsh_home/profiles/web/package.json"
    local before_preset before_state before_manifest
    before_preset="$(shasum "$preset")"
    before_state="$(shasum "$state")"
    before_manifest="$(shasum "$manifest")"

    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

real_cleanup = dsh._cleanup_owned_entries
failed = False

def fail_uninstall_once(entries):
    global failed
    is_uninstall = any(
        ".ai-toolkit-uninstall." in str(entry.path) for entry in entries
    )
    if is_uninstall and not failed:
        failed = True
        raise OSError("injected uninstall cleanup failure")
    return real_cleanup(entries)

dsh._cleanup_owned_entries = fail_uninstall_once
raise SystemExit(dsh.main(["uninstall", "--profile", "web", "--yes"]))
PY

    [ "$status" -ne 0 ]
    [ "$(shasum "$preset")" = "$before_preset" ]
    [ "$(shasum "$state")" = "$before_state" ]
    [ "$(shasum "$manifest")" = "$before_manifest" ]
    [ -z "$(find "$dsh_home/.agent-presets" -mindepth 1 -maxdepth 1 \
        -name '.softspark-orchestrator.ai-toolkit-uninstall.*' -print -quit)" ]
}

@test "DSH KeyboardInterrupt at uninstall boundaries restores or preserves exact bytes" {
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    for boundary in \
        backup first_remove second_remove state cleanup_before cleanup_after; do
        local case_root="$TEST_ROOT/uninstall-$boundary"
        local case_home="$case_root/home"
        local dsh_home="$case_root/dsh"
        mkdir -p "$case_home" "$dsh_home"
        HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
        [ "$status" -eq 0 ]
        local preset="$dsh_home/.agent-presets/softspark-orchestrator/preset.md"
        local state="$case_home/.softspark/ai-toolkit/state.json"
        local manifest="$dsh_home/profiles/web/package.json"
        local before_preset before_state before_manifest
        before_preset="$(shasum "$preset")"
        before_state="$(shasum "$state")"
        before_manifest="$(shasum "$manifest")"

        HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            run python3 - "$TOOLKIT_DIR" "$boundary" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
boundary = sys.argv[2]
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

if boundary == "backup":
    real = dsh._secure_rename_noreplace

    def injected(source, destination):
        result = real(source, destination)
        destination = Path(destination)
        if (
            Path(source).name == dsh.PRESET_NAME
            and destination.name == "managed-preset"
            and ".ai-toolkit-uninstall." in destination.parent.name
        ):
            raise KeyboardInterrupt
        return result

    dsh._secure_rename_noreplace = injected
elif boundary in {"first_remove", "second_remove"}:
    real = dsh._run
    target = (
        "@softspark/dsh-orchestrator"
        if boundary == "first_remove"
        else "@softspark/dsh-codex"
    )

    def injected(argv, *, dsh_home):
        result = real(argv, dsh_home=dsh_home)
        if "remove" in argv and target in argv:
            raise KeyboardInterrupt
        return result

    dsh._run = injected
elif boundary == "state":
    real = dsh.remove_dsh_profile

    def injected(profile, **kwargs):
        real(profile, **kwargs)
        raise KeyboardInterrupt

    dsh.remove_dsh_profile = injected
else:
    real = dsh._cleanup_owned_entries

    def injected(entries):
        is_uninstall = any(
            ".ai-toolkit-uninstall." in str(entry.path) for entry in entries
        )
        if is_uninstall:
            if boundary == "cleanup_before":
                raise KeyboardInterrupt
            result = real(entries)
            raise KeyboardInterrupt
        return real(entries)

    dsh._cleanup_owned_entries = injected

raise SystemExit(dsh.main(["uninstall", "--profile", "web", "--yes"]))
PY

        [ "$status" -ne 0 ]
        [[ "$output" == *"interrupted"* ]]
        [[ "$output" != *"Traceback"* ]]
        [ "$(shasum "$preset")" = "$before_preset" ] || {
            echo "preset mismatch at uninstall boundary: $boundary"
            false
        }
        [ "$(shasum "$state")" = "$before_state" ]
        if [ "$boundary" = first_remove ] || [ "$boundary" = second_remove ]; then
            [ "$(shasum "$manifest")" != "$before_manifest" ]
            [[ "$output" == *"run 'ai-toolkit dsh doctor --profile web'"* ]]
        else
            [ "$(shasum "$manifest")" = "$before_manifest" ]
        fi
        [ -z "$(find "$dsh_home/.agent-presets" -mindepth 1 -maxdepth 1 \
            -name '.softspark-orchestrator.ai-toolkit-uninstall.*' -print -quit)" ] || {
            echo "uninstall recovery survived boundary: $boundary"
            find "$dsh_home/.agent-presets" -mindepth 1 -maxdepth 2 -print
            false
        }
    done
}

@test "DSH partial backup cleanup preserves deterministic doctor-visible recovery" {
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    for operation in update uninstall; do
        local case_root="$TEST_ROOT/partial-$operation"
        local case_home="$case_root/home"
        local dsh_home="$case_root/dsh"
        mkdir -p "$case_home" "$dsh_home"
        HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
        [ "$status" -eq 0 ]
        if [ "$operation" = update ]; then
            printf '%s\n' '{"preset_content_once":"new package preset\n"}' > \
                "$dsh_home/fake-control.json"
            suffix=backup
        else
            suffix=uninstall
        fi
        HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            run python3 - "$TOOLKIT_DIR" "$operation" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
operation = sys.argv[2]
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

real_cleanup = dsh._cleanup_owned_entries

def partially_delete_backup(entries):
    suffix = ".ai-toolkit-backup." if operation == "update" else ".ai-toolkit-uninstall."
    roots = [
        entry.path
        for entry in entries
        if entry.kind == "directory"
        and entry.path.name == "managed-preset"
        and suffix in entry.path.parent.name
    ]
    if roots:
        (roots[0] / "preset.md").unlink()
        raise OSError("injected partial backup cleanup")
    return real_cleanup(entries)

dsh._cleanup_owned_entries = partially_delete_backup
arguments = [operation, "--profile", "web"]
if operation == "uninstall":
    arguments.append("--yes")
raise SystemExit(dsh.main(arguments))
PY

        [ "$status" -ne 0 ]
        [[ "$output" == *"Recovery required"* ]]
        local artifact_real
        artifact_real="$(find "$dsh_home/.agent-presets" -mindepth 1 -maxdepth 1 \
            -name ".softspark-orchestrator.ai-toolkit-$suffix.*" -print -quit)"
        [ -n "$artifact_real" ]
        [[ "$output" == *"'$artifact_real'"* ]]
        [ -d "$artifact_real" ]

        HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh doctor --profile web
        [ "$status" -ne 0 ]
        [[ "$output" == *"Recovery artifact: '$artifact_real'"* ]]
        [[ "$output" == *"Recovery needed: yes"* ]]
    done
}

@test "DSH backup cleanup preserves additions created after its owned inventory" {
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    for operation in update uninstall; do
        for kind in file directory symlink; do
            local case_root="$TEST_ROOT/cleanup-$operation-$kind"
            local case_home="$case_root/home"
            local dsh_home="$case_root/dsh"
            mkdir -p "$case_home" "$dsh_home"
            HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
                run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
            [ "$status" -eq 0 ]
            if [ "$operation" = update ]; then
                printf '%s\n' '{"preset_content_once":"updated preset\n"}' > \
                    "$dsh_home/fake-control.json"
                suffix=backup
            else
                suffix=uninstall
            fi
            HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
                run python3 - "$TOOLKIT_DIR" "$operation" "$kind" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
operation, kind = sys.argv[2:]
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

real_cleanup = dsh._cleanup_owned_entries
injected = False

def inject_concurrent_entry(entries):
    global injected
    roots = [
        entry.path
        for entry in entries
        if entry.kind == "directory"
        and entry.path.name == "managed-preset"
        and (
            ".ai-toolkit-backup."
            if operation == "update"
            else ".ai-toolkit-uninstall."
        ) in entry.path.parent.name
    ]
    if roots and not injected:
        injected = True
        root = roots[0]
        if kind == "file":
            (root / "concurrent.txt").write_text("concurrent user bytes\n")
        elif kind == "directory":
            (root / "concurrent-dir").mkdir()
            (root / "concurrent-dir" / "keep.txt").write_text(
                "concurrent user bytes\n"
            )
        else:
            outside = root.parent / "concurrent-outside"
            outside.write_text("concurrent user bytes\n")
            (root / "concurrent-link").symlink_to(outside)
    return real_cleanup(entries)

dsh._cleanup_owned_entries = inject_concurrent_entry
arguments = [operation, "--profile", "web"]
if operation == "uninstall":
    arguments.append("--yes")
raise SystemExit(dsh.main(arguments))
PY

            [ "$status" -ne 0 ]
            [[ "$output" == *"Recovery required"* ]]
            artifact="$(find "$dsh_home/.agent-presets" -mindepth 1 -maxdepth 1 \
                -name ".softspark-orchestrator.ai-toolkit-$suffix.*" -print -quit)"
            [ -n "$artifact" ]
            [[ "$output" == *"'$artifact'"* ]]
            [ -d "$artifact" ]
            case "$kind" in
                file)
                    [ "$(cat "$artifact/managed-preset/concurrent.txt")" = \
                        "concurrent user bytes" ]
                    ;;
                directory)
                    [ "$(cat "$artifact/managed-preset/concurrent-dir/keep.txt")" = \
                        "concurrent user bytes" ]
                    ;;
                symlink)
                    [ -L "$artifact/managed-preset/concurrent-link" ]
                    [ "$(cat "$artifact/managed-preset/concurrent-link")" = \
                        "concurrent user bytes" ]
                    ;;
            esac
            HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
                run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh doctor --profile web
            [ "$status" -ne 0 ]
            [[ "$output" == *"Recovery artifact: '$artifact'"* ]]
            [[ "$output" == *"Recovery needed: yes"* ]]
        done
    done
}

@test "DSH recovery reports restore failures and still restores ownership state" {
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    for operation in update uninstall; do
        local case_root="$TEST_ROOT/restore-failure-$operation"
        local case_home="$case_root/home"
        local dsh_home="$case_root/dsh"
        mkdir -p "$case_home" "$dsh_home"
        HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
        [ "$status" -eq 0 ]
        if [ "$operation" = update ]; then
            printf '%s\n' '{"preset_content_once":"updated preset\n"}' > \
                "$dsh_home/fake-control.json"
        fi

        HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            run python3 - "$TOOLKIT_DIR" "$operation" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
operation = sys.argv[2]
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

real_rename = dsh._secure_rename_noreplace

def fail_backup_restore(source, destination):
    source_path = Path(source)
    destination_path = Path(destination)
    suffix = ".ai-toolkit-backup" if operation == "update" else ".ai-toolkit-uninstall"
    if (
        source_path.name == "managed-preset"
        and suffix in source_path.parent.name
        and destination_path.name == dsh.PRESET_NAME
    ):
        raise OSError("injected backup restore rename failure")
    return real_rename(source, destination)

dsh._secure_rename_noreplace = fail_backup_restore
if operation == "update":
    real_state = dsh.record_dsh_profile

    def fail_after_state(**kwargs):
        real_state(**kwargs)
        raise OSError("injected primary state failure")

    dsh.record_dsh_profile = fail_after_state
    arguments = ["update", "--profile", "web"]
else:
    real_state = dsh.remove_dsh_profile

    def fail_after_state(profile, **kwargs):
        real_state(profile, **kwargs)
        raise OSError("injected primary state failure")

    dsh.remove_dsh_profile = fail_after_state
    arguments = ["uninstall", "--profile", "web", "--yes"]

raise SystemExit(dsh.main(arguments))
PY

        [ "$status" -ne 0 ]
        [[ "$output" == *"injected primary state failure"* ]]
        [[ "$output" == *"Recovery required"* ]]
        [[ "$output" == *"injected backup restore rename failure"* || \
            "$output" == *"restore managed preset"* ]]
        python3 - "$case_home/.softspark/ai-toolkit/state.json" <<'PY'
import json
import sys

state = json.load(open(sys.argv[1], encoding="utf-8"))
assert "web" in state["dsh"]["profiles"], state
PY
    done
}

@test "DSH recovery hash and backup restore failures do not prevent state restoration" {
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    for operation in update uninstall; do
        for failure in hash copy; do
            local case_root="$TEST_ROOT/recovery-$operation-$failure"
            local case_home="$case_root/home"
            local dsh_home="$case_root/dsh"
            mkdir -p "$case_home" "$dsh_home"
            HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
                run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
            [ "$status" -eq 0 ]
            if [ "$operation" = update ]; then
                printf '%s\n' '{"preset_content_once":"updated preset\n"}' > \
                    "$dsh_home/fake-control.json"
            fi

            HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
                run python3 - "$TOOLKIT_DIR" "$operation" "$failure" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
operation, failure = sys.argv[2:]
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

real_hash = dsh._tree_hash
real_rename = dsh._secure_rename_noreplace
recovering = False

def fail_recovery_hash(path):
    path = Path(path)
    is_package_source = (
        "node_modules" in path.parts
        and "@softspark" in path.parts
        and "dsh-orchestrator" in path.parts
        and path.name == dsh.PRESET_NAME
    )
    if recovering and failure == "hash" and is_package_source:
        raise OSError("injected recovery hash failure")
    return real_hash(path)

def fail_recovery_restore(source, destination):
    source_path = Path(source)
    destination_path = Path(destination)
    if (
        recovering
        and failure == "copy"
        and source_path.name == "managed-preset"
        and ".ai-toolkit-" in source_path.parent.name
        and destination_path.name == dsh.PRESET_NAME
    ):
        raise OSError("injected recovery copy failure")
    return real_rename(source, destination)

dsh._tree_hash = fail_recovery_hash
dsh._secure_rename_noreplace = fail_recovery_restore
if operation == "update":
    real_state = dsh.record_dsh_profile

    def fail_after_state(**kwargs):
        global recovering
        real_state(**kwargs)
        recovering = True
        raise OSError("injected primary state failure")

    dsh.record_dsh_profile = fail_after_state
    arguments = ["update", "--profile", "web"]
else:
    real_state = dsh.remove_dsh_profile

    def fail_after_state(profile, **kwargs):
        global recovering
        real_state(profile, **kwargs)
        recovering = True
        raise OSError("injected primary state failure")

    dsh.remove_dsh_profile = fail_after_state
    arguments = ["uninstall", "--profile", "web", "--yes"]

raise SystemExit(dsh.main(arguments))
PY

            [ "$status" -ne 0 ]
            [[ "$output" == *"injected primary state failure"* ]]
            [[ "$output" == *"Recovery required"* ]] || {
                echo "missing recovery diagnostics for $operation/$failure: $output"
                false
            }
            if [ "$failure" = hash ]; then
                [[ "$output" == *"verify restored package preset failed: injected recovery hash failure"* ]]
            fi
            python3 - "$case_home/.softspark/ai-toolkit/state.json" <<'PY'
import json
import sys

state = json.load(open(sys.argv[1], encoding="utf-8"))
assert "web" in state["dsh"]["profiles"], state
PY
        done
    done
}

@test "DSH rollback preserves concurrent unrelated state and reports DSH CAS conflicts" {
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    for operation in install update uninstall; do
        for race in unrelated dsh; do
            local case_root="$TEST_ROOT/state-race-$operation-$race"
            local case_home="$case_root/home"
            local dsh_home="$case_root/dsh"
            mkdir -p "$case_home" "$dsh_home"
            if [ "$operation" != install ]; then
                HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
                    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
                [ "$status" -eq 0 ]
            fi

            HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
                run python3 - "$TOOLKIT_DIR" "$operation" "$race" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
operation, race = sys.argv[2:]
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

state_path = Path.home() / ".softspark" / "ai-toolkit" / "state.json"

def inject_race() -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if race == "unrelated":
        state["concurrent_writer"] = {"preserve": True}
    else:
        current = state.get("dsh", {}).get("profiles", {}).get("web")
        if current is None:
            current = {
                "dsh_home": str(Path(dsh._dsh_home())),
                "profile": "web",
                "packages": dict(dsh.PACKAGES),
                "preset_path": str(
                    dsh._dsh_home()
                    / ".agent-presets"
                    / dsh.PRESET_NAME
                ),
                "preset_hash": "c" * 64,
                "owned": True,
                "installed_at": "2026-08-29T00:00:00Z",
                "last_updated": "2026-08-29T00:00:01Z",
            }
            state["dsh"] = {"profiles": {"web": current}}
        else:
            current["preset_hash"] = "c" * 64
            current["last_updated"] = "2026-08-29T00:00:01Z"
    state_path.write_text(json.dumps(state) + "\n")

if operation in {"install", "update"}:
    real = dsh.record_dsh_profile

    def fail_state(**kwargs):
        if operation == "update":
            real(**kwargs)
        inject_race()
        raise OSError("injected state race failure")

    dsh.record_dsh_profile = fail_state
else:
    real = dsh.remove_dsh_profile

    def fail_state(profile, **kwargs):
        real(profile, **kwargs)
        inject_race()
        raise OSError("injected state race failure")

    dsh.remove_dsh_profile = fail_state

arguments = [operation, "--profile", "web"]
if operation == "uninstall":
    arguments.append("--yes")
raise SystemExit(dsh.main(arguments))
PY

            [ "$status" -ne 0 ]
            python3 - "$case_home/.softspark/ai-toolkit/state.json" \
                "$operation" "$race" <<'PY'
import json
import sys

state = json.load(open(sys.argv[1], encoding="utf-8"))
operation, race = sys.argv[2:]
if race == "unrelated":
    assert state["concurrent_writer"] == {"preserve": True}, state
    if operation == "install":
        assert "dsh" not in state, state
    else:
        assert "web" in state["dsh"]["profiles"], state
else:
    assert state["dsh"]["profiles"]["web"]["preset_hash"] == "c" * 64, state
PY
            if [ "$race" = dsh ]; then
                [[ "$output" == *"Recovery required"* ]]
                [[ "$output" == *"restore ai-toolkit state"* ]]
            fi
        done
    done
}

@test "DSH install rollback preserves a concurrently created empty state file" {
    local fake_bin="$TEST_ROOT/fake-bin"
    local dsh_home="$TEST_ROOT/dsh-empty-state"
    mkdir -p "$fake_bin" "$dsh_home"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"

    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run python3 - "$TOOLKIT_DIR" <<'PY'
from pathlib import Path
import sys

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

state_path = Path.home() / ".softspark" / "ai-toolkit" / "state.json"

def concurrent_empty_state(**_kwargs):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{}\n")
    raise OSError("injected state failure")

dsh.record_dsh_profile = concurrent_empty_state
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [ -f "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
    [ "$(cat "$TEST_HOME/.softspark/ai-toolkit/state.json")" = "{}" ]
}

@test "DSH rollback never removes a concurrently replaced package tree" {
    fake_bin="$TEST_ROOT/fake-bin"
    TEST_DSH_HOME="$TEST_ROOT/dsh-home"
    mkdir -p "$fake_bin" "$TEST_DSH_HOME"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    cat > "$TEST_DSH_HOME/fake-control.json" <<'JSON'
{
  "fail_before": "add:@softspark/dsh-orchestrator",
  "replace_package_before_failure": "add:@softspark/dsh-orchestrator",
  "replacement_package": "@softspark/dsh-codex"
}

JSON

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -ne 0 ]
    [[ "$output" == *"package identity changed during failed external mutation"* ]]
    [[ "$output" == *"run 'ai-toolkit dsh doctor --profile web'"* ]]
    replacement="$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-codex"
    [ "$(cat "$replacement/concurrent-user-data.txt")" = "preserve concurrent bytes" ]
    [ "$(python3 -c "import json; print(json.load(open('$replacement/package.json'))['version'])")" = "9.9.9" ]
    [ "$(wc -l < "$TEST_DSH_HOME/fake-argv.jsonl" | xargs)" -eq 2 ]

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh doctor --profile web
    [ "$status" -ne 0 ]
    [[ "$output" == *"Recovery artifact:"* ]]
}

@test "DSH update and uninstall rollback preserve concurrent package replacements" {
    fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"

    for operation in update uninstall; do
        case_home="$TEST_ROOT/$operation-home"
        case_dsh="$TEST_ROOT/$operation-dsh"
        mkdir -p "$case_home" "$case_dsh"
        command=(env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
            node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
        run "${command[@]}" install --profile web
        [ "$status" -eq 0 ]
        if [ "$operation" = update ]; then
            trigger='add:@softspark/dsh-orchestrator'
            replacement='@softspark/dsh-codex'
            arguments=(update --profile web)
        else
            trigger='remove:@softspark/dsh-codex'
            replacement='@softspark/dsh-orchestrator'
            arguments=(uninstall --profile web --yes)
        fi
        python3 - "$case_dsh/fake-control.json" "$trigger" "$replacement" <<'PY'
import json
import sys

path, trigger, replacement = sys.argv[1:]
with open(path, "w", encoding="utf-8") as stream:
    json.dump(
        {
            "fail_before": trigger,
            "replace_package_before_failure": trigger,
            "replacement_package": replacement,
        },
        stream,
    )
PY

        run "${command[@]}" "${arguments[@]}"
        [ "$status" -ne 0 ]
        [[ "$output" == *"package identity changed during failed external mutation"* ]]
        [[ "$output" == *"run 'ai-toolkit dsh doctor --profile web'"* ]]
        replacement_root="$case_dsh/profiles/web/node_modules/${replacement}"
        [ "$(cat "$replacement_root/concurrent-user-data.txt")" = \
            "preserve concurrent bytes" ]
        [ "$(wc -l < "$case_dsh/fake-argv.jsonl" | xargs)" -eq 4 ]
    done
}

@test "DSH update staging exceptions preserve concurrent bytes and report recovery" {
    local fake_bin="$TEST_ROOT/fake-bin"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    for failure in keyboard os_error; do
        for boundary in claim copy hash; do
            local case_root="$TEST_ROOT/staging-$failure-$boundary"
            local case_home="$case_root/home"
            local dsh_home="$case_root/dsh"
            mkdir -p "$case_home" "$dsh_home"
            HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
                run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
            [ "$status" -eq 0 ]
            printf '%s\n' '{"preset_content_once":"updated preset\n"}' > \
                "$dsh_home/fake-control.json"
            local artifact="$dsh_home/.agent-presets/.softspark-orchestrator.ai-toolkit-new"

            HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
                run python3 - "$TOOLKIT_DIR" "$failure" "$boundary" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
failure, boundary = sys.argv[2:]
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

def interrupt():
    if failure == "keyboard":
        raise KeyboardInterrupt
    raise OSError("injected staging I/O failure")

if boundary == "claim":
    real = dsh._claim_directory

    def injected(path, owned, *, mode=0o700):
        real(path, owned, mode=mode)
        if path.name.endswith(".ai-toolkit-new"):
            (path / "concurrent.txt").write_text("concurrent user bytes\n")
            interrupt()

    dsh._claim_directory = injected
elif boundary == "copy":
    real = dsh._copy_tree_exclusive

    def injected(source, destination, owned):
        real(source, destination, owned)
        if destination.name.endswith(".ai-toolkit-new"):
            (destination / "concurrent.txt").write_text("concurrent user bytes\n")
            interrupt()

    dsh._copy_tree_exclusive = injected
else:
    real = dsh._tree_hash

    def injected(path):
        result = real(path)
        if path.name.endswith(".ai-toolkit-new"):
            (path / "concurrent.txt").write_text("concurrent user bytes\n")
            interrupt()
        return result

    dsh._tree_hash = injected

raise SystemExit(dsh.main(["update", "--profile", "web"]))
PY

            [ "$status" -ne 0 ]
            [[ "$output" == *"Recovery required"* ]]
            [[ "$output" == *"'$artifact'"* ]]
            [ "$(cat "$artifact/concurrent.txt")" = "concurrent user bytes" ]
            [ ! -e "$artifact/preset.md" ]
            HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
                run node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh doctor --profile web
            [ "$status" -ne 0 ]
            [[ "$output" == *"Recovery artifact: '$artifact'"* ]]
            [[ "$output" == *"Recovery needed: yes"* ]]
        done
    done
}

@test "DSH uninstall preserves a byte-identical replacement of relocated backup" {
    local fake_bin="$TEST_ROOT/relocated-uninstall-bin"
    local dsh_home="$TEST_ROOT/relocated-uninstall-dsh"
    mkdir -p "$fake_bin" "$dsh_home"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    local command=(env HOME="$TEST_HOME" DSH_HOME="$dsh_home" \
        PATH="$fake_bin:$PATH" node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
    run "${command[@]}" install --profile web
    [ "$status" -eq 0 ]
    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run python3 - "$TOOLKIT_DIR" <<'PY'
import shutil
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

real_replace = dsh._secure_rename_noreplace
injected = False


def replace_with_identical_inode(source, destination):
    global injected
    source = Path(source)
    destination = Path(destination)
    real_replace(source, destination)
    if (
        destination.name == "managed-preset"
        and ".ai-toolkit-uninstall." in destination.parent.name
        and not injected
    ):
        injected = True
        original = destination.parent / ".original-relocated-payload"
        real_replace(destination, original)
        shutil.copytree(original, destination)


dsh._secure_rename_noreplace = replace_with_identical_inode
raise SystemExit(dsh.main(["uninstall", "--profile", "web", "--yes"]))
PY

    [ "$status" -ne 0 ]
    backup="$(find "$dsh_home/.agent-presets" -mindepth 1 -maxdepth 1 \
        -name '.softspark-orchestrator.ai-toolkit-uninstall.*' -print -quit)"
    [ -n "$backup" ]
    [[ "$output" == *"identity changed"* ]]
    [[ "$output" == *"'$backup'"* ]]
    [ -f "$backup/managed-preset/preset.md" ]
    diff -qr \
        "$backup/managed-preset" \
        "$backup/.original-relocated-payload"
    run "${command[@]}" doctor --profile web
    [ "$status" -ne 0 ]
    [[ "$output" == *"Recovery artifact: '$backup'"* ]]
    [[ "$output" == *"Recovery needed: yes"* ]]
}

@test "DSH update lifecycle identity errors clean or report transaction staging" {
    local fake_bin="$TEST_ROOT/staging-lifecycle-bin"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"
    for concurrent in no yes; do
        local case_root="$TEST_ROOT/staging-lifecycle-$concurrent"
        local case_home="$case_root/home"
        local dsh_home="$case_root/dsh"
        mkdir -p "$case_home" "$dsh_home"
        local command=(env HOME="$case_home" DSH_HOME="$dsh_home" \
            PATH="$fake_bin:$PATH" node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
        run "${command[@]}" install --profile web
        [ "$status" -eq 0 ]
        printf '%s\n' '{"preset_content_once":"updated preset\n"}' > \
            "$dsh_home/fake-control.json"
        local staging="$dsh_home/.agent-presets/.softspark-orchestrator.ai-toolkit-new"

        HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            run python3 - "$TOOLKIT_DIR" "$concurrent" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
concurrent = sys.argv[2] == "yes"
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

real_assert = dsh._assert_entry_unchanged
raised = False


def fail_after_staging(expected, label):
    global raised
    staging = expected.path.parent / f".{expected.path.name}.ai-toolkit-new"
    if label == "managed preset" and staging.is_dir() and not raised:
        raised = True
        if concurrent:
            (staging / "concurrent.txt").write_text("concurrent user bytes\n")
        raise dsh.DshLifecycleError("injected lifecycle identity failure")
    return real_assert(expected, label)


dsh._assert_entry_unchanged = fail_after_staging
raise SystemExit(dsh.main(["update", "--profile", "web"]))
PY

        [ "$status" -ne 0 ]
        [[ "$output" == *"injected lifecycle identity failure"* ]]
        if [ "$concurrent" = no ]; then
            [ ! -e "$staging" ]
        else
            [[ "$output" == *"Recovery required"* ]]
            [[ "$output" == *"'$staging'"* ]]
            [ "$(cat "$staging/concurrent.txt")" = "concurrent user bytes" ]
            [ ! -e "$staging/preset.md" ]
            run "${command[@]}" doctor --profile web
            [ "$status" -ne 0 ]
            [[ "$output" == *"Recovery artifact: '$staging'"* ]]
            [[ "$output" == *"Recovery needed: yes"* ]]
        fi
    done
}

@test "DSH update and uninstall never clobber recovery paths raced after preflight" {
    local fake_bin="$TEST_ROOT/recovery-race-bin"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"

    for operation in update uninstall; do
        for kind in empty file symlink; do
            local case_root="$TEST_ROOT/recovery-race-$operation-$kind"
            local case_home="$case_root/home"
            local dsh_home="$case_root/dsh"
            mkdir -p "$case_home" "$dsh_home"
            local command=(env HOME="$case_home" DSH_HOME="$dsh_home" \
                PATH="$fake_bin:$PATH" node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
            run "${command[@]}" install --profile web
            [ "$status" -eq 0 ]
            if [ "$operation" = update ]; then
                printf '%s\n' '{"preset_content_once":"updated preset\n"}' > \
                    "$dsh_home/fake-control.json"
                local suffix=backup
            else
                local suffix=uninstall
            fi
            local preset="$dsh_home/.agent-presets/softspark-orchestrator"
            local raced="$dsh_home/.agent-presets/.softspark-orchestrator.ai-toolkit-$suffix"
            local manifest="$dsh_home/profiles/web/package.json"
            local state="$case_home/.softspark/ai-toolkit/state.json"
            local before_preset before_manifest before_state
            before_preset="$(profile_fingerprint "$preset")"
            before_manifest="$(shasum "$manifest")"
            before_state="$(shasum "$state")"

            HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
                run python3 - "$TOOLKIT_DIR" "$operation" "$kind" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
operation, kind = sys.argv[2:]
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

home = dsh._dsh_home()
preset = home / ".agent-presets" / dsh.PRESET_NAME
suffix = "backup" if operation == "update" else "uninstall"
raced = preset.parent / f".{preset.name}.ai-toolkit-{suffix}"
real_claim = dsh._claim_recovery_location
injected = False


def inject_recovery_race(destination, suffix):
    global injected
    if not injected:
        injected = True
        if kind == "empty":
            raced.mkdir()
        elif kind == "file":
            raced.write_text("concurrent recovery bytes\n", encoding="utf-8")
        else:
            target = home / "concurrent-recovery-target"
            target.write_text("concurrent target bytes\n", encoding="utf-8")
            raced.symlink_to(target)
    return real_claim(destination, suffix)


dsh._claim_recovery_location = inject_recovery_race
arguments = [operation, "--profile", "web"]
if operation == "uninstall":
    arguments.append("--yes")
status = dsh.main(arguments)
assert injected, "recovery race injection was not reached"
raise SystemExit(status)
PY

            [ "$status" -ne 0 ]
            [[ "$output" == *"recovery collision"* ]]
            [ "$(profile_fingerprint "$preset")" = "$before_preset" ]
            [ "$(shasum "$manifest")" = "$before_manifest" ]
            [ "$(shasum "$state")" = "$before_state" ]
            case "$kind" in
                empty) [ -d "$raced" ] && [ -z "$(find "$raced" -mindepth 1 -print -quit)" ] ;;
                file) [ "$(cat "$raced")" = "concurrent recovery bytes" ] ;;
                symlink)
                    [ -L "$raced" ]
                    [ "$(cat "$raced")" = "concurrent target bytes" ]
                    ;;
            esac
            run "${command[@]}" doctor --profile web
            [ "$status" -ne 0 ]
            [[ "$output" == *"Recovery artifact:"* ]]
            [[ "$output" == *".ai-toolkit-$suffix"* ]]
        done
    done
}

@test "DSH install aggregates every owned-cleanup failure with the primary error" {
    local fake_bin="$TEST_ROOT/cleanup-aggregation-bin"
    local dsh_home="$TEST_ROOT/cleanup-aggregation-dsh"
    mkdir -p "$fake_bin" "$dsh_home"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"

    HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

cleanup_count = 0


def fail_cleanup(_entries):
    global cleanup_count
    cleanup_count += 1
    raise dsh.DshLifecycleError(f"injected cleanup lifecycle failure {cleanup_count}")


def fail_state(**_kwargs):
    dsh._cleanup_owned_entries = fail_cleanup
    raise OSError("injected primary state failure")


dsh.record_dsh_profile = fail_state
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    echo "$output" | grep -Fq "injected primary state failure"
    echo "$output" | grep -Fq "injected cleanup lifecycle failure 1"
    echo "$output" | grep -Fq "injected cleanup lifecycle failure 2"
    echo "$output" | grep -Fq "inspect preserved recovery path"
    [ -d "$dsh_home/.agent-presets/softspark-orchestrator" ]

    run env HOME="$TEST_HOME" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh doctor --profile web
    [ "$status" -ne 0 ]
    [[ "$output" == *"Recovery artifact:"* ]]
    [[ "$output" == *".ai-toolkit-package"* ]]
    [[ "$output" == *"Recovery needed: yes"* ]]
}

@test "DSH staging retains primary and snapshot cleanup errors with recovery paths" {
    local fake_bin="$TEST_ROOT/staging-snapshot-bin"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    chmod +x "$fake_bin/dsh"

    for failure in keyboard os_error; do
        local case_root="$TEST_ROOT/staging-snapshot-$failure"
        local case_home="$case_root/home"
        local dsh_home="$case_root/dsh"
        mkdir -p "$case_home" "$dsh_home"
        local command=(env HOME="$case_home" DSH_HOME="$dsh_home" \
            PATH="$fake_bin:$PATH" node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
        run "${command[@]}" install --profile web
        [ "$status" -eq 0 ]
        printf '%s\n' '{"preset_content_once":"updated preset\n"}' > \
            "$dsh_home/fake-control.json"
        local staging="$dsh_home/.agent-presets/.softspark-orchestrator.ai-toolkit-new"

        HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            run python3 - "$TOOLKIT_DIR" "$failure" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
failure = sys.argv[2]
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

real_hash = dsh._tree_hash
real_snapshot = dsh._snapshot_tree
primary_injected = False


def fail_after_staging(path):
    global primary_injected
    result = real_hash(path)
    if path.name.endswith(".ai-toolkit-new") and not primary_injected:
        primary_injected = True
        (path / "concurrent.txt").write_text("concurrent staging bytes\n")
        raise dsh.DshLifecycleError("injected primary staging failure")
    return result


def fail_snapshot(path):
    if path.name.endswith(".ai-toolkit-new"):
        if failure == "keyboard":
            raise KeyboardInterrupt
        raise OSError("injected snapshot cleanup I/O failure")
    return real_snapshot(path)


dsh._tree_hash = fail_after_staging
dsh._snapshot_tree = fail_snapshot
status = dsh.main(["update", "--profile", "web"])
assert primary_injected, "primary staging failure was not reached"
raise SystemExit(status)
PY

        [ "$status" -ne 0 ]
        echo "$output" | grep -Fq "injected primary staging failure"
        if [ "$failure" = keyboard ]; then
            echo "$output" | grep -Fq "snapshot cleanup failed: interrupted"
        else
            echo "$output" | grep -Fq \
                "snapshot cleanup failed: injected snapshot cleanup I/O failure"
        fi
        echo "$output" | grep -Fq "inspect preserved recovery path"
        echo "$output" | grep -Fq ".ai-toolkit-new"
        [ "$(cat "$staging/concurrent.txt")" = "concurrent staging bytes" ]
        run "${command[@]}" doctor --profile web
        [ "$status" -ne 0 ]
        [[ "$output" == *"Recovery artifact: '$staging'"* ]]
        [[ "$output" == *"Recovery needed: yes"* ]]
    done
}

@test "DSH package recovery stops after drift for every lifecycle order" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path
from types import SimpleNamespace

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

packages = dict(dsh.PACKAGES)
orders = {
    "install": ({}, packages, False),
    "update": (packages, packages, True),
    "uninstall": (packages, {}, False),
}

for lifecycle, (before, current, force_reinstall) in orders.items():
    for boundary in ("exception", "success"):
        profile_root = Path.home() / f"profile-{lifecycle}-{boundary}"
        package_trees = {
            profile_root / "node_modules" / Path(package): None
            for package in packages
        }
        original_identity = dsh._PackageMutationIdentity(None, package_trees)
        drifted_identity = dsh._PackageMutationIdentity(
            None,
            {**package_trees, next(iter(package_trees)): {}},
        )
        transaction = SimpleNamespace(
            profile_root=profile_root,
            manifest=None,
            package_trees=package_trees,
            latest_package_identity=original_identity,
            rollback_blocked=False,
        )
        calls = []

        def run_recovery(command, *, dsh_home, transaction, recovery_target):
            assert recovery_target.profile == "web"
            nonlocal_observed[0] = drifted_identity
            calls.append(command)
            if boundary == "exception":
                transaction.rollback_blocked = True
                raise dsh.DshLifecycleError("injected recovery drift")

        nonlocal_observed = [original_identity]

        def capture_changed_identity(_profile_root):
            return nonlocal_observed[0]

        real_versions = dsh._profile_package_versions
        real_unmanaged = dsh._profile_unmanaged_dependencies
        real_capture = dsh._capture_package_mutation_identity
        real_run = dsh._run_profile_command
        dsh._profile_package_versions = lambda _home, _profile: dict(current)
        dsh._profile_unmanaged_dependencies = lambda _home, _profile: {}
        dsh._capture_package_mutation_identity = capture_changed_identity
        dsh._run_profile_command = run_recovery
        try:
            failed = dsh._restore_packages(
                executable="/fake/dsh",
                dsh_home=Path.home() / ".dsh",
                profile="web",
                before=dict(before),
                force_reinstall=force_reinstall,
                transaction=transaction,
            )
        finally:
            dsh._profile_package_versions = real_versions
            dsh._profile_unmanaged_dependencies = real_unmanaged
            dsh._capture_package_mutation_identity = real_capture
            dsh._run_profile_command = real_run

        assert len(calls) == 1, (lifecycle, boundary, calls)
        assert transaction.rollback_blocked, (lifecycle, boundary)
        assert any("dsh doctor --profile web" in item for item in failed), failed
        assert any(str(transaction.profile_root) in item for item in failed), failed
PY

    [ "$status" -eq 0 ]
}

@test "DSH package recovery real boundary rejects successful non-target managed drift" {
    run env HOME="$TEST_HOME" python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import json
import os
import shutil
import stat
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
test_root = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

packages = dict(dsh.PACKAGES)
orders = {
    "install": ({}, packages, False),
    "update": (packages, packages, True),
    "uninstall": (packages, {}, False),
}

fake_source = r'''#!/usr/bin/env python3
import json
import shutil
import sys
from pathlib import Path

home = Path(__import__("os").environ["DSH_HOME"])
control = json.loads((home / "recovery-control.json").read_text())
profile = sys.argv[3]
operation = sys.argv[4]
operand = sys.argv[5]
package = operand.rsplit("@", 1)[0] if operation == "add" else operand
version = operand.rsplit("@", 1)[1] if operation == "add" else None
profile_root = home / "profiles" / profile
manifest_path = profile_root / "package.json"
document = json.loads(manifest_path.read_text())
dependencies = document.setdefault("dependencies", {})
package_root = profile_root / "node_modules" / Path(package)
if package_root.exists():
    shutil.rmtree(package_root)
if operation == "add":
    dependencies[package] = version
    package_root.mkdir(parents=True)
    (package_root / "package.json").write_text(
        json.dumps({"name": package, "version": version}) + "\n"
    )
    (package_root / "payload.txt").write_text("original\n")
else:
    dependencies.pop(package, None)
manifest_path.write_text(json.dumps(document, sort_keys=True) + "\n")
other = next(name for name in control["packages"] if name != package)
other_root = profile_root / "node_modules" / Path(other)
other_root.mkdir(parents=True, exist_ok=True)
(other_root / "non-target-drift.txt").write_text("preserve non-target drift\n")
with (home / "recovery-calls.jsonl").open("a") as stream:
    stream.write(json.dumps(sys.argv[1:]) + "\n")
raise SystemExit(71 if control["boundary"] == "failure" else 0)
'''


def write_profile(profile_root, installed, payload):
    if profile_root.exists():
        shutil.rmtree(profile_root)
    profile_root.mkdir(parents=True)
    dependencies = {"customer-package": "2.0.0", **installed}
    (profile_root / "package.json").write_text(
        json.dumps({"dependencies": dependencies}, sort_keys=True) + "\n"
    )
    for package, version in installed.items():
        package_root = profile_root / "node_modules" / Path(package)
        package_root.mkdir(parents=True)
        (package_root / "package.json").write_text(
            json.dumps({"name": package, "version": version}) + "\n"
        )
        (package_root / "payload.txt").write_text(f"{payload}\n")


for lifecycle, (before, current, force_reinstall) in orders.items():
    for boundary in ("success", "failure"):
        case_root = test_root / f"real-recovery-{lifecycle}-{boundary}"
        dsh_home = case_root / "home"
        profile_root = dsh_home / "profiles" / "web"
        dsh_home.mkdir(parents=True)
        executable = case_root / "dsh"
        executable.write_text(fake_source)
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
        execution_path = str(case_root) + os.pathsep + os.environ["PATH"]
        dsh._ACTIVE_PREREQUISITES = dsh._PrerequisiteRecord(
            execution_path=execution_path,
            dsh=dsh._capture_executable_prerequisite(
                "dsh",
                execution_path=execution_path,
                missing_error="missing test DSH",
            ),
            pnpm=dsh._capture_executable_prerequisite(
                "pnpm",
                execution_path=execution_path,
                missing_error="missing test pnpm",
            ),
        )
        (dsh_home / "recovery-control.json").write_text(
            json.dumps({"boundary": boundary, "packages": list(packages)})
        )

        write_profile(profile_root, before, "original")
        transaction = dsh._capture_profile_transaction(dsh_home, "web")
        write_profile(profile_root, current, "current")
        transaction.latest_package_identity = dsh._capture_package_mutation_identity(
            profile_root
        )
        dsh._observe_profile_transaction(transaction)

        failed = dsh._restore_packages(
            executable=str(executable),
            dsh_home=dsh_home,
            profile="web",
            before=dict(before),
            force_reinstall=force_reinstall,
            transaction=transaction,
        )

        calls = (dsh_home / "recovery-calls.jsonl").read_text().splitlines()
        assert len(calls) == 1, (lifecycle, boundary, calls)
        assert transaction.rollback_blocked, (lifecycle, boundary)
        assert any("dsh doctor --profile web" in item for item in failed), failed
        assert any(str(profile_root) in item for item in failed), failed
        drift = list((profile_root / "node_modules").rglob("non-target-drift.txt"))
        assert len(drift) == 1, (lifecycle, boundary, drift)
        assert drift[0].read_text() == "preserve non-target drift\n"
PY

    [ "$status" -eq 0 ]
}

@test "DSH snapshot file recreation never follows a swapped parent" {
    run env HOME="$TEST_HOME" python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = (Path(sys.argv[2]) / "snapshot-file-parent-swap").resolve()
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

parent = root / "managed"
preserved = root / "managed-preserved"
outside = root / "outside"
parent.mkdir(parents=True)
outside.mkdir()
snapshot = dsh._PathPrestate(
    parent / "payload.txt", "file", 0o640, content=b"rollback bytes\n"
)
real_write_all = dsh._write_all
injected = [False]


def swap_parent_before_create(descriptor, content):
    if not injected[0]:
        injected[0] = True
        parent.rename(preserved)
        parent.symlink_to(outside, target_is_directory=True)
    real_write_all(descriptor, content)


dsh._write_all = swap_parent_before_create
try:
    created = dsh._create_snapshot_entry(snapshot)
finally:
    dsh._write_all = real_write_all

assert injected[0], "file creation boundary was not reached"
assert not created
assert not (outside / snapshot.path.name).exists()
assert (preserved / snapshot.path.name).read_bytes() == snapshot.content
PY

    [ "$status" -eq 0 ]
}

@test "DSH snapshot directory recreation never follows a swapped parent" {
    run env HOME="$TEST_HOME" python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = (Path(sys.argv[2]) / "snapshot-directory-parent-swap").resolve()
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

parent = root / "managed"
preserved = root / "managed-preserved"
outside = root / "outside"
parent.mkdir(parents=True)
outside.mkdir()
snapshot = dsh._PathPrestate(parent / "payload", "directory", 0o750)
real_mkdir = os.mkdir
real_supported = dsh._secure_mutation_supported
injected = [False]


def swap_parent_before_create(path, mode=0o777, *, dir_fd=None):
    name = os.fsdecode(path)
    if not injected[0] and (name == str(snapshot.path) or name == snapshot.path.name):
        injected[0] = True
        parent.rename(preserved)
        parent.symlink_to(outside, target_is_directory=True)
    return real_mkdir(path, mode, dir_fd=dir_fd)


os.mkdir = swap_parent_before_create
dsh._secure_mutation_supported = lambda: True
try:
    created = dsh._create_snapshot_entry(snapshot)
finally:
    dsh._secure_mutation_supported = real_supported
    os.mkdir = real_mkdir

assert injected[0], "directory creation boundary was not reached"
assert not created
assert not (outside / snapshot.path.name).exists()
assert (preserved / snapshot.path.name).is_dir()
PY

    [ "$status" -eq 0 ]
}

@test "DSH snapshot symlink recreation never follows a swapped parent" {
    run env HOME="$TEST_HOME" python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = (Path(sys.argv[2]) / "snapshot-symlink-parent-swap").resolve()
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

parent = root / "managed"
preserved = root / "managed-preserved"
outside = root / "outside"
parent.mkdir(parents=True)
outside.mkdir()
snapshot = dsh._PathPrestate(
    parent / "payload-link", "symlink", 0o777, link_target="target.txt"
)
real_symlink = os.symlink
real_supported = dsh._secure_mutation_supported
injected = [False]


def swap_parent_before_create(source, destination, target_is_directory=False, *, dir_fd=None):
    name = os.fsdecode(destination)
    if not injected[0] and (name == str(snapshot.path) or name == snapshot.path.name):
        injected[0] = True
        parent.rename(preserved)
        parent.symlink_to(outside, target_is_directory=True)
    return real_symlink(
        source,
        destination,
        target_is_directory=target_is_directory,
        dir_fd=dir_fd,
    )


os.symlink = swap_parent_before_create
dsh._secure_mutation_supported = lambda: True
try:
    created = dsh._create_snapshot_entry(snapshot)
finally:
    dsh._secure_mutation_supported = real_supported
    os.symlink = real_symlink

assert injected[0], "symlink creation boundary was not reached"
assert not created
assert not (outside / snapshot.path.name).exists()
assert (preserved / snapshot.path.name).is_symlink()
assert os.readlink(preserved / snapshot.path.name) == snapshot.link_target
PY

    [ "$status" -eq 0 ]
}

@test "DSH tree mode restoration preserves a byte-identical inode replacement" {
    run env HOME="$TEST_HOME" python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import os
import stat
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = (Path(sys.argv[2]) / "snapshot-mode-inode-race").resolve()
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

root.mkdir(parents=True)
payload = root / "payload.txt"
preserved = root / "payload-managed.txt"
content = b"byte-identical content\n"
payload.write_bytes(content)
payload.chmod(0o644)
root_mode = stat.S_IMODE(root.stat(follow_symlinks=False).st_mode)
snapshots = {
    root: dsh._PathPrestate(root, "directory", root_mode),
    payload: dsh._PathPrestate(payload, "file", 0o600, content=content),
}
real_fchmod = os.fchmod
injected = [False]


def replace_before_fchmod(descriptor, mode):
    if not injected[0]:
        injected[0] = True
        payload.rename(preserved)
        payload.write_bytes(content)
        payload.chmod(0o644)
    real_fchmod(descriptor, mode)


os.fchmod = replace_before_fchmod
try:
    residuals = dsh._restore_tree_prestate(root, snapshots)
finally:
    os.fchmod = real_fchmod

assert injected[0], "fd-based mode restoration was not reached"
assert payload in residuals
assert payload.read_bytes() == content
assert stat.S_IMODE(payload.stat(follow_symlinks=False).st_mode) == 0o644
assert preserved.read_bytes() == content
assert stat.S_IMODE(preserved.stat(follow_symlinks=False).st_mode) == 0o600
PY

    [ "$status" -eq 0 ]
}

@test "DSH tree prestate restores file and directory mode-only drift" {
    run env HOME="$TEST_HOME" python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import stat
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = (Path(sys.argv[2]) / "snapshot-mode-only-drift").resolve()
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

root.mkdir(parents=True)
directory = root / "managed-directory"
directory.mkdir(mode=0o755)
payload = directory / "payload.txt"
payload.write_bytes(b"unchanged bytes\n")
payload.chmod(0o644)
root_mode = stat.S_IMODE(root.stat(follow_symlinks=False).st_mode)
snapshots = {
    root: dsh._PathPrestate(root, "directory", root_mode),
    directory: dsh._PathPrestate(directory, "directory", 0o700),
    payload: dsh._PathPrestate(
        payload, "file", 0o600, content=b"unchanged bytes\n"
    ),
}

residuals = dsh._restore_tree_prestate(root, snapshots)

assert residuals == [], residuals
assert payload.read_bytes() == b"unchanged bytes\n"
assert stat.S_IMODE(payload.stat(follow_symlinks=False).st_mode) == 0o600
assert stat.S_IMODE(directory.stat(follow_symlinks=False).st_mode) == 0o700
PY

    [ "$status" -eq 0 ]
}

@test "DSH manifest mode restoration rejects a byte-identical inode replacement" {
    run env HOME="$TEST_HOME" python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import stat
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
profile = (Path(sys.argv[2]) / "manifest-mode-inode-race").resolve()
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

profile.mkdir(parents=True)
manifest = profile / "package.json"
preserved = profile / "package-managed.json"
content = b'{"dependencies":{"customer":"2.0.0"}}\n'
manifest.write_bytes(content)
manifest.chmod(0o644)
transaction = dsh._ProfileTransaction(
    profile,
    {profile: True},
    dsh._PathPrestate(manifest, "file", 0o600, content=content),
    {},
    {},
    latest_manifest=dsh._capture_entry(manifest),
)
real_read = dsh._read_regular_bytes
injected = [False]


def replace_after_content_check(path):
    result = real_read(path)
    if path == manifest and not injected[0]:
        injected[0] = True
        manifest.rename(preserved)
        manifest.write_bytes(content)
        manifest.chmod(0o644)
    return result


dsh._read_regular_bytes = replace_after_content_check
try:
    residuals = dsh._restore_manifest_prestate(transaction)
finally:
    dsh._read_regular_bytes = real_read

assert injected[0], "manifest content boundary was not reached"
assert manifest in residuals
assert manifest.read_bytes() == content
assert stat.S_IMODE(manifest.stat(follow_symlinks=False).st_mode) == 0o644
assert preserved.read_bytes() == content
assert stat.S_IMODE(preserved.stat(follow_symlinks=False).st_mode) == 0o644
PY

    [ "$status" -eq 0 ]
}

@test "DSH mode rollback never chmods a replacement DSH root" {
    run env HOME="$TEST_HOME" python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import stat
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = (Path(sys.argv[2]) / "mode-root-swap").resolve()
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

dsh_home = root / "dsh-home"
profile = dsh_home / "profiles" / "web"
profile.mkdir(parents=True)
payload = profile / "payload.txt"
content = b"managed bytes\n"
payload.write_bytes(content)
payload.chmod(0o644)
snapshot = dsh._PathPrestate(payload, "file", 0o600, content=content)
pinned_home = dsh._pin_dsh_home(dsh_home)
previous_active = dsh._ACTIVE_DSH_HOME
dsh._ACTIVE_DSH_HOME = pinned_home
preserved_home = root / "dsh-home-preserved"
dsh_home.rename(preserved_home)
replacement_profile = dsh_home / "profiles" / "web"
replacement_profile.mkdir(parents=True)
replacement_payload = replacement_profile / payload.name
replacement_payload.write_bytes(content)
replacement_payload.chmod(0o644)

try:
    restored = dsh._secure_restore_snapshot_entry(snapshot)
finally:
    dsh._ACTIVE_DSH_HOME = previous_active
    dsh._close_pinned_dsh_home(pinned_home)

assert not restored
assert stat.S_IMODE(replacement_payload.stat(follow_symlinks=False).st_mode) == 0o644
preserved_payload = preserved_home / "profiles" / "web" / payload.name
assert stat.S_IMODE(preserved_payload.stat(follow_symlinks=False).st_mode) == 0o644
PY

    [ "$status" -eq 0 ]
}

@test "DSH mode rollback reports descendant parent rebinds in an active lifecycle" {
    run env HOME="$TEST_HOME" python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import os
import stat
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = (Path(sys.argv[2]) / "mode-descendant-parent-swap").resolve()
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

content = b"managed bytes\n"
parent_variants = (
    Path("profiles/web"),
    Path("profiles/web/node_modules/@softspark/dsh-orchestrator/dist"),
)

for index, relative_parent in enumerate(parent_variants):
    dsh_home = root / f"dsh-home-{index}"
    parent = dsh_home / relative_parent
    parent.mkdir(parents=True)
    payload = parent / "payload.txt"
    payload.write_bytes(content)
    payload.chmod(0o644)
    managed_inode = payload.stat(follow_symlinks=False).st_ino
    snapshot = dsh._PathPrestate(payload, "file", 0o600, content=content)
    preserved_parent = parent.with_name(f"{parent.name}-managed")
    replacement_payload = parent / payload.name
    real_fchmod = os.fchmod
    injected = [False]

    def swap_descendant_parent_before_fchmod(descriptor, mode):
        if not injected[0]:
            injected[0] = True
            parent.rename(preserved_parent)
            parent.mkdir()
            replacement_payload.write_bytes(content)
            replacement_payload.chmod(0o644)
        real_fchmod(descriptor, mode)

    pinned_home = dsh._pin_dsh_home(dsh_home)
    previous_active = dsh._ACTIVE_DSH_HOME
    dsh._ACTIVE_DSH_HOME = pinned_home
    os.fchmod = swap_descendant_parent_before_fchmod
    try:
        residuals = dsh._restore_tree_prestate(dsh_home, {payload: snapshot})
    finally:
        os.fchmod = real_fchmod
        dsh._ACTIVE_DSH_HOME = previous_active
        dsh._close_pinned_dsh_home(pinned_home)

    assert injected[0], ("fd-based mode restoration was not reached", relative_parent)
    assert payload in residuals, (relative_parent, residuals)
    assert replacement_payload.read_bytes() == content
    assert stat.S_IMODE(
        replacement_payload.stat(follow_symlinks=False).st_mode
    ) == 0o644
    preserved_payload = preserved_parent / payload.name
    assert preserved_payload.read_bytes() == content
    assert preserved_payload.stat(follow_symlinks=False).st_ino == managed_inode
    assert stat.S_IMODE(
        preserved_payload.stat(follow_symlinks=False).st_mode
    ) == 0o600
PY

    [ "$status" -eq 0 ]
}

@test "DSH manifest rollback creates no temporary file in a replacement root" {
    run env HOME="$TEST_HOME" python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = (Path(sys.argv[2]) / "manifest-temp-root-swap").resolve()
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

dsh_home = root / "dsh-home"
profile = dsh_home / "profiles" / "web"
profile.mkdir(parents=True)
manifest = profile / "package.json"
manifest.write_bytes(b'{"dependencies":{"after":"2.0.0"}}\n')
expected = dsh._PathPrestate(
    manifest,
    "file",
    0o600,
    content=b'{"dependencies":{"before":"1.0.0"}}\n',
)
transaction = dsh._ProfileTransaction(
    profile,
    {profile: True},
    expected,
    {},
    {},
    latest_manifest=dsh._capture_entry(manifest),
)
pinned_home = dsh._pin_dsh_home(dsh_home)
previous_active = dsh._ACTIVE_DSH_HOME
dsh._ACTIVE_DSH_HOME = pinned_home
preserved_home = root / "dsh-home-preserved"
replacement_manifest_content = b'{"replacement":true}\n'
real_assert = dsh._assert_entry_unchanged
injected = [False]


def swap_root_after_manifest_check(entry, label):
    real_assert(entry, label)
    if label == "profile package manifest" and not injected[0]:
        injected[0] = True
        dsh_home.rename(preserved_home)
        replacement_profile = dsh_home / "profiles" / "web"
        replacement_profile.mkdir(parents=True)
        (replacement_profile / "package.json").write_bytes(
            replacement_manifest_content
        )


dsh._assert_entry_unchanged = swap_root_after_manifest_check
try:
    residuals = dsh._restore_manifest_prestate(transaction)
finally:
    dsh._assert_entry_unchanged = real_assert
    dsh._ACTIVE_DSH_HOME = previous_active
    dsh._close_pinned_dsh_home(pinned_home)

assert injected[0], "manifest mutation boundary was not reached"
assert manifest in residuals
replacement_profile = dsh_home / "profiles" / "web"
assert sorted(path.name for path in replacement_profile.iterdir()) == ["package.json"]
assert (replacement_profile / "package.json").read_bytes() == replacement_manifest_content
preserved_profile = preserved_home / "profiles" / "web"
assert not list(preserved_profile.glob(".package.dsh-rollback-*.tmp"))
PY

    [ "$status" -eq 0 ]
}

@test "DSH profile rollback preserves manifest and directory replacements" {
    run env HOME="$TEST_HOME" python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

root = (Path.home() / "rollback-races").resolve()
root.mkdir()


def create_concurrent(path, kind, label):
    preserved = path.with_name(f"{path.name}.{label}.managed")
    path.rename(preserved)
    if kind == "file":
        path.write_text(f"concurrent {label} file\n", encoding="utf-8")
    elif kind == "symlink":
        target = path.with_name(f"{path.name}.{label}.target")
        target.write_text(f"concurrent {label} symlink\n", encoding="utf-8")
        path.symlink_to(target)
    else:
        path.mkdir()
    return preserved


def assert_concurrent(path, kind, label):
    if kind == "file":
        assert path.read_text() == f"concurrent {label} file\n"
    elif kind == "symlink":
        assert path.is_symlink(), path
        assert path.read_text() == f"concurrent {label} symlink\n"
    else:
        assert path.is_dir() and not path.is_symlink(), path


for kind in ("file", "symlink", "directory"):
    profile = root / f"remove-{kind}"
    profile.mkdir()
    manifest = profile / "package.json"
    manifest.write_text('{"dependencies":{}}\n', encoding="utf-8")
    transaction = dsh._ProfileTransaction(
        profile,
        {profile: True},
        None,
        {},
        {},
        latest_manifest=dsh._capture_entry(manifest),
    )
    real_assert = dsh._assert_entry_unchanged
    injected = [False]

    def inject_remove_race(expected, label):
        real_assert(expected, label)
        if label == "profile package manifest" and not injected[0]:
            injected[0] = True
            create_concurrent(manifest, kind, "remove")

    dsh._assert_entry_unchanged = inject_remove_race
    try:
        residuals = dsh._restore_manifest_prestate(transaction)
    finally:
        dsh._assert_entry_unchanged = real_assert
    assert injected[0], ("remove", kind)
    assert_concurrent(manifest, kind, "remove")
    assert residuals, ("remove", kind)

for kind in ("file", "symlink", "directory"):
    profile = root / f"replace-{kind}"
    profile.mkdir()
    manifest = profile / "package.json"
    expected = dsh._PathPrestate(
        manifest,
        "file",
        0o600,
        content=b'{"dependencies":{"before":"1.0.0"}}\n',
    )
    manifest.write_text(
        '{"dependencies":{"after":"2.0.0"}}\n', encoding="utf-8"
    )
    transaction = dsh._ProfileTransaction(
        profile,
        {profile: True},
        expected,
        {},
        {},
        latest_manifest=dsh._capture_entry(manifest),
    )
    real_assert = dsh._assert_entry_unchanged
    assertions = [0]

    def inject_replace_race(expected_entry, label):
        real_assert(expected_entry, label)
        if label == "profile package manifest":
            assertions[0] += 1
            if assertions[0] == 2:
                create_concurrent(manifest, kind, "replace")

    dsh._assert_entry_unchanged = inject_replace_race
    try:
        residuals = dsh._restore_manifest_prestate(transaction)
    finally:
        dsh._assert_entry_unchanged = real_assert
    assert assertions[0] >= 2, ("replace", kind, assertions)
    assert_concurrent(manifest, kind, "replace")
    assert residuals, ("replace", kind)

for kind in ("file", "symlink", "directory"):
    profile = root / f"directory-{kind}"
    profile.mkdir()
    device, inode = dsh._entry_identity(profile)
    transaction = dsh._ProfileTransaction(
        profile,
        {profile: False},
        None,
        {},
        {profile: dsh._OwnedEntry(profile, device, inode, "directory")},
    )
    real_identity = dsh._entry_identity
    injected = [False]

    def inject_directory_race(path):
        identity = real_identity(path)
        if path == profile and not injected[0]:
            injected[0] = True
            create_concurrent(profile, kind, "directory")
        return identity

    dsh._entry_identity = inject_directory_race
    try:
        residuals = dsh._restore_profile_prestate(transaction)
    finally:
        dsh._entry_identity = real_identity
    assert injected[0], ("directory", kind)
    assert_concurrent(profile, kind, "directory")
    assert residuals, ("directory", kind)
PY

    [ "$status" -eq 0 ]
}

@test "DSH preset mutations reject descendant parent and claimed-child symlink swaps" {
    run env HOME="$TEST_HOME" python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = (Path(sys.argv[2]) / "descendant-containment").resolve()
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

dsh_home = root / "dsh"
presets = dsh_home / ".agent-presets"
source = dsh_home / "source"
presets.mkdir(parents=True)
source.mkdir()
(source / "preset.md").write_text("managed\n", encoding="utf-8")
outside = root / "outside"
outside.mkdir()

pinned = dsh._pin_dsh_home(dsh_home)
previous = dsh._ACTIVE_DSH_HOME
dsh._ACTIVE_DSH_HOME = pinned
real_assert = dsh._assert_dsh_home_binding
try:
    preserved_parent = dsh_home / ".agent-presets-preserved"
    injected = [False]

    def swap_parent_after_binding(home):
        real_assert(home)
        if not injected[0]:
            injected[0] = True
            presets.rename(preserved_parent)
            presets.symlink_to(outside, target_is_directory=True)

    dsh._assert_dsh_home_binding = swap_parent_after_binding
    try:
        dsh._claim_directory(presets / "staging", [])
    except (dsh.DshLifecycleError, OSError):
        pass
    else:
        raise AssertionError("claimed a directory through replaced preset parent")
    finally:
        dsh._assert_dsh_home_binding = real_assert
    assert injected[0]
    assert not (outside / "staging").exists()
    presets.unlink()
    preserved_parent.rename(presets)

    staging = presets / ".softspark-orchestrator.ai-toolkit-new"
    staging_owned = []
    dsh._claim_directory(staging, staging_owned)
    preserved_staging = presets / ".staging-preserved"
    injected = [False]

    def swap_claimed_child_after_binding(home):
        real_assert(home)
        if not injected[0]:
            injected[0] = True
            staging.rename(preserved_staging)
            staging.symlink_to(outside, target_is_directory=True)

    dsh._assert_dsh_home_binding = swap_claimed_child_after_binding
    try:
        dsh._copy_tree_exclusive(source, staging, staging_owned)
    except (dsh.DshLifecycleError, OSError):
        pass
    else:
        raise AssertionError("copied through replaced staging child")
    finally:
        dsh._assert_dsh_home_binding = real_assert
    assert injected[0]
    assert not (outside / "preset.md").exists()
    staging.unlink()
    preserved_staging.rename(staging)

    destination = presets / dsh.PRESET_NAME
    real_claim = dsh._claim_recovery_location
    preserved_marker = [None]

    def swap_marker_child(destination, suffix):
        location = real_claim(destination, suffix)
        preserved = location.root.path.with_name(
            f"{location.root.path.name}.preserved"
        )
        location.root.path.rename(preserved)
        location.root.path.symlink_to(outside, target_is_directory=True)
        preserved_marker[0] = preserved
        return location

    dsh._claim_recovery_location = swap_marker_child
    try:
        dsh._create_package_recovery_marker(destination)
    except (dsh.DshLifecycleError, OSError):
        pass
    else:
        raise AssertionError("wrote recovery marker through replaced child")
    finally:
        dsh._claim_recovery_location = real_claim
    assert preserved_marker[0] is not None
    assert not (outside / "RECOVERY.txt").exists()
finally:
    dsh._assert_dsh_home_binding = real_assert
    dsh._ACTIVE_DSH_HOME = previous
    dsh._close_pinned_dsh_home(pinned)
PY

    [ "$status" -eq 0 ]
}
