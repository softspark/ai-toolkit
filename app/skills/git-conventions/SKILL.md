---
name: git-conventions
description: "Conventional Commits only (feat, fix, docs, refactor, test, chore); no AI co-authorship trailer and no AI signature in a commit message. Triggers: commit, git, message, changelog, release, pull request."
effort: low
user-invocable: false
allowed-tools: Read
---

# Git Conventions

This rule comes from `app/rules/git-conventions.md` in ai-toolkit. It applies to
every task in this workspace, not only when it is loaded.

# Git Conventions

- Do NOT add `Co-Authored-By: Claude` or any AI co-authorship to commits
- Do NOT add Claude signatures or attribution to commit messages
- Conventional commits format: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
