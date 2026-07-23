#!/usr/bin/env bats
# Cross-runtime uninstall coverage for Codex and GitHub Copilot.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_ROOT="$BATS_TEST_TMPDIR/root"
    TEST_HOME="$TEST_ROOT/home"
    TEST_PROJECT="$TEST_ROOT/project"
    mkdir -p "$TEST_HOME" "$TEST_PROJECT"
}

@test "uninstall --local removes generated Codex and Copilot surfaces but preserves user data" {
    mkdir -p "$TEST_PROJECT/.claude" "$TEST_PROJECT/.github"

    python3 "$TOOLKIT_DIR/scripts/generate_codex.py" > "$TEST_PROJECT/AGENTS.md"
    python3 "$TOOLKIT_DIR/scripts/generate_codex_agents.py" "$TEST_PROJECT" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_codex_skills.py" --enable "$TEST_PROJECT" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$TEST_PROJECT" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" > \
        "$TEST_PROJECT/.github/copilot-instructions.md"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot.py" "$TEST_PROJECT" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/generate_copilot_hooks.py" "$TEST_PROJECT" >/dev/null

    cat >> "$TEST_PROJECT/AGENTS.md" <<'EOF'

# User instructions

<!-- TOOLKIT:plugin-memory-pack-rules START -->
plugin-owned rule
<!-- TOOLKIT:plugin-memory-pack-rules END -->
EOF
    cat > "$TEST_PROJECT/.codex/agents/user-agent.toml" <<'EOF'
name = "user-agent"
description = "Keep me"
developer_instructions = "User owned"
EOF
    mkdir -p "$TEST_PROJECT/.agents/skills/user-skill"
    printf '%s\n' '---' 'name: user-skill' 'description: Keep me' '---' > \
        "$TEST_PROJECT/.agents/skills/user-skill/SKILL.md"
    printf '%s\n' '# user Codex hook' > "$TEST_PROJECT/.codex/hooks/user-hook.sh"
    mkdir -p "$TEST_PROJECT/.github/instructions" "$TEST_PROJECT/.github/agents" \
        "$TEST_PROJECT/.github/prompts" "$TEST_PROJECT/.github/skills/user-skill"
    printf '%s\n' 'user instruction' > \
        "$TEST_PROJECT/.github/instructions/user.instructions.md"
    printf '%s\n' 'user agent' > "$TEST_PROJECT/.github/agents/user.agent.md"
    printf '%s\n' 'user prompt' > "$TEST_PROJECT/.github/prompts/user.prompt.md"
    printf '%s\n' 'user skill' > "$TEST_PROJECT/.github/skills/user-skill/SKILL.md"
    printf '%s\n' 'keep user addition' > \
        "$TEST_PROJECT/.github/skills/ai-toolkit-build/user-added.txt"
    printf '%s\n' '# user Copilot hook' > \
        "$TEST_PROJECT/.github/hooks/ai-toolkit/user-hook.py"

    python3 - "$TEST_PROJECT" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
codex = root / ".codex" / "hooks.json"
data = json.loads(codex.read_text())
data["hooks"].setdefault("Stop", []).append({
    "hooks": [
        {"type": "command", "command": "echo user"},
        {
            "type": "command",
            "command": "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack echo plugin",
        },
    ]
})
codex.write_text(json.dumps(data, indent=2) + "\n")

copilot = root / ".github" / "hooks" / "ai-toolkit.json"
data = json.loads(copilot.read_text())
data["hooks"].setdefault("sessionEnd", []).append({
    "type": "command",
    "bash": "echo user",
})
copilot.write_text(json.dumps(data, indent=2) + "\n")
PY

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --local --yes --target "$TEST_PROJECT"
    [ "$status" -eq 0 ]

    grep -q '^# User instructions$' "$TEST_PROJECT/AGENTS.md"
    grep -q 'plugin-owned rule' "$TEST_PROJECT/AGENTS.md"
    ! grep -q '<!-- TOOLKIT:ai-toolkit START -->' "$TEST_PROJECT/AGENTS.md"
    [ -f "$TEST_PROJECT/.codex/agents/user-agent.toml" ]
    ! grep -R -l -m1 '^# ai-toolkit-managed: codex-agent$' \
        "$TEST_PROJECT/.codex/agents" >/dev/null 2>&1
    grep -q 'echo user' "$TEST_PROJECT/.codex/hooks.json"
    grep -q 'ai-toolkit-plugin-memory-pack' "$TEST_PROJECT/.codex/hooks.json"
    ! grep -q 'AI_TOOLKIT_HOOK_OWNER=ai-toolkit ' "$TEST_PROJECT/.codex/hooks.json"
    [ -f "$TEST_PROJECT/.codex/hooks/user-hook.sh" ]
    ! grep -R -l -m1 '^# ai-toolkit-managed: codex-hook-script$' \
        "$TEST_PROJECT/.codex/hooks" >/dev/null 2>&1
    [ -f "$TEST_PROJECT/.agents/skills/user-skill/SKILL.md" ]
    [ "$(find "$TEST_PROJECT/.agents/skills" -mindepth 1 -maxdepth 1 | wc -l | xargs)" -eq 1 ]

    [ -f "$TEST_PROJECT/.github/instructions/user.instructions.md" ]
    [ -f "$TEST_PROJECT/.github/agents/user.agent.md" ]
    [ -f "$TEST_PROJECT/.github/prompts/user.prompt.md" ]
    [ -f "$TEST_PROJECT/.github/skills/user-skill/SKILL.md" ]
    [ -f "$TEST_PROJECT/.github/skills/ai-toolkit-build/user-added.txt" ]
    [ ! -f "$TEST_PROJECT/.github/skills/ai-toolkit-build/SKILL.md" ]
    ! grep -R -l -m1 '<!-- ai-toolkit-managed: github-copilot -->' \
        "$TEST_PROJECT/.github" >/dev/null 2>&1
    grep -q 'echo user' "$TEST_PROJECT/.github/hooks/ai-toolkit.json"
    ! grep -q 'AI_TOOLKIT_HOOK_OWNER' "$TEST_PROJECT/.github/hooks/ai-toolkit.json"
    [ -f "$TEST_PROJECT/.github/hooks/ai-toolkit/user-hook.py" ]
    [ ! -f "$TEST_PROJECT/.github/hooks/ai-toolkit/copilot_hook.py" ]
}

@test "uninstall --local removes the managed project output-filter policy only" {
    mkdir -p "$TEST_PROJECT/.claude"
    printf '{"mode":"safe"}\n' \
        > "$TEST_PROJECT/.claude/ai-toolkit-output-filter.json"
    printf 'ai-toolkit-output-filter-policy-v1\n' \
        > "$TEST_PROJECT/.claude/.ai-toolkit-output-filter.owner"

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --local --yes --target "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [ ! -f "$TEST_PROJECT/.claude/ai-toolkit-output-filter.json" ]
    [ ! -f "$TEST_PROJECT/.claude/.ai-toolkit-output-filter.owner" ]

    # A user-owned policy (foreign marker) must survive.
    mkdir -p "$TEST_PROJECT/.claude"
    printf '{"mode":"safe"}\n' \
        > "$TEST_PROJECT/.claude/ai-toolkit-output-filter.json"
    printf 'user-owned-marker\n' \
        > "$TEST_PROJECT/.claude/.ai-toolkit-output-filter.owner"

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --local --yes --target "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [ -f "$TEST_PROJECT/.claude/ai-toolkit-output-filter.json" ]
    [ -f "$TEST_PROJECT/.claude/.ai-toolkit-output-filter.owner" ]
}

@test "uninstall --global honors CODEX_HOME and COPILOT_HOME" {
    local codex_home="$TEST_ROOT/custom-codex"
    local copilot_home="$TEST_ROOT/custom-copilot"
    mkdir -p "$codex_home/agents" "$codex_home/ai-toolkit-hooks" \
        "$copilot_home/instructions" "$copilot_home/agents" \
        "$copilot_home/prompts" "$copilot_home/skills/ai-toolkit-demo" \
        "$copilot_home/hooks/ai-toolkit" "$TEST_HOME/.agents/skills"

    cat > "$codex_home/AGENTS.md" <<'EOF'
user prefix
<!-- TOOLKIT:ai-toolkit START -->
managed core
<!-- TOOLKIT:ai-toolkit END -->
EOF
    printf '%s\n' '# ai-toolkit-managed: codex-agent' > \
        "$codex_home/agents/ai-toolkit-demo.toml"
    printf '%s\n' '# ai-toolkit-managed: codex-hook-script' > \
        "$codex_home/ai-toolkit-hooks/core.sh"
    cat > "$codex_home/hooks.json" <<'EOF'
{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"AI_TOOLKIT_HOOK_OWNER=ai-toolkit true"}]}]}}
EOF
    ln -s "$TOOLKIT_DIR/app/skills/api-patterns" \
        "$TEST_HOME/.agents/skills/api-patterns"

    cat > "$copilot_home/copilot-instructions.md" <<'EOF'
user prefix
<!-- TOOLKIT:ai-toolkit START -->
managed core
<!-- TOOLKIT:ai-toolkit END -->
EOF
    printf '%s\n' '<!-- ai-toolkit-managed: github-copilot -->' > \
        "$copilot_home/instructions/ai-toolkit-demo.instructions.md"
    printf '%s\n' '<!-- ai-toolkit-managed: github-copilot -->' > \
        "$copilot_home/agents/ai-toolkit-demo.agent.md"
    printf '%s\n' '<!-- ai-toolkit-managed: github-copilot -->' > \
        "$copilot_home/skills/ai-toolkit-demo/SKILL.md"
    printf '%s\n' '["SKILL.md", ".ai-toolkit-managed-files"]' > \
        "$copilot_home/skills/ai-toolkit-demo/.ai-toolkit-managed-files"
    printf '%s\n' '# ai-toolkit-managed: github-copilot-hook' > \
        "$copilot_home/hooks/ai-toolkit/copilot_hook.py"
    cat > "$copilot_home/hooks/ai-toolkit.json" <<'EOF'
{"version":1,"hooks":{"sessionStart":[{"type":"command","bash":"true","env":{"AI_TOOLKIT_HOOK_OWNER":"ai-toolkit"}}]}}
EOF

    HOME="$TEST_HOME" CODEX_HOME="$codex_home" COPILOT_HOME="$copilot_home" \
        run python3 "$TOOLKIT_DIR/scripts/uninstall.py" --global --yes
    [ "$status" -eq 0 ]

    grep -q '^user prefix$' "$codex_home/AGENTS.md"
    ! grep -q '<!-- TOOLKIT:ai-toolkit START -->' "$codex_home/AGENTS.md"
    [ ! -f "$codex_home/agents/ai-toolkit-demo.toml" ]
    [ ! -f "$codex_home/hooks.json" ]
    [ ! -f "$codex_home/ai-toolkit-hooks/core.sh" ]
    [ ! -L "$TEST_HOME/.agents/skills/api-patterns" ]
    grep -q '^user prefix$' "$copilot_home/copilot-instructions.md"
    [ ! -f "$copilot_home/instructions/ai-toolkit-demo.instructions.md" ]
    [ ! -f "$copilot_home/agents/ai-toolkit-demo.agent.md" ]
    [ ! -e "$copilot_home/skills/ai-toolkit-demo" ]
    [ ! -f "$copilot_home/hooks/ai-toolkit.json" ]
    [ ! -f "$copilot_home/hooks/ai-toolkit/copilot_hook.py" ]
}

@test "unsafe recovery symlink is rejected before editor mutations" {
    local managed_agent="$TEST_HOME/.codex/agents/ai-toolkit-managed.toml"
    local linked_copy="$TEST_HOME/managed-agent-hardlink"
    local output_root="$TEST_HOME/.softspark/ai-toolkit/sessions/repo/output-filter"
    local session_root="$output_root/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    local owned_name="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.json"
    local external="$TEST_ROOT/external-recovery.json"

    mkdir -p "$TEST_HOME/.codex/agents" "$session_root"
    chmod 700 "$output_root" "$session_root"
    printf '%s\n' '# ai-toolkit-managed: codex-agent' > "$managed_agent"
    ln "$managed_agent" "$linked_copy"
    printf '%s\n' 'external user data' > "$external"
    ln -s "$external" "$session_root/$owned_name"

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --global --yes
    [ "$status" -ne 0 ]

    [ -f "$managed_agent" ]
    [ -L "$session_root/$owned_name" ]
    python3 - "$managed_agent" "$linked_copy" <<'PY'
import os
import sys

assert os.path.samefile(sys.argv[1], sys.argv[2]), (
    "unsafe recovery was detected only after editor mutations"
)
PY
    grep -q '^external user data$' "$external"
}

@test "uninstall refuses symlinked editor roots before modifying sibling surfaces" {
    local external="$TEST_ROOT/external-codex"
    mkdir -p "$external" "$TEST_PROJECT/.github/instructions"
    printf '%s\n' '# ai-toolkit-managed: codex-agent' > "$external/managed.toml"
    ln -s "$external" "$TEST_PROJECT/.codex"
    printf '%s\n' '<!-- ai-toolkit-managed: github-copilot -->' > \
        "$TEST_PROJECT/.github/instructions/ai-toolkit-demo.instructions.md"

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --local --yes --target "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [ -f "$external/managed.toml" ]
    [ -f "$TEST_PROJECT/.github/instructions/ai-toolkit-demo.instructions.md" ]
}

@test "uninstall never follows symlinked parents from a Copilot skill manifest" {
    local skill="$TEST_PROJECT/.github/skills/ai-toolkit-demo"
    local external="$TEST_ROOT/external-skill-assets"
    mkdir -p "$skill" "$external"
    printf '%s\n' '<!-- ai-toolkit-managed: github-copilot -->' > \
        "$skill/SKILL.md"
    printf '%s\n' 'external user data' > "$external/managed.txt"
    ln -s "$external" "$skill/nested"
    cat > "$skill/.ai-toolkit-managed-files" <<'EOF'
["SKILL.md", "nested/managed.txt", ".ai-toolkit-managed-files"]
EOF

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --local --yes --target "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [ -f "$external/managed.txt" ]
    grep -q '^external user data$' "$external/managed.txt"
    [ -L "$skill/nested" ]
}

@test "uninstall accepts a pure editor project and is idempotent" {
    mkdir -p "$TEST_PROJECT/.codex/agents"
    printf '%s\n' '# ai-toolkit-managed: codex-agent' > \
        "$TEST_PROJECT/.codex/agents/ai-toolkit-demo.toml"

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --local --yes --target "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [ ! -f "$TEST_PROJECT/.codex/agents/ai-toolkit-demo.toml" ]

    HOME="$TEST_HOME" run python3 "$TOOLKIT_DIR/scripts/uninstall.py" \
        --local --yes --target "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Nothing to remove"* ]]
}

@test "uninstall help documents local global and target scopes" {
    run python3 "$TOOLKIT_DIR/scripts/uninstall.py" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--local"* ]]
    [[ "$output" == *"--global"* ]]
    [[ "$output" == *"--target"* ]]
    [[ "$output" == *"CODEX_HOME"* ]]
    [[ "$output" == *"COPILOT_HOME"* ]]
}

@test "uninstall script remains directly executable" {
    [ -x "$TOOLKIT_DIR/scripts/uninstall.py" ]
    run "$TOOLKIT_DIR/scripts/uninstall.py" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"usage:"* ]]
}

@test "late Copilot failure rolls back every runtime byte-for-byte" {
    mkdir -p "$TEST_PROJECT/.claude" "$TEST_PROJECT/.codex/agents" \
        "$TEST_PROJECT/.github/instructions"
    cat > "$TEST_PROJECT/.claude/constitution.md" <<'EOF'
user claude
<!-- TOOLKIT:ai-toolkit START -->
managed claude
<!-- TOOLKIT:ai-toolkit END -->
EOF
    cat > "$TEST_PROJECT/AGENTS.md" <<'EOF'
user codex
<!-- TOOLKIT:ai-toolkit START -->
managed codex
<!-- TOOLKIT:ai-toolkit END -->
EOF
    printf '%s\n' '# ai-toolkit-managed: codex-agent' 'name = "managed"' > \
        "$TEST_PROJECT/.codex/agents/ai-toolkit-managed.toml"
    printf '%s\n' '<!-- ai-toolkit-managed: github-copilot -->' 'managed copilot' > \
        "$TEST_PROJECT/.github/instructions/ai-toolkit-managed.instructions.md"
    chmod 640 "$TEST_PROJECT/.claude/constitution.md"
    chmod 600 "$TEST_PROJECT/.codex/agents/ai-toolkit-managed.toml"

    python3 - "$TOOLKIT_DIR" "$TEST_PROJECT" <<'PY'
import base64
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
spec = importlib.util.spec_from_file_location("uninstall_under_test", toolkit / "scripts" / "uninstall.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

def snapshot(path):
    result = {}
    for item in [path, *sorted(path.rglob("*"))]:
        relative = "." if item == path else item.relative_to(path).as_posix()
        metadata = os.lstat(item)
        entry = {"mode": stat.S_IMODE(metadata.st_mode)}
        if stat.S_ISLNK(metadata.st_mode):
            entry.update(type="symlink", target=os.readlink(item))
        elif stat.S_ISDIR(metadata.st_mode):
            entry.update(type="directory")
        elif stat.S_ISREG(metadata.st_mode):
            entry.update(type="file", data=base64.b64encode(item.read_bytes()).decode())
        else:
            entry.update(type="other")
        result[relative] = entry
    return json.dumps(result, sort_keys=True)

before = snapshot(root)
original = module._remove_copilot

def fail_after_copilot(*args, **kwargs):
    original(*args, **kwargs)
    raise OSError("injected late Copilot failure")

module._remove_copilot = fail_after_copilot
try:
    module.main(["--local", "--yes", "--target", str(root)])
except SystemExit as error:
    assert error.code == 1, error.code
else:
    raise AssertionError("uninstall unexpectedly succeeded")
after = snapshot(root)
assert after == before, "rollback did not restore the complete tree"
PY
}

@test "unlink revalidates a Copilot parent symlink immediately before mutation" {
    local instructions="$TEST_PROJECT/.github/instructions"
    local external="$TEST_ROOT/external-instructions"
    mkdir -p "$instructions" "$external"
    printf '%s\n' '<!-- ai-toolkit-managed: github-copilot -->' > \
        "$instructions/ai-toolkit-managed.instructions.md"
    printf '%s\n' 'external user data' > \
        "$external/ai-toolkit-managed.instructions.md"

    python3 - "$TOOLKIT_DIR" "$TEST_PROJECT" "$external" <<'PY'
import importlib.util
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = Path(sys.argv[2])
external = Path(sys.argv[3])
sys.path.insert(0, str(toolkit / "scripts"))
spec = importlib.util.spec_from_file_location("uninstall_toctou_test", toolkit / "scripts" / "uninstall.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

target = root / ".github" / "instructions" / "ai-toolkit-managed.instructions.md"
parent = target.parent
moved = parent.with_name("instructions-before-swap")
real_assert = module._assert_mutation_parent
swapped = False

def swap_parent_then_validate(path, *args):
    global swapped
    if path == target and not swapped:
        swapped = True
        os.rename(parent, moved)
        os.symlink(external, parent, target_is_directory=True)
        try:
            return real_assert(path, *args)
        finally:
            os.unlink(parent)
            os.rename(moved, parent)
    return real_assert(path, *args)

module._assert_mutation_parent = swap_parent_then_validate
try:
    module.main(["--local", "--yes", "--target", str(root)])
except SystemExit as error:
    assert error.code == 1, error.code
else:
    raise AssertionError("uninstall ignored the parent symlink swap")
assert swapped, "the mutation guard was not reached"
assert target.is_file(), "managed file was not rolled back"
external_file = external / target.name
assert external_file.read_text() == "external user data\n"
PY
}

@test "unlink rejects a symlinked Copilot ancestor below its trusted boundary" {
    local instructions="$TEST_PROJECT/.github/instructions"
    local external_github="$TEST_ROOT/external-github"
    mkdir -p "$instructions" "$external_github/instructions"
    printf '%s\n' '<!-- ai-toolkit-managed: github-copilot -->' > \
        "$instructions/ai-toolkit-managed.instructions.md"
    printf '%s\n' 'external user data' > \
        "$external_github/instructions/ai-toolkit-managed.instructions.md"

    python3 - "$TOOLKIT_DIR" "$TEST_PROJECT" "$external_github" <<'PY'
import importlib.util
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = Path(sys.argv[2])
external_github = Path(sys.argv[3])
sys.path.insert(0, str(toolkit / "scripts"))
spec = importlib.util.spec_from_file_location(
    "uninstall_nested_toctou_test",
    toolkit / "scripts" / "uninstall.py",
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

github = root / ".github"
target = github / "instructions" / "ai-toolkit-managed.instructions.md"
moved = github.with_name(".github-before-swap")
real_assert = module._assert_mutation_parent
swapped = False

def restore_github():
    if github.is_symlink():
        os.unlink(github)
        os.rename(moved, github)

def swap_ancestor_then_validate(path, *args):
    global swapped
    if path == target and not swapped:
        swapped = True
        os.rename(github, moved)
        os.symlink(external_github, github, target_is_directory=True)
        try:
            return real_assert(path, *args)
        except Exception:
            restore_github()
            raise
    return real_assert(path, *args)

module._assert_mutation_parent = swap_ancestor_then_validate
try:
    try:
        module.main(["--local", "--yes", "--target", str(root)])
    except SystemExit as error:
        assert error.code == 1, error.code
    else:
        raise AssertionError("uninstall ignored the nested ancestor symlink swap")
finally:
    restore_github()

assert swapped, "the mutation guard was not reached"
assert target.is_file(), "managed file was not rolled back"
external_file = external_github / "instructions" / target.name
assert external_file.read_text() == "external user data\n"
PY
}

@test "uninstall fails closed without secure directory traversal primitives" {
    local instructions="$TEST_PROJECT/.github/instructions"
    local external_github="$TEST_ROOT/external-github"
    mkdir -p "$instructions" "$external_github/instructions" "$TEST_ROOT/empty"
    printf '%s\n' '<!-- ai-toolkit-managed: github-copilot -->' > \
        "$instructions/ai-toolkit-managed.instructions.md"
    printf '%s\n' 'local user data' > "$TEST_PROJECT/user.txt"
    printf '%s\n' 'external user data' > \
        "$external_github/instructions/ai-toolkit-managed.instructions.md"

    python3 - "$TOOLKIT_DIR" "$TEST_ROOT" "$TEST_PROJECT" <<'PY'
import base64
import contextlib
import importlib.util
import io
import json
import os
import stat
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
snapshot_root = Path(sys.argv[2])
root = Path(sys.argv[3])
sys.path.insert(0, str(toolkit / "scripts"))
spec = importlib.util.spec_from_file_location(
    "uninstall_forced_fallback_test",
    toolkit / "scripts" / "uninstall.py",
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

def snapshot(path):
    result = {}
    for item in [path, *sorted(path.rglob("*"))]:
        relative = "." if item == path else item.relative_to(path).as_posix()
        metadata = os.lstat(item)
        entry = {"mode": stat.S_IMODE(metadata.st_mode)}
        if stat.S_ISLNK(metadata.st_mode):
            entry.update(type="symlink", target=os.readlink(item))
        elif stat.S_ISDIR(metadata.st_mode):
            entry.update(type="directory")
        elif stat.S_ISREG(metadata.st_mode):
            entry.update(type="file", data=base64.b64encode(item.read_bytes()).decode())
        else:
            entry.update(type="other")
        result[relative] = entry
    return json.dumps(result, sort_keys=True)

before = snapshot(snapshot_root)
module._SECURE_DIR_FD = False
stderr = io.StringIO()
exit_code = None
with contextlib.redirect_stderr(stderr):
    try:
        module.main(["--local", "--yes", "--target", str(root)])
    except SystemExit as error:
        exit_code = error.code

managed_file = root / ".github" / "instructions" / "ai-toolkit-managed.instructions.md"
try:
    module._safe_unlink(managed_file, root)
except RuntimeError as error:
    assert "No files were changed" in str(error), str(error)
else:
    raise AssertionError("mutation helper used the unsafe fallback")

stdout = io.StringIO()
with contextlib.redirect_stdout(stdout):
    module.main(["--local", "--yes", "--target", str(snapshot_root / "empty")])
assert "Nothing to remove" in stdout.getvalue(), stdout.getvalue()

help_stdout = io.StringIO()
with contextlib.redirect_stdout(help_stdout):
    try:
        module.main(["--help"])
    except SystemExit as error:
        assert error.code == 0, error.code
assert "--local" in help_stdout.getvalue(), help_stdout.getvalue()

after = snapshot(snapshot_root)
assert exit_code == 1, exit_code
assert before == after, "unsupported-platform uninstall changed the filesystem"
assert "No files were changed" in stderr.getvalue(), stderr.getvalue()
PY
}
