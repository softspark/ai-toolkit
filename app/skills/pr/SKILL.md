---
name: pr
description: "Create pull requests with pre-flight validation"
effort: medium
disable-model-invocation: true
argument-hint: "[title or branch]"
allowed-tools: Bash, Read, Grep
---

# Pull Request

$ARGUMENTS

Create a GitHub pull request.

## Project context

- Recent commits: !`git log --oneline main..HEAD 2>/dev/null | head -20`

## Usage

```
/pr [title]
```

## Automated PR Summary Generation

Generate a structured PR summary from the commit history before writing the PR description:

```bash
python3 "$(dirname "$0")/scripts/pr-summary.py" [base_branch]
# Default base branch: main
# Example: python3 scripts/pr-summary.py develop
```

The script outputs JSON with:
- **title_suggestion**: auto-generated PR title from dominant commit type and scope
- **commits[]**: each commit parsed into type, scope, description (conventional commits)
- **groups**: commits grouped by type (Features, Bug Fixes, etc.)
- **summary_bullets**: ready-to-use summary lines for the PR body
- **has_breaking**: whether any BREAKING CHANGE markers were found
- **breaking_changes[]**: list of breaking change descriptions
- **files_changed**: total files in the diff
- **test_files_changed**: count of test files modified
- **has_tests**: whether the PR includes test changes

Use the output to populate the PR template fields below.

---

## PR Creation Workflow

### 1. Pre-PR Checks

```bash
# Run CI checks
ruff check . && mypy src/ && pytest tests/

# Check branch status
git status
git diff main...HEAD --stat
```

### 2. Create PR

```bash
gh pr create --title "feat: add multi-hop reasoning" --body "$(cat <<'EOF'
## Summary
- Implement query decomposition for complex questions
- Add iterative retrieval with reasoning
- Include answer synthesis from aggregated context

## Test plan
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing with sample queries

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

## PR Template

```markdown
## Summary
<1-3 bullet points describing changes>

## Changes
- [ ] Feature implementation
- [ ] Tests added/updated
- [ ] Documentation updated

## Test plan
- [ ] CI checks pass (lint, typecheck, tests)
- [ ] Manual testing completed
- [ ] No regressions

## Screenshots
<if applicable>

Generated with [Claude Code](https://claude.com/claude-code)
```

## PR Checklist

Before creating PR:
- [ ] All tests pass: `pytest tests/`
- [ ] Linting passes: `ruff check .`
- [ ] Type checking passes: `mypy src/`
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventional commits
- [ ] Branch is up to date with main

## Useful gh Commands

```bash
# View PR
gh pr view

# Check PR status
gh pr checks

# Request review
gh pr edit --add-reviewer username

# Merge PR
gh pr merge --squash
```
