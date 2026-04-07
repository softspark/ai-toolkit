---
language: common
category: git-workflow
version: "1.0.0"
---

# Git Workflow Rules

## Commit Messages
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- First line: imperative mood, max 72 chars (`feat: add user registration endpoint`).
- Body (optional): explain *why*, not *what*. The diff shows what.
- Reference tickets: `fix: prevent duplicate orders (PROJ-456)`.

## Commit Practices
- Commit small, atomic changes. One commit = one logical change.
- Never commit: secrets, `.env` files, build artifacts, large binaries.
- Never commit broken code to `main`. Use feature branches.
- Squash fixup commits before merging to keep history clean.

## Branching
- `main` is always deployable. Protect it with required reviews and CI.
- Feature branches: `feat/user-registration`, `fix/order-total-calc`.
- Delete branches after merge. Stale branches are clutter.
- Rebase feature branches on main before PR to keep linear history.

## Pull Requests
- Keep PRs small: <400 lines changed. Split large features into stacked PRs.
- PR title follows conventional commit format.
- Include: summary, test plan, and screenshots/recordings for UI changes.
- Require at least one approval before merge.

## Code Review
- Review for: correctness, security, performance, readability.
- Approve with comments if nits only. Block for: bugs, security, missing tests.
- Respond to reviews within 24 hours. Do not let PRs rot.

## Tags and Releases
- Use semantic versioning: MAJOR.MINOR.PATCH.
- Tag releases: `git tag v1.2.3`. Automate changelog from commits.

## Recovery
- Use `git stash` for WIP, not unfinished commits.
- Prefer `git revert` over `git reset --hard` on shared branches.
- Never force-push to `main` or shared branches.
