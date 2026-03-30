---
name: docker-devops
description: "Loaded when user asks about Docker, containers, or DevOps patterns"
effort: medium
user-invocable: false
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
