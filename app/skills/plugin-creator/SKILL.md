---
name: plugin-creator
description: "Creates opt-in plugin packs with manifests + module scaffolding for Claude/Codex. Triggers: new plugin, plugin pack, plugin scaffold."
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
  "name": "memory-pack",
  "description": "Domain plugin pack for persistent cross-session memory.",
  "version": "1.0.0",
  "domain": "memory",
  "type": "plugin-pack",
  "status": "experimental",
  "requires": {
    "ai-toolkit": ">=1.0.0",
    "claude-code": ">=1.0.33"
  },
  "includes": {
    "agents": [],
    "skills": ["mem-search"],
    "rules": [],
    "hooks": ["observation-capture.sh", "session-summary.sh"]
  },
  "hook_events": {
    "observation-capture.sh": "PostToolUse",
    "session-summary.sh": "Stop"
  }
}
```

The two hooks are files the pack **owns**, under `app/plugins/memory-pack/hooks/`.
That is what makes this a pack rather than a bookmark: installing it puts scripts
on disk and entries in the host's hook config that were not there before.

## Authoring Rules

- **MUST** keep packs domain-scoped — "memory-pack", "mobile-pack", not "misc-pack"
- **MUST** install something the core install does not already provide. `ai-toolkit install` links every core skill and agent, so a pack whose `includes` names only core assets installs **zero files** and is a no-op. Verify before shipping: install core into a throwaway `HOME`, then install the pack, and confirm the file count changed. Nine packs were removed in v4.20.0 for failing exactly this check.
- **MUST** reference existing toolkit assets rather than forking them — but referencing alone is not a pack. A pack earns its existence through hooks, scripts, or assets of its own; the reference list is context, not content.
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
- [ ] **The pack installs a non-zero number of files.** `ai-toolkit install` into a throwaway `HOME`, then `plugin install <name>`, and confirm the reported file count is above zero on every runtime the pack claims. A pack reporting `(0 file items)` does nothing and must not ship.
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
