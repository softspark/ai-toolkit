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
