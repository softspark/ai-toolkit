#!/usr/bin/env bats
# Tests for agent definitions correctness — single-pass validation

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
AGENTS_DIR="$TOOLKIT_DIR/app/agents"

@test "at least 40 agent files exist" {
    count=$(ls "$AGENTS_DIR"/*.md 2>/dev/null | wc -l)
    [ "$count" -ge 40 ]
}

@test "all agents pass structural validation (name, description, tools, format, length, filename match)" {
    errors=0
    for f in "$AGENTS_DIR"/*.md; do
        filename=$(basename "$f" .md)
        # Single awk: extract name, description, tools in one pass (no eval — safe from injection)
        fm_name=$(awk '/^---/{fc++; next} fc==1 && /^name:/{gsub(/^name:[[:space:]]*/,""); gsub(/^"/,""); gsub(/"$/,""); print; exit}' "$f")
        fm_desc=$(awk '/^---/{fc++; next} fc==1 && /^description:/{found=1} fc>=2{exit} END{if(found) print 1}' "$f")
        fm_tools=$(awk '/^---/{fc++; next} fc==1 && /^tools:/{found=1} fc>=2{exit} END{if(found) print 1}' "$f")

        if [ -z "${fm_name:-}" ]; then
            echo "MISSING name: $f"; errors=$((errors+1))
        else
            if echo "$fm_name" | grep -qE '[^a-z0-9-]'; then
                echo "INVALID name format: $fm_name in $f"; errors=$((errors+1))
            fi
            if [ "${#fm_name}" -gt 64 ]; then
                echo "NAME TOO LONG (${#fm_name} chars): $fm_name"; errors=$((errors+1))
            fi
            if [ "$filename" != "$fm_name" ]; then
                echo "MISMATCH: file=$filename name=$fm_name"; errors=$((errors+1))
            fi
        fi
        [ -z "${fm_desc:-}" ] && { echo "MISSING description: $f"; errors=$((errors+1)); }
        [ -z "${fm_tools:-}" ] && { echo "MISSING tools: $f"; errors=$((errors+1)); }
        unset fm_name fm_desc fm_tools
    done
    [ "$errors" -eq 0 ]
}

@test "AGENTS.md exists and is non-empty" {
    [ -f "$TOOLKIT_DIR/AGENTS.md" ]
    [ -s "$TOOLKIT_DIR/AGENTS.md" ]
}

@test "AGENTS.md contains all agent names" {
    agents_content=$(cat "$TOOLKIT_DIR/AGENTS.md")
    missing=0
    for f in "$AGENTS_DIR"/*.md; do
        name=$(basename "$f" .md)
        if ! echo "$agents_content" | grep -q "$name"; then
            echo "NOT IN AGENTS.md: $name"
            missing=$((missing+1))
        fi
    done
    [ "$missing" -eq 0 ]
}
