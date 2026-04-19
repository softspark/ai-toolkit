---
name: ci-cd-patterns
description: "CI/CD pipeline and deployment automation: GitHub Actions, GitLab CI, Jenkins, build stages, caching, artifact promotion, blue-green, canary, rollback gates. Triggers: CI, CD, pipeline, GitHub Actions, workflow YAML, deploy automation, release, artifact, rollout, canary, blue-green. Load when designing or fixing a build/release pipeline."
effort: medium
user-invocable: false
allowed-tools: Read
---

# CI/CD Patterns

## GitHub Actions

### Standard Pipeline
```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "npm"
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck

  test:
    runs-on: ubuntu-latest
    needs: lint
    strategy:
      matrix:
        node-version: [18, 20, 22]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: "npm"
      - run: npm ci
      - run: npm test -- --coverage
      - uses: actions/upload-artifact@v4
        with:
          name: coverage-${{ matrix.node-version }}
          path: coverage/

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "npm"
      - run: npm ci
      - run: npm run build
```

### Python CI
```yaml
name: Python CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: mypy --strict src/
      - run: pytest --cov=src --cov-report=xml
```

### Docker Build & Push
```yaml
  build-docker:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.ref == 'refs/heads/main' }}
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## GitLab CI

```yaml
stages:
  - lint
  - test
  - build
  - deploy

lint:
  stage: lint
  image: node:20
  cache:
    key: $CI_COMMIT_REF_SLUG
    paths: [node_modules/]
  script:
    - npm ci
    - npm run lint

test:
  stage: test
  image: node:20
  services:
    - postgres:16
  variables:
    DATABASE_URL: "postgresql://postgres:postgres@postgres/test"
  script:
    - npm ci
    - npm test

build:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  only:
    - main
```

## Docker Multi-stage Builds

### Node.js
```dockerfile
# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --production

# Stage 2: Build
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 3: Production
FROM node:20-alpine AS production
WORKDIR /app
ENV NODE_ENV=production
COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
USER node
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

### Python
```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir --target=/deps .

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /deps /usr/local/lib/python3.12/site-packages
COPY src/ ./src/
USER nobody
CMD ["python", "-m", "src.main"]
```

## Caching Strategies

### npm/pnpm
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-npm-${{ hashFiles('**/package-lock.json') }}
    restore-keys: ${{ runner.os }}-npm-
```

### pip
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
```

### Docker Layer Caching
```yaml
- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

## Kubernetes Deployment

### Rolling Update
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
        - name: api
          image: ghcr.io/org/api:latest
          readinessProbe:
            httpGet:
              path: /ready
              port: 3000
            initialDelaySeconds: 5
          livenessProbe:
            httpGet:
              path: /live
              port: 3000
            initialDelaySeconds: 10
```

## Secret Management

```yaml
# GitHub Actions - use secrets
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  API_KEY: ${{ secrets.API_KEY }}

# Never hardcode secrets in pipelines
# Use OIDC for cloud provider auth (no long-lived credentials)
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789:role/deploy
    aws-region: us-east-1
```

## Release Automation

### Semantic Release
```json
{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    "@semantic-release/changelog",
    "@semantic-release/npm",
    "@semantic-release/github",
    "@semantic-release/git"
  ]
}
```

### Conventional Commits for Auto-versioning
| Prefix | Version Bump | Example |
|--------|-------------|---------|
| `fix:` | Patch (0.0.x) | `fix: resolve null pointer in auth` |
| `feat:` | Minor (0.x.0) | `feat: add user search endpoint` |
| `feat!:` / `BREAKING CHANGE:` | Major (x.0.0) | `feat!: change API response format` |

## Common Rationalizations

| Excuse | Why It's Wrong |
|--------|----------------|
| "CI is green, ship it" | CI tests the happy path — verify edge cases, security, and performance separately |
| "Manual deploys give us more control" | Manual deploys give you more human error — automate the repeatable parts |
| "We'll set up CI when the project is bigger" | Small projects grow fast — CI debt compounds and retrofitting is painful |
| "Caching isn't worth the complexity" | Uncached builds waste developer time daily — caching pays for itself in a week |
| "Feature flags are over-engineering" | Feature flags decouple deploy from release — they're the cheapest safety net |

## Anti-Patterns
- Secrets in pipeline logs or environment dumps
- No caching (slow builds)
- Running tests only on main (should run on PRs)
- Manual deployments to production
- No rollback strategy
- Skipping linting/type-checking in CI
