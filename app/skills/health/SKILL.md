---
name: health
description: "Report service and infrastructure health status via liveness/readiness checks, resource usage, and quick diagnostics. Use when the user asks whether services are up or degraded — not for deep debugging of a known error."
effort: medium
disable-model-invocation: true
argument-hint: "[service]"
allowed-tools: Bash, Read
---

# Health Check

$ARGUMENTS

Check the health of all project services.

## Project context

- Services: !`docker compose ps 2>/dev/null || echo "no-docker"`

## Auto-Detection

Detect services from `docker-compose.yml`, `.env`, or project configuration.

### Quick Check
```bash
# If using Docker Compose
docker compose ps

# Process check (bare metal)
ps aux | grep -E "(node|python|java|php)" | grep -v grep
```

## Common Service Checks

| Service | Health Check |
|---------|-------------|
| HTTP API | `curl -f http://localhost:{port}/health` |
| PostgreSQL | `pg_isready -h localhost -p 5432` |
| MySQL | `mysqladmin ping -h localhost` |
| Redis | `redis-cli ping` |
| MongoDB | `mongosh --eval "db.runCommand({ping:1})"` |
| Elasticsearch | `curl -f http://localhost:9200/_cluster/health` |
| RabbitMQ | `curl -f http://localhost:15672/api/healthchecks/node` |

## Diagnostics

```bash
# Container logs (if Docker)
docker compose logs --tail 50 {service}

# Resource usage
docker stats --no-stream   # Docker
htop                       # Bare metal

# Disk usage
df -h                      # System
docker system df           # Docker

# Network
netstat -tlnp              # Listening ports
curl -I http://localhost:{port}  # Connectivity
```

## Common Issues

| Symptom | Check | Solution |
|---------|-------|----------|
| Service not responding | Process running? Port open? | Restart service |
| Slow responses | Resource usage, connections | Scale or optimize |
| Connection refused | Network, firewall, port | Check config |
| Out of memory | `free -h`, container limits | Increase limits |

## Automated Health Check

Run the bundled script for a JSON health report:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/health_check.py http://localhost:8000
```

## Health Report Format

```yaml
services:
  {service-name}:
    status: healthy|degraded|down
    uptime: Xd Xh
    cpu: X%
    memory: XMB
    notes: "any issues"
```

## Rules

- **MUST** report measured values — never mark a service healthy without a successful probe
- **NEVER** restart a degraded service without the user's explicit go-ahead
- **CRITICAL**: separate liveness (process up) from readiness (accepting traffic) in the report
- **MANDATORY**: if a health endpoint times out, classify as `degraded`, not `healthy`

## Gotchas

- `docker compose ps` shows `Up` even when a container is **crash-looping** via restart policy — look at the `STATUS` column for `(unhealthy)` or `Restarting` rather than trusting "Up" alone.
- Many `/health` endpoints return 200 as long as the web server answers, even when the DB connection is down. If the service exposes a `/ready` or `/healthz?deep=true` endpoint, prefer it — shallow health is a lie.
- `pg_isready` reports success the moment Postgres accepts TCP, which happens seconds before the DB is actually query-ready after a restart. Chain it with a trivial `SELECT 1`.
- `docker stats --no-stream` needs cgroups v2 access; on older hosts or LXC containers it returns 0% CPU/memory silently instead of erroring. Verify at least one non-zero value before trusting the report.

## When NOT to Use

- To debug a specific failing service — use `/debug` after the health check narrows it down
- For performance bottlenecks — use `/performance-profiling`
- For a production incident with page/alert — use `/workflow incident-response`
- For CI pipeline status — use `/ci`
