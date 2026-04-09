---
description: Profile and optimize performance bottlenecks
---

# Performance Optimization Workflow

1. Measure first — establish baseline metrics (latency, throughput, memory)
2. Profile to find the actual bottleneck — do not guess
3. Check for N+1 queries, unnecessary allocations, blocking I/O
4. Implement the smallest change that addresses the bottleneck
5. Measure again — verify improvement with same benchmark
6. If no improvement, revert and investigate further
7. Document the optimization and its measured impact
