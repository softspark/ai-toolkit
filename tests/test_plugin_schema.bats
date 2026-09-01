#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Direct contract tests for scripts/plugin_schema.py.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

@test "plugin schema: rejects manifest missing requires" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from plugin_schema import validate_manifest

manifest = {
    "name": "example-pack",
    "description": "Example plugin pack.",
    "version": "1.0.0",
    "domain": "example",
    "type": "plugin-pack",
    "status": "experimental",
    "includes": {"agents": [], "skills": [], "rules": [], "hooks": []},
}
errors = validate_manifest(manifest)
assert "Missing required field: requires" in errors, errors
PY
    [ "$status" -eq 0 ]
}

@test "plugin schema: rejects requires with wrong type" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from plugin_schema import validate_manifest

manifest = {
    "name": "example-pack",
    "description": "Example plugin pack.",
    "version": "1.0.0",
    "domain": "example",
    "type": "plugin-pack",
    "status": "experimental",
    "requires": ["ai-toolkit"],
    "includes": {"agents": [], "skills": [], "rules": [], "hooks": []},
}
errors = validate_manifest(manifest)
assert "'requires' must be a non-empty dictionary" in errors, errors
PY
    [ "$status" -eq 0 ]
}

@test "plugin schema: rejects empty requires map" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from plugin_schema import validate_manifest

manifest = {
    "name": "example-pack",
    "description": "Example plugin pack.",
    "version": "1.0.0",
    "domain": "example",
    "type": "plugin-pack",
    "status": "experimental",
    "requires": {},
    "includes": {"agents": [], "skills": [], "rules": [], "hooks": []},
}
errors = validate_manifest(manifest)
assert "'requires' must be a non-empty dictionary" in errors, errors
PY
    [ "$status" -eq 0 ]
}

@test "plugin schema: rejects non-string and empty requires constraints" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from plugin_schema import validate_manifest

manifest = {
    "name": "example-pack",
    "description": "Example plugin pack.",
    "version": "1.0.0",
    "domain": "example",
    "type": "plugin-pack",
    "status": "experimental",
    "requires": {"ai-toolkit": 1, "claude-code": " "},
    "includes": {"agents": [], "skills": [], "rules": [], "hooks": []},
}
errors = validate_manifest(manifest)
assert "requires.ai-toolkit must be a non-empty string" in errors, errors
assert "requires.claude-code must be a non-empty string" in errors, errors
PY
    [ "$status" -eq 0 ]
}

@test "plugin schema: validates includes.mcp type names and template existence" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from plugin_schema import validate_manifest

base = {
    "name": "example-pack",
    "description": "Example plugin pack.",
    "version": "1.0.0",
    "domain": "example",
    "type": "plugin-pack",
    "status": "experimental",
    "requires": {"ai-toolkit": ">=1.0.0"},
    "includes": {"agents": [], "skills": [], "rules": [], "hooks": []},
}

unsafe_name = json.loads(json.dumps(base))
unsafe_name["name"] = "../unsafe-name"
assert "name must be a safe lowercase-hyphen identifier" in validate_manifest(unsafe_name)

wrong_type = json.loads(json.dumps(base))
wrong_type["includes"]["mcp"] = "rag-mcp"
assert "includes.mcp must be a list" in validate_manifest(wrong_type)

with tempfile.TemporaryDirectory() as tmp:
    pack = Path(tmp) / "example-pack"
    (pack / "mcp").mkdir(parents=True)

    invalid = json.loads(json.dumps(base))
    invalid["includes"]["mcp"] = [42, "../unsafe", "missing-template"]
    errors = validate_manifest(invalid, pack)
    assert "includes.mcp entries must be safe lowercase-hyphen names" in errors, errors
    assert "MCP template not found: missing-template" in errors, errors

    (pack / "mcp" / "local-template.json").write_text(
        json.dumps({
            "name": "different-name",
            "mcpServers": {"local-template": {"command": "fixture"}},
        }),
        encoding="utf-8",
    )
    mismatch = json.loads(json.dumps(base))
    mismatch["includes"]["mcp"] = ["local-template"]
    errors = validate_manifest(mismatch, pack)
    assert "MCP template name mismatch: local-template" in errors, errors

    (pack / "mcp" / "local-template.json").write_text(
        json.dumps({
            "name": "local-template",
            "mcpServers": {"local-template": {"command": "fixture"}},
        }),
        encoding="utf-8",
    )
    assert validate_manifest(mismatch, pack) == [], validate_manifest(mismatch, pack)
PY
    [ "$status" -eq 0 ]
}

@test "plugin schema enforces runtime MCP shape symlink and localhost warning parity" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from plugin_schema import validate_manifest

manifest = {
    "name": "example-pack",
    "description": "Example plugin pack.",
    "version": "1.0.0",
    "domain": "example",
    "type": "plugin-pack",
    "status": "experimental",
    "requires": {"ai-toolkit": ">=1.0.0"},
    "includes": {
        "agents": [],
        "skills": [],
        "rules": [],
        "hooks": [],
        "mcp": ["local-template"],
    },
}

with tempfile.TemporaryDirectory() as tmp:
    pack = Path(tmp) / "example-pack"
    templates = pack / "mcp"
    templates.mkdir(parents=True)
    template_path = templates / "local-template.json"

    template_path.write_text(
        json.dumps({"name": "local-template", "mcpServers": {}}),
        encoding="utf-8",
    )
    errors = validate_manifest(manifest, pack)
    assert "MCP template requires non-empty mcpServers: local-template" in errors, errors

    template_path.write_text(
        json.dumps({"name": "local-template", "mcpServers": {"local-template": []}}),
        encoding="utf-8",
    )
    errors = validate_manifest(manifest, pack)
    assert "MCP template has invalid server entries: local-template" in errors, errors

    template_path.write_text(
        json.dumps({
            "name": "local-template",
            "mcpServers": {
                "local-template": {
                    "type": "http",
                    "url": "http://localhost:9999/mcp/sse",
                },
            },
        }),
        encoding="utf-8",
    )
    errors = validate_manifest(manifest, pack)
    expected = "Local HTTP MCP template must warn that access is unauthenticated: local-template"
    assert expected in errors, errors

    real_template = Path(tmp) / "real-template.json"
    real_template.write_text(
        json.dumps({
            "name": "local-template",
            "mcpServers": {"local-template": {"command": "fixture"}},
        }),
        encoding="utf-8",
    )
    template_path.unlink()
    template_path.symlink_to(real_template)
    errors = validate_manifest(manifest, pack)
    assert "MCP template must not be symlinked: local-template" in errors, errors
PY
    [ "$status" -eq 0 ]
}
