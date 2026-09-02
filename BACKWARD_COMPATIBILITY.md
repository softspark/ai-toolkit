<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu) -->

# Backward Compatibility Contract

`@softspark/ai-toolkit` installs into `~/.claude/` and `~/.softspark/ai-toolkit/`
on machines this repository cannot reach. Users keep state there — registered
rules, injected hooks and MCP templates, `state.json`, per-project registrations,
usage stats — and no release can migrate it for them.

The npm registry reported 3,909 downloads in the 30 days to 2026-08-05, with
traffic on 29 of those days across 106 published versions. Whatever a release
breaks, it breaks for people who are not in this room.

This document says which surfaces are load-bearing and what it costs to change one.

## Protected surfaces

Changing any of these is a **breaking change** and needs the deprecation path below.

### 1. Skill and agent names

108 skill directories under `app/skills/` and 44 agent files under `app/agents/`.
Skill names are the user's slash commands (`/review`, `/debug`, `/tdd`) and appear
in muscle memory, shell aliases, CI invocations, and other people's docs. Agent
names appear in skill frontmatter (`agent:`) and in `Agent` tool calls.

A rename is a break even when the behaviour is identical.

### 2. Skill frontmatter fields and their meaning

| Field | Skills using it | Notes |
|---|---|---|
| `name` | 108 | must equal the directory name |
| `description` | 108 | the routing surface — see below |
| `allowed-tools` | 108 | narrowing it can break a working skill |
| `effort` | 106 | |
| `user-invocable` | 79 | |
| `argument-hint` | 57 | |
| `disable-model-invocation` | 32 | |
| `context` | 22 | pairs with `agent` |
| `agent` | 22 | pairs with `context: fork` |
| `hooks` | 5 | skill-scoped hooks |
| `scripts` | 4 | |
| `model` | 3 | |

`description` deserves its own line: it decides which prompts select the skill.
Rewording it moves routing, so it is a behavioural change even when no other line
of the skill moves. `scripts/check_split.py` gate D exists to catch exactly that
during refactors.

### 3. Agent frontmatter fields

`name`, `description`, `model`, `color`, `tools`, `skills` — all six present on all
44 agents. `tools` and `skills` are consumed by the runtime, not decoration.

### 4. Install paths

`~/.claude/` and `~/.softspark/ai-toolkit/`. The `~/.softspark/<tool-name>/`
convention is shared across SoftSpark open-source tools; moving it orphans user
state in every one of them.

### 5. CLI commands and their flags

`install`, `update`, `status`, `reset`, `uninstall`, `add-rule`, `remove-rule`,
`inject-hook`, `remove-hook`, `inject-mcp`, `remove-mcp`, `validate`, `doctor`,
`eject`, `benchmark`, `benchmark-ecosystem`, `evaluate`, `stats`, `create`, `mcp`,
`config`, `projects`, `plugin`, `sync`, and the `codex-*` generators.

Flags that appear in the SOPs under `kb/procedures/` are part of the surface, not
implementation detail — `--local`, `--profile`, `--editors`, `--fix`, `--strict`,
`--execute`, `--dry-run`.

### 6. Hook names and their I/O contract

Event names in `app/hooks.json` and the script names under `app/hooks/`. Users
inject their own hooks alongside ours via `inject-hook`, and removal is keyed on
source name. The *contents* of a hook script are free to change; what it is called
and what it reads and writes are not.

### 7. KB taxonomy

The eight categories in `VALID_KB_CATEGORIES` (`scripts/validate.py`) and the
matching list in `app/skills/documentation-standards/SKILL.md`. Consumers file
their own KB documents against it; dropping a category invalidates their
frontmatter. The two lists are one taxonomy in two places — a change belongs in
both, in the same commit.

### 8. Plugin pack names

`enterprise-pack`, `memory-pack`. `plugin install <name>` is a user-typed string.

## Free to change

- Skill and agent body prose, and everything under a skill's `reference/`
- The internal implementation of any hook script, generator, or CLI command
- New skills, agents, packs, hooks, CLI commands, flags, frontmatter fields, or KB
  categories — additive is not breaking, provided defaults preserve current behaviour
- Validation thresholds, subject to the ratchet rule in
  `kb/procedures/sop-release.md`: never lower a threshold in the same
  change that violates it, never raise one to green a red build
- README copy, badges, CI workflows, test internals

## The deprecation path

When a break is genuinely unavoidable:

1. **Keep the old name working for at least one minor release.** For frontmatter,
   the precedent already exists: `validate.py` accepts the retired `version`,
   `delegate-agent` and `run-mode` fields and emits a warning naming the
   replacement. Do the same for anything new that retires.
2. **Warn, do not fail.** A deprecation that errors on first contact is a break
   wearing a deprecation label.
3. **Record it in `CHANGELOG.md` and `DECISIONS.md`**, with what moved, what to do
   about it, and whether anything is actually lost. v4.20.0 is the model: it
   removed nine plugin packs and proved in the entry that no file and no
   capability went with them.
4. **Remove in the next minor at the earliest**, never in a patch.

For config and state files, bump a `version` field and handle the migration on
read. Keep the parser tolerant of the previous shape for one release cycle.

## Verifying before a tag

```bash
python3 scripts/validate.py --strict     # counts, versions, taxonomy, budgets
python3 scripts/audit_skills.py --ci     # security scan
shellcheck --severity=warning app/hooks/*.sh
npm test 2>&1 | grep "^not ok"           # must be empty; the tail line is a test
                                         # number, never a pass count
```

`kb/procedures/sop-release.md` carries the full sequence.
