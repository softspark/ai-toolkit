---
name: commit
description: "Create Conventional Commits with pre-commit validation"
effort: medium
disable-model-invocation: true
argument-hint: "[message or scope]"
allowed-tools: Bash, Read, Grep
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "echo 'Reminder: ensure linting passes before committing'"
---

# Git Commit

$ARGUMENTS

Creates well-structured git commits following Conventional Commits specification.

## Project context

- Staged changes: !`git diff --cached --stat 2>/dev/null || echo "nothing staged"`
- Current branch: !`git branch --show-current 2>/dev/null`

## Commit Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

## Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code restructuring |
| `perf` | Performance improvement |
| `test` | Adding/updating tests |
| `chore` | Maintenance tasks |
| `ci` | CI/CD changes |

## Examples

```bash
# Feature
git commit -m "$(cat <<'EOF'
feat(search): add multi-hop reasoning support

- Implement query decomposition
- Add iterative retrieval with reasoning
- Include answer synthesis from aggregated context
EOF
)"

# Bug fix
git commit -m "$(cat <<'EOF'
fix(cache): resolve connection pool exhaustion

Root cause: connections not returned to pool on error
Solution: use context manager for automatic cleanup

Fixes #123
EOF
)"
```

## Automated Pre-Commit Check

Run the bundled script for structured pre-commit analysis:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/pre-commit-check.py
```

Use the output to validate staged changes, detect secrets, and suggest commit type/scope.

## Pre-Commit Checklist

Before committing:
- [ ] Run linting: `make lint` (or `docker exec {app-container} make lint`)
- [ ] Run tests: `make test` (or `docker exec {app-container} make test`)
- [ ] Check for secrets: No API keys or passwords

## Git Safety

- NEVER use `--force` push without explicit request
- NEVER skip hooks (`--no-verify`) unless explicitly asked
- ALWAYS create NEW commits (don't amend previous unless asked)
- Stage specific files, avoid `git add -A` with sensitive files
