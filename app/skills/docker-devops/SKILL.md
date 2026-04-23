---
name: docker-devops
description: "Docker, containers, Kubernetes, and DevOps patterns: Dockerfile best practices, multi-stage builds, compose, k8s manifests, Helm charts, service mesh, image hardening. Triggers: Docker, Dockerfile, container, image, Kubernetes, k8s, compose, Helm, registry, layer caching, service mesh, pod, deployment yaml. Load when writing or fixing container/orchestration configs."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Docker & DevOps Skill

## Dockerfile Best Practices

### Multi-Stage Build (Node.js)

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
```

### Multi-Stage Build (Python)

```dockerfile
# Build stage
FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt -o requirements.txt

# Production stage
FROM python:3.12-slim
WORKDIR /app

# Non-root user
RUN useradd -m -u 1000 appuser

COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Docker Compose Patterns

### Development Setup

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - .:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/app
    depends_on:
      - db
      - redis

  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### Production Setup

```yaml
version: '3.8'

services:
  app:
    image: ${REGISTRY}/app:${TAG}
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
```

---

## CI/CD Patterns

### GitHub Actions (Node.js)

```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run test
      - run: npm run build

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to production
        run: |
          # Deploy commands
```

### GitHub Actions (Python)

```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Lint
        run: poetry run ruff check .
      - name: Type check
        run: poetry run mypy .
      - name: Test
        run: poetry run pytest --cov
```

---

## Infrastructure as Code

### Terraform Basic Structure

```
infrastructure/
├── main.tf
├── variables.tf
├── outputs.tf
├── providers.tf
├── modules/
│   ├── networking/
│   ├── compute/
│   └── database/
└── environments/
    ├── dev/
    ├── staging/
    └── prod/
```

### Terraform Best Practices

```hcl
# variables.tf
variable "environment" {
  description = "Environment name"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

# main.tf
resource "aws_instance" "app" {
  ami           = var.ami_id
  instance_type = var.instance_type

  tags = {
    Name        = "${var.project}-${var.environment}-app"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
```

---

## Health Checks

### HTTP Health Check

```python
# FastAPI
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION
    }

@app.get("/ready")
async def readiness_check():
    # Check database
    try:
        await db.execute("SELECT 1")
    except Exception:
        raise HTTPException(503, "Database not ready")

    return {"status": "ready"}
```

### Docker Health Check

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1
```

---

## Security Checklist

- [ ] No secrets in Dockerfile or compose
- [ ] Non-root user in container
- [ ] Minimal base image (alpine, distroless)
- [ ] Pinned image versions
- [ ] Read-only filesystem where possible
- [ ] Resource limits defined
- [ ] Health checks configured
- [ ] Logs to stdout/stderr

## Rules

- **MUST** use multi-stage builds for any production image — shipping build tools in the final layer is wasteful and insecure
- **MUST** pin base images by digest (`@sha256:...`), not just by tag — tags are mutable and reproducibility collapses on every `latest` update
- **NEVER** run a container as `root` in production — `USER appuser` with a non-zero UID is the default, not an optimization
- **NEVER** `COPY . .` before the dependency manifest — layer cache becomes useless and every source change re-downloads packages
- **CRITICAL**: logs go to stdout/stderr. Containers writing to log files require volumes, lose on crash, and break 12-factor assumptions.
- **MANDATORY**: every Dockerfile has a `HEALTHCHECK`, every compose service has `restart: unless-stopped` (or `always` in production)

## Gotchas

- `alpine` uses `musl` libc, not `glibc`. Python wheels compiled for glibc fail to install on alpine — use `python:3.12-slim` (glibc-based, small) instead of `python:3.12-alpine` unless you know every dependency ships a musl wheel.
- `docker compose build` caches layers per service. A change to a shared file (e.g., root `COPY . .` used by two services) invalidates both caches. Structure Dockerfiles to copy manifests first, source last.
- `HEALTHCHECK` in a Dockerfile is only respected by Docker and Compose, **not by Kubernetes**. K8s uses its own `livenessProbe` / `readinessProbe`. Maintaining both costs duplicate logic.
- `docker compose up -d` streams build output only to the terminal, not to a build log. CI that captures `docker compose up -d` silently misses build errors — use `docker compose build` as a separate step with log redirection.
- Container time is host time unless you mount `/etc/localtime` — a container running on a UTC host is UTC regardless of its `TZ` env var for anything reading `/etc/localtime`. For Python `datetime.now(timezone.utc)` is safer than `datetime.now()` inside containers.
- `volumes: ./data:/app/data` on macOS with VirtioFS mounts with inverted ownership (host UID vs container UID). Containers that chmod/chown the volume fail silently in dev, succeed in Linux CI.

## When NOT to Load

- For **CI/CD pipeline** design that uses Docker — use `/ci-cd-patterns`
- For generating a project-specific Dockerfile — use `/app-builder`
- For Kubernetes-specific manifests beyond Docker — this skill covers compose + basics; use `/devops-implementer` agent for k8s depth
- For **observability** of containers (metrics, logs, traces) — use `/observability-patterns`
- For **secret management** at runtime — use `/security-patterns`
