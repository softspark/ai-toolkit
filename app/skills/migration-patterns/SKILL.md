---
name: migration-patterns
description: "Zero-downtime database migration patterns: expand-contract, double-write, backfill, blue-green schema changes, feature flags, rollback safety, online DDL. Triggers: migration, schema change, zero-downtime, expand-contract, double-write, backfill, ALTER TABLE, column rename, safe deploy, online DDL. Load when planning non-trivial DB schema changes."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Migration Patterns

## Database Migration Tools

### Alembic (Python/SQLAlchemy)
```bash
# Initialize
alembic init migrations

# Create migration
alembic revision --autogenerate -m "add users table"

# Apply
alembic upgrade head

# Rollback
alembic downgrade -1
```

```python
# migrations/versions/001_add_users.py
def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_users_email", "users", ["email"])

def downgrade():
    op.drop_index("idx_users_email")
    op.drop_table("users")
```

### Prisma (TypeScript)
```bash
# Create migration
npx prisma migrate dev --name add_users

# Apply in production
npx prisma migrate deploy

# Reset (dev only)
npx prisma migrate reset
```

### Laravel (PHP)
```bash
# Create migration
php artisan make:migration create_users_table

# Apply
php artisan migrate

# Rollback
php artisan migrate:rollback --step=1

# Dry run
php artisan migrate --pretend
```

### Django (Python)
```bash
# Create migration from models
python manage.py makemigrations

# Apply
python manage.py migrate

# Rollback
python manage.py migrate app_name 0001

# Show plan
python manage.py showmigrations
```

### Flyway (Java/SQL)
```bash
flyway migrate
flyway info
flyway undo    # Undo last migration (Teams edition)
flyway repair  # Fix metadata table
```

## Zero-Downtime Migration Strategies

### 1. Expand-Contract Pattern
```
Phase 1 (Expand): Add new column, keep old
  ALTER TABLE users ADD COLUMN full_name VARCHAR(200);

Phase 2 (Migrate): Copy data
  UPDATE users SET full_name = first_name || ' ' || last_name;

Phase 3 (Switch): Update code to use new column
  Deploy new code that reads/writes full_name

Phase 4 (Contract): Remove old columns
  ALTER TABLE users DROP COLUMN first_name;
  ALTER TABLE users DROP COLUMN last_name;
```

### 2. Safe Column Operations
```sql
-- Safe: Add nullable column
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- Safe: Add column with default (PostgreSQL 11+, instant)
ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active';

-- Safe: Create index concurrently (no lock)
CREATE INDEX CONCURRENTLY idx_users_status ON users(status);

-- UNSAFE: Add NOT NULL without default (locks table)
-- Instead, do it in 3 steps:
ALTER TABLE users ADD COLUMN email VARCHAR(255);
UPDATE users SET email = 'unknown@example.com' WHERE email IS NULL;
ALTER TABLE users ALTER COLUMN email SET NOT NULL;
```

### 3. Rename Column Safely
```
Step 1: Add new column
Step 2: Write to both old and new columns (dual-write)
Step 3: Backfill new column from old
Step 4: Read from new column
Step 5: Stop writing to old column
Step 6: Drop old column (next release)
```

## Data Backfill Patterns

### Batch Processing
```python
BATCH_SIZE = 1000

def backfill_users():
    last_id = 0
    while True:
        batch = db.execute(
            "SELECT id, first_name, last_name FROM users "
            "WHERE id > :last_id ORDER BY id LIMIT :limit",
            {"last_id": last_id, "limit": BATCH_SIZE}
        ).fetchall()

        if not batch:
            break

        for row in batch:
            db.execute(
                "UPDATE users SET full_name = :name WHERE id = :id",
                {"name": f"{row.first_name} {row.last_name}", "id": row.id}
            )

        db.commit()
        last_id = batch[-1].id
        logger.info(f"Backfilled up to id={last_id}")
```

## API Versioning

### URL-Based (Most Common)
```
GET /api/v1/users
GET /api/v2/users
```

### Header-Based
```
GET /api/users
Accept: application/vnd.myapp.v2+json
```

### Implementation Pattern
```python
# FastAPI
from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1")
v2_router = APIRouter(prefix="/api/v2")

@v1_router.get("/users")
def get_users_v1():
    return [{"name": user.name} for user in users]  # Old format

@v2_router.get("/users")
def get_users_v2():
    return [{"full_name": user.name, "id": user.id} for user in users]  # New format
```

## Feature Flags for Gradual Rollout

```python
# Simple feature flag
import os

def is_feature_enabled(feature: str, user_id: str | None = None) -> bool:
    flag = os.getenv(f"FF_{feature.upper()}", "false")
    if flag == "true":
        return True
    if flag.endswith("%") and user_id:
        percentage = int(flag[:-1])
        return hash(user_id) % 100 < percentage
    return False

# Usage
if is_feature_enabled("new_search", user_id=request.user.id):
    return new_search(query)
else:
    return old_search(query)
```

## Rollback Strategies

### Database Rollback
```bash
# Always test rollback before deploying
alembic downgrade -1   # Alembic
npx prisma migrate resolve --rolled-back 20240101_migration  # Prisma
php artisan migrate:rollback --step=1  # Laravel
```

### Application Rollback
```bash
# Git-based rollback
git revert HEAD --no-edit
git push

# Container rollback
kubectl rollout undo deployment/api
docker service rollback api
```

## Migration Checklist

- [ ] Forward migration tested on staging
- [ ] Rollback migration tested on staging
- [ ] No data loss in either direction
- [ ] Performance impact assessed (large tables?)
- [ ] Backward compatible with current code
- [ ] Backfill script tested (if needed)
- [ ] Feature flag in place (if needed)
- [ ] Monitoring/alerts configured
- [ ] Team notified of migration window

## Anti-Patterns
- Running migrations without rollback plan
- Locking large tables during peak hours
- Mixing schema and data migrations
- Not testing rollback path
- Deploying code before migration completes
- Dropping columns before removing code references
