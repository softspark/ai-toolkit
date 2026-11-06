#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# opencode generator contract tests.
# Consolidates assertions on all six opencode generators: AGENTS.md,
# .opencode/agents/, .opencode/commands/, .opencode/skills/,
# .opencode/plugins/, and opencode.json MCP merge. Cross-checks upstream docs
# (packages/web/src/content/docs/*).
#
# Run with: bats tests/test_opencode.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export OC_DIR; OC_DIR="$(mktemp -d)"
    export OC_LOG_DIR; OC_LOG_DIR="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_opencode.py" > "$OC_LOG_DIR/agents-md" 2>/dev/null
    echo $? > "$OC_LOG_DIR/agents-md.status"
    python3 "$TOOLKIT_DIR/scripts/generate_opencode_agents.py" "$OC_DIR" > "$OC_LOG_DIR/agents.log" 2>/dev/null
    echo $? > "$OC_LOG_DIR/agents.status"
    python3 "$TOOLKIT_DIR/scripts/generate_opencode_commands.py" "$OC_DIR" > "$OC_LOG_DIR/commands.log" 2>/dev/null
    echo $? > "$OC_LOG_DIR/commands.status"
    python3 "$TOOLKIT_DIR/scripts/generate_opencode_plugin.py" "$OC_DIR" > "$OC_LOG_DIR/plugin.log" 2>/dev/null
    echo $? > "$OC_LOG_DIR/plugin.status"
    python3 "$TOOLKIT_DIR/scripts/generate_opencode_json.py" "$OC_DIR" > "$OC_LOG_DIR/json.log" 2>/dev/null
    echo $? > "$OC_LOG_DIR/json.status"
}

teardown_file() {
    rm -rf "$OC_DIR" "$OC_LOG_DIR"
}

# ── AGENTS.md (generate_opencode.py) ────────────────────────────────────────

@test "opencode: AGENTS.md generator exits 0" {
    [ "$(cat "$OC_LOG_DIR/agents-md.status")" = "0" ]
}

@test "opencode: AGENTS.md mentions the rules-file convention" {
    # opencode docs/rules.mdx documents AGENTS.md as the project rules file.
    grep -qi 'opencode' "$OC_LOG_DIR/agents-md"
}

# ── .opencode/agents/ (generate_opencode_agents.py) ─────────────────────────

@test "opencode: agents generator emits ai-toolkit-* prefix (clean-uninstall contract)" {
    count=$(ls "$OC_DIR/.opencode/agents"/ai-toolkit-*.md 2>/dev/null | wc -l | xargs)
    [ "$count" -ge 10 ]
}

@test "opencode: agent frontmatter sets mode=subagent" {
    # Upstream: packages/web/src/content/docs/agents.mdx distinguishes
    # `primary` vs `subagent`. Our generated agents are always subagents.
    for f in "$OC_DIR"/.opencode/agents/ai-toolkit-*.md; do
        grep -q '^mode: subagent$' "$f" || { echo "Missing mode: subagent in $f"; return 1; }
    done
}

@test "opencode: agent frontmatter omits invalid fields" {
    # Regression: earlier versions emitted `# source model hint ...`
    # and bare `model:` without `provider/model-id` which opencode rejects.
    ! grep -qrE '^model: (opus|sonnet|haiku)' "$OC_DIR/.opencode/agents/"
    ! grep -qr 'source model hint' "$OC_DIR/.opencode/agents/"
}

# ── .opencode/commands/ (generate_opencode_commands.py) ─────────────────────

@test "opencode: skills generator copies complete skill directories without commands" {
    tmp="$(mktemp -d)"

    run python3 "$TOOLKIT_DIR/scripts/generate_opencode_skills.py" "$tmp"

    [ "$status" -eq 0 ]
    [ -f "$tmp/.opencode/skills/clean-code/SKILL.md" ]
    [ -f "$tmp/.opencode/skills/clean-code/reference/python.md" ]
    [ ! -d "$tmp/.opencode/commands" ]
    rm -rf "$tmp"
}

@test "opencode: skills map invocation metadata and remove Claude-only runtime fields" {
    tmp="$(mktemp -d)"
    source="$tmp/source"
    mkdir -p "$source/sample/reference"
    cat > "$source/sample/SKILL.md" <<'EOF'
---
name: sample
description: "Portable sample"
license: Apache-2.0
compatibility: Requires Python 3
metadata:
  owner: softspark
user-invocable: false
disable-model-invocation: true
effort: high
context: fork
agent: orchestrator
allowed-tools: Read, Agent
---
# Sample

Use `${CLAUDE_SKILL_DIR}/reference/guide.md`, then call spawn_agent.
EOF
    echo 'guide' > "$source/sample/reference/guide.md"

    run python3 - "$TOOLKIT_DIR" "$tmp/out" "$source" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import generate
generate(Path(sys.argv[2]), source_root=Path(sys.argv[3]))
PY

    [ "$status" -eq 0 ]
    skill="$tmp/out/.opencode/skills/sample/SKILL.md"
    grep -q '^name: sample$' "$skill"
    grep -q '^description: "Portable sample"$' "$skill"
    grep -q '^license: Apache-2.0$' "$skill"
    grep -q '^compatibility: Requires Python 3$' "$skill"
    grep -q '^slash: false$' "$skill"
    grep -q '^  owner: softspark$' "$skill"
    grep -q '^  opencode/autoinvoke: false$' "$skill"
    ! grep -qE '^(user-invocable|disable-model-invocation|effort|context|agent|allowed-tools):' "$skill"
    ! grep -qE 'CLAUDE_SKILL_DIR|spawn_agent' "$skill"
    [ -f "$tmp/out/.opencode/skills/sample/reference/guide.md" ]
    rm -rf "$tmp"
}

@test "opencode: skills reject source symlinks before mutating destination" {
    tmp="$(mktemp -d)"
    source="$tmp/source"
    mkdir -p "$source/alpha" "$source/beta/reference" "$tmp/out"
    cat > "$source/alpha/SKILL.md" <<'EOF'
---
name: alpha
description: Alpha
---
Alpha
EOF
    cat > "$source/beta/SKILL.md" <<'EOF'
---
name: beta
description: Beta
---
Beta
EOF
    echo outside > "$tmp/outside.md"
    ln -s "$tmp/outside.md" "$source/beta/reference/unsafe.md"
    echo keep > "$tmp/out/sentinel"

    run python3 - "$TOOLKIT_DIR" "$tmp/out" "$source" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import generate
generate(Path(sys.argv[2]), source_root=Path(sys.argv[3]))
PY

    [ "$status" -ne 0 ]
    [ "$(cat "$tmp/out/sentinel")" = keep ]
    [ ! -e "$tmp/out/.opencode" ]

    rm -rf "$source/invalid"
    mkdir -p "$source/description"
    long_description="$(printf 'x%.0s' {1..1025})"
    cat > "$source/description/SKILL.md" <<EOF
---
name: description
description: $long_description
---
Invalid
EOF
    run python3 - "$TOOLKIT_DIR" "$tmp/out" "$source" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import generate
generate(Path(sys.argv[2]), source_root=Path(sys.argv[3]))
PY
    [ "$status" -ne 0 ]
    [ ! -e "$tmp/out/.opencode" ]
    rm -rf "$tmp"
}

@test "opencode: skills reject names and descriptions beyond stable limits" {
    tmp="$(mktemp -d)"
    source="$tmp/source"
    mkdir -p "$source/invalid" "$tmp/out"
    long_name="$(printf 'a%.0s' {1..65})"
    cat > "$source/invalid/SKILL.md" <<EOF
---
name: $long_name
description: Invalid long name
---
Invalid
EOF
    echo keep > "$tmp/out/sentinel"

    run python3 - "$TOOLKIT_DIR" "$tmp/out" "$source" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import generate
generate(Path(sys.argv[2]), source_root=Path(sys.argv[3]))
PY

    [ "$status" -ne 0 ]
    [ "$(cat "$tmp/out/sentinel")" = keep ]
    [ ! -e "$tmp/out/.opencode" ]
    rm -rf "$tmp"
}

@test "opencode: skills remove stale managed output and preserve user skills" {
    tmp="$(mktemp -d)"
    source="$tmp/source"
    out="$tmp/out"
    mkdir -p "$source/alpha" "$out/.opencode/skills/custom"
    cat > "$source/alpha/SKILL.md" <<'EOF'
---
name: alpha
description: Alpha
---
Alpha
EOF
    cat > "$out/.opencode/skills/custom/SKILL.md" <<'EOF'
---
name: custom
description: User owned
---
keep me
EOF

    python3 - "$TOOLKIT_DIR" "$out" "$source" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import generate
generate(Path(sys.argv[2]), source_root=Path(sys.argv[3]))
PY
    rm -rf "$source/alpha"
    mkdir -p "$source/beta"
    cat > "$source/beta/SKILL.md" <<'EOF'
---
name: beta
description: Beta
---
Beta
EOF

    run python3 - "$TOOLKIT_DIR" "$out" "$source" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import generate
generate(Path(sys.argv[2]), source_root=Path(sys.argv[3]))
PY

    [ "$status" -eq 0 ]
    [ ! -e "$out/.opencode/skills/alpha" ]
    [ -f "$out/.opencode/skills/beta/SKILL.md" ]
    grep -q 'keep me' "$out/.opencode/skills/custom/SKILL.md"
    rm -rf "$tmp"
}

@test "opencode: skills preserve a user-owned destination collision" {
    tmp="$(mktemp -d)"
    source="$tmp/source"
    out="$tmp/out"
    mkdir -p "$source/sample" "$out/.opencode/skills/sample"
    cat > "$source/sample/SKILL.md" <<'EOF'
---
name: sample
description: Toolkit sample
---
toolkit body
EOF
    cat > "$out/.opencode/skills/sample/SKILL.md" <<'EOF'
---
name: sample
description: User sample
---
user body
EOF
    echo private > "$out/.opencode/skills/sample/private.txt"

    run python3 - "$TOOLKIT_DIR" "$out" "$source" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import generate
print(generate(Path(sys.argv[2]), source_root=Path(sys.argv[3])))
PY

    [ "$status" -eq 0 ]
    grep -q 'user body' "$out/.opencode/skills/sample/SKILL.md"
    ! grep -q 'toolkit body' "$out/.opencode/skills/sample/SKILL.md"
    [ "$(cat "$out/.opencode/skills/sample/private.txt")" = private ]
    [[ "$output" == *"(0, 0, 1)"* ]]
    rm -rf "$tmp"
}

@test "opencode: skills refresh managed resources while retaining user extras" {
    tmp="$(mktemp -d)"
    source="$tmp/source"
    out="$tmp/out"
    mkdir -p "$source/sample/reference" "$source/sample/legacy"
    cat > "$source/sample/SKILL.md" <<'EOF'
---
name: sample
description: Sample
---
Sample
EOF
    echo old > "$source/sample/reference/old.md"
    echo old > "$source/sample/legacy/old.md"

    python3 - "$TOOLKIT_DIR" "$out" "$source" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import generate
generate(Path(sys.argv[2]), source_root=Path(sys.argv[3]))
PY
    echo user > "$out/.opencode/skills/sample/user-notes.md"
    mkdir -p "$out/.opencode/skills/sample/user-empty"
    rm "$source/sample/reference/old.md"
    rm -rf "$source/sample/legacy"
    echo new > "$source/sample/reference/new.md"

    run python3 - "$TOOLKIT_DIR" "$out" "$source" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import generate
generate(Path(sys.argv[2]), source_root=Path(sys.argv[3]))
PY

    [ "$status" -eq 0 ]
    [ ! -e "$out/.opencode/skills/sample/reference/old.md" ]
    [ ! -e "$out/.opencode/skills/sample/legacy" ]
    [ "$(cat "$out/.opencode/skills/sample/reference/new.md")" = new ]
    [ "$(cat "$out/.opencode/skills/sample/user-notes.md")" = user ]
    [ -d "$out/.opencode/skills/sample/user-empty" ]
    rm -rf "$tmp"
}

@test "opencode: skills restore the previous files when a secure write fails" {
    tmp="$(mktemp -d)"
    source="$tmp/source"
    out="$tmp/out"
    mkdir -p "$source/sample"
    cat > "$source/sample/SKILL.md" <<'EOF'
---
name: sample
description: Sample
---
old body
EOF
    python3 - "$TOOLKIT_DIR" "$out" "$source" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import generate
generate(Path(sys.argv[2]), source_root=Path(sys.argv[3]))
PY
    sed -i.bak 's/old body/new body/' "$source/sample/SKILL.md"
    rm "$source/sample/SKILL.md.bak"

    run python3 - "$TOOLKIT_DIR" "$out" "$source" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
import generate_opencode_skills as module

real_atomic_write = module.SecureTransaction.atomic_write
failed = False
def fail_after_first_write(transaction, destination, content, mode=None):
    global failed
    real_atomic_write(transaction, destination, content, mode)
    if not failed:
        failed = True
        raise OSError("injected secure write failure")

module.SecureTransaction.atomic_write = fail_after_first_write
try:
    module.generate(Path(sys.argv[2]), source_root=Path(sys.argv[3]))
except OSError:
    pass
else:
    raise SystemExit("secure write failure was not injected")
PY

    [ "$status" -eq 0 ]
    grep -q 'old body' "$out/.opencode/skills/sample/SKILL.md"
    ! grep -q 'new body' "$out/.opencode/skills/sample/SKILL.md"
    [ -z "$(find "$out/.opencode/skills" -name '*.tmp' -print -quit)" ]
    rm -rf "$tmp"
}

@test "opencode: skills abort a user-asset collision without partial staging" {
    tmp="$(mktemp -d)"
    source="$tmp/source"
    out="$tmp/out"
    mkdir -p "$source/alpha" "$source/beta"
    for name in alpha beta; do
        cat > "$source/$name/SKILL.md" <<EOF
---
name: $name
description: $name
---
old $name
EOF
    done
    python3 - "$TOOLKIT_DIR" "$out" "$source" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import generate
generate(Path(sys.argv[2]), source_root=Path(sys.argv[3]))
PY
    echo user > "$out/.opencode/skills/beta/new.md"
    echo toolkit > "$source/beta/new.md"
    sed -i.bak 's/old alpha/new alpha/' "$source/alpha/SKILL.md"
    rm "$source/alpha/SKILL.md.bak"

    run python3 - "$TOOLKIT_DIR" "$out" "$source" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import generate
generate(Path(sys.argv[2]), source_root=Path(sys.argv[3]))
PY

    [ "$status" -ne 0 ]
    grep -q 'old alpha' "$out/.opencode/skills/alpha/SKILL.md"
    [ "$(cat "$out/.opencode/skills/beta/new.md")" = user ]
    [ -z "$(find "$out/.opencode/skills" -maxdepth 1 -name '.ai-toolkit-*' -print -quit)" ]
    rm -rf "$tmp"
}

@test "opencode: commands generator emits user-invocable skills only" {
    # debug is user-invocable → should exist
    [ -f "$OC_DIR/.opencode/commands/ai-toolkit-debug.md" ]
    # knowledge-only skills (user-invocable: false) must NOT be emitted
    [ ! -f "$OC_DIR/.opencode/commands/ai-toolkit-rag-patterns.md" ]
}

@test "opencode: command prompt lives in the markdown body (not template frontmatter)" {
    # Upstream opencode.ai/docs/commands: the markdown BODY becomes the prompt
    # template; `template:` frontmatter is JSON-config-only and ignored in .md.
    for f in "$OC_DIR"/.opencode/commands/ai-toolkit-*.md; do
        ! grep -q '^template:' "$f" || { echo "stale template frontmatter in $f"; return 1; }
        body_lines=$(sed '1,/^---$/d' "$f" | grep -c .)
        [ "$body_lines" -ge 1 ] || { echo "empty command body in $f"; return 1; }
    done
}

@test "opencode: adapted commands use portable OpenCode-native guidance" {
    commands="$OC_DIR/.opencode/commands"
    grep -q 'OpenCode-native subagents' "$commands/ai-toolkit-orchestrate.md"
    grep -q '\$ARGUMENTS' "$commands/ai-toolkit-orchestrate.md"
    ! grep -qrE 'Codex Translation Layer|Codex-native' "$commands"
    ! grep -qrE 'CLAUDE_SKILL_DIR|spawn_agent|send_input|wait_agent|close_agent|update_plan|fork_context' "$commands"
}

# ── .opencode/plugins/ (generate_opencode_plugin.py) ────────────────────────

@test "opencode: plugin file exists" {
    [ -f "$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js" ]
}

@test "opencode: plugin uses one dual V1 and V2 default export" {
    f="$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js"
    grep -q '^export default' "$f"
    grep -q 'server: AiToolkitHooks' "$f"
    grep -q 'async setup(ctx)' "$f"
    ! grep -q '^export const ' "$f"
}

@test "opencode: doctor warns only for managed V1-only plugins and preserves their bytes" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import contextlib
import io
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from doctor import DiagResult, check_opencode_plugin
from generate_opencode_plugin import GENERATED_HEADER, PLUGIN_BODY, PLUGIN_NAME

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    project, home = root / "project", root / "home"
    local = project / ".opencode/plugins" / PLUGIN_NAME
    global_plugin = home / ".config/opencode/plugins" / PLUGIN_NAME
    local.parent.mkdir(parents=True)
    global_plugin.parent.mkdir(parents=True)
    old = GENERATED_HEADER + b"\nexport const AiToolkitHooks = async () => ({});\n"
    local.write_bytes(old)
    global_plugin.write_bytes(old)
    report = DiagResult()
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        check_opencode_plugin(report, project, home)
    assert report.warnings == 2
    assert "install --local --editors opencode" in output.getvalue()
    assert "install --editors opencode" in output.getvalue()
    assert local.read_bytes() == old and global_plugin.read_bytes() == old

    local.write_text(PLUGIN_BODY)
    global_plugin.write_text("export const AiToolkitHooks = async () => ({}); // user-owned")
    report = DiagResult()
    check_opencode_plugin(report, project, home)
    assert report.warnings == 0
PY
    [ "$status" -eq 0 ]
}

@test "opencode: plugin migration preserves user files and rejects symlinked output" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from generate_opencode_plugin import GENERATED_HEADER, PLUGIN_BODY, PLUGIN_NAME, generate

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    user_project = root / "user"
    plugin = user_project / ".opencode/plugins" / PLUGIN_NAME
    plugin.parent.mkdir(parents=True)
    plugin.write_text("// user plugin\n")
    try:
        generate(user_project)
    except RuntimeError as error:
        assert "user-owned" in str(error)
    else:
        raise AssertionError("user plugin overwritten")
    assert plugin.read_text() == "// user plugin\n"

    linked = root / "linked"
    (linked / ".opencode").mkdir(parents=True)
    external = root / "external"
    external.mkdir()
    (linked / ".opencode/plugins").symlink_to(external, target_is_directory=True)
    try:
        generate(linked)
    except RuntimeError:
        pass
    else:
        raise AssertionError("symlinked output followed")
    assert not list(external.iterdir())

    plugin.write_bytes(GENERATED_HEADER + b"\nexport const AiToolkitHooks = async () => ({});\n")
    assert generate(user_project).read_text() == PLUGIN_BODY
PY
    [ "$status" -eq 0 ]
}

@test "opencode: plugin bridges all event families documented in packages/web/.../plugins.mdx" {
    f="$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js"
    for evt in 'session.created' 'session.compacted' 'session.deleted' 'message.updated' 'tool.execute.before' 'tool.execute.after' 'permission.asked' 'command.executed'; do
        grep -q "$evt" "$f" || { echo "plugin missing event: $evt"; return 1; }
    done
}

@test "opencode: plugin invokes shared toolkit hooks directory (no script copy)" {
    grep -q '.softspark/ai-toolkit/hooks' "$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js"
}

@test "opencode: plugin passes event payloads via stdin (no shell interpolation)" {
    # Security: prevent shell injection via event payloads.
    f="$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js"
    grep -q 'proc.stdin.end(input)' "$f"
    grep -Fq 'spawn("bash", [scriptPath]' "$f"
}

@test "opencode: guard exit 2 rejects tool execution" {
    run node - "$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js" "$TOOLKIT_DIR" <<'JS'
const fs = require("fs");
const os = require("os");
const path = require("path");

(async () => {
  const fixture = fs.mkdtempSync(path.join(os.tmpdir(), "opencode-v1-guard-"));
  try {
  process.env.HOME = fixture;
  const hooksDir = path.join(fixture, ".softspark/ai-toolkit/hooks");
  fs.mkdirSync(hooksDir, { recursive: true });
  for (const name of ["guard-destructive.sh", "_hook-io.sh"]) {
    fs.copyFileSync(path.join(process.argv[3], "app/hooks", name), path.join(hooksDir, name));
  }
  const source = fs.readFileSync(process.argv[2]);
  const pluginUrl = `data:text/javascript;base64,${source.toString("base64")}`;
  const { default: { server: AiToolkitHooks } } = await import(pluginUrl);
  const hooks = await AiToolkitHooks({
    project: {},
    directory: fixture,
    worktree: fixture,
  });

  try {
    await hooks["tool.execute.before"](
      { tool: "bash" },
      { args: { command: "rm -rf /tmp/example" } },
    );
  } catch (error) {
    if (!String(error.message).includes("guard-destructive.sh")) {
      throw error;
    }
    return;
  }
  throw new Error("guard exit 2 did not block tool execution");
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
JS
    [ "$status" -eq 0 ]
}

@test "opencode: payloads preserve session IDs and native tool input" {
    run node - "$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js" <<'JS'
const fs = require("fs");
const os = require("os");
const path = require("path");

(async () => {
  const fixture = fs.mkdtempSync(path.join(os.tmpdir(), "opencode-v1-payload-"));
  try {
  process.env.HOME = fixture;
  const hooksDir = path.join(fixture, ".softspark/ai-toolkit/hooks");
  fs.mkdirSync(hooksDir, { recursive: true });
  const payloadLog = path.join(fixture, "payloads.jsonl");
  process.env.AI_TOOLKIT_TEST_LOG = payloadLog;
  for (const name of ["guard-destructive", "commit-quality", "session-start", "mcp-health"]) {
    fs.writeFileSync(path.join(hooksDir, `${name}.sh`),
      '#!/usr/bin/env bash\ncat >> "$AI_TOOLKIT_TEST_LOG"\nprintf "\\n" >> "$AI_TOOLKIT_TEST_LOG"\n');
  }
  const source = fs.readFileSync(process.argv[2]);
  const pluginUrl = `data:text/javascript;base64,${source.toString("base64")}`;
  const { default: { server: AiToolkitHooks } } = await import(pluginUrl);
  const hooks = await AiToolkitHooks({
    project: {},
    directory: fixture,
    worktree: fixture,
  });

  await hooks["tool.execute.before"](
    { tool: "bash", sessionID: "tool-session" },
    { args: { command: "git status" } },
  );
  await hooks.event({
    event: {
      type: "session.created",
      properties: { sessionID: "event-session" },
    },
  });

  const payloads = fs.readFileSync(payloadLog, "utf8").trim().split("\n").map(JSON.parse);
  if (payloads[0].session_id !== "tool-session") {
    throw new Error(`missing tool session ID: ${JSON.stringify(payloads[0])}`);
  }
  if (payloads[0].tool_input?.command !== "git status") {
    throw new Error(`missing native tool input: ${JSON.stringify(payloads[0])}`);
  }
  if (payloads[2].session_id !== "event-session") {
    throw new Error(`missing event session ID: ${JSON.stringify(payloads[2])}`);
  }
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
JS
    [ "$status" -eq 0 ]
}

@test "opencode: V2 native hooks preserve blocking payloads and dispose the event stream" {
    run node - "$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js" "$TOOLKIT_DIR" <<'JS'
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

(async () => {
  const fixture = fs.mkdtempSync(path.join(os.tmpdir(), "opencode-v2-"));
  try {
    process.env.HOME = fixture;
    process.env.AI_TOOLKIT_TEST_DIR = fixture;
    const project = path.join(fixture, "project with spaces");
    fs.mkdirSync(project);
    const hookDir = path.join(fixture, ".softspark/ai-toolkit/hooks");
    fs.mkdirSync(hookDir, { recursive: true });
    for (const name of ["session-start", "mcp-health", "session-end", "save-session",
      "user-prompt-submit", "track-usage", "pre-compact", "pre-compact-save",
      "commit-quality", "post-tool-use"]) {
      fs.writeFileSync(path.join(hookDir, `${name}.sh`),
        '#!/usr/bin/env bash\ncat >> "$AI_TOOLKIT_TEST_DIR/' + name + '.jsonl"\n' +
        'printf "\\n" >> "$AI_TOOLKIT_TEST_DIR/' + name + '.jsonl"\n');
    }
    for (const name of ["guard-destructive.sh", "_hook-io.sh"]) {
      fs.copyFileSync(path.join(process.argv[3], "app/hooks", name), path.join(hookDir, name));
    }
    const source = fs.readFileSync(process.argv[2]);
    const { default: plugin } = await import(`data:text/javascript;base64,${source.toString("base64")}`);
    assert.equal(plugin.id, "ai-toolkit.project");
    assert.equal(typeof plugin.server, "function");
    assert.equal(typeof plugin.setup, "function");
    const tool = new Map(), session = new Map();
    let signal;
    let finishEvents;
    const finishedEvents = new Promise(resolve => { finishEvents = resolve; });
    const cleanup = await plugin.setup({
      location: { directory: project, project: { id: "project" } },
      tool: { async hook(name, callback) { tool.set(name, callback); } },
      session: { async hook(name, callback) { session.set(name, callback); } },
      event: { async *subscribe(options) {
        signal = options.signal;
        assert.deepEqual(options.types, ["session.created", "session.deleted"]);
        yield { type: "session.created", data: { sessionID: "foreign" }, location: { directory: "/other" } };
        yield { type: "session.created", data: { sessionID: "other-workspace" }, location: { directory: project, workspaceID: "other" } };
        for (const type of options.types) {
          yield { type, data: { sessionID: "native-session" }, location: { directory: project } };
        }
        finishEvents();
        await new Promise(resolve => signal.addEventListener("abort", resolve, { once: true }));
      } },
    });
    assert.deepEqual([...tool.keys()], ["execute.before", "execute.after"]);
    assert.deepEqual([...session.keys()], ["prompt", "compaction"]);
    await tool.get("execute.before")({ tool: "shell", sessionID: "tool-session", input: { command: "git status" } });
    await assert.rejects(tool.get("execute.before")({ tool: "shell", sessionID: "tool-session",
      input: { command: "rm -rf /fixture" } }), /guard-destructive.sh blocked/);
    await tool.get("execute.after")({ tool: "shell", sessionID: "tool-session", status: "completed", result: { content: "done" } });
    await session.get("prompt")({ sessionID: "prompt-session", prompt: { text: "Fix a bug" } });
    await session.get("compaction")({ sessionID: "compact-session" });
    await finishedEvents;
    const lines = name => fs.readFileSync(path.join(fixture, `${name}.jsonl`), "utf8").trim().split("\n").map(JSON.parse);
    assert.equal(lines("commit-quality")[0].tool_input.command, "git status");
    assert.equal(lines("commit-quality")[0].session_id, "tool-session");
    assert.equal(lines("post-tool-use")[0].session_id, "tool-session");
    assert.equal(lines("user-prompt-submit")[0].prompt, "Fix a bug");
    assert.equal(lines("track-usage").length, 1);
    assert.equal(lines("pre-compact")[0].session_id, "compact-session");
    assert.deepEqual(lines("session-start").map(item => item.session_id), ["native-session"]);
    assert.equal(lines("save-session")[0].session_id, "native-session");
    await cleanup();
    assert.equal(signal.aborted, true);
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exit(1); });
JS
    [ "$status" -eq 0 ]
}

@test "opencode: guard infrastructure failures reject V1 and V2 tool execution" {
    run node - "$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js" <<'JS'
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

(async () => {
  const fixture = fs.mkdtempSync(path.join(os.tmpdir(), "opencode-guard-errors-"));
  try {
    process.env.HOME = fixture;
    const hookDir = path.join(fixture, ".softspark/ai-toolkit/hooks");
    fs.mkdirSync(hookDir, { recursive: true });
    const source = fs.readFileSync(process.argv[2]);
    const { default: plugin } = await import(`data:text/javascript;base64,${source.toString("base64")}`);
    const legacy = await plugin.server({ directory: fixture, project: {} });
    const nativeDirectory = path.join(fixture, "native");
    fs.mkdirSync(nativeDirectory);
    const native = new Map();
    const cleanup = await plugin.setup({
      location: { directory: nativeDirectory, project: {} },
      tool: { async hook(name, callback) { native.set(name, callback); } },
      session: { async hook() {} },
      event: { async *subscribe() {} },
    });
    const invoke = [
      () => legacy["tool.execute.before"]({ tool: "bash", sessionID: "legacy" }, { args: { command: "git status" } }),
      () => native.get("execute.before")({ tool: "shell", sessionID: "native", input: { command: "git status" } }),
    ];
    for (const call of invoke) {
      await assert.rejects(call(), /guard-destructive.sh failed \(exit 127\)/);
    }
    const guard = path.join(hookDir, "guard-destructive.sh");
    for (const body of ["exit 1", "kill -TERM $$"]) {
      fs.writeFileSync(guard, `#!/usr/bin/env bash\n${body}\n`);
      for (const call of invoke) await assert.rejects(call(), /guard-destructive.sh failed/);
    }
    await legacy.dispose();
    await cleanup();
    // Exercise the real timeout path with a sleeping child, using a shorter
    // deadline in this isolated runtime copy to keep the suite fast.
    const shortened = source.toString().replace("timeout: 30000", "timeout: 50");
    assert.notEqual(shortened, source.toString());
    const { default: timedPlugin } = await import(`data:text/javascript;base64,${Buffer.from(shortened).toString("base64")}`);
    fs.writeFileSync(guard, '#!/usr/bin/env bash\nexec sleep 2\n');
    const timed = await timedPlugin.server({ directory: fixture, project: {} });
    await assert.rejects(timed["tool.execute.before"]({ tool: "bash" }, { args: { command: "git status" } }), /guard-destructive.sh failed/);
    await timed.dispose();
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exit(1); });
JS
    [ "$status" -eq 0 ]
}

@test "opencode: global and project plugins execute once and survive owner unload" {
    run node - "$TOOLKIT_DIR" <<'JS'
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

(async () => {
  const fixture = fs.mkdtempSync(path.join(os.tmpdir(), "opencode-layers-"));
  try {
    process.env.HOME = fixture;
    process.env.AI_TOOLKIT_TEST_DIR = fixture;
    const hooks = path.join(fixture, ".softspark/ai-toolkit/hooks");
    fs.mkdirSync(hooks, { recursive: true });
    for (const name of ["post-tool-use", "user-prompt-submit", "track-usage"]) {
      fs.writeFileSync(path.join(hooks, `${name}.sh`),
        `#!/usr/bin/env bash\necho hit >> "$AI_TOOLKIT_TEST_DIR/${name}.log"\n`);
    }
    const project = path.join(fixture, "project");
    const globalRoot = path.join(fixture, "global");
    fs.mkdirSync(project);
    const generator = path.join(process.argv[2], "scripts/generate_opencode_plugin.py");
    execFileSync("python3", [generator, project]);
    execFileSync("python3", [generator, project, "--config-root", globalRoot]);
    const load = async file => (await import(`data:text/javascript;base64,${fs.readFileSync(file).toString("base64")}`)).default;
    const globalPlugin = await load(path.join(globalRoot, "plugins/ai-toolkit-hooks.js"));
    const projectPlugin = await load(path.join(project, ".opencode/plugins/ai-toolkit-hooks.js"));
    assert.equal(globalPlugin.id, "ai-toolkit.global");
    assert.equal(projectPlugin.id, "ai-toolkit.project");
    const counts = name => fs.readFileSync(path.join(fixture, `${name}.log`), "utf8").trim().split("\n").length;
    const context = () => {
      const callbacks = new Map();
      return { callbacks, location: { directory: project, project: {} },
        tool: { async hook(name, callback) { callbacks.set(name, callback); } },
        session: { async hook(name, callback) { callbacks.set(name, callback); } },
        event: { async *subscribe() {} } };
    };
    const first = context(), second = context();
    const stopFirst = await globalPlugin.setup(first);
    const stopSecond = await projectPlugin.setup(second);
    for (const ctx of [first, second]) {
      await ctx.callbacks.get("execute.after")({ tool: "read", sessionID: "test", result: {} });
      await ctx.callbacks.get("prompt")({ sessionID: "test", prompt: { text: "test" } });
    }
    assert.equal(counts("post-tool-use"), 1);
    assert.equal(counts("user-prompt-submit"), 1);
    assert.equal(counts("track-usage"), 1);
    // A standby safety callback must still enforce its guard. Otherwise an
    // unload between callbacks could leave the dispatch without any guard.
    const guarded = { tool: "shell", sessionID: "test", input: { command: "git status" } };
    await assert.rejects(second.callbacks.get("execute.before")(guarded), /guard-destructive.sh failed/);
    await stopFirst();
    // Native dispatch may already have captured a callback before unload.
    await assert.rejects(first.callbacks.get("execute.before")(guarded), /guard-destructive.sh failed/);
    await second.callbacks.get("execute.after")({ tool: "read", sessionID: "test", result: {} });
    assert.equal(counts("post-tool-use"), 2);
    await stopSecond();
    const legacyFirst = await globalPlugin.server({ directory: project, project: {} });
    const legacySecond = await projectPlugin.server({ directory: project, project: {} });
    for (const instance of [legacyFirst, legacySecond]) {
      await instance["tool.execute.after"]({ tool: "read", sessionID: "test" }, {});
    }
    assert.equal(counts("post-tool-use"), 3);
    await legacyFirst.dispose();
    await legacySecond["tool.execute.after"]({ tool: "read", sessionID: "test" }, {});
    assert.equal(counts("post-tool-use"), 4);
    await legacySecond.dispose();
    const broken = context();
    broken.tool.hook = async () => { throw new Error("registration failed"); };
    await assert.rejects(globalPlugin.setup(broken), /registration failed/);
    const recovered = context();
    const stopRecovered = await projectPlugin.setup(recovered);
    await recovered.callbacks.get("execute.after")({ tool: "read", sessionID: "test", result: {} });
    assert.equal(counts("post-tool-use"), 5);
    await stopRecovered();
    let failStream;
    const streamOwner = context(), survivor = context();
    streamOwner.event.subscribe = async function* () {
      await new Promise((resolve, reject) => { failStream = reject; });
    };
    const stopStreamOwner = await globalPlugin.setup(streamOwner);
    const stopSurvivor = await projectPlugin.setup(survivor);
    await survivor.callbacks.get("execute.after")({ tool: "read", sessionID: "test", result: {} });
    assert.equal(counts("post-tool-use"), 5);
    failStream(new Error("stream disconnected"));
    await new Promise(resolve => setImmediate(resolve));
    await survivor.callbacks.get("execute.after")({ tool: "read", sessionID: "test", result: {} });
    assert.equal(counts("post-tool-use"), 6);
    await assert.rejects(streamOwner.callbacks.get("execute.before")(guarded), /guard-destructive.sh failed/);
    await stopStreamOwner();
    await stopSurvivor();
  } finally {
    fs.rmSync(fixture, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); process.exit(1); });
JS
    [ "$status" -eq 0 ]
}

# ── opencode.json (generate_opencode_json.py) ───────────────────────────────

@test "opencode: opencode.json is valid JSON with the upstream \$schema URL" {
    [ -f "$OC_DIR/opencode.json" ]
    run python3 -c "
import json
d = json.load(open('$OC_DIR/opencode.json'))
assert d['\$schema'] == 'https://opencode.ai/config.json'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "opencode: MCP merge translates command-style servers with enabled=true default" {
    tmp="$(mktemp -d)"
    cat > "$tmp/.mcp.json" <<'EOF'
{
  "mcpServers": {
    "fs": {"command": "npx", "args": ["-y", "@mcp/fs", "/tmp"]}
  }
}
EOF
    python3 "$TOOLKIT_DIR/scripts/generate_opencode_json.py" "$tmp" >/dev/null
    run python3 -c "
import json
d = json.load(open('$tmp/opencode.json'))
srv = d['mcp']['fs']
assert srv['type'] == 'local'
assert srv['command'][0] == 'npx'
assert srv['enabled'] is True
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
    rm -rf "$tmp"
}

@test "opencode: MCP merge translates remote servers and preserves headers" {
    tmp="$(mktemp -d)"
    cat > "$tmp/.mcp.json" <<'EOF'
{
  "mcpServers": {
    "gh": {"url": "https://mcp.github.com", "headers": {"Authorization": "Bearer TOKEN"}}
  }
}
EOF
    python3 "$TOOLKIT_DIR/scripts/generate_opencode_json.py" "$tmp" >/dev/null
    run python3 -c "
import json
d = json.load(open('$tmp/opencode.json'))
srv = d['mcp']['gh']
assert srv['type'] == 'remote'
assert srv['url'].startswith('https://')
assert srv['headers']['Authorization'] == 'Bearer TOKEN'
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
    rm -rf "$tmp"
}

# ── Global layout (config_root override) ────────────────────────────────────

@test "opencode: global layout lays down directly under ~/.config/opencode (no .opencode/ prefix)" {
    tmp="$(mktemp -d)"
    home="$tmp/.config/opencode"
    python3 - "$TOOLKIT_DIR" "$tmp" "$home" <<'PYEOF'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_agents import generate as gen_a
from generate_opencode_commands import generate as gen_c
from generate_opencode_skills import generate as gen_s
from generate_opencode_plugin import generate as gen_p
from generate_opencode_json import merge_into_opencode_json
target = Path(sys.argv[2]); home = Path(sys.argv[3])
gen_a(target, config_root=home)
gen_c(target, config_root=home)
gen_s(target, config_root=home)
gen_p(target, config_root=home)
merge_into_opencode_json(target, output_path=home / "opencode.json")
PYEOF
    [ -d "$home/agents" ]
    [ -d "$home/commands" ]
    [ -f "$home/skills/clean-code/SKILL.md" ]
    [ -f "$home/plugins/ai-toolkit-hooks.js" ]
    [ -f "$home/opencode.json" ]
    [ ! -d "$home/.opencode" ]
    rm -rf "$tmp"
}

@test "opencode: global skills reject a symlinked config ancestor before generate or cleanup" {
    tmp="$(mktemp -d)"
    home="$tmp/home"
    external="$tmp/external"
    mkdir -p "$home" "$external"

    python3 - "$TOOLKIT_DIR" "$external" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import generate

external = Path(sys.argv[2])
generate(external, config_root=external / "opencode")
PY
    echo external-user-data > "$external/opencode/skills/clean-code/user-notes.md"
    before="$(find "$external" -type f -exec cksum {} + | sort)"
    ln -s "$external" "$home/.config"

    run python3 - "$TOOLKIT_DIR" "$home" generate <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import cleanup, generate

home = Path(sys.argv[2])
operation = sys.argv[3]
function = generate if operation == "generate" else cleanup
function(home, config_root=home / ".config" / "opencode")
PY
    [ "$status" -ne 0 ]
    [[ "$output" == *"unsafe"* || "$output" == *"symlink"* ]] || return 1
    [ "$(find "$external" -type f -exec cksum {} + | sort)" = "$before" ]

    run python3 - "$TOOLKIT_DIR" "$home" cleanup <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, f"{sys.argv[1]}/scripts")
from generate_opencode_skills import cleanup, generate

home = Path(sys.argv[2])
operation = sys.argv[3]
function = generate if operation == "generate" else cleanup
function(home, config_root=home / ".config" / "opencode")
PY
    [ "$status" -ne 0 ]
    [[ "$output" == *"unsafe"* || "$output" == *"symlink"* ]] || return 1
    [ "$(find "$external" -type f -exec cksum {} + | sort)" = "$before" ]
    grep -q '^external-user-data$' \
        "$external/opencode/skills/clean-code/user-notes.md"
    rm -rf "$tmp"
}

@test "opencode: global generate stays pinned across an ancestor swap" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, f"{sys.argv[1]}/scripts")
import generate_opencode_skills as module

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    home = root / "home"
    source = root / "source"
    external = root / "external"
    home.mkdir()
    (source / "sample").mkdir(parents=True)
    external.mkdir()
    (source / "sample" / "SKILL.md").write_text(
        "---\nname: sample\ndescription: Sample\n---\nnew body\n"
    )
    (external / "sentinel").write_text("external\n")
    config = home / ".config"
    moved = home / ".config-before-swap"
    calls = [0]
    swapped = [False]
    real_materialize = module.SecureTransaction.materialize_parents

    def materialize_then_swap(transaction):
        real_materialize(transaction)
        calls[0] += 1
        if calls[0] == 2:
            os.rename(config, moved)
            os.symlink(external, config, target_is_directory=True)
            swapped[0] = True

    module.SecureTransaction.materialize_parents = materialize_then_swap
    try:
        module.generate(
            home,
            config_root=config / "opencode",
            source_root=source,
        )
    finally:
        if swapped[0]:
            os.unlink(config)
            os.rename(moved, config)

    assert swapped[0], "ancestor swap was not injected during secure apply"
    skill = config / "opencode" / "skills" / "sample" / "SKILL.md"
    assert "new body" in skill.read_text()
    assert sorted(path.name for path in external.iterdir()) == ["sentinel"]
    assert (external / "sentinel").read_text() == "external\n"
PY
    [ "$status" -eq 0 ]
}

@test "opencode: global cleanup stays pinned across an ancestor swap" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, f"{sys.argv[1]}/scripts")
import generate_opencode_skills as module

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    home = root / "home"
    source = root / "source"
    external = root / "external"
    home.mkdir()
    (source / "sample").mkdir(parents=True)
    external.mkdir()
    (source / "sample" / "SKILL.md").write_text(
        "---\nname: sample\ndescription: Sample\n---\nmanaged\n"
    )
    (external / "sentinel").write_text("external\n")
    config = home / ".config"
    module.generate(home, config_root=config / "opencode", source_root=source)
    user_note = config / "opencode" / "skills" / "sample" / "user.md"
    user_note.write_text("user\n")
    moved = home / ".config-before-swap"
    calls = [0]
    swapped = [False]
    real_materialize = module.SecureTransaction.materialize_parents

    def materialize_then_swap(transaction):
        real_materialize(transaction)
        calls[0] += 1
        if calls[0] == 2:
            os.rename(config, moved)
            os.symlink(external, config, target_is_directory=True)
            swapped[0] = True

    module.SecureTransaction.materialize_parents = materialize_then_swap
    try:
        module.cleanup(home, config_root=config / "opencode")
    finally:
        if swapped[0]:
            os.unlink(config)
            os.rename(moved, config)

    assert swapped[0], "ancestor swap was not injected during secure cleanup"
    skill_root = config / "opencode" / "skills" / "sample"
    assert not (skill_root / "SKILL.md").exists()
    assert (skill_root / "user.md").read_text() == "user\n"
    assert sorted(path.name for path in external.iterdir()) == ["sentinel"]
    assert (external / "sentinel").read_text() == "external\n"
PY
    [ "$status" -eq 0 ]
}

@test "opencode: secure rollback restores prior skills after an ancestor swap" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, f"{sys.argv[1]}/scripts")
import generate_opencode_skills as module

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    home = root / "home"
    source = root / "source"
    external = root / "external"
    home.mkdir()
    (source / "sample").mkdir(parents=True)
    external.mkdir()
    skill_source = source / "sample" / "SKILL.md"
    skill_source.write_text(
        "---\nname: sample\ndescription: Sample\n---\nold body\n"
    )
    (external / "sentinel").write_text("external\n")
    config = home / ".config"
    module.generate(home, config_root=config / "opencode", source_root=source)
    skill_root = config / "opencode" / "skills" / "sample"
    before = {
        path.relative_to(skill_root): path.read_bytes()
        for path in skill_root.rglob("*")
        if path.is_file()
    }
    skill_source.write_text(
        "---\nname: sample\ndescription: Sample\n---\nnew body\n"
    )
    moved = home / ".config-before-swap"
    materialize_calls = [0]
    write_calls = [0]
    swapped = [False]
    real_materialize = module.SecureTransaction.materialize_parents
    real_write = module.SecureTransaction.atomic_write

    def materialize_then_swap(transaction):
        real_materialize(transaction)
        materialize_calls[0] += 1
        if materialize_calls[0] == 2:
            os.rename(config, moved)
            os.symlink(external, config, target_is_directory=True)
            swapped[0] = True

    def write_then_fail(transaction, destination, content, mode=None):
        real_write(transaction, destination, content, mode)
        write_calls[0] += 1
        if write_calls[0] == 1:
            raise OSError("injected failure after pinned write")

    module.SecureTransaction.materialize_parents = materialize_then_swap
    module.SecureTransaction.atomic_write = write_then_fail
    try:
        try:
            module.generate(
                home,
                config_root=config / "opencode",
                source_root=source,
            )
        except OSError:
            pass
        else:
            raise AssertionError("pinned write failure was not injected")
    finally:
        if swapped[0]:
            os.unlink(config)
            os.rename(moved, config)

    assert swapped[0], "ancestor swap was not injected during secure rollback"
    after = {
        path.relative_to(skill_root): path.read_bytes()
        for path in skill_root.rglob("*")
        if path.is_file()
    }
    assert after == before, "secure rollback did not restore the complete skill tree"
    assert sorted(path.name for path in external.iterdir()) == ["sentinel"]
    assert (external / "sentinel").read_text() == "external\n"
PY
    [ "$status" -eq 0 ]
}

# ── Registry integrity ──────────────────────────────────────────────────────

@test "opencode: registry lists native generators and V1 V2 compatibility" {
    run python3 -c "
import json
d = json.load(open('$TOOLKIT_DIR/scripts/ecosystem_tools.json'))
entries = [t for t in d['tools'] if t['id'] == 'opencode']
assert len(entries) == 1
gens = set(entries[0]['our_generators'])
expected = {
    'scripts/generate_opencode.py',
    'scripts/generate_opencode_agents.py',
    'scripts/generate_opencode_commands.py',
    'scripts/generate_opencode_json.py',
    'scripts/generate_opencode_plugin.py',
    'scripts/generate_opencode_skills.py',
}
missing = expected - gens
assert not missing, f'missing generators in registry: {missing}'
paths = set(entries[0]['config_paths'])
for path in ('opencode.jsonc', 'skills/*.md', 'skills/**/SKILL.md'):
    assert path in paths, f'missing current OpenCode config path: {path}'
markers = set(entries[0]['capability_markers'])
assert 'plugin event: message.part.updated' in markers
assert 'skills array (local paths + HTTP URLs)' in markers
note = entries[0]['status_note'].lower()
assert 'setup' in note and 'server' in note and '1.18.29' in note
assert 'undocumented' not in note
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}
