---
name: build
description: "Build the project with auto-detected toolchain (npm, poetry, cargo, go, flutter, Docker). Use when the user asks to compile, bundle, or produce artifacts — not to run tests or deploy."
effort: low
disable-model-invocation: true
argument-hint: "[target]"
allowed-tools: Bash, Read
---

# Build Project

$ARGUMENTS

Build the current project.

## Project context

- Project config: !`cat package.json 2>/dev/null || cat pyproject.toml 2>/dev/null || echo "unknown"`

## Auto-Detection

Run the bundled script to detect build system:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/detect-build.py [dev|prod|docker]
```

## Usage

```
/build [target]
```

## What This Command Does

1. **Detects** project type
2. **Runs** appropriate build command
3. **Reports** build status

## Build Commands by Project Type

| Project Type | Build Command |
|--------------|---------------|
| Node.js | `npm run build` or `pnpm build` |
| Python | `poetry build` or `pip install -e .` |
| Flutter | `flutter build` |
| Go | `go build ./...` |
| Rust | `cargo build --release` |
| Docker | `docker compose build` |

## Output Format

```markdown
## Build Report

### Status: Success / Failed

### Build Details
- **Project**: [name]
- **Type**: [type]
- **Command**: [command used]
- **Duration**: [time]

### Artifacts
- [artifact 1]
- [artifact 2]

### Warnings
- [warning if any]

### Errors
- [error if any]
```

## Targets

| Target | Description |
|--------|-------------|
| `dev` | Development build |
| `prod` | Production build |
| `docker` | Docker image build |
| `all` | Build all targets |

## MANDATORY: Documentation Update

After build configuration changes, update documentation:

### When to Update
- Build config changes -> Update build docs
- New dependencies -> Update requirements docs
- Docker changes -> Update Docker docs
- CI changes -> Update CI/CD docs

### Post-Build Changes Checklist
- [ ] Build successful
- [ ] **README build instructions updated** (if changed)
- [ ] **CI/CD config documented**

## Rules

- **MUST** detect the build system automatically (`detect-build.py`) before invoking any command
- **NEVER** run a `clean` build when incremental works — clean only on explicit user request
- **CRITICAL**: surface the first build error literally, including the stack trace and file:line. Paraphrasing loses the diagnostic.
- **MANDATORY**: on success, report the artifact paths (compiled binaries, bundled output, built images) — callers downstream need them

## Gotchas

- `npm run build` does not refresh `node_modules`. If `package-lock.json` is out of sync, the build runs against stale dependencies and "succeeds" with wrong versions. In CI always precede with `npm ci`.
- `cargo build --release` takes 5-10× longer than debug. Never use `--release` in a dev loop; reserve it for CI artifacts and benchmarks.
- `docker compose build` keys layer cache per service. A change to a shared context file (e.g., root `COPY . .`) invalidates every service's cache. Structure Dockerfiles to copy dependency manifests first, source last.
- `flutter build apk` without `--split-per-abi` produces a fat APK ~3× larger than needed. Production builds should always split unless explicitly bundling.
- `go build ./...` succeeds with a warning when a package has no Go files (e.g., pure-doc subdir). Downstream tools that expect every listed package to compile a binary fail silently — check `go build -v` for the list of built packages.

## When NOT to Use

- For running tests — use `/test`
- For deployment or artifact push — use `/deploy`
- For scaffolding a new build system — use `/app-builder` or `/ci`
- For CI pipeline generation — use `/ci`
- When the project has no build step (interpreted code, pure docs) — this skill has nothing to do
