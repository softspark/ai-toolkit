---
name: lint
description: "Lint code with auto-detected tools and fix suggestions"
effort: low
disable-model-invocation: true
argument-hint: "[path]"
allowed-tools: Bash, Read
---

# Lint Runner

$ARGUMENTS

Run linting and type checking based on detected project type.

## Project context

- Project files: !`ls pyproject.toml package.json composer.json pubspec.yaml go.mod 2>/dev/null`

## Auto-Detection

Run the bundled script to detect available linters:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/detect-linters.py .
```

## Usage

```
/lint [path]
```

## Commands by Project Type

| Project Type | Lint Command | Type Check |
|--------------|--------------|------------|
| **Python** | `ruff check .` | `mypy .` |
| **TypeScript/Node** | `npx eslint .` | `npx tsc --noEmit` |
| **PHP** | `./vendor/bin/phpstan analyse` | - |
| **Go** | `golangci-lint run` | - |
| **Rust** | `cargo clippy` | - |
| **Flutter/Dart** | `dart analyze` | - |

## Python Projects

```bash
# Linting
ruff check .

# Type checking
mypy .

# Auto-fix
ruff check --fix .
ruff format .
```

## TypeScript/Node Projects

```bash
# Linting
npx eslint .

# Type checking
npx tsc --noEmit

# Auto-fix
npx eslint --fix .
```

## PHP Projects

```bash
# Static analysis
./vendor/bin/phpstan analyse

# Code style
./vendor/bin/phpcs
./vendor/bin/phpcbf  # auto-fix
```

## Docker Execution (if applicable)

```bash
# Generic pattern - replace {container} with your app container
docker exec {container} make lint
docker exec {container} make typecheck
```

## Quality Gates

- Linting: 0 errors
- Type checking: 0 errors (for new code)

## Common Issues

| Error | Fix |
|-------|-----|
| Missing type hints | Add type annotations |
| Unused imports | Remove or use `# noqa: F401` |
| Line too long | Break line or disable for that line |
| Import order | Let linter fix with `--fix` |
