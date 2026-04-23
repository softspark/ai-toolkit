---
name: pr
description: "Create a GitHub pull request after running pre-flight checks (lint, typecheck, tests) and generating a structured summary from commit history. Use when the branch is ready to merge — not for drafting work-in-progress."
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

## Rules

- **MUST** run lint + typecheck + tests locally before opening the PR
- **NEVER** force-push `main` or `master`
- **NEVER** add `Co-Authored-By: Claude` or other AI attribution to commits
- **CRITICAL**: PR body must include a Test plan checklist — no exceptions
- **MANDATORY**: commit messages follow conventional commits (`feat:`, `fix:`, `docs:` etc.)

## Gotchas

- `gh pr merge --squash` **drops** all original commit trailers, including `Co-Authored-By:` lines. If the PR had legitimate co-authors, note them in the squashed commit body or use `--rebase` instead.
- `gh` defaults to `github.com`; for GitHub Enterprise the host must be set per-repo with `gh auth login --hostname <host>` and `gh repo set-default`. Silent failures on enterprise usually mean the wrong host.
- Running `gh pr create` without `--body` opens an editor (`$EDITOR` or `vi`) — in non-interactive contexts this hangs indefinitely. Always pass `--body` or `--body-file`.
- The pre-flight `ruff check .` walks respecting `.gitignore` by default but `mypy src/` does not — if `src/` contains generated code excluded from git, mypy will still scan it and report spurious errors.
- `git diff main...HEAD` (triple dot) shows commits on HEAD since the merge-base; `git diff main..HEAD` (double dot) shows all differences including main's newer commits. Use triple-dot for PR-scope diffs.

## When NOT to Use

- For creating a commit (without a PR) — use `/commit`
- For reviewing a PR someone else opened — use `/review`
- For drafting release notes across many PRs — use `/docs` or a release script
- When the branch has uncommitted changes — commit first, then open the PR
