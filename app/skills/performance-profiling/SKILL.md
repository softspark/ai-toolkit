---
name: performance-profiling
description: "Performance measurement and optimization: four golden signals (latency/traffic/errors/saturation), p50/p95/p99, baseline-change-measure loop, flame graphs, load testing. Triggers: performance, slow, latency, p99, flame graph, profile, bottleneck, optimization, load test, benchmark, CPU profiling, memory leak. Load when diagnosing or optimizing slow code or services."
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

## Common Rationalizations

| Excuse | Why It's Wrong |
|--------|----------------|
| "It feels slow, let me optimize this function" | Feelings aren't data — profile first, then optimize the actual bottleneck |
| "We should optimize everything" | Premature optimization is the root of all evil — focus on the critical path |
| "Caching will fix it" | Caching masks problems and adds complexity — fix the root cause first |
| "It's fast enough in dev" | Dev has 1 user — production has thousands and cold caches |
| "We'll optimize later" | Performance debt compounds — a 100ms regression per sprint = 5s in a year |

## Example

```bash
# Capture a 30-second CPU flamegraph from a running Python service
py-spy record -o profile.svg --duration 30 --pid "$(pgrep -f my-service)"

# Identify top 3 hot functions
py-spy top --pid "$(pgrep -f my-service)"
```

Then, per the optimization hierarchy, start with DB/IO fixes (indexing, batching, caching the right layer) before touching algorithm-level changes.

## Rules

- **MUST** capture a baseline measurement before proposing any change
- **NEVER** optimize code without profiler data pointing at it as the bottleneck
- **CRITICAL**: report p95/p99, not just p50 — averages hide real user pain
- **MANDATORY**: follow the hierarchy — DB/IO before algorithm before micro-optimization

## Gotchas

- `py-spy` needs `CAP_SYS_PTRACE` on Linux and SIP-disabled codesigning on macOS to attach to another process. Containerized services usually run without ptrace privileges — profiling requires a `--cap-add=SYS_PTRACE` on the container or an in-process alternative (`cProfile`, `yappi`).
- Production hosts frequently set `/proc/sys/kernel/perf_event_paranoid=2` or higher, which disables user-space perf events. Tools that rely on perf (`perf`, `bcc`, `bpftrace`) silently produce empty output — check `cat /proc/sys/kernel/perf_event_paranoid` first.
- Node.js `--prof` output gets interleaved across worker threads and child processes. A single `isolate-*.log` mixes samples from multiple isolates unless each worker writes its own — filter by PID or use `clinic flame` which handles the split.
- Chrome DevTools samples at ~1kHz; operations faster than ~1ms vanish. For microbenchmarks, prefer `performance.now()` with manual markers, not the Performance tab.
- `EXPLAIN ANALYZE` on Postgres **executes** the query, including `INSERT`/`UPDATE`/`DELETE` — wrap write queries in a transaction that you roll back, or use `EXPLAIN (ANALYZE, BUFFERS) ... ; ROLLBACK;` in one statement.

## When NOT to Use

- For correctness bugs (wrong output) — use `/debug`
- For frontend render bugs without timing data — measure with DevTools first
- For infrastructure capacity planning — use load testing, not profiling
- For generic code quality — use `/analyze`
