#!/usr/bin/env bats
# Global uninstall coverage for output-filter recovery cleanup.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_ROOT="$BATS_TEST_TMPDIR/root"
    TEST_HOME="$TEST_ROOT/home"
    TEST_PROJECT="$TEST_ROOT/project"
    unset CODEX_HOME COPILOT_HOME
    mkdir -p "$TEST_HOME" "$TEST_PROJECT"
}

create_recovery_session() {
    local repository="$1"
    local session_identifier="$2"
    mkdir -p "$repository"
    chmod 700 "$repository"
    python3 - "$TOOLKIT_DIR" "$repository" "$session_identifier" <<'PY'
import hashlib
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
repository = Path(sys.argv[2])
session_identifier = sys.argv[3]
sys.path.insert(0, str(toolkit))

from scripts.tool_output_filter.contracts import FilterTelemetry
from scripts.tool_output_filter.recovery import EphemeralRecoveryStore

with EphemeralRecoveryStore(
    repository,
    session_identifier=session_identifier,
    random_handle=lambda: "a" * 32,
) as recovery:
    recovery.save({"stdout": "remove me"})
    recovery.save_failure_count(2)
    recovery.record(
        FilterTelemetry(
            profile_id="repeat-lines",
            profile_version=1,
            input_bytes=100,
            output_bytes=20,
            input_lines=10,
            output_lines=2,
            outcome="observed",
        )
    )

session_key = hashlib.sha256(session_identifier.encode()).hexdigest()[:32]
print(repository / "output-filter" / session_key)
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
