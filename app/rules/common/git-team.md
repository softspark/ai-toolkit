---
language: common
category: git-team
version: "1.0.0"
profiles:
  - "strict"
---

# Git Team Workflow Rules

These rules assume more than one person merges into `main`. They ship only with
the `strict` profile; a solo maintainer who commits straight to `main` is not
doing anything wrong, and a reviewer that keeps flagging "use a feature branch"
in that setting is noise. The solo-safe core (commit format, no secrets, no
force-push) lives in `git-workflow`.

## Branching
- Protect `main` with required reviews and CI. Never commit broken code to it.
- Work on feature branches: `feat/user-registration`, `fix/order-total-calc`.
- Rebase feature branches on `main` before opening a PR to keep linear history.
- Squash fixup commits before merging to keep history clean.
- Delete branches after merge. Stale branches are clutter.

## Pull Requests
- Keep PRs small: <400 lines changed. Split large features into stacked PRs.
- PR title follows conventional commit format.
- Include: summary, test plan, and screenshots/recordings for UI changes.
- Require at least one approval before merge.

## Code Review
- Review for: correctness, security, performance, readability.
- Approve with comments if nits only. Block for: bugs, security, missing tests.
- Respond to reviews within 24 hours. Do not let PRs rot.
