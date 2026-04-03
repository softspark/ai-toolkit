---
name: performance-profiling
description: "Loaded when user asks about performance profiling or optimization"
effort: medium
allowed-tools: Read, Grep
user-invocable: false
---

# Performance Profiling Skill

## Optimization Golden Rule
**"Don't optimize without a baseline."**
Always measure -> change -> measure.

## Critical Metrics (The 4 Golden Signals)
1. **Latency**: Time it takes to serve a request. (p50, p95, p99)
2. **Traffic**: Demand on your system (req/sec).
3. **Errors**: Rate of requests that fail.
4. **Saturation**: How "full" your service is (CPU/Memory usage).

## Profiling Tools & Techniques

### Python
- **CPU Sampling**: `py-spy`
  ```bash
  # Record flamegraph
  py-spy record -o profile.svg --pid <pid>
  ```
- **Function Profiling**: `cProfile`
  ```python
  import cProfile
  cProfile.run('main()')
  ```

### Node.js
- **Flamegraphs**: `0x` or built-in profiler.
  ```bash
  node --prof app.js
  node --prof-process isolate-0xnnnnn.log > processed.txt
  ```
- **Event Loop**: `clinic doctor`

### Database (SQL)
- **Explain Plan**: Analyze query cost.
  ```sql
  EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM users WHERE active = 1;
  ```
- **N+1 Problem**: Look for loop-generated queries.

### Frontend (Browser)
- **Lighthouse**: Core Web Vitals (LCP, CLS, INP).
- **Chrome Performance Tab**: Main thread blocking time.
- **Network Waterfall**: Time to First Byte (TTFB).

## Optimization Hierarchy
1. **Database/IO**: (Indexing, Caching, Batching) - *Biggest Gains*
2. **Algorithm**: (O(n²) -> O(n log n))
3. **Memory**: (Allocation churn, GC pressure)
4. **Micro-optimization**: (Loop unrolling, etc.) - *Smallest Gains*
