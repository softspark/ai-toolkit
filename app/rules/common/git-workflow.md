---
language: common
category: git-workflow
version: "2.0.0"
---

# Git Workflow Rules

Solo-safe core: everything here holds whether one person or twenty merge into
`main`. Branching, pull-request, and review conventions for teams live in
`git-team` and ship only with the `strict` profile.

## Commit Messages
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- First line: imperative mood, max 72 chars (`feat: add user registration endpoint`).
- Body (optional): explain *why*, not *what*. The diff shows what.
- Reference tickets: `fix: prevent duplicate orders (PROJ-456)`.

## Commit Practices
- Commit small, atomic changes. One commit = one logical change.
- Never commit: secrets, `.env` files, build artifacts, large binaries.
- `main` is always deployable: run the project's gates before every commit that lands there.

## Tags and Releases
- Use semantic versioning: MAJOR.MINOR.PATCH.
- Tag releases: `git tag v1.2.3`. Automate changelog from commits.

## Recovery
- Use `git stash` for WIP, not unfinished commits.
- Prefer `git revert` over `git reset --hard` on shared branches.
- Never force-push to `main` or shared branches.
