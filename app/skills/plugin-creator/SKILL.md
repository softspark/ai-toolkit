---
name: plugin-creator
description: "Creates experimental opt-in Claude Code plugin packs with manifests, conventions, and optional module scaffolding"
effort: high
disable-model-invocation: true
argument-hint: "[plugin pack name or domain]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Plugin Creator

$ARGUMENTS

Create a new experimental opt-in Claude Code plugin pack following ai-toolkit conventions.

## Workflow

1. **Capture scope** -- what domain should the plugin pack own?
2. **Pick packaging model** -- domain pack, policy pack, or hook/observability pack?
3. **Define manifest** -- name, description, version, domain, compatibility, included assets
4. **Select assets** -- agents, skills, rules, hooks, docs, templates
5. **Add scaffolding** -- create `plugin.json`, `README.md`, and optional subdirectories
6. **Validate** -- manifest JSON, included asset references, executable hooks, documentation links

## Directory Layout

```text
app/plugins/<plugin-name>/
├── plugin.json
├── README.md
├── agents/           # optional
├── skills/           # optional
├── hooks/            # optional
├── rules/            # optional
└── templates/        # optional
```

## Manifest Template

```json
{
  "name": "security-pack",
  "description": "Domain plugin pack for secure coding, review, and hardening workflows.",
  "version": "1.0.0",
  "domain": "security",
  "type": "plugin-pack",
  "status": "experimental",
  "requires": {
    "ai-toolkit": ">=1.0.0",
    "claude-code": ">=1.0.33"
  },
  "includes": {
    "agents": ["security-auditor", "security-architect"],
    "skills": ["review", "security-patterns"],
    "rules": [],
    "hooks": []
  }
}
```

## Authoring Rules

- Keep packs **domain-scoped**, not generic junk drawers
- Prefer referencing existing toolkit assets before duplicating them
- Pack manifests must be valid JSON with `name`, `description`, `version`, `domain`, `type`, `status`, and `includes`
- Optional hooks must be executable and documented in the pack README
- If the pack introduces policy or hook behavior, document install/opt-in semantics clearly, including that the pack is not part of the default install
- Experimental packs should remain opt-in and must not silently alter default global install behavior

## Validation Checklist

- [ ] `app/plugins/<plugin-name>/plugin.json` exists and parses as JSON
- [ ] `README.md` explains purpose, included assets, and opt-in flow
- [ ] Referenced agents and skills exist or are created in the same change set
- [ ] Optional hooks are executable and use `#!/bin/bash`
- [ ] `scripts/validate.py` passes
- [ ] Public docs mention the pack only after the manifest and README exist

