---
title: "AI Toolkit - CI Integration"
category: reference
service: ai-toolkit
tags: [ci, github-actions, automation, validation]
version: "1.0.0"
created: "2026-03-29"
last_updated: "2026-03-29"
description: "Reusable GitHub Action for ai-toolkit validation in CI pipelines."
---

# CI Integration

## GitHub Action

Validate your toolkit setup in CI using the reusable composite action.

### Basic Usage

```yaml
# .github/workflows/validate-toolkit.yml
name: Validate AI Toolkit
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: softspark/ai-toolkit@v1
        with:
          command: validate
```

### Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `toolkit-version` | `latest` | npm version of @softspark/ai-toolkit |
| `node-version` | `20` | Node.js version |
| `command` | `validate` | Command to run (`validate` or `doctor`) |

### Outputs

| Output | Description |
|--------|-------------|
| `status` | `pass` or `fail` |

## Alternative: npx

For simpler setups without the action:

```yaml
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npx @softspark/ai-toolkit validate
```

## What Gets Validated

- Agent frontmatter (name, description, tools, model)
- Skill frontmatter (name, description, format, references)
- Hook event names against whitelist
- Plugin pack manifests (JSON validity, asset references)
- Metadata contracts (README badges vs actual counts)
- Core file presence (LICENSE, CHANGELOG, SECURITY)
