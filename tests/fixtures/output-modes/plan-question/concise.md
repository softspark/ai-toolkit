Depends on three checks:

- **Latency:** is current session p95 >5ms? If no, skip — Redis adds ops overhead for no win.
- **Consistency:** need clear invalidation. Write-through (both Redis + Postgres) is the safe default.
- **Ops cost:** already running Redis? Free. New dependency? Real cost.

Recommend: add it if p95 >5ms AND Redis already deployed. Otherwise wait for measured pain.
