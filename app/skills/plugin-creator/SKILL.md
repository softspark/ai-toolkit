---
name: plugin-creator
description: "Creates experimental opt-in plugin packs with manifests, conventions, and optional module scaffolding for Claude and Codex runtimes"
effort: high
disable-model-invocation: true
argument-hint: "[plugin pack name or domain]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Plugin Creator

$ARGUMENTS

Create a new experimental opt-in plugin pack following ai-toolkit conventions.

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

- **MUST** keep packs domain-scoped — "security-pack", "mobile-pack", not "misc-pack"
- **MUST** reference existing toolkit assets before duplicating — packs extend, they do not fork
- **MUST** ship a valid `plugin.json` with `name`, `description`, `version`, `domain`, `type`, `status`, and `includes`
- **NEVER** have a pack silently alter default global install behavior — experimental packs are **opt-in only**
- **NEVER** copy an agent or skill file into a pack when referencing the toolkit-level version suffices; duplication creates drift
- **CRITICAL**: optional hooks bundled in a pack must be executable (`chmod +x`) and documented in the pack README with their install semantics
- **MANDATORY**: the pack README names supported runtimes (`claude`, `codex`, or `all`) and explains that the pack is not part of the default install

## Gotchas

- Plugin packs are discovered by scanning `app/plugins/*/plugin.json`. A pack with a missing or malformed `plugin.json` is silently ignored — no error surfaces. Check with `ls app/plugins/*/plugin.json` and `jq . app/plugins/*/plugin.json`.
- The `status: experimental` flag gates visibility in some install paths — marking a pack "stable" before it is audited can make it install by default for every user. Keep `experimental` until the pack has eaten its own dogfood.
- Packs that include hooks inherit the toolkit's hook merge rules (`_source: "ai-toolkit"`). Hooks without the `_source` tag survive `ai-toolkit update` and can leak into other packs' merge pools.
- Versions in `plugin.json` are separate from the toolkit version. A pack at v1.2 running inside toolkit v2.11 may still satisfy `requires.ai-toolkit: >=1.0.0` but mean nothing about actual compatibility — test against the current toolkit before tagging.
- Codex-runtime packs need matching `.agents/rules/` and `.codex/hooks.json` variants; a plugin that only ships Claude assets looks broken under Codex CLI. Declare runtime support explicitly.

## Validation Checklist

- [ ] `app/plugins/<plugin-name>/plugin.json` exists and parses as JSON
- [ ] `README.md` explains purpose, included assets, and opt-in flow
- [ ] Referenced agents and skills exist or are created in the same change set
- [ ] Optional hooks are executable and use `#!/bin/bash`
- [ ] `scripts/validate.py` passes
- [ ] Public docs mention the pack only after the manifest and README exist

## When NOT to Use

- For an individual **skill** (slash command or knowledge doc) — use `/skill-creator`
- For an individual **agent** — use `/agent-creator`
- For a single **hook** (not a pack) — use `/hook-creator`
- For an MCP server — use `/mcp-builder`
- For modifying an existing plugin pack — edit its files directly; this skill is create-only
