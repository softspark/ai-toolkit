---
title: "AI Toolkit - CI Integration"
category: reference
service: ai-toolkit
tags: [ci, github-actions, automation, validation]
version: "1.0.0"
created: "2026-03-29"
last_updated: "2026-10-05"
description: "Reusable GitHub Action for ai-toolkit validation in CI pipelines."
---

# CI Integration

## GitHub Action

Validate your toolkit setup in CI using the reusable composite action.

The action pins `actions/setup-node` v7.0.0 to an immutable commit. Its Node 24
action runtime requires Actions Runner 2.327.1 or later; GitHub-hosted
`ubuntu-latest` runners satisfy this requirement. The `node-version` input
still selects the Node.js version used by the toolkit, independently of that
action runtime.

### Basic Usage

```yaml
# .github/workflows/validate-toolkit.yml
name: Validate AI Toolkit
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: softspark/ai-toolkit@<reviewed-commit-sha>
        with:
          command: validate
```

Replace `<reviewed-commit-sha>` with the full commit SHA reviewed for your
workflow. This consumer example can run on PRs; the toolkit repository's own
workflow publishes only on release tags, following its local-gates SOP.

### Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `toolkit-version` | `latest` | npm version of @softspark/ai-toolkit |
| `node-version` | `20` | Node.js version |
| `command` | `validate` | Command to run (`validate` or `doctor`) |

`toolkit-version` is passed through an environment variable and quoted as one
npm package argument. Tags, versions and ranges are supported; shell syntax
in the value is never executed. Choose a trusted package version, since the
installed toolkit executable runs with the workflow's permissions.

### Outputs

| Output | Description |
|--------|-------------|
| `status` | `pass` or `fail` |

## Alternative: npx

For simpler setups without the action:

```yaml
      - uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0
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
