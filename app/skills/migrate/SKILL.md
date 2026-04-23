---
name: migrate
description: "Run or create database migrations with the detected tool (Alembic, Prisma, Laravel, Django, Flyway, Drizzle) and verify backups exist first. Use when the user asks to apply, roll back, or generate a migration — not for general schema design."
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

## Rules

- **MUST** verify a recent backup exists (or confirmed in-progress) before any forward migration on production
- **MUST** show the generated SQL (dry-run / `--pretend` / `--sql`) before applying — the user approves the diff, not just the command
- **NEVER** run destructive migrations (DROP TABLE/COLUMN, NOT NULL on existing column, type change) without a tested rollback path
- **NEVER** mix schema changes and data backfill in the same migration — they fail differently and roll back differently
- **CRITICAL**: large-table operations use the concurrent/online variant (`ALTER TABLE ... ALGORITHM=INPLACE`, `CREATE INDEX CONCURRENTLY`) — table locks in production cause outages, not slowdowns
- **MANDATORY**: migrations test on a non-production environment first with representative data volume

## Gotchas

- `alembic upgrade head` silently skips migrations with `branches` if the branch head is not explicit. Multi-head migrations need `alembic upgrade <revision>@head` or a merge migration first.
- Prisma's `prisma migrate dev` auto-generates migrations AND applies them AND reseeds the dev database. Running it on a production-connected config destroys data. Always use `prisma migrate deploy` in non-dev.
- Laravel's `migrate` command without `--force` refuses to run in `APP_ENV=production`. Scripts that blindly run `migrate` hang on interactive prompts in prod — always use `artisan migrate --force` in automation.
- Django's `migrate --fake` marks a migration as applied **without running it**. Intended for manual data fixes, but accidentally using it skips real schema changes and silently diverges production from code.
- `CREATE INDEX CONCURRENTLY` (Postgres) cannot run inside a transaction. Alembic wraps each migration in a transaction by default — concurrent index creation needs `op.execute()` with `autocommit_block()` or a manual `COMMIT`.
- Rolling back a forward migration that added a NOT NULL column deletes the column; data in that column is gone. "Rollback" is not "undo" if the column held user data during the forward window.

## When NOT to Use

- For **zero-downtime schema evolution** strategy (expand-contract, double-write) — use `/migration-patterns`
- For designing the schema from scratch — use `/database-patterns`
- For application-layer rollback (deploying previous code) — use `/rollback`
- For CI-triggered migrations — use `/ci` or `/deploy`
- When no migration tool is detected — propose one from `/app-builder` instead of ad-hoc SQL
