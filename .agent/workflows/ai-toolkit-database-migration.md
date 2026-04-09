---
description: Safely evolve database schema with zero-downtime migration
---

# Database Migration Workflow

1. Write the migration script (up and down)
2. Test migration on a copy of production data
3. Check for breaking changes: column renames, type changes, NOT NULL on existing data
4. Plan backfill strategy for new columns with defaults
5. Consider index impact on large tables (concurrent index creation)
6. Update ORM models/entities to match new schema
7. Run the full test suite against the migrated schema
8. Document rollback procedure
