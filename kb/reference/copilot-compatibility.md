---
title: "AI Toolkit - GitHub Copilot Compatibility"
category: reference
service: ai-toolkit
tags: [copilot, compatibility, install, skills, prompts, instructions, agents, hooks]
version: "1.1.0"
created: "2026-07-15"
last_updated: "2026-09-23"
description: "GitHub Copilot instructions, agents, skills, prompts and hooks, with CLI, cloud agent and VS Code compatibility boundaries."
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
| Shared rules | root `AGENTS.md` | Read by CLI, cloud agent, VS Code Chat and GitHub.com code review |

## Surface Loading Semantics

The customization surfaces do **not** all cost context the same way. This
is the practical difference that governs token usage and any perceived
"double loading":

| Surface | Enters context… | Passive cost |
|---------|-----------------|--------------|
| `copilot-instructions.md` | Every chat request in the repo | Always-on |
| `*.instructions.md` with `applyTo: "**"` | Every request (glob matches all files) | Effectively always-on |
| `*.instructions.md` with a scoped glob (e.g. `**/*.py`) | Only when a matching file is in context | Path-scoped |
| `*.prompt.md` | **Only** when the user runs `/<name>` | None until invoked |
| `SKILL.md` | Body loads on relevant automatic or explicit invocation | Name and description participate in discovery |
| `*.agent.md` | When selected or delegated to as a custom agent | Discovery metadata; body on use |

Instructions are auto-added to requests as soon as their `applyTo` glob matches;
skill bodies and prompt bodies load on demand. Skill discovery metadata still
uses context; progressive disclosure does not mean zero passive cost.

## Prompt ↔ Skill Duplication

Profiles with prompts retain existing `/ai-toolkit-<name>` prompt entry points.
Native skills also support slash invocation by their `name`, such as `/review`,
in current VS Code and Copilot CLI. Prefer the native skill when it needs bundled
scripts or references: a prompt file does not carry the skill directory.

The generator preserves the source skill's `user-invocable` and
`disable-model-invocation` booleans. VS Code documents these controls explicitly:
`user-invocable: false` hides the slash entry; `disable-model-invocation: true`
prevents automatic selection. Omitted fields retain the client's defaults.
The CLI guide documents slash invocation but does not specify these booleans;
do not treat them as a cross-client permission boundary. Source Claude tool
allowlists are not copied into Copilot tool preapprovals.

Prompt and skill bodies come from the same source with different execution
notes. Their full bodies load only when used; selecting both in one turn can
repeat instructions. Keeping prompts preserves existing entry points and does
not imply that native skills lack slash commands.

## Compatibility Read Paths

Copilot also discovers project `.claude/skills` and `.agents/skills`, and
personal `~/.agents/skills`. ai-toolkit still materializes self-contained native
skills under `.github/skills` (and under the active Copilot config root for
global installs) so that bundled assets and helper scripts remain available and
`COPILOT_HOME` sessions do not depend on fallback discovery. VS Code additionally
documents personal `~/.claude/skills`. Installing several editor integrations can
leave equivalent skills in more than one discovery root; inspect the client's
loaded skills rather than assuming these roots are mutually exclusive.

## Generated, Git-Ignored Artifacts

All Copilot outputs are build products, regenerated on every install/generate,
and listed in `.gitignore`:

- `.github/copilot-instructions.md`
- `.github/instructions/`
- `.github/prompts/`
- `.github/agents/`
- `.github/skills/`
- `.github/hooks/`

The next `ai-toolkit install --editors copilot` or generator run recreates managed
files. These directories can also contain user-authored files; being ignored by
Git does not make an entire directory disposable. The generator cleans stale
managed entries and byte-exact historical ai-toolkit files while preserving
user-authored files. Cloud agent can read only files present in its checkout;
ignored local output is not automatically available to a cloud job.

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

## Hook Runtime Boundaries

The generated version-1 JSON remains the CLI/cloud format. VS Code also reads
that format, maps camelCase events and platform commands, and supplies its own
snake_case payload fields. CLI also accepts PascalCase configuration and can
send the same input shape, so `hook_event_name` does not identify the client.
The runtime preserves flat permission/context fields and adds an equivalent
`hookSpecificOutput` envelope for PascalCase input. Terminal protection
recognizes CLI `bash`/`powershell` and VS Code terminal tools. File-change
reminders filter VS Code tool names locally because its hook matchers are
currently ignored.
Stop decisions preserve both output forms and respect `stop_hook_active` in
either input format; the existing bounded retry counter remains a fallback.

The CLI reference describes a single `JSON.parse` of hook output. VS Code's
[hook result parser](https://github.com/microsoft/vscode/blob/main/extensions/copilot/src/extension/chat/vscode-node/chatHookService.ts)
retains non-common fields and reads event output from `hookSpecificOutput`.
Both views carry the same decision and context in one JSON object.

CLI/cloud keep their top-level decision and context fields. Cloud hooks execute
in an ephemeral noninteractive Linux environment; CLI notification and permission
events do not provide equivalent cloud behavior. VS Code's documented event
list does not include `postToolUseFailure`, so that recovery hook remains a
CLI/cloud capability. No second hook config is emitted, avoiding duplicate
execution in clients that read both formats.

## Reviewed Upstream Contracts (2026-09-23)

- [Instruction support matrix](https://docs.github.com/en/copilot/reference/custom-instructions-support):
  CLI reads repository, scoped and personal instructions; GitHub.com code review
  reads scoped instructions and `AGENTS.md`. VS Code code review currently lists
  only repository-wide instructions, so it must not inherit that GitHub.com claim.
- [VS Code skills](https://code.visualstudio.com/docs/agent-customization/agent-skills):
  slash invocation, invocation controls, supported roots and progressive loading.
- [Copilot CLI skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills):
  CLI discovery, slash usage and tool preapproval distinction.
- [VS Code hooks](https://code.visualstudio.com/docs/agent-customization/hooks) and
  [payload reference](https://code.visualstudio.com/docs/agents/reference/hooks-reference):
  CLI configuration import, editor payloads and event-specific responses.
- [GitHub hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference):
  CLI/cloud configuration and execution differences. Enterprise policy hooks,
  HTTP hooks and direct `exec` entries are available but are not emitted by this
  command-hook generator.
- [Custom agents](https://docs.github.com/en/copilot/reference/custom-agents-configuration):
  the body limit is 30,000 characters, not UTF-8 bytes. `infer` is retired; the
  generator does not emit it and requires no migration. IDE `handoffs` and
  `argument-hint` are not portable cloud agent settings.

SOP classification: skill invocation controls are **B** (integrated); VS Code
hook runtime adaptation is **F** (integrated); redirected documentation paths
are **A**. Retired `infer` is **D**, but no toolkit output uses it. Enterprise
policy and HTTP hook surfaces are **C** (not adopted).

## Verification

- `scripts/generate_copilot.py` / `generate_copilot_hooks.py` contract tests
  (`tests/test_copilot.bats`, `tests/test_copilot_hooks.bats`).
- Release layout check in `kb/procedures/sop-release-verification.md` asserts the
  `.github/{agents,skills,instructions,prompts,hooks}` surfaces.
- `validate.py --strict` + `audit_skills.py --ci` in CI.

## Related

- `kb/reference/global-install-model.md`
- `kb/reference/supported-tools-registry.md`
- `kb/reference/codex-cli-compatibility.md`
- `kb/reference/opencode-compatibility.md`
- `kb/reference/skills-catalog.md`
- `kb/reference/agents-catalog.md`
