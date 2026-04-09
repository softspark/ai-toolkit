---
title: "SOP: Claude Toolkit Maintenance"
category: procedures
service: ai-toolkit
tags: [sop, maintenance, agents, skills, install]
version: "1.0.0"
created: "2026-03-23"
last_updated: "2026-04-02"
description: "Standard operating procedures for installing, maintaining, and evolving the ai-toolkit."
---

# SOP: Claude Toolkit Maintenance

## Init Repository (New Project)

Use this when starting a new project that should use the toolkit.

**Prerequisites:** toolkit installed globally (`ai-toolkit install` already done once).

```bash
cd /path/to/new-project
ai-toolkit install --local
```

This creates/updates:
- `CLAUDE.md` — project-specific rules template (only if missing)
- `.claude/settings.local.json` — MCP servers, env vars, permissions (only if missing, initialized with MCP defaults)
- `.claude/constitution.md` — toolkit constitution **injected** via markers (preserves user content)
- `.github/copilot-instructions.md` — GitHub Copilot rules (marker-injected)
- `.clinerules` — Cline rules (marker-injected)
- `.roomodes` — Roo Code custom modes (generated)
- `.aider.conf.yml` — Aider configuration (generated)
- `.git/hooks/pre-commit` — Safety fallback for quality gates (generated)

**Note:** Hooks are global-only — merged into `~/.claude/settings.json` by `ai-toolkit install`. Project-local `--local` does not install hooks; any legacy `.claude/hooks.json` is removed automatically.

Then edit `CLAUDE.md`:
```markdown
# My Project

## Overview
What this project does.

## Tech Stack
- Language: TypeScript
- Framework: Next.js
- Database: PostgreSQL

## Commands
# Dev: npm run dev
# Test: npm test
# Build: npm run build
```

---

## Install Toolkit Globally

Run once per machine. Installs into `~/.claude/` — available in all projects.

```bash
npm install -g @softspark/ai-toolkit   # once per machine
ai-toolkit install                      # sets up ~/.claude/
```

What `install` and `update` do (merge-friendly — user content never overwritten):

| Component | Strategy | User collision |
|-----------|----------|---------------|
| `agents/*.md` | Per-file symlinks into `~/.claude/agents/` | User file with same name preserved (toolkit skipped) |
| `skills/*/` | Per-directory symlinks into `~/.claude/skills/` | User dir with same name preserved |
| `settings.json` hooks | JSON merge via `merge-hooks.py` | User hooks + settings preserved, toolkit entries tagged `_source: ai-toolkit` |
| `constitution.md` | Marker injection via `inject_section_cli.py` | User content outside `<!-- TOOLKIT:* -->` markers untouched |
| `ARCHITECTURE.md` | Marker injection via `inject_section_cli.py` | Same as above |
| `CLAUDE.md` | Marker injection of `app/rules/*.md` via `inject_rule_cli.py` | User content outside markers untouched |

Re-running updates only toolkit content. Old whole-directory symlinks are auto-upgraded to per-file on next run.

---

## Update Toolkit

After a new npm release:

```bash
npm install -g @softspark/ai-toolkit@latest
ai-toolkit update
```

`update` is a semantic alias for `install` — use it for all re-apply flows. Supports the same flags:

```bash
ai-toolkit update --only agents,hooks   # re-apply only specific components
ai-toolkit update --local               # refresh project-local configs (auto-detects editors from existing files)
ai-toolkit update --list                # dry-run: show what would change
```

---

## Register a Rule from Another Repo

Third-party repos (jira-mcp, rag-mcp, etc.) can register their own rules globally:

```bash
ai-toolkit add-rule ./my-project-rules.md
# → copies to ~/.ai-toolkit/rules/my-project-rules.md

ai-toolkit update
# → injects the rule into ~/.claude/CLAUDE.md, ~/.cursor/rules, Windsurf, Gemini
```

To unregister (removes from registry **and** strips the block from CLAUDE.md):

```bash
ai-toolkit remove-rule my-project-rules
```

Rule names derive from the filename (`my-project-rules.md` → marker `TOOLKIT:my-project-rules`).

---

## Adding a New Agent

1. Create `app/agents/<agent-name>.md` with YAML frontmatter:
   ```yaml
   ---
   name: agent-name
   description: "When to use this agent. Triggers: keyword1, keyword2."
   tools: Read, Write, Edit, Bash
   model: opus
   skills: skill-1, skill-2
   ---
   ```
2. Write agent instructions below frontmatter
3. Update `kb/reference/agents-catalog.md`
4. Update `app/ARCHITECTURE.md` counts
5. Run `scripts/validate.py`
6. Regenerate: `scripts/generate_agents_md.py > AGENTS.md`

## Adding a New Skill

1. Create `app/skills/<skill-name>/SKILL.md` with frontmatter:
   ```yaml
   ---
   name: skill-name
   description: "Third-person description. Max 1024 chars."
   effort: medium
   disable-model-invocation: true   # task skill
   user-invocable: false            # knowledge skill
   ---
   ```
2. Update `kb/reference/skills-catalog.md` and `app/ARCHITECTURE.md`
3. Run `scripts/validate.py`

## Adding a New Hook

Preferred path:

```bash
/hook-creator [event or hook description]
```

Manual path:

1. Create `app/hooks/<hook-name>.sh`
2. Register the hook under `app/hooks.json`
3. Run `scripts/validate.py`
4. Run `scripts/doctor.py`
5. Update `kb/reference/hooks-catalog.md`, `README.md`, and any affected architecture docs

Use `PreToolUse` for blocking validations, `PostToolUse` for non-blocking feedback, `UserPromptSubmit` for prompt governance, and `PreCompact` / `SessionEnd` for context preservation and handoff.

## Managing Plugins

```bash
ai-toolkit plugin list               # show available packs
ai-toolkit plugin install <name>     # install a single pack
ai-toolkit plugin install --all      # install all 11 packs
ai-toolkit plugin update <name>      # update a pack (preserves data)
ai-toolkit plugin update --all       # update all installed packs
ai-toolkit plugin clean <name>       # prune data older than 90 days
ai-toolkit plugin clean <name> --days 30  # custom retention
ai-toolkit plugin remove <name>      # remove a pack
ai-toolkit plugin status             # show installed packs with data stats
```

Install copies hooks/scripts, verifies agents+skills are linked, merges hooks into `settings.json`, and runs init scripts. Update removes and reinstalls from current source (data preserved). Clean prunes old plugin data. Remove reverses install but leaves data intact. Core agents/skills are never removed.

Memory-pack auto-prunes observations older than 90 days on every session end (configurable via `MEMORY_RETENTION_DAYS`).

State tracked in `~/.ai-toolkit/plugins.json`.

## Adding a KB Document

Follow the `documentation-standards` knowledge skill (`app/skills/documentation-standards/SKILL.md`) for full spec. Quick checklist:

1. **Choose category directory:** `kb/reference/`, `kb/howto/`, `kb/procedures/`, `kb/troubleshooting/`, or `kb/best-practices/`
2. **Create file:** kebab-case name, no dates in filename
3. **Add frontmatter** with all 7 required fields: `title`, `category`, `service`, `tags`, `created`, `last_updated`, `description`
4. **Write in English**
5. **Validate:** `scripts/validate.py` (checks all `kb/**/*.md` frontmatter)

**Documents without valid frontmatter will fail `validate.py` and block CI.**

## Adding Scripts to Skills

1. Create `app/skills/<skill-name>/scripts/<script>.py` (stdlib only, JSON output)
2. `chmod +x` the script
3. Reference: `` python3 ${CLAUDE_SKILL_DIR}/scripts/script.py . ``

## Quality Checks

```bash
scripts/validate.py           # agents, skills, hooks, core files, metadata counts
scripts/doctor.py             # install health, hooks, benchmark freshness, artifact drift diagnostics
scripts/benchmark_ecosystem.py --offline   # ecosystem benchmark snapshot
scripts/benchmark_ecosystem.py --dashboard-json --out benchmarks/ecosystem-dashboard.json
scripts/harvest_ecosystem.py --offline     # refresh machine-readable ecosystem harvest
scripts/evaluate_skills.py    # skill classification report
npm test                      # bats test suite (all workstreams)
```

Or via CLI:

```bash
ai-toolkit validate           # integrity check
ai-toolkit doctor             # install health diagnostics
ai-toolkit benchmark-ecosystem --offline   # benchmark snapshot
```

## Modifying Components

Changes propagate instantly to all machines via symlinks. After any change:

```bash
scripts/validate.py           # must pass before commit
npm test                      # must pass before commit
```

If you added/removed agents or skills, also regenerate derived artifacts:

```bash
npm run generate:all          # regenerates AGENTS.md, llms.txt, all platform configs
```

## Release Checklist

Follow this sequence before every `npm publish` / `git tag`:

### 1. Bump version

```bash
# Edit package.json version field (semver: X.Y.Z)
# Add entry to CHANGELOG.md
```

### 2. Regenerate all artifacts

```bash
npm run generate:all
```

### 3. Validate and test

```bash
npm run validate    # scripts/validate.py — agents, skills, counts
npm test            # full bats suite including metadata contracts and CLI tests
```

### 4. Verify counts are in sync

The metadata contract tests (`tests/test_metadata_contracts.bats`) catch drift
automatically. If they fail, fix the stale numbers before continuing.

### 5. Commit and tag

```bash
git add -A
git commit -m "chore: release vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

The publish workflow (`.github/workflows/publish.yml`) picks up the tag, runs full
validation + tests, regenerates AGENTS.md + llms.txt, and publishes to npm.

## Model Tiers

| Agent Type | Model | Examples |
|-----------|-------|---------|
| Complex reasoning | opus | orchestrator, backend-specialist, security-auditor |
| Pattern-following | sonnet | documenter, explorer-agent, data-analyst |

## Uninstall

```bash
ai-toolkit uninstall    # strips toolkit components from ~/.claude/
```

What `uninstall` does:
- Removes per-file agent symlinks (user agents preserved)
- Removes per-directory skill symlinks (user skills preserved)
- Strips toolkit hook entries from `settings.json` (user hooks + settings preserved)
- Strips toolkit markers from `constitution.md` and `ARCHITECTURE.md` (user content preserved; empty files removed)
- `~/.claude/CLAUDE.md` preserved (contains your custom rules + toolkit rule markers)
- Empty `agents/` and `skills/` directories cleaned up
