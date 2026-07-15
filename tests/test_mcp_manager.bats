#!/usr/bin/env bats
# test_mcp_manager.bats — Tests for scripts/mcp_manager.py
# Run with: bats tests/test_mcp_manager.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
MCP_MANAGER="python3 $TOOLKIT_DIR/scripts/mcp_manager.py"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    unset CODEX_HOME COPILOT_HOME
}

teardown() {
    rm -rf "$TEST_TMP"
}

# ── list ────────────────────────────────────────────────────────────────────

@test "mcp list: exits 0" {
    run $MCP_MANAGER list
    [ "$status" -eq 0 ]
}

@test "mcp list: shows 26 templates" {
    run $MCP_MANAGER list
    echo "$output" | grep -q '26 templates available'
}

@test "mcp list: output contains github" {
    run $MCP_MANAGER list
    echo "$output" | grep -q 'github'
}

@test "mcp list: output contains postgres" {
    run $MCP_MANAGER list
    echo "$output" | grep -q 'postgres'
}

@test "mcp list: output contains slack" {
    run $MCP_MANAGER list
    echo "$output" | grep -q 'slack'
}

@test "mcp editors: lists codex, cursor, and Antigravity adapters" {
    run $MCP_MANAGER editors
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'codex'
    echo "$output" | grep -q 'cursor'
    echo "$output" | grep -q 'antigravity.*project + global.*\.agents/mcp_config.json.*\.gemini/config/mcp_config.json'
}

# ── show ────────────────────────────────────────────────────────────────────

@test "mcp show github: exits 0 and shows mcpServers config" {
    run $MCP_MANAGER show github
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'mcpServers'
}

@test "mcp show github: shows required env vars" {
    run $MCP_MANAGER show github
    echo "$output" | grep -q 'GITHUB_PERSONAL_ACCESS_TOKEN'
}

@test "mcp show nonexistent: exits non-zero" {
    run $MCP_MANAGER show nonexistent-server-xyz
    [ "$status" -ne 0 ]
}

# ── add ─────────────────────────────────────────────────────────────────────

@test "mcp add github: creates .mcp.json with github config" {
    run $MCP_MANAGER add github --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.mcp.json" ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.mcp.json'))
assert 'github' in cfg['mcpServers'], 'github not in mcpServers'
"
    [ "$status" -eq 0 ]
}

@test "mcp add github postgres: adds both servers" {
    run $MCP_MANAGER add github postgres --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.mcp.json'))
assert 'github' in cfg['mcpServers'], 'github missing'
assert 'postgres' in cfg['mcpServers'], 'postgres missing'
"
    [ "$status" -eq 0 ]
}

@test "mcp add github: is idempotent (re-running does not duplicate)" {
    run $MCP_MANAGER add github --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    run $MCP_MANAGER add github --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.mcp.json'))
# Only one 'github' key should exist (dict keys are unique)
assert list(cfg['mcpServers'].keys()).count('github') == 1
"
    [ "$status" -eq 0 ]
}

@test "mcp install project cursor github: writes .cursor/mcp.json and .mcp.json" {
    run $MCP_MANAGER install --editor cursor --scope project --target "$TEST_TMP" github
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.mcp.json" ]
    [ -f "$TEST_TMP/.cursor/mcp.json" ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.cursor/mcp.json'))
assert 'github' in cfg['mcpServers']
"
    [ "$status" -eq 0 ]
}

@test "mcp install project copilot context7: writes .github/mcp.json with tools and type" {
    run $MCP_MANAGER install --editor copilot --scope project --target "$TEST_TMP" context7
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.github/mcp.json" ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.github/mcp.json'))
server = cfg['mcpServers']['context7']
assert server['type'] == 'local'
assert server['tools'] == ['*']
"
    [ "$status" -eq 0 ]
}

@test "mcp install global copilot github: writes default ~/.copilot/mcp-config.json" {
    run $MCP_MANAGER install --editor copilot github
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.copilot/mcp-config.json" ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.copilot/mcp-config.json'))
server = cfg['mcpServers']['github']
assert server['type'] == 'local'
assert server['tools'] == ['*']
"
    [ "$status" -eq 0 ]
}

@test "mcp install global copilot honors absolute existing COPILOT_HOME" {
    export COPILOT_HOME="$TEST_TMP/custom-copilot-home"
    mkdir -p "$COPILOT_HOME"

    run $MCP_MANAGER install --editor copilot github
    [ "$status" -eq 0 ]
    [ -f "$COPILOT_HOME/mcp-config.json" ]
    [ ! -e "$TEST_TMP/.copilot/mcp-config.json" ]

    run $MCP_MANAGER remove github --editor copilot
    [ "$status" -eq 0 ]
    run python3 -c "
import json
cfg = json.load(open('$COPILOT_HOME/mcp-config.json'))
assert 'github' not in cfg['mcpServers']
"
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_TMP/.copilot/mcp-config.json" ]
}

@test "mcp install global copilot rejects relative COPILOT_HOME" {
    cd "$TEST_TMP"
    export COPILOT_HOME="relative-copilot-home"

    run $MCP_MANAGER install --editor copilot github
    [ "$status" -ne 0 ]
    [ ! -e "$TEST_TMP/relative-copilot-home" ]
    [ ! -e "$TEST_TMP/.copilot/mcp-config.json" ]
}

@test "mcp install global copilot requires configured COPILOT_HOME to exist" {
    export COPILOT_HOME="$TEST_TMP/missing-copilot-home"

    run $MCP_MANAGER install --editor copilot github
    [ "$status" -ne 0 ]
    [ ! -e "$COPILOT_HOME" ]
    [ ! -e "$TEST_TMP/.copilot/mcp-config.json" ]
}

@test "mcp install global copilot rejects non-directory COPILOT_HOME" {
    export COPILOT_HOME="$TEST_TMP/copilot-home-file"
    printf '%s\n' 'user data' > "$COPILOT_HOME"

    run $MCP_MANAGER install --editor copilot github
    [ "$status" -ne 0 ]
    grep -q '^user data$' "$COPILOT_HOME"
    [ ! -e "$TEST_TMP/.copilot/mcp-config.json" ]
}

@test "mcp install global copilot rejects symlinked COPILOT_HOME" {
    external="$TEST_TMP/external-copilot-home"
    mkdir -p "$external"
    ln -s "$external" "$TEST_TMP/copilot-home-link"
    export COPILOT_HOME="$TEST_TMP/copilot-home-link"

    run $MCP_MANAGER install --editor copilot github
    [ "$status" -ne 0 ]
    [ ! -e "$external/mcp-config.json" ]
    [ ! -e "$TEST_TMP/.copilot/mcp-config.json" ]
}

@test "mcp install project roo github: writes .roo/mcp.json" {
    run $MCP_MANAGER install --editor roo --scope project --target "$TEST_TMP" github
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.roo/mcp.json" ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.roo/mcp.json'))
assert 'github' in cfg['mcpServers']
"
    [ "$status" -eq 0 ]
}

@test "Antigravity MCP project adapter preserves url schema, user data, and idempotence" {
    mkdir -p "$TEST_TMP/.agents"
    printf '%s\n' '{"theme":"user","mcpServers":{"user-owned":{"command":"true"}}}' > "$TEST_TMP/.agents/mcp_config.json"

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
from mcp_editors import install_servers

servers = {
    "remote": {
        "url": "https://example.invalid/mcp",
        "headers": {"Authorization": "Bearer TEST_TOKEN"},
        "disabled": False,
        "disabledTools": ["dangerous_tool"],
        "transport": "http",
    }
}
path = install_servers(
    ["antigravity"], servers, scope="project", project_dir=target
)[0]
first = path.read_bytes()
install_servers(["antigravity"], servers, scope="project", project_dir=target)
assert path.read_bytes() == first

config = json.loads(first)
assert config["theme"] == "user"
assert config["mcpServers"]["user-owned"] == {"command": "true"}
assert config["mcpServers"]["remote"] == servers["remote"]
PY
    [ "$status" -eq 0 ]
}

@test "mcp install global Antigravity writes ~/.gemini/config/mcp_config.json" {
    run $MCP_MANAGER install --editor antigravity github
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.gemini/config/mcp_config.json" ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.gemini/config/mcp_config.json'))
assert cfg['mcpServers']['github']['command'] == 'npx'
"
    [ "$status" -eq 0 ]
}

@test "Antigravity MCP remove preserves top-level data and user-owned servers" {
    mkdir -p "$TEST_TMP/.agents"
    printf '%s\n' '{"theme":"user","mcpServers":{"user-owned":{"serverUrl":"https://user.invalid/mcp"}}}' > "$TEST_TMP/.agents/mcp_config.json"

    run $MCP_MANAGER install --editor antigravity --scope project --target "$TEST_TMP" github
    [ "$status" -eq 0 ]
    run $MCP_MANAGER remove github --editor antigravity --scope project --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.agents/mcp_config.json'))
assert cfg['theme'] == 'user'
assert cfg['mcpServers'] == {
    'user-owned': {'serverUrl': 'https://user.invalid/mcp'}
}
canonical = json.load(open('$TEST_TMP/.mcp.json'))
assert 'github' not in canonical['mcpServers']
"
    [ "$status" -eq 0 ]
}

@test "Antigravity MCP rejects legacy httpUrl without mutating config" {
    mkdir -p "$TEST_TMP/.agents"
    printf '%s\n' '{"mcpServers":{"user-owned":{"command":"true"}}}' > "$TEST_TMP/.agents/mcp_config.json"
    cp "$TEST_TMP/.agents/mcp_config.json" "$TEST_TMP/antigravity.before"

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
from mcp_editors import install_servers

install_servers(
    ["antigravity"],
    {"legacy": {"httpUrl": "https://example.invalid/mcp"}},
    scope="project",
    project_dir=target,
)
PY
    [ "$status" -ne 0 ]
    cmp "$TEST_TMP/antigravity.before" "$TEST_TMP/.agents/mcp_config.json"
}

@test "Antigravity MCP project preflight rejects symlinked config root transactionally" {
    project="$TEST_TMP/project"
    external="$TEST_TMP/external"
    mkdir -p "$project" "$external"
    printf '%s\n' '{"mcpServers":{"user-owned":{"command":"true"}}}' > "$project/.mcp.json"
    cp "$project/.mcp.json" "$TEST_TMP/canonical.before-antigravity"
    ln -s "$external" "$project/.agents"

    run $MCP_MANAGER install --editor antigravity --scope project --target "$project" github
    [ "$status" -ne 0 ]
    cmp "$TEST_TMP/canonical.before-antigravity" "$project/.mcp.json"
    [ ! -e "$external/mcp_config.json" ]
}

@test "Antigravity MCP transaction rolls canonical config back after late replace failure" {
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import mcp_editors

canonical = target / ".mcp.json"
native = target / ".agents" / "mcp_config.json"
native.parent.mkdir(parents=True)
canonical.write_text('{"mcpServers":{"canonical-user":{"command":"true"}}}\n')
native.write_text('{"mcpServers":{"native-user":{"command":"true"}}}\n')
canonical_before = canonical.read_bytes()
native_before = native.read_bytes()

updates = mcp_editors.prepare_install_servers(
    ["claude", "antigravity"],
    {"github": {"command": "npx", "args": ["-y", "server"]}},
    scope="project",
    project_dir=target,
)
real_replace = mcp_editors.os.replace
failed = False

def fail_antigravity_once(source, destination):
    global failed
    if Path(destination) == native and not failed:
        failed = True
        raise OSError("injected Antigravity replace failure")
    return real_replace(source, destination)

mcp_editors.os.replace = fail_antigravity_once
try:
    mcp_editors.apply_config_updates(updates)
except OSError as error:
    assert "injected Antigravity replace failure" in str(error)
else:
    raise AssertionError("transaction must surface the injected failure")
finally:
    mcp_editors.os.replace = real_replace

assert canonical.read_bytes() == canonical_before
assert native.read_bytes() == native_before
PY
    [ "$status" -eq 0 ]
}

@test "mcp install global codex github: writes ~/.codex/config.toml" {
    run $MCP_MANAGER install --editor codex github
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.codex/config.toml" ]
    grep -q '\[mcp_servers.github\]' "$TEST_TMP/.codex/config.toml"
    grep -q 'command = "npx"' "$TEST_TMP/.codex/config.toml"
}

@test "mcp install global codex honors CODEX_HOME" {
    export CODEX_HOME="$TEST_TMP/custom-codex-home"
    mkdir -p "$CODEX_HOME"

    run $MCP_MANAGER install --editor codex github
    [ "$status" -eq 0 ]
    [ -f "$CODEX_HOME/config.toml" ]
    [ ! -e "$TEST_TMP/.codex/config.toml" ]
    grep -q '\[mcp_servers.github\]' "$CODEX_HOME/config.toml"
}

@test "mcp install global codex requires configured CODEX_HOME to exist" {
    export CODEX_HOME="$TEST_TMP/missing-codex-home"

    run $MCP_MANAGER install --editor codex github
    [ "$status" -ne 0 ]
    [ ! -e "$CODEX_HOME" ]
}

@test "mcp install global codex rejects symlinked CODEX_HOME" {
    external="$TEST_TMP/external-codex-home"
    mkdir -p "$external"
    ln -s "$external" "$TEST_TMP/codex-home-link"
    export CODEX_HOME="$TEST_TMP/codex-home-link"

    run $MCP_MANAGER install --editor codex github
    [ "$status" -ne 0 ]
    [ ! -e "$external/config.toml" ]
}

@test "mcp install global codex preserves quoted project path tables" {
    mkdir -p "$TEST_TMP/.codex"
    cat > "$TEST_TMP/.codex/config.toml" <<'TOML'
personality = "pragmatic"

[mcp_servers]

[projects."/Users/example/Workspace Foo"]
trust_level = "trusted"
TOML

    run $MCP_MANAGER install --editor codex github
    [ "$status" -eq 0 ]
    run python3 -c "
import tomllib
from pathlib import Path
cfg = tomllib.loads(Path('$TEST_TMP/.codex/config.toml').read_text(encoding='utf-8'))
assert cfg['projects']['/Users/example/Workspace Foo']['trust_level'] == 'trusted'
assert 'github' in cfg['mcp_servers']
"
    [ "$status" -eq 0 ]
}

@test "mcp install project codex writes documented project config and preserves comments" {
    mkdir -p "$TEST_TMP/.codex"
    cat > "$TEST_TMP/.codex/config.toml" <<'TOML'
# keep this user comment exactly
personality = "pragmatic"

[projects."/Users/example/Workspace Foo"]
trust_level = "trusted" # keep inline comment
TOML

    run $MCP_MANAGER install --editor codex --scope project --target "$TEST_TMP" github
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.codex/config.toml" ]
    grep -q '^# keep this user comment exactly$' "$TEST_TMP/.codex/config.toml"
    grep -q 'trust_level = "trusted" # keep inline comment' "$TEST_TMP/.codex/config.toml"
    grep -q '^# >>> ai-toolkit managed Codex MCP servers >>>$' "$TEST_TMP/.codex/config.toml"
    grep -q '^\[mcp_servers.github\]$' "$TEST_TMP/.codex/config.toml"
    run python3 -c "
import tomllib
from pathlib import Path
cfg = tomllib.loads(Path('$TEST_TMP/.codex/config.toml').read_text(encoding='utf-8'))
assert cfg['projects']['/Users/example/Workspace Foo']['trust_level'] == 'trusted'
assert cfg['mcp_servers']['github']['command'] == 'npx'
"
    [ "$status" -eq 0 ]
}

@test "codex MCP renders documented STDIO and HTTP schemas idempotently" {
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
from mcp_editors import install_servers

servers = {
    "local docs": {
        "command": "python3",
        "args": ["-m", "docs_mcp"],
        "env": {"MODE": "read-only"},
        "env_vars": ["LOCAL_TOKEN", {"name": "REMOTE_TOKEN", "source": "remote"}],
        "enabled_tools": ["search"],
        "default_tools_approval_mode": "prompt",
    },
    "remote": {
        "url": "https://example.invalid/mcp",
        "bearer_token_env_var": "MCP_TOKEN",
        "http_headers": {"X-Region": "eu"},
        "tool_timeout_sec": 45,
        "tools": {"search": {"approval_mode": "approve"}},
    },
}
path = install_servers(["codex"], servers, scope="project", project_dir=target)[0]
first = path.read_bytes()
install_servers(["codex"], servers, scope="project", project_dir=target)
assert path.read_bytes() == first
PY
    [ "$status" -eq 0 ]
    run python3 -c "
import tomllib
from pathlib import Path
cfg = tomllib.loads(Path('$TEST_TMP/.codex/config.toml').read_text())['mcp_servers']
assert cfg['local docs']['env']['MODE'] == 'read-only'
assert cfg['local docs']['env_vars'][1] == {'name': 'REMOTE_TOKEN', 'source': 'remote'}
assert cfg['remote']['tools']['search']['approval_mode'] == 'approve'
"
    [ "$status" -eq 0 ]
}

@test "codex MCP translates compatible portable transport type metadata" {
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
import tomllib
from pathlib import Path

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
from mcp_editors import install_servers

install_servers(
    ["codex"],
    {
        "remote": {"type": "http", "url": "https://example.invalid/mcp"},
        "stdio": {"type": "stdio", "command": "python3", "args": ["-m", "mcp"]},
        "local": {"type": "local", "command": "node", "args": ["server.js"]},
    },
    scope="project",
    project_dir=target,
)
servers = tomllib.loads(
    (target / ".codex" / "config.toml").read_text(encoding="utf-8")
)["mcp_servers"]
assert servers["remote"] == {"url": "https://example.invalid/mcp"}
assert servers["stdio"] == {"command": "python3", "args": ["-m", "mcp"]}
assert servers["local"] == {"command": "node", "args": ["server.js"]}
PY
    [ "$status" -eq 0 ]
}

@test "codex MCP rejects unsupported and conflicting portable transports unchanged" {
    mkdir -p "$TEST_TMP/.codex"
    printf '%s\n' 'personality = "pragmatic"' > "$TEST_TMP/.codex/config.toml"
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
config = target / ".codex" / "config.toml"
original = config.read_bytes()
sys.path.insert(0, str(toolkit / "scripts"))
from mcp_editors import install_servers

invalid_servers = [
    {"type": "sse", "url": "https://example.invalid/sse"},
    {"type": "tcp", "url": "https://example.invalid/mcp"},
    {"type": [], "url": "https://example.invalid/mcp"},
    {"type": "http", "command": "node"},
    {"type": "http", "url": "https://example.invalid/mcp", "command": "node"},
    {"type": "stdio", "url": "https://example.invalid/mcp"},
    {"type": "local", "url": "https://example.invalid/mcp"},
    {"type": "http", "url": "https://example.invalid/mcp", "args": ["bad"]},
]
for server in invalid_servers:
    try:
        install_servers(
            ["codex"],
            {"bad": server},
            scope="project",
            project_dir=target,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(f"Codex accepted incompatible portable server: {server}")
    assert config.read_bytes() == original
PY
    [ "$status" -eq 0 ]
}

@test "codex MCP rejects invalid TOML and incompatible fields unchanged" {
    mkdir -p "$TEST_TMP/.codex"
    printf '%s\n' '[broken' > "$TEST_TMP/.codex/config.toml"
    cp "$TEST_TMP/.codex/config.toml" "$TEST_TMP/config.before"
    run $MCP_MANAGER install --editor codex github
    [ "$status" -ne 0 ]
    cmp "$TEST_TMP/config.before" "$TEST_TMP/.codex/config.toml"

    rm "$TEST_TMP/.codex/config.toml"
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
from pathlib import Path
toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
from mcp_editors import install_servers

try:
    install_servers(
        ["codex"],
        {"bad": {"command": "node", "type": "local", "tools": ["*"]}},
        scope="project",
        project_dir=target,
    )
except ValueError:
    pass
else:
    raise AssertionError("Copilot tool lists must be rejected for Codex")
assert not (target / ".codex" / "config.toml").exists()
PY
    [ "$status" -eq 0 ]
}

@test "codex MCP rejects symlinked project roots and config paths without external writes" {
    external="$TEST_TMP/external"
    mkdir -p "$external"
    printf '%s\n' 'sentinel' > "$external/sentinel.txt"
    ln -s "$external" "$TEST_TMP/project-link"

    run $MCP_MANAGER install --editor codex --scope project --target "$TEST_TMP/project-link" github
    [ "$status" -ne 0 ]
    grep -q '^sentinel$' "$external/sentinel.txt"
    [ ! -e "$external/.codex/config.toml" ]

    real_project="$TEST_TMP/real-project"
    config_external="$TEST_TMP/config-external"
    mkdir -p "$real_project" "$config_external"
    ln -s "$config_external" "$real_project/.codex"
    run $MCP_MANAGER install --editor codex --scope project --target "$real_project" github
    [ "$status" -ne 0 ]
    [ ! -e "$config_external/config.toml" ]
}

@test "project MCP install leaves Codex TOML byte-identical when canonical config is symlinked" {
    project="$TEST_TMP/project"
    external="$TEST_TMP/external"
    mkdir -p "$project/.codex" "$external"
    printf '%s\n' '# existing Codex config' 'personality = "pragmatic"' > "$project/.codex/config.toml"
    printf '%s\n' '{"mcpServers":{"user":{"command":"true"}}}' > "$external/canonical.json"
    ln -s "$external/canonical.json" "$project/.mcp.json"
    cp "$project/.codex/config.toml" "$TEST_TMP/codex.before"
    cp "$external/canonical.json" "$TEST_TMP/canonical.before"

    run $MCP_MANAGER install --editor codex --scope project --target "$project" github
    [ "$status" -ne 0 ]
    cmp "$TEST_TMP/codex.before" "$project/.codex/config.toml"
    cmp "$TEST_TMP/canonical.before" "$external/canonical.json"
}

@test "MCP config transaction rolls back the first file when a later atomic replace fails" {
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import mcp_editors

first = target / "first.json"
second = target / "second.json"
first.write_text('{"before":1}\n', encoding="utf-8")
second.write_text('{"before":2}\n', encoding="utf-8")
first_before = first.read_bytes()
second_before = second.read_bytes()
updates = [
    mcp_editors.prepare_json_config(first, {"after": 1}),
    mcp_editors.prepare_json_config(second, {"after": 2}),
]

real_replace = mcp_editors.os.replace
failed = False

def fail_second_once(source, destination):
    global failed
    if Path(destination) == second and not failed:
        failed = True
        raise OSError("injected second replace failure")
    return real_replace(source, destination)

mcp_editors.os.replace = fail_second_once
try:
    mcp_editors.apply_config_updates(updates)
except OSError as error:
    assert "injected second replace failure" in str(error)
else:
    raise AssertionError("transaction must surface the injected failure")
finally:
    mcp_editors.os.replace = real_replace

assert first.read_bytes() == first_before
assert second.read_bytes() == second_before
PY
    [ "$status" -eq 0 ]
}

@test "project MCP remove preserves canonical bytes when Codex preflight fails" {
    run $MCP_MANAGER install --editor codex --scope project --target "$TEST_TMP" github
    [ "$status" -eq 0 ]
    cp "$TEST_TMP/.mcp.json" "$TEST_TMP/canonical.before-remove"
    printf '%s\n' '[broken' > "$TEST_TMP/.codex/config.toml"

    run $MCP_MANAGER remove github --editor codex --scope project --target "$TEST_TMP"
    [ "$status" -ne 0 ]
    cmp "$TEST_TMP/canonical.before-remove" "$TEST_TMP/.mcp.json"
}

@test "codex MCP removal deletes requested managed server and preserves user bytes" {
    mkdir -p "$TEST_TMP/.codex"
    printf '%s\n' '# user prefix' 'personality = "pragmatic"' > "$TEST_TMP/.codex/config.toml"
    run $MCP_MANAGER install --editor codex --scope project --target "$TEST_TMP" github context7
    [ "$status" -eq 0 ]
    run $MCP_MANAGER remove github --editor codex --scope project --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    grep -q '^# user prefix$' "$TEST_TMP/.codex/config.toml"
    grep -q '^personality = "pragmatic"$' "$TEST_TMP/.codex/config.toml"
    ! grep -q '\[mcp_servers.github\]' "$TEST_TMP/.codex/config.toml"
    grep -q '\[mcp_servers.context7\]' "$TEST_TMP/.codex/config.toml"
}

@test "mcp install project without names syncs existing .mcp.json into Claude .mcp.json" {
    run $MCP_MANAGER add github --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    run $MCP_MANAGER install --editor claude --scope project --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.mcp.json" ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.mcp.json'))
assert 'github' in cfg['mcpServers']
"
    [ "$status" -eq 0 ]
}

# ── remove ──────────────────────────────────────────────────────────────────

@test "mcp remove github: removes server from .mcp.json" {
    # First add github
    run $MCP_MANAGER add github --target "$TEST_TMP"
    [ "$status" -eq 0 ]

    # Then remove it
    run $MCP_MANAGER remove github --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.mcp.json'))
assert 'github' not in cfg['mcpServers'], 'github still present after remove'
"
    [ "$status" -eq 0 ]
}

@test "mcp remove github --editor cursor: removes from project editor config and .mcp.json" {
    run $MCP_MANAGER install --editor cursor --scope project --target "$TEST_TMP" github
    [ "$status" -eq 0 ]
    run $MCP_MANAGER remove github --editor cursor --scope project --target "$TEST_TMP"
    [ "$status" -eq 0 ]
    run python3 -c "
import json
cfg = json.load(open('$TEST_TMP/.mcp.json'))
assert 'github' not in cfg['mcpServers']
cfg = json.load(open('$TEST_TMP/.cursor/mcp.json'))
assert 'github' not in cfg['mcpServers']
"
    [ "$status" -eq 0 ]
}

@test "mcp remove nonexistent: exits non-zero" {
    # Create a valid .mcp.json first
    run $MCP_MANAGER add github --target "$TEST_TMP"
    [ "$status" -eq 0 ]

    run $MCP_MANAGER remove nonexistent-server-xyz --target "$TEST_TMP"
    [ "$status" -ne 0 ]
}

# ── error handling ──────────────────────────────────────────────────────────

@test "mcp: without subcommand exits non-zero" {
    run $MCP_MANAGER
    [ "$status" -ne 0 ]
}

# ── MCP template tracking in state.json ───────────────────────────────────

@test "mcp install global: tracks template in state.json" {
    export AI_TOOLKIT_HOME="$TEST_TMP/.softspark/ai-toolkit"
    mkdir -p "$AI_TOOLKIT_HOME"
    run $MCP_MANAGER install jira --editor claude --scope global
    [ "$status" -eq 0 ]
    run python3 -c "
import json
with open('$AI_TOOLKIT_HOME/state.json') as f:
    state = json.load(f)
assert 'jira' in state.get('mcp_templates', []), f'jira not tracked: {state}'
"
    [ "$status" -eq 0 ]
}

@test "mcp remove global: unregisters template from state.json" {
    export AI_TOOLKIT_HOME="$TEST_TMP/.softspark/ai-toolkit"
    mkdir -p "$AI_TOOLKIT_HOME"
    # Install first
    run $MCP_MANAGER install jira --editor claude --scope global
    [ "$status" -eq 0 ]
    # Remove
    run $MCP_MANAGER remove jira --editor claude --scope global
    [ "$status" -eq 0 ]
    run python3 -c "
import json
with open('$AI_TOOLKIT_HOME/state.json') as f:
    state = json.load(f)
assert 'jira' not in state.get('mcp_templates', []), f'jira still tracked: {state}'
"
    [ "$status" -eq 0 ]
}

# ── template validation ────────────────────────────────────────────────────

@test "mcp: all template JSON files are valid" {
    run python3 -c "
import json, sys
from pathlib import Path
templates_dir = Path('$TOOLKIT_DIR/app/mcp-templates')
errors = []
for p in sorted(templates_dir.glob('*.json')):
    try:
        data = json.load(open(p, encoding='utf-8'))
        assert 'name' in data, f'{p.name}: missing name'
        assert 'mcpServers' in data, f'{p.name}: missing mcpServers'
    except Exception as e:
        errors.append(f'{p.name}: {e}')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
"
    [ "$status" -eq 0 ]
}
