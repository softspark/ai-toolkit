---
name: migrate
description: "Run database migrations with backup verification"
effort: medium
disable-model-invocation: true
argument-hint: "[direction]"
allowed-tools: Bash, Read
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "echo 'Reminder: ensure database backup exists before running migrations'"
scripts:
  - scripts/migration-status.py
---

# /migrate - Database Migration Workflow

$ARGUMENTS

## What This Command Does

Create, run, or manage database migrations with auto-detection of the migration tool.

## Project context

- Migration tools: !`ls alembic.ini prisma/ database/migrations/ manage.py 2>/dev/null`

## Migration Status Script

Detect migration tool and report status:
```bash
python3 scripts/migration-status.py [directory]
```

Returns JSON with: `tool`, `config_file`, `migrations_dir`, `total_migrations`, `latest`, `commands{}` (status/create/upgrade/downgrade).

## Auto-Detection

| File Found | Tool | Commands |
|------------|------|----------|
| `alembic.ini` | Alembic | `alembic revision`, `alembic upgrade` |
| `prisma/schema.prisma` | Prisma | `npx prisma migrate dev` |
| `database/migrations/` + `artisan` | Laravel | `php artisan migrate` |
| `manage.py` | Django | `python manage.py migrate` |
| `flyway.conf` | Flyway | `flyway migrate` |
| `drizzle.config.ts` | Drizzle | `npx drizzle-kit push` |

## Workflow

### Create New Migration
1. Detect migration tool
2. Generate migration from model/schema changes
3. Review generated SQL
4. Validate syntax

### Run Migrations
1. Show pending migrations
2. Dry-run if supported (`--pretend`, `--sql`)
3. Backup reminder
4. Apply with user confirmation
5. Verify success

### Rollback
1. Show last applied migration
2. Confirm rollback scope
3. Execute rollback
4. Verify state

## Safety Checks (MANDATORY)

- [ ] Migration tested on development/staging first
- [ ] Rollback path verified
- [ ] No data loss in forward or backward direction
- [ ] Large table operations use concurrent/online DDL
- [ ] Backup exists or reminder given

## Usage Examples

```
/migrate                     # Show migration status
/migrate create add_users    # Create new migration
/migrate run                 # Apply pending migrations
/migrate rollback            # Rollback last migration
/migrate status              # Show applied/pending migrations
```

## Reference Skill
Use `migration-patterns` skill for zero-downtime strategies and best practices.
