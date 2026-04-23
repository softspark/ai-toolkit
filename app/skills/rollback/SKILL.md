---
name: rollback
description: "Roll back a git commit, database migration, or deployment to a previous known-good state with safety checks and health verification. Use when the user wants to revert recent changes safely — not to undo local edits or halt the whole system."
effort: medium
disable-model-invocation: true
argument-hint: "[target: git/db/deploy]"
allowed-tools: Bash, Read
hooks:
  PostToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "echo 'Reminder: verify rollback was successful and services are healthy'"
scripts:
  - scripts/rollback_info.py
---

# /rollback - Safe Rollback

$ARGUMENTS

## What This Command Does

Safely revert changes with appropriate safety checks and confirmation.

## Rollback Types

### 1. Git Rollback
```bash
# Revert last commit (creates new commit)
git revert HEAD --no-edit

# Revert specific commit
git revert <commit-sha> --no-edit

# Revert to specific state (CAUTION)
git reset --soft <commit-sha>  # Keep changes staged
```

### 2. Database Migration Rollback

| Tool | Command |
|------|---------|
| Alembic | `alembic downgrade -1` |
| Prisma | `npx prisma migrate resolve --rolled-back <name>` |
| Laravel | `php artisan migrate:rollback --step=1` |
| Django | `python manage.py migrate <app> <previous>` |
| Flyway | `flyway undo` |

### 3. Deployment Rollback

| Platform | Command |
|----------|---------|
| Kubernetes | `kubectl rollout undo deployment/<name>` |
| Docker Compose | `docker compose up -d --force-recreate` (with previous image tag) |
| Heroku | `heroku rollback` |

## Gather Rollback Context

Run the rollback info script to assess current state before rolling back:
```bash
bash scripts/rollback_info.py
```

Returns JSON with:
- `git{}` - current/previous commit, branch, commits ahead, uncommitted changes
- `migrations{}` - detected tool (alembic/prisma/laravel/django/drizzle), rollback command
- `docker{}` - running services and image tags

## Safety Checks (MANDATORY)

Before any rollback:
1. Confirm what will be reverted (show diff/plan)
2. Check for dependent changes that may break
3. Verify backup exists (for database rollbacks)
4. Get explicit user confirmation

## Usage Examples

```
/rollback                    # Interactive - asks what to rollback
/rollback git last           # Revert last git commit
/rollback migration          # Rollback last database migration
/rollback deploy             # Rollback to previous deployment
```

> **CRITICAL: Always confirm with the user before executing destructive rollback operations.**

## Rules

- **MUST** confirm the current state AND the target state before rolling back — surface the diff in plain English
- **MUST** verify a recent backup exists (for DB rollbacks) or explicitly warn the user that none was found
- **NEVER** roll back without an explicit "yes" from the user — rollbacks are irreversible in the user-experience sense even when technically reversible
- **NEVER** `git reset --hard` on a branch others have pulled from — it rewrites shared history
- **CRITICAL**: after any rollback, run a health check (`/health` or the project's equivalent) to confirm the target state is stable — a "successful" rollback to a broken baseline is worse than the original state
- **MANDATORY**: log the rollback with timestamp, scope, and reason — post-mortems need this trail

## Gotchas

- `git revert` creates a **new commit** that undoes the target commit. The reverted commit is still in history — if the target commit was sensitive (secret, PII), revert alone does not remove it. Use history rewriting tools for that.
- Database migration rollbacks sometimes **lose data**. A forward migration that added a NOT NULL column with a default, then populated it with user data, cannot restore the column contents on rollback — the data is gone.
- Kubernetes `kubectl rollout undo` rolls back to the previous ReplicaSet, not to a specific version. If you need "rollback to v1.2.3 specifically", track deployments by image tag and use `kubectl set image`, not `rollout undo`.
- Heroku and similar PaaS platforms `rollback` restores the slug but not environment config that changed after the rollback target was built — new env vars or add-ons may break the rolled-back version.
- `git reset --soft` preserves staged changes, `--mixed` (default) preserves working tree, `--hard` discards both. Wrong flag = lost work; always state the flag explicitly in the confirmation prompt.
- Restoring a DB backup on top of an active database can cause data loss between the backup time and the restore time. Take a fresh snapshot before the restore, even when rolling back — the current (broken) state might contain post-backup user writes.

## When NOT to Use

- For emergency halt of all agent activity — use `/panic`
- For undoing local uncommitted edits — use `git checkout` directly, not this skill
- For an incident with user-facing impact — use `/workflow incident-response` for coordinated response
- For planned schema changes — use `/migrate` with a forward rollback migration, not this skill after-the-fact
- For a feature flag off-switch — toggle the flag; rollback is a heavier tool than needed
