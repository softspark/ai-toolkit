---
name: database-patterns
description: "Loaded when user asks about database schema or query optimization"
effort: medium
user-invocable: false
---

# Database Patterns Skill

## ORM Selection

| Scenario | ORM |
|----------|-----|
| Node.js, type-safe | Prisma |
| Node.js, SQL-first | Drizzle |
| Python, async | SQLAlchemy 2.0 |
| Python, simple | SQLModel |
| PHP | Doctrine, Eloquent |

---

## Schema Design

### Naming Conventions

```sql
-- Tables: plural, snake_case
CREATE TABLE user_profiles (...);

-- Columns: snake_case
user_id, created_at, is_active

-- Indexes: idx_{table}_{columns}
CREATE INDEX idx_users_email ON users(email);

-- Foreign keys: fk_{table}_{ref_table}
CONSTRAINT fk_orders_users FOREIGN KEY (user_id) REFERENCES users(id)
```

### Common Patterns

#### Soft Delete
```sql
ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP NULL;

-- Query active records
SELECT * FROM users WHERE deleted_at IS NULL;
```

#### Audit Columns
```sql
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
created_by UUID REFERENCES users(id),
updated_by UUID REFERENCES users(id)
```

#### UUID vs Serial
| Use Case | Type |
|----------|------|
| Internal only | SERIAL/BIGSERIAL |
| External/distributed | UUID |
| Human readable | SERIAL with prefix |

---

## Index Strategies

### When to Index
- Foreign keys (always)
- Columns in WHERE clauses
- Columns in ORDER BY
- Columns in JOIN conditions

### Index Types
| Type | Use Case |
|------|----------|
| B-tree | Equality, range (default) |
| Hash | Equality only |
| GIN | Arrays, JSONB, full-text |
| GiST | Geometric, full-text |
| BRIN | Large sequential data |

### Composite Index Order
```sql
-- Good: matches query pattern
CREATE INDEX idx_orders_user_date ON orders(user_id, created_at);
SELECT * FROM orders WHERE user_id = 1 AND created_at > '2024-01-01';

-- Index used for:
-- WHERE user_id = 1
-- WHERE user_id = 1 AND created_at > ...

-- Index NOT used for:
-- WHERE created_at > '2024-01-01' (missing leading column)
```

---

## Query Optimization

### Explain Analyze
```sql
EXPLAIN ANALYZE
SELECT * FROM users WHERE email = 'test@example.com';
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Seq Scan on large table | Add index |
| High row estimate | Update statistics |
| Nested Loop on large sets | Consider hash join |
| Sort in memory | Increase work_mem |

### N+1 Prevention
```python
# Bad: N+1
for user in users:
    print(user.orders)  # Query per user

# Good: Eager loading
users = User.query.options(joinedload(User.orders)).all()
```

---

## Migration Best Practices

### Safe Migrations
```sql
-- Add column (safe)
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- Add NOT NULL column (safe pattern)
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
UPDATE users SET phone = '' WHERE phone IS NULL;
ALTER TABLE users ALTER COLUMN phone SET NOT NULL;

-- Rename column (use application-level)
-- 1. Add new column
-- 2. Copy data
-- 3. Update application
-- 4. Remove old column
```

### Migration Checklist
- [ ] Tested on production-like data
- [ ] Rollback script ready
- [ ] No long locks on large tables
- [ ] Indexes created concurrently
- [ ] Application handles both states

---

## Connection Pooling

### PgBouncer Settings
```ini
[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
```

### Application Settings
| Framework | Pool Size Formula |
|-----------|------------------|
| General | (cores * 2) + disk spindles |
| Read-heavy | cores * 4 |
| Write-heavy | cores * 2 |

---

## Vector Database (Qdrant) Patterns

### Client Setup
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Sync client
client = QdrantClient(host="localhost", port=6333)

# Async client
from qdrant_client import AsyncQdrantClient
async_client = AsyncQdrantClient(host="localhost", port=6333)
```

### Collection Management
```python
# Create collection (single vector)
client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)

# Create collection (multi-vector)
from qdrant_client.models import VectorParams

client.create_collection(
    collection_name="multimodal",
    vectors_config={
        "text": VectorParams(size=384, distance=Distance.COSINE),
        "image": VectorParams(size=512, distance=Distance.EUCLID),
    }
)
```

### Upserting Vectors
```python
# Single upsert
client.upsert(
    collection_name="documents",
    points=[
        PointStruct(
            id=1,
            vector=[0.1, 0.2, 0.3, ...],  # 384-dim vector
            payload={"title": "Doc 1", "category": "tech"}
        )
    ]
)

# Batch upsert
points = [
    PointStruct(id=i, vector=vectors[i], payload=payloads[i])
    for i in range(len(vectors))
]
client.upsert(collection_name="documents", points=points, batch_size=100)
```

### Searching Vectors
```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Basic search
results = client.search(
    collection_name="documents",
    query_vector=[0.1, 0.2, ...],
    limit=10
)

# Search with filter
results = client.search(
    collection_name="documents",
    query_vector=[0.1, 0.2, ...],
    query_filter=Filter(
        must=[
            FieldCondition(key="category", match=MatchValue(value="tech"))
        ]
    ),
    limit=10,
    with_payload=True,
    score_threshold=0.7
)

# Search with range filter
from qdrant_client.models import Range

results = client.search(
    collection_name="documents",
    query_vector=query_vector,
    query_filter=Filter(
        must=[
            FieldCondition(key="price", range=Range(gte=10, lte=100))
        ]
    ),
    limit=10
)
```

### Payload Indexing
```python
# Create payload index for faster filtering
client.create_payload_index(
    collection_name="documents",
    field_name="category",
    field_schema="keyword"  # or "integer", "float", "bool"
)
```

### Best Practices
| Aspect | Recommendation |
|--------|----------------|
| Batch Size | 100-1000 points per upsert |
| Vector Dim | Match your embedding model (384, 768, 1536) |
| Filters | Index frequently filtered fields |
| Distance | COSINE for normalized, EUCLID for raw |
| Sharding | Use for >1M vectors |

### Distance Metrics
| Metric | Best For | Normalized |
|--------|----------|------------|
| COSINE | Text embeddings | Yes |
| EUCLID | Image embeddings | No |
| DOT | When vectors pre-normalized | Yes |
