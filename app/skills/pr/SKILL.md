---
name: pr
description: "Creates GitHub PR after pre-flight checks (lint/typecheck/tests), structured summary from commits. Triggers: pr, pull request, create PR, ready to merge."
effort: medium
disable-model-invocation: true
argument-hint: "[title or branch]"
allowed-tools: Bash, Read, Grep
---

# Pull Request

$ARGUMENTS

Create or update the task's GitHub pull request after project-specific checks.
When called by `/autonomous-dev`, preserve its run ID, branch, PR identity,
approval history and evidence. This skill publishes the PR; the calling process
owns subsequent review, QA and required-CI completion.

## Project context

- Inspect the actual repository, branch and working tree. Resolve the base from
  an existing PR first, then project configuration or the remote default branch.
  Do not assume a branch named `main` exists.

## Usage

```
/pr [title]
```

## Automated PR Summary Generation

Generate a structured PR summary from the commit history before writing the PR description:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/pr-summary.py [base_branch]
# Pass the resolved PR base explicitly, for example develop.
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

Read the project's instructions, CI configuration and package/Make scripts.
For an autonomous run, use the commands frozen in its plan from
`.ai-toolkit/autonomous.json`. Run the actual lint, typecheck, test and build
commands applicable to that project; a Python command is not a universal gate.
Inspect every result and preserve evidence of the tested commit. Missing runtime
services or failed commands are blockers, never successful checks.

Verify that the authorized changes are committed, the intended base exists,
and the diff contains only the task's work. Use the resolved base with a
triple-dot diff for PR scope. Preserve unrelated dirty work and report it.

### 2. Create PR

Verify the repository and active account. Search for an existing PR from the
exact head branch before creation, including after an interrupted publication.
Update that PR when it represents this task. Never open a duplicate merely
because a previous assistant message omitted its URL.

Use the repository's template and write the exact body with an editing tool to
an absolute temporary file outside the checkout. Pass it through a structured
connector argument or `gh --body-file`, preserving real newlines. For example,
with actual repository/branch values and the prepared body file:

```bash
gh pr create --base develop --head feat/csv-export --title "feat: export filtered orders" --body-file /absolute/run/pr-body.md
```

Publishing must already be authorized by the task and allowed by the current
host. A missing permission leaves a prepared, reviewable result and a concrete
blocker. Creating a PR does not authorize merging it. Record the returned URL
immediately in the autonomous run before continuing.

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

```

## PR Checklist

Before creating PR:
- [ ] Project tests and required build pass for the current commit
- [ ] Applicable linting and type checking pass
- [ ] Actual base/head and repository are verified; an existing PR is reused
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventional commits
- [ ] Changes against the actual base are reviewed; merge conflicts are resolved

## Useful gh Commands

```bash
# View PR
gh pr view

# Check PR status
gh pr checks

# Inspect the current head and review state
gh pr view --json url,headRefOid,baseRefName,reviewDecision,mergeStateStatus
```

## Rules

- **MUST** run the project's applicable validation commands before opening the PR
- **NEVER** force-push `main` or `master`
- **NEVER** add AI co-authorship or generated-by signatures to commits or the PR body
- **CRITICAL**: PR body must include a Test plan checklist — no exceptions
- **MANDATORY**: commit messages follow conventional commits (`feat:`, `fix:`, `docs:` etc.)

## Gotchas

- `gh` defaults to `github.com`; for GitHub Enterprise the host must be set per-repo with `gh auth login --hostname <host>` and `gh repo set-default`. Silent failures on enterprise usually mean the wrong host.
- Running `gh pr create` without `--body` opens an editor (`$EDITOR` or `vi`) — in non-interactive contexts this hangs indefinitely. Always pass `--body` or `--body-file`.
- A local validation pass does not prove required remote CI or human approval.
  Report pending conditions; `/autonomous-dev` waits for them before completion.
- A triple-dot diff uses the merge-base. Use the resolved PR base rather than
  substituting a hardcoded branch name.

## When NOT to Use

- For creating a commit (without a PR) — use `/commit`
- For reviewing a PR someone else opened — use `/review`
- For drafting release notes across many PRs — use `/docs` or a release script
- When the branch has uncommitted changes — commit first, then open the PR
