---
name: rollback
description: "Roll back a deployment safely with verification"
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
