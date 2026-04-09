#!/usr/bin/env bats
# Tests for CLI flag validation and untested flags:
# --lang, --editors, --persona, --modules, --auto-detect, --status,
# --only/--skip invalid values

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_PROJECT="$(mktemp -d)"
    TMP_HOME="$(mktemp -d)"
    export HOME="$TMP_HOME"
    # Create a minimal git repo for --local tests
    git init "$TEST_PROJECT" >/dev/null 2>&1
}

teardown() {
    rm -rf "$TEST_PROJECT" "$TMP_HOME"
}

# ---------------------------------------------------------------------------
# --lang flag
# ---------------------------------------------------------------------------

@test "--lang python installs python language rules" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --lang python
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "python"
    [ -f "$TEST_PROJECT/.claude/CLAUDE.md" ]
    grep -q "python" "$TEST_PROJECT/.claude/CLAUDE.md"
}

@test "--lang typescript,python installs both language rules" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --lang typescript,python
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "typescript"
    echo "$output" | grep -qi "python"
}

@test "--lang=golang works with equals format" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --lang=golang --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "golang\|rules-golang"
}

@test "--lang go resolves alias to golang" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --lang go --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "golang\|rules-golang"
}

@test "--lang c# resolves alias to csharp" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" "--lang=c#" --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "csharp\|rules-csharp"
}

@test "--lang invalid exits non-zero" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --lang foobar --dry-run
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Unknown language"
}

@test "--lang with mixed valid and invalid exits non-zero" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --lang python,foobar --dry-run
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Unknown language.*foobar"
}

@test "--lang implies --local (project-specific)" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --lang python --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "project-local\|Project-local"
}

# ---------------------------------------------------------------------------
# --editors flag
# ---------------------------------------------------------------------------

@test "--editors cursor installs only cursor config" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --editors cursor
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "cursor"
    # Should have cursor config
    [ -f "$TEST_PROJECT/.cursorrules" ] || [ -d "$TEST_PROJECT/.cursor" ]
}

@test "--editors cursor,aider installs both" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --editors cursor,aider
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "cursor"
    echo "$output" | grep -qi "aider"
}

@test "--editors all installs all editors" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --editors all
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "copilot"
    echo "$output" | grep -qi "cursor"
    echo "$output" | grep -qi "aider"
}

@test "--editors=cursor works with equals format" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --editors=cursor --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "cursor"
}

@test "--editors invalid exits non-zero" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --editors foobar --dry-run
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Unknown editor"
}

@test "--editors with mixed valid and invalid exits non-zero" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --editors cursor,foobar --dry-run
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Unknown editor.*foobar"
}

# ---------------------------------------------------------------------------
# --only / --skip invalid values
# ---------------------------------------------------------------------------

@test "--only invalid component exits non-zero" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --only foobar --dry-run
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Unknown component in --only"
}

@test "--only with mixed valid and invalid exits non-zero" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --only agents,foobar --dry-run
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Unknown component in --only.*foobar"
}

@test "--skip invalid component exits non-zero" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --skip foobar --dry-run
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Unknown component in --skip"
}

@test "--skip=foobar with equals format exits non-zero" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --skip=foobar --dry-run
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Unknown component in --skip"
}

@test "--only all valid components passes" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --only agents,skills,hooks --dry-run
    [ "$status" -eq 0 ]
}

@test "--skip all valid components passes" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --skip hooks,rules --dry-run
    [ "$status" -eq 0 ]
}

# ---------------------------------------------------------------------------
# --persona flag
# ---------------------------------------------------------------------------

@test "--persona backend-lead is accepted" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --persona backend-lead --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "persona.*backend-lead"
}

@test "--persona=frontend-lead works with equals format" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --persona=frontend-lead --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "persona.*frontend-lead"
}

@test "--persona invalid exits non-zero" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --persona foobar
    [ "$status" -ne 0 ]
    echo "$output" | grep -q "Unknown persona"
}

# ---------------------------------------------------------------------------
# --modules flag
# ---------------------------------------------------------------------------

@test "--modules core,agents exits 0 in dry-run" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --modules core,agents --dry-run
    [ "$status" -eq 0 ]
}

@test "--modules=skills works with equals format" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --modules=skills --dry-run
    [ "$status" -eq 0 ]
}

@test "--modules unknown warns but does not fail" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --local --modules foobar --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "unknown module\|Warning"
}

# ---------------------------------------------------------------------------
# --auto-detect flag
# ---------------------------------------------------------------------------

@test "--auto-detect implies --local" {
    cd "$TEST_PROJECT"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --auto-detect --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "local\|project"
}

@test "--auto-detect detects languages from project files" {
    cd "$TEST_PROJECT"
    echo '{}' > "$TEST_PROJECT/package.json"
    run python3 "$TOOLKIT_DIR/scripts/install.py" --auto-detect --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "typescript\|detected"
}

# ---------------------------------------------------------------------------
# --status flag
# ---------------------------------------------------------------------------

@test "--status exits 0 with no state" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" --status
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "state\|install\|status"
}

@test "--status shows info after install" {
    python3 "$TOOLKIT_DIR/scripts/install.py" "$TMP_HOME" --only agents >/dev/null 2>&1
    run python3 "$TOOLKIT_DIR/scripts/install.py" --status
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi "Version\|Profile"
}

# ---------------------------------------------------------------------------
# Multiple validation errors at once
# ---------------------------------------------------------------------------

@test "multiple invalid flags report all errors" {
    run python3 "$TOOLKIT_DIR/scripts/install.py" "$TEST_PROJECT" --only foobar --skip bazqux --dry-run
    [ "$status" -ne 0 ]
    # Should report both errors
    echo "$output" | grep -q "Unknown component in --only.*foobar"
    echo "$output" | grep -q "Unknown component in --skip.*bazqux"
}
