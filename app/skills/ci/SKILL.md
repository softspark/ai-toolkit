---
name: ci
description: "Detect, generate, or troubleshoot CI/CD pipeline configuration for the current project type (GitHub Actions, GitLab CI). Use when the user asks to set up, update, or debug a build pipeline — not for running tests locally."
effort: medium
disable-model-invocation: true
argument-hint: "[platform]"
allowed-tools: Bash, Read, Write
agent: devops-implementer
context: fork
scripts:
  - scripts/ci-detect.py
---

# /ci - CI/CD Pipeline Management

$ARGUMENTS

## What This Command Does

Generate, update, or troubleshoot CI/CD pipeline configuration based on project type.

## Project context

- CI config: !`cat .github/workflows/*.yml 2>/dev/null || cat .gitlab-ci.yml 2>/dev/null || echo "no-ci"`

## CI Detection Script

Detect CI platform and analyze configuration:
```bash
python3 scripts/ci-detect.py [directory]
```

Returns JSON with:
- `platform` - detected CI platform (github-actions, gitlab-ci, jenkins, bitbucket, circleci)
- `config_files[]` - CI config file paths
- `project_type` - detected project type (python, node, flutter, go, rust, php, docker)
- `jobs_found[]` - job/stage names extracted from config
- `stages_detected[]` - best-practice stages found (lint, test, build, deploy)
- `missing_stages[]` - recommended stages not yet configured
- `suggested_template` - pointer to ci-cd-patterns skill for templates

## Auto-Detection

| File Found | Project Type | Pipeline |
|------------|-------------|----------|
| `package.json` | Node.js/TypeScript | npm ci, lint, test, build |
| `pyproject.toml` / `setup.py` | Python | pip install, ruff, mypy, pytest |
| `pubspec.yaml` | Flutter/Dart | dart analyze, flutter test, build |
| `composer.json` | PHP | composer install, phpstan, phpunit |
| `go.mod` | Go | go vet, go test, go build |
| `Cargo.toml` | Rust | cargo clippy, cargo test, cargo build |
| `Dockerfile` | Docker | Build and push image |

## Supported Platforms

- **GitHub Actions** (default): `.github/workflows/ci.yml`
- **GitLab CI**: `.gitlab-ci.yml`

## Pipeline Stages

1. **Lint** - Static analysis, formatting checks
2. **Test** - Unit tests, integration tests with coverage
3. **Build** - Compile, bundle, Docker image
4. **Deploy** (optional) - Deploy to staging/production

## Usage Examples

```
/ci                          # Generate CI config for detected project type
/ci github-actions           # Explicitly use GitHub Actions
/ci add deploy staging       # Add deployment stage for staging
/ci fix                      # Troubleshoot failing pipeline
/ci add matrix node 18,20,22 # Add matrix testing
```

## Reference Skill
Use `ci-cd-patterns` skill for pipeline templates and best practices.

## Rules

- **MUST** detect existing CI platform before generating a new config — do not overwrite silently
- **NEVER** commit generated CI configs that embed hardcoded secrets or tokens
- **CRITICAL**: preserve existing job names and triggers unless the user explicitly asks for a restructure
- **MANDATORY**: every generated pipeline must include lint + test stages at minimum

## Gotchas

- GitHub Actions YAML parses `on:` as a reserved word only when unquoted. Writing `"on":` (quoted) produces a valid-looking file whose workflow **never triggers**. YAML anchors in this field also silently break.
- GitLab CI's `rules:` and `only:/except:` are mutually exclusive at the job level. Mixing them fails parse on pipeline run but not at `git push` time — test with `gitlab-ci-lint` before committing.
- `secrets.*` in GitHub Actions is undefined in workflows triggered from **forked** PRs (security boundary). Jobs that need secrets must gate on `github.event.pull_request.head.repo.full_name == github.repository` or use `pull_request_target` carefully.
- `actions/checkout@v4` defaults to `fetch-depth: 1` (shallow). Commands that need history (`git log`, `git describe`, conventional-commit tools) fail with misleading errors — set `fetch-depth: 0` for those jobs.

## When NOT to Use

- For running tests locally — use `/test`
- For general CI/CD patterns and theory — use `/ci-cd-patterns` (knowledge skill)
- For deployment orchestration only — use `/deploy`
- When the project has no VCS-hosted CI platform — generate locally-runnable scripts instead
