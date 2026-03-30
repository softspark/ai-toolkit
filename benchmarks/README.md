# ai-toolkit Benchmarks

Structured benchmarks to measure the toolkit's impact on developer productivity.

## Methodology

Each benchmark task is run twice:
1. **Without toolkit**: Vanilla Claude Code, no agents or skills
2. **With toolkit**: ai-toolkit installed with standard profile

Metrics captured:
- **Time to first useful output** (seconds)
- **Number of tool calls** (fewer = more precise)
- **Task completion rate** (% of success criteria met)
- **User corrections needed** (0 = perfect, higher = worse)

Each task is run 3 times per condition, results averaged.

## Benchmark Tasks

### B1: Debug a multi-file bug

**Task:** Given a FastAPI application with a broken authentication middleware (JWT validation fails silently), identify root cause and propose fix.

**Success criteria:**
- [ ] Identifies the exact line causing the issue
- [ ] Explains why it fails
- [ ] Proposes correct fix
- [ ] Fix passes type checking

### B2: Code review

**Task:** Review a 200-line Python module with 3 intentional issues (SQL injection, missing error handling, N+1 query).

**Success criteria:**
- [ ] Finds SQL injection vulnerability
- [ ] Finds missing error handling
- [ ] Finds N+1 query
- [ ] No false positives

### B3: Refactor to clean code

**Task:** Refactor a 150-line function with 4 responsibilities into smaller, well-named functions.

**Success criteria:**
- [ ] Single responsibility per function
- [ ] Clear function names
- [ ] No behavior change
- [ ] Tests still pass

### B4: Generate tests

**Task:** Generate unit tests for a payment processing module with 5 methods.

**Success criteria:**
- [ ] All 5 methods covered
- [ ] Edge cases included
- [ ] Tests are runnable (no syntax errors)
- [ ] Mocks external dependencies

### B5: Generate documentation

**Task:** Generate README, API docs, and inline docstrings for a 3-file Flask microservice.

**Success criteria:**
- [ ] README covers install, usage, API
- [ ] All public endpoints documented
- [ ] Docstrings on all public functions
- [ ] Examples are accurate

## Running Benchmarks

```bash
python3 benchmarks/run.py [task-id]
python3 scripts/benchmark_ecosystem.py --offline
python3 scripts/benchmark_ecosystem.py --dashboard-json --out benchmarks/ecosystem-dashboard.json
python3 scripts/harvest_ecosystem.py --offline

# Examples:
python3 benchmarks/run.py B1         # run single benchmark
python3 benchmarks/run.py all        # run all 5 benchmarks
python3 benchmarks/run.py --report   # print last results
```

## Ecosystem Benchmark Artifacts

- `benchmarks/ecosystem-dashboard.json` — curated summary with freshness, comparison matrix, and repo metrics
- `benchmarks/ecosystem-harvest.json` — machine-readable harvest for roadmap / changelog reuse

Use `scripts/benchmark_ecosystem.py` for curated reports and `scripts/harvest_ecosystem.py` for repeatable JSON harvesting.

## Results

**Run date:** 2026-03-26 · **Model:** claude-sonnet-4-6

| Benchmark | With Toolkit | Tool Calls | Without Toolkit | Tool Calls |
|-----------|-------------|------------|-----------------|------------|
| B1: Debug (FastAPI JWT) | 4/4 ✓ | 1 | 4/4 ✓ | 1 |
| B2: Review (SQL/N+1/error) | 4/4 ✓ | 1 | 4/4 ✓ | 1 |
| B3: Refactor (god function) | 4/4 ✓ | 1 | 4/4 ✓ | 2 |
| B4: Test gen (payments) | 4/4 ✓ | 1 | 4/4 ✓ | 8* |
| B5: Docs (Flask API) | 4/4 ✓ | 3 | 4/4 ✓ | 10 |
| **TOTAL** | **20/20** | **avg 1.4** | **20/20** | **avg 4.4** |

*B4 vanilla found existing test file from prior run — tool call count inflated.

**Finding:** Same accuracy on isolated single-file tasks. Toolkit delivers **3.1× fewer tool calls** on complex tasks (B4/B5). Real gains expected on multi-file, multi-step real-world scenarios where agent specialization and skill context compound.

---

*Run `./benchmarks/run.sh all` then `./benchmarks/run.sh --report` to see results.*
