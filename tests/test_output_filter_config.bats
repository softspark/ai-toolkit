#!/usr/bin/env bats
# Configuration contract tests for the native tool-output filter.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

@test "output filter default policy is disabled and bounded" {
    run python3 - "$TOOLKIT_DIR/app/output-filter-policy.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    policy = json.load(handle)

assert policy == {
    "mode": "off",
    "profiles": ["repeat-lines", "tap-success"],
    "maxInputBytes": 8_388_608,
    "minSavingsBytes": 1_024,
    "minSavingsRatio": 0.15,
    "recovery": {
        "mode": "ephemeral",
        "ttlMinutes": 60,
        "maxSessionBytes": 33_554_432,
    },
}
PY

    [ "$status" -eq 0 ]
}

@test "config JSON Schema declares the bounded toolOutputFilter contract" {
    run python3 - "$TOOLKIT_DIR/scripts/schemas/ai-toolkit-config.schema.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    schema = json.load(handle)

field = schema["properties"]["toolOutputFilter"]
assert field["type"] == "object"
assert field["additionalProperties"] is False
properties = field["properties"]
assert properties["mode"]["enum"] == ["off", "observe", "safe"]
assert properties["profiles"]["items"]["enum"] == ["repeat-lines", "tap-success"]
assert properties["maxInputBytes"]["maximum"] == 8_388_608
assert properties["minSavingsBytes"]["minimum"] == 0
assert properties["minSavingsRatio"]["minimum"] == 0
assert properties["minSavingsRatio"]["maximum"] == 1
recovery = properties["recovery"]
assert recovery["type"] == "object"
assert recovery["additionalProperties"] is False
assert recovery["properties"]["mode"]["enum"] == ["ephemeral"]
assert recovery["properties"]["ttlMinutes"]["minimum"] == 1
assert recovery["properties"]["maxSessionBytes"]["minimum"] == 1
PY

    [ "$status" -eq 0 ]
}

@test "config validator rejects an unknown output filter mode" {
    config="$BATS_TEST_TMPDIR/invalid-output-filter.json"
    cat > "$config" <<'EOF'
{
  "toolOutputFilter": {
    "mode": "aggressive"
  }
}
EOF

    run python3 "$TOOLKIT_DIR/scripts/config_validator.py" "$config" --strict

    [ "$status" -eq 1 ]
    [[ "$output" == *"toolOutputFilter.mode"* ]]
}

@test "config validator rejects unknown output filter keys" {
    config="$BATS_TEST_TMPDIR/unknown-output-filter-key.json"
    cat > "$config" <<'EOF'
{
  "toolOutputFilter": {
    "mode": "off",
    "rewriteCommands": true
  }
}
EOF

    run python3 "$TOOLKIT_DIR/scripts/config_validator.py" "$config" --strict

    [ "$status" -eq 1 ]
    [[ "$output" == *"rewriteCommands"* ]]
}

@test "config validator rejects unbounded output filter values" {
    config="$BATS_TEST_TMPDIR/unbounded-output-filter.json"
    cat > "$config" <<'EOF'
{
  "toolOutputFilter": {
    "mode": "safe",
    "profiles": ["repeat-lines", "unknown"],
    "maxInputBytes": 8388609,
    "minSavingsBytes": -1,
    "minSavingsRatio": 1.01,
    "recovery": {
      "mode": "persistent",
      "ttlMinutes": 0,
      "maxSessionBytes": 0,
      "path": "/tmp/raw"
    }
  }
}
EOF

    run python3 "$TOOLKIT_DIR/scripts/config_validator.py" "$config" --strict

    [ "$status" -eq 1 ]
    [[ "$output" == *"toolOutputFilter.profiles"* ]]
    [[ "$output" == *"toolOutputFilter.maxInputBytes"* ]]
    [[ "$output" == *"toolOutputFilter.minSavingsBytes"* ]]
    [[ "$output" == *"toolOutputFilter.minSavingsRatio"* ]]
    [[ "$output" == *"toolOutputFilter.recovery.mode"* ]]
    [[ "$output" == *"toolOutputFilter.recovery.ttlMinutes"* ]]
    [[ "$output" == *"toolOutputFilter.recovery.maxSessionBytes"* ]]
    [[ "$output" == *"toolOutputFilter.recovery"* ]]
    [[ "$output" == *"path"* ]]
}

@test "config validator rejects savings threshold above input limit" {
    config="$BATS_TEST_TMPDIR/inconsistent-output-filter-limits.json"
    cat > "$config" <<'EOF'
{
  "toolOutputFilter": {
    "mode": "safe",
    "maxInputBytes": 100,
    "minSavingsBytes": 1024
  }
}
EOF

    run python3 "$TOOLKIT_DIR/scripts/config_validator.py" "$config" --strict

    [ "$status" -eq 1 ]
    [[ "$output" == *"toolOutputFilter.minSavingsBytes"* ]]
    [[ "$output" == *"must not exceed"* ]]
    [[ "$output" == *"toolOutputFilter.maxInputBytes"* ]]
}

@test "config validator applies the default savings threshold to partial limits" {
    config="$BATS_TEST_TMPDIR/partial-output-filter-limits.json"
    cat > "$config" <<'EOF'
{
  "toolOutputFilter": {
    "mode": "safe",
    "maxInputBytes": 100
  }
}
EOF

    run python3 "$TOOLKIT_DIR/scripts/config_validator.py" "$config" --strict

    [ "$status" -eq 1 ]
    [[ "$output" == *"toolOutputFilter.minSavingsBytes"* ]]
    [[ "$output" == *"toolOutputFilter.maxInputBytes"* ]]
}

@test "config validator rejects duplicate output filter profiles" {
    config="$BATS_TEST_TMPDIR/duplicate-output-filter-profiles.json"
    cat > "$config" <<'EOF'
{
  "toolOutputFilter": {
    "mode": "safe",
    "profiles": ["repeat-lines", "repeat-lines"]
  }
}
EOF

    run python3 "$TOOLKIT_DIR/scripts/config_validator.py" "$config" --strict

    [ "$status" -eq 1 ]
    [[ "$output" == *"toolOutputFilter.profiles"* ]]
    [[ "$output" == *"duplicate"* ]]
}

@test "config merge materializes a complete effective output filter policy" {
    base="$BATS_TEST_TMPDIR/base.json"
    project="$BATS_TEST_TMPDIR/project.json"
    printf '{}\n' > "$base"
    cat > "$project" <<'EOF'
{
  "toolOutputFilter": {
    "mode": "observe",
    "minSavingsBytes": 2048
  }
}
EOF

    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" "$base" "$project"

    [ "$status" -eq 0 ]
    echo "$output" | python3 -c '
import json
import sys

policy = json.load(sys.stdin)["merged"]["toolOutputFilter"]
assert policy == {
    "mode": "observe",
    "profiles": ["repeat-lines", "tap-success"],
    "maxInputBytes": 8_388_608,
    "minSavingsBytes": 2_048,
    "minSavingsRatio": 0.15,
    "recovery": {
        "mode": "ephemeral",
        "ttlMinutes": 60,
        "maxSessionBytes": 33_554_432,
    },
}
'
}

@test "hook installer copies the output filter policy and Python package" {
    hooks_dir="$BATS_TEST_TMPDIR/hooks"
    scripts_dir="$BATS_TEST_TMPDIR/scripts"
    mkdir -p "$hooks_dir" "$scripts_dir"

    run python3 - "$TOOLKIT_DIR" "$hooks_dir" "$scripts_dir" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "scripts"))
from install_steps.hooks import _copy_hook_runtime_scripts, _copy_hook_scripts

hooks_dir = Path(sys.argv[2])
scripts_dir = Path(sys.argv[3])
_copy_hook_scripts(Path("/unused"), hooks_dir)
_copy_hook_runtime_scripts(scripts_dir)

assert (hooks_dir / "filter-tool-output.sh").is_file()
assert (hooks_dir / "output-filter-policy.json").is_file()
assert (scripts_dir / "output_filter_cli.py").is_file()
assert (scripts_dir / "output_filter_hook.py").is_file()
assert (scripts_dir / "tool_output_filter" / "__init__.py").is_file()
assert (scripts_dir / "tool_output_filter" / "engine.py").is_file()
assert not (scripts_dir / "tool_output_filter" / "__pycache__").exists()
PY

    [ "$status" -eq 0 ]
}

@test "hook installer preserves an existing global policy and prunes stale runtime modules" {
    hooks_dir="$BATS_TEST_TMPDIR/preserve-hooks"
    scripts_dir="$BATS_TEST_TMPDIR/preserve-scripts"
    mkdir -p "$hooks_dir" "$scripts_dir/tool_output_filter"
    printf '{"mode":"safe","profiles":["repeat-lines"]}\n' \
        > "$hooks_dir/output-filter-policy.json"
    printf 'stale = True\n' > "$scripts_dir/tool_output_filter/removed_module.py"

    run python3 - "$TOOLKIT_DIR" "$hooks_dir" "$scripts_dir" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "scripts"))
from install_steps.hooks import _copy_hook_runtime_scripts, _copy_hook_scripts

hooks_dir = Path(sys.argv[2])
scripts_dir = Path(sys.argv[3])
_copy_hook_scripts(Path("/unused"), hooks_dir)
_copy_hook_runtime_scripts(scripts_dir)

policy = (hooks_dir / "output-filter-policy.json").read_text(encoding="utf-8")
assert '"mode":"safe"' in policy.replace(" ", ""), policy
assert not (scripts_dir / "tool_output_filter" / "removed_module.py").exists()
assert (scripts_dir / "tool_output_filter" / "engine.py").is_file()
PY

    [ "$status" -eq 0 ]
}

@test "config merge rejects disabling an inherited required plugin" {
    base="$BATS_TEST_TMPDIR/required-plugin-base.json"
    project="$BATS_TEST_TMPDIR/required-plugin-project.json"
    cat > "$base" <<'EOF'
{
  "enforce": {
    "requiredPlugins": ["security-pack"]
  }
}
EOF
    cat > "$project" <<'EOF'
{
  "plugins": {
    "disabled": ["security-pack"]
  }
}
EOF

    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" "$base" "$project"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Cannot disable plugin 'security-pack'"* ]]
}

@test "config merge materializes inherited required plugins as enabled intent" {
    base="$BATS_TEST_TMPDIR/materialized-plugin-base.json"
    project="$BATS_TEST_TMPDIR/materialized-plugin-project.json"
    cat > "$base" <<'EOF'
{
  "enforce": {
    "requiredPlugins": ["security-pack", "policy-pack"]
  }
}
EOF
    printf '{}\n' > "$project"

    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" "$base" "$project"

    [ "$status" -eq 0 ]
    echo "$output" | python3 -c '
import json
import sys
plugins = json.load(sys.stdin)["merged"]["plugins"]
assert plugins == {
    "enabled": ["policy-pack", "security-pack"],
    "disabled": [],
}
'
}

@test "config validator rejects malformed plugin intent" {
    config="$BATS_TEST_TMPDIR/malformed-plugins.json"
    cat > "$config" <<'EOF'
{
  "plugins": {
    "enabled": ["security-pack", 42],
    "disabled": "policy-pack",
    "required": ["not-a-supported-key"]
  }
}
EOF

    run python3 "$TOOLKIT_DIR/scripts/config_validator.py" "$config" --strict

    [ "$status" -eq 1 ]
    [[ "$output" == *"plugins.enabled"* ]]
    [[ "$output" == *"plugins.disabled"* ]]
    [[ "$output" == *"required"* ]]
}

@test "config validator rejects ambiguous and empty plugin intent" {
    config="$BATS_TEST_TMPDIR/ambiguous-plugins.json"
    cat > "$config" <<'EOF'
{
  "plugins": {
    "enabled": ["security-pack", "security-pack", ""],
    "disabled": ["security-pack"]
  },
  "enforce": {
    "requiredPlugins": ["", ""]
  }
}
EOF

    run python3 "$TOOLKIT_DIR/scripts/config_validator.py" "$config" --strict

    [ "$status" -eq 1 ]
    [[ "$output" == *"non-empty strings"* ]]
    [[ "$output" == *"both enabled and disabled"* ]]
}

@test "config merger rejects malformed plugin arrays without partial intent" {
    base="$BATS_TEST_TMPDIR/malformed-plugin-base.json"
    project="$BATS_TEST_TMPDIR/malformed-plugin-project.json"
    printf '{}\n' > "$base"
    cat > "$project" <<'EOF'
{
  "plugins": {
    "enabled": "security-pack"
  }
}
EOF

    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" "$base" "$project"

    [ "$status" -eq 1 ]
    [[ "$output" == *"project plugins.enabled"* ]]
    [[ "$output" == *"non-empty strings"* ]]
}

@test "config JSON Schema declares plugin enable and disable intent" {
    run python3 - "$TOOLKIT_DIR/scripts/schemas/ai-toolkit-config.schema.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    schema = json.load(handle)

plugins = schema["properties"]["plugins"]
assert plugins["type"] == "object"
assert plugins["additionalProperties"] is False
assert set(plugins["properties"]) == {"enabled", "disabled"}
for key in ("enabled", "disabled"):
    assert plugins["properties"][key]["type"] == "array"
    assert plugins["properties"][key]["items"] == {
        "type": "string",
        "minLength": 1,
    }
    assert plugins["properties"][key]["uniqueItems"] is True
required = schema["properties"]["enforce"]["properties"]["requiredPlugins"]
assert required["items"] == {"type": "string", "minLength": 1}
assert required["uniqueItems"] is True
PY

    [ "$status" -eq 0 ]
}

@test "merged config validation fails when a required plugin is not enabled" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "scripts"))
from config_validator import validate_merged_config

errors = validate_merged_config(
    {"plugins": {"enabled": ["policy-pack"]}},
    {"enforce": {"requiredPlugins": ["policy-pack", "security-pack"]}},
)
assert errors == ["Required plugins missing from enabled intent: security-pack."]
PY

    [ "$status" -eq 0 ]
}

@test "constitution Article VII is reserved and custom amendments start at VIII" {
    base="$BATS_TEST_TMPDIR/constitution-base.json"
    project="$BATS_TEST_TMPDIR/constitution-project.json"
    printf '{}\n' > "$base"
    cat > "$project" <<'EOF'
{
  "constitution": {
    "amendments": [
      {
        "article": 7,
        "title": "Replacement",
        "text": "Attempt to replace epistemic integrity."
      }
    ]
  }
}
EOF

    run python3 "$TOOLKIT_DIR/scripts/config_merger.py" "$base" "$project"

    [ "$status" -eq 1 ]
    [[ "$output" == *"Cannot modify Constitution Article 7"* ]]
    [[ "$output" == *"Articles I-VII"* ]]
    [[ "$output" == *"article 8+"* ]]
}

@test "config validator rejects amendments to core Articles I through VII" {
    config="$BATS_TEST_TMPDIR/core-article.json"
    cat > "$config" <<'EOF'
{
  "constitution": {
    "amendments": [
      {
        "article": 7,
        "title": "Replacement",
        "text": "Attempt to replace epistemic integrity."
      }
    ]
  }
}
EOF

    run python3 "$TOOLKIT_DIR/scripts/config_validator.py" "$config" --strict

    [ "$status" -eq 1 ]
    [[ "$output" == *"Article 7"* ]]
    [[ "$output" == *"reserved"* ]]
    [[ "$output" == *"8+"* ]]
}

@test "local install materializes independent output filter policies per project" {
    first="$BATS_TEST_TMPDIR/first-project"
    second="$BATS_TEST_TMPDIR/second-project"
    mkdir -p "$first/.claude" "$second/.claude"

    run python3 - "$TOOLKIT_DIR" "$first" "$second" <<'PY'
import json
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1])
first = Path(sys.argv[2])
second = Path(sys.argv[3])
sys.path.insert(0, str(root / "scripts"))
from install_steps.ai_tools import _sync_local_output_filter_policy

_sync_local_output_filter_policy(first, {
    "mode": "observe",
    "profiles": ["repeat-lines"],
})
_sync_local_output_filter_policy(second, {
    "mode": "safe",
    "profiles": ["tap-success"],
    "minSavingsBytes": 4096,
})

first_policy_path = first / ".claude" / "ai-toolkit-output-filter.json"
second_policy_path = second / ".claude" / "ai-toolkit-output-filter.json"
with open(first_policy_path, encoding="utf-8") as handle:
    first_policy = json.load(handle)
with open(second_policy_path, encoding="utf-8") as handle:
    second_policy = json.load(handle)

assert first_policy["mode"] == "observe"
assert first_policy["profiles"] == ["repeat-lines"]
assert first_policy["minSavingsBytes"] == 1024
assert second_policy["mode"] == "safe"
assert second_policy["profiles"] == ["tap-success"]
assert second_policy["minSavingsBytes"] == 4096
assert stat.S_IMODE(first_policy_path.stat().st_mode) == 0o600
assert stat.S_IMODE(second_policy_path.stat().st_mode) == 0o600
assert first_policy_path.read_bytes() != second_policy_path.read_bytes()
PY

    [ "$status" -eq 0 ]
}

@test "local policy sync preserves the last valid policy when new config is invalid" {
    project="$BATS_TEST_TMPDIR/invalid-policy-project"
    mkdir -p "$project/.claude"

    run python3 - "$TOOLKIT_DIR" "$project" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
project = Path(sys.argv[2])
sys.path.insert(0, str(root / "scripts"))
from install_steps.ai_tools import _sync_local_output_filter_policy

_sync_local_output_filter_policy(project, {"mode": "observe"})
policy_path = project / ".claude" / "ai-toolkit-output-filter.json"
before = policy_path.read_bytes()
_sync_local_output_filter_policy(project, {"mode": "invalid"})
assert policy_path.read_bytes() == before
_sync_local_output_filter_policy(project, {"recovery": [["invalid"]]})
assert policy_path.read_bytes() == before
PY

    [ "$status" -eq 0 ]
    [ "$(printf '%s\n' "$output" | grep -c "policy not changed")" -eq 2 ]
}

@test "local policy cleanup removes only toolkit-owned policy files" {
    managed="$BATS_TEST_TMPDIR/managed-project"
    user_owned="$BATS_TEST_TMPDIR/user-project"
    mkdir -p "$managed/.claude" "$user_owned/.claude"
    printf '{"mode":"safe"}\n' \
        > "$user_owned/.claude/ai-toolkit-output-filter.json"

    run python3 - "$TOOLKIT_DIR" "$managed" "$user_owned" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
managed = Path(sys.argv[2])
user_owned = Path(sys.argv[3])
sys.path.insert(0, str(root / "scripts"))
from install_steps.ai_tools import _sync_local_output_filter_policy

_sync_local_output_filter_policy(managed, {"mode": "observe"})
_sync_local_output_filter_policy(managed, None)
_sync_local_output_filter_policy(user_owned, None)

assert not (managed / ".claude" / "ai-toolkit-output-filter.json").exists()
assert not (managed / ".claude" / ".ai-toolkit-output-filter.owner").exists()
assert (
    user_owned / ".claude" / "ai-toolkit-output-filter.json"
).read_text(encoding="utf-8") == '{"mode":"safe"}\n'
assert not (
    user_owned / ".claude" / ".ai-toolkit-output-filter.owner"
).exists()
PY

    [ "$status" -eq 0 ]
    [[ "$output" == *"Kept: user-owned"* ]]
}

@test "install local writes the effective project output filter policy" {
    project="$BATS_TEST_TMPDIR/install-project"
    toolkit_home="$BATS_TEST_TMPDIR/toolkit-home"
    mkdir -p "$project" "$toolkit_home"
    cat > "$project/.softspark-toolkit.json" <<'EOF'
{
  "toolOutputFilter": {
    "mode": "observe",
    "minSavingsBytes": 2048
  }
}
EOF

    run env AI_TOOLKIT_HOME="$toolkit_home" \
        bash -c "cd \"\$1\" && python3 \"\$2/scripts/install.py\" --local --skip agents,skills,hooks" \
        _ "$project" "$TOOLKIT_DIR"

    [ "$status" -eq 0 ]
    policy="$project/.claude/ai-toolkit-output-filter.json"
    owner="$project/.claude/.ai-toolkit-output-filter.owner"
    [ -f "$policy" ]
    [ "$(cat "$owner")" = "ai-toolkit-output-filter-policy-v1" ]
    python3 - "$policy" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    policy = json.load(handle)
assert policy["mode"] == "observe"
assert policy["minSavingsBytes"] == 2048
assert policy["maxInputBytes"] == 8_388_608
assert policy["recovery"]["ttlMinutes"] == 60
PY
}

@test "install local dry-run reports project output filter materialization" {
    project="$BATS_TEST_TMPDIR/dry-run-project"
    toolkit_home="$BATS_TEST_TMPDIR/dry-run-home"
    mkdir -p "$project" "$toolkit_home"
    cat > "$project/.softspark-toolkit.json" <<'EOF'
{"toolOutputFilter":{"mode":"observe"}}
EOF

    run env AI_TOOLKIT_HOME="$toolkit_home" \
        bash -c "cd \"\$1\" && python3 \"\$2/scripts/install.py\" --local --dry-run --skip agents,skills,hooks" \
        _ "$project" "$TOOLKIT_DIR"

    [ "$status" -eq 0 ]
    [[ "$output" == *"Would write: .claude/ai-toolkit-output-filter.json"* ]]
    [ ! -e "$project/.claude/ai-toolkit-output-filter.json" ]
}

@test "config validator enforces top-level JSON Schema fields" {
    config="$BATS_TEST_TMPDIR/unknown-top-level.json"
    cat > "$config" <<'EOF'
{
  "profile": "standard",
  "toolOutputRewrite": {
    "mode": "safe"
  }
}
EOF

    run python3 "$TOOLKIT_DIR/scripts/config_validator.py" "$config" --strict

    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown top-level config keys"* ]]
    [[ "$output" == *"toolOutputRewrite"* ]]
}
