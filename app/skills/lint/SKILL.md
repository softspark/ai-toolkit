---
name: lint
description: "Run the project's linter and type-checker with auto-detected toolchain (ruff/mypy, eslint/tsc, phpstan, golangci-lint, clippy, dart analyze). Use when the user asks for static-analysis feedback — not to run tests or refactor."
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

## Rules

- **MUST** auto-detect the linter from project config (`pyproject.toml`, `package.json`, `.eslintrc.*`, `composer.json`, `go.mod`, `Cargo.toml`, `pubspec.yaml`) — do not assume
- **MUST** show the diff before applying any `--fix` run; the user owns the decision to accept auto-fixes
- **NEVER** suppress lint errors with blanket `# noqa` or `eslint-disable-next-line` without naming the specific rule and a reason
- **NEVER** run the formatter (ruff format, prettier, dprint) inside a lint pass unless the project has that wired explicitly — formatting and linting are separate concerns
- **CRITICAL**: report the error count **before and after** any auto-fix — delta visibility is what makes the run trustworthy
- **MANDATORY**: respect the project's lint config (`.ruff.toml`, `eslint.config.js`, `phpstan.neon`) — overriding project rules on the fly produces arguments during code review

## Gotchas

- `ruff check .` and `ruff format .` are **separate** commands in modern ruff (>0.1.0). Running only `ruff check` misses formatting drift; some repos expect both as part of "lint".
- `mypy` without `--strict` has a permissive default: missing annotations count as `Any`, so the type checker silently accepts untyped functions. Check whether the project pins `strict = true` in `pyproject.toml` before declaring "0 type errors".
- `eslint` follows `eslint.config.js` (flat config, ESLint 9+) OR `.eslintrc.*` (legacy). Mixing produces mysterious "no rules applied" errors. Check ESLint version first (`npx eslint --version`).
- `phpstan` levels (0-10) silently affect which rules apply. A repo at level 5 has different expectations than level 9; report the level alongside the error count.
- `golangci-lint` composes many linters; disabling one at the project level may still show its warnings if invoked with `--enable-all` flag. Check `.golangci.yml` before treating a warning as a new regression.
- Dart analyze reports on **all** files including generated `*.g.dart`. Some projects expect generated files to be excluded via `analysis_options.yaml`; without it, lint noise dominates real issues.

## When NOT to Use

- To **fix** the errors — use `/fix` after this skill surfaces them
- To run tests — use `/test`
- For code review of logic and design — use `/review`
- For security-specific static analysis (SAST) — use `/cve-scan` or `/security-patterns`
- For project-specific rule authoring — edit the linter's config directly
