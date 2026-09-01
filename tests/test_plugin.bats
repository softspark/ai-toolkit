#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Tests for plugin pack installation across Claude and global Codex targets.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CLI="node $TOOLKIT_DIR/bin/ai-toolkit.js"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    unset CODEX_HOME
}

teardown() {
    rm -rf "$TEST_TMP"
}

_make_mcp_fixture_pack() {
    local name="${1:-legal-mcp-pack}"
    local server="${2:-rag-mcp-legal}"
    local url="${3:-http://localhost:8082/mcp/sse}"
    local pack="$TEST_TMP/.softspark/ai-toolkit/plugins/$name"
    mkdir -p "$pack/mcp"
    cat > "$pack/plugin.json" <<JSON
{
  "name": "$name",
  "description": "fixture pack with MCP",
  "version": "1.0.0",
  "domain": "legal",
  "type": "plugin-pack",
  "status": "stable",
  "requires": {"ai-toolkit": ">=1.0.0"},
  "includes": {
    "agents": [],
    "skills": [],
    "rules": [],
    "hooks": [],
    "mcp": ["$server"]
  }
}
JSON
    cat > "$pack/mcp/$server.json" <<JSON
{
  "name": "$server",
  "description": "fixture legal MCP",
  "mcpServers": {
    "$server": {"type": "http", "url": "$url"}
  },
  "postInstall": "The localhost endpoint is unauthenticated by design; keep it on localhost or protect it with a reverse proxy."
}
JSON
}

_make_gemini_mcp_hook_fixture_pack() {
    local name="${1:-gemini-combined-pack}"
    _make_mcp_fixture_pack "$name" rag-mcp-legal
    local pack="$TEST_TMP/.softspark/ai-toolkit/plugins/$name"
    mkdir -p "$pack/hooks"
    cat > "$pack/hooks/guard-destructive.sh" <<'SH'
#!/bin/sh
exit 0
SH
    chmod +x "$pack/hooks/guard-destructive.sh"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["hooks"] = ["guard-destructive.sh"]
manifest["hook_events"] = {"guard-destructive.sh": "PreToolUse"}
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]
}

@test "Gemini plugin combines MCP and hooks in one shared settings lifecycle" {
    _make_gemini_mcp_hook_fixture_pack
    mkdir -p "$TEST_TMP/.gemini"
    printf '%s\n' '{"theme":"user"}' > "$TEST_TMP/.gemini/settings.json"

    run $CLI plugin install --editor gemini gemini-combined-pack
    [ "$status" -eq 0 ]

    run python3 - "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

home = Path(sys.argv[1])
config = json.loads((home / ".gemini" / "settings.json").read_text(encoding="utf-8"))
assert config["theme"] == "user", config
assert config["mcpServers"]["rag-mcp-legal"]["url"] == "http://localhost:8082/mcp/sse", config
hooks = config["hooks"]["BeforeTool"]
assert len([entry for entry in hooks if entry.get("_source") == "ai-toolkit-plugin-gemini-combined-pack"]) == 1, hooks
state = json.loads((home / ".softspark" / "ai-toolkit" / "plugins.json").read_text(encoding="utf-8"))
assert "gemini-combined-pack" in state["targets"]["gemini"]["installed"], state
assert "gemini-combined-pack" in state["targets"]["gemini"]["mcp_ownership"], state
PY
    [ "$status" -eq 0 ]

    run python3 - "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

home = Path(sys.argv[1])
pack = home / ".softspark" / "ai-toolkit" / "plugins" / "gemini-combined-pack"
manifest_path = pack / "plugin.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"] = "2.0.0"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
template_path = pack / "mcp" / "rag-mcp-legal.json"
template = json.loads(template_path.read_text(encoding="utf-8"))
template["mcpServers"]["rag-mcp-legal"]["url"] = "http://localhost:9082/mcp/sse"
template_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run $CLI plugin update --editor gemini gemini-combined-pack
    [ "$status" -eq 0 ]

    run python3 - "$TEST_TMP/.gemini/settings.json" <<'PY'
import json
import sys

config = json.load(open(sys.argv[1], encoding="utf-8"))
assert config["mcpServers"]["rag-mcp-legal"]["url"] == "http://localhost:9082/mcp/sse", config
hooks = config["hooks"]["BeforeTool"]
assert len([entry for entry in hooks if entry.get("_source") == "ai-toolkit-plugin-gemini-combined-pack"]) == 1, hooks
PY
    [ "$status" -eq 0 ]

    run $CLI plugin remove --editor gemini gemini-combined-pack
    [ "$status" -eq 0 ]

    run python3 - "$TEST_TMP/.gemini/settings.json" <<'PY'
import json
import sys

config = json.load(open(sys.argv[1], encoding="utf-8"))
assert config["theme"] == "user", config
assert "rag-mcp-legal" not in config.get("mcpServers", {}), config
assert not any(
    entry.get("_source") == "ai-toolkit-plugin-gemini-combined-pack"
    for entries in config.get("hooks", {}).values()
    for entry in entries
    if isinstance(entry, dict)
), config
PY
    [ "$status" -eq 0 ]
}

@test "Gemini combined MCP and hook removal rolls back before deleting hook assets" {
    _make_gemini_mcp_hook_fixture_pack gemini-rollback-pack
    run $CLI plugin install --editor gemini gemini-rollback-pack
    [ "$status" -eq 0 ]

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

settings = home / ".gemini" / "settings.json"
state_path = home / ".softspark" / "ai-toolkit" / "plugins.json"
hook_asset = (
    home
    / ".softspark"
    / "ai-toolkit"
    / "hooks"
    / "plugin-gemini-rollback-pack-guard-destructive.sh"
)
settings_before = settings.read_bytes()
real_rename = plugin.os.rename
failed = False

def fail_settings_once(source, destination, **kwargs):
    global failed
    if Path(source).name == settings.name and not failed:
        failed = True
        raise OSError("injected Gemini settings replace failure")
    return real_rename(source, destination, **kwargs)

plugin.os.rename = fail_settings_once
try:
    plugin.remove_pack("gemini-rollback-pack", "gemini")
except OSError as error:
    assert "injected Gemini settings replace failure" in str(error), error
else:
    raise AssertionError("combined Gemini removal must surface the write failure")
finally:
    plugin.os.rename = real_rename

assert settings.read_bytes() == settings_before
state = json.loads(state_path.read_text(encoding="utf-8"))
assert "gemini-rollback-pack" in state["targets"]["gemini"]["installed"], state
assert hook_asset.is_file(), hook_asset
PY
    [ "$status" -eq 0 ]
}

@test "Gemini combined update rolls back the shared settings replacement" {
    _make_gemini_mcp_hook_fixture_pack gemini-update-rollback-pack
    run $CLI plugin install --editor gemini gemini-update-rollback-pack
    [ "$status" -eq 0 ]

    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/gemini-update-rollback-pack"
    run python3 - "$pack" <<'PY'
import json
import os
import sys
from pathlib import Path

pack = Path(sys.argv[1])
manifest_path = pack / "plugin.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"] = "2.0.0"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
template_path = pack / "mcp" / "rag-mcp-legal.json"
template = json.loads(template_path.read_text(encoding="utf-8"))
template["mcpServers"]["rag-mcp-legal"]["url"] = "http://localhost:9182/mcp/sse"
template_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

settings = home / ".gemini" / "settings.json"
state_path = home / ".softspark" / "ai-toolkit" / "plugins.json"
hook_asset = (
    home
    / ".softspark"
    / "ai-toolkit"
    / "hooks"
    / "plugin-gemini-update-rollback-pack-guard-destructive.sh"
)
settings_before = settings.read_bytes()
state_before = state_path.read_bytes()
hook_before = hook_asset.read_bytes()
real_rename = plugin.os.rename
settings_moves = 0

def fail_new_settings(source, destination, **kwargs):
    global settings_moves
    if Path(source).name == settings.name:
        settings_moves += 1
    if Path(source).name == settings.name and settings_moves == 2:
        raise OSError("injected Gemini update replace failure")
    return real_rename(source, destination, **kwargs)

plugin.os.rename = fail_new_settings
try:
    plugin.update_pack("gemini-update-rollback-pack", "gemini")
except OSError as error:
    assert "injected Gemini update replace failure" in str(error), error
else:
    raise AssertionError("combined Gemini update must surface the write failure")
finally:
    plugin.os.rename = real_rename

assert settings.read_bytes() == settings_before
assert state_path.read_bytes() == state_before
assert hook_asset.read_bytes() == hook_before
PY
    [ "$status" -eq 0 ]
}

@test "Gemini MCP multi-rule install rolls back settings assets rules and state" {
    _make_gemini_mcp_hook_fixture_pack gemini-install-transaction-pack
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/gemini-install-transaction-pack"
    mkdir -p "$pack/rules" "$pack/scripts" "$TEST_TMP/.gemini"
    printf '%s\n' '# First Gemini transaction rule' > "$pack/rules/first-policy.md"
    printf '%s\n' '# Second Gemini transaction rule' > "$pack/rules/second-policy.md"
    printf '%s\n' '#!/bin/sh' 'exit 0' > "$pack/scripts/helper.sh"
    chmod +x "$pack/scripts/helper.sh"
    printf '%s\n' '{"theme":"user"}' > "$TEST_TMP/.gemini/settings.json"
    printf '%s\n' '# User Gemini context' > "$TEST_TMP/.gemini/GEMINI.md"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["rules"] = ["first-policy", "second-policy"]
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

settings = home / ".gemini" / "settings.json"
gemini_md = home / ".gemini" / "GEMINI.md"
hook_asset = home / ".softspark" / "ai-toolkit" / "hooks" / "plugin-gemini-install-transaction-pack-guard-destructive.sh"
script_asset = home / ".softspark" / "ai-toolkit" / "plugin-scripts" / "gemini-install-transaction-pack" / "helper.sh"
state_path = home / ".softspark" / "ai-toolkit" / "plugins.json"
settings_before = settings.read_bytes()
gemini_before = gemini_md.read_bytes()
real_after_state = plugin._after_plugin_state_write

def fail_after_state(state, editor, name, action):
    raise OSError("injected ownership state failure")

plugin._after_plugin_state_write = fail_after_state
try:
    plugin.install_pack("gemini-install-transaction-pack", "gemini")
except OSError as error:
    assert "injected ownership state failure" in str(error), error
else:
    raise AssertionError("Gemini transaction must surface the late state failure")
finally:
    plugin._after_plugin_state_write = real_after_state

assert settings.read_bytes() == settings_before
assert gemini_md.read_bytes() == gemini_before
assert not hook_asset.exists(), hook_asset
assert not script_asset.exists(), script_asset
assert not state_path.exists(), state_path

assert plugin.install_pack("gemini-install-transaction-pack", "gemini")
config = json.loads(settings.read_text(encoding="utf-8"))
assert "rag-mcp-legal" in config["mcpServers"], config
assert "ai-toolkit-plugin-gemini-install-transaction-pack" in settings.read_text(encoding="utf-8")
gemini_content = gemini_md.read_text(encoding="utf-8")
assert "plugin-gemini-install-transaction-pack-first-policy" in gemini_content
assert "plugin-gemini-install-transaction-pack-second-policy" in gemini_content
assert hook_asset.is_file() and script_asset.is_file()
state = json.loads(state_path.read_text(encoding="utf-8"))
assert "gemini-install-transaction-pack" in state["targets"]["gemini"]["installed"], state
PY
    [ "$status" -eq 0 ]
}

@test "Gemini update restores settings rules assets and state after late ownership failure" {
    _make_gemini_mcp_hook_fixture_pack gemini-full-update-pack
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/gemini-full-update-pack"
    mkdir -p "$pack/rules" "$pack/scripts" "$TEST_TMP/.gemini"
    printf '%s\n' '# First Gemini update v1' > "$pack/rules/first-policy.md"
    printf '%s\n' '# Second Gemini update v1' > "$pack/rules/second-policy.md"
    printf '%s\n' '#!/bin/sh' '# hook v1' 'exit 0' > "$pack/hooks/guard-destructive.sh"
    printf '%s\n' '#!/bin/sh' '# helper v1' 'exit 0' > "$pack/scripts/helper.sh"
    chmod +x "$pack/hooks/guard-destructive.sh" "$pack/scripts/helper.sh"
    printf '%s\n' '# User Gemini context' > "$TEST_TMP/.gemini/GEMINI.md"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["rules"] = ["first-policy", "second-policy"]
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]
    run $CLI plugin install --editor gemini gemini-full-update-pack
    [ "$status" -eq 0 ]

    run python3 - "$pack" <<'PY'
import json
import sys
from pathlib import Path

pack = Path(sys.argv[1])
manifest_path = pack / "plugin.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"] = "2.0.0"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
(pack / "rules" / "first-policy.md").write_text("# First Gemini update v2\n", encoding="utf-8")
(pack / "rules" / "second-policy.md").write_text("# Second Gemini update v2\n", encoding="utf-8")
(pack / "hooks" / "guard-destructive.sh").write_text("#!/bin/sh\n# hook v2\nexit 0\n", encoding="utf-8")
(pack / "scripts" / "helper.sh").write_text("#!/bin/sh\n# helper v2\nexit 0\n", encoding="utf-8")
template_path = pack / "mcp" / "rag-mcp-legal.json"
template = json.loads(template_path.read_text(encoding="utf-8"))
template["mcpServers"]["rag-mcp-legal"]["url"] = "http://localhost:9382/mcp/sse"
template_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

paths = [
    home / ".gemini" / "settings.json",
    home / ".gemini" / "GEMINI.md",
    home / ".softspark" / "ai-toolkit" / "hooks" / "plugin-gemini-full-update-pack-guard-destructive.sh",
    home / ".softspark" / "ai-toolkit" / "plugin-scripts" / "gemini-full-update-pack" / "helper.sh",
    home / ".softspark" / "ai-toolkit" / "plugins.json",
]
before = {path: path.read_bytes() for path in paths}
real_after_state = plugin._after_plugin_state_write

def fail_after_v2_state(state, editor, name, action):
    version = state["targets"]["gemini"]["versions"].get("gemini-full-update-pack")
    if version == "2.0.0":
        raise OSError("injected Gemini late update ownership failure")

plugin._after_plugin_state_write = fail_after_v2_state
try:
    plugin.update_pack("gemini-full-update-pack", "gemini")
except OSError as error:
    assert "injected Gemini late update ownership failure" in str(error), error
else:
    raise AssertionError("Gemini update must surface the late ownership failure")
finally:
    plugin._after_plugin_state_write = real_after_state

for path, expected in before.items():
    assert path.read_bytes() == expected, path

assert plugin.update_pack("gemini-full-update-pack", "gemini")
assert b"http://localhost:9382/mcp/sse" in paths[0].read_bytes()
assert b"First Gemini update v2" in paths[1].read_bytes()
assert b"Second Gemini update v2" in paths[1].read_bytes()
assert b"hook v2" in paths[2].read_bytes()
assert b"helper v2" in paths[3].read_bytes()
PY
    [ "$status" -eq 0 ]
}

@test "Gemini direct remove restores settings rules assets and state after late failure" {
    _make_gemini_mcp_hook_fixture_pack gemini-remove-transaction-pack
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/gemini-remove-transaction-pack"
    mkdir -p "$pack/rules" "$pack/scripts" "$TEST_TMP/.gemini"
    printf '%s\n' '# First Gemini remove rule' > "$pack/rules/first-policy.md"
    printf '%s\n' '# Second Gemini remove rule' > "$pack/rules/second-policy.md"
    printf '%s\n' '#!/bin/sh' 'exit 0' > "$pack/scripts/helper.sh"
    chmod +x "$pack/scripts/helper.sh"
    printf '%s\n' '# User Gemini context' > "$TEST_TMP/.gemini/GEMINI.md"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["rules"] = ["first-policy", "second-policy"]
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]
    run $CLI plugin install --editor gemini gemini-remove-transaction-pack
    [ "$status" -eq 0 ]

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

paths = [
    home / ".gemini" / "settings.json",
    home / ".gemini" / "GEMINI.md",
    home / ".softspark" / "ai-toolkit" / "hooks" / "plugin-gemini-remove-transaction-pack-guard-destructive.sh",
    home / ".softspark" / "ai-toolkit" / "plugin-scripts" / "gemini-remove-transaction-pack" / "helper.sh",
    home / ".softspark" / "ai-toolkit" / "plugins.json",
]
before = {path: path.read_bytes() for path in paths}
real_after_state = plugin._after_plugin_state_write

def fail_after_state(state, editor, name, action):
    raise OSError("injected Gemini direct remove state failure")

plugin._after_plugin_state_write = fail_after_state
try:
    plugin.remove_pack("gemini-remove-transaction-pack", "gemini")
except OSError as error:
    assert "injected Gemini direct remove state failure" in str(error), error
else:
    raise AssertionError("Gemini direct remove must surface the late state failure")
finally:
    plugin._after_plugin_state_write = real_after_state

for path, expected in before.items():
    assert path.read_bytes() == expected, path

assert plugin.remove_pack("gemini-remove-transaction-pack", "gemini")
settings = json.loads(paths[0].read_text(encoding="utf-8"))
assert "rag-mcp-legal" not in settings.get("mcpServers", {}), settings
gemini = paths[1].read_text(encoding="utf-8")
assert "gemini-remove-transaction-pack" not in gemini, gemini
assert not paths[2].exists() and not paths[3].exists()
state = json.loads(paths[4].read_text(encoding="utf-8"))
assert "gemini-remove-transaction-pack" not in state["targets"]["gemini"]["installed"], state
PY
    [ "$status" -eq 0 ]
}

@test "plugin includes.mcp installs a pack-local HTTP MCP idempotently for the selected editor" {
    _make_mcp_fixture_pack

    run $CLI plugin install --editor cursor legal-mcp-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi 'unauthenticated'

    run $CLI plugin install --editor cursor legal-mcp-pack
    [ "$status" -eq 0 ]

    run python3 - <<PY
import json
from pathlib import Path

config = json.loads(Path("$TEST_TMP/.cursor/mcp.json").read_text(encoding="utf-8"))
assert list(config["mcpServers"]) == ["rag-mcp-legal"], config
assert config["mcpServers"]["rag-mcp-legal"]["url"] == "http://localhost:8082/mcp/sse"

state = json.loads(Path("$TEST_TMP/.softspark/ai-toolkit/plugins.json").read_text(encoding="utf-8"))
ownership = state["targets"]["cursor"]["mcp_ownership"]["legal-mcp-pack"]
assert ownership["source"] == "ai-toolkit-plugin-legal-mcp-pack", ownership
assert set(ownership["servers"]) == {"rag-mcp-legal"}, ownership
PY
    [ "$status" -eq 0 ]
}

@test "plugin includes.mcp refuses to overwrite an unowned MCP server" {
    _make_mcp_fixture_pack
    mkdir -p "$TEST_TMP/.cursor"
    cat > "$TEST_TMP/.cursor/mcp.json" <<'JSON'
{
  "mcpServers": {
    "rag-mcp-legal": {
      "type": "http",
      "url": "https://user.example/mcp"
    }
  }
}

JSON

    run $CLI plugin install --editor cursor legal-mcp-pack
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'Refusing user-owned MCP server collision'

    run python3 - <<PY
import json
from pathlib import Path

config = json.loads(Path("$TEST_TMP/.cursor/mcp.json").read_text(encoding="utf-8"))
assert config["mcpServers"]["rag-mcp-legal"]["url"] == "https://user.example/mcp"
state = Path("$TEST_TMP/.softspark/ai-toolkit/plugins.json")
assert not state.exists(), state
PY
    [ "$status" -eq 0 ]
}

@test "MCP-only plugin rejects an unsafe global plugin name before writing" {
    _make_mcp_fixture_pack unsafe-name-directory rag-mcp-legal
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/unsafe-name-directory"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["name"] = "../unsafe-name"
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run $CLI plugin install --editor cursor ../unsafe-name
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'Unsafe plugin name'
    [ ! -e "$TEST_TMP/.cursor/mcp.json" ]
    [ ! -e "$TEST_TMP/.softspark/ai-toolkit/plugins.json" ]
}

@test "plugin remove deletes its unchanged MCP server and preserves unrelated servers" {
    _make_mcp_fixture_pack
    run $CLI plugin install --editor cursor legal-mcp-pack
    [ "$status" -eq 0 ]

    run python3 - <<PY
import json
from pathlib import Path

path = Path("$TEST_TMP/.cursor/mcp.json")
config = json.loads(path.read_text(encoding="utf-8"))
config["mcpServers"]["user-server"] = {
    "type": "http",
    "url": "https://user.example/mcp",
}
path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run $CLI plugin remove --editor cursor legal-mcp-pack
    [ "$status" -eq 0 ]

    run python3 - <<PY
import json
from pathlib import Path

config = json.loads(Path("$TEST_TMP/.cursor/mcp.json").read_text(encoding="utf-8"))
assert "rag-mcp-legal" not in config["mcpServers"], config
assert config["mcpServers"]["user-server"]["url"] == "https://user.example/mcp"
state = json.loads(Path("$TEST_TMP/.softspark/ai-toolkit/plugins.json").read_text(encoding="utf-8"))
assert "legal-mcp-pack" not in state["targets"]["cursor"]["mcp_ownership"], state
PY
    [ "$status" -eq 0 ]
}

@test "plugin remove preserves a plugin MCP server changed by the user" {
    _make_mcp_fixture_pack
    run $CLI plugin install --editor cursor legal-mcp-pack
    [ "$status" -eq 0 ]

    run python3 - <<PY
import json
from pathlib import Path

path = Path("$TEST_TMP/.cursor/mcp.json")
config = json.loads(path.read_text(encoding="utf-8"))
config["mcpServers"]["rag-mcp-legal"]["url"] = "https://user.example/legal-mcp"
path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run $CLI plugin remove --editor cursor legal-mcp-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'preserved changed or user-owned MCP server'

    run python3 - <<PY
import json
from pathlib import Path

config = json.loads(Path("$TEST_TMP/.cursor/mcp.json").read_text(encoding="utf-8"))
assert config["mcpServers"]["rag-mcp-legal"]["url"] == "https://user.example/legal-mcp"
PY
    [ "$status" -eq 0 ]
}

@test "plugin install --editor codex bootstraps global Codex surface and installs memory-pack hooks" {
    run $CLI plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]

    # Global Codex instructions live at ~/.codex/AGENTS.md, not ~/AGENTS.md.
    [ -f "$TEST_TMP/.codex/AGENTS.md" ]
    [ ! -f "$TEST_TMP/AGENTS.md" ]
    [ -f "$TEST_TMP/.codex/hooks.json" ]
    [ -e "$TEST_TMP/.agents/skills/mem-search" ]
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh" ]
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-session-summary.sh" ]
    [ ! -e "$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-memory-pack-observation-capture.sh" ]

    run python3 - <<PY
import json
from pathlib import Path

hooks = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
post = hooks["hooks"]["PostToolUse"]
stop = hooks["hooks"]["Stop"]
owner = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack"

assert set(hooks) == {"hooks"}
assert "_source" not in json.dumps(hooks)
for event, groups in hooks["hooks"].items():
    for group in groups:
        assert set(group) <= {"matcher", "hooks"}, (event, group)
        for handler in group["hooks"]:
            assert set(handler) <= {
                "type", "command", "commandWindows", "timeout", "statusMessage", "async"
            }, handler

assert any(
    entry.get("matcher") == "Bash"
    and owner in entry["hooks"][0]["command"]
    and entry["hooks"][0]["command"].endswith(
        '/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh"'
    )
    for entry in post
), post

assert any(
    "matcher" not in entry
    and owner in entry["hooks"][0]["command"]
    and entry["hooks"][0]["command"].endswith(
        '/ai-toolkit-hooks/plugin-memory-pack-session-summary.sh"'
    )
    for entry in stop
), stop
plugin_commands = [
    handler["command"]
    for groups in hooks["hooks"].values()
    for entry in groups
    for handler in entry["hooks"]
    if owner in handler["command"]
]
assert len(plugin_commands) == 2, plugin_commands
assert all('\${CODEX_HOME:-\$HOME/.codex}' in command for command in plugin_commands)
PY
    [ "$status" -eq 0 ]
}

@test "plugin install --editor codex does not duplicate a core hook the pack declares" {
    # enterprise-pack declares core's session-end.sh alongside two hooks of its
    # own. A pack naming a core hook must not get a second copy of it.
    run $CLI plugin install --editor codex enterprise-pack
    [ "$status" -eq 0 ]

    run python3 - <<PY
import json
from pathlib import Path

hooks = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
assert "_source" not in json.dumps(hooks)
matches = 0
for entries in hooks["hooks"].values():
    for entry in entries:
        for hook in entry.get("hooks", []):
            if hook.get("command", "").endswith("session-end.sh\""):
                matches += 1

# Base Codex hooks already register session-end.sh. Installing a pack that
# declares the same core hook must not increase that count.
assert matches <= 1, matches
PY
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-enterprise-pack-session-end.sh" ]

    # The pack's own hooks DO land, under pack-prefixed names.
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-enterprise-pack-status-line.sh" ]
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-enterprise-pack-output-style.sh" ]
}

@test "plugin rules are marker-injected into Codex AGENTS.md, not written as files" {
    # Driven against a fixture pack: no shipped pack declares rules since the
    # nine no-op packs were removed, and creating one under app/plugins would
    # race the pack-count assertions in other files under --jobs 4.
    run python3 - <<PY
import json, pathlib, sys, tempfile
sys.path.insert(0, "$TOOLKIT_DIR/scripts")
import plugin

tmp = pathlib.Path(tempfile.mkdtemp())
pack = tmp / "fixture-pack"
(pack / "rules").mkdir(parents=True)
(pack / "rules" / "quality-gates.md").write_text("# Fixture rule\n\nBody.\n")
(pack / "plugin.json").write_text(json.dumps({
    "name": "fixture-pack",
    "description": "ships one rule",
    "version": "1.0.0",
    "domain": "testing",
    "type": "plugin-pack",
    "includes": {"agents": [], "skills": [], "rules": ["quality-gates"], "hooks": []},
}))
plugin.PLUGINS_DIR = tmp
sys.exit(0 if plugin.install_pack("fixture-pack", "codex") else 1)
PY
    [ "$status" -eq 0 ]

    # Codex reads instructions only from AGENTS.md, so pack rules are marker-
    # injected there, not written as unread ~/.agents/rules/ files.
    grep -q '<!-- TOOLKIT:plugin-fixture-pack-quality-gates START -->' "$TEST_TMP/.codex/AGENTS.md"
    [ ! -f "$TEST_TMP/.agents/rules/plugin-fixture-pack-quality-gates.md" ]
}

@test "plugin Codex install preserves user logical skill collisions" {
    mkdir -p "$TEST_TMP/.agents/skills/custom-memory"
    cat > "$TEST_TMP/.agents/skills/custom-memory/SKILL.md" <<'MD'
---
name: mem-search
description: User-owned memory search.
---
Keep this plugin collision unchanged.
MD

    run $CLI plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_TMP/.agents/skills/mem-search" ]
    grep -q 'Keep this plugin collision unchanged' \
        "$TEST_TMP/.agents/skills/custom-memory/SKILL.md"
}

@test "plugin Codex install rejects symlinked skill roots without external writes" {
    external="$(mktemp -d)"
    printf '%s\n' 'external plugin sentinel' > "$external/sentinel.txt"
    shasum "$external/sentinel.txt" > "$external.before"
    ln -s "$external" "$TEST_TMP/.agents"

    run $CLI plugin install --editor codex memory-pack
    [ "$status" -ne 0 ]
    shasum "$external/sentinel.txt" > "$external.after"
    cmp "$external.before" "$external.after"
    [ ! -e "$external/skills" ]
    rm -rf "$external"
}

@test "plugin remove --editor codex strips only owned handlers and files" {
    run $CLI plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]

    run python3 - <<PY
import json
from pathlib import Path

path = Path("$TEST_TMP/.codex/hooks.json")
data = json.loads(path.read_text(encoding="utf-8"))
owner = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack"
plugin_group = next(
    group
    for group in data["hooks"]["PostToolUse"]
    if owner in group["hooks"][0]["command"]
)
plugin_group["hooks"].append({"type": "command", "command": "echo colocated-user"})
data["hooks"]["Stop"].append({
    "hooks": [{"type": "command", "command": "echo independent-user"}]
})
path.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run $CLI plugin remove --editor codex memory-pack
    [ "$status" -eq 0 ]

    [ ! -f "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh" ]
    [ ! -f "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-session-summary.sh" ]

    run python3 - <<PY
import json
from pathlib import Path

hooks = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
commands = []
for entries in hooks["hooks"].values():
    for entry in entries:
        assert set(entry) <= {"matcher", "hooks"}, entry
        commands.extend(handler["command"] for handler in entry["hooks"])
assert not any("AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack" in c for c in commands)
assert "echo colocated-user" in commands
assert "echo independent-user" in commands
assert any("AI_TOOLKIT_HOOK_OWNER=ai-toolkit " in c for c in commands)
PY
    [ "$status" -eq 0 ]
}

@test "shared plugin assets stay when removing one editor target" {
    run $CLI plugin install --editor all memory-pack
    [ "$status" -eq 0 ]

    [ -f "$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-memory-pack-observation-capture.sh" ]
    [ -f "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh" ]
    [ -f "$TEST_TMP/.claude/settings.json" ]
    [ -f "$TEST_TMP/.codex/hooks.json" ]

    run $CLI plugin remove --editor codex memory-pack
    [ "$status" -eq 0 ]

    [ -f "$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-memory-pack-observation-capture.sh" ]
    [ ! -f "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh" ]

    run python3 - <<PY
import json
from pathlib import Path

claude = json.loads(Path("$TEST_TMP/.claude/settings.json").read_text(encoding="utf-8"))
assert any(
    entry.get("_source") == "ai-toolkit-plugin-memory-pack"
    for entry in claude["hooks"].get("PostToolUse", [])
), claude["hooks"]

codex = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
codex_commands = []
for entries in codex["hooks"].values():
    for entry in entries:
        codex_commands.extend(handler["command"] for handler in entry["hooks"])
assert not any(
    "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack" in command
    for command in codex_commands
)
assert any("AI_TOOLKIT_HOOK_OWNER=ai-toolkit " in command for command in codex_commands)
PY
    [ "$status" -eq 0 ]
}

@test "base Codex hook regeneration preserves native plugin handlers and assets" {
    run $CLI plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]

    shasum "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-"*.sh \
        > "$TEST_TMP/plugin-assets.before"
    run env HOME="$TEST_TMP" \
        python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$TEST_TMP" --global
    [ "$status" -eq 0 ]
    shasum "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-"*.sh \
        > "$TEST_TMP/plugin-assets.after"
    cmp "$TEST_TMP/plugin-assets.before" "$TEST_TMP/plugin-assets.after"

    run python3 - <<PY
import json
from pathlib import Path

data = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
commands = [
    handler["command"]
    for groups in data["hooks"].values()
    for group in groups
    for handler in group["hooks"]
]
owner = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack"
assert sum(owner in command for command in commands) == 2, commands
assert any("AI_TOOLKIT_HOOK_OWNER=ai-toolkit " in command for command in commands)
assert "_source" not in json.dumps(data)
PY
    [ "$status" -eq 0 ]
}

@test "plugin install migrates legacy Codex _source ownership to native commands" {
    mkdir -p "$TEST_TMP/.codex"
    cat > "$TEST_TMP/.codex/hooks.json" <<'JSON'
{
  "hooks": {
    "PostToolUse": [
      {
        "_source": "ai-toolkit-plugin-memory-pack",
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"$HOME/.softspark/ai-toolkit/hooks/plugin-memory-pack-observation-capture.sh\""
          }
        ]
      }
    ]
  }
}
JSON

    run $CLI plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]

    run python3 - <<PY
import json
from pathlib import Path

data = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
serialized = json.dumps(data)
assert "_source" not in serialized
assert ".softspark/ai-toolkit/hooks" not in serialized
owner = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack"
commands = [
    handler["command"]
    for groups in data["hooks"].values()
    for group in groups
    for handler in group["hooks"]
]
assert sum(owner in command for command in commands) == 2, commands
PY
    [ "$status" -eq 0 ]
}

@test "plugin Codex target honors an existing custom CODEX_HOME" {
    custom_home="$TEST_TMP/custom-codex-home"
    mkdir -p "$custom_home"

    run env CODEX_HOME="$custom_home" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]
    [ -f "$custom_home/AGENTS.md" ]
    [ -f "$custom_home/hooks.json" ]
    [ -x "$custom_home/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh" ]
    [ ! -e "$TEST_TMP/.codex/hooks.json" ]
    grep -q '\${CODEX_HOME:-\$HOME/.codex}/ai-toolkit-hooks/' "$custom_home/hooks.json"

    run env CODEX_HOME="$custom_home" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" plugin remove --editor codex memory-pack
    [ "$status" -eq 0 ]
    [ ! -e "$custom_home/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh" ]
}

@test "plugin Codex target rejects symlinked CODEX_HOME without external writes" {
    external="$TEST_TMP/external-codex"
    mkdir -p "$external"
    printf '%s\n' 'external sentinel' > "$external/sentinel.txt"
    shasum "$external/sentinel.txt" > "$TEST_TMP/external.before"
    ln -s "$external" "$TEST_TMP/.codex"

    run $CLI plugin install --editor codex memory-pack
    [ "$status" -ne 0 ]
    shasum "$external/sentinel.txt" > "$TEST_TMP/external.after"
    cmp "$TEST_TMP/external.before" "$TEST_TMP/external.after"
    [ ! -e "$external/hooks.json" ]
    [ ! -e "$external/AGENTS.md" ]
}

@test "plugin Codex target preserves a user-owned hook asset collision" {
    mkdir -p "$TEST_TMP/.codex/ai-toolkit-hooks"
    user_asset="$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh"
    printf '%s\n' '#!/usr/bin/env bash' 'echo user-owned' > "$user_asset"
    cp "$user_asset" "$TEST_TMP/user-asset.before"

    run $CLI plugin install --editor codex memory-pack
    [ "$status" -ne 0 ]
    cmp "$TEST_TMP/user-asset.before" "$user_asset"

    run python3 - <<PY
import json
from pathlib import Path

data = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
assert "ai-toolkit-plugin-memory-pack" not in json.dumps(data)
PY
    [ "$status" -eq 0 ]
}

@test "plugin Codex hook transaction rolls back assets when JSON write fails" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

pack = plugin.find_pack("memory-pack")
assert pack is not None
pack_dir = Path(pack["_dir"])
plugin._install_codex_base()
hooks_path = plugin.CODEX_HOME / "hooks.json"
before = hooks_path.read_bytes()
specs = plugin._resolve_pack_hooks(pack, pack_dir)

with mock.patch.object(plugin, "write_hooks_json", side_effect=OSError("injected")):
    try:
        plugin._install_codex_hooks("memory-pack", specs, [])
    except OSError as error:
        assert "injected" in str(error)
    else:
        raise AssertionError("expected injected JSON write failure")

assert hooks_path.read_bytes() == before
assert not list(plugin.CODEX_HOOKS_DIR.glob("plugin-memory-pack-*.sh"))
assert not list(plugin.CODEX_HOOKS_DIR.glob(".*.tmp"))
PY
    [ "$status" -eq 0 ]
}

@test "plugin Codex install keeps multiple hooks for one event across pack installs" {
    # enterprise-pack puts two hooks on Stop; memory-pack adds a third from a
    # different pack, plus one on PostToolUse. Two packs writing the same event
    # must accumulate rather than overwrite each other.
    run $CLI plugin install --editor codex enterprise-pack
    [ "$status" -eq 0 ]
    run $CLI plugin install --editor codex memory-pack
    [ "$status" -eq 0 ]

    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-enterprise-pack-status-line.sh" ]
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-enterprise-pack-output-style.sh" ]
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-session-summary.sh" ]
    [ -x "$TEST_TMP/.codex/ai-toolkit-hooks/plugin-memory-pack-observation-capture.sh" ]

    run python3 - <<PY
import json
from pathlib import Path

data = json.loads(Path("$TEST_TMP/.codex/hooks.json").read_text(encoding="utf-8"))
enterprise = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-enterprise-pack"
memory = "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack"
stop_enterprise = [
    group
    for group in data["hooks"]["Stop"]
    if any(enterprise in handler["command"] for handler in group["hooks"])
]
stop_memory = [
    group
    for group in data["hooks"]["Stop"]
    if any(memory in handler["command"] for handler in group["hooks"])
]
post_memory = [
    group
    for group in data["hooks"]["PostToolUse"]
    if any(memory in handler["command"] for handler in group["hooks"])
]
# The second pack must not clobber the first one's entries on the same event.
assert len(stop_enterprise) == 2, stop_enterprise
assert len(stop_memory) == 1, stop_memory
assert all("matcher" not in group for group in stop_enterprise + stop_memory)
assert len(post_memory) == 1, post_memory
assert "_source" not in json.dumps(data)
PY
    [ "$status" -eq 0 ]
}

# A throwaway toolkit whose only pack ships its own agent and skill, mirroring a
# self-contained plugin pack rather than one that merely references core assets.
_selfcontained_pack_toolkit() {
    local root
    root="$(mktemp -d)"
    cp -R "$TOOLKIT_DIR/bin" "$TOOLKIT_DIR/scripts" "$root/"
    mkdir -p "$root/app/agents" "$root/app/skills" "$root/app/hooks" \
             "$root/app/plugins/demo-selfcontained/agents" \
             "$root/app/plugins/demo-selfcontained/skills/demo-own-skill"

    cat > "$root/app/plugins/demo-selfcontained/plugin.json" <<'EOF'
{
  "name": "demo-selfcontained",
  "description": "Pack shipping its own agent and skill",
  "version": "1.0.0",
  "domain": "demo",
  "type": "plugin-pack",
  "status": "experimental",
  "requires": {"ai-toolkit": ">=1.0.0", "claude-code": ">=1.0.33"},
  "includes": {"agents": ["demo-own-agent"], "skills": ["demo-own-skill"], "rules": [], "hooks": []},
  "hook_events": {}
}
EOF
    cat > "$root/app/plugins/demo-selfcontained/agents/demo-own-agent.md" <<'EOF'
---
name: demo-own-agent
description: An agent shipped by the pack itself
tools: Read
model: sonnet
---
Body.
EOF
    cat > "$root/app/plugins/demo-selfcontained/skills/demo-own-skill/SKILL.md" <<'EOF'
---
name: demo-own-skill
description: "A skill shipped by the pack itself"
allowed-tools: Read
---
Body.
EOF
    echo "$root"
}

@test "plugin install links an agent the pack ships itself" {
    local root
    root="$(_selfcontained_pack_toolkit)"

    run node "$root/bin/ai-toolkit.js" plugin install --editor claude demo-selfcontained
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Linked agent: demo-own-agent"
    echo "$output" | grep -qv "WARN agent not found"

    # The link must point into the pack, not into app/agents.
    [ -L "$TEST_TMP/.claude/agents/demo-own-agent.md" ]
    run readlink "$TEST_TMP/.claude/agents/demo-own-agent.md"
    echo "$output" | grep -q "plugins/demo-selfcontained/agents/demo-own-agent.md"
    [ -e "$TEST_TMP/.claude/skills/demo-own-skill" ]

    rm -rf "$root"
}

@test "plugin remove drops the agent link the pack owns" {
    local root
    root="$(_selfcontained_pack_toolkit)"

    run node "$root/bin/ai-toolkit.js" plugin install --editor claude demo-selfcontained
    [ "$status" -eq 0 ]
    [ -L "$TEST_TMP/.claude/agents/demo-own-agent.md" ]

    run node "$root/bin/ai-toolkit.js" plugin remove --editor claude demo-selfcontained
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_TMP/.claude/agents/demo-own-agent.md" ]

    rm -rf "$root"
}

@test "pack reference validation accepts assets the pack ships itself" {
    run python3 - <<PY
import sys, tempfile
from pathlib import Path

sys.path.insert(0, "$TOOLKIT_DIR/scripts")
from plugin_schema import validate_references

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    core_agents = root / "app" / "agents"
    core_skills = root / "app" / "skills"
    pack = root / "app" / "plugins" / "demo"
    core_agents.mkdir(parents=True)
    core_skills.mkdir(parents=True)
    (pack / "agents").mkdir(parents=True)
    (pack / "skills" / "own-skill").mkdir(parents=True)
    (pack / "agents" / "own-agent.md").write_text("x", encoding="utf-8")
    (pack / "skills" / "own-skill" / "SKILL.md").write_text("x", encoding="utf-8")

    data = {"includes": {"agents": ["own-agent"], "skills": ["own-skill"]}}

    # Core dirs only: the pack's own assets are invisible — the old false errors.
    without = validate_references(data, core_agents, core_skills)
    assert len(without) == 2, without

    # With the pack dir: clean.
    with_pack = validate_references(data, core_agents, core_skills, pack_dir=pack)
    assert with_pack == [], with_pack

    # A genuinely missing reference still errors.
    missing = validate_references(
        {"includes": {"agents": ["nope"], "skills": []}},
        core_agents, core_skills, pack_dir=pack,
    )
    assert missing == ["References missing agent: nope"], missing

print("OK")
PY
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "^OK\$"
}

# A pack dropped into the user-level plugins dir, i.e. outside the npm package.
# AI_TOOLKIT_HOME points the toolkit's data dir at the test HOME, so the pack
# root under test is $TEST_TMP/.softspark/ai-toolkit/plugins.
_user_pack() {
    local dir="$TEST_TMP/.softspark/ai-toolkit/plugins/demo-user-pack"
    mkdir -p "$dir/agents" "$dir/skills/demo-user-skill"

    cat > "$dir/plugin.json" <<'EOF'
{
  "name": "demo-user-pack",
  "description": "Pack installed outside the toolkit package",
  "version": "2.0.0",
  "domain": "demo",
  "type": "plugin-pack",
  "status": "experimental",
  "requires": {"ai-toolkit": ">=1.0.0", "claude-code": ">=1.0.33"},
  "includes": {"agents": ["demo-user-agent"], "skills": ["demo-user-skill"], "rules": [], "hooks": []},
  "hook_events": {}
}
EOF
    cat > "$dir/agents/demo-user-agent.md" <<'EOF'
---
name: demo-user-agent
description: An agent from a user-installed pack
tools: Read
model: sonnet
---
Body.
EOF
    cat > "$dir/skills/demo-user-skill/SKILL.md" <<'EOF'
---
name: demo-user-skill
description: "A skill from a user-installed pack"
allowed-tools: Read
---
Body.
EOF
    echo "$dir"
}

@test "plugin list discovers a pack in the user-level plugins dir" {
    _user_pack >/dev/null

    AI_TOOLKIT_HOME="$TEST_TMP/.softspark/ai-toolkit" run $CLI plugin list
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "demo-user-pack"
    # Core packs stay visible alongside it.
    echo "$output" | grep -q "memory-pack"
}

@test "plugin install works from the user-level plugins dir" {
    local dir
    dir="$(_user_pack)"

    AI_TOOLKIT_HOME="$TEST_TMP/.softspark/ai-toolkit" run $CLI plugin install --editor claude demo-user-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Linked agent: demo-user-agent"
    echo "$output" | grep -q "Linked skill: demo-user-skill"

    # Both links resolve into the user dir, not into the toolkit package.
    run readlink "$TEST_TMP/.claude/agents/demo-user-agent.md"
    echo "$output" | grep -q "\.softspark/ai-toolkit/plugins/demo-user-pack/agents/demo-user-agent.md"
    run readlink "$TEST_TMP/.claude/skills/demo-user-skill"
    echo "$output" | grep -q "\.softspark/ai-toolkit/plugins/demo-user-pack/skills/demo-user-skill"
}

@test "a core pack wins a name collision with a user pack" {
    local dir="$TEST_TMP/.softspark/ai-toolkit/plugins/memory-pack"
    mkdir -p "$dir"
    cat > "$dir/plugin.json" <<'EOF'
{
  "name": "memory-pack",
  "description": "Shadow attempt",
  "version": "9.9.9",
  "domain": "demo",
  "type": "plugin-pack",
  "status": "experimental",
  "requires": {"ai-toolkit": ">=1.0.0", "claude-code": ">=1.0.33"},
  "includes": {"agents": [], "skills": [], "rules": [], "hooks": []},
  "hook_events": {}
}
EOF

    AI_TOOLKIT_HOME="$TEST_TMP/.softspark/ai-toolkit" run python3 -c "
import sys
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
import plugin
packs = [p for p in plugin.list_available() if p['name'] == 'memory-pack']
assert len(packs) == 1, packs
assert packs[0]['_root'] == 'core', packs[0]['_root']
assert packs[0]['version'] != '9.9.9', packs[0]['version']
print('OK')
"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "^OK\$"
}

@test "plugin install repairs a dangling link left by a toolkit upgrade" {
    _user_pack >/dev/null
    export AI_TOOLKIT_HOME="$TEST_TMP/.softspark/ai-toolkit"

    # The state a toolkit upgrade leaves behind: links into the old npm package
    # path, which the upgrade deleted. The pack now lives somewhere else.
    mkdir -p "$TEST_TMP/.claude/agents" "$TEST_TMP/.claude/skills"
    ln -s "$TEST_TMP/gone/plugins/demo-user-pack/agents/demo-user-agent.md" \
          "$TEST_TMP/.claude/agents/demo-user-agent.md"
    ln -s "$TEST_TMP/gone/plugins/demo-user-pack/skills/demo-user-skill" \
          "$TEST_TMP/.claude/skills/demo-user-skill"
    [ -L "$TEST_TMP/.claude/agents/demo-user-agent.md" ]
    [ ! -e "$TEST_TMP/.claude/agents/demo-user-agent.md" ]   # dangling

    run $CLI plugin install --editor claude demo-user-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Dangling agent link removed"
    echo "$output" | grep -q "Dangling skill link removed"
    echo "$output" | grep -q "Linked agent: demo-user-agent"
    echo "$output" | grep -q "Linked skill: demo-user-skill"

    # Both links resolve again, into the pack root that actually exists.
    [ -e "$TEST_TMP/.claude/agents/demo-user-agent.md" ]
    [ -e "$TEST_TMP/.claude/skills/demo-user-skill/SKILL.md" ]
    run readlink "$TEST_TMP/.claude/agents/demo-user-agent.md"
    echo "$output" | grep -q "\.softspark/ai-toolkit/plugins/demo-user-pack/agents/demo-user-agent.md"
}

@test "plugin install leaves a live link and a real file alone" {
    _user_pack >/dev/null
    export AI_TOOLKIT_HOME="$TEST_TMP/.softspark/ai-toolkit"

    # A real file the user owns, sitting on the agent name.
    mkdir -p "$TEST_TMP/.claude/agents"
    printf 'user content\n' > "$TEST_TMP/.claude/agents/demo-user-agent.md"

    run $CLI plugin install --editor claude demo-user-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "OK agent: demo-user-agent"
    [ ! -L "$TEST_TMP/.claude/agents/demo-user-agent.md" ]
    grep -q "user content" "$TEST_TMP/.claude/agents/demo-user-agent.md"

    # A second run over the now-live skill link reports OK, not a relink.
    run $CLI plugin install --editor claude demo-user-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "OK skill: demo-user-skill"
    echo "$output" | grep -qv "Dangling"
}

@test "plugin rejects a localhost HTTP MCP template without an unauthenticated warning" {
    _make_mcp_fixture_pack
    run python3 - <<PY
import json
from pathlib import Path

path = Path("$TEST_TMP/.softspark/ai-toolkit/plugins/legal-mcp-pack/mcp/rag-mcp-legal.json")
template = json.loads(path.read_text(encoding="utf-8"))
template.pop("postInstall")
path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run $CLI plugin install --editor cursor legal-mcp-pack
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'must warn that access is unauthenticated'
    [ ! -e "$TEST_TMP/.cursor/mcp.json" ]
    [ ! -e "$TEST_TMP/.softspark/ai-toolkit/plugins.json" ]
}

@test "plugin update preflights a changed MCP server before mutating state skill or rule" {
    _make_mcp_fixture_pack update-guard-pack rag-mcp-legal
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/update-guard-pack"
    mkdir -p "$pack/skills/update-guard-skill" "$pack/rules"
    cat > "$pack/skills/update-guard-skill/SKILL.md" <<'MD'
---
name: update-guard-skill
description: Fixture skill for update preflight.
---
Keep this skill installed when update preflight fails.
MD
    printf '%s\n' '# Update guard rule' '' 'Keep this rule installed.' \
        > "$pack/rules/update-guard-rule.md"
    run python3 - <<PY
import json
from pathlib import Path

path = Path("$pack/plugin.json")
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["skills"] = ["update-guard-skill"]
manifest["includes"]["rules"] = ["update-guard-rule"]
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run $CLI plugin install --editor claude update-guard-pack
    [ "$status" -eq 0 ]
    [ -L "$TEST_TMP/.claude/skills/update-guard-skill" ]
    grep -q 'TOOLKIT:plugin-update-guard-pack-update-guard-rule START' \
        "$TEST_TMP/.claude/CLAUDE.md"

    run python3 - <<PY
import json
from pathlib import Path

manifest_path = Path("$pack/plugin.json")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"] = "2.0.0"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

config_path = Path("$TEST_TMP/.claude.json")
config = json.loads(config_path.read_text(encoding="utf-8"))
config["mcpServers"]["rag-mcp-legal"]["url"] = "https://user.example/legal"
config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    state_before="$(shasum -a 256 "$TEST_TMP/.softspark/ai-toolkit/plugins.json")"
    rule_before="$(shasum -a 256 "$TEST_TMP/.claude/CLAUDE.md")"
    skill_before="$(readlink "$TEST_TMP/.claude/skills/update-guard-skill")"

    run $CLI plugin update --editor claude update-guard-pack
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'Refusing user-owned MCP server collision'

    [ "$state_before" = "$(shasum -a 256 "$TEST_TMP/.softspark/ai-toolkit/plugins.json")" ]
    [ "$rule_before" = "$(shasum -a 256 "$TEST_TMP/.claude/CLAUDE.md")" ]
    [ "$skill_before" = "$(readlink "$TEST_TMP/.claude/skills/update-guard-skill")" ]
    grep -q 'Keep this rule installed.' "$TEST_TMP/.claude/CLAUDE.md"
}

_make_rule_fixture_pack() {
    local name="${1:-rule-fixture-pack}"
    local pack="$TEST_TMP/.softspark/ai-toolkit/plugins/$name"
    mkdir -p "$pack/rules"
    cat > "$pack/plugin.json" <<JSON
{
  "name": "$name",
  "description": "fixture pack with one native rule",
  "version": "1.0.0",
  "domain": "testing",
  "type": "plugin-pack",
  "status": "stable",
  "requires": {"ai-toolkit": ">=1.0.0"},
  "includes": {
    "agents": [],
    "skills": [],
    "rules": ["fixture-policy"],
    "hooks": [],
    "mcp": []
  }
}
JSON
    printf '%s\n' '# Fixture policy' '' 'Preserve this plugin rule.' \
        > "$pack/rules/fixture-policy.md"
}

@test "Cursor multi-rule install rolls back a later write failure and retries cleanly" {
    _make_rule_fixture_pack multi-rule-pack
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/multi-rule-pack"
    printf '%s\n' '# Second fixture policy' '' 'Second plugin rule.' \
        > "$pack/rules/second-policy.md"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["rules"] = ["fixture-policy", "second-policy"]
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

first = home / ".cursor" / "rules" / "plugin-multi-rule-pack-fixture-policy.mdc"
second = home / ".cursor" / "rules" / "plugin-multi-rule-pack-second-policy.mdc"
state_path = home / ".softspark" / "ai-toolkit" / "plugins.json"
real_write = plugin._secure_atomic_write
writes = 0

def fail_second_write(path, content, mode, pins, expected_before=None):
    global writes
    if path.parent.name == "rules":
        writes += 1
        if writes == 2:
            raise OSError("injected second Cursor rule write failure")
    return real_write(path, content, mode, pins, expected_before)

plugin._secure_atomic_write = fail_second_write
try:
    plugin.install_pack("multi-rule-pack", "cursor")
except OSError as error:
    assert "injected second Cursor rule write failure" in str(error), error
else:
    raise AssertionError("multi-rule install must surface the later write failure")
finally:
    plugin._secure_atomic_write = real_write

assert not first.exists(), first
assert not second.exists(), second
if state_path.exists():
    failed_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "multi-rule-pack" not in failed_state["targets"]["cursor"]["installed"], failed_state

assert plugin.install_pack("multi-rule-pack", "cursor")
assert first.is_file(), first
assert second.is_file(), second
state = json.loads(state_path.read_text(encoding="utf-8"))
ownership = state["targets"]["cursor"]["rule_ownership"]["multi-rule-pack"]
assert set(ownership["entries"]) == {"fixture-policy", "second-policy"}, ownership
PY
    [ "$status" -eq 0 ]
}

@test "Cursor MCP and multi-rule install rolls back one ownership transaction" {
    _make_mcp_fixture_pack cursor-transaction-pack rag-mcp-legal
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/cursor-transaction-pack"
    mkdir -p "$pack/rules"
    printf '%s\n' '# First transaction rule' > "$pack/rules/first-policy.md"
    printf '%s\n' '# Second transaction rule' > "$pack/rules/second-policy.md"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["rules"] = ["first-policy", "second-policy"]
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

mcp_config = home / ".cursor" / "mcp.json"
first = home / ".cursor" / "rules" / "plugin-cursor-transaction-pack-first-policy.mdc"
second = home / ".cursor" / "rules" / "plugin-cursor-transaction-pack-second-policy.mdc"
state_path = home / ".softspark" / "ai-toolkit" / "plugins.json"
real_write = plugin._secure_atomic_write
writes = 0

def fail_second_rule(path, content, mode, pins, expected_before=None):
    global writes
    if path.parent.name == "rules":
        writes += 1
        if writes == 2:
            raise OSError("injected Cursor transaction rule failure")
    return real_write(path, content, mode, pins, expected_before)

plugin._secure_atomic_write = fail_second_rule
try:
    plugin.install_pack("cursor-transaction-pack", "cursor")
except OSError as error:
    assert "injected Cursor transaction rule failure" in str(error), error
else:
    raise AssertionError("Cursor transaction must surface the later rule failure")
finally:
    plugin._secure_atomic_write = real_write

assert not mcp_config.exists(), mcp_config
assert not first.exists(), first
assert not second.exists(), second
assert not state_path.exists(), state_path

assert plugin.install_pack("cursor-transaction-pack", "cursor")
config = json.loads(mcp_config.read_text(encoding="utf-8"))
assert "rag-mcp-legal" in config["mcpServers"], config
assert first.is_file() and second.is_file()
state = json.loads(state_path.read_text(encoding="utf-8"))
assert "cursor-transaction-pack" in state["targets"]["cursor"]["installed"], state
PY
    [ "$status" -eq 0 ]
}

@test "Cursor rollback preserves a concurrent config replacement and reports CAS conflict" {
    _make_mcp_fixture_pack cursor-cas-pack rag-mcp-legal

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import json
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

config = home / ".cursor" / "mcp.json"
state_path = home / ".softspark" / "ai-toolkit" / "plugins.json"
external = b'{"mcpServers":{"external":{"url":"https://external.invalid/mcp"}}}\n'

real_after_state = plugin._after_plugin_state_write

def replace_config_then_fail(state, editor, name, action):
    replacement = config.with_name("external-replacement.json")
    replacement.write_bytes(external)
    replacement.chmod(0o640)
    os.replace(replacement, config)
    raise OSError("injected failure after external path swap")

plugin._after_plugin_state_write = replace_config_then_fail
try:
    plugin.install_pack("cursor-cas-pack", "cursor")
except RuntimeError as error:
    assert "rollback conflict" in str(error).lower(), error
else:
    raise AssertionError("rollback must report the concurrent replacement")
finally:
    plugin._after_plugin_state_write = real_after_state

assert config.read_bytes() == external
assert config.stat().st_mode & 0o777 == 0o640
assert not state_path.exists(), state_path
PY
    [ "$status" -eq 0 ]
}

@test "plugin install rejects symlinked hook and plugin-script ancestors before external writes" {
    _make_mcp_fixture_pack unsafe-ancestor-pack rag-mcp-legal
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/unsafe-ancestor-pack"
    mkdir -p "$pack/hooks" "$pack/scripts"
    printf '%s\n' '#!/bin/sh' 'exit 0' > "$pack/hooks/guard-destructive.sh"
    printf '%s\n' '#!/bin/sh' 'exit 0' > "$pack/scripts/helper.sh"
    chmod +x "$pack/hooks/guard-destructive.sh" "$pack/scripts/helper.sh"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["hooks"] = ["guard-destructive.sh"]
manifest["hook_events"] = {"guard-destructive.sh": "PreToolUse"}
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    mkdir -p "$TEST_TMP/external-hooks" "$TEST_TMP/external-scripts"
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    ln -s "$TEST_TMP/external-hooks" "$TEST_TMP/.softspark/ai-toolkit/hooks"
    ln -s "$TEST_TMP/external-scripts" "$TEST_TMP/.softspark/ai-toolkit/plugin-scripts"

    run $CLI plugin install --editor cursor unsafe-ancestor-pack
    [ "$status" -ne 0 ]
    echo "$output" | grep -Eq 'symlinked|path identity changed'
    [ -z "$(find "$TEST_TMP/external-hooks" -mindepth 1 -print -quit)" ]
    [ -z "$(find "$TEST_TMP/external-scripts" -mindepth 1 -print -quit)" ]
    [ ! -e "$TEST_TMP/.cursor/mcp.json" ]
    [ ! -e "$TEST_TMP/.softspark/ai-toolkit/plugins.json" ]
}

@test "plugin install rejects a hook parent path swap after preflight" {
    _make_mcp_fixture_pack path-swap-pack rag-mcp-legal
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/path-swap-pack"
    mkdir -p "$pack/hooks"
    printf '%s\n' '#!/bin/sh' 'exit 0' > "$pack/hooks/guard-destructive.sh"
    chmod +x "$pack/hooks/guard-destructive.sh"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["hooks"] = ["guard-destructive.sh"]
manifest["hook_events"] = {"guard-destructive.sh": "PreToolUse"}
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

external = home / "external-hook-target"
external.mkdir()
real_apply = plugin._apply_asset_install

def swap_parent_then_apply(transaction, specs, name, *args):
    hooks = home / ".softspark" / "ai-toolkit" / "hooks"
    moved = hooks.with_name("hooks-pinned-original")
    hooks.rename(moved)
    hooks.symlink_to(external, target_is_directory=True)
    return real_apply(transaction, specs, name, *args)

plugin._apply_asset_install = swap_parent_then_apply
try:
    plugin.install_pack("path-swap-pack", "cursor")
except RuntimeError as error:
    assert "symlinked" in str(error).lower() or "identity changed" in str(error).lower(), error
else:
    raise AssertionError("plugin install must reject the swapped hook parent")
finally:
    plugin._apply_asset_install = real_apply

assert not any(external.iterdir()), list(external.iterdir())
assert not (home / ".cursor" / "mcp.json").exists()
assert not (home / ".softspark" / "ai-toolkit" / "plugins.json").exists()
PY
    [ "$status" -eq 0 ]
}

@test "Cursor update restores MCP rules assets and ownership after late install failure" {
    _make_mcp_fixture_pack cursor-update-transaction-pack rag-mcp-legal
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/cursor-update-transaction-pack"
    mkdir -p "$pack/rules" "$pack/hooks" "$pack/scripts"
    printf '%s\n' '# First Cursor v1' > "$pack/rules/first-policy.md"
    printf '%s\n' '# Second Cursor v1' > "$pack/rules/second-policy.md"
    printf '%s\n' '#!/bin/sh' 'exit 0' > "$pack/hooks/guard-destructive.sh"
    printf '%s\n' '#!/bin/sh' 'exit 0' > "$pack/scripts/helper.sh"
    chmod +x "$pack/hooks/guard-destructive.sh" "$pack/scripts/helper.sh"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["rules"] = ["first-policy", "second-policy"]
manifest["includes"]["hooks"] = ["guard-destructive.sh"]
manifest["hook_events"] = {"guard-destructive.sh": "PreToolUse"}
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]
    run $CLI plugin install --editor cursor cursor-update-transaction-pack
    [ "$status" -eq 0 ]

    run python3 - "$pack" <<'PY'
import json
import sys
from pathlib import Path

pack = Path(sys.argv[1])
manifest_path = pack / "plugin.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"] = "2.0.0"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
(pack / "rules" / "first-policy.md").write_text("# First Cursor v2\n", encoding="utf-8")
(pack / "rules" / "second-policy.md").write_text("# Second Cursor v2\n", encoding="utf-8")
template_path = pack / "mcp" / "rag-mcp-legal.json"
template = json.loads(template_path.read_text(encoding="utf-8"))
template["mcpServers"]["rag-mcp-legal"]["url"] = "http://localhost:9282/mcp/sse"
template_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

paths = [
    home / ".cursor" / "mcp.json",
    home / ".cursor" / "hooks.json",
    home / ".cursor" / "rules" / "plugin-cursor-update-transaction-pack-first-policy.mdc",
    home / ".cursor" / "rules" / "plugin-cursor-update-transaction-pack-second-policy.mdc",
    home / ".softspark" / "ai-toolkit" / "hooks" / "plugin-cursor-update-transaction-pack-guard-destructive.sh",
    home / ".softspark" / "ai-toolkit" / "plugin-scripts" / "cursor-update-transaction-pack" / "helper.sh",
    home / ".softspark" / "ai-toolkit" / "plugins.json",
]
before = {path: path.read_bytes() for path in paths}
real_write = plugin._secure_atomic_write
writes = 0

def fail_second_new_rule(path, content, mode, pins, expected_before=None):
    global writes
    if path.parent.name == "rules":
        writes += 1
        if writes == 2:
            raise OSError("injected Cursor update rule failure")
    return real_write(path, content, mode, pins, expected_before)

plugin._secure_atomic_write = fail_second_new_rule
try:
    plugin.update_pack("cursor-update-transaction-pack", "cursor")
except OSError as error:
    assert "injected Cursor update rule failure" in str(error), error
else:
    raise AssertionError("Cursor update must surface the later rule failure")
finally:
    plugin._secure_atomic_write = real_write

for path, expected in before.items():
    assert path.read_bytes() == expected, path

assert plugin.update_pack("cursor-update-transaction-pack", "cursor")
assert b"http://localhost:9282/mcp/sse" in paths[0].read_bytes()
assert b"First Cursor v2" in paths[2].read_bytes()
assert b"Second Cursor v2" in paths[3].read_bytes()
PY
    [ "$status" -eq 0 ]
}

@test "Cursor direct remove restores MCP rules assets and ownership after late failure" {
    _make_mcp_fixture_pack cursor-remove-transaction-pack rag-mcp-legal
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/cursor-remove-transaction-pack"
    mkdir -p "$pack/rules" "$pack/hooks" "$pack/scripts"
    printf '%s\n' '# First Cursor remove rule' > "$pack/rules/first-policy.md"
    printf '%s\n' '# Second Cursor remove rule' > "$pack/rules/second-policy.md"
    printf '%s\n' '#!/bin/sh' 'exit 0' > "$pack/hooks/guard-destructive.sh"
    printf '%s\n' '#!/bin/sh' 'exit 0' > "$pack/scripts/helper.sh"
    chmod +x "$pack/hooks/guard-destructive.sh" "$pack/scripts/helper.sh"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["rules"] = ["first-policy", "second-policy"]
manifest["includes"]["hooks"] = ["guard-destructive.sh"]
manifest["hook_events"] = {"guard-destructive.sh": "PreToolUse"}
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]
    run $CLI plugin install --editor cursor cursor-remove-transaction-pack
    [ "$status" -eq 0 ]

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

paths = [
    home / ".cursor" / "mcp.json",
    home / ".cursor" / "hooks.json",
    home / ".cursor" / "rules" / "plugin-cursor-remove-transaction-pack-first-policy.mdc",
    home / ".cursor" / "rules" / "plugin-cursor-remove-transaction-pack-second-policy.mdc",
    home / ".softspark" / "ai-toolkit" / "hooks" / "plugin-cursor-remove-transaction-pack-guard-destructive.sh",
    home / ".softspark" / "ai-toolkit" / "plugin-scripts" / "cursor-remove-transaction-pack" / "helper.sh",
    home / ".softspark" / "ai-toolkit" / "plugins.json",
]
before = {path: path.read_bytes() for path in paths}
real_after_state = plugin._after_plugin_state_write

def fail_after_state(state, editor, name, action):
    raise OSError("injected Cursor direct remove state failure")

plugin._after_plugin_state_write = fail_after_state
try:
    plugin.remove_pack("cursor-remove-transaction-pack", "cursor")
except OSError as error:
    assert "injected Cursor direct remove state failure" in str(error), error
else:
    raise AssertionError("Cursor direct remove must surface the late state failure")
finally:
    plugin._after_plugin_state_write = real_after_state

for path, expected in before.items():
    assert path.read_bytes() == expected, path

assert plugin.remove_pack("cursor-remove-transaction-pack", "cursor")
mcp = json.loads(paths[0].read_text(encoding="utf-8"))
assert "rag-mcp-legal" not in mcp.get("mcpServers", {}), mcp
assert not paths[2].exists() and not paths[3].exists()
assert not paths[4].exists() and not paths[5].exists()
state = json.loads(paths[6].read_text(encoding="utf-8"))
assert "cursor-remove-transaction-pack" not in state["targets"]["cursor"]["installed"], state
PY
    [ "$status" -eq 0 ]
}

@test "plugin remove preserves path-swapped mode-changed and user-added shared assets" {
    _make_mcp_fixture_pack exact-asset-pack rag-mcp-legal
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/exact-asset-pack"
    mkdir -p "$pack/hooks" "$pack/scripts"
    printf '%s\n' '#!/bin/sh' '# owned hook' 'exit 0' > "$pack/hooks/guard-destructive.sh"
    printf '%s\n' '#!/bin/sh' '# owned helper' 'exit 0' > "$pack/scripts/helper.sh"
    chmod +x "$pack/hooks/guard-destructive.sh" "$pack/scripts/helper.sh"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["hooks"] = ["guard-destructive.sh"]
manifest["hook_events"] = {"guard-destructive.sh": "PreToolUse"}
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]
    run $CLI plugin install --editor cursor exact-asset-pack
    [ "$status" -eq 0 ]

    hook="$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-exact-asset-pack-guard-destructive.sh"
    scripts="$TEST_TMP/.softspark/ai-toolkit/plugin-scripts/exact-asset-pack"
    run python3 - "$hook" "$scripts" <<'PY'
import os
import sys
from pathlib import Path

hook = Path(sys.argv[1])
scripts = Path(sys.argv[2])
helper = scripts / "helper.sh"
replacement = scripts / "replacement.tmp"
replacement.write_bytes(helper.read_bytes())
replacement.chmod(helper.stat().st_mode & 0o777)
os.replace(replacement, helper)
hook.chmod(0o600)
(scripts / "user-added.txt").write_text("preserve user file\n", encoding="utf-8")
(scripts / "nested").mkdir()
(scripts / "nested" / "user.txt").write_text("preserve nested file\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run $CLI plugin remove --editor cursor exact-asset-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'preserved changed or user-owned plugin asset'
    [ -f "$hook" ]
    [ "$(stat -f '%Lp' "$hook")" = "600" ]
    [ -f "$scripts/helper.sh" ]
    grep -q 'owned helper' "$scripts/helper.sh"
    grep -q 'preserve user file' "$scripts/user-added.txt"
    grep -q 'preserve nested file' "$scripts/nested/user.txt"
}

@test "plugin remove preserves a concurrent create at an owned asset path" {
    _make_mcp_fixture_pack concurrent-create-pack rag-mcp-legal
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/concurrent-create-pack"
    mkdir -p "$pack/hooks"
    printf '%s\n' '#!/bin/sh' '# owned hook' 'exit 0' > "$pack/hooks/guard-destructive.sh"
    chmod +x "$pack/hooks/guard-destructive.sh"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["hooks"] = ["guard-destructive.sh"]
manifest["hook_events"] = {"guard-destructive.sh": "PreToolUse"}
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]
    run $CLI plugin install --editor cursor concurrent-create-pack
    [ "$status" -eq 0 ]

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

hook = home / ".softspark" / "ai-toolkit" / "hooks" / "plugin-concurrent-create-pack-guard-destructive.sh"
state_path = home / ".softspark" / "ai-toolkit" / "plugins.json"
external = b"#!/bin/sh\n# concurrent user file\nexit 7\n"
real_after_state = plugin._after_plugin_state_write

def create_user_file_then_fail(state, editor, name, action):
    hook.write_bytes(external)
    hook.chmod(0o640)
    raise OSError("injected failure after concurrent create")

plugin._after_plugin_state_write = create_user_file_then_fail
try:
    plugin.remove_pack("concurrent-create-pack", "cursor")
except RuntimeError as error:
    assert "rollback conflict" in str(error).lower(), error
else:
    raise AssertionError("rollback must report the concurrent create")
finally:
    plugin._after_plugin_state_write = real_after_state

assert hook.read_bytes() == external
assert hook.stat().st_mode & 0o777 == 0o640
state = json.loads(state_path.read_text(encoding="utf-8"))
assert "concurrent-create-pack" in state["targets"]["cursor"]["installed"], state
PY
    [ "$status" -eq 0 ]
}

@test "Cursor warns when declared rules resolve only to core assets" {
    _make_rule_fixture_pack core-only-rule-pack
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/core-only-rule-pack"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["rules"] = ["quality-gates"]
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run $CLI plugin install --editor cursor core-only-rule-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'WARN nothing registered for cursor'
}

@test "plugin CLI guidance and summaries expose Cursor and Gemini targets" {
    run $CLI plugin list --editor all
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Cursor'
    echo "$output" | grep -q 'Gemini'
    echo "$output" | grep -q 'claude|codex|cursor|gemini|all'

    run $CLI plugin status --editor all
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '^Installed plugins for cursor:'
    echo "$output" | grep -q '^Installed plugins for gemini:'

    run $CLI plugin list --editor unsupported
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'Valid values: claude, codex, cursor, gemini, all'
}

@test "plugin lifecycle lock serializes concurrent toolkit installs" {
    _make_mcp_fixture_pack lifecycle-lock-pack rag-mcp-legal
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/lifecycle-lock-pack"
    mkdir -p "$pack/scripts"
    cat > "$pack/scripts/init.py" <<'PY'
import os
import time
from pathlib import Path

marker = Path.home() / ".softspark" / "ai-toolkit" / "init-active.lock"
try:
    descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    raise SystemExit("OVERLAPPING PLUGIN LIFECYCLE")
try:
    time.sleep(0.4)
finally:
    os.close(descriptor)
    marker.unlink(missing_ok=True)
PY

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import os
import subprocess
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
command = [
    "node",
    str(toolkit / "bin" / "ai-toolkit.js"),
    "plugin",
    "install",
    "--editor",
    "cursor",
    "lifecycle-lock-pack",
]
env = dict(os.environ)
env["HOME"] = str(home)
first = subprocess.Popen(command, cwd=toolkit, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
second = subprocess.Popen(command, cwd=toolkit, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
first_output, _ = first.communicate(timeout=15)
second_output, _ = second.communicate(timeout=15)
assert first.returncode == 0, first_output
assert second.returncode == 0, second_output
combined = first_output + second_output
assert "OVERLAPPING PLUGIN LIFECYCLE" not in combined, combined
assert "WARN init failed" not in combined, combined
PY
    [ "$status" -eq 0 ]
}

@test "Cursor plugin rules install idempotently and remove only their owned file" {
    _make_rule_fixture_pack
    mkdir -p "$TEST_TMP/.cursor/rules"
    printf '%s\n' 'user cursor rule' > "$TEST_TMP/.cursor/rules/user-owned.mdc"

    run $CLI plugin install --editor cursor rule-fixture-pack
    [ "$status" -eq 0 ]
    owned="$TEST_TMP/.cursor/rules/plugin-rule-fixture-pack-fixture-policy.mdc"
    [ -f "$owned" ]
    grep -q '^alwaysApply: true$' "$owned"
    grep -q 'Preserve this plugin rule.' "$owned"
    before="$(shasum -a 256 "$owned")"

    run $CLI plugin install --editor cursor rule-fixture-pack
    [ "$status" -eq 0 ]
    [ "$before" = "$(shasum -a 256 "$owned")" ]

    run $CLI plugin remove --editor cursor rule-fixture-pack
    [ "$status" -eq 0 ]
    [ ! -e "$owned" ]
    grep -q '^user cursor rule$' "$TEST_TMP/.cursor/rules/user-owned.mdc"
}

@test "Cursor plugin remove preserves a user-modified owned rule file" {
    _make_rule_fixture_pack
    run $CLI plugin install --editor cursor rule-fixture-pack
    [ "$status" -eq 0 ]
    owned="$TEST_TMP/.cursor/rules/plugin-rule-fixture-pack-fixture-policy.mdc"
    printf '%s\n' 'user modification' >> "$owned"

    run $CLI plugin remove --editor cursor rule-fixture-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'preserved changed or user-owned plugin rule'
    grep -q '^user modification$' "$owned"
}

@test "Gemini plugin rules install idempotently and remove only their owned section" {
    _make_rule_fixture_pack
    mkdir -p "$TEST_TMP/.gemini"
    printf '%s\n' '# User Gemini context' > "$TEST_TMP/.gemini/GEMINI.md"

    run $CLI plugin install --editor gemini rule-fixture-pack
    [ "$status" -eq 0 ]
    target="$TEST_TMP/.gemini/GEMINI.md"
    grep -q 'TOOLKIT:plugin-rule-fixture-pack-fixture-policy START' "$target"
    grep -q 'Preserve this plugin rule.' "$target"
    before="$(shasum -a 256 "$target")"

    run $CLI plugin install --editor gemini rule-fixture-pack
    [ "$status" -eq 0 ]
    [ "$before" = "$(shasum -a 256 "$target")" ]

    run $CLI plugin remove --editor gemini rule-fixture-pack
    [ "$status" -eq 0 ]
    ! grep -q 'plugin-rule-fixture-pack-fixture-policy' "$target"
    grep -q '^# User Gemini context$' "$target"
}

@test "Gemini plugin remove preserves a user-modified owned rule section" {
    _make_rule_fixture_pack
    run $CLI plugin install --editor gemini rule-fixture-pack
    [ "$status" -eq 0 ]
    target="$TEST_TMP/.gemini/GEMINI.md"
    run python3 - <<PY
from pathlib import Path

path = Path("$target")
content = path.read_text(encoding="utf-8")
content = content.replace(
    "Preserve this plugin rule.",
    "Preserve this plugin rule.\nUser-modified Gemini rule.",
)
path.write_text(content, encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run $CLI plugin remove --editor gemini rule-fixture-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'preserved changed or user-owned plugin rule'
    grep -q 'User-modified Gemini rule.' "$target"
}

@test "secure atomic write never overwrites a concurrent replacement at the CAS boundary" {
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

target = home / ".softspark" / "ai-toolkit" / "cas-write.json"
target.parent.mkdir(parents=True)
target.write_bytes(b"original\n")
before = plugin._read_file_version(target)
assert before is not None
pins = plugin._pin_ancestors(target)
external = b"concurrent replacement\n"
real_rename = plugin.os.rename
injected = False

def race_before_quarantine(source, destination, *args, **kwargs):
    global injected
    source_name = os.fspath(source)
    if not injected and source_name == target.name:
        replacement = target.with_name("external-write.json")
        replacement.write_bytes(external)
        os.replace(replacement, target)
        injected = True
    return real_rename(source, destination, *args, **kwargs)

plugin.os.rename = race_before_quarantine
try:
    try:
        plugin._secure_atomic_write(target, b"toolkit update\n", 0o600, pins, before)
    except RuntimeError as error:
        assert "changed" in str(error).lower() or "concurrent" in str(error).lower(), error
    else:
        raise AssertionError("CAS write must reject a concurrent replacement")
finally:
    plugin.os.rename = real_rename

assert injected, "the write did not cross the atomic quarantine boundary"
assert target.read_bytes() == external
PY
    [ "$status" -eq 0 ]
}

@test "secure unlink never deletes a concurrent replacement at the CAS boundary" {
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

target = home / ".softspark" / "ai-toolkit" / "cas-unlink.json"
target.parent.mkdir(parents=True)
target.write_bytes(b"original\n")
before = plugin._read_file_version(target)
assert before is not None
pins = plugin._pin_ancestors(target)
external = b"concurrent replacement\n"
real_rename = plugin.os.rename
injected = False

def race_before_quarantine(source, destination, *args, **kwargs):
    global injected
    source_name = os.fspath(source)
    if not injected and source_name == target.name:
        replacement = target.with_name("external-unlink.json")
        replacement.write_bytes(external)
        os.replace(replacement, target)
        injected = True
    return real_rename(source, destination, *args, **kwargs)

plugin.os.rename = race_before_quarantine
try:
    try:
        plugin._secure_unlink(target, before, pins)
    except RuntimeError as error:
        assert "changed" in str(error).lower() or "concurrent" in str(error).lower(), error
    else:
        raise AssertionError("CAS unlink must reject a concurrent replacement")
finally:
    plugin.os.rename = real_rename

assert injected, "the unlink did not cross the atomic quarantine boundary"
assert target.read_bytes() == external
PY
    [ "$status" -eq 0 ]
}

@test "JSON runtime writes plugin ownership state inside its pinned file transaction" {
    _make_mcp_fixture_pack transactional-state-pack rag-mcp-legal

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

real_save_state = plugin.save_state

def reject_resnapshot(_state):
    raise AssertionError("plugins.json bypassed PluginFileTransaction")

plugin.save_state = reject_resnapshot
try:
    assert plugin.install_pack("transactional-state-pack", "cursor")
finally:
    plugin.save_state = real_save_state

state_path = home / ".softspark" / "ai-toolkit" / "plugins.json"
state = json.loads(state_path.read_text(encoding="utf-8"))
assert "transactional-state-pack" in state["targets"]["cursor"]["installed"], state
PY
    [ "$status" -eq 0 ]
}

@test "Gemini rules reject duplicate orphaned and crossed owned markers without changing content" {
    _make_rule_fixture_pack
    run $CLI plugin install --editor gemini rule-fixture-pack
    [ "$status" -eq 0 ]

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin_rules

state = json.loads(
    (home / ".softspark" / "ai-toolkit" / "plugins.json").read_text(encoding="utf-8")
)
ownership = state["targets"]["gemini"]["rule_ownership"]["rule-fixture-pack"]
path = home / ".gemini" / "GEMINI.md"
valid = path.read_text(encoding="utf-8")
section = "plugin-rule-fixture-pack-fixture-policy"
start = f"<!-- TOOLKIT:{section} START -->"
end = f"<!-- TOOLKIT:{section} END -->"
block_start = valid.index(start)
block_end = valid.index(end, block_start) + len(end)
block = valid[block_start:block_end]
body = "Preserve this plugin rule."
cases = {
    "duplicate": valid + "\n" + block + "\n",
    "orphan-start": f"# User Gemini context\n\n{start}\n{body}\n",
    "orphan-end": f"# User Gemini context\n\n{body}\n{end}\n",
    "crossed": (
        f"# User Gemini context\n\n{start}\n"
        "<!-- TOOLKIT:user-section START -->\n"
        f"{body}\n{end}\n"
        "<!-- TOOLKIT:user-section END -->\n"
    ),
}
for label, malformed in cases.items():
    path.write_text(malformed, encoding="utf-8")
    before = path.read_bytes()
    try:
        plugin_rules.prepare_plugin_rule_removal(
            "rule-fixture-pack",
            "gemini",
            ownership,
        )
    except RuntimeError as error:
        assert "marker" in str(error).lower(), (label, error)
    else:
        raise AssertionError(f"{label} owned markers must fail closed")
    assert path.read_bytes() == before, label
PY
    [ "$status" -eq 0 ]
}

@test "plugin init runs only after the cross-process lifecycle lock is released" {
    _make_mcp_fixture_pack reentrant-init-pack rag-mcp-legal
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/reentrant-init-pack"
    mkdir -p "$pack/scripts"
    printf '%s\n' 'raise SystemExit(0)' > "$pack/scripts/init.py"

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

real_init = plugin._run_plugin_init
observed_depths = []

def assert_lock_released(pack_dir):
    observed_depths.append(plugin._PLUGIN_LOCK_DEPTH)
    assert plugin._PLUGIN_LOCK_DEPTH == 0, "init inherited the lifecycle lock"

plugin._run_plugin_init = assert_lock_released
try:
    assert plugin.install_pack("reentrant-init-pack", "cursor")
finally:
    plugin._run_plugin_init = real_init

assert observed_depths == [0], observed_depths
PY
    [ "$status" -eq 0 ]
}

@test "plugin init subprocess is bounded and marks reentrant child lifecycle" {
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import subprocess
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

pack = home / ".softspark" / "ai-toolkit" / "plugins" / "bounded-init-pack"
(pack / "scripts").mkdir(parents=True)
(pack / "scripts" / "init.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
captured = {}
real_popen = plugin.subprocess.Popen

class FakeProcess:
    def __init__(self, command, **kwargs):
        self.args = command
        self.returncode = 0
        captured.update(kwargs)

    def communicate(self, timeout):
        captured["timeout"] = timeout
        return "initialized\n", ""

def fake_popen(command, **kwargs):
    return FakeProcess(command, **kwargs)

plugin.subprocess.Popen = fake_popen
try:
    plugin._run_plugin_init(pack)
finally:
    plugin.subprocess.Popen = real_popen

assert isinstance(captured.get("timeout"), (int, float)), captured
assert 0 < captured["timeout"] <= 60, captured
assert captured["env"]["AI_TOOLKIT_PLUGIN_INIT_ACTIVE"] == "1", captured
assert captured["start_new_session"] is True, captured
assert captured["stdout"] is subprocess.PIPE, captured
assert captured["stderr"] is subprocess.PIPE, captured
PY
    [ "$status" -eq 0 ]
}

@test "rolling multi-editor update retires shared assets after their last consumer" {
    _make_mcp_fixture_pack rolling-assets-pack rag-mcp-legal
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/rolling-assets-pack"
    mkdir -p "$pack/hooks" "$pack/scripts"
    printf '%s\n' '#!/bin/sh' 'exit 0' > "$pack/hooks/old-hook.sh"
    printf '%s\n' '#!/bin/sh' 'exit 0' > "$pack/scripts/old-helper.sh"
    chmod +x "$pack/hooks/old-hook.sh" "$pack/scripts/old-helper.sh"
    run python3 - "$pack/plugin.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["includes"]["hooks"] = ["old-hook.sh"]
manifest["hook_events"] = {"old-hook.sh": "PreToolUse"}
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
    [ "$status" -eq 0 ]

    run $CLI plugin install --editor cursor rolling-assets-pack
    [ "$status" -eq 0 ]
    run $CLI plugin install --editor gemini rolling-assets-pack
    [ "$status" -eq 0 ]

    old_hook="$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-rolling-assets-pack-old-hook.sh"
    old_script="$TEST_TMP/.softspark/ai-toolkit/plugin-scripts/rolling-assets-pack/old-helper.sh"
    [ -f "$old_hook" ]
    [ -f "$old_script" ]

    run python3 - "$pack" <<'PY'
import json
import sys
from pathlib import Path

pack = Path(sys.argv[1])
manifest_path = pack / "plugin.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["version"] = "2.0.0"
manifest["includes"]["hooks"] = ["new-hook.sh"]
manifest["hook_events"] = {"new-hook.sh": "PreToolUse"}
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
(pack / "hooks" / "old-hook.sh").unlink()
(pack / "scripts" / "old-helper.sh").unlink()
(pack / "hooks" / "new-hook.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
(pack / "scripts" / "new-helper.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
(pack / "hooks" / "new-hook.sh").chmod(0o755)
(pack / "scripts" / "new-helper.sh").chmod(0o755)
PY
    [ "$status" -eq 0 ]

    run $CLI plugin update --editor cursor rolling-assets-pack
    [ "$status" -eq 0 ]
    [ -f "$old_hook" ]
    [ -f "$old_script" ]
    run python3 - "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

home = Path(sys.argv[1])
state = json.loads(
    (home / ".softspark" / "ai-toolkit" / "plugins.json").read_text(encoding="utf-8")
)
ownership = state["shared_asset_ownership"]["rolling-assets-pack"]
assert ownership["consumers"]["cursor"] == ["hook:new-hook.sh", "script:new-helper.sh"], ownership
assert ownership["consumers"]["gemini"] == ["hook:old-hook.sh", "script:old-helper.sh"], ownership
PY
    [ "$status" -eq 0 ]

    run $CLI plugin update --editor gemini rolling-assets-pack
    [ "$status" -eq 0 ]
    [ ! -e "$old_hook" ]
    [ ! -e "$old_script" ]
    run python3 - "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

home = Path(sys.argv[1])
state = json.loads(
    (home / ".softspark" / "ai-toolkit" / "plugins.json").read_text(encoding="utf-8")
)
ownership = state["shared_asset_ownership"]["rolling-assets-pack"]
assert set(ownership["entries"]) == {"hook:new-hook.sh", "script:new-helper.sh"}, ownership
assert ownership["consumers"] == {
    "cursor": ["hook:new-hook.sh", "script:new-helper.sh"],
    "gemini": ["hook:new-hook.sh", "script:new-helper.sh"],
}, ownership
PY
    [ "$status" -eq 0 ]
}

@test "normal lifecycle commands wait for an active post-commit plugin init" {
    _make_mcp_fixture_pack init-gate-pack rag-mcp-legal
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/init-gate-pack"
    mkdir -p "$pack/scripts"
    cat > "$pack/scripts/init.py" <<'PY'
import time
from pathlib import Path

marker = Path.home() / ".softspark" / "ai-toolkit" / "init-gate-active"
marker.write_text("active\n", encoding="utf-8")
try:
    time.sleep(1.5)
finally:
    marker.unlink(missing_ok=True)
PY

    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import os
import subprocess
import sys
import time
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
base = ["node", str(toolkit / "bin" / "ai-toolkit.js"), "plugin"]
env = dict(os.environ)
env["HOME"] = str(home)
install = subprocess.Popen(
    [*base, "install", "--editor", "cursor", "init-gate-pack"],
    cwd=toolkit,
    env=env,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
marker = home / ".softspark" / "ai-toolkit" / "init-gate-active"
deadline = time.monotonic() + 5
while not marker.exists() and time.monotonic() < deadline:
    time.sleep(0.02)
assert marker.exists(), "plugin init did not start"
remove = subprocess.Popen(
    [*base, "remove", "--editor", "cursor", "init-gate-pack"],
    cwd=toolkit,
    env=env,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
time.sleep(0.6)
assert remove.poll() is None, "normal lifecycle mutated state while init was active"
install_output, _ = install.communicate(timeout=10)
remove_output, _ = remove.communicate(timeout=10)
assert install.returncode == 0, install_output
assert remove.returncode == 0, remove_output
PY
    [ "$status" -eq 0 ]
}

@test "direct reinstall retires stale shared assets with no remaining consumer" {
    _make_mcp_fixture_pack reinstall-assets-pack rag-mcp-legal
    pack="$TEST_TMP/.softspark/ai-toolkit/plugins/reinstall-assets-pack"
    mkdir -p "$pack/scripts"
    printf '%s\n' '#!/bin/sh' 'exit 0' > "$pack/scripts/old-helper.sh"
    chmod +x "$pack/scripts/old-helper.sh"

    run $CLI plugin install --editor cursor reinstall-assets-pack
    [ "$status" -eq 0 ]
    old_asset="$TEST_TMP/.softspark/ai-toolkit/plugin-scripts/reinstall-assets-pack/old-helper.sh"
    new_asset="$TEST_TMP/.softspark/ai-toolkit/plugin-scripts/reinstall-assets-pack/new-helper.sh"
    [ -f "$old_asset" ]

    run python3 - "$pack" <<'PY'
import sys
from pathlib import Path

pack = Path(sys.argv[1])
(pack / "scripts" / "old-helper.sh").unlink()
(pack / "scripts" / "new-helper.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
(pack / "scripts" / "new-helper.sh").chmod(0o755)
PY
    [ "$status" -eq 0 ]

    run $CLI plugin install --editor cursor reinstall-assets-pack
    [ "$status" -eq 0 ]
    [ ! -e "$old_asset" ]
    [ -f "$new_asset" ]
    run python3 - "$TEST_TMP" <<'PY'
import json
import sys
from pathlib import Path

home = Path(sys.argv[1])
state = json.loads(
    (home / ".softspark" / "ai-toolkit" / "plugins.json").read_text(encoding="utf-8")
)
ownership = state["shared_asset_ownership"]["reinstall-assets-pack"]
assert set(ownership["entries"]) == {"script:new-helper.sh"}, ownership
assert ownership["consumers"] == {"cursor": ["script:new-helper.sh"]}, ownership
PY
    [ "$status" -eq 0 ]
}

@test "rollback restore preserves a concurrent replacement at the final CAS boundary" {
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

target = home / ".softspark" / "ai-toolkit" / "restore-cas.json"
target.parent.mkdir(parents=True)
target.write_bytes(b"original\n")
target.chmod(0o600)
transaction = plugin.PluginFileTransaction((target,))
transaction.expect_file(target, b"produced\n", 0o600)
mutation = transaction.mutations[target]
transaction.backup(target)
produced = plugin._secure_atomic_write(
    target,
    b"produced\n",
    0o600,
    mutation.ancestors,
    mutation.before,
)
transaction.record_version(target, produced)
external = b"concurrent external replacement\n"

def replace_at_restore_boundary(_mutation, _expected_current):
    replacement = target.with_name("external-restore.json")
    replacement.write_bytes(external)
    replacement.chmod(0o640)
    os.replace(replacement, target)

plugin._before_restore_backup_exchange = replace_at_restore_boundary
try:
    transaction.rollback()
except RuntimeError as error:
    message = str(error).lower()
    assert "rollback conflict" in message, error
    assert "original retained" in message or "concurrent" in message, error
else:
    raise AssertionError("rollback restore must reject the final-boundary replacement")

assert target.read_bytes() == external
assert target.stat().st_mode & 0o777 == 0o640
assert mutation.backup_path is not None and mutation.backup_path.exists()
PY
    [ "$status" -eq 0 ]
}

@test "plugin init timeout kills the whole process group before a grandchild writes" {
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import os
import sys
import time
from pathlib import Path

if os.name != "posix":
    raise SystemExit(0)

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

pack = home / ".softspark" / "ai-toolkit" / "plugins" / "init-tree-pack"
scripts = pack / "scripts"
scripts.mkdir(parents=True)
marker = home / "late-grandchild-marker"
child_code = (
    "import time\n"
    "from pathlib import Path\n"
    "time.sleep(0.7)\n"
    f"Path({str(marker)!r}).write_text('late\\n', encoding='utf-8')\n"
)
(scripts / "init.py").write_text(
    "import subprocess, sys, time\n"
    f"subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
    "time.sleep(10)\n",
    encoding="utf-8",
)
real_timeout = plugin.PLUGIN_INIT_TIMEOUT_SECONDS
plugin.PLUGIN_INIT_TIMEOUT_SECONDS = 0.2
try:
    plugin._run_plugin_init(pack)
finally:
    plugin.PLUGIN_INIT_TIMEOUT_SECONDS = real_timeout
time.sleep(0.9)
assert not marker.exists(), marker.read_text(encoding="utf-8") if marker.exists() else marker
PY
    [ "$status" -eq 0 ]
}

@test "plugin init fails before execution when process-tree isolation is unsupported" {
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import subprocess
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
home = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

pack = home / ".softspark" / "ai-toolkit" / "plugins" / "windows-init-pack"
(pack / "scripts").mkdir(parents=True)
(pack / "scripts" / "init.py").write_text(
    "from pathlib import Path\nPath.home().joinpath('unsafe-init-ran').write_text('ran')\n",
    encoding="utf-8",
)
real_name = plugin.os.name
real_run = plugin.subprocess.run
executed = False

def forbidden_run(*args, **kwargs):
    global executed
    executed = True
    return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

plugin.os.name = "nt"
plugin.subprocess.run = forbidden_run
try:
    try:
        plugin._run_plugin_init(pack)
    except RuntimeError as error:
        assert "unsupported" in str(error).lower(), error
    else:
        raise AssertionError("unsupported process-tree isolation must fail closed")
finally:
    plugin.os.name = real_name
    plugin.subprocess.run = real_run

assert not executed
assert not (home / "unsafe-init-ran").exists()
PY
    [ "$status" -eq 0 ]
}

@test "plugin init tree cleanup survives repeated interrupts before re-raising" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import signal
import subprocess
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
import plugin

class FakeProcess:
    pid = 424242
    returncode = None

    def poll(self):
        if killed:
            self.returncode = -signal.SIGKILL
        return self.returncode

    def wait(self, timeout):
        if not killed:
            raise subprocess.TimeoutExpired(["fixture"], timeout)
        self.returncode = -signal.SIGKILL
        return self.returncode

real_killpg = plugin.os.killpg
real_term_grace = plugin.PLUGIN_INIT_TERMINATE_GRACE_SECONDS
real_kill_grace = plugin.PLUGIN_INIT_KILL_GRACE_SECONDS
attempts = 0
probe_interrupts = 0
killed = False

def interrupted_killpg(process_group, signal_number):
    global attempts, probe_interrupts, killed
    assert process_group == FakeProcess.pid
    if signal_number == 0:
        if killed:
            raise ProcessLookupError
        probe_interrupts += 1
        if probe_interrupts <= 2:
            raise KeyboardInterrupt
        return
    attempts += 1
    if attempts <= 2:
        raise KeyboardInterrupt
    if signal_number == signal.SIGKILL:
        killed = True

plugin.os.killpg = interrupted_killpg
plugin.PLUGIN_INIT_TERMINATE_GRACE_SECONDS = 0.02
plugin.PLUGIN_INIT_KILL_GRACE_SECONDS = 0.02
try:
    try:
        plugin._terminate_plugin_init_tree(FakeProcess())
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError("cleanup must re-raise the deferred interrupt")
finally:
    plugin.os.killpg = real_killpg
    plugin.PLUGIN_INIT_TERMINATE_GRACE_SECONDS = real_term_grace
    plugin.PLUGIN_INIT_KILL_GRACE_SECONDS = real_kill_grace

assert killed, attempts
assert attempts >= 3, attempts
assert probe_interrupts >= 3, probe_interrupts
PY
    [ "$status" -eq 0 ]
}
