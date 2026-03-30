---
name: git-mastery
description: "Loaded when user asks about advanced Git workflows or history rewriting"
effort: medium
user-invocable: false
allowed-tools: Bash
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
