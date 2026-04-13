---
title: "SOP: Claude Toolkit Maintenance"
category: procedures
service: ai-toolkit
tags: [sop, maintenance, agents, skills, install]
version: "1.4.4"
created: "2026-03-23"
last_updated: "2026-04-13"
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

By default, `--local` installs Claude Code configs only:
- `CLAUDE.md` — project-specific rules template (only if missing)
- `.claude/settings.local.json` — MCP servers, env vars, permissions (only if missing, initialized with MCP defaults)
- `.claude/constitution.md` — toolkit constitution **injected** via markers (preserves user content)

To also install editor configs, use `--editors`:

```bash
ai-toolkit install --local --editors all                  # all supported editors
ai-toolkit install --local --editors cursor,aider         # specific editors only
```

Supported editors: `cursor`, `windsurf`, `cline`, `roo`, `aider`, `augment`, `copilot`, `antigravity`, `codex`.

To restrict which language rules are injected, use `--lang`:

```bash
ai-toolkit install --local --lang python,typescript
ai-toolkit install --local --lang python --editors all  # language rules propagated to all editors
```

When `--editors` is combined with `--lang` (or auto-detected languages), language rules are propagated to all configured editors as `ai-toolkit-lang-<lang>` files — not just Claude's `CLAUDE.md`. Similarly, registered custom rules (`~/.softspark/ai-toolkit/rules/`) are propagated to directory-based editor configs as `ai-toolkit-custom-<name>` files.

**Note:** Hooks are global-only — merged into `~/.claude/settings.json` by `ai-toolkit install`. Project-local `--local` does not install hooks; any legacy `.claude/hooks.json` is removed automatically.

**Input validation (v1.4.2):** `--only`, `--skip`, `--editors`, and `--lang` are validated on input; an invalid value exits with a clear error before any changes are made.

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
ai-toolkit update --only agents,hooks                  # re-apply only specific components
ai-toolkit update --local                              # refresh project-local Claude Code configs; auto-detects editors from existing project files (no --editors needed)
ai-toolkit update --local --editors cursor,windsurf   # override auto-detection and target specific editors
ai-toolkit update --list                               # dry-run: show what would change
```

When running `update --local`, the CLI inspects existing config files (e.g. `.cursor/rules`, `.aider.conf.yml`) to determine which editors are present and refreshes only those — no flags required.

---

## Register a Rule from Another Repo

Third-party repos (jira-mcp, rag-mcp, etc.) can register their own rules globally:

```bash
ai-toolkit add-rule ./my-project-rules.md
# → copies to ~/.softspark/ai-toolkit/rules/my-project-rules.md

ai-toolkit update
# → injects the rule into ~/.claude/CLAUDE.md and all global editor configs

ai-toolkit update --local
# → also propagates as ai-toolkit-custom-<name> to directory-based editors (Cursor, Windsurf, Cline, Roo, Augment, Antigravity)
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
ai-toolkit plugin list                             # show available packs
ai-toolkit plugin install --editor claude <name>  # install for Claude global target
ai-toolkit plugin install --editor codex <name>   # install for Codex global target
ai-toolkit plugin install --editor all --all      # install all 11 packs for both runtimes
ai-toolkit plugin update --editor all --all       # re-apply all installed packs after toolkit updates
ai-toolkit plugin clean <name>                    # prune data older than 90 days
ai-toolkit plugin clean <name> --days 30  # custom retention
ai-toolkit plugin remove --editor codex <name>    # remove from one runtime only
ai-toolkit plugin status --editor all             # show installed packs with runtime details
```

Install copies hooks/scripts, verifies agents+skills are linked, merges hooks into the selected runtime config, and runs init scripts. For Codex, the selected runtime is the global `HOME` layer (`~/AGENTS.md`, `~/.agents/`, `~/.codex/hooks.json`). Update removes and reinstalls from current source while preserving plugin data. Clean prunes old plugin data. Remove reverses install for the selected runtime but leaves plugin data intact. Core agents/skills are never removed.

Memory-pack auto-prunes observations older than 90 days on every session end (configurable via `MEMORY_RETENTION_DAYS`).

State is tracked per runtime in `~/.softspark/ai-toolkit/plugins.json`. After every `ai-toolkit update`, also run `ai-toolkit plugin update --editor all --all` if plugin packs are installed.

## Adding a KB Document

Follow the `documentation-standards` knowledge skill (`app/skills/documentation-standards/SKILL.md`) for full spec. Quick checklist:

1. **Choose category directory:** `kb/reference/`, `kb/howto/`, `kb/procedures/`, `kb/troubleshooting/`, `kb/best-practices/`, or `kb/planning/`
2. **Create file:** kebab-case name, no dates in filename
3. **Add frontmatter** with all 7 required fields: `title`, `category`, `service`, `tags`, `created`, `last_updated`, `description`
4. **Write in English**
5. **Validate:** `scripts/validate.py` (checks all `kb/**/*.md` frontmatter)

**Documents without valid frontmatter will fail `validate.py` and block CI.**

## Adding Scripts to Skills

1. Create `app/skills/<skill-name>/scripts/<script>.py` (stdlib only, JSON output)
2. `chmod +x` the script
3. Reference: `` python3 ${CLAUDE_SKILL_DIR}/scripts/script.py . ``

## Cross-Editor Verification (Mandatory)

**Every addition — skill, hook, MCP template, agent, rule — MUST be verified against all supported editors before merge.**

This toolkit targets 10 platforms. Each has its own config format, file path conventions, and runtime capabilities. A feature that works in Claude Code may silently break in Cursor, Codex, or Copilot if the editor's official spec diverges.

### Verification checklist

When adding or modifying any toolkit component:

1. **Check official docs** — before implementing, fetch the editor's current documentation (web search or Context7) to confirm the config format, file path, and feature support haven't changed
2. **Validate output format** — ensure the generated file matches what the editor expects (JSON schema, TOML structure, MDC frontmatter, directory naming)
3. **Test scope rules** — verify project-local vs global behavior matches the editor's own scope model
4. **Confirm feature parity** — if the feature relies on runtime primitives (hooks, MCP, agent delegation), check whether the target editor supports them; document gaps in `kb/reference/` if not

### Editor documentation sources

| Editor | Where to verify |
|--------|----------------|
| Claude Code | `docs.anthropic.com/claude-code` |
| Cursor | `docs.cursor.com` |
| Windsurf | `docs.codeium.com/windsurf` |
| GitHub Copilot | `docs.github.com/copilot` |
| Gemini CLI | `github.com/google-gemini/gemini-cli` |
| Cline | `github.com/cline/cline` |
| Roo Code | `github.com/RooVetGit/Roo-Code` |
| Aider | `aider.chat` |
| Augment | `docs.augmentcode.com` |
| Codex CLI | `github.com/openai/codex` |
| Google Antigravity | `developers.google.com/project-idx` |

### When to do this

- Adding a new skill → verify it renders correctly for Codex `.agents/skills/` and all directory-based editors
- Adding a new hook → verify event name is valid in Claude and check `.codex/hooks.json` compatibility
- Adding a new MCP template → verify it installs correctly for all 8 native adapters (`mcp_editors.py`)
- Modifying generator output → check that every editor-specific generator still produces valid output
- Adding a new editor → verify ALL existing features render correctly for the new target

### Anti-pattern

Do NOT assume an editor's format based on memory or past behavior. Editors ship breaking changes to their config surfaces. Always verify against current official docs before implementation.

---

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
npm run generate:all          # FIRST: regenerate AGENTS.md, Codex rules, llms.txt, and platform configs
scripts/validate.py           # then validate — must pass before commit
npm test                      # then test — must pass before commit
```

Run `generate:all` before validate and test so that generated artifacts are current when
the metadata contract tests run. This includes `.agents/rules/ai-toolkit-*.md` via
`generate_codex_rules.py . --skip-cleanup` and `.clinerules/ai-toolkit-*.md` via
`generate_cline_rules.py . --skip-cleanup`, which refresh the standard generated rule
sets without deleting custom overlays such as registered repo-specific rules or
language-specific files. Committing without regenerating first causes artifact drift and
fails CI.

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

### 5. Check for artifact drift

```bash
git diff --stat
```

Review the diff to confirm that all generated files (`AGENTS.md`, `llms.txt`, platform
configs) reflect the current state. If `generate:all` produced unexpected changes,
investigate before staging.

### 6. Commit and tag

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
