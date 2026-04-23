---
name: git-mastery
description: "Advanced Git workflows: interactive rebase, bisect, reflog, cherry-pick, worktrees, history rewriting, submodules, large-file migration (LFS/filter-repo). Triggers: git rebase, bisect, cherry-pick, reflog, force push, history rewrite, detached HEAD, merge conflict, worktree, squash, fixup, submodule. Load when user needs non-trivial Git operations."
effort: medium
user-invocable: false
allowed-tools: Read, Grep, Glob
---

# Git Mastery Skill

## 🛡️ Safety First Protocol
- **Never** force push to `main` / `master` / `develop`.
- **Always** use `--force-with-lease` instead of `--force`.
- **Always** create a backup branch before complex operations:
  `git branch backup/feature-xyz-pre-rebase`

## Advanced Workflows

### 1. Automated Bug Hunting (Git Bisect)
Find the specific commit that introduced a bug.
```bash
# Start
git bisect start
git bisect bad              # Current version is broken
git bisect good <commit-sha> # Version that worked

# Automate with test script
git bisect run pytest tests/test_failing_feature.py
```

### 2. Interactive Interactive Rebase
Clean up commit history before merge.
```bash
git rebase -i HEAD~n
```
- **squash**: Combine commits.
- **reword**: Fix messages.
- **dropped**: Remove junk commits.

### 3. Log Analysis
Visualize branch topology.
```bash
git log --graph --oneline --decorate --all
```

### 4. Recovery (Reflog)
Recover "lost" commits after a bad reset/rebase.
```bash
git reflog
git reset --hard HEAD@{n}
```

### 5. Cherry Picking
Pick specific commits from other branches.
```bash
git cherry-pick <commit-sha>
# If valid conflict
git add .
git cherry-pick --continue
```

## Commit Message Standard (Conventional Commits)
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `style:` Formatting (white-space, etc)
- `refactor:` Code change that neither fixes a bug nor adds a feature
- `perf:` Performance improvement
- `test:` Adding missing tests
- `chore:` Build process/auxiliary tools

## Common Rationalizations

| Excuse | Why It's Wrong |
|--------|----------------|
| "I'll clean up commits later" | Later means never — write clean commits as you go |
| "Force push is fine on my branch" | Others may have fetched your branch — use --force-with-lease |
| "One big commit is simpler" | Big commits are impossible to review, bisect, or revert — keep them atomic |
| "Merge conflicts mean someone else's problem" | Conflicts mean you diverged too long — rebase frequently to stay aligned |
| "Commit messages don't matter" | Messages are documentation — future you needs to understand why, not just what |

## Rules

- **MUST** use `--force-with-lease` instead of `--force` for any force operation on a shared branch
- **MUST** create a backup branch before interactive rebase, reset --hard, or filter-repo: `git branch backup/<name>-pre-rebase`
- **NEVER** force-push to `main`, `master`, or `develop` — these are shared trunk branches by convention
- **NEVER** rewrite history that has already been pushed AND consumed by others — you will orphan their clones
- **CRITICAL**: the reflog is a 90-day safety net (`gc.reflogExpire`) — tag anything you want to keep longer. Do not rely on reflog for multi-month recovery.
- **MANDATORY**: commit messages follow Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) — drift defeats automated changelog and release tooling

## Gotchas

- `git bisect` relies on each commit being testable. Flaky tests corrupt the bisection silently — a flaky "bad" mark sends `bisect` down the wrong half. Run the test 3× at the boundary commits if flakiness is known.
- `git cherry-pick <sha>` of a merge commit fails without `--mainline 1` (or 2). The error is cryptic ("commit is a merge but no -m option was given"); the fix is simple but non-obvious.
- `git reflog` entries expire by default in 90 days (`gc.reflogExpire`) and unreferenced commits get garbage-collected after 30 days (`gc.reflogExpireUnreachable`). Long-term recovery of "lost" commits from reflog is not guaranteed.
- `git rebase -i --root` is supposed to include the very first commit, but on **shallow clones** (`--depth N`) the "root" is the shallow boundary, not the actual initial commit. Run `git fetch --unshallow` before rebasing --root.
- `git filter-branch` is **deprecated** and slow (shell-based, re-forks per commit). Use `git filter-repo` for history rewriting — it is a separate tool (`pip install git-filter-repo`) but 100× faster and endorsed by the Git maintainers.
- `git pull --rebase` on a branch with unpushed merge commits rewrites those merges into linear history, silently losing the merge metadata. If a merge was intentional (e.g., to preserve feature-branch context), use `git pull --no-rebase` or set `pull.ff=only` globally.

## When NOT to Load

- For simple commits on a ready branch — use `/commit`
- For opening a PR after commits are clean — use `/pr`
- For a specific failed operation needing root-cause analysis — use `/debug` on the git output
- For CI-specific git behavior (shallow clones, LFS on runners) — use `/ci-cd-patterns`
- For the in-repo `.git/hooks/*` content — this skill is user-facing Git; hook mechanics live in `/hook-creator` and `install_git_hooks.py`
