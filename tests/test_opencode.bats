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

@test "opencode: plugin uses NAMED export only (opencode requirement)" {
    f="$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js"
    grep -q '^export const ' "$f"
    ! grep -q '^export default' "$f"
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
    grep -q 'proc.stdin.write' "$f"
    grep -q 'bash \${scriptPath}' "$f"
}

@test "opencode: guard exit 2 rejects tool execution" {
    run node - "$OC_DIR/.opencode/plugins/ai-toolkit-hooks.js" <<'JS'
const fs = require("fs");

(async () => {
  const source = fs.readFileSync(process.argv[2]);
  const pluginUrl = `data:text/javascript;base64,${source.toString("base64")}`;
  const { AiToolkitHooks } = await import(pluginUrl);
  const shell = () => {
    const proc = {
      env() { return this; },
      stdin: { write() {}, end() {} },
      quiet() { return this; },
      nothrow() {
        return Promise.resolve({
          exitCode: 2,
          stderr: { toString: () => "blocked by guard" },
        });
      },
    };
    return proc;
  };
  const hooks = await AiToolkitHooks({
    $: shell,
    project: {},
    directory: "/tmp",
    worktree: "/tmp",
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

(async () => {
  const source = fs.readFileSync(process.argv[2]);
  const pluginUrl = `data:text/javascript;base64,${source.toString("base64")}`;
  const { AiToolkitHooks } = await import(pluginUrl);
  const payloads = [];
  const shell = () => {
    const proc = {
      env() { return this; },
      stdin: {
        write(input) { payloads.push(JSON.parse(input)); },
        end() {},
      },
      quiet() { return this; },
      nothrow() {
        return Promise.resolve({
          exitCode: 0,
          stderr: { toString: () => "" },
        });
      },
    };
    return proc;
  };
  const hooks = await AiToolkitHooks({
    $: shell,
    project: {},
    directory: "/tmp",
    worktree: "/tmp",
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

  if (payloads[0].session_id !== "tool-session") {
    throw new Error(`missing tool session ID: ${JSON.stringify(payloads[0])}`);
  }
  if (payloads[0].tool_input?.command !== "git status") {
    throw new Error(`missing native tool input: ${JSON.stringify(payloads[0])}`);
  }
  if (payloads[2].session_id !== "event-session") {
    throw new Error(`missing event session ID: ${JSON.stringify(payloads[2])}`);
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
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

@test "opencode: registry lists all native generators and current Class C surfaces" {
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
assert 'beta' in note and 'no migration' in note
assert 'undocumented' not in note
print('ok')
"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}
