---
name: deploy
description: "Deploy with pre-flight checks and health verification"
effort: medium
disable-model-invocation: true
argument-hint: "[environment]"
allowed-tools: Bash, Read
hooks:
  PostToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "echo 'Reminder: verify health checks pass after deployment'"
scripts:
  - scripts/pre_deploy_check.py
---

# Deploy Application

$ARGUMENTS

Deploy application to target environment.

## Project context

- Docker config: !`cat docker-compose.yml 2>/dev/null || cat Dockerfile 2>/dev/null || echo "no-docker"`

## Usage

```
/deploy [environment]
```

## What This Command Does

1. **Validates** deployment prerequisites
2. **Runs** pre-deployment checks
3. **Executes** deployment
4. **Verifies** deployment success

## Environments

| Environment | Description |
|-------------|-------------|
| `dev` | Development environment |
| `staging` | Staging/QA environment |
| `prod` | Production environment |

## Pre-Deployment Checklist

Run automated pre-deployment checks:
```bash
python3 scripts/pre_deploy_check.py [environment]
```

Returns JSON with pass/fail for each check:
- `git_clean` - no uncommitted changes
- `branch` - on main/master for production
- `docker` - services running (if applicable)
- `env_file` - .env or .env.$ENV exists
- `build_artifacts` - dist/build present
- `tests_ran` - test result artifacts found

Manual verification:
- [ ] Tests passing
- [ ] Build successful
- [ ] Environment variables set
- [ ] Secrets configured
- [ ] Database migrations ready
- [ ] Rollback plan documented

## Deployment Strategies

| Strategy | Use Case |
|----------|----------|
| Rolling | Zero-downtime, gradual |
| Blue-Green | Instant switch, easy rollback |
| Canary | Risk mitigation, gradual traffic |
| Recreate | Simple, allows downtime |

## Output Format

```markdown
## Deployment Report

### Status: Success / Failed

### Details
- **Environment**: [env]
- **Version**: [version]
- **Started**: [timestamp]
- **Completed**: [timestamp]

### Steps
1. [Step 1] - Done
2. [Step 2] - Done
3. [Step 3] - Failed (if failed)

### Health Check
- [endpoint]: [status]

### Rollback
If needed: `[rollback command]`
```

## PRODUCTION SAFETY

- Always deploy to staging first
- Verify health checks pass
- Have rollback plan ready
- Monitor after deployment

## MANDATORY: Documentation Update

After deployment, update documentation:

### Required Updates
| Change Type | Update |
|-------------|--------|
| New release | CHANGELOG, release notes |
| Config changes | Deployment docs, procedures |
| New features | User documentation |
| Infrastructure | `kb/procedures/deployment-*.md` |

### Post-Deployment Checklist
- [ ] Deployment successful
- [ ] Health checks passing
- [ ] **CHANGELOG updated**
- [ ] **Deployment docs updated**
- [ ] Release notes created (if applicable)
