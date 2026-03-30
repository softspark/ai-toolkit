---
name: build
description: "Build the project with auto-detected toolchain"
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
