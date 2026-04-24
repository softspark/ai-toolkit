#!/usr/bin/env bats
# Dedicated language-rule contract tests.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
RULES_DIR="$TOOLKIT_DIR/app/rules"

@test "rules: every rule file has required frontmatter fields" {
    while IFS= read -r file; do
        head -1 "$file" | grep -q '^---$' || { echo "Missing frontmatter: $file" >&2; return 1; }
        grep -q '^language:' "$file" || { echo "Missing language: $file" >&2; return 1; }
        grep -q '^category:' "$file" || { echo "Missing category: $file" >&2; return 1; }
        grep -q '^version:' "$file" || { echo "Missing version: $file" >&2; return 1; }
    done < <(find "$RULES_DIR" -mindepth 2 -maxdepth 2 -type f -name '*.md' | sort)
}

@test "rules: language directories expose the required categories" {
    for dir in "$RULES_DIR"/*; do
        [ -d "$dir" ] || continue
        name="${dir##*/}"
        if [ "$name" = "common" ]; then
            required=(coding-style testing security performance git-workflow)
        else
            required=(coding-style testing security patterns frameworks)
        fi
        for category in "${required[@]}"; do
            [ -f "$dir/$category.md" ] || {
                echo "Missing $category.md in $name" >&2
                return 1
            }
        done
    done
}

@test "rules: validate.py includes rule format validation" {
    run python3 "$TOOLKIT_DIR/scripts/validate.py" "$TOOLKIT_DIR"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "## Language Rules"
    echo "$output" | grep -q "rule files validated"
}
