#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# KB document frontmatter validation tests
# Single-pass validation: one find, one awk per file, all checks at once.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
KB_DIR="$TOOLKIT_DIR/kb"

@test "at least 15 KB documents exist" {
    count=$(find "$KB_DIR" -name "*.md" ! -name "README.md" -type f | wc -l | xargs)
    [ "$count" -ge 15 ]
}

@test "all KB documents have valid frontmatter (required fields, category, tags)" {
    valid_categories="reference howto procedures troubleshooting best-practices planning"
    errors=0
    while IFS= read -r f; do
        if ! head -1 "$f" | grep -q '^---$'; then
            echo "MISSING frontmatter: $f"
            errors=$((errors + 1))
            continue
        fi
        fm=$(awk 'NR==1{next} /^---$/{exit} {print}' "$f")

        # Required fields
        for field in title category service tags last_updated created description; do
            if ! echo "$fm" | grep -q "^${field}:"; then
                echo "MISSING $field: $f"
                errors=$((errors + 1))
            fi
        done

        # Category must be valid
        cat=$(echo "$fm" | grep '^category:' | sed 's/category: *//' | tr -d '"' | tr -d "'" | tr -d '[:space:]')
        if [ -n "$cat" ]; then
            if ! echo " $valid_categories " | grep -q " $cat "; then
                echo "INVALID category '$cat': $f"
                errors=$((errors + 1))
            fi
            dir=$(basename "$(dirname "$f")")
            if [ "$cat" != "$dir" ]; then
                echo "MISMATCH: category=$cat dir=$dir in $f"
                errors=$((errors + 1))
            fi
        fi

        # Tags non-empty (accepts inline "[a, b]" and block "- a" list styles)
        if echo "$fm" | grep -q '^tags:'; then
            tag_count=$(echo "$fm" | awk '
                /^tags:/ {
                    inline = $0
                    sub(/^tags:[[:space:]]*/, "", inline)
                    if (inline ~ /\[/) {
                        gsub(/[][]/, "", inline)
                        n = split(inline, parts, ",")
                        for (i = 1; i <= n; i++) if (parts[i] ~ /[a-z]/) count++
                    } else {
                        block = 1
                    }
                    next
                }
                block && /^[[:space:]]+-[[:space:]]*[^[:space:]]/ { count++; next }
                block && /^[^[:space:]]/ { block = 0 }
                END { print count + 0 }
            ')
            if [ "$tag_count" -lt 1 ]; then
                echo "EMPTY tags: $f"
                errors=$((errors + 1))
            fi
        fi
    done < <(find "$KB_DIR" -name "*.md" ! -name "README.md" ! -path "*/history/*" -type f)
    [ "$errors" -eq 0 ]
}
