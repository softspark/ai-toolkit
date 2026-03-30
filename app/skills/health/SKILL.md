---
name: health
description: "Report service and infrastructure health status"
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
