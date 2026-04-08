---
name: debug
description: "Debug errors and trace root causes systematically"
user-invocable: true
effort: medium
argument-hint: "[symptom]"
agent: debugger
context: fork
allowed-tools: Bash, Read, Grep
---

# Debug Helper

$ARGUMENTS

Systematic debugging for application issues.

## Project context

- Recent logs: !`docker compose logs --tail 20 2>/dev/null || tail -20 logs/*.log 2>/dev/null || echo "no-logs-found"`

## Automated Error Parsing

Pipe error output through the error parser for structured diagnosis:

```bash
# Pipe from failing command
your_command 2>&1 | python3 "$(dirname "$0")/scripts/error-parser.py"

# Or from a log file
cat /var/log/app/error.log | python3 scripts/error-parser.py
```

The script outputs JSON with:
- **language**: detected language (python/node/go/php)
- **error_type**: extracted error class (e.g., ModuleNotFoundError)
- **message**: the error message text
- **category**: classification (import, reference, type, connection, timeout, memory, permission, syntax)
- **stack_frames**: parsed file/line/function from the stack trace
- **files_to_check**: unique files from the trace, ordered by relevance
- **common_causes**: likely root causes for this error category

Use the parsed output to focus investigation on the right files and hypotheses.

---

## Debugging Workflow

### 1. Check Logs

```bash
# Application logs (auto-detect environment)
# Docker:
docker compose logs --tail 100 {service} 2>&1 | grep -i error

# Bare metal / systemd:
journalctl -u {service} --since "1 hour ago" | grep -i error

# Log files:
tail -100 logs/app.log | grep -i error
```

### 2. Check Service Health

```bash
# Docker environment
docker compose ps

# Process check
ps aux | grep -E "(node|python|java|php)" | grep -v grep

# HTTP health endpoints
curl -sf http://localhost:{port}/health
```

### 3. Interactive Debug

```bash
# Python
python3 -c "import module; print(module.function('test'))"

# Node.js
node -e "const m = require('./module'); console.log(m.fn('test'))"

# PHP
php -r "require 'vendor/autoload.php'; echo MyClass::method('test');"
```

### 4. Database Checks

```bash
# PostgreSQL
psql -U postgres -c "SELECT version();"

# MySQL
mysql -e "SELECT VERSION();"

# Redis
redis-cli ping && redis-cli info memory

# MongoDB
mongosh --eval "db.runCommand({ping:1})"
```

## Common Debug Scenarios

### API Returns 500
```bash
# Check server logs for stack traces
grep -A5 "Traceback\|Error\|Exception" logs/app.log
```

### Slow Performance
```bash
# Resource usage
top -bn1 | head -20     # CPU/memory
iostat -x 1 3            # Disk I/O
ss -tlnp                 # Open connections
```

### Connection Issues
```bash
# Test connectivity
curl -I http://localhost:{port}
nc -zv {host} {port}
```

## Parallel Hypothesis Debugging (Agent Teams)

For complex bugs (open >1h, unclear root cause), spawn teammates to investigate competing hypotheses:

```
Create an agent team to debug this issue:
- Teammate 1 (debugger): "Investigate if [bug] is caused by [hypothesis A: database issue].
  Check logs, connection pools, timeouts, query performance."
  Use Opus.
- Teammate 2 (debugger): "Investigate if [bug] is caused by [hypothesis B: race condition].
  Look for async issues, locking, concurrency, shared state."
  Use Opus.
- Teammate 3 (debugger): "Investigate if [bug] is caused by [hypothesis C: configuration drift].
  Compare env vars, config files, recent changes, dependency versions."
  Use Opus.
Have them talk to each other to challenge each other's theories.
Report consensus when done.
```

## Common Rationalizations

| Excuse | Why It's Wrong |
|--------|----------------|
| "It works on my machine" | Environment differences are the #1 cause of production bugs — reproduce in prod-like env |
| "It must be a library bug" | 95% of the time it's your code — exhaust local hypotheses first |
| "I'll just add more logging and wait" | Passive debugging wastes hours — form a hypothesis and test it actively |
| "The error message says X, so it must be X" | Error messages often describe symptoms, not root causes — trace the full chain |
| "It only happens sometimes, probably a fluke" | Intermittent bugs are race conditions or state leaks — they get worse, not better |

## Debug Checklist

- [ ] Identified error/symptom
- [ ] Checked relevant logs
- [ ] Verified service health
- [ ] Reproduced issue
- [ ] Formed hypothesis
- [ ] Tested fix

## Related Skills
- Bug fixed? → `/review` to verify the fix quality
- Need a regression test? → `/tdd` to write it test-first
- Performance issue? → `/analyze --type=complexity` for hotspot analysis
- Incident in production? → `/workflow incident-response` for full response
