---
title: "AI Toolkit - GitHub Copilot Compatibility"
category: reference
service: ai-toolkit
tags: [copilot, compatibility, install, skills, prompts, instructions, agents, hooks]
version: "1.0.0"
created: "2026-07-15"
last_updated: "2026-07-15"
description: "Reference for how ai-toolkit integrates with GitHub Copilot — the five .github/ surfaces, their runtime context-loading semantics, and why the same skill is emitted as both a prompt file and a skill directory."
---

# AI Toolkit - GitHub Copilot Compatibility

## Summary

`ai-toolkit install --local --editors copilot` emits native GitHub Copilot
customization files under `.github/`. Copilot is the toolkit's widest-surface
editor target: a single skill can materialize into up to three distinct Copilot
mechanisms (path-scoped instruction, invokable prompt, on-demand skill). All
emitted paths are generated build artifacts and are `.gitignore`d — they are not
committed source. This document explains what each surface is, **when each one
enters the model context**, and why the same skill body appears in more than one
file. Install/profile behavior is owned by `kb/reference/global-install-model.md`;
config-path and capability tracking by `kb/reference/supported-tools-registry.md`.

## Generated Surfaces

| Surface | Path | Copilot mechanism |
|---------|------|-------------------|
| Repo-wide instructions | `.github/copilot-instructions.md` | Always-on repository custom instructions |
| Path-scoped instructions | `.github/instructions/ai-toolkit-*.instructions.md` | Custom instructions gated by an `applyTo` glob |
| Prompt files | `.github/prompts/ai-toolkit-*.prompt.md` | Reusable prompts, invoked as `/name` |
| Native agents | `.github/agents/ai-toolkit-*.agent.md` | Custom agents in the agent picker |
| Portable skills | `.github/skills/ai-toolkit-*/SKILL.md` (+ `reference/`, `scripts/`) | Agent Skills, injected on demand |
| Lifecycle hooks | `.github/hooks/ai-toolkit.json` + runtime | Version-1 Copilot hooks (profile ≥ `standard`) |
| Shared rules | root `AGENTS.md` | Read by Copilot code review and CLI |

## Surface Loading Semantics

The five customization surfaces do **not** all cost context the same way. This
is the practical difference that governs token usage and any perceived
"double loading":

| Surface | Enters context… | Passive cost |
|---------|-----------------|--------------|
| `copilot-instructions.md` | Every chat request in the repo | Always-on |
| `*.instructions.md` with `applyTo: "**"` | Every request (glob matches all files) | Effectively always-on |
| `*.instructions.md` with a scoped glob (e.g. `**/*.py`) | Only when a matching file is in context | Path-scoped |
| `*.prompt.md` | **Only** when the user runs `/<name>` | None until invoked |
| `SKILL.md` | **Only** when Copilot chooses to use the skill (progressive disclosure) | None until triggered |
| `*.agent.md` | Only when that agent is selected in the picker | None until selected |

Instructions are auto-added to requests as soon as their `applyTo` glob matches;
skills and prompts are pull-based, never injected passively.

## Prompt ↔ Skill Duplication

Every user-invocable skill is emitted **both** as a `.github/prompts/*.prompt.md`
(so it is available as a `/slash-command`) **and** as a
`.github/skills/<name>/SKILL.md` directory (so Copilot can auto-trigger it with
its bundled `scripts/` and `reference/` assets). The two bodies are byte-identical
after their frontmatter and Copilot execution-notes header; the differences are:

- the prompt carries only a `description`; the skill adds `name` and bundles the
  runnable assets the prompt does not ship;
- the prompt's execution note treats the current request as task input, the
  skill's note resolves relative paths against its own directory.

**This is intentional, not a stale leftover, and does not cause a persistent
double-load:**

- Neither surface is always-on. The prompt loads only on explicit `/invoke`; the
  skill loads only on trigger. Neither sits in `copilot-instructions.md` or in an
  always-matching `applyTo`, so the shared body carries **zero** passive context
  cost.
- The same skill is registered from a **single** root (`.github/skills`), not
  duplicated across `.claude/skills` or `.agents/skills` in the same repo, so
  there is no duplicate skill registration.
- The one edge case is a single turn where the user runs `/<name>` **and** Copilot
  autonomously pulls the matching skill in the same request. That is a one-shot
  redundancy of identical text — wasted tokens for that turn only, with no
  conflicting instructions and no persistent effect.

Neither surface can replace the other: the prompt has no bundled scanner or
reference material, and the skill directory is not exposed as a slash command.
The body is duplicated so each surface is self-contained.

## Compatibility Read Paths

Copilot also discovers project `.claude/skills` and `.agents/skills`, and
personal `~/.agents/skills`. ai-toolkit still materializes self-contained native
skills under `.github/skills` (and under the active Copilot config root for
global installs) so that bundled assets and helper scripts remain available and
`COPILOT_HOME` sessions do not depend on fallback discovery. The toolkit does not
write the same skill into two roots at once, so fallback discovery never produces
a duplicate registration.

## Generated, Git-Ignored Artifacts

All Copilot outputs are build products, regenerated on every install/generate,
and listed in `.gitignore`:

- `.github/copilot-instructions.md`
- `.github/instructions/`
- `.github/prompts/`
- `.github/agents/`
- `.github/skills/`
- `.github/hooks/`

Deleting them locally is safe (they are untracked and ignored); the next
`ai-toolkit install --editors copilot` or generator run recreates them. The
generator also cleans stale managed entries and byte-exact historical ai-toolkit
files while preserving user-authored files.

## Install & Profiles

Authoritative behavior lives in `kb/reference/global-install-model.md`. In brief:

- **All profiles (including `minimal`)** emit root `AGENTS.md`,
  `.github/copilot-instructions.md`, native `.github/agents`, and portable
  self-contained `.github/skills`.
- **`standard`, `strict`, `full`** additionally emit scoped `.github/instructions`,
  `.github/prompts`, and native version-1 `.github/hooks`.
- **`minimal`** omits instructions, prompts, and hooks.

Moving an existing project down to `minimal` removes only marked or byte-exact
historical ai-toolkit instructions/prompts/hooks; unmanaged project files stay.

## Auto-Detection

The installer treats Copilot as configured when any of these markers exist:
`.github/copilot-instructions.md`, `.github/instructions`, `.github/prompts`,
`.github/agents`, `.github/skills`, `.github/hooks`, `.github/mcp.json`.
`ai-toolkit update` then picks up Copilot automatically.

## Generators & CLI

Copilot has no dedicated `ai-toolkit copilot-*` subcommand; it is produced by
`ai-toolkit install --editors copilot` (add `--local` for project scope) or by
running the generators directly:

- `scripts/generate_copilot.py` — instructions, prompts, native agents, and
  portable skill directories (`> .github/copilot-instructions.md` with no target
  argument; multi-surface emission with a target directory).
- `scripts/generate_copilot_hooks.py` — version-1 hook config plus a
  self-contained repository/config-root runtime.

## Behavioral Limits

- Prompt files are available only in VS Code, Visual Studio, and JetBrains IDEs;
  GitHub.com and the CLI use instructions, skills, agents, and `AGENTS.md`.
- Custom agents emit native `.agent.md` with `name` and `description`; `tools` is
  omitted rather than guessing editor-specific aliases.
- Prompt and skill bodies strip Claude-only interpolation (`$ARGUMENTS`,
  `CLAUDE_SKILL_DIR`) and delegation APIs; hooks use the GitHub version-1 schema
  with camelCase event names.

## Verification

- `scripts/generate_copilot.py` / `generate_copilot_hooks.py` contract tests
  (`tests/test_copilot.bats`, `tests/test_copilot_hooks.bats`).
- Release layout check in `kb/procedures/release-verification-sop.md` asserts the
  `.github/{agents,skills,instructions,prompts,hooks}` surfaces.
- `validate.py --strict` + `audit_skills.py --ci` in CI.

## Related

- `kb/reference/global-install-model.md`
- `kb/reference/supported-tools-registry.md`
- `kb/reference/codex-cli-compatibility.md`
- `kb/reference/opencode-compatibility.md`
- `kb/reference/skills-catalog.md`
- `kb/reference/agents-catalog.md`
