#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    export TEST_PROJECT; TEST_PROJECT="$(mktemp -d)"
    export TEST_HOME; TEST_HOME="$(mktemp -d)"
    export TEST_DSH_HOME; TEST_DSH_HOME="$(mktemp -d)"
}

teardown() {
    rm -rf "$TEST_PROJECT" "$TEST_HOME" "$TEST_DSH_HOME"
}

install_fake_dsh() {
    local fake_bin="$TEST_PROJECT/fake-bin"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/pnpm"
    chmod +x "$fake_bin/dsh"
    chmod +x "$fake_bin/pnpm"
    printf '%s\n' "$fake_bin"
}

install_fake_dsh_without_pnpm() {
    local fake_bin="$TEST_PROJECT/fake-bin-without-pnpm"
    mkdir -p "$fake_bin"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    ln -s "$(command -v python3)" "$fake_bin/python3"
    chmod +x "$fake_bin/dsh"
    printf '%s\n' "$fake_bin"
}

portable_mode() {
    python3 - "$1" <<'PY'
import os
import stat
import sys

print(f"{stat.S_IMODE(os.stat(sys.argv[1]).st_mode):o}")
PY
}

assert_no_dsh_lifecycle_artifacts() {
    [ ! -e "$TEST_DSH_HOME/.ai-toolkit-lifecycle.lock" ]
    [ ! -e "$TEST_DSH_HOME/profiles/web/package.json" ]
    [ ! -e "$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-codex" ]
    [ ! -e "$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-orchestrator" ]
    [ ! -e "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator" ]
    [ ! -e "$TEST_DSH_HOME/fake-argv.jsonl" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

validate_emitted() {
    env PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - "$1" <<'PY'
import sys
from pathlib import Path

from validate import ValidationResult, validate_emitted_agent_skills

result = ValidationResult()
validate_emitted_agent_skills(Path(sys.argv[1]), result)
raise SystemExit(1 if result.errors else 0)
PY
}

surface_fingerprint() {
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
        continue
    if stat.S_ISDIR(mode):
        records.append((relative, "dir", ""))
        pending.extend(sorted(path.iterdir(), reverse=True))
        continue
    if stat.S_ISREG(mode):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append((relative, "file", digest))
        continue
    records.append((relative, "other", oct(mode)))

for record in sorted(records):
    print("\t".join(record))
PY
}

project_tree_fingerprint() {
    python3 - "$1" <<'PY'
import hashlib
import os
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1])
pending = [root]
records = []
while pending:
    path = pending.pop()
    relative = "." if path == root else path.relative_to(root).as_posix()
    metadata = path.lstat()
    kind = stat.S_IFMT(metadata.st_mode)
    common = (
        relative,
        stat.S_IMODE(metadata.st_mode),
        metadata.st_mtime_ns,
    )
    if stat.S_ISLNK(kind):
        records.append((*common, "link", os.readlink(path)))
        continue
    if stat.S_ISDIR(kind):
        records.append((*common, "dir", ""))
        pending.extend(sorted(path.iterdir(), reverse=True))
        continue
    if stat.S_ISREG(kind):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append((*common, "file", metadata.st_size, digest))
        continue
    records.append((*common, "other", oct(kind)))

for record in sorted(records):
    print(repr(record))
PY
}

write_extends_fixture() {
    mkdir -p "$TEST_PROJECT/base-config"
    cat > "$TEST_PROJECT/base-config/ai-toolkit.config.json" <<'EOF'
{
  "name": "@test/dsh-base",
  "version": "1.0.0",
  "profile": "standard"
}
EOF
    cat > "$TEST_PROJECT/.softspark-toolkit.json" <<'EOF'
{
  "extends": "./base-config"
}
EOF
}

assert_uninstall_post_relocation_package_race() {
    local variant="$1"
    local fake_bin
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
    [ "$status" -eq 0 ]

    python3 - "$TEST_DSH_HOME/profiles/web" <<'PY'
import json
import sys
from pathlib import Path

profile = Path(sys.argv[1])
manifest = profile / "package.json"
document = json.loads(manifest.read_text())
document.setdefault("dependencies", {})["unrelated-package"] = "7.7.7"
manifest.write_text(json.dumps(document, sort_keys=True) + "\n")
unrelated = profile / "node_modules/unrelated-package"
unrelated.mkdir(parents=True)
(unrelated / "package.json").write_text(
    json.dumps({"name": "unrelated-package", "version": "7.7.7"}) + "\n"
)
PY

    local calls="$TEST_DSH_HOME/fake-argv.jsonl"
    local before_calls
    before_calls="$(wc -l < "$calls" | xargs)"
    local preset="$TEST_DSH_HOME/.agent-presets/softspark-orchestrator"
    local state="$TEST_HOME/.softspark/ai-toolkit/state.json"
    local before_preset
    before_preset="$(surface_fingerprint "$preset")"
    local before_state
    before_state="$(shasum "$state")"

    HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        run python3 - "$TOOLKIT_DIR" "$variant" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
variant = sys.argv[2]
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

real_relocate = dsh._relocate_owned_preset
injected = False


def relocate_then_race(expected, suffix, recovery_owned=None):
    global injected
    relocated = real_relocate(expected, suffix, recovery_owned)
    if suffix != "uninstall" or injected:
        return relocated
    injected = True
    profile = Path(dsh._dsh_home()) / "profiles/web"
    manifest = profile / "package.json"
    document = json.loads(manifest.read_text())
    if variant == "version":
        raced_value = "9.9.9"
        package_manifest = profile / "node_modules/@softspark/dsh-codex/package.json"
        package_document = json.loads(package_manifest.read_text())
        package_document["version"] = raced_value
        package_document["concurrent_change"] = True
        package_manifest.write_text(json.dumps(package_document, sort_keys=True) + "\n")
    elif variant == "malformed":
        raced_value = ["9.9.9"]
    else:
        raise AssertionError(f"unsupported race variant: {variant}")
    document["dependencies"]["@softspark/dsh-codex"] = raced_value
    manifest.write_text(json.dumps(document, sort_keys=True) + "\n")
    return relocated


dsh._relocate_owned_preset = relocate_then_race
status = dsh.main(["uninstall", "--profile", "web", "--yes"])
assert injected, "post-relocation package race injection was not reached"
raise SystemExit(status)
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"package inventory changed before external mutation"* ]]
    [[ "$output" != *"9.9.9"* ]]
    local after_calls
    after_calls="$(wc -l < "$calls" | xargs)"
    [ "$after_calls" -eq "$before_calls" ]
    [ "$(surface_fingerprint "$preset")" = "$before_preset" ]
    [ "$(shasum "$state")" = "$before_state" ]
    local recovery
    recovery="$(find "$TEST_DSH_HOME/.agent-presets" -mindepth 1 -maxdepth 1 \
        -name '.softspark-orchestrator.ai-toolkit-*' -print -quit)"
    [ -z "$recovery" ]

    python3 - "$TEST_DSH_HOME/profiles/web" "$variant" <<'PY'
import json
import sys
from pathlib import Path

profile = Path(sys.argv[1])
variant = sys.argv[2]
manifest = json.loads((profile / "package.json").read_text())
expected = "9.9.9" if variant == "version" else ["9.9.9"]
assert manifest["dependencies"]["@softspark/dsh-codex"] == expected, manifest
assert manifest["dependencies"]["unrelated-package"] == "7.7.7", manifest
unrelated = json.loads(
    (profile / "node_modules/unrelated-package/package.json").read_text()
)
assert unrelated == {"name": "unrelated-package", "version": "7.7.7"}, unrelated
if variant == "version":
    package = json.loads(
        (profile / "node_modules/@softspark/dsh-codex/package.json").read_text()
    )
    assert package["version"] == "9.9.9", package
    assert package["concurrent_change"] is True, package
PY
}

@test "dsh: selector is explicit-only and requires a local install" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" help
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'dsh (explicit project target;'

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" \
        python3 "$TOOLKIT_DIR/scripts/install.py" --editors dsh --dry-run
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Editor 'dsh' is project-local and requires --local"
}

@test "dsh project dry-run with extends leaves a lock-free project byte-for-byte unchanged" {
    write_extends_fixture
    before="$(project_tree_fingerprint "$TEST_PROJECT")"

    cd "$TEST_PROJECT"
    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" \
        python3 "$TOOLKIT_DIR/scripts/install.py" --local --editors dsh --dry-run

    [ "$status" -eq 0 ]
    [ ! -e "$TEST_PROJECT/.softspark-toolkit.lock.json" ]
    after="$(project_tree_fingerprint "$TEST_PROJECT")"
    [ "$after" = "$before" ]
}

@test "dsh project dry-run with extends preserves an existing lock byte-for-byte and mtime" {
    write_extends_fixture
    cat > "$TEST_PROJECT/.softspark-toolkit.lock.json" <<'EOF'
{"sentinel": true}
EOF
    python3 - "$TEST_PROJECT/.softspark-toolkit.lock.json" <<'PY'
import os
import subprocess
import sys

timestamp_ns = 1_600_000_000_123_456_789
os.utime(sys.argv[1], ns=(timestamp_ns, timestamp_ns))
PY
    before="$(project_tree_fingerprint "$TEST_PROJECT")"

    cd "$TEST_PROJECT"
    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" \
        python3 "$TOOLKIT_DIR/scripts/install.py" --local --editors dsh --dry-run

    [ "$status" -eq 0 ]
    after="$(project_tree_fingerprint "$TEST_PROJECT")"
    [ "$after" = "$before" ]
}

@test "dsh project real install and local update persist the current extends lock" {
    write_extends_fixture
    cd "$TEST_PROJECT"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" \
        python3 "$TOOLKIT_DIR/scripts/install.py" --local --editors dsh
    [ "$status" -eq 0 ]
    python3 - "$TEST_PROJECT/.softspark-toolkit.lock.json" "1.0.0" <<'PY'
import json
import sys
from pathlib import Path

lock = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert lock["resolved"]["@test/dsh-base"]["version"] == sys.argv[2]
PY

    python3 - "$TEST_PROJECT/base-config/ai-toolkit.config.json" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
config = json.loads(config_path.read_text(encoding="utf-8"))
config["version"] = "1.0.1"
config_path.write_text(json.dumps(config) + "\n", encoding="utf-8")
PY
    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" update --local --editors dsh
    [ "$status" -eq 0 ]
    python3 - "$TEST_PROJECT/.softspark-toolkit.lock.json" "1.0.1" <<'PY'
import json
import sys
from pathlib import Path

lock = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert lock["resolved"]["@test/dsh-base"]["version"] == sys.argv[2]
PY
}

@test "dsh project dry-run resolves npm extends without mutating empty or existing config cache" {
    fake_bin="$TEST_PROJECT/fake-npm-bin"
    mkdir -p "$fake_bin"
    cat > "$fake_bin/npm" <<'PY'
#!/usr/bin/env python3
import io
import sys
import tarfile
from pathlib import Path

destination = Path(sys.argv[sys.argv.index("--pack-destination") + 1])
tarball = destination / "test-dsh-remote-1.2.3.tgz"
payload = b'{"name":"@test/dsh-remote","version":"1.2.3","profile":"standard"}\n'
with tarfile.open(tarball, "w:gz") as archive:
    member = tarfile.TarInfo("package/ai-toolkit.config.json")
    member.size = len(payload)
    member.mtime = 1_600_000_000
    archive.addfile(member, io.BytesIO(payload))
print(tarball.name)
PY
    chmod +x "$fake_bin/npm"

    for cache_state in empty existing; do
        case_root="$TEST_PROJECT/npm-$cache_state"
        case_project="$case_root/project"
        case_data="$case_root/toolkit-data"
        cache_root="$case_data/config-cache"
        mkdir -p "$case_project" "$cache_root"
        cat > "$case_project/.softspark-toolkit.json" <<'EOF'
{"extends":"@test/dsh-remote@1.2.3"}
EOF
        if [ "$cache_state" = existing ]; then
            cached="$cache_root/@test/dsh-remote/1.2.3"
            mkdir -p "$cached"
            cat > "$cached/ai-toolkit.config.json" <<'EOF'
{"name":"@test/dsh-remote","version":"1.2.3","profile":"standard"}
EOF
        fi

        cache_before="$(project_tree_fingerprint "$cache_root")"
        project_before="$(project_tree_fingerprint "$case_project")"
        cd "$case_project"
        run env HOME="$TEST_HOME" AI_TOOLKIT_HOME="$case_data" \
            PATH="$fake_bin:$PATH" \
            python3 "$TOOLKIT_DIR/scripts/install.py" \
            --local --editors dsh --dry-run

        [ "$status" -eq 0 ]
        cache_after="$(project_tree_fingerprint "$cache_root")"
        project_after="$(project_tree_fingerprint "$case_project")"
        [ "$cache_after" = "$cache_before" ]
        [ "$project_after" = "$project_before" ]
    done
}

@test "dsh project dry-run resolves git extends without mutating empty or existing config cache" {
    fake_bin="$TEST_PROJECT/fake-git-bin"
    mkdir -p "$fake_bin"
    cat > "$fake_bin/git" <<'PY'
#!/usr/bin/env python3
import sys
from pathlib import Path

if sys.argv[1:] == ["--version"]:
    print("git version 2.0.0-test")
    raise SystemExit

destination = Path(sys.argv[-1])
destination.mkdir(parents=True, exist_ok=True)
(destination / "ai-toolkit.config.json").write_text(
    '{"name":"@test/dsh-git","version":"2.0.0","profile":"standard"}\n',
    encoding="utf-8",
)
PY
    chmod +x "$fake_bin/git"

    source_url="https://example.invalid/dsh-config.git"
    cache_key="$(python3 -c 'import hashlib, sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:16])' "$source_url")"
    for cache_state in empty existing; do
        case_root="$TEST_PROJECT/git-$cache_state"
        case_project="$case_root/project"
        case_data="$case_root/toolkit-data"
        cache_root="$case_data/config-cache"
        mkdir -p "$case_project" "$cache_root"
        cat > "$case_project/.softspark-toolkit.json" <<EOF
{"extends":"git+$source_url"}
EOF
        if [ "$cache_state" = existing ]; then
            cached="$cache_root/git/$cache_key"
            mkdir -p "$cached"
            cat > "$cached/ai-toolkit.config.json" <<'EOF'
{"name":"@test/dsh-git","version":"2.0.0","profile":"standard"}
EOF
        fi

        cache_before="$(project_tree_fingerprint "$cache_root")"
        project_before="$(project_tree_fingerprint "$case_project")"
        cd "$case_project"
        run env HOME="$TEST_HOME" AI_TOOLKIT_HOME="$case_data" \
            PATH="$fake_bin:$PATH" \
            python3 "$TOOLKIT_DIR/scripts/install.py" \
            --local --editors dsh --dry-run

        [ "$status" -eq 0 ]
        cache_after="$(project_tree_fingerprint "$cache_root")"
        project_after="$(project_tree_fingerprint "$case_project")"
        [ "$cache_after" = "$cache_before" ]
        [ "$project_after" = "$project_before" ]
    done
}

@test "dsh lifecycle: clean install uses exact plugin argv and owns the released preset" {
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -eq 0 ]
    python3 - "$TEST_DSH_HOME" "$TEST_HOME/.softspark/ai-toolkit/state.json" <<'PY'
import json
import sys
from pathlib import Path

dsh_home = Path(sys.argv[1])
state_path = Path(sys.argv[2])
calls = [json.loads(line) for line in (dsh_home / "fake-argv.jsonl").read_text().splitlines()]
assert calls == [
    ["plugin", "--profile", "web", "add", "@softspark/dsh-codex@1.0.0", "--save-exact"],
    ["plugin", "--profile", "web", "add", "@softspark/dsh-orchestrator@1.0.1", "--save-exact"],
], calls
preset = dsh_home / ".agent-presets" / "softspark-orchestrator"
assert (preset / "preset.md").read_text() == "softspark orchestrator\n"
state = json.loads(state_path.read_text())["dsh"]["profiles"]["web"]
assert state["dsh_home"] == str(dsh_home.resolve())
assert state["profile"] == "web"
assert state["packages"] == {
    "@softspark/dsh-codex": "1.0.0",
    "@softspark/dsh-orchestrator": "1.0.1",
}

assert set(state["package_trees"]) == set(state["packages"])

assert state["preset_path"] == str(preset.resolve())
assert len(state["preset_hash"]) == 64
assert state["owned"] is True
assert set(state) == {
    "dsh_home", "profile", "packages", "package_trees", "preset_path", "preset_hash",
    "owned", "installed_at", "last_updated",
}
PY
}

@test "dsh lifecycle: missing pnpm fails before every lifecycle mutation" {
    fake_bin="$(install_fake_dsh_without_pnpm)"
    python_bin="$(command -v python3)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" "$python_bin" - <<'PY'
from install_steps import dsh

raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"pnpm executable not found on PATH"* ]] || false
    [[ "$output" == *"install pnpm >=11.7.0,<12.0.0"* ]] || false
    assert_no_dsh_lifecycle_artifacts

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" "$python_bin" - <<'PY'
from install_steps import dsh

raise SystemExit(dsh.main(["install", "--profile", "web", "--dry-run"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"pnpm executable not found on PATH"* ]] || false
    assert_no_dsh_lifecycle_artifacts
}

@test "dsh lifecycle: broken pnpm probes fail closed without mutation" {
    python_bin="$(command -v python3)"
    python_dir="$(dirname "$python_bin")"
    for fixture in nonzero malformed below-minimum next-major timeout; do
        fake_bin="$(install_fake_dsh)"
        case "$fixture" in
            nonzero)
                printf '%s\n' \
                    '{"pnpm_fail_code":23,"pnpm_stderr":"NPM_TOKEN=PROBE_SECRET"}' \
                    > "$TEST_DSH_HOME/fake-control.json"
                ;;
            malformed)
                printf '%s\n' '{"pnpm_stdout":"pnpm eleven"}' \
                    > "$TEST_DSH_HOME/fake-control.json"
                ;;
            below-minimum)
                printf '%s\n' '{"pnpm_version":"11.6.9"}' \
                    > "$TEST_DSH_HOME/fake-control.json"
                ;;
            next-major)
                printf '%s\n' '{"pnpm_version":"12.0.0"}' \
                    > "$TEST_DSH_HOME/fake-control.json"
                ;;
            timeout)
                printf '%s\n' '{"pnpm_sleep_seconds":2}' \
                    > "$TEST_DSH_HOME/fake-control.json"
                ;;
        esac

        run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" \
            PATH="$fake_bin:$python_dir:/usr/bin:/bin" \
            PYTHONPATH="$TOOLKIT_DIR/scripts" "$python_bin" - "$fixture" <<'PY'
import sys

from install_steps import dsh

if sys.argv[1] == "timeout":
    dsh.PROBE_TIMEOUT_SECONDS = 1.0
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

        [ "$status" -ne 0 ]
        if [[ "$output" != *"pnpm prerequisite"* ]]; then
            echo "fixture=$fixture output=$output" >&2
            false
        fi
        [[ "$output" != *"PROBE_SECRET"* ]] || false
        assert_no_dsh_lifecycle_artifacts
    done
}

@test "dsh lifecycle: doctor reports pnpm prerequisite without writing" {
    fake_bin="$(install_fake_dsh)"
    before_dsh="$(surface_fingerprint "$TEST_DSH_HOME")"
    before_home="$(surface_fingerprint "$TEST_HOME")"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh doctor --profile web

    [ "$status" -ne 0 ]
    [[ "$output" == *"Package manager: supported (pnpm 11.24.0)"* ]] || false
    [ "$(surface_fingerprint "$TEST_DSH_HOME")" = "$before_dsh" ]
    [ "$(surface_fingerprint "$TEST_HOME")" = "$before_home" ]

    missing_bin="$(install_fake_dsh_without_pnpm)"
    python_bin="$(command -v python3)"
    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$missing_bin" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" "$python_bin" - <<'PY'
from install_steps import dsh

raise SystemExit(dsh.main(["doctor", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"Package manager: unsupported or missing"* ]] || false
    [[ "$output" == *"pnpm executable not found on PATH"* ]] || false
    [ "$(surface_fingerprint "$TEST_DSH_HOME")" = "$before_dsh" ]
    [ "$(surface_fingerprint "$TEST_HOME")" = "$before_home" ]
}

@test "dsh lifecycle: pnpm probe uses its resolved path and minimal environment" {
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        OPENAI_API_KEY=do-not-forward NPM_TOKEN=do-not-forward \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - "$fake_bin/pnpm" <<'PY'
import os
import subprocess
import sys
from pathlib import Path

from install_steps import dsh

expected = Path(sys.argv[1]).resolve()
real_run = subprocess.run
captured = {}


def inspect_probe(argv, **kwargs):
    captured["argv"] = argv
    captured["env"] = kwargs["env"]
    captured["shell"] = kwargs["shell"]
    return real_run(argv, **kwargs)


dsh.subprocess.run = inspect_probe
executable, version = dsh._find_supported_pnpm(Path(os.environ["DSH_HOME"]))
assert Path(executable) == expected
assert captured["argv"] == [str(expected), "--version"]
assert captured["shell"] is False
assert version == "11.24.0"
assert "OPENAI_API_KEY" not in captured["env"]
assert "NPM_TOKEN" not in captured["env"]
assert {"HOME", "DSH_HOME", "PATH"}.issubset(captured["env"])
PY

    [ "$status" -eq 0 ]
    assert_no_dsh_lifecycle_artifacts
}

@test "dsh lifecycle: prerequisite drift after lock fails before plugin mutation" {
    for race in replacement removal path-shadow; do
        case_root="$TEST_PROJECT/prerequisite-$race"
        case_home="$case_root/home"
        case_dsh="$case_root/dsh"
        fake_bin="$case_root/fake-bin"
        shadow_bin="$case_root/shadow-bin"
        mkdir -p "$case_home" "$case_dsh" "$fake_bin" "$shadow_bin"
        cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
        cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/pnpm"
        chmod +x "$fake_bin/dsh" "$fake_bin/pnpm"

        run env HOME="$case_home" DSH_HOME="$case_dsh" \
            PATH="$shadow_bin:$fake_bin:$PATH" PYTHONPATH="$TOOLKIT_DIR/scripts" \
            python3 - "$race" "$fake_bin/pnpm" "$shadow_bin/pnpm" <<'PY'
import shutil
import sys
from pathlib import Path

from install_steps import dsh

race = sys.argv[1]
pnpm = Path(sys.argv[2])
shadow = Path(sys.argv[3])
preserved = pnpm.with_name("pnpm.preflight")
real_acquire = dsh._acquire_lifecycle_lock


def acquire_then_race(dsh_home):
    lock = real_acquire(dsh_home)
    if race == "replacement":
        pnpm.rename(preserved)
        pnpm.write_text("#!/bin/sh\nprintf '11.24.0\\n'\n", encoding="utf-8")
        pnpm.chmod(0o755)
    elif race == "removal":
        pnpm.rename(preserved)
    elif race == "path-shadow":
        shutil.copy2(pnpm, shadow)
        shadow.chmod(0o755)
    else:
        raise AssertionError(race)
    return lock


dsh._acquire_lifecycle_lock = acquire_then_race
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

        [ "$status" -ne 0 ]
        [[ "$output" == *"prerequisite"* ]] || false
        [ ! -e "$case_dsh/fake-argv.jsonl" ]
        [ ! -e "$case_dsh/.ai-toolkit-lifecycle.lock" ]
        [ ! -e "$case_dsh/profiles/web/package.json" ]
        [ ! -e "$case_home/.softspark/ai-toolkit/state.json" ]
    done
}

@test "dsh lifecycle: verified pnpm directory leads the mutation PATH" {
    fake_bin="$(install_fake_dsh)"
    shadow_bin="$TEST_PROJECT/empty-shadow-bin"
    mkdir -p "$shadow_bin"
    printf '%s\n' '{"record_path":true}' > "$TEST_DSH_HOME/fake-control.json"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" \
        PATH="$shadow_bin:$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -eq 0 ]
    python3 - "$TEST_DSH_HOME/fake-path.jsonl" "$fake_bin" <<'PY'
import json
import os
import sys
from pathlib import Path

paths = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
expected = Path(sys.argv[2]).resolve()
assert len(paths) == 2, paths
assert all(Path(value.split(os.pathsep)[0]).resolve() == expected for value in paths), paths
PY
}

@test "dsh lifecycle: pnpm drift before the next mutation also blocks rollback" {
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - "$fake_bin/pnpm" <<'PY'
import sys
from pathlib import Path

from install_steps import dsh

pnpm = Path(sys.argv[1])
preserved = pnpm.with_name("pnpm.after-first-add")
real_run = dsh._run
injected = [False]


def drift_after_first_add(argv, *, dsh_home):
    result = real_run(argv, dsh_home=dsh_home)
    if "@softspark/dsh-codex@1.0.0" in argv and not injected[0]:
        injected[0] = True
        pnpm.rename(preserved)
    return result


dsh._run = drift_after_first_add
status = dsh.main(["install", "--profile", "web"])
assert injected[0]
raise SystemExit(status)
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"pnpm prerequisite"* ]] || false
    [[ "$output" == *"Recovery required"* ]] || false
    python3 - "$TEST_DSH_HOME/fake-argv.jsonl" <<'PY'
import json
import sys
from pathlib import Path

calls = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
assert calls == [[
    "plugin", "--profile", "web", "add",
    "@softspark/dsh-codex@1.0.0", "--save-exact",
]], calls
PY
    [ -e "$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-codex" ]
    [ ! -e "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: unsupported process groups fail before lifecycle writes" {
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from install_steps import dsh

dsh._mutation_process_groups_supported = lambda: False
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"process-group termination is unsupported"* ]] || false
    assert_no_dsh_lifecycle_artifacts
}

@test "dsh lifecycle: timeout kills delayed child and grandchild before rollback" {
    fake_bin="$(install_fake_dsh)"
    cat > "$TEST_DSH_HOME/fake-control.json" <<'JSON'
{
  "spawn_delayed_descendant_tree_before":"add:@softspark/dsh-codex",
  "descendant_delay_seconds":0.4,
  "descendant_host_sleep_seconds":5,
  "descendant_parent_sleep_seconds":5
}
JSON

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from install_steps import dsh

dsh.PACKAGE_MUTATION_TIMEOUT_SECONDS = 0.2
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"timed out after 0.2s"* ]] || false
    sleep 0.7
    [ ! -e "$TEST_DSH_HOME/late-descendant-marker.txt" ] || false
    [ ! -e "$TEST_DSH_HOME/profiles/web/late-descendant-profile-write.txt" ] || false
    [ ! -e "$TEST_DSH_HOME/profiles/web/package.json" ]
    [ ! -e "$TEST_DSH_HOME/.ai-toolkit-lifecycle.lock" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: interruption kills delayed child and grandchild before rollback" {
    fake_bin="$(install_fake_dsh)"
    cat > "$TEST_DSH_HOME/fake-control.json" <<'JSON'
{
  "spawn_delayed_descendant_tree_before":"add:@softspark/dsh-codex",
  "descendant_delay_seconds":0.4,
  "descendant_host_sleep_seconds":5,
  "descendant_parent_sleep_seconds":5
}
JSON

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
import os
import signal
import threading

from install_steps import dsh

real_run = dsh._run
injected = [False]


def interrupt_first_mutation(argv, *, dsh_home):
    if injected[0]:
        return real_run(argv, dsh_home=dsh_home)
    injected[0] = True
    timer = threading.Timer(0.2, lambda: os.kill(os.getpid(), signal.SIGINT))
    timer.start()
    try:
        return real_run(argv, dsh_home=dsh_home)
    finally:
        timer.cancel()


dsh._run = interrupt_first_mutation
status = dsh.main(["install", "--profile", "web"])
assert injected[0]
raise SystemExit(status)
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"interrupted"* ]] || false
    sleep 0.7
    [ ! -e "$TEST_DSH_HOME/late-descendant-marker.txt" ] || false
    [ ! -e "$TEST_DSH_HOME/profiles/web/late-descendant-profile-write.txt" ] || false
    [ ! -e "$TEST_DSH_HOME/profiles/web/package.json" ]
    [ ! -e "$TEST_DSH_HOME/.ai-toolkit-lifecycle.lock" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: repeated SIGINT cannot escape process-tree teardown" {
    fake_bin="$(install_fake_dsh)"
    cat > "$TEST_DSH_HOME/fake-control.json" <<'JSON'
{
  "spawn_delayed_descendant_tree_before":"add:@softspark/dsh-codex",
  "descendant_delay_seconds":0.4,
  "descendant_host_sleep_seconds":5,
  "descendant_parent_sleep_seconds":5
}
JSON

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
import os
import signal
import threading

from install_steps import dsh

real_signal_group = dsh._signal_process_group
real_wait_group = dsh._wait_for_process_group_exit
real_run = dsh._run
signal_interrupts = [2]
wait_interrupts = [2]
mutation_started = [False]


def repeatedly_interrupt_signal(process_group, signal_number):
    if signal_interrupts[0]:
        signal_interrupts[0] -= 1
        raise KeyboardInterrupt
    return real_signal_group(process_group, signal_number)


def repeatedly_interrupt_wait(process_group, timeout):
    if wait_interrupts[0]:
        wait_interrupts[0] -= 1
        raise KeyboardInterrupt
    return real_wait_group(process_group, timeout)


def interrupt_first_mutation(argv, *, dsh_home):
    if mutation_started[0]:
        return real_run(argv, dsh_home=dsh_home)
    mutation_started[0] = True
    timer = threading.Timer(0.2, lambda: os.kill(os.getpid(), signal.SIGINT))
    timer.start()
    try:
        return real_run(argv, dsh_home=dsh_home)
    finally:
        timer.cancel()


dsh._signal_process_group = repeatedly_interrupt_signal
dsh._wait_for_process_group_exit = repeatedly_interrupt_wait
dsh._run = interrupt_first_mutation
status = dsh.main(["install", "--profile", "web"])
assert mutation_started == [True]
assert signal_interrupts == [0]
assert wait_interrupts == [0]
print("teardown-retried-sigint")
raise SystemExit(status)
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"interrupted"* ]] || false
    [[ "$output" == *"teardown-retried-sigint"* ]] || false
    [[ "$output" != *"Traceback"* ]] || false
    sleep 0.7
    [ ! -e "$TEST_DSH_HOME/late-descendant-marker.txt" ] || false
    [ ! -e "$TEST_DSH_HOME/profiles/web/late-descendant-profile-write.txt" ] || false
    [ ! -e "$TEST_DSH_HOME/profiles/web/package.json" ]
    [ ! -e "$TEST_DSH_HOME/.ai-toolkit-lifecycle.lock" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: SIGINT after Popen return cannot escape process-tree teardown" {
    fake_bin="$(install_fake_dsh)"
    printf '%s\n' \
        '{"sleep_before":"add:@softspark/dsh-codex","sleep_seconds":5}' \
        > "$TEST_DSH_HOME/fake-control.json"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
import os
import signal

from install_steps import dsh

real_run = dsh._run
real_popen = dsh.subprocess.Popen
spawned = []
boundary_reached = [False]


def interrupting_popen(*args, **kwargs):
    process = real_popen(*args, **kwargs)
    spawned.append(process)
    boundary_reached[0] = True
    os.kill(os.getpid(), signal.SIGINT)
    return process


def run_with_spawn_boundary(argv, *, dsh_home):
    dsh.subprocess.Popen = interrupting_popen
    try:
        return real_run(argv, dsh_home=dsh_home)
    finally:
        dsh.subprocess.Popen = real_popen


dsh._run = run_with_spawn_boundary
status = dsh.main(["install", "--profile", "web"])
assert boundary_reached == [True]
assert len(spawned) == 1
process = spawned[0]
survived = process.poll() is None
if survived:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.communicate(timeout=2)
assert not survived, "spawned DSH process escaped teardown"
print("post-popen-sigint-teardown-confirmed")
raise SystemExit(status)
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"interrupted"* ]] || false
    [[ "$output" == *"post-popen-sigint-teardown-confirmed"* ]] || false
    [[ "$output" != *"Traceback"* ]] || false
    [ ! -e "$TEST_DSH_HOME/.ai-toolkit-lifecycle.lock" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: SIGINT after communicate cannot bypass final PGID teardown" {
    fake_bin="$(install_fake_dsh)"
    printf '%s\n' \
        '{"success_noop":"add:@softspark/dsh-codex"}' \
        > "$TEST_DSH_HOME/fake-control.json"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
import os
import signal

from install_steps import dsh

real_group_exists = dsh._process_group_exists
real_terminate = dsh._terminate_mutation_process_tree
boundary_reached = [False]
teardown_calls = [0]


def interrupt_before_final_group_check(process_group):
    if not boundary_reached[0]:
        boundary_reached[0] = True
        os.kill(os.getpid(), signal.SIGINT)
    return real_group_exists(process_group)


def record_teardown(process, *, profile):
    teardown_calls[0] += 1
    return real_terminate(process, profile=profile)


dsh._process_group_exists = interrupt_before_final_group_check
dsh._terminate_mutation_process_tree = record_teardown
status = dsh.main(["install", "--profile", "web"])
assert boundary_reached == [True]
assert teardown_calls == [1]
print("post-communicate-sigint-teardown-confirmed")
raise SystemExit(status)
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"interrupted"* ]] || false
    [[ "$output" == *"post-communicate-sigint-teardown-confirmed"* ]] || false
    [[ "$output" != *"Traceback"* ]] || false
    [ ! -e "$TEST_DSH_HOME/.ai-toolkit-lifecycle.lock" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: unconfirmed process-tree exit blocks package rollback" {
    fake_bin="$(install_fake_dsh)"
    cat > "$TEST_DSH_HOME/fake-control.json" <<'JSON'
{"sleep_before":"add:@softspark/dsh-orchestrator","sleep_seconds":5}
JSON

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from install_steps import dsh

dsh.PACKAGE_MUTATION_TIMEOUT_SECONDS = 0.2
dsh.PROCESS_TERMINATION_GRACE_SECONDS = 0.05
dsh._wait_for_process_group_exit = lambda process_group, timeout: False
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"process tree termination could not be confirmed"* ]] || false
    [[ "$output" == *"package recovery is blocked"* ]] || false
    python3 - "$TEST_DSH_HOME/fake-argv.jsonl" <<'PY'
import json
import sys
from pathlib import Path

calls = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
assert calls == [
    ["plugin", "--profile", "web", "add", "@softspark/dsh-codex@1.0.0", "--save-exact"],
    ["plugin", "--profile", "web", "add", "@softspark/dsh-orchestrator@1.0.1", "--save-exact"],
], calls
PY
    [ -e "$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-codex" ]
    [ ! -e "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: unconfirmed rollback tree aborts all later restoration" {
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from pathlib import Path

from install_steps import dsh

home = Path(dsh._dsh_home())
profile_restore_marker = home / "unexpected-profile-restore"
state_restore_marker = home / "unexpected-state-restore"
recovery_calls = []
real_claim = dsh._claim_directory
real_run = dsh._run


def fail_after_packages(path, owned, *, mode=0o700):
    if path == home / ".agent-presets":
        raise dsh.DshLifecycleError("injected primary preset failure")
    return real_claim(path, owned, mode=mode)


def unconfirmed_first_recovery(argv, *, dsh_home):
    if "remove" in argv:
        recovery_calls.append(list(argv))
        raise dsh._ProcessTreeTerminationError(
            "DSH recovery process tree termination could not be confirmed; "
            "package recovery is blocked",
            process_group=424242,
            profile="web",
        )
    return real_run(argv, dsh_home=dsh_home)


def unexpected_profile_restore(*args, **kwargs):
    profile_restore_marker.write_text("called\n", encoding="utf-8")


def unexpected_state_restore(*args, **kwargs):
    state_restore_marker.write_text("called\n", encoding="utf-8")


dsh._claim_directory = fail_after_packages
dsh._run = unconfirmed_first_recovery
dsh._safe_restore_profile_prestate = unexpected_profile_restore
dsh._safe_restore_state = unexpected_state_restore
status = dsh.main(["install", "--profile", "web"])
assert len(recovery_calls) == 1, recovery_calls
assert recovery_calls[0][1:] == [
    "plugin", "--profile", "web", "remove", "@softspark/dsh-orchestrator",
], recovery_calls
print("rollback-tree-boundary-reached")
raise SystemExit(status)
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"rollback-tree-boundary-reached"* ]] || false
    [[ "$output" == *"injected primary preset failure"* ]] || false
    [[ "$output" == *"recovery process tree termination could not be confirmed"* ]] \
        || false
    [[ "$output" != *"CHILD_SECRET"* ]] || false
    [ ! -e "$TEST_DSH_HOME/unexpected-profile-restore" ]
    [ ! -e "$TEST_DSH_HOME/unexpected-state-restore" ]

    recovery_gate="$(find "$TEST_DSH_HOME" -mindepth 1 -maxdepth 1 -type f \
        -name '.ai-toolkit-lifecycle-tree-recovery-*' -print -quit)"
    [ -n "$recovery_gate" ]
    grep -q '^reason=unconfirmed-process-tree$' "$recovery_gate"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh doctor --profile web

    [ "$status" -ne 0 ]
    [[ "$output" == *"Recovery gate: unconfirmed DSH process tree"* ]] || false
    [[ "$output" == *"$recovery_gate"* ]] || false

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -ne 0 ]
    [[ "$output" == *"lifecycle recovery gate blocks mutation"* ]] || false
}

@test "dsh lifecycle: unconfirmed process-tree exit leaves a durable recovery gate" {
    fake_bin="$(install_fake_dsh)"
    cat > "$TEST_DSH_HOME/fake-control.json" <<'JSON'
{"sleep_before":"add:@softspark/dsh-orchestrator","sleep_seconds":5}
JSON

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from install_steps import dsh

dsh.PACKAGE_MUTATION_TIMEOUT_SECONDS = 0.2
dsh.PROCESS_TERMINATION_GRACE_SECONDS = 0.05
dsh._wait_for_process_group_exit = lambda process_group, timeout: False
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    gate="$TEST_DSH_HOME/.ai-toolkit-lifecycle.lock"
    [ -f "$gate" ]
    grep -q '^state=recovery$' "$gate"
    grep -q '^reason=unconfirmed-process-tree$' "$gate"
    grep -Eq '^process_group=[1-9][0-9]*$' "$gate"
    grep -q '^profile=web$' "$gate"
    recovery_sentinel="$(find "$TEST_DSH_HOME" -mindepth 1 -maxdepth 1 -type f \
        -name '.ai-toolkit-lifecycle-tree-recovery-*' -print -quit)"
    [ -n "$recovery_sentinel" ]
    grep -q '^reason=unconfirmed-process-tree$' "$recovery_sentinel"
    calls_before="$(wc -l < "$TEST_DSH_HOME/fake-argv.jsonl" | tr -d ' ')"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from install_steps import dsh

dsh.LIFECYCLE_LOCK_TIMEOUT_SECONDS = 0.05
commands = [
    ["install", "--profile", "web"],
    ["update", "--profile", "web"],
    ["uninstall", "--profile", "web", "--yes"],
]
for command in commands:
    assert dsh.main(command) == 1
    print(f"blocked:{command[0]}")
PY

    [ "$status" -eq 0 ]
    [[ "$output" == *"lifecycle recovery gate blocks mutation"* ]] || false
    [[ "$output" == *"blocked:install"* ]] || false
    [[ "$output" == *"blocked:update"* ]] || false
    [[ "$output" == *"blocked:uninstall"* ]] || false
    [ "$(wc -l < "$TEST_DSH_HOME/fake-argv.jsonl" | tr -d ' ')" = "$calls_before" ]

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh doctor --profile alternate

    [ "$status" -ne 0 ]
    [[ "$output" == *"Recovery gate: unconfirmed DSH process tree"* ]] || false
    [[ "$output" == *"verify that process group"* ]] || false
    [[ "$output" == *"$TEST_DSH_HOME/profiles/web"* ]] || false
    [[ "$output" != *"$TEST_DSH_HOME/profiles/alternate"* ]] || false
    [[ "$output" == *"remove only after manual verification"* ]] || false
    [ -f "$gate" ]
}

@test "dsh lifecycle: canonical lock loss preserves a recognized recovery gate" {
    for race in removed renamed replaced; do
        case_root="$TEST_PROJECT/process-tree-gate-$race"
        case_home="$case_root/home"
        case_dsh="$case_root/dsh"
        fake_bin="$case_root/fake-bin"
        mkdir -p "$case_home" "$case_dsh" "$fake_bin"
        cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
        cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/pnpm"
        chmod +x "$fake_bin/dsh" "$fake_bin/pnpm"
        printf '%s\n' \
            '{"sleep_before":"add:@softspark/dsh-orchestrator","sleep_seconds":5}' \
            > "$case_dsh/fake-control.json"

        run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
            PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - "$race" <<'PY'
import sys
from pathlib import Path

from install_steps import dsh

race = sys.argv[1]
real_preserve = dsh._preserve_lifecycle_recovery_gate


def race_canonical_lock(lock, termination):
    if race == "removed":
        lock.path.unlink()
    elif race == "renamed":
        lock.path.rename(lock.path.with_name("renamed-original-lock"))
    elif race == "replaced":
        lock.path.rename(lock.path.with_name("replaced-original-lock"))
        lock.path.write_text("foreign concurrent lock\n", encoding="utf-8")
    else:
        raise AssertionError(race)
    return real_preserve(lock, termination)


dsh._preserve_lifecycle_recovery_gate = race_canonical_lock
dsh.PACKAGE_MUTATION_TIMEOUT_SECONDS = 0.2
dsh.PROCESS_TERMINATION_GRACE_SECONDS = 0.05
dsh._wait_for_process_group_exit = lambda process_group, timeout: False
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

        [ "$status" -ne 0 ]
        recovery_gate="$(find "$case_dsh" -mindepth 1 -maxdepth 1 -type f \
            -name '.ai-toolkit-lifecycle-tree-recovery-*' -print -quit)"
        [ -n "$recovery_gate" ]
        grep -q '^state=recovery$' "$recovery_gate"
        grep -q '^reason=unconfirmed-process-tree$' "$recovery_gate"
        grep -q '^profile=web$' "$recovery_gate"

        case "$race" in
            removed)
                [ ! -e "$case_dsh/.ai-toolkit-lifecycle.lock" ]
                ;;
            renamed)
                grep -Eq '^pid=[1-9][0-9]*$' "$case_dsh/renamed-original-lock"
                [ ! -e "$case_dsh/.ai-toolkit-lifecycle.lock" ]
                ;;
            replaced)
                [ "$(cat "$case_dsh/.ai-toolkit-lifecycle.lock")" = \
                    "foreign concurrent lock" ]
                grep -Eq '^pid=[1-9][0-9]*$' "$case_dsh/replaced-original-lock"
                ;;
        esac

        calls_before="$(wc -l < "$case_dsh/fake-argv.jsonl" | tr -d ' ')"
        run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
            PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from install_steps import dsh

dsh.LIFECYCLE_LOCK_TIMEOUT_SECONDS = 0.05
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

        [ "$status" -ne 0 ]
        [[ "$output" == *"lifecycle recovery gate blocks mutation"* ]] || false
        [ "$(wc -l < "$case_dsh/fake-argv.jsonl" | tr -d ' ')" = "$calls_before" ]

        run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
            node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh doctor --profile alternate

        [ "$status" -ne 0 ]
        [[ "$output" == *"Recovery gate: unconfirmed DSH process tree"* ]] || false
        [[ "$output" == *"$recovery_gate"* ]] || false
        [[ "$output" == *"$case_dsh/profiles/web"* ]] || false
    done
}

@test "dsh lifecycle: pinned directory lock closes the pre-sentinel race" {
    fake_bin="$(install_fake_dsh)"
    ready="$TEST_PROJECT/pre-sentinel-ready"
    release="$TEST_PROJECT/pre-sentinel-release"
    process_a_output="$TEST_PROJECT/process-a-output"
    printf '%s\n' \
        '{"sleep_before":"add:@softspark/dsh-orchestrator","sleep_seconds":5}' \
        > "$TEST_DSH_HOME/fake-control.json"

    env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - "$ready" "$release" \
        > "$process_a_output" 2>&1 <<'PY' &
import sys
import time
from pathlib import Path

from install_steps import dsh

ready = Path(sys.argv[1])
release = Path(sys.argv[2])
canonical = Path(dsh._dsh_home()) / ".ai-toolkit-lifecycle.lock"
displaced = canonical.with_name("paused-original-lock")
real_create_gate = dsh._create_process_tree_recovery_gate


def pause_before_sentinel(home, payload):
    canonical.rename(displaced)
    ready.write_text("ready\n", encoding="utf-8")
    deadline = time.monotonic() + 10
    while not release.exists():
        if time.monotonic() >= deadline:
            raise AssertionError("barrier release timed out")
        time.sleep(0.01)
    return real_create_gate(home, payload)


dsh._create_process_tree_recovery_gate = pause_before_sentinel
dsh.PACKAGE_MUTATION_TIMEOUT_SECONDS = 0.2
dsh.PROCESS_TERMINATION_GRACE_SECONDS = 0.05
dsh._wait_for_process_group_exit = lambda process_group, timeout: False
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY
    process_a_pid=$!

    for _ in $(seq 1 500); do
        [ -e "$ready" ] && break
        sleep 0.01
    done
    [ -e "$ready" ]

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from install_steps import dsh

dsh.LIFECYCLE_LOCK_TIMEOUT_SECONDS = 0.05
dsh._install = lambda **kwargs: "SECOND_LIFECYCLE_ENTERED"
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY
    process_b_status="$status"
    process_b_output="$output"

    printf '%s\n' 'release' > "$release"
    if wait "$process_a_pid"; then
        process_a_status=0
    else
        process_a_status=$?
    fi

    [ "$process_b_status" -ne 0 ]
    [[ "$process_b_output" == *"DSH home directory lifecycle lock is busy"* ]] \
        || false
    [[ "$process_b_output" != *"SECOND_LIFECYCLE_ENTERED"* ]] || false
    [ "$process_a_status" -ne 0 ]

    recovery_gate="$(find "$TEST_DSH_HOME" -mindepth 1 -maxdepth 1 -type f \
        -name '.ai-toolkit-lifecycle-tree-recovery-*' -print -quit)"
    [ -n "$recovery_gate" ]
    grep -q '^reason=unconfirmed-process-tree$' "$recovery_gate"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from install_steps import dsh

dsh._install = lambda **kwargs: "THIRD_LIFECYCLE_ENTERED"
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"lifecycle recovery gate blocks mutation"* ]] || false
    [[ "$output" != *"THIRD_LIFECYCLE_ENTERED"* ]] || false
}

@test "dsh lifecycle: cold add can exceed the legacy scaled timeout below the mutation bound" {
    fake_bin="$(install_fake_dsh)"
    printf '%s\n' \
        '{"sleep_before":"add:@softspark/dsh-codex","sleep_seconds":0.08}' \
        > "$TEST_DSH_HOME/fake-control.json"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from install_steps import dsh

assert dsh.PACKAGE_MUTATION_TIMEOUT_SECONDS == 300
dsh.PACKAGE_MUTATION_TIMEOUT_SECONDS = 0.2
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -eq 0 ]
    [ -e "$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-codex" ]
    [ -e "$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-orchestrator" ]
}

@test "dsh lifecycle: lock is bounded, rejects nonregular entries, and releases only its inode" {
    fake_bin="$(install_fake_dsh)"
    lock="$TEST_DSH_HOME/.ai-toolkit-lifecycle.lock"

    for kind in file directory symlink; do
        rm -f "$lock" 2>/dev/null || true
        rmdir "$lock" 2>/dev/null || true
        case "$kind" in
            file) printf '%s\n' 'concurrent lifecycle' > "$lock" ;;
            directory) mkdir "$lock" ;;
            symlink)
                printf '%s\n' 'foreign lock target' > "$TEST_DSH_HOME/foreign-lock"
                ln -s "$TEST_DSH_HOME/foreign-lock" "$lock"
                ;;
        esac

        before=$(surface_fingerprint "$TEST_DSH_HOME")
        run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
            node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

        [ "$status" -ne 0 ]
        if [ "$kind" = file ]; then
            [[ "$output" == *"lifecycle lock timed out"* ]]
        else
            [[ "$output" == *"lifecycle lock is not a regular file"* ]]
        fi
        after=$(surface_fingerprint "$TEST_DSH_HOME")
        [ "$after" = "$before" ]
    done

    rm "$lock"
    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from pathlib import Path

from install_steps import dsh

lock = Path(dsh._dsh_home()) / ".ai-toolkit-lifecycle.lock"


def replace_lock(*, profile, dry_run, pinned_home=None):
    if lock.exists():
        lock.unlink()
    lock.write_text("concurrent replacement\n", encoding="utf-8")


dsh._install = replace_lock
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"lifecycle lock identity changed"* ]]
    replacement="$(find "$TEST_DSH_HOME" -mindepth 1 -maxdepth 1 -type f \
        -name '.ai-toolkit-lifecycle-lock-release-*' -print -quit)"
    [ -n "$replacement" ]
    [ "$(cat "$replacement")" = "concurrent replacement" ]
}

@test "dsh lifecycle: install preserves both DSH roots when home is replaced after lock" {
    fake_bin="$(install_fake_dsh)"
    displaced="$TEST_PROJECT/dsh-displaced-after-lock"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - \
        "$TEST_DSH_HOME" "$displaced" <<'PY'
import sys
from pathlib import Path

from install_steps import dsh

home = Path(sys.argv[1])
displaced = Path(sys.argv[2])
real_install = dsh._install
injected = [False]


def replace_home_after_lock(*, profile, dry_run, pinned_home=None):
    if not injected[0]:
        injected[0] = True
        home.rename(displaced)
        home.mkdir()
        (home / "replacement-sentinel.txt").write_text("preserve replacement\n")
    if pinned_home is None:
        return real_install(profile=profile, dry_run=dry_run)
    return real_install(
        profile=profile,
        dry_run=dry_run,
        pinned_home=pinned_home,
    )


dsh._install = replace_home_after_lock
status = dsh.main(["install", "--profile", "web"])
assert injected[0], "post-lock DSH root boundary was not reached"
assert status == 1, status
assert (home / "replacement-sentinel.txt").read_text() == "preserve replacement\n"
assert not (home / "fake-argv.jsonl").exists()
assert not (displaced / "fake-argv.jsonl").exists()
assert not (home / ".ai-toolkit-lifecycle.lock").exists()
assert not (displaced / ".ai-toolkit-lifecycle.lock").exists()
assert not (Path.home() / ".softspark/ai-toolkit/state.json").exists()
PY

    [ "$status" -eq 0 ]
    [[ "$output" == *"DSH home identity changed"* ]]
}

@test "dsh lifecycle: update and uninstall reject a DSH home replaced after lock" {
    fake_bin="$(install_fake_dsh)"
    for operation in update uninstall; do
        case_root="$TEST_PROJECT/root-swap-$operation"
        case_home="$case_root/home"
        case_dsh="$case_root/dsh"
        displaced="$case_root/dsh-displaced"
        mkdir -p "$case_home" "$case_dsh"

        run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
            node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
        [ "$status" -eq 0 ]

        run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
            PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - \
            "$operation" "$case_dsh" "$displaced" <<'PY'
import sys
from pathlib import Path

from install_steps import dsh

operation = sys.argv[1]
home = Path(sys.argv[2])
displaced = Path(sys.argv[3])
state_path = Path.home() / ".softspark/ai-toolkit/state.json"
state_before = state_path.read_bytes()
calls_before = (home / "fake-argv.jsonl").read_bytes()
real_operation = getattr(dsh, f"_{operation}")
injected = [False]


def replace_home_after_lock(**kwargs):
    if not injected[0]:
        injected[0] = True
        home.rename(displaced)
        home.mkdir()
        (home / "replacement-sentinel.txt").write_text("preserve replacement\n")
    return real_operation(**kwargs)


setattr(dsh, f"_{operation}", replace_home_after_lock)
argv = [operation, "--profile", "web"]
if operation == "uninstall":
    argv.append("--yes")
status = dsh.main(argv)
assert injected[0], "post-lock DSH root boundary was not reached"
assert status == 1, status
assert state_path.read_bytes() == state_before
assert (displaced / "fake-argv.jsonl").read_bytes() == calls_before
assert not (home / "fake-argv.jsonl").exists()
assert (home / "replacement-sentinel.txt").read_text() == "preserve replacement\n"
assert not (home / ".ai-toolkit-lifecycle.lock").exists()
assert not (displaced / ".ai-toolkit-lifecycle.lock").exists()
PY

        [ "$status" -eq 0 ]
        [[ "$output" == *"DSH home identity changed"* ]]
    done
}

@test "dsh lifecycle: root swaps at external and internal mutation boundaries stop install" {
    fake_bin="$(install_fake_dsh)"
    for boundary in after_external before_internal_mutation; do
        case_root="$TEST_PROJECT/root-swap-boundary-$boundary"
        case_home="$case_root/home"
        case_dsh="$case_root/dsh"
        displaced="$case_root/dsh-displaced"
        mkdir -p "$case_home" "$case_dsh"

        run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
            PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - \
            "$boundary" "$case_dsh" "$displaced" <<'PY'
import sys
from pathlib import Path

from install_steps import dsh

boundary = sys.argv[1]
home = Path(sys.argv[2])
displaced = Path(sys.argv[3])
injected = [False]


def swap_home():
    injected[0] = True
    home.rename(displaced)
    home.mkdir()
    (home / "replacement-sentinel.txt").write_text("preserve replacement\n")


if boundary == "after_external":
    real_run = dsh._run

    def run_then_swap(argv, *, dsh_home):
        result = real_run(argv, dsh_home=dsh_home)
        if "plugin" in argv and not injected[0]:
            swap_home()
        return result

    dsh._run = run_then_swap
else:
    real_claim = dsh._claim_directory

    def swap_before_claim(path, owned, *, mode=0o700):
        if not injected[0]:
            swap_home()
        return real_claim(path, owned, mode=mode)

    dsh._claim_directory = swap_before_claim

status = dsh.main(["install", "--profile", "web"])
assert injected[0], f"{boundary} was not reached"
assert status == 1, status
assert (home / "replacement-sentinel.txt").read_text() == "preserve replacement\n"
assert not (home / "fake-argv.jsonl").exists()
assert not (home / ".agent-presets").exists()
assert not (home / ".ai-toolkit-lifecycle.lock").exists()
assert not (displaced / ".ai-toolkit-lifecycle.lock").exists()
assert not (Path.home() / ".softspark/ai-toolkit/state.json").exists()
calls = (displaced / "fake-argv.jsonl").read_text().splitlines()
if boundary == "after_external":
    assert len(calls) == 1, calls
else:
    assert len(calls) == 2, calls
PY

        [ "$status" -eq 0 ]
        [[ "$output" == *"DSH home identity changed"* ]]
    done
}

@test "dsh lifecycle: user preset collision refuses before the first plugin mutation" {
    fake_bin="$(install_fake_dsh)"
    preset="$TEST_DSH_HOME/.agent-presets/softspark-orchestrator"
    mkdir -p "$preset"
    printf '%s\n' 'user-owned preset' > "$preset/preset.md"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'preset collision'
    [ "$(cat "$preset/preset.md")" = 'user-owned preset' ]
    [ ! -e "$TEST_DSH_HOME/fake-argv.jsonl" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: concurrent preset directory file and symlink are never removed" {
    for kind in directory file symlink; do
        case_home="$(mktemp -d)"
        fake_bin="$(install_fake_dsh)"
        printf '{"preset_race_after_add":"%s"}\n' "$kind" > \
            "$case_home/fake-control.json"

        run env HOME="$TEST_HOME" DSH_HOME="$case_home" PATH="$fake_bin:$PATH" \
            node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

        [ "$status" -ne 0 ]
        destination="$case_home/.agent-presets/softspark-orchestrator"
        if [ "$kind" = file ]; then
            [ "$(cat "$destination")" = 'concurrent user data' ]
        else
            [ "$(cat "$destination/keep.txt")" = 'concurrent user data' ]
        fi
        [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
    done
}

@test "dsh lifecycle: install copy failure preserves concurrent additions" {
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from pathlib import Path

from install_steps import dsh

real_copytree = dsh._copy_tree_exclusive
calls = 0

def fail_second_copy(source, destination, owned):
    global calls
    calls += 1
    if calls == 2:
        destination = Path(destination)
        (destination / "keep.txt").write_text(
            "concurrent user data\n", encoding="utf-8"
        )
        raise OSError("injected preset copy failure")
    return real_copytree(source, destination, owned)

dsh._copy_tree_exclusive = fail_second_copy
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"Recovery required"* ]]
    [[ "$output" == *"softspark-orchestrator"* ]]
    [ "$(cat "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator/keep.txt")" = \
        'concurrent user data' ]
    find "$TEST_DSH_HOME/.agent-presets" -mindepth 1 -maxdepth 1 \
        -type d -name '.softspark-orchestrator.ai-toolkit-package.*' | grep -q .
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: install rollback owns only its empty preset parent" {
    fake_bin="$(install_fake_dsh)"
    for concurrent in no yes; do
        case_root="$(mktemp -d)"
        case_home="$case_root/home"
        case_dsh="$case_root/dsh"
        mkdir -p "$case_home" "$case_dsh"

        run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
            PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - "$concurrent" <<'PY'
import os
import sys
from pathlib import Path

from install_steps import dsh

concurrent = sys.argv[1] == "yes"

def fail_state(**_kwargs):
    if concurrent:
        parent = Path(os.environ["DSH_HOME"]).resolve() / ".agent-presets"
        (parent / "concurrent.txt").write_text("concurrent user bytes\n")
    raise OSError("injected state failure")

dsh.record_dsh_profile = fail_state
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

        [ "$status" -ne 0 ]
        parent="$case_dsh/.agent-presets"
        if [ "$concurrent" = no ]; then
            [ ! -e "$parent" ]
        else
            [ "$(cat "$parent/concurrent.txt")" = "concurrent user bytes" ]
            [[ "$output" == *"Recovery required"* ]]
            [[ "$output" == *"'$parent'"* ]]
            find "$parent" -mindepth 1 -maxdepth 1 -type d \
                -name '.softspark-orchestrator.ai-toolkit-package.*' | grep -q .
        fi
    done
}

@test "dsh lifecycle: same-name unowned plugin collision refuses before mutation" {
    fake_bin="$(install_fake_dsh)"
    profile="$TEST_DSH_HOME/profiles/web"
    mkdir -p "$profile"
    cat > "$profile/package.json" <<'JSON'
{"dependencies":{"@softspark/dsh-codex":"9.9.9","unrelated":"2.0.0"}}
JSON
    before="$(shasum "$profile/package.json")"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'plugin collision'
    [ "$(shasum "$profile/package.json")" = "$before" ]
    [ ! -e "$TEST_DSH_HOME/fake-argv.jsonl" ]
    [ ! -e "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: malformed managed dependency values fail closed unchanged" {
    fake_bin="$(install_fake_dsh)"
    for package in @softspark/dsh-codex @softspark/dsh-orchestrator; do
        for shape in number null object array boolean empty malformed; do
            case_root="$(mktemp -d)"
            case_home="$case_root/home"
            case_dsh="$case_root/dsh"
            profile="$case_dsh/profiles/web"
            mkdir -p "$case_home" "$profile"
            python3 - "$profile/package.json" "$package" "$shape" <<'PY'
import json
import sys
from pathlib import Path

values = {
    "number": 17,
    "null": None,
    "object": {"version": "1.0.0"},
    "array": ["1.0.0"],
    "boolean": True,
    "empty": "",
    "malformed": "not a version",
}
path, package, shape = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
path.write_text(
    json.dumps(
        {
            "dependencies": {
                package: values[shape],
                "unrelated-user-package": {"keep": [True, None, 3]},
            },
            "userMetadata": ["keep", {"shape": "unchanged"}],
        },
        sort_keys=True,
    )
    + "\n"
)
PY
            before="$(shasum "$profile/package.json")"

            run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
                node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

            [ "$status" -ne 0 ]
            [[ "$output" == *"invalid managed package version"* ]]
            [[ "$output" != *"Traceback"* ]]
            [ "$(shasum "$profile/package.json")" = "$before" ]
            [ ! -e "$case_dsh/fake-argv.jsonl" ]
            [ ! -e "$case_dsh/.agent-presets/softspark-orchestrator" ]
            [ ! -e "$case_home/.softspark/ai-toolkit/state.json" ]
        done
    done
}

@test "dsh lifecycle: malformed shared state fails closed without traceback or mutation" {
    fake_bin="$(install_fake_dsh)"
    mkdir -p "$TEST_HOME/.softspark/ai-toolkit"
    printf '%s\n' '{malformed' > "$TEST_HOME/.softspark/ai-toolkit/state.json"
    before="$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'malformed ai-toolkit state file'
    [[ "$output" != *"Traceback"* ]]
    [ "$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")" = "$before" ]
    [ ! -e "$TEST_DSH_HOME/fake-argv.jsonl" ]
}

@test "dsh lifecycle: profile-root symlink is rejected before plugin mutation" {
    fake_bin="$(install_fake_dsh)"
    external="$TEST_PROJECT/external-profiles"
    mkdir -p "$external"
    ln -s "$external" "$TEST_DSH_HOME/profiles"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'unsafe symlink'
    [ -z "$(find "$external" -mindepth 1 -print -quit)" ]
    [ ! -e "$TEST_DSH_HOME/fake-argv.jsonl" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: user-owned symlink in DSH_HOME ancestry is rejected" {
    fake_bin="$(install_fake_dsh)"
    external="$TEST_PROJECT/external-home"
    linked_parent="$TEST_PROJECT/linked-home"
    mkdir -p "$external"
    ln -s "$external" "$linked_parent"
    linked_home="$linked_parent/child"

    run env HOME="$TEST_HOME" DSH_HOME="$linked_home" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'DSH_HOME has unsafe symlink ancestry'
    [ -z "$(find "$external" -mindepth 1 -print -quit)" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: unsupported runtime version fails before profile mutation" {
    fake_bin="$(install_fake_dsh)"
    printf '%s\n' '{"version":"0.1.1-rc.3"}' > "$TEST_DSH_HOME/fake-control.json"
    before="$(surface_fingerprint "$TEST_DSH_HOME")"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'unsupported DSH version 0.1.1-rc.3'
    echo "$output" | grep -q 'required 0.1.1-rc.2'
    [ "$(surface_fingerprint "$TEST_DSH_HOME")" = "$before" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: missing runtime is actionable and leaves all roots unchanged" {
    empty_bin="$TEST_PROJECT/empty-bin"
    mkdir -p "$empty_bin"
    python_bin="$(command -v python3)"
    before="$(surface_fingerprint "$TEST_DSH_HOME")"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$empty_bin" \
        "$python_bin" "$TOOLKIT_DIR/scripts/install_steps/dsh.py" install --profile web

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'DSH executable not found on PATH'
    [ "$(surface_fingerprint "$TEST_DSH_HOME")" = "$before" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: invalid profile id fails before runtime discovery" {
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile '../escape'

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'invalid DSH profile id'
    [ ! -e "$TEST_DSH_HOME/fake-argv.jsonl" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: dry-run prints exact argv and paths with zero mutations" {
    fake_bin="$(install_fake_dsh)"
    printf '%s\n' 'keep' > "$TEST_DSH_HOME/user-file"
    before="$(surface_fingerprint "$TEST_DSH_HOME")"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --dry-run

    [ "$status" -eq 0 ]
    echo "$output" | grep -Fq \
        "'plugin', '--profile', 'web', 'add', '@softspark/dsh-codex@1.0.0', '--save-exact'"
    echo "$output" | grep -Fq \
        "'plugin', '--profile', 'web', 'add', '@softspark/dsh-orchestrator@1.0.1', '--save-exact'"
    echo "$output" | grep -Fq \
        "$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-orchestrator/agent-presets/softspark-orchestrator"
    echo "$output" | grep -Fq \
        "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator"
    [ "$(surface_fingerprint "$TEST_DSH_HOME")" = "$before" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
}

@test "dsh lifecycle: canonical tree identity separates structure modes and links" {
    run python3 - "$TOOLKIT_DIR" "$BATS_TEST_TMPDIR" <<'PY'
import os
import sys
from pathlib import Path

toolkit, temporary = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

tree_a = temporary / "tree-a"
tree_b = temporary / "tree-b"
tree_a.mkdir()
tree_b.mkdir()
(tree_a / "a").write_bytes(b"f\0b\0X")
(tree_b / "a").write_bytes(b"")
(tree_b / "b").write_bytes(b"X")
assert dsh._tree_hash(tree_a) != dsh._tree_hash(tree_b)

mode_a = temporary / "mode-a"
mode_b = temporary / "mode-b"
mode_a.mkdir()
mode_b.mkdir()
(mode_a / "entry").write_text("same", encoding="utf-8")
(mode_b / "entry").write_text("same", encoding="utf-8")
os.chmod(mode_a / "entry", 0o600)
os.chmod(mode_b / "entry", 0o644)
assert dsh._tree_hash(mode_a) != dsh._tree_hash(mode_b)

link_a = temporary / "link-a"
link_b = temporary / "link-b"
link_a.mkdir()
link_b.mkdir()
(link_a / "entry").symlink_to("one")
(link_b / "entry").symlink_to("two")
assert dsh._tree_hash(link_a) != dsh._tree_hash(link_b)
PY

    [ "$status" -eq 0 ]
}

@test "dsh lifecycle: dry-run never acquires a writable lifecycle lock" {
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

def reject_lock(_dsh_home):
    raise AssertionError("dry-run attempted a writable lifecycle lock")

dsh._acquire_lifecycle_lock = reject_lock
raise SystemExit(dsh.main(["install", "--profile", "web", "--dry-run"]))
PY

    [ "$status" -eq 0 ]
    [ ! -e "$TEST_DSH_HOME/.ai-toolkit-lifecycle.lock" ]
}

@test "dsh lifecycle: unsupported secure mutation platform fails before first write" {
    fake_bin="$(install_fake_dsh)"
    before="$(surface_fingerprint "$TEST_DSH_HOME")"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

dsh._secure_mutation_supported = lambda: False
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"secure DSH filesystem mutation is unsupported"* ]]
    [ "$(surface_fingerprint "$TEST_DSH_HOME")" = "$before" ]
    [ ! -e "$TEST_DSH_HOME/fake-argv.jsonl" ]
}

@test "dsh lifecycle: unsupported secure state platform fails before every write" {
    fake_bin="$(install_fake_dsh)"
    state_root="$TEST_HOME/.softspark/ai-toolkit"
    before="$(surface_fingerprint "$TEST_DSH_HOME")"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

dsh._secure_mutation_supported = lambda: True
dsh.secure_dsh_state_mutation_supported = lambda: False
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"secure ai-toolkit state mutation"* ]]
    [ "$(surface_fingerprint "$TEST_DSH_HOME")" = "$before" ]
    [ ! -e "$TEST_DSH_HOME/.ai-toolkit-lifecycle.lock" ]
    [ ! -e "$TEST_DSH_HOME/fake-argv.jsonl" ]
    [ ! -e "$state_root" ]
}

@test "dsh lifecycle: repeated unchanged install is byte-idempotent" {
    fake_bin="$(install_fake_dsh)"
    command=(env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web)

    run "${command[@]}"
    [ "$status" -eq 0 ]
    before_state="$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")"
    before_preset="$(surface_fingerprint "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator")"
    before_calls="$(cat "$TEST_DSH_HOME/fake-argv.jsonl")"

    run "${command[@]}"

    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'already installed and unchanged'
    [ "$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")" = "$before_state" ]
    [ "$(surface_fingerprint "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator")" = "$before_preset" ]
    [ "$(cat "$TEST_DSH_HOME/fake-argv.jsonl")" = "$before_calls" ]
}

@test "dsh lifecycle: second package failure rolls back the first package deterministically" {
    fake_bin="$(install_fake_dsh)"
    cat > "$TEST_DSH_HOME/fake-control.json" <<'JSON'
{"fail_before":"add:@softspark/dsh-orchestrator"}
JSON

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'DSH command failed with exit status 70'
    [ ! -e "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
    [ ! -e "$TEST_DSH_HOME/profiles/web/package.json" ]
    [ ! -e "$TEST_DSH_HOME/profiles/web/node_modules/@softspark" ]
    [ ! -e "$TEST_DSH_HOME/profiles/web" ]
    python3 - "$TEST_DSH_HOME" <<'PY'
import json
import sys
from pathlib import Path

home = Path(sys.argv[1])
calls = [json.loads(line) for line in (home / "fake-argv.jsonl").read_text().splitlines()]
assert calls == [
    ["plugin", "--profile", "web", "add", "@softspark/dsh-codex@1.0.0", "--save-exact"],
    ["plugin", "--profile", "web", "add", "@softspark/dsh-orchestrator@1.0.1", "--save-exact"],
    ["plugin", "--profile", "web", "remove", "@softspark/dsh-codex"],
], calls
PY
}

@test "dsh lifecycle: clean rollback preserves concurrent profile additions as recovery" {
    fake_bin="$(install_fake_dsh)"
    printf '%s\n' '{"fail_before":"add:@softspark/dsh-orchestrator"}' > \
        "$TEST_DSH_HOME/fake-control.json"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
import os
from pathlib import Path

from install_steps import dsh

real_run = dsh._run
added = False

def add_user_file_after_first_package(argv, *, dsh_home):
    global added
    result = real_run(argv, dsh_home=dsh_home)
    if "add" in argv and "@softspark/dsh-codex@1.0.0" in argv and not added:
        added = True
        profile = Path(os.environ["DSH_HOME"]) / "profiles" / "web"
        (profile / "concurrent-user.txt").write_text("concurrent user bytes\n")
    return result

dsh._run = add_user_file_after_first_package
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    [[ "$output" == *"Recovery required"* ]]
    [[ "$output" == *"'$TEST_DSH_HOME/profiles/web'"* ]]
    [ "$(cat "$TEST_DSH_HOME/profiles/web/concurrent-user.txt")" = \
        "concurrent user bytes" ]
    [ ! -e "$TEST_DSH_HOME/profiles/web/package.json" ]
    [ ! -e "$TEST_DSH_HOME/profiles/web/node_modules" ]
}

@test "dsh lifecycle: interrupted plugin command rolls back and reports interruption" {
    fake_bin="$(install_fake_dsh)"
    cat > "$TEST_DSH_HOME/fake-control.json" <<'JSON'
{"fail_before":"add:@softspark/dsh-orchestrator","fail_code":130}
JSON

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -ne 0 ]
    echo "$output" | grep -qi 'interrupted'
    [ ! -e "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
    [ ! -e "$TEST_DSH_HOME/profiles/web" ]
}

@test "dsh lifecycle: KeyboardInterrupt after a completed add preserves package bytes" {
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from install_steps import dsh

real_run = dsh._run

def interrupt_after_first_add(argv, *, dsh_home):
    result = real_run(argv, dsh_home=dsh_home)
    if "add" in argv and "@softspark/dsh-codex@1.0.0" in argv:
        raise KeyboardInterrupt
    return result

dsh._run = interrupt_after_first_add
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    echo "$output" | grep -qi 'interrupted'
    [[ "$output" != *'Traceback'* ]]
    [ ! -e "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
    [ -f "$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-codex/package.json" ]
    [[ "$output" == *"run 'ai-toolkit dsh doctor --profile web'"* ]]
    find "$TEST_DSH_HOME/.agent-presets" -mindepth 1 -maxdepth 1 -type d \
        -name '.softspark-orchestrator.ai-toolkit-package.*' | grep -q .
}

@test "dsh lifecycle: KeyboardInterrupt after state persistence restores state prestate" {
    fake_bin="$(install_fake_dsh)"
    mkdir -p "$TEST_HOME/.softspark/ai-toolkit"
    printf '%s\n' '{"installed_version":"4.29.2","installed_modules":["core"]}' > \
        "$TEST_HOME/.softspark/ai-toolkit/state.json"
    before_state="$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from install_steps import dsh

real_record = dsh.record_dsh_profile

def interrupt_after_record(**kwargs):
    real_record(**kwargs)
    raise KeyboardInterrupt

dsh.record_dsh_profile = interrupt_after_record
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    echo "$output" | grep -qi 'interrupted'
    [[ "$output" != *'Traceback'* ]]
    [ "$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")" = "$before_state" ]
    [ ! -e "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator" ]
}

@test "dsh lifecycle: KeyboardInterrupt at every install mutation boundary restores prestate" {
    fake_bin="$(install_fake_dsh)"
    for boundary in \
        second_add destination_claim destination_copy destination_hash \
        staging_cleanup state; do
        case_root="$(mktemp -d)"
        case_home="$case_root/home"
        case_dsh="$case_root/dsh"
        mkdir -p "$case_home" "$case_dsh"

        run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
            PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - "$boundary" <<'PY'
import sys

from install_steps import dsh

boundary = sys.argv[1]

if boundary == "second_add":
    real = dsh._run

    def injected(argv, *, dsh_home):
        result = real(argv, dsh_home=dsh_home)
        if "add" in argv and "@softspark/dsh-orchestrator@1.0.1" in argv:
            raise KeyboardInterrupt
        return result

    dsh._run = injected
elif boundary == "destination_claim":
    real = dsh._claim_directory

    def injected(path, owned, *, mode=0o700):
        real(path, owned, mode=mode)
        if path.name == dsh.PRESET_NAME:
            raise KeyboardInterrupt

    dsh._claim_directory = injected
elif boundary == "destination_copy":
    real = dsh._copy_tree_exclusive

    def injected(source, destination, owned):
        real(source, destination, owned)
        if destination.name == dsh.PRESET_NAME:
            raise KeyboardInterrupt

    dsh._copy_tree_exclusive = injected
elif boundary == "destination_hash":
    real = dsh._tree_hash

    def injected(path):
        result = real(path)
        if path.name == dsh.PRESET_NAME and path.parent.name == ".agent-presets":
            raise KeyboardInterrupt
        return result

    dsh._tree_hash = injected
elif boundary == "staging_cleanup":
    real = dsh._cleanup_owned_entries
    raised = False

    def injected(owned):
        global raised
        is_staging = any(".ai-toolkit-new" in entry.path.as_posix() for entry in owned)
        result = real(owned)
        if is_staging and not raised:
            raised = True
            raise KeyboardInterrupt
        return result

    dsh._cleanup_owned_entries = injected
elif boundary == "state":
    real = dsh.record_dsh_profile

    def injected(**kwargs):
        real(**kwargs)
        raise KeyboardInterrupt

    dsh.record_dsh_profile = injected

raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

        [ "$status" -ne 0 ]
        echo "$output" | grep -qi 'interrupted'
        [[ "$output" != *'Traceback'* ]]
        [ ! -e "$case_home/.softspark/ai-toolkit/state.json" ]
        [ ! -e "$case_dsh/.agent-presets/softspark-orchestrator" ]
        [ ! -e "$case_dsh/.agent-presets/.softspark-orchestrator.ai-toolkit-new" ]
        if [ "$boundary" = second_add ]; then
            [ -f "$case_dsh/profiles/web/node_modules/@softspark/dsh-orchestrator/package.json" ]
            [[ "$output" == *"run 'ai-toolkit dsh doctor --profile web'"* ]]
        else
            [ ! -e "$case_dsh/profiles/web" ]
        fi
    done
}

@test "dsh lifecycle: rollback failure prints deterministic recovery argv and doctor detects it" {
    fake_bin="$(install_fake_dsh)"
    cat > "$TEST_DSH_HOME/fake-control.json" <<'JSON'
{
  "fail_before": [
    "add:@softspark/dsh-orchestrator",
    "remove:@softspark/dsh-codex"
  ]
}
JSON
    command=(env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)

    run "${command[@]}" install --profile web

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'Recovery required'
    echo "$output" | grep -Fq \
        "'plugin', '--profile', 'web', 'remove', '@softspark/dsh-codex'"
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
    [ -d "$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-codex" ]

    run "${command[@]}" doctor --profile web
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'Recovery needed: yes'
    [ -d "$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-codex" ]
}

@test "dsh lifecycle: plugin errors suppress credential-shaped output" {
    fake_bin="$(install_fake_dsh)"
    cat > "$TEST_DSH_HOME/fake-control.json" <<'JSON'
{
  "fail_before": "add:@softspark/dsh-codex",
  "failure_message": "registry https://build-user:super-secret@example.test npm_abcd1234567890 token=private-value"
}
JSON

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'DSH command failed with exit status 70'
    [[ "$output" != *"super-secret"* ]]
    [[ "$output" != *"npm_abcd1234567890"* ]]
    [[ "$output" != *"private-value"* ]]
}

@test "dsh lifecycle: child stdout and stderr diagnostics never expose secrets" {
    fake_bin="$(install_fake_dsh)"
    for stream in stdout stderr; do
        python3 - "$TEST_DSH_HOME/fake-control.json" "$stream" <<'PY'
import json
import sys
from pathlib import Path

stream = sys.argv[2]
diagnostic = (
    '//registry.npmjs.org/:_authToken="NPM_STREAM_SECRET"\n'
    'Authorization: Bearer BEARER_STREAM_SECRET\r\n'
    '{"api_key":"JSON_STREAM_SECRET"} '
    "api-key: 'COLON_STREAM_SECRET' API_KEY = \"EQUAL_STREAM_SECRET\" "
    'https://BuildUser:MIXED_URL_SECRET@example.test/\u0001CONTROL_STREAM_SECRET'
)
Path(sys.argv[1]).write_text(
    json.dumps({
        "fail_before": "add:@softspark/dsh-codex",
        f"failure_{stream}": diagnostic,
    }),
    encoding="utf-8",
)
PY

        run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
            node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

        [ "$status" -ne 0 ]
        echo "$output" | grep -q 'DSH command failed with exit status 70'
        for secret in \
            NPM_STREAM_SECRET BEARER_STREAM_SECRET JSON_STREAM_SECRET \
            COLON_STREAM_SECRET EQUAL_STREAM_SECRET MIXED_URL_SECRET \
            CONTROL_STREAM_SECRET; do
            [[ "$output" != *"$secret"* ]]
        done
        [[ "$output" != *'_authToken'* ]]
        [[ "$output" != *'Authorization'* ]]
        [[ "$output" != *'api_key'* ]]
        [[ "$output" != *'api-key'* ]]
    done
}

@test "dsh lifecycle: plugin subprocess receives no provider or registry secrets" {
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        OPENAI_API_KEY='do-not-forward' ANTHROPIC_API_KEY='do-not-forward' \
        GOOGLE_API_KEY='do-not-forward' NPM_TOKEN='do-not-forward' \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -eq 0 ]
    python3 - "$TEST_DSH_HOME/fake-env-keys.json" <<'PY'
import json
import sys
from pathlib import Path

keys = set(json.loads(Path(sys.argv[1]).read_text()))
assert not keys.intersection({
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "NPM_TOKEN",
}), keys
assert {"HOME", "DSH_HOME", "PATH"}.issubset(keys), keys
PY
}

@test "dsh lifecycle: bounded command timeout leaves the clean prestate" {
    fake_bin="$(install_fake_dsh)"
    cat > "$TEST_DSH_HOME/fake-control.json" <<'JSON'
{"sleep_before":"add:@softspark/dsh-orchestrator","sleep_seconds":1}
JSON

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from install_steps import dsh

real_run = dsh._run
dsh.PACKAGE_MUTATION_TIMEOUT_SECONDS = 0.5


def timeout_only_cold_add(argv, *, dsh_home):
    is_cold_target = (
        "add" in argv
        and "@softspark/dsh-orchestrator@1.0.1" in argv
    )
    if is_cold_target:
        dsh.PACKAGE_MUTATION_TIMEOUT_SECONDS = 0.2
    try:
        return real_run(argv, dsh_home=dsh_home)
    finally:
        dsh.PACKAGE_MUTATION_TIMEOUT_SECONDS = 0.5


dsh._run = timeout_only_cold_add
raise SystemExit(dsh.main(["install", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'timed out after 0.2s'
    [ ! -e "$TEST_DSH_HOME/profiles/web/package.json" ]
    [ ! -e "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator" ]
    [ ! -e "$TEST_HOME/.softspark/ai-toolkit/state.json" ]
    python3 - "$TEST_DSH_HOME/fake-argv.jsonl" <<'PY'
import json
import sys
from pathlib import Path

calls = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
assert calls == [
    ["plugin", "--profile", "web", "add", "@softspark/dsh-codex@1.0.0", "--save-exact"],
    ["plugin", "--profile", "web", "add", "@softspark/dsh-orchestrator@1.0.1", "--save-exact"],
    ["plugin", "--profile", "web", "remove", "@softspark/dsh-codex"],
], calls
PY
}

@test "dsh lifecycle: update replaces only the unchanged owned preset from the package" {
    fake_bin="$(install_fake_dsh)"
    command=(env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)

    run "${command[@]}" install --profile web
    [ "$status" -eq 0 ]
    cat > "$TEST_DSH_HOME/fake-control.json" <<'JSON'
{"preset_content":"updated released preset\n"}
JSON

    run "${command[@]}" update --profile web

    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator/preset.md")" = \
        'updated released preset' ]
    [ "$(wc -l < "$TEST_DSH_HOME/fake-argv.jsonl" | xargs)" -eq 4 ]
    python3 - "$TEST_DSH_HOME" "$TEST_HOME/.softspark/ai-toolkit/state.json" <<'PY'
import json
import sys
from pathlib import Path

dsh_home = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(Path.cwd() / "scripts"))
from install_steps import dsh

state = json.loads(Path(sys.argv[2]).read_text())["dsh"]["profiles"]["web"]
preset = dsh_home / ".agent-presets" / "softspark-orchestrator"
assert state["preset_hash"] == dsh._tree_hash(preset)
PY
}

@test "dsh lifecycle: subprocess success requires exact package postconditions" {
    fake_bin="$(install_fake_dsh)"

    for control in success_noop_once wrong_version_once; do
        case_root="$(mktemp -d)"
        case_home="$case_root/home"
        case_dsh="$case_root/dsh"
        mkdir -p "$case_home" "$case_dsh"
        printf '{"%s":"add:@softspark/dsh-codex"}\n' "$control" > \
            "$case_dsh/fake-control.json"

        run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
            node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

        [ "$status" -ne 0 ]
        [[ "$output" == *"package postcondition failed"* ]]
        [ ! -e "$case_home/.softspark/ai-toolkit/state.json" ]
        [ ! -e "$case_dsh/.agent-presets/softspark-orchestrator" ]
    done

    case_root="$(mktemp -d)"
    case_home="$case_root/home"
    case_dsh="$case_root/dsh"
    mkdir -p "$case_home" "$case_dsh/profiles/web"
    printf '%s\n' '{"dependencies":{"unrelated":"2.0.0"}}' > \
        "$case_dsh/profiles/web/package.json"
    printf '%s\n' \
        '{"mutate_unrelated_once":"add:@softspark/dsh-orchestrator"}' > \
        "$case_dsh/fake-control.json"

    run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web

    [ "$status" -ne 0 ]
    [[ "$output" == *"package postcondition failed"* ]]
    [[ "$output" == *"dsh doctor --profile web"* ]]
    python3 - "$case_dsh/profiles/web/package.json" <<'PY'
import json
import sys
from pathlib import Path

dependencies = json.loads(Path(sys.argv[1]).read_text())["dependencies"]
assert dependencies["unrelated"] == "9.9.9", dependencies
PY
    find "$case_dsh/.agent-presets" -mindepth 1 -maxdepth 1 -type d \
        -name '.softspark-orchestrator.ai-toolkit-package.*' | grep -q .
    [ ! -e "$case_home/.softspark/ai-toolkit/state.json" ]

    case_root="$(mktemp -d)"
    case_home="$case_root/home"
    case_dsh="$case_root/dsh"
    mkdir -p "$case_home" "$case_dsh"
    run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
    [ "$status" -eq 0 ]
    python3 - "$case_dsh/profiles/web/package.json" <<'PY'
import json
import sys
from pathlib import Path

manifest = Path(sys.argv[1])
document = json.loads(manifest.read_text())
document["dependencies"]["unrelated"] = "2.0.0"
manifest.write_text(json.dumps(document, sort_keys=True) + "\n")
PY
    before_state="$(shasum "$case_home/.softspark/ai-toolkit/state.json")"
    printf '%s\n' \
        '{"mutate_unrelated_once":"add:@softspark/dsh-orchestrator"}' > \
        "$case_dsh/fake-control.json"

    run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh update --profile web

    [ "$status" -ne 0 ]
    [[ "$output" == *"package postcondition failed"* ]]
    [[ "$output" == *"dsh doctor --profile web"* ]]
    python3 - "$case_dsh/profiles/web/package.json" <<'PY'
import json
import sys
from pathlib import Path

dependencies = json.loads(Path(sys.argv[1]).read_text())["dependencies"]
assert dependencies["unrelated"] == "9.9.9", dependencies
PY
    find "$case_dsh/.agent-presets" -mindepth 1 -maxdepth 1 -type d \
        -name '.softspark-orchestrator.ai-toolkit-package.*' | grep -q .
    [ "$(shasum "$case_home/.softspark/ai-toolkit/state.json")" = "$before_state" ]

    case_root="$(mktemp -d)"
    case_home="$case_root/home"
    case_dsh="$case_root/dsh"
    mkdir -p "$case_home" "$case_dsh"
    run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
    [ "$status" -eq 0 ]
    before_state="$(shasum "$case_home/.softspark/ai-toolkit/state.json")"
    before_preset="$(surface_fingerprint \
        "$case_dsh/.agent-presets/softspark-orchestrator")"
    printf '%s\n' \
        '{"success_noop_once":"remove:@softspark/dsh-codex"}' > \
        "$case_dsh/fake-control.json"

    run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh uninstall --profile web --yes

    [ "$status" -ne 0 ]
    [[ "$output" == *"package postcondition failed"* ]]
    [ "$(shasum "$case_home/.softspark/ai-toolkit/state.json")" = "$before_state" ]
    [ "$(surface_fingerprint \
        "$case_dsh/.agent-presets/softspark-orchestrator")" = "$before_preset" ]
}

@test "dsh lifecycle: update and uninstall reject preset identity swaps at rename" {
    fake_bin="$(install_fake_dsh)"
    for operation in update uninstall; do
        for kind in directory file symlink; do
            case_root="$(mktemp -d)"
            case_home="$case_root/home"
            case_dsh="$case_root/dsh"
            mkdir -p "$case_home" "$case_dsh"
            run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
                node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
            [ "$status" -eq 0 ]
            if [ "$operation" = update ]; then
                printf '%s\n' '{"preset_content_once":"updated preset\n"}' > \
                    "$case_dsh/fake-control.json"
            fi

            run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
                PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - "$operation" "$kind" <<'PY'
import os
import shutil
import sys
from pathlib import Path

from install_steps import dsh

operation, kind = sys.argv[1:]
destination = (
    Path(os.environ["DSH_HOME"]).resolve()
    / ".agent-presets"
    / dsh.PRESET_NAME
)
outside = Path(os.environ["DSH_HOME"]) / "concurrent-user-preset"
real_assert = dsh._assert_entry_unchanged
swapped = False

def inject_identity_swap(expected, label):
    global swapped
    if not swapped:
        swapped = True
        shutil.rmtree(destination)
        if kind == "directory":
            destination.mkdir()
            (destination / "keep.txt").write_text("concurrent user bytes\n")
        elif kind == "file":
            destination.write_text("concurrent user bytes\n")
        else:
            outside.mkdir()
            (outside / "keep.txt").write_text("concurrent user bytes\n")
            destination.symlink_to(outside, target_is_directory=True)
    return real_assert(expected, label)

dsh._assert_entry_unchanged = inject_identity_swap
arguments = [operation, "--profile", "web"]
if operation == "uninstall":
    arguments.append("--yes")
raise SystemExit(dsh.main(arguments))
PY

            [ "$status" -ne 0 ]
            [[ "$output" == *"preset identity changed"* ]]
            destination="$case_dsh/.agent-presets/softspark-orchestrator"
            if [ "$kind" = file ]; then
                [ "$(cat "$destination")" = "concurrent user bytes" ]
            else
                [ "$(cat "$destination/keep.txt")" = "concurrent user bytes" ]
            fi
            [ ! -e "$case_dsh/.agent-presets/.softspark-orchestrator.ai-toolkit-backup" ]
            [ ! -e "$case_dsh/.agent-presets/.softspark-orchestrator.ai-toolkit-uninstall" ]
        done
    done
}

@test "dsh lifecycle: update and uninstall bind captured preset digest to ownership state" {
    fake_bin="$(install_fake_dsh)"
    for operation in update uninstall; do
        case_root="$(mktemp -d)"
        case_home="$case_root/home"
        case_dsh="$case_root/dsh"
        mkdir -p "$case_home" "$case_dsh"
        run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
            node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
        [ "$status" -eq 0 ]

        run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
            PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - "$operation" <<'PY'
import os
import shutil
import sys
from pathlib import Path

from install_steps import dsh

operation = sys.argv[1]
destination = (
    Path(os.environ["DSH_HOME"]).resolve()
    / ".agent-presets"
    / dsh.PRESET_NAME
)
real_capture = dsh._capture_entry
swapped = False

def swap_before_identity_capture(path):
    global swapped
    if path == destination and not swapped:
        swapped = True
        shutil.rmtree(destination)
        destination.mkdir()
        (destination / "keep.txt").write_text("concurrent user bytes\n")
    return real_capture(path)

dsh._capture_entry = swap_before_identity_capture
arguments = [operation, "--profile", "web"]
if operation == "uninstall":
    arguments.append("--yes")
raise SystemExit(dsh.main(arguments))
PY

        [ "$status" -ne 0 ]
        [[ "$output" == *"preset drift detected"* ]]
        [ "$(cat "$case_dsh/.agent-presets/softspark-orchestrator/keep.txt")" = \
            "concurrent user bytes" ]
        [ ! -e "$case_dsh/.agent-presets/.softspark-orchestrator.ai-toolkit-backup" ]
        [ ! -e "$case_dsh/.agent-presets/.softspark-orchestrator.ai-toolkit-uninstall" ]
    done
}

@test "dsh lifecycle: update accepts owned package trees recorded under older exact pins" {
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
import json
import os
from pathlib import Path

from install_steps import dsh

assert dsh.main(["install", "--profile", "web"]) == 0
state_path = Path(os.environ["HOME"]) / ".softspark/ai-toolkit/state.json"
old_record = json.loads(state_path.read_text())["dsh"]["profiles"]["web"]
assert old_record["packages"] == {
    "@softspark/dsh-codex": "1.0.0",
    "@softspark/dsh-orchestrator": "1.0.1",
}

dsh.PACKAGES = {
    "@softspark/dsh-codex": "1.1.0",
    "@softspark/dsh-orchestrator": "1.1.0",
}
assert dsh.main(["update", "--profile", "web"]) == 0

profile = Path(os.environ["DSH_HOME"]) / "profiles/web"
record = json.loads(state_path.read_text())["dsh"]["profiles"]["web"]
assert record["packages"] == dsh.PACKAGES
assert set(record["package_trees"]) == set(dsh.PACKAGES)
for package, version in dsh.PACKAGES.items():
    package_manifest = profile / "node_modules" / Path(package) / "package.json"
    assert json.loads(package_manifest.read_text())["version"] == version
PY

    [ "$status" -eq 0 ]
    [[ "$output" == *"Updated DSH profile integration: web"* ]]
}

@test "dsh lifecycle: uninstall removes owned package trees recorded under older exact pins" {
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
import json
import os
from pathlib import Path

from install_steps import dsh

assert dsh.main(["install", "--profile", "web"]) == 0
dsh.PACKAGES = {
    "@softspark/dsh-codex": "1.1.0",
    "@softspark/dsh-orchestrator": "1.1.0",
}
assert dsh.main(["uninstall", "--profile", "web", "--yes"]) == 0

dsh_home = Path(os.environ["DSH_HOME"]).resolve()
state = json.loads(
    (Path(os.environ["HOME"]) / ".softspark/ai-toolkit/state.json").read_text()
)
assert "dsh" not in state
assert not (dsh_home / ".agent-presets/softspark-orchestrator").exists()
for package in dsh.MANAGED_PACKAGE_NAMES:
    assert not (dsh_home / "profiles/web/node_modules" / Path(package)).exists()
calls = [
    json.loads(line)
    for line in (dsh_home / "fake-argv.jsonl").read_text().splitlines()
]
assert calls[-2:] == [
    ["plugin", "--profile", "web", "remove", "@softspark/dsh-orchestrator"],
    ["plugin", "--profile", "web", "remove", "@softspark/dsh-codex"],
]
PY

    [ "$status" -eq 0 ]
    [[ "$output" == *"Uninstalled DSH profile integration: web"* ]]
}

@test "dsh lifecycle: malformed recorded package ownership remains fail closed" {
    fake_bin="$(install_fake_dsh)"

    for operation in update uninstall; do
        for variant in \
            packages-not-object packages-missing packages-extra \
            version-not-string version-range version-tag \
            trees-missing trees-extra; do
            case_root="$TEST_PROJECT/$operation-$variant"
            case_home="$case_root/home"
            case_dsh="$case_root/dsh"
            mkdir -p "$case_home" "$case_dsh"
            run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
                node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
            [ "$status" -eq 0 ]
            state="$case_home/.softspark/ai-toolkit/state.json"
            calls="$case_dsh/fake-argv.jsonl"
            python3 - "$state" "$variant" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
variant = sys.argv[2]
state = json.loads(path.read_text())
record = state["dsh"]["profiles"]["web"]
if variant == "packages-not-object":
    record["packages"] = []
elif variant == "packages-missing":
    record["packages"].pop("@softspark/dsh-codex")
elif variant == "packages-extra":
    record["packages"]["unowned-package"] = "1.0.0"
elif variant == "version-not-string":
    record["packages"]["@softspark/dsh-codex"] = 1
elif variant == "version-range":
    record["packages"]["@softspark/dsh-codex"] = "^1.0.0"
elif variant == "version-tag":
    record["packages"]["@softspark/dsh-codex"] = "latest"
elif variant == "trees-missing":
    record["package_trees"].pop("@softspark/dsh-codex")
elif variant == "trees-extra":
    record["package_trees"]["unowned-package"] = {}
else:
    raise AssertionError(variant)
path.write_text(json.dumps(state, sort_keys=True) + "\n")
PY
            before_state="$(shasum "$state")"
            before_dsh="$(surface_fingerprint "$case_dsh")"
            before_calls="$(wc -l < "$calls" | xargs)"

            arguments=(dsh "$operation" --profile web)
            if [ "$operation" = uninstall ]; then
                arguments+=(--yes)
            fi
            run env HOME="$case_home" DSH_HOME="$case_dsh" PATH="$fake_bin:$PATH" \
                node "$TOOLKIT_DIR/bin/ai-toolkit.js" "${arguments[@]}"

            [ "$status" -ne 0 ]
            [[ "$output" == *"invalid DSH ownership state"* ]] || {
                echo "unexpected ownership diagnostic for $operation/$variant: $output"
                false
            }
            [[ "$output" != *"Traceback"* ]]
            [ "$(shasum "$state")" = "$before_state" ]
            [ "$(surface_fingerprint "$case_dsh")" = "$before_dsh" ]
            [ "$(wc -l < "$calls" | xargs)" = "$before_calls" ]
        done
    done
}

@test "dsh lifecycle: failed pin-bump update rolls back to recorded exact versions" {
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
import json
import os
from pathlib import Path

from install_steps import dsh

assert dsh.main(["install", "--profile", "web"]) == 0
dsh_home = Path(os.environ["DSH_HOME"]).resolve()
state_path = Path(os.environ["HOME"]) / ".softspark/ai-toolkit/state.json"
old_state = state_path.read_bytes()
old_preset = dsh._tree_hash(dsh_home / ".agent-presets/softspark-orchestrator")
(dsh_home / "fake-control.json").write_text(
    json.dumps({"fail_before_once": "add:@softspark/dsh-orchestrator"})
)
dsh.PACKAGES = {
    "@softspark/dsh-codex": "1.1.0",
    "@softspark/dsh-orchestrator": "1.1.0",
}
assert dsh.main(["update", "--profile", "web"]) == 1

profile = dsh_home / "profiles/web"
assert state_path.read_bytes() == old_state
assert dsh._tree_hash(dsh_home / ".agent-presets/softspark-orchestrator") == old_preset
expected_recorded_versions = {
    "@softspark/dsh-codex": "1.0.0",
    "@softspark/dsh-orchestrator": "1.0.1",
}
for package in dsh.MANAGED_PACKAGE_NAMES:
    package_manifest = profile / "node_modules" / Path(package) / "package.json"
    assert (
        json.loads(package_manifest.read_text())["version"]
        == expected_recorded_versions[package]
    )
calls = [
    json.loads(line)
    for line in (dsh_home / "fake-argv.jsonl").read_text().splitlines()
]
assert calls[-4:] == [
    ["plugin", "--profile", "web", "add", "@softspark/dsh-codex@1.1.0", "--save-exact"],
    ["plugin", "--profile", "web", "add", "@softspark/dsh-orchestrator@1.1.0", "--save-exact"],
    ["plugin", "--profile", "web", "add", "@softspark/dsh-orchestrator@1.0.1", "--save-exact"],
    ["plugin", "--profile", "web", "add", "@softspark/dsh-codex@1.0.0", "--save-exact"],
]
PY

    [ "$status" -eq 0 ]
    [[ "$output" == *"DSH command failed with exit status 70"* ]]
}

@test "dsh lifecycle: failed old-pin uninstall rolls back to recorded exact versions" {
    fake_bin="$(install_fake_dsh)"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
import json
import os
from pathlib import Path

from install_steps import dsh

assert dsh.main(["install", "--profile", "web"]) == 0
dsh_home = Path(os.environ["DSH_HOME"]).resolve()
state_path = Path(os.environ["HOME"]) / ".softspark/ai-toolkit/state.json"
old_state = state_path.read_bytes()
old_preset = dsh._tree_hash(dsh_home / ".agent-presets/softspark-orchestrator")
(dsh_home / "fake-control.json").write_text(
    json.dumps({"fail_before_once": "remove:@softspark/dsh-codex"})
)
dsh.PACKAGES = {
    "@softspark/dsh-codex": "1.1.0",
    "@softspark/dsh-orchestrator": "1.1.0",
}
assert dsh.main(["uninstall", "--profile", "web", "--yes"]) == 1

profile = dsh_home / "profiles/web"
assert state_path.read_bytes() == old_state
assert dsh._tree_hash(dsh_home / ".agent-presets/softspark-orchestrator") == old_preset
expected_recorded_versions = {
    "@softspark/dsh-codex": "1.0.0",
    "@softspark/dsh-orchestrator": "1.0.1",
}
for package in dsh.MANAGED_PACKAGE_NAMES:
    package_manifest = profile / "node_modules" / Path(package) / "package.json"
    assert (
        json.loads(package_manifest.read_text())["version"]
        == expected_recorded_versions[package]
    )
calls = [
    json.loads(line)
    for line in (dsh_home / "fake-argv.jsonl").read_text().splitlines()
]
assert calls[-3:] == [
    ["plugin", "--profile", "web", "remove", "@softspark/dsh-orchestrator"],
    ["plugin", "--profile", "web", "remove", "@softspark/dsh-codex"],
    ["plugin", "--profile", "web", "add", "@softspark/dsh-orchestrator@1.0.1", "--save-exact"],
]
PY

    [ "$status" -eq 0 ]
    [[ "$output" == *"DSH command failed with exit status 70"* ]]
}

@test "dsh lifecycle: KeyboardInterrupt after completed update add preserves new package bytes" {
    fake_bin="$(install_fake_dsh)"
    command=(env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
    run "${command[@]}" install --profile web
    [ "$status" -eq 0 ]
    before_source="$(surface_fingerprint "$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-orchestrator")"
    before_preset="$(surface_fingerprint "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator")"
    before_state="$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")"
    printf '%s\n' '{"preset_content_once":"updated before interrupt\n"}' > \
        "$TEST_DSH_HOME/fake-control.json"

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
from install_steps import dsh

real_run = dsh._run

def interrupt_after_orchestrator_add(argv, *, dsh_home):
    result = real_run(argv, dsh_home=dsh_home)
    if "add" in argv and "@softspark/dsh-orchestrator@1.0.1" in argv:
        raise KeyboardInterrupt
    return result

dsh._run = interrupt_after_orchestrator_add
raise SystemExit(dsh.main(["update", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    echo "$output" | grep -qi 'interrupted'
    [[ "$output" != *'Traceback'* ]]
    [ "$(surface_fingerprint "$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-orchestrator")" != "$before_source" ]
    [ "$(surface_fingerprint "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator")" = "$before_preset" ]
    [ "$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")" = "$before_state" ]
    [[ "$output" == *"run 'ai-toolkit dsh doctor --profile web'"* ]]
}

@test "dsh lifecycle: profile doctor is read-only and reports ownership drift" {
    fake_bin="$(install_fake_dsh)"
    command=(env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
    run "${command[@]}" install --profile web
    [ "$status" -eq 0 ]

    run "${command[@]}" doctor --profile web
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Runtime: supported (0.1.1-rc.2)'
    echo "$output" | grep -q '@softspark/dsh-codex: 1.0.0 (expected 1.0.0)'
    echo "$output" | grep -q '@softspark/dsh-orchestrator: 1.0.1 (expected 1.0.1)'
    echo "$output" | grep -q 'Preset: owned, hash matches'
    echo "$output" | grep -q 'State: consistent'
    echo "$output" | grep -q 'Recovery needed: no'

    printf '%s\n' 'user modification' >> \
        "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator/preset.md"
    before="$(surface_fingerprint "$TEST_DSH_HOME")"
    before_state="$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")"
    run "${command[@]}" doctor --profile web
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'Preset: owned, hash drift'
    echo "$output" | grep -q 'Recovery needed: yes'
    [ "$(surface_fingerprint "$TEST_DSH_HOME")" = "$before" ]
    [ "$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")" = "$before_state" ]
}

@test "dsh lifecycle: doctor reports every preserved preset recovery artifact read-only" {
    fake_bin="$(install_fake_dsh)"
    command=(env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
    run "${command[@]}" install --profile web
    [ "$status" -eq 0 ]
    recovery_root="$(cd "$TEST_DSH_HOME/.agent-presets" && pwd -P)"
    for suffix in new backup uninstall; do
        artifact="$recovery_root/.softspark-orchestrator.ai-toolkit-$suffix"
        mkdir "$artifact"
        printf '%s\n' "preserved $suffix recovery" > "$artifact/keep.txt"
    done
    before_dsh="$(surface_fingerprint "$TEST_DSH_HOME")"
    before_state="$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")"

    run "${command[@]}" doctor --profile web

    [ "$status" -ne 0 ]
    for suffix in new backup uninstall; do
        artifact="$recovery_root/.softspark-orchestrator.ai-toolkit-$suffix"
        echo "$output" | grep -Fq "Recovery artifact: '$artifact'"
    done
    echo "$output" | grep -q 'Recovery needed: yes'
    [ "$(surface_fingerprint "$TEST_DSH_HOME")" = "$before_dsh" ]
    [ "$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")" = "$before_state" ]
}

@test "dsh lifecycle: package node_modules drift blocks update before mutation" {
    fake_bin="$(install_fake_dsh)"
    command=(env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
    run "${command[@]}" install --profile web
    [ "$status" -eq 0 ]
    package_manifest="$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-codex/package.json"
    printf '%s\n' '{"name":"@softspark/dsh-codex","version":"9.9.9"}' > \
        "$package_manifest"
    before_calls="$(cat "$TEST_DSH_HOME/fake-argv.jsonl")"
    before_preset="$(surface_fingerprint "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator")"

    run "${command[@]}" update --profile web

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'package drift'
    [ "$(cat "$TEST_DSH_HOME/fake-argv.jsonl")" = "$before_calls" ]
    [ "$(surface_fingerprint "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator")" = "$before_preset" ]
}

@test "dsh lifecycle: persisted package trees block added files mode drift and symlinks" {
    fake_bin="$(install_fake_dsh)"
    command=(env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
    run "${command[@]}" install --profile web
    [ "$status" -eq 0 ]

    state="$TEST_HOME/.softspark/ai-toolkit/state.json"
    python3 - "$state" <<'PY'
import json
import sys

record = json.load(open(sys.argv[1], encoding="utf-8"))["dsh"]["profiles"]["web"]
trees = record["package_trees"]
assert set(trees) == {
    "@softspark/dsh-codex",
    "@softspark/dsh-orchestrator",
}
for tree in trees.values():
    assert len(tree["digest"]) == 64
    assert tree["entries"][0]["path"] == "."
    assert all("content" not in entry for entry in tree["entries"])
PY

    calls="$TEST_DSH_HOME/fake-argv.jsonl"
    before_calls="$(wc -l < "$calls" | xargs)"
    codex="$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-codex"
    orchestrator="$TEST_DSH_HOME/profiles/web/node_modules/@softspark/dsh-orchestrator"
    printf '%s\n' 'user bytes' > "$codex/user-owned.txt"
    before_file="$(shasum "$codex/user-owned.txt")"

    run "${command[@]}" update --profile web
    [ "$status" -ne 0 ]
    [[ "$output" == *"managed DSH package tree drift detected"* ]]
    [ "$(wc -l < "$calls" | xargs)" = "$before_calls" ]
    [ "$(shasum "$codex/user-owned.txt")" = "$before_file" ]

    mv "$codex/user-owned.txt" "$TEST_DSH_HOME/user-owned.preserved"
    chmod 600 "$codex/package.json"
    run "${command[@]}" uninstall --profile web --yes
    [ "$status" -ne 0 ]
    [[ "$output" == *"managed DSH package tree drift detected"* ]]
    [ "$(wc -l < "$calls" | xargs)" = "$before_calls" ]
    [ "$(portable_mode "$codex/package.json")" = "600" ]

    chmod 644 "$codex/package.json"
    ln -s '../outside-user-target' "$orchestrator/user-link"
    run "${command[@]}" update --profile web
    [ "$status" -ne 0 ]
    [[ "$output" == *"managed DSH package tree drift detected"* ]]
    [ "$(wc -l < "$calls" | xargs)" = "$before_calls" ]
    [ "$(readlink "$orchestrator/user-link")" = "../outside-user-target" ]
}

@test "dsh lifecycle: update recovery-path collision fails before package mutation" {
    fake_bin="$(install_fake_dsh)"
    command=(env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
    run "${command[@]}" install --profile web
    [ "$status" -eq 0 ]
    collision="$TEST_DSH_HOME/.agent-presets/.softspark-orchestrator.ai-toolkit-new"
    mkdir -p "$collision"
    printf '%s\n' 'user collision' > "$collision/keep.txt"
    before_calls="$(cat "$TEST_DSH_HOME/fake-argv.jsonl")"

    run "${command[@]}" update --profile web

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'recovery collision'
    [ "$(cat "$collision/keep.txt")" = 'user collision' ]
    [ "$(cat "$TEST_DSH_HOME/fake-argv.jsonl")" = "$before_calls" ]
}

@test "dsh lifecycle: uninstall removes only owned packages and preset" {
    fake_bin="$(install_fake_dsh)"
    mkdir -p "$TEST_HOME/.softspark/ai-toolkit"
    cat > "$TEST_HOME/.softspark/ai-toolkit/state.json" <<'JSON'
{"installed_version":"4.29.2","installed_modules":["core"]}
JSON
    command=(env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
    run "${command[@]}" install --profile web
    [ "$status" -eq 0 ]
    mkdir -p "$TEST_DSH_HOME/profiles/web/node_modules/unrelated" \
        "$TEST_DSH_HOME/.agent-presets/user-preset"
    printf '%s\n' 'keep plugin' > \
        "$TEST_DSH_HOME/profiles/web/node_modules/unrelated/keep.txt"
    printf '%s\n' 'keep preset' > \
        "$TEST_DSH_HOME/.agent-presets/user-preset/preset.md"
    python3 - "$TEST_DSH_HOME/profiles/web/package.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
document = json.loads(path.read_text())
document["dependencies"]["unrelated"] = "2.0.0"
path.write_text(json.dumps(document) + "\n")
PY

    run "${command[@]}" uninstall --profile web --yes

    [ "$status" -eq 0 ]
    [ ! -e "$TEST_DSH_HOME/.agent-presets/softspark-orchestrator" ]
    [ "$(cat "$TEST_DSH_HOME/.agent-presets/user-preset/preset.md")" = 'keep preset' ]
    [ "$(cat "$TEST_DSH_HOME/profiles/web/node_modules/unrelated/keep.txt")" = 'keep plugin' ]
    python3 - "$TEST_DSH_HOME" "$TEST_HOME/.softspark/ai-toolkit/state.json" <<'PY'
import json
import sys
from pathlib import Path

dsh_home = Path(sys.argv[1])
manifest = json.loads((dsh_home / "profiles/web/package.json").read_text())
assert manifest["dependencies"] == {"unrelated": "2.0.0"}, manifest
state = json.loads(Path(sys.argv[2]).read_text())
assert "dsh" not in state
assert state["installed_version"] == "4.29.2"
assert state["installed_modules"] == ["core"]
calls = [json.loads(line) for line in (dsh_home / "fake-argv.jsonl").read_text().splitlines()]
assert calls[-2:] == [
    ["plugin", "--profile", "web", "remove", "@softspark/dsh-orchestrator"],
    ["plugin", "--profile", "web", "remove", "@softspark/dsh-codex"],
], calls
PY
}

@test "dsh lifecycle: declined uninstall confirmation changes no owned bytes" {
    fake_bin="$(install_fake_dsh)"
    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh install --profile web
    [ "$status" -eq 0 ]
    before_dsh="$(surface_fingerprint "$TEST_DSH_HOME")"
    before_state="$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")"

    run bash -c "printf 'n\n' | env HOME='$TEST_HOME' DSH_HOME='$TEST_DSH_HOME' \
        PATH='$fake_bin:$PATH' node '$TOOLKIT_DIR/bin/ai-toolkit.js' \
        dsh uninstall --profile web"

    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'uninstall cancelled'
    [ "$(surface_fingerprint "$TEST_DSH_HOME")" = "$before_dsh" ]
    [ "$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")" = "$before_state" ]
}

@test "dsh lifecycle: owned update and uninstall dry-runs perform zero mutations" {
    fake_bin="$(install_fake_dsh)"
    command=(env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
    run "${command[@]}" install --profile web
    [ "$status" -eq 0 ]
    before_dsh="$(surface_fingerprint "$TEST_DSH_HOME")"
    before_state="$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")"

    run "${command[@]}" update --profile web --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'PLAN argv:'
    [ "$(surface_fingerprint "$TEST_DSH_HOME")" = "$before_dsh" ]
    [ "$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")" = "$before_state" ]

    run "${command[@]}" uninstall --profile web --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'PLAN remove preset:'
    echo "$output" | grep -q 'PLAN remove state: dsh.profiles.web'
    [ "$(surface_fingerprint "$TEST_DSH_HOME")" = "$before_dsh" ]
    [ "$(shasum "$TEST_HOME/.softspark/ai-toolkit/state.json")" = "$before_state" ]
}

@test "dsh: explicit dry-run writes nothing and excludes implicit selection" {
    printf '%s\n' 'dry-run sentinel' > "$TEST_DSH_HOME/sentinel.txt"
    before_dsh=$(shasum "$TEST_DSH_HOME/sentinel.txt")
    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' DSH_HOME='$TEST_DSH_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors dsh --dry-run"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Editors: dsh'
    echo "$output" | grep -q 'Would generate: .agents/skills/ DSH-compatible managed skills'
    [ -z "$(find "$TEST_PROJECT" -mindepth 1 -print -quit)" ]
    [ "$(shasum "$TEST_DSH_HOME/sentinel.txt")" = "$before_dsh" ]
    [ "$(find "$TEST_DSH_HOME" -mindepth 1 -maxdepth 1 | wc -l | xargs)" -eq 1 ]

    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' DSH_HOME='$TEST_DSH_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors all --dry-run"
    [ "$status" -eq 0 ]
    if echo "$output" | grep -Eq 'Editors:.*(^|, )dsh(,|$)'; then
        false
    fi

    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' DSH_HOME='$TEST_DSH_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --profile full --dry-run"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Editors: none'
    if echo "$output" | grep -Eq 'Editors:.*(^|, )dsh(,|$)'; then
        false
    fi
}

@test "dsh: doctor reports installed and missing local AI runtimes" {
    fake_bin="$TEST_PROJECT/fake-bin"
    mkdir -p "$fake_bin"
    for spec in \
        'dsh:DSH:1.2.3' \
        'codex:Codex:2.3.4' \
        'claude:Claude:3.4.5' \
        'copilot:Copilot:4.5.6'; do
        binary=${spec%%:*}
        rest=${spec#*:}
        label=${rest%%:*}
        version=${rest##*:}
        cat > "$fake_bin/$binary" <<SH
#!/bin/sh
printf '%s %s\n' '$label' '$version'
SH
        chmod +x "$fake_bin/$binary"
    done

    python_bin=$(command -v python3)
    run env HOME="$TEST_HOME" PATH="$fake_bin:$PATH" \
        "$python_bin" "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q '^## AI Runtimes$'
    echo "$output" | grep -q 'OK: DSH (dsh) 1.2.3'
    echo "$output" | grep -q 'OK: Codex (codex) 2.3.4'
    echo "$output" | grep -q 'OK: Claude Code (claude) 3.4.5'
    echo "$output" | grep -q 'OK: GitHub Copilot (copilot) 4.5.6'

    rm "$fake_bin/dsh"
    run env HOME="$TEST_HOME" PATH="$fake_bin:/usr/bin:/bin" \
        "$python_bin" "$TOOLKIT_DIR/scripts/doctor.py"
    echo "$output" | grep -q 'SKIP: DSH (dsh) not found'
}

@test "dsh: local install emits only the shared managed skill surface idempotently" {
    printf '%s\n' 'owned by dsh user' > "$TEST_DSH_HOME/sentinel.txt"
    before_dsh=$(shasum "$TEST_DSH_HOME/sentinel.txt")
    fake_bin="$TEST_PROJECT/fake-bin"
    mkdir -p "$fake_bin"
    for binary in dsh npm; do
        cat > "$fake_bin/$binary" <<SH
#!/bin/sh
printf '%s\n' '$binary invoked' >> '$TEST_PROJECT/unexpected-runtime-call'
exit 99
SH
        chmod +x "$fake_bin/$binary"
    done

    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' DSH_HOME='$TEST_DSH_HOME' PATH='$fake_bin:$PATH' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors dsh"
    [ "$status" -eq 0 ]

    expected=$(find "$TOOLKIT_DIR/app/skills" -mindepth 1 -maxdepth 1 \
        -type d -not -name '_*' -exec test -f '{}/SKILL.md' ';' -print | wc -l | xargs)
    actual=$(find "$TEST_PROJECT/.agents/skills" -mindepth 1 -maxdepth 1 \
        \( -type d -o -type l \) | wc -l | xargs)
    [ "$actual" -eq "$expected" ]
    [ -z "$(find "$TEST_PROJECT/.agents/skills" -mindepth 3 -name SKILL.md -print -quit)" ]
    for skill in "$TEST_PROJECT"/.agents/skills/*; do
        [ -f "$skill/SKILL.md" ]
    done
    [ "$(cat "$TEST_PROJECT/.agents/.ai-toolkit-skill-owners")" = 'dsh' ]

    [ ! -e "$TEST_PROJECT/AGENTS.md" ]
    [ ! -e "$TEST_PROJECT/.codex" ]
    [ ! -e "$TEST_PROJECT/unexpected-runtime-call" ]
    [ "$(shasum "$TEST_DSH_HOME/sentinel.txt")" = "$before_dsh" ]
    [ "$(find "$TEST_DSH_HOME" -mindepth 1 -maxdepth 1 | wc -l | xargs)" -eq 1 ]

    first_manifest=$(for skill in "$TEST_PROJECT"/.agents/skills/*; do
        printf '%s ' "$(basename "$skill")"
        shasum "$skill/SKILL.md"
    done)
    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' DSH_HOME='$TEST_DSH_HOME' PATH='$fake_bin:$PATH' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors dsh"
    [ "$status" -eq 0 ]
    second_manifest=$(for skill in "$TEST_PROJECT"/.agents/skills/*; do
        printf '%s ' "$(basename "$skill")"
        shasum "$skill/SKILL.md"
    done)
    [ "$second_manifest" = "$first_manifest" ]
    [ "$(shasum "$TEST_DSH_HOME/sentinel.txt")" = "$before_dsh" ]
}

@test "dsh: invalid regular owner marker is rejected before managed bytes change" {
    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors codex"
    [ "$status" -eq 0 ]
    marker="$TEST_PROJECT/.agents/.ai-toolkit-skill-owners"
    printf '%s\n' 'codex, dsh' > "$marker"
    before=$(surface_fingerprint "$TEST_PROJECT/.agents")

    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors dsh"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'invalid skill-surface owner marker'
    after=$(surface_fingerprint "$TEST_PROJECT/.agents")
    [ "$after" = "$before" ]
}

@test "dsh: every noncanonical regular owner marker blocks install unchanged" {
    for variant in reversed duplicate unknown leading-space trailing-space blank-line; do
        project="$TEST_PROJECT/$variant"
        marker="$project/.agents/.ai-toolkit-skill-owners"
        mkdir -p "$project/.agents/skills/user-skill"
        printf '%s\n' 'user content' > "$project/.agents/skills/user-skill/notes.txt"
        case "$variant" in
            reversed) printf '%s\n' 'dsh' 'codex' > "$marker" ;;
            duplicate) printf '%s\n' 'codex' 'codex' > "$marker" ;;
            unknown) printf '%s\n' 'codex' 'user-runtime' > "$marker" ;;
            leading-space) printf ' codex\n' > "$marker" ;;
            trailing-space) printf 'codex \n' > "$marker" ;;
            blank-line) printf 'codex\n\n' > "$marker" ;;
        esac
        before=$(surface_fingerprint "$project/.agents")

        run bash -c "cd '$project' && HOME='$TEST_HOME' \
            python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors dsh"
        [ "$status" -ne 0 ]
        echo "$output" | grep -q 'invalid skill-surface owner marker'
        after=$(surface_fingerprint "$project/.agents")
        [ "$after" = "$before" ]
    done
}

@test "dsh: symlink owner marker is rejected before managed bytes change" {
    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors codex"
    [ "$status" -eq 0 ]
    marker="$TEST_PROJECT/.agents/.ai-toolkit-skill-owners"
    mv "$marker" "$TEST_PROJECT/.agents/original-owner-marker"
    printf '%s\n' 'codex' > "$TEST_PROJECT/external-owner-marker"
    ln -s "$TEST_PROJECT/external-owner-marker" "$marker"
    before=$(surface_fingerprint "$TEST_PROJECT/.agents")

    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors dsh"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'invalid skill-surface owner marker.*symlink'
    after=$(surface_fingerprint "$TEST_PROJECT/.agents")
    [ "$after" = "$before" ]
    [ "$(cat "$TEST_PROJECT/external-owner-marker")" = 'codex' ]
}

@test "dsh: directory owner marker fails before any managed wrapper transition" {
    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors codex"
    [ "$status" -eq 0 ]
    marker="$TEST_PROJECT/.agents/.ai-toolkit-skill-owners"
    mv "$marker" "$TEST_PROJECT/.agents/original-owner-marker"
    mkdir "$marker"
    before=$(surface_fingerprint "$TEST_PROJECT/.agents")

    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors dsh"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'invalid skill-surface owner marker.*directory'
    after=$(surface_fingerprint "$TEST_PROJECT/.agents")
    [ "$after" = "$before" ]
}

@test "dsh: unreadable owner marker is rejected before managed bytes change" {
    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors codex"
    [ "$status" -eq 0 ]
    before=$(surface_fingerprint "$TEST_PROJECT/.agents")

    run env PYTHONPATH="$TOOLKIT_DIR/scripts:$TOOLKIT_DIR/scripts/install_steps" \
        python3 - "$TEST_PROJECT" <<'PY'
import sys
from pathlib import Path

from install_steps import ai_tools

project = Path(sys.argv[1])
marker = project / ".agents" / ".ai-toolkit-skill-owners"
real_read_bytes = Path.read_bytes


def deny_marker_read(path):
    if path == marker:
        raise PermissionError("injected unreadable owner marker")
    return real_read_bytes(path)


Path.read_bytes = deny_marker_read
try:
    ai_tools._install_agent_skills(project, target="dsh")
finally:
    Path.read_bytes = real_read_bytes
PY
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'invalid skill-surface owner marker.*cannot read regular marker'
    after=$(surface_fingerprint "$TEST_PROJECT/.agents")
    [ "$after" = "$before" ]
}

@test "dsh: final owner marker failure rolls back every managed byte" {
    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors codex"
    [ "$status" -eq 0 ]
    printf '%s\n' 'preserve user addition' > \
        "$TEST_PROJECT/.agents/skills/orchestrate/user-added.txt"
    before=$(surface_fingerprint "$TEST_PROJECT/.agents")

    run env PYTHONPATH="$TOOLKIT_DIR/scripts:$TOOLKIT_DIR/scripts/install_steps" \
        python3 - "$TEST_PROJECT" <<'PY'
import os
import sys
from pathlib import Path

import codex_skill_adapter
from install_steps import ai_tools

project = Path(sys.argv[1])
real_replace = codex_skill_adapter.os.replace
failed = False


def fail_final_marker(source, destination):
    global failed
    destination = Path(destination)
    if (
        not failed
        and destination.name == codex_skill_adapter.SKILL_SURFACE_OWNERS_MARKER
    ):
        failed = True
        raise OSError("injected final owner-marker write failure")
    return real_replace(source, destination)


codex_skill_adapter.os.replace = fail_final_marker
try:
    ai_tools._install_agent_skills(project, target="dsh")
finally:
    codex_skill_adapter.os.replace = real_replace
assert failed, "owner marker replacement was not reached"
PY
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'injected final owner-marker write failure'
    after=$(surface_fingerprint "$TEST_PROJECT/.agents")
    [ "$after" = "$before" ]
    [ -f "$TEST_PROJECT/.agents/skills/orchestrate/user-added.txt" ]
}

@test "dsh: managed sync failure rolls back without removing user additions" {
    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors codex"
    [ "$status" -eq 0 ]
    printf '%s\n' 'preserve user addition' > \
        "$TEST_PROJECT/.agents/skills/orchestrate/user-added.txt"
    before=$(surface_fingerprint "$TEST_PROJECT/.agents")

    run env PYTHONPATH="$TOOLKIT_DIR/scripts:$TOOLKIT_DIR/scripts/install_steps" \
        python3 - "$TEST_PROJECT" <<'PY'
import sys
from pathlib import Path

from install_steps import ai_tools

project = Path(sys.argv[1])
real_sync = ai_tools.sync_dsh_skill
calls = 0


def fail_managed_sync(*args, **kwargs):
    global calls
    calls += 1
    if calls == 5:
        raise OSError("injected managed sync failure")
    return real_sync(*args, **kwargs)


ai_tools.sync_dsh_skill = fail_managed_sync
try:
    ai_tools._install_agent_skills(project, target="dsh")
finally:
    ai_tools.sync_dsh_skill = real_sync
assert calls == 5, calls
PY
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'injected managed sync failure'
    after=$(surface_fingerprint "$TEST_PROJECT/.agents")
    [ "$after" = "$before" ]
    [ -f "$TEST_PROJECT/.agents/skills/orchestrate/user-added.txt" ]
}

@test "dsh: user-added wrapper files survive coherent owner transitions both ways" {
    wrapper="$TEST_PROJECT/.agents/skills/orchestrate"
    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors codex"
    [ "$status" -eq 0 ]
    codex_skill_hash=$(shasum "$wrapper/SKILL.md")
    printf '%s\n' 'user content survives every owner transition' > \
        "$wrapper/user-added.txt"
    mkdir "$wrapper/user-added-directory"
    printf '%s\n' 'nested user content' > \
        "$wrapper/user-added-directory/nested.txt"
    printf '%s\n' 'external user target' > "$TEST_PROJECT/user-link-target.txt"
    ln -s "$TEST_PROJECT/user-link-target.txt" "$wrapper/user-added-link"
    user_hash=$(shasum "$wrapper/user-added.txt")
    user_directory_hash=$(shasum "$wrapper/user-added-directory/nested.txt")

    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors dsh"
    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_PROJECT/.agents/.ai-toolkit-skill-owners")" = 'dsh' ]
    [ -f "$wrapper/.ai-toolkit-dsh-adapted" ]
    [ ! -e "$wrapper/.ai-toolkit-codex-adapted" ]
    grep -q 'Portable Translation Layer' "$wrapper/SKILL.md"
    [ "$(shasum "$wrapper/user-added.txt")" = "$user_hash" ]
    [ "$(shasum "$wrapper/user-added-directory/nested.txt")" = "$user_directory_hash" ]
    [ "$(readlink "$wrapper/user-added-link")" = "$TEST_PROJECT/user-link-target.txt" ]

    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors codex,dsh"
    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_PROJECT/.agents/.ai-toolkit-skill-owners")" = $'codex\ndsh' ]
    [ -f "$wrapper/.ai-toolkit-shared-adapted" ]
    [ ! -e "$wrapper/.ai-toolkit-dsh-adapted" ]
    [ "$(shasum "$wrapper/user-added.txt")" = "$user_hash" ]
    [ "$(shasum "$wrapper/user-added-directory/nested.txt")" = "$user_directory_hash" ]
    [ "$(readlink "$wrapper/user-added-link")" = "$TEST_PROJECT/user-link-target.txt" ]

    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors codex"
    [ "$status" -eq 0 ]
    [ "$(cat "$TEST_PROJECT/.agents/.ai-toolkit-skill-owners")" = 'codex' ]
    [ -f "$wrapper/.ai-toolkit-codex-adapted" ]
    [ ! -e "$wrapper/.ai-toolkit-dsh-adapted" ]
    grep -q 'Codex Translation Layer' "$wrapper/SKILL.md"
    [ "$(shasum "$wrapper/SKILL.md")" = "$codex_skill_hash" ]
    [ "$(shasum "$wrapper/user-added.txt")" = "$user_hash" ]
    [ "$(shasum "$wrapper/user-added-directory/nested.txt")" = "$user_directory_hash" ]
    [ "$(readlink "$wrapper/user-added-link")" = "$TEST_PROJECT/user-link-target.txt" ]
}

@test "dsh: action skills preserve invocation metadata with portable guidance" {
    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' DSH_HOME='$TEST_DSH_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors dsh"
    [ "$status" -eq 0 ]

    for skill in deploy rollback chaos; do
        skill_dir="$TEST_PROJECT/.agents/skills/$skill"
        skill_file="$skill_dir/SKILL.md"
        [ -f "$skill_file" ]
        grep -q '^disable-model-invocation: true$' "$skill_file"
        ! grep -q 'Codex Translation Layer' "$skill_file"
        ! grep -q 'Codex-native' "$skill_file"
        [ ! -e "$skill_dir/.ai-toolkit-codex-adapted" ]
    done

    run validate_emitted "$TEST_PROJECT"
    [ "$status" -eq 0 ]
}

@test "dsh: every adapted skill preserves its complete invocation contract" {
    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' DSH_HOME='$TEST_DSH_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors dsh"
    [ "$status" -eq 0 ]

    run env PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - \
        "$TOOLKIT_DIR/app/skills" "$TEST_PROJECT/.agents/skills" <<'PY'
import sys
from pathlib import Path

from codex_skill_adapter import is_codex_adapted_skill

source_root = Path(sys.argv[1])
emitted_root = Path(sys.argv[2])
invocation_fields = ("user-invocable", "disable-model-invocation")
codex_only_guidance = (
    "Codex Translation Layer",
    "Codex-native",
    "Codex-specific",
)


def frontmatter_lines(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---", path
    closing = lines.index("---", 1)
    return lines[1:closing]


adapted = 0
for source_file in sorted(source_root.glob("*/SKILL.md")):
    if not is_codex_adapted_skill(source_file):
        continue
    adapted += 1
    emitted_file = emitted_root / source_file.parent.name / "SKILL.md"
    source_lines = frontmatter_lines(source_file)
    emitted_lines = frontmatter_lines(emitted_file)
    for field in invocation_fields:
        source_values = [
            line for line in source_lines if line.startswith(f"{field}:")
        ]
        emitted_values = [
            line for line in emitted_lines if line.startswith(f"{field}:")
        ]
        assert emitted_values == source_values, (
            source_file.parent.name,
            field,
            source_values,
            emitted_values,
        )
        assert len(emitted_values) <= 1, (source_file.parent.name, field)
    emitted_text = emitted_file.read_text(encoding="utf-8")
    assert not any(token in emitted_text for token in codex_only_guidance), (
        source_file.parent.name,
        emitted_file,
    )

assert adapted > 0
print(f"validated={adapted}")
PY
    [ "$status" -eq 0 ]
    echo "$output" | grep -Eq '^validated=[1-9][0-9]*$'
}

@test "dsh: adapted renderer preserves exact quoted invocation metadata" {
    run env PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - "$TEST_PROJECT" <<'PY'
import sys
from pathlib import Path

from codex_skill_adapter import build_dsh_skill_text

root = Path(sys.argv[1])
fixtures = {
    "quoted-lower": (
        'user-invocable: "false"',
        "disable-model-invocation: 'true'",
    ),
    "quoted-alternate": (
        "user-invocable: 'YES'",
        'disable-model-invocation: "OFF"',
    ),
}

for name, invocation_lines in fixtures.items():
    source = root / f"{name}.md"
    source.write_text(
        "---\n"
        f"name: {name}\n"
        f"description: Exact metadata for {name}.\n"
        "allowed-tools: Agent, Bash\n"
        "argument-hint: unsupported output field\n"
        f"{invocation_lines[0]}\n"
        f"{invocation_lines[1]}\n"
        "---\n"
        "Agent(prompt=\"delegate\")\n",
        encoding="utf-8",
    )
    rendered = build_dsh_skill_text(source)
    frontmatter = rendered.split("---", 2)[1].splitlines()
    for line in invocation_lines:
        assert frontmatter.count(line) == 1, (name, line, frontmatter)
    assert not any(line.startswith("allowed-tools:") for line in frontmatter)
    assert not any(line.startswith("argument-hint:") for line in frontmatter)
    assert "Codex Translation Layer" not in rendered
    assert "Codex-native" not in rendered

duplicate = root / "duplicate.md"
duplicate.write_text(
    "---\n"
    "name: duplicate\n"
    "description: Duplicate invocation metadata.\n"
    "allowed-tools: Agent\n"
    "user-invocable: true\n"
    "user-invocable: false\n"
    "---\n"
    "Agent(prompt=\"delegate\")\n",
    encoding="utf-8",
)
try:
    build_dsh_skill_text(duplicate)
except ValueError as error:
    assert "Duplicate invocation metadata field: user-invocable" in str(error)
else:
    raise AssertionError("duplicate invocation metadata must not be rendered")
PY
    [ "$status" -eq 0 ]
}

@test "dsh: codex and dsh share one deterministic portable skill surface" {
    first="$TEST_PROJECT/codex-dsh"
    second="$TEST_PROJECT/dsh-codex"
    codex_only="$TEST_PROJECT/codex-only"
    mkdir -p "$first" "$second" "$codex_only"

    run bash -c "cd '$first' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors codex,dsh"
    [ "$status" -eq 0 ]
    run bash -c "cd '$second' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors dsh,codex"
    [ "$status" -eq 0 ]
    cmp "$first/.agents/skills/orchestrate/SKILL.md" \
        "$second/.agents/skills/orchestrate/SKILL.md"
    first_surface=$(surface_fingerprint "$first/.agents/skills")
    second_surface=$(surface_fingerprint "$second/.agents/skills")
    [ "$second_surface" = "$first_surface" ]
    grep -q 'Portable Translation Layer' \
        "$first/.agents/skills/orchestrate/SKILL.md"
    [ -e "$first/.agents/skills/orchestrate/.ai-toolkit-shared-adapted" ]
    [ "$(cat "$first/.agents/.ai-toolkit-skill-owners")" = $'codex\ndsh' ]

    run bash -c "cd '$first' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors dsh,codex"
    [ "$status" -eq 0 ]
    repeated_surface=$(surface_fingerprint "$first/.agents/skills")
    [ "$repeated_surface" = "$first_surface" ]

    run bash -c "cd '$codex_only' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors codex"
    [ "$status" -eq 0 ]
    grep -q 'Codex Translation Layer' \
        "$codex_only/.agents/skills/orchestrate/SKILL.md"
    [ -e "$codex_only/.agents/skills/orchestrate/.ai-toolkit-codex-adapted" ]
    [ "$(cat "$codex_only/.agents/.ai-toolkit-skill-owners")" = 'codex' ]
}

@test "dsh: a second bare local install does not activate codex implicitly" {
    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --editors dsh"
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_PROJECT/AGENTS.md" ]
    [ ! -e "$TEST_PROJECT/.codex" ]

    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Editors: none'
    [ ! -e "$TEST_PROJECT/AGENTS.md" ]
    [ ! -e "$TEST_PROJECT/.codex" ]
}

@test "dsh: emitted-skill validator rejects missing closing frontmatter delimiter" {
    fixture="$TEST_PROJECT/emitted"
    mkdir -p "$fixture/.agents/skills/no-close"
    cat > "$fixture/.agents/skills/no-close/SKILL.md" <<'MD'
---
name: no-close
description: Frontmatter never closes.
Body is incorrectly parsed as metadata.
MD

    run validate_emitted "$fixture"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'missing closing frontmatter delimiter'
}

@test "dsh: emitted-skill validator requires an opening frontmatter delimiter" {
    fixture="$TEST_PROJECT/emitted"
    mkdir -p "$fixture/.agents/skills/no-open"
    cat > "$fixture/.agents/skills/no-open/SKILL.md" <<'MD'
name: no-open
description: Frontmatter never opens.
---
Body.
MD

    run validate_emitted "$fixture"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'missing opening frontmatter delimiter'
}

@test "dsh: emitted-skill validator requires non-empty name and description" {
    fixture="$TEST_PROJECT/emitted"
    mkdir -p "$fixture/.agents/skills/missing-name"
    cat > "$fixture/.agents/skills/missing-name/SKILL.md" <<'MD'
---
name:
description: Present.
---
Body.
MD
    mkdir -p "$fixture/.agents/skills/missing-description"
    cat > "$fixture/.agents/skills/missing-description/SKILL.md" <<'MD'
---
name: missing-description
description: ""
---
Body.
MD

    run validate_emitted "$fixture"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "required field 'name' must be non-empty"
    echo "$output" | grep -q "required field 'description' must be non-empty"
}

@test "dsh: emitted-skill validator rejects duplicate and mismatched names" {
    fixture="$TEST_PROJECT/emitted"
    mkdir -p "$fixture/.agents/skills/duplicate-name"
    cat > "$fixture/.agents/skills/duplicate-name/SKILL.md" <<'MD'
---
name: duplicate-name
name: duplicate-name
description: Duplicate.
---
Body.
MD
    mkdir -p "$fixture/.agents/skills/directory-name"
    cat > "$fixture/.agents/skills/directory-name/SKILL.md" <<'MD'
---
name: declared-name
description: Mismatch.
---
Body.
MD

    run validate_emitted "$fixture"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "duplicate top-level key 'name'"
    echo "$output" | grep -q "does not match directory 'directory-name'"
}

@test "dsh: emitted-skill parser rejects non-scalar YAML and preserves quoted scalars" {
    fixture="$TEST_PROJECT/emitted-invalid"
    mkdir -p \
        "$fixture/.agents/skills/unexpected-indent" \
        "$fixture/.agents/skills/unterminated-single" \
        "$fixture/.agents/skills/unterminated-double" \
        "$fixture/.agents/skills/literal-block" \
        "$fixture/.agents/skills/flow-sequence" \
        "$fixture/.agents/skills/flow-mapping"
    cat > "$fixture/.agents/skills/unexpected-indent/SKILL.md" <<'MD'
---
name: unexpected-indent
description: Scalar value.
  unexpected continuation
---
Body.
MD
    cat > "$fixture/.agents/skills/unterminated-single/SKILL.md" <<'MD'
---
name: unterminated-single
description: 'Unterminated scalar.
---
Body.
MD
    cat > "$fixture/.agents/skills/unterminated-double/SKILL.md" <<'MD'
---
name: unterminated-double
description: "Unterminated scalar.
---
Body.
MD
    cat > "$fixture/.agents/skills/literal-block/SKILL.md" <<'MD'
---
name: literal-block
description: |-
  Unsupported block scalar.
---
Body.
MD
    cat > "$fixture/.agents/skills/flow-sequence/SKILL.md" <<'MD'
---
name: flow-sequence
description: [unsupported, collection]
---
Body.
MD
    cat > "$fixture/.agents/skills/flow-mapping/SKILL.md" <<'MD'
---
name: flow-mapping
description: {unsupported: mapping}
---
Body.
MD

    run validate_emitted "$fixture"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'unexpected-indent/SKILL.md:4 - unexpected indentation'
    echo "$output" | grep -q 'unterminated-single/SKILL.md:3 - unterminated single-quoted scalar'
    echo "$output" | grep -q 'unterminated-double/SKILL.md:3 - unterminated double-quoted scalar'
    echo "$output" | grep -q 'literal-block/SKILL.md:3 - unsupported block scalar'
    echo "$output" | grep -q 'flow-sequence/SKILL.md:3 - unsupported collection value'
    echo "$output" | grep -q 'flow-mapping/SKILL.md:3 - unsupported collection value'

    valid="$TEST_PROJECT/emitted-valid"
    mkdir -p "$valid/.agents/skills/quoted-scalars"
    cat > "$valid/.agents/skills/quoted-scalars/SKILL.md" <<'MD'
---
name: quoted-scalars
description: "Double-quoted: # remains scalar"
argument-hint: 'Single-quoted: # remains scalar'
---
Body.
MD

    run validate_emitted "$valid"
    [ "$status" -eq 0 ]
}

@test "dsh: emitted-skill validator accepts pinned boolean spellings" {
    fixture="$TEST_PROJECT/emitted"
    for spec in \
        'valid-yes:user-invocable:YES' \
        'valid-on:user-invocable:on' \
        'valid-one:disable-model-invocation:1' \
        'valid-quoted:disable-model-invocation:"false"'; do
        name=${spec%%:*}
        rest=${spec#*:}
        field=${rest%%:*}
        value=${rest#*:}
        mkdir -p "$fixture/.agents/skills/$name"
        printf '%s\n' '---' "name: $name" "description: Valid $name." \
            "$field: $value" '---' 'Body.' \
            > "$fixture/.agents/skills/$name/SKILL.md"
    done

    run validate_emitted "$fixture"
    [ "$status" -eq 0 ]
}

@test "dsh: emitted-skill validator rejects invalid and camel-case invocation values" {
    fixture="$TEST_PROJECT/emitted"
    mkdir -p "$fixture/.agents/skills/invalid-invocation"
    cat > "$fixture/.agents/skills/invalid-invocation/SKILL.md" <<'MD'
---
name: invalid-invocation
description: Invalid invocation metadata.
userInvocable: false
disableModelInvocation: true
user-invocable: sometimes
---
Body.
MD

    run validate_emitted "$fixture"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "camel-case field 'userInvocable' is forbidden"
    echo "$output" | grep -q "camel-case field 'disableModelInvocation' is forbidden"
    echo "$output" | grep -q "field 'user-invocable' has invalid boolean value"
}

@test "dsh: emitted-skill validator fails closed on YAML key indirection" {
    fixture="$TEST_PROJECT/emitted"
    for name in quoted-key spaced-key anchored-value aliased-value merged-key; do
        mkdir -p "$fixture/.agents/skills/$name"
    done
    cat > "$fixture/.agents/skills/quoted-key/SKILL.md" <<'MD'
---
name: quoted-key
description: Quoted invocation key.
"userInvocable": false
---
Body.
MD
    cat > "$fixture/.agents/skills/spaced-key/SKILL.md" <<'MD'
---
name: spaced-key
description: Spaced invocation key.
userInvocable : false
---
Body.
MD
    cat > "$fixture/.agents/skills/anchored-value/SKILL.md" <<'MD'
---
name: anchored-value
description: Anchored invocation value.
user-invocable: &invocation.flag false
---
Body.
MD
    cat > "$fixture/.agents/skills/aliased-value/SKILL.md" <<'MD'
---
name: aliased-value
description: Aliased invocation value.
disable-model-invocation: *invocation.flag
---
Body.
MD
    cat > "$fixture/.agents/skills/merged-key/SKILL.md" <<'MD'
---
name: merged-key
description: Merged invocation metadata.
<<: *invocation-defaults
---
Body.
MD

    run validate_emitted "$fixture"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'quoted-key/SKILL.md:4 - quoted frontmatter keys are unsupported'
    echo "$output" | grep -q "spaced-key/SKILL.md:4 - whitespace before ':' is unsupported"
    echo "$output" | grep -q 'anchored-value/SKILL.md:4 - YAML anchors are unsupported'
    echo "$output" | grep -q 'aliased-value/SKILL.md:4 - YAML aliases are unsupported'
    echo "$output" | grep -q "merged-key/SKILL.md:4 - YAML merge key '<<' is unsupported"
}

@test "dsh: emitted-skill validator enforces kebab-case one-level layout" {
    fixture="$TEST_PROJECT/emitted"
    mkdir -p "$fixture/.agents/skills/Bad_Name"
    cat > "$fixture/.agents/skills/Bad_Name/SKILL.md" <<'MD'
---
name: bad-name
description: Invalid directory fixture.
---
Fixture.
MD
    mkdir -p "$fixture/.agents/skills/invalid-name"
    cat > "$fixture/.agents/skills/invalid-name/SKILL.md" <<'MD'
---
name: Invalid_Name
description: Invalid declared name fixture.
---
Fixture.
MD
    mkdir -p "$fixture/.agents/skills/valid-skill/reference/nested"
    cat > "$fixture/.agents/skills/valid-skill/SKILL.md" <<'MD'
---
name: valid-skill
description: Valid top-level fixture.
---
Fixture.
MD
    cat > "$fixture/.agents/skills/valid-skill/reference/nested/SKILL.md" <<'MD'
---
name: nested-skill
description: Invalid nested fixture.
---
Fixture.
MD

    run validate_emitted "$fixture"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q '.agents/skills/Bad_Name - invalid skill directory name'
    echo "$output" | grep -q 'name must be kebab-case'
    echo "$output" | grep -q 'nested SKILL.md is not discoverable'
}

@test "dsh: emitted-skill validator rejects nested SKILL.md in symlinked bundle" {
    fixture="$TEST_PROJECT/emitted"
    source_bundle="$fixture/source/symlinked-skill"
    mkdir -p "$fixture/.agents/skills" "$source_bundle/reference/nested"
    cat > "$source_bundle/SKILL.md" <<'MD'
---
name: symlinked-skill
description: Valid root skill in a symlinked bundle.
---
Fixture.
MD
    cat > "$source_bundle/reference/nested/SKILL.md" <<'MD'
---
name: nested-skill
description: Invalid nested fixture in a symlinked bundle.
---
Fixture.
MD
    ln -s "$source_bundle" "$fixture/.agents/skills/symlinked-skill"

    run validate_emitted "$fixture"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q \
        '.agents/skills/symlinked-skill/reference/nested/SKILL.md - nested SKILL.md is not discoverable'
}

@test "dsh: emitted-skill validator rejects escaping nested SKILL.md symlinks lexically" {
    fixture="$TEST_PROJECT/emitted-invalid"
    outside="$TEST_PROJECT/outside"
    mkdir -p \
        "$fixture/.agents/skills/external-file/reference" \
        "$fixture/.agents/skills/external-directory/reference" \
        "$outside/directory-target"
    for name in external-file external-directory; do
        cat > "$fixture/.agents/skills/$name/SKILL.md" <<MD
---
name: $name
description: Root skill with an escaping nested SKILL.md link.
---
Fixture.
MD
    done
    printf '%s\n' 'external file' > "$outside/external-skill.md"
    printf '%s\n' 'external directory file' > "$outside/directory-target/usage.md"
    ln -s "$outside/external-skill.md" \
        "$fixture/.agents/skills/external-file/reference/SKILL.md"
    ln -s "$outside/directory-target" \
        "$fixture/.agents/skills/external-directory/reference/SKILL.md"

    run validate_emitted "$fixture"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q \
        'external-file/reference/SKILL.md - nested SKILL.md is not discoverable'
    echo "$output" | grep -q \
        'external-directory/reference/SKILL.md - nested SKILL.md is not discoverable'

    valid="$TEST_PROJECT/emitted-valid"
    mkdir -p "$valid/.agents/skills/support-link/reference"
    cat > "$valid/.agents/skills/support-link/SKILL.md" <<'MD'
---
name: support-link
description: Root skill with an external support-file link.
---
Fixture.
MD
    ln -s "$outside/external-skill.md" \
        "$valid/.agents/skills/support-link/reference/usage.md"

    run validate_emitted "$valid"
    [ "$status" -eq 0 ]
}

@test "dsh: emitted-skill validator rejects symlink cycles within a bundle" {
    fixture="$TEST_PROJECT/emitted"
    source_bundle="$fixture/source/cyclic-skill"
    mkdir -p "$fixture/.agents/skills" "$source_bundle/reference"
    cat > "$source_bundle/SKILL.md" <<'MD'
---
name: cyclic-skill
description: Root skill with an invalid symlink cycle.
---
Fixture.
MD
    ln -s .. "$source_bundle/reference/cycle"
    ln -s "$source_bundle" "$fixture/.agents/skills/cyclic-skill"

    run validate_emitted "$fixture"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q \
        '.agents/skills/cyclic-skill/reference/cycle - symlink cycle detected'
}

@test "dsh: emitted-skill validator accepts a valid symlinked root bundle" {
    fixture="$TEST_PROJECT/emitted"
    source_bundle="$fixture/source/valid-symlinked-skill"
    mkdir -p "$fixture/.agents/skills" "$source_bundle/reference"
    cat > "$source_bundle/SKILL.md" <<'MD'
---
name: valid-symlinked-skill
description: Valid root skill in a symlinked bundle.
---
Fixture.
MD
    printf '%s\n' 'Supporting reference without nested skill metadata.' \
        > "$source_bundle/reference/usage.md"
    ln -s "$source_bundle" \
        "$fixture/.agents/skills/valid-symlinked-skill"

    run validate_emitted "$fixture"
    [ "$status" -eq 0 ]
}

@test "dsh: emitted-skill validator does not follow links outside the bundle" {
    fixture="$TEST_PROJECT/emitted"
    source_bundle="$fixture/source/escaping-skill"
    outside_bundle="$fixture/outside"
    mkdir -p "$fixture/.agents/skills" "$source_bundle/reference" \
        "$outside_bundle/nested"
    cat > "$source_bundle/SKILL.md" <<'MD'
---
name: escaping-skill
description: Root skill with a managed external support link.
---
Fixture.
MD
    cat > "$outside_bundle/nested/SKILL.md" <<'MD'
---
name: external-skill
description: External content must not be traversed.
---
Fixture.
MD
    ln -s "$outside_bundle" "$source_bundle/reference/external"
    ln -s "$source_bundle" "$fixture/.agents/skills/escaping-skill"

    run validate_emitted "$fixture"
    [ "$status" -eq 0 ]
    if echo "$output" | grep -q 'reference/external/nested/SKILL.md'; then
        false
    fi
}

@test "dsh: canonical skill validator rejects ambiguous invocation metadata" {
    fixture="$TEST_PROJECT/toolkit"
    mkdir -p "$fixture"
    tar -cf - -C "$TOOLKIT_DIR" --exclude=.git --exclude=node_modules . | \
        tar -xf - -C "$fixture"

    python3 - "$fixture/app/skills/clean-code/SKILL.md" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
closing = text.index("\n---\n", 4)
invalid = """
userInvocable: false
disableModelInvocation: true
user-invocable: sometimes
disable-model-invocation: "invalid"
""".rstrip()
path.write_text(text[:closing] + "\n" + invalid + text[closing:], encoding="utf-8")
PY

    run python3 "$fixture/scripts/validate.py" --strict "$fixture"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "camel-case field 'userInvocable' is forbidden"
    echo "$output" | grep -q "camel-case field 'disableModelInvocation' is forbidden"
    echo "$output" | grep -q "field 'user-invocable' has invalid boolean value"
    echo "$output" | grep -q "field 'disable-model-invocation' has invalid boolean value"
}

@test "dsh: canonical skill validator rejects duplicate invocation keys" {
    fixture="$TEST_PROJECT/toolkit"
    mkdir -p "$fixture"
    tar -cf - -C "$TOOLKIT_DIR" --exclude=.git --exclude=node_modules . | \
        tar -xf - -C "$fixture"

    python3 - "$fixture/app/skills/clean-code/SKILL.md" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
closing = text.index("\n---\n", 4)
duplicates = """
user-invocable: true
disable-model-invocation: false
disable-model-invocation: true
""".rstrip()
path.write_text(text[:closing] + "\n" + duplicates + text[closing:], encoding="utf-8")
PY

    run python3 "$fixture/scripts/validate.py" --strict "$fixture"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "duplicate canonical invocation key 'user-invocable'"
    echo "$output" | grep -q "duplicate canonical invocation key 'disable-model-invocation'"
}

@test "dsh: canonical validator fails closed on YAML invocation indirection" {
    fixture="$TEST_PROJECT/toolkit"
    mkdir -p "$fixture"
    tar -cf - -C "$TOOLKIT_DIR" --exclude=.git --exclude=node_modules . | \
        tar -xf - -C "$fixture"

    python3 - "$fixture/app/skills/clean-code/SKILL.md" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
closing = text.index("\n---\n", 4)
indirection = """
"userInvocable": false
disableModelInvocation : true
user-invocable: &enabled.flag true
disable-model-invocation: *enabled.flag
<<: *invocation-defaults
""".rstrip()
path.write_text(
    text[:closing] + "\n" + indirection + text[closing:],
    encoding="utf-8",
)
PY

    run python3 "$fixture/scripts/validate.py" --strict "$fixture"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'quoted frontmatter keys are unsupported'
    echo "$output" | grep -q "whitespace before ':' is unsupported"
    echo "$output" | grep -q 'YAML anchors are unsupported'
    echo "$output" | grep -q 'YAML aliases are unsupported'
    echo "$output" | grep -q "YAML merge key '<<' is unsupported"
}

@test "dsh: emitted-skill traversal bounds one directory before sorting" {
    fixture="$TEST_PROJECT/emitted/.agents/skills/bounded-enumeration"
    mkdir -p "$fixture"
    cat > "$fixture/SKILL.md" <<'MD'
---
name: bounded-enumeration
description: Synthetic bounded traversal fixture.
---
Fixture.
MD

    run env PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - "$fixture" <<'PY'
import contextlib
import io
import sys
from pathlib import Path

import validate

bundle = Path(sys.argv[1])
real_iterdir = Path.iterdir
consumed = 0


def oversized_directory(path):
    global consumed
    if path == bundle:
        for index in range(validate.MAX_EMITTED_SKILL_NODES + 500):
            consumed += 1
            yield path / f"synthetic-{index:05d}"
        return
    yield from real_iterdir(path)


Path.iterdir = oversized_directory
result = validate.ValidationResult()
try:
    with contextlib.redirect_stdout(io.StringIO()):
        validate._validate_emitted_skill_layout(
            bundle,
            ".agents/skills/bounded-enumeration",
            result,
        )
finally:
    Path.iterdir = real_iterdir

assert result.errors > 0
assert consumed <= validate.MAX_EMITTED_SKILL_NODES + 1, consumed
print(f"consumed={consumed}")

skills_root = bundle.parent
consumed = 0


def oversized_skill_root(path):
    global consumed
    if path == skills_root:
        for index in range(validate.MAX_EMITTED_SKILL_NODES + 500):
            consumed += 1
            yield path / f"synthetic-skill-{index:05d}"
        return
    yield from real_iterdir(path)


Path.iterdir = oversized_skill_root
result = validate.ValidationResult()
try:
    with contextlib.redirect_stdout(io.StringIO()):
        validate.validate_emitted_agent_skills(bundle.parents[2], result)
finally:
    Path.iterdir = real_iterdir

assert result.errors > 0
assert consumed <= validate.MAX_EMITTED_SKILL_NODES + 1, consumed
print(f"root-consumed={consumed}")
PY
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '^consumed=10001$'
    echo "$output" | grep -q '^root-consumed=10001$'
}

@test "dsh lifecycle: update preserves a byte-identical replacement of relocated backup" {
    fake_bin="$(install_fake_dsh)"
    command=(env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
    run "${command[@]}" install --profile web
    [ "$status" -eq 0 ]
    printf '%s\n' '{"preset_content_once":"updated preset\n"}' > \
        "$TEST_DSH_HOME/fake-control.json"
    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" PATH="$fake_bin:$PATH" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - <<'PY'
import shutil
from pathlib import Path

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
        and ".ai-toolkit-backup." in destination.parent.name
        and not injected
    ):
        injected = True
        original = destination.parent / ".original-relocated-payload"
        real_replace(destination, original)
        shutil.copytree(original, destination)


dsh._secure_rename_noreplace = replace_with_identical_inode
raise SystemExit(dsh.main(["update", "--profile", "web"]))
PY

    [ "$status" -ne 0 ]
    backup="$(find "$TEST_DSH_HOME/.agent-presets" -mindepth 1 -maxdepth 1 \
        -name '.softspark-orchestrator.ai-toolkit-backup.*' -print -quit)"
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

@test "dsh lifecycle: package inventory race refuses at the first plugin boundary" {
    fake_bin="$(install_fake_dsh)"

    for operation in install update uninstall; do
        case_root="$TEST_PROJECT/package-boundary-$operation"
        case_home="$case_root/home"
        dsh_home="$case_root/dsh"
        mkdir -p "$case_home" "$dsh_home"
        command=(env HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
        if [ "$operation" != install ]; then
            run "${command[@]}" install --profile web
            [ "$status" -eq 0 ]
        fi
        calls="$dsh_home/fake-argv.jsonl"
        before_calls=0
        if [ -f "$calls" ]; then
            before_calls="$(wc -l < "$calls" | xargs)"
        fi
        preset="$dsh_home/.agent-presets/softspark-orchestrator"
        state="$case_home/.softspark/ai-toolkit/state.json"
        if [ "$operation" != install ]; then
            before_preset="$(surface_fingerprint "$preset")"
            before_state="$(shasum "$state")"
        fi

        HOME="$case_home" DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            run python3 - "$TOOLKIT_DIR" "$operation" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
operation = sys.argv[2]
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

real_capture = dsh._capture_profile_transaction
injected = False


def inject_package_race(dsh_home, profile):
    global injected
    transaction = real_capture(dsh_home, profile)
    if injected:
        return transaction
    injected = True
    profile_root = dsh_home / "profiles" / profile
    manifest = profile_root / "package.json"
    profile_root.mkdir(parents=True, exist_ok=True)
    document = json.loads(manifest.read_text()) if manifest.exists() else {}
    dependencies = document.setdefault("dependencies", {})
    raced_version = "9.9.9" if operation == "install" else "1.0.0"
    dependencies["@softspark/dsh-codex"] = raced_version
    manifest.write_text(json.dumps(document, sort_keys=True) + "\n")
    package_root = profile_root / "node_modules/@softspark/dsh-codex"
    package_root.mkdir(parents=True, exist_ok=True)
    (package_root / "package.json").write_text(
        json.dumps(
            {
                "name": "@softspark/dsh-codex",
                "version": raced_version,
                "concurrent_change": True,
            }
        )
        + "\n"
    )
    return transaction


dsh._capture_profile_transaction = inject_package_race
arguments = [operation, "--profile", "web"]
if operation == "uninstall":
    arguments.append("--yes")
status = dsh.main(arguments)
assert injected, "package race injection was not reached"
raise SystemExit(status)
PY

        [ "$status" -ne 0 ]
        [[ "$output" == *"package inventory changed before external mutation"* ]]
        after_calls=0
        if [ -f "$calls" ]; then
            after_calls="$(wc -l < "$calls" | xargs)"
        fi
        [ "$after_calls" -eq "$before_calls" ]
        python3 - "$dsh_home/profiles/web" "$operation" <<'PY'
import json
import sys
from pathlib import Path

profile = Path(sys.argv[1])
operation = sys.argv[2]
manifest = json.loads((profile / "package.json").read_text())
raced_version = "9.9.9" if operation == "install" else "1.0.0"
assert manifest["dependencies"]["@softspark/dsh-codex"] == raced_version, manifest
package = json.loads(
    (profile / "node_modules/@softspark/dsh-codex/package.json").read_text()
)
assert package == {
    "name": "@softspark/dsh-codex",
    "version": raced_version,
    "concurrent_change": True,
}, package
PY
        if [ "$operation" = install ]; then
            [ ! -e "$preset" ]
            [ ! -e "$state" ]
        else
            [ "$(surface_fingerprint "$preset")" = "$before_preset" ]
            [ "$(shasum "$state")" = "$before_state" ]
        fi
    done
}

@test "dsh lifecycle: uninstall refuses version drift after preset relocation" {
    assert_uninstall_post_relocation_package_race version
}

@test "dsh lifecycle: uninstall refuses malformed managed value after preset relocation" {
    assert_uninstall_post_relocation_package_race malformed
}

@test "dsh lifecycle: regular-byte snapshots reject same-inode mutation and mode hybrids" {
    run env HOME="$TEST_HOME" python3 - "$TOOLKIT_DIR" "$TEST_PROJECT" <<'PY'
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = (Path(sys.argv[2]) / "stable-regular-byte-read").resolve()
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

root.mkdir(parents=True)
payload = root / "payload.bin"
original = b"A" * (64 * 1024) + b"B" * (64 * 1024)
payload.write_bytes(original)
payload.chmod(0o600)
metadata = payload.stat(follow_symlinks=False)

real_read = dsh.os.read
mutated = [False]


def mutate_second_half(descriptor, size):
    chunk = real_read(descriptor, size)
    if chunk and not mutated[0]:
        mutated[0] = True
        writer = os.open(payload, os.O_WRONLY)
        try:
            os.pwrite(writer, b"C" * (64 * 1024), 64 * 1024)
            os.fsync(writer)
        finally:
            os.close(writer)
        os.utime(
            payload,
            ns=(metadata.st_atime_ns, metadata.st_mtime_ns),
            follow_symlinks=False,
        )
    return chunk


dsh.os.read = mutate_second_half
try:
    try:
        dsh._read_regular_bytes(payload)
    except dsh.DshLifecycleError:
        pass
    else:
        raise AssertionError("same-inode content mutation was accepted")
finally:
    dsh.os.read = real_read
assert mutated[0], "same-inode read boundary was not reached"

payload.write_bytes(original)
payload.chmod(0o600)
real_open = dsh.os.open
real_supported = dsh._secure_mutation_supported
mode_changed = [False]


def change_mode_before_open(path, flags, mode=0o777, *, dir_fd=None):
    if Path(path).name == payload.name and not mode_changed[0]:
        mode_changed[0] = True
        payload.chmod(0o640)
    if dir_fd is None:
        return real_open(path, flags, mode)
    return real_open(path, flags, mode, dir_fd=dir_fd)


dsh.os.open = change_mode_before_open
dsh._secure_mutation_supported = lambda: True
try:
    try:
        dsh._path_prestate(payload)
    except dsh.DshLifecycleError:
        pass
    else:
        raise AssertionError("mode and byte snapshot from different states was accepted")
finally:
    dsh._secure_mutation_supported = real_supported
    dsh.os.open = real_open
assert mode_changed[0], "mode race boundary was not reached"
PY

    [ "$status" -eq 0 ]
}

@test "dsh lifecycle: file identities reject ctime drift and final path replacement" {
    run env HOME="$TEST_HOME" python3 - "$TOOLKIT_DIR" "$TEST_PROJECT" <<'PY'
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = (Path(sys.argv[2]) / "stable-regular-file-identity").resolve()
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

root.mkdir(parents=True)
payload = root / "payload.bin"
original = b"A" * (64 * 1024) + b"B" * (64 * 1024)
payload.write_bytes(original)
payload.chmod(0o640)
metadata = payload.stat(follow_symlinks=False)

real_read = dsh.os.read
mutated = [False]


def mutate_same_size_and_restore_mtime(descriptor, size):
    chunk = real_read(descriptor, size)
    if chunk and not mutated[0]:
        mutated[0] = True
        writer = os.open(payload, os.O_WRONLY)
        try:
            os.pwrite(writer, b"C" * (64 * 1024), 64 * 1024)
            os.fsync(writer)
        finally:
            os.close(writer)
        os.utime(
            payload,
            ns=(metadata.st_atime_ns, metadata.st_mtime_ns),
            follow_symlinks=False,
        )
    return chunk


dsh.os.read = mutate_same_size_and_restore_mtime
try:
    try:
        dsh._regular_file_identity(payload)
    except dsh.DshLifecycleError:
        pass
    else:
        raise AssertionError("same-size ctime drift was accepted")
finally:
    dsh.os.read = real_read
assert mutated[0], "same-size mutation boundary was not reached"

payload.write_bytes(original)
payload.chmod(0o640)
expected_inode = payload.stat(follow_symlinks=False).st_ino
preserved = root / "payload-managed.bin"
real_fstat = dsh.os.fstat
file_fstats = [0]
replaced = [False]


def replace_path_after_final_descriptor_stat(descriptor):
    metadata = real_fstat(descriptor)
    if metadata.st_ino == expected_inode:
        file_fstats[0] += 1
        if file_fstats[0] == 2 and not replaced[0]:
            replaced[0] = True
            payload.rename(preserved)
            payload.write_bytes(original)
            payload.chmod(0o640)
    return metadata


dsh.os.fstat = replace_path_after_final_descriptor_stat
try:
    try:
        dsh._regular_file_identity(payload)
    except dsh.DshLifecycleError:
        pass
    else:
        raise AssertionError("final pathname replacement was accepted")
finally:
    dsh.os.fstat = real_fstat
assert replaced[0], "final pathname boundary was not reached"
assert payload.read_bytes() == original
assert preserved.read_bytes() == original
assert payload.stat(follow_symlinks=False).st_ino != expected_inode
PY

    [ "$status" -eq 0 ]
}

@test "dsh lifecycle: failed lock initialization cleans exact inode and reports cleanup recovery" {
    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" python3 - \
        "$TOOLKIT_DIR" <<'PY'
import contextlib
import io
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import dsh

dsh_home = Path(os.environ["DSH_HOME"]).resolve()
lock_path = dsh_home / ".ai-toolkit-lifecycle.lock"


def assert_next_acquire_succeeds():
    lock = dsh._acquire_lifecycle_lock(dsh_home)
    dsh._release_lifecycle_lock(lock)
    assert not lock_path.exists(), lock_path


for failure in ("write", "fsync", "interrupt", "close"):
    real_write = dsh.os.write
    real_fsync = dsh.os.fsync
    real_close = dsh.os.close
    injected = [False]
    close_armed = [False]

    def fail_write(descriptor, content):
        if failure in {"write", "interrupt", "close"} and not injected[0]:
            injected[0] = True
            if failure == "interrupt":
                raise KeyboardInterrupt()
            if failure == "close":
                close_armed[0] = True
            raise OSError("injected lock write failure")
        return real_write(descriptor, content)

    def fail_fsync(descriptor):
        if failure == "fsync" and not injected[0]:
            injected[0] = True
            raise OSError("injected lock fsync failure")
        return real_fsync(descriptor)

    def fail_close(descriptor):
        if close_armed[0]:
            close_armed[0] = False
            raise OSError("injected lock close failure")
        return real_close(descriptor)

    dsh.os.write = fail_write
    dsh.os.fsync = fail_fsync
    dsh.os.close = fail_close
    try:
        try:
            dsh._acquire_lifecycle_lock(dsh_home)
        except (dsh.DshLifecycleError, KeyboardInterrupt):
            pass
        else:
            raise AssertionError(f"{failure} lock failure was accepted")
    finally:
        dsh.os.write = real_write
        dsh.os.fsync = real_fsync
        dsh.os.close = real_close
    assert injected[0], failure
    assert_next_acquire_succeeds()

real_write = dsh.os.write
real_cleanup_rename = dsh._secure_rename_noreplace_at


def fail_write(descriptor, content):
    raise OSError("injected lock write failure")


def fail_cleanup_rename(parent, source, destination):
    raise OSError("injected lock cleanup failure")


dsh.os.write = fail_write
dsh._secure_rename_noreplace_at = fail_cleanup_rename
try:
    try:
        dsh._acquire_lifecycle_lock(dsh_home)
    except dsh.DshLifecycleError as error:
        message = str(error)
        assert "Recovery artifact" in message, message
        assert str(lock_path) in message, message
    else:
        raise AssertionError("lock cleanup failure was not reported")
finally:
    dsh.os.write = real_write
    dsh._secure_rename_noreplace_at = real_cleanup_rename

assert lock_path.is_file(), lock_path
assert any(
    path == lock_path
    for path in dsh._lifecycle_lock_recovery_artifacts(dsh_home)
)
real_timeout = dsh.LIFECYCLE_LOCK_TIMEOUT_SECONDS
dsh.LIFECYCLE_LOCK_TIMEOUT_SECONDS = 0
try:
    try:
        dsh._acquire_lifecycle_lock(dsh_home)
    except dsh.DshLifecycleError as error:
        assert "timed out" in str(error), error
    else:
        raise AssertionError("next lifecycle command ignored recovery lock")
finally:
    dsh.LIFECYCLE_LOCK_TIMEOUT_SECONDS = real_timeout
assert lock_path.is_file(), lock_path
captured = io.StringIO()
with contextlib.redirect_stdout(captured):
    doctor_status = dsh._doctor(profile="web")
assert doctor_status != 0
assert f"Lifecycle lock recovery artifact: '{lock_path}'" in captured.getvalue()
PY

    [ "$status" -eq 0 ]
}

@test "dsh lifecycle: install update and uninstall pin one state root through final CAS" {
    fake_bin="$(install_fake_dsh)"
    for operation in install update uninstall; do
        case_root="$TEST_PROJECT/state-root-$operation"
        case_home="$case_root/home"
        dsh_home="$case_root/dsh"
        state_root="$case_root/state"
        displaced="$case_root/state-displaced"
        mkdir -p "$case_home" "$dsh_home" "$state_root"
        command=(env HOME="$case_home" AI_TOOLKIT_HOME="$state_root" \
            DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)
        if [ "$operation" != install ]; then
            run "${command[@]}" install --profile web
            [ "$status" -eq 0 ]
        fi

        run env HOME="$case_home" AI_TOOLKIT_HOME="$state_root" \
            DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
            PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - \
            "$operation" "$state_root" "$displaced" <<'PY'
import os
import shutil
import sys
from pathlib import Path

from install_steps import dsh

operation = sys.argv[1]
state_root = Path(sys.argv[2])
displaced = Path(sys.argv[3])
dsh_home = Path(os.environ["DSH_HOME"]).resolve()
preset = dsh_home / ".agent-presets" / dsh.PRESET_NAME
before_preset = dsh._tree_hash(preset) if preset.exists() else None
before_packages = dsh._profile_package_versions(dsh_home, "web")
before_state = (state_root / "state.json").read_bytes() \
    if (state_root / "state.json").exists() else None
real_capture = dsh._capture_state
injected = [False]


def swap_state_root_after_snapshot(profile, expected_profile):
    snapshot = real_capture(profile, expected_profile)
    if not injected[0]:
        injected[0] = True
        state_root.rename(displaced)
        state_root.mkdir()
        if snapshot.existed:
            shutil.copy2(displaced / "state.json", state_root / "state.json")
    return snapshot


dsh._capture_state = swap_state_root_after_snapshot
arguments = [operation, "--profile", "web"]
if operation == "uninstall":
    arguments.append("--yes")
try:
    status = dsh.main(arguments)
finally:
    dsh._capture_state = real_capture

assert injected[0], f"{operation} state snapshot boundary was not reached"
assert status != 0, f"{operation} accepted a replacement state root"
displaced_state = displaced / "state.json"
replacement_state = state_root / "state.json"
assert (
    displaced_state.read_bytes() if displaced_state.exists() else None
) == before_state
assert (
    replacement_state.read_bytes() if replacement_state.exists() else None
) == before_state
assert not list(displaced.glob(".state*.tmp")), list(displaced.iterdir())
assert not list(state_root.glob(".state*.tmp")), list(state_root.iterdir())
assert not (displaced / ".state.lock").exists()
assert not (state_root / ".state.lock").exists()
assert dsh._profile_package_versions(dsh_home, "web") == before_packages
assert (dsh._tree_hash(preset) if preset.exists() else None) == before_preset
PY

        [ "$status" -eq 0 ]
        [[ "$output" == *"state parent identity changed"* ]]
        [[ "$output" == *"restore ai-toolkit state"* ]]
    done
}
