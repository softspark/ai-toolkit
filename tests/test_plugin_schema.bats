#!/usr/bin/env bats
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
