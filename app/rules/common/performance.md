---
language: common
category: performance
version: "1.0.0"
---

# Universal Performance Rules

## Mindset
- Profile before optimizing. Measure, do not guess.
- Premature optimization is the root of all evil. Ship correct first, fast second.
- Set performance budgets and test against them in CI.

## Database
- Fix N+1 queries: use JOINs, eager loading, or batch fetching.
- Add indexes for columns used in WHERE, ORDER BY, and JOIN clauses.
- Use EXPLAIN/ANALYZE to verify query plans. Avoid full table scans.
- Paginate all list endpoints. Never return unbounded result sets.
- Use connection pooling. Never open a new connection per request.

## Caching
- Cache at the right layer: CDN > reverse proxy > application > database.
- Set explicit TTLs. Stale cache is worse than no cache.
- Cache immutable or slowly-changing data. Avoid caching user-specific mutable data.
- Use cache-aside pattern: check cache, fetch on miss, populate cache.
- Include cache invalidation strategy before adding any cache.

## I/O and Network
- Async/non-blocking for I/O-bound work. Thread pools for CPU-bound work.
- Batch operations where possible: bulk inserts, batch API calls.
- Set timeouts on all external calls: HTTP, database, message queues.
- Use streaming for large payloads instead of loading everything into memory.

## Memory
- Preallocate collections when size is known.
- Use streaming/iterators for large datasets instead of loading all into memory.
- Watch for memory leaks: unclosed connections, growing caches, event listener accumulation.
- Avoid unnecessary copies/clones of large data structures.

## API Performance
- Compress responses (gzip/brotli). Return only requested fields.
- Use HTTP/2 or HTTP/3 where supported.
- Implement request deduplication for identical concurrent requests.
- Return 202 Accepted for long-running operations, process async.

## Monitoring
- Track p50, p95, p99 latencies, not just averages.
- Alert on latency regressions, not just errors.
- Log slow queries (>100ms) and slow endpoints (>500ms).
