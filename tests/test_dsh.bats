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

@test "dsh: selector is explicit-only and requires a local install" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" help
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'dsh (explicit project target;'

    run env HOME="$TEST_HOME" DSH_HOME="$TEST_DSH_HOME" \
        python3 "$TOOLKIT_DIR/scripts/install.py" --editors dsh --dry-run
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Editor 'dsh' is project-local and requires --local"
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
    ! echo "$output" | grep -Eq 'Editors:.*(^|, )dsh(,|$)'

    run bash -c "cd '$TEST_PROJECT' && HOME='$TEST_HOME' DSH_HOME='$TEST_DSH_HOME' \
        python3 '$TOOLKIT_DIR/scripts/install.py' --local --profile full --dry-run"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Editors: none'
    ! echo "$output" | grep -Eq 'Editors:.*(^|, )dsh(,|$)'
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
    ! echo "$output" | grep -q 'reference/external/nested/SKILL.md'
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
