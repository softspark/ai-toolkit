#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_HOME="$BATS_TEST_TMPDIR/home"
    mkdir -p "$TEST_HOME"
}

run_python() {
    run env -u CODEX_HOME -u COPILOT_HOME -u CLAUDE_USER_DATA_DIR \
        HOME="$TEST_HOME" SOFTSPARK_HOME="$TEST_HOME/.softspark" \
        AI_TOOLKIT_HOME="$TEST_HOME/.softspark/ai-toolkit" \
        PYTHONPATH="$TOOLKIT_DIR/scripts" python3 - "$TEST_HOME" "$TOOLKIT_DIR"
}

@test "endpoint resolver supports portable defaults without recursive or native expansion" {
    run_python <<'PY'
import os
from mcp_editors import resolve_endpoint_url

os.environ.pop("MCP_TEST_ENDPOINT", None)
default = "http://localhost:8082/mcp/sse"
expression = "${MCP_TEST_ENDPOINT:-" + default + "}"
assert resolve_endpoint_url(expression) == default
os.environ["MCP_TEST_ENDPOINT"] = ""
assert resolve_endpoint_url(expression) == default
os.environ["MCP_TEST_ENDPOINT"] = "https://custom.example/mcp"
assert resolve_endpoint_url(expression) == "https://custom.example/mcp"
assert resolve_endpoint_url("${MCP_TEST_ENDPOINT}") == "https://custom.example/mcp"
assert resolve_endpoint_url("${env:MCP_TEST_ENDPOINT}") == "${env:MCP_TEST_ENDPOINT}"
os.environ["MCP_TEST_ENDPOINT"] = "${MCP_TEST_NESTED:-secret}"
assert resolve_endpoint_url("${MCP_TEST_ENDPOINT}") == "${MCP_TEST_NESTED:-secret}"
assert resolve_endpoint_url(default) == default
PY
    [ "$status" -eq 0 ]
}

@test "missing portable endpoint variable fails without revealing endpoint credentials" {
    run_python <<'PY'
import os
from mcp_editors import resolve_endpoint_url

os.environ.pop("MCP_TEST_MISSING", None)
endpoint = "https://private-user:private-password@example.test/${MCP_TEST_MISSING}?token=private-token"
try:
    resolve_endpoint_url(endpoint)
except ValueError as error:
    message = str(error)
    assert "MCP_TEST_MISSING" in message, message
    for private in ("private-user", "private-password", "example.test", "private-token"):
        assert private not in message, message
else:
    raise AssertionError("missing endpoint variable must fail")
PY
    [ "$status" -eq 0 ]
}

@test "native adapters resolve endpoint fields without changing template or unrelated placeholders" {
    run_python <<'PY'
import copy
import json
import os
import sys
import tomllib
from pathlib import Path
from mcp_editors import install_servers, resolve_editor_path

home = Path(sys.argv[1])
os.environ.pop("MCP_TEST_ENDPOINT", None)
url = "http://localhost:8082/mcp/sse"
placeholder = "${MCP_TEST_ENDPOINT:-" + url + "}"
for editor, field in (("codex", "url"), ("cursor", "url"), ("antigravity", "serverUrl"), ("gemini", "httpUrl"), ("claude-app", "url")):
    servers = {"legal": {field: placeholder}}
    original = copy.deepcopy(servers)
    install_servers([editor], servers, scope="global", home=home)
    assert servers == original, editor
    path = resolve_editor_path(editor, "global", home=home)
    if editor == "codex":
        actual = tomllib.loads(path.read_text())["mcp_servers"]["legal"]
    else:
        actual = json.loads(path.read_text())["mcpServers"]["legal"]
    if editor == "claude-app":
        assert url in actual["args"], actual
    else:
        assert actual[field] == url, (editor, actual)
    before = path.read_bytes()
    install_servers([editor], servers, scope="global", home=home)
    assert path.read_bytes() == before, editor

servers = {
    "remote": {"url": placeholder, "headers": {"Authorization": "${MCP_TEST_TOKEN}"}},
    "local": {"command": "echo", "args": ["${MCP_TEST_ARG}"], "env": {"TOKEN": "${MCP_TEST_TOKEN}"}},
}
install_servers(["cursor"], servers, scope="global", home=home)
actual = json.loads((home / ".cursor/mcp.json").read_text())["mcpServers"]
assert actual["remote"]["headers"] == servers["remote"]["headers"]
assert actual["local"]["args"] == servers["local"]["args"]
assert actual["local"]["env"] == servers["local"]["env"]
install_servers(["claude", "codex"], {"legal": {"url": placeholder}}, scope="project", project_dir=home)
canonical = json.loads((home / ".mcp.json").read_text())
assert canonical["mcpServers"]["legal"]["url"] == placeholder
PY
    [ "$status" -eq 0 ]
}

@test "inject CLI repairs stale managed Codex endpoint and preserves canonical expression and comments" {
    run_python <<'PY'
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from mcp_editors import CODEX_MCP_BLOCK_START, CODEX_MCP_BLOCK_END

home, toolkit = map(Path, sys.argv[1:])
os.environ.pop("RAG_MCP_LEGAL_URL", None)
expression = "${RAG_MCP_LEGAL_URL:-http://localhost:8082/mcp/sse}"
template = home / "legal.json"
template.write_text(json.dumps({"mcpServers": {"rag-mcp-legal": {"type": "http", "url": expression}}}))
original = template.read_bytes()
config = home / ".codex/config.toml"
config.parent.mkdir()
prefix = '# user comment\npersonality = "pragmatic" # preserve inline comment\n'
config.write_text(prefix + CODEX_MCP_BLOCK_START + '\n[mcp_servers.rag-mcp-legal]\nurl = "' + expression + '"\n' + CODEX_MCP_BLOCK_END + '\n')
command = [sys.executable, str(toolkit / "scripts/inject_mcp_cli.py"), str(template), str(home)]
subprocess.run(command, check=True, capture_output=True, text=True)
assert config.read_text().startswith(prefix)
assert tomllib.loads(config.read_text())["mcp_servers"]["rag-mcp-legal"]["url"] == "http://localhost:8082/mcp/sse"
assert json.loads((home / ".mcp.json").read_text())["mcpServers"]["rag-mcp-legal"]["url"] == expression
assert template.read_bytes() == original
before = config.read_bytes()
subprocess.run(command, check=True, capture_output=True, text=True)
assert config.read_bytes() == before
PY
    [ "$status" -eq 0 ]
}

@test "refresh re-reads registered local template and repairs stale Codex URL without losing comments" {
    run_python <<'PY'
import json
import os
import sys
import tomllib
from pathlib import Path
from inject_mcp_cli import inject
from install_steps.markers import refresh_mcp_templates
from mcp_sources import register_path_source

home = Path(sys.argv[1])
os.environ.pop("RAG_MCP_LEGAL_URL", None)
template = home / "legal.json"
template.write_text(json.dumps({"mcpServers": {"rag-mcp-legal": {"url": "http://localhost:8082/mcp/sse"}}}))
inject(str(template), str(home))
config = home / ".codex/config.toml"
config.write_text('# keep me\n' + config.read_text().replace("http://localhost:8082/mcp/sse", "${RAG_MCP_LEGAL_URL:-http://localhost:8082/mcp/sse}"))
template.write_text(json.dumps({"mcpServers": {"rag-mcp-legal": {"url": "${RAG_MCP_LEGAL_URL:-http://localhost:9082/mcp/sse}"}}}))
register_path_source(None, "missing", home / "does-not-exist.json")
refresh_mcp_templates(str(home))
assert config.read_text().startswith('# keep me\n')
assert tomllib.loads(config.read_text())["mcp_servers"]["rag-mcp-legal"]["url"] == "http://localhost:9082/mcp/sse"
PY
    [ "$status" -eq 0 ]
    [[ "$output" == *Warning* || "$output" == *warning* ]]
    [[ "$output" == *missing* || "$output" == *does-not-exist* ]]
}

@test "OpenCode generation resolves endpoint and preserves canonical placeholders" {
    run_python <<'PY'
import json
import os
import subprocess
import sys
from pathlib import Path

home, toolkit = map(Path, sys.argv[1:])
os.environ.pop("MCP_TEST_ENDPOINT", None)
canonical = home / ".mcp.json"
canonical.write_text(json.dumps({"mcpServers": {"legal": {
    "type": "http", "url": "${MCP_TEST_ENDPOINT:-http://localhost:8082/mcp/sse}",
    "headers": {"Authorization": "${MCP_TEST_TOKEN}"},
}}}))
before = canonical.read_bytes()
command = [sys.executable, str(toolkit / "scripts/generate_opencode_json.py"), str(home)]
subprocess.run(command, check=True, capture_output=True, text=True)
actual = json.loads((home / "opencode.json").read_text())["mcp"]["legal"]
assert actual["url"] == "http://localhost:8082/mcp/sse", actual
assert actual["headers"]["Authorization"] == "${MCP_TEST_TOKEN}", actual
assert canonical.read_bytes() == before
PY
    [ "$status" -eq 0 ]
}

@test "global install CLI refreshes registered local MCP sources on update" {
    run_python <<'PY'
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from mcp_sources import register_path_source

home, toolkit = map(Path, sys.argv[1:])
template = home / "legal.json"
template.write_text(json.dumps({"mcpServers": {"legal": {"url": "http://localhost:8082/mcp/sse"}}}))
register_path_source(None, "legal", template)
command = [sys.executable, str(toolkit / "scripts/install.py"), str(home), "--only", "rules"]
subprocess.run(command, check=True, capture_output=True, text=True, cwd=home)
config = home / ".codex/config.toml"
assert tomllib.loads(config.read_text())["mcp_servers"]["legal"]["url"] == "http://localhost:8082/mcp/sse"
template.write_text(json.dumps({"mcpServers": {"legal": {"url": "http://localhost:9182/mcp/sse"}}}))
subprocess.run(command, check=True, capture_output=True, text=True, cwd=home)
assert tomllib.loads(config.read_text())["mcp_servers"]["legal"]["url"] == "http://localhost:9182/mcp/sse"
PY
    [ "$status" -eq 0 ]
}

@test "unresolved endpoint aborts native installation without changing any existing config" {
    run_python <<'PY'
import os
import sys
from pathlib import Path
from mcp_editors import install_servers

home = Path(sys.argv[1])
os.environ.pop("MCP_TEST_MISSING", None)
paths = [home / ".codex/config.toml", home / ".cursor/mcp.json"]
for path, content in zip(paths, ['# user comment\n[mcp_servers.user]\ncommand = "true"\n', '{"mcpServers":{"user":{"command":"true"}}}\n']):
    path.parent.mkdir()
    path.write_text(content)
before = [path.read_bytes() for path in paths]
try:
    install_servers(["cursor", "codex"], {"legal": {"url": "${MCP_TEST_MISSING}"}}, scope="global", home=home)
except ValueError:
    pass
else:
    raise AssertionError("missing endpoint must abort native installation")
assert [path.read_bytes() for path in paths] == before
PY
    [ "$status" -eq 0 ]
}

@test "local refresh preserves missing-source config and never forces source ownership conflicts" {
    run_python <<'PY'
import contextlib
import io
import json
import sys
from pathlib import Path
from install_steps.markers import refresh_mcp_templates
from mcp_sources import register_path_source

home = Path(sys.argv[1])
canonical = home / ".mcp.json"
data = {"mcpServers": {
    "legal": {"url": "https://user.example/mcp", "_source": "user-source"},
    "missing": {"url": "https://missing.example/mcp", "_source": "missing"},
}}
canonical.write_text(json.dumps(data))
template = home / "legal.json"
template.write_text(json.dumps({"mcpServers": {"legal": {"url": "http://localhost:8082/mcp/sse"}}}))
register_path_source(None, "missing", home / "does-not-exist.json")
register_path_source(None, "legal", template)
before = canonical.read_bytes()
output = io.StringIO()
with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
    try:
        refresh_mcp_templates(str(home))
    except SystemExit as error:
        assert error.code != 0
assert canonical.read_bytes() == before
assert "missing" in output.getvalue() or "does-not-exist" in output.getvalue(), output.getvalue()
PY
    [ "$status" -eq 0 ]
}
