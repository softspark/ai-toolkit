#!/usr/bin/env bats
# Tests for skill and agent frontmatter correctness — optimized single-pass loops
# Agent structural tests (name, description, tools, format) are in test_agents.bats.
# This file focuses on: skill validation, tool whitelist, depends-on, and dirname matching.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
AGENTS_DIR="$TOOLKIT_DIR/app/agents"
SKILLS_DIR="$TOOLKIT_DIR/app/skills"

@test "at least 50 skills exist" {
    count=$(find "$SKILLS_DIR" -maxdepth 1 -mindepth 1 -type d -not -name '_*' | wc -l | xargs)
    [ "$count" -ge 50 ]
}

@test "all skills pass structural validation (name, description, length, dirname match)" {
    errors=0
    for skill_dir in "$SKILLS_DIR"/*/; do
        # Skip internal directories (e.g., _lib/)
        case "$(basename "$skill_dir")" in _*) continue ;; esac
        skill_file="$skill_dir/SKILL.md"
        if [ ! -f "$skill_file" ]; then
            echo "MISSING SKILL.md: $skill_dir"; errors=$((errors+1))
            continue
        fi
        dirname=$(basename "$skill_dir")
        # Safe extraction without eval
        fm_name=$(awk '/^---/{fc++; next} fc==1 && /^name:/{gsub(/^name:[[:space:]]*/,""); gsub(/^"/,""); gsub(/"$/,""); print; exit}' "$skill_file")
        fm_desc=$(awk '/^---/{fc++; next} fc==1 && /^description:/{found=1} fc>=2{exit} END{if(found) print 1}' "$skill_file")

        if [ -z "${fm_name:-}" ]; then
            echo "MISSING name: $skill_file"; errors=$((errors+1))
        else
            if [ "${#fm_name}" -gt 64 ]; then
                echo "NAME TOO LONG (${#fm_name} chars): $fm_name"; errors=$((errors+1))
            fi
            if [ "$fm_name" != "$dirname" ]; then
                echo "MISMATCH: dir=$dirname name=$fm_name in $skill_file"; errors=$((errors+1))
            fi
        fi
        [ -z "${fm_desc:-}" ] && { echo "MISSING description: $skill_file"; errors=$((errors+1)); }
        unset fm_name fm_desc
    done
    [ "$errors" -eq 0 ]
}

@test "no deprecated fields and correct context:fork usage in skills" {
    errors=0
    for skill_dir in "$SKILLS_DIR"/*/; do
        skill_file="$skill_dir/SKILL.md"
        [ -f "$skill_file" ] || continue
        # Safe extraction without eval
        fm=$(awk 'NR==1{next} /^---$/{exit} {print}' "$skill_file")
        has_delegate=$(echo "$fm" | grep -c '^delegate-agent:' || true)
        has_runmode=$(echo "$fm" | grep -c '^run-mode:' || true)
        has_fork=$(echo "$fm" | grep -c '^context: *fork' || true)
        has_agent=$(echo "$fm" | grep -c '^agent:' || true)

        [ "$has_delegate" -gt 0 ] && { echo "DEPRECATED delegate-agent in $skill_file"; errors=$((errors+1)); }
        [ "$has_runmode" -gt 0 ] && { echo "DEPRECATED run-mode in $skill_file"; errors=$((errors+1)); }
        [ "$has_fork" -gt 0 ] && [ "$has_agent" -eq 0 ] && { echo "MISSING agent: in $skill_file (has context: fork)"; errors=$((errors+1)); }
    done
    [ "$errors" -eq 0 ]
}

@test "all depends-on references resolve to existing skills" {
    broken=0
    for skill_dir in "$SKILLS_DIR"/*/; do
        skill_file="$skill_dir/SKILL.md"
        [ -f "$skill_file" ] || continue
        dep_line=$(awk 'NR==1{next} /^---$/{exit} /^depends-on:/{gsub(/^depends-on:[[:space:]]*/,""); print; exit}' "$skill_file")
        [ -z "$dep_line" ] && continue
        for dep in $(echo "$dep_line" | tr ',' '\n' | tr -d ' '); do
            [ -z "$dep" ] && continue
            [ ! -f "$SKILLS_DIR/$dep/SKILL.md" ] && { echo "BROKEN depends-on: $dep in $skill_file"; broken=$((broken+1)); }
        done
    done
    [ "$broken" -eq 0 ]
}

@test "agent tool names are valid Claude Code tools" {
    VALID_TOOLS="Read Write Edit Bash Grep Glob Agent WebSearch WebFetch TodoRead TodoWrite TeamCreate TeamDelete SendMessage TaskCreate TaskList TaskUpdate TaskGet TaskOutput TaskStop NotebookEdit ExitPlanMode EnterPlanMode ExitWorktree EnterWorktree RemoteTrigger"
    invalid=0
    for f in "$AGENTS_DIR"/*.md; do
        [ -f "$f" ] || continue
        tools=$(awk '/^---/{fc++; next} fc==1 && /^tools:/{gsub(/^tools:[[:space:]]*/,""); print; exit}' "$f")
        [ -z "$tools" ] && continue
        for tool in $(echo "$tools" | tr ',' '\n' | tr -d ' '); do
            [ -z "$tool" ] && continue
            echo " $VALID_TOOLS " | grep -q " $tool " || { echo "INVALID tool '$tool' in $f"; invalid=$((invalid+1)); }
        done
    done
    [ "$invalid" -eq 0 ]
}
