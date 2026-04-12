---
name: repeat
description: "Run a prompt or slash command on a recurring interval until task complete or limits reached. Use when user wants to set up a recurring task, poll for status, or run something repeatedly on an interval."
user-invocable: true
effort: medium
argument-hint: "[interval] [command or prompt] (e.g., /repeat 5m /test, defaults to 10m)"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
---

# /repeat - Autonomous Recurring Execution

$ARGUMENTS

## Argument Parsing

Parse the user input into three components:

1. **Interval** — duration between iterations (default: `10m`)
   - Accepts: `1m`, `5m`, `10m`, `30m`, `1h`
   - Minimum: `1m` (enforced, reject anything lower)
2. **Command or prompt** — the slash command or freeform prompt to execute each iteration
3. **Flags**:
   - `--iterations N` — maximum number of iterations (default: `5`)

Examples of parsed input:
- `/repeat 5m /test` -> interval=5m, command=/test, iterations=5
- `/repeat 10m "check deploy status"` -> interval=10m, command="check deploy status", iterations=5
- `/repeat --iterations 3 /review` -> interval=10m, command=/review, iterations=3
- `/repeat 2m --iterations 10 /lint` -> interval=2m, command=/lint, iterations=10

## Safety Controls

These limits are constitutionally mandated (Article I, Section 4). Violating them is not permitted.

### Max Iterations
- Default: **5** iterations
- Configurable via `--iterations N`
- Hard ceiling: the loop MUST terminate after N iterations regardless of outcome

### Circuit Breaker
- Track consecutive failures (non-zero exit code, error output, exceptions)
- **3 consecutive failures** -> immediate hard stop
- Reset the failure counter on any successful iteration

### Minimum Interval
- **Never** execute faster than 1 minute between iterations
- If user requests `<1m`, override to `1m` and warn

### Exit Detection
After each iteration, inspect the output for completion signals:
- Exit code `0` combined with success markers
- Output contains: `DONE`, `COMPLETE`, `ALL PASS`, `ALL TESTS PASSED`, `SUCCESS`
- Case-insensitive matching
- If detected: stop the loop early and report success

## Execution Protocol

```
For iteration = 1 to max_iterations:
    1. Log iteration start (timestamp, iteration number)
    2. Execute the command or prompt
    3. Capture output and exit status
    4. Check exit detection:
       - If completion marker found -> STOP, report success
    5. Check circuit breaker:
       - If failure: increment consecutive_failures
       - If success: reset consecutive_failures to 0
       - If consecutive_failures >= 3 -> HARD STOP, report failure
    6. Log iteration result to stats
    7. If not last iteration: wait for interval duration
    8. Repeat

After loop ends:
    - Print summary: total iterations, pass/fail counts, elapsed time
    - Final status: COMPLETED | EARLY_SUCCESS | CIRCUIT_BREAKER | MAX_ITERATIONS
```

## Stats Logging

Each iteration MUST be logged to `~/.softspark/ai-toolkit/stats.json`:

```json
{
  "loop_runs": [
    {
      "id": "loop-<timestamp>",
      "command": "/test",
      "interval": "5m",
      "max_iterations": 5,
      "started_at": "2026-04-01T10:00:00Z",
      "iterations": [
        {
          "number": 1,
          "timestamp": "2026-04-01T10:00:00Z",
          "result": "pass",
          "exit_code": 0,
          "summary": "All 42 tests passed"
        },
        {
          "number": 2,
          "timestamp": "2026-04-01T10:05:00Z",
          "result": "fail",
          "exit_code": 1,
          "summary": "3 tests failed"
        }
      ],
      "final_status": "EARLY_SUCCESS",
      "ended_at": "2026-04-01T10:10:00Z"
    }
  ]
}
```

Ensure the stats directory and file exist before writing. Append to existing data, never overwrite.

## Usage Examples

```bash
# Run tests every 5 minutes until all pass (max 5 iterations)
/repeat 5m /test

# Poll deployment status every 10 minutes
/repeat 10m "check deploy status"

# Run review max 3 times at default interval
/repeat --iterations 3 /review

# Lint every 2 minutes, up to 10 times
/repeat 2m --iterations 10 /lint

# Monitor CI pipeline every 5 minutes
/repeat 5m "check if CI pipeline passed for current branch"
```

## When to Use

- Polling deployment or CI/CD pipeline status
- Running tests repeatedly until green
- Monitoring an external process for completion
- Retrying a flaky operation with intervals
- Watching for a condition to become true

## When NOT to Use

- Anything requiring human judgment between iterations
- Tasks where each iteration depends on user feedback
- Long-running computations that should be a single background job
- Destructive operations (deletes, drops, force pushes) -- never loop these
- Intervals shorter than 1 minute -- use a proper scheduler instead
