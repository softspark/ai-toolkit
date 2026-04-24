#!/usr/bin/env bats
# Windows support contract tests.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

@test "detect_os recognizes Windows package managers" {
    run python3 - <<PY
import platform
import shutil
import sys

sys.path.insert(0, "$TOOLKIT_DIR/scripts")
import _common

platform.system = lambda: "Windows"
shutil.which = lambda name: "C:/Windows/System32/winget.exe" if name == "winget" else None

info = _common.detect_os()
assert info["os"] == "Windows", info
assert info["pkg_manager"] == "winget", info
assert info["install_cmd"] == "winget install", info
print("ok")
PY
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "check_deps exposes Windows install hints" {
    run python3 - <<PY
import platform
import shutil
import sys

sys.path.insert(0, "$TOOLKIT_DIR/scripts")
import _common
import check_deps

check_deps.detect_os = lambda: {
    "os": "Windows",
    "distro": "test",
    "pkg_manager": "winget",
    "install_cmd": "winget install",
}
check_deps.shutil.which = lambda _name: None
check_deps.get_version = lambda _binary: ""

results = check_deps.check_deps(verbose=False)
cmds = "\\n".join(results["missing_cmds"])
assert "winget install Python.Python.3" in cmds, cmds
assert "winget install Git.Git" in cmds, cmds
assert "winget install OpenJS.NodeJS" in cmds, cmds
print("ok")
PY
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}
