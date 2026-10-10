---
title: "AI Toolkit - DSH Integration (removed)"
category: planning
service: ai-toolkit
tags: [dsh, deepseek-harness, removed, migration]
doc_type: postmortem
status: completed
version: "3.0.0"
created: "2026-08-31"
last_updated: "2026-10-10"
description: "REMOVED. DeepSeek Harness support left ai-toolkit in 5.0.0 (2026-09-24); the deprecation stubs and the cleanup of old DSH project skills left in 5.4.0 (2026-10-10). Lists what each old input does now and the manual cleanup for projects and DSH profiles that still carry toolkit files."
---

# DSH Integration (removed)

## Summary

DeepSeek Harness (DSH) support was removed in two steps, both by decision of the repository owner (see `DECISIONS.md`, "DSH integration retired" and "DSH leftovers removed"):

| Release | Date | What left |
|---|---|---|
| 5.0.0 | 2026-09-24 | The `dsh` install target and the `ai-toolkit dsh` profile lifecycle. Two warning stubs and a migration for old project skills stayed. |
| 5.4.0 | 2026-10-10 | The stubs and the migration. No toolkit code knows about DSH any more. |

The SoftSpark DSH plugins (`@softspark/dsh-codex`, `@softspark/dsh-orchestrator` and the others) were discontinued and their repositories archived on 2026-10-10.

## What old inputs do in 5.4.0

Releases 5.0.0 to 5.3.5 handled every row below without an error. 5.4.0 does not.

| Input | 5.0.0 to 5.3.5 | 5.4.0 |
|---|---|---|
| `ai-toolkit dsh ...` | Printed manual cleanup steps, exit 0 | Unknown command: prints help, exit 1 |
| `ai-toolkit install --local --editors dsh,...` | Warned and ignored `dsh` | `Unknown editor: 'dsh'`, exit 1, nothing installed |
| Registered project listing `dsh` in its editors | Entry dropped on read | `ai-toolkit update` fails for that project with `Unknown editor: 'dsh'` |
| `.agents/.ai-toolkit-skill-owners` naming `dsh` | Surface re-rendered for Codex, or removed when DSH-only | Marker is invalid: `install --local --editors codex` stops with `Refusing invalid skill-surface owner marker`; `uninstall` leaves the marker in place |
| Skill wrapper marked `.ai-toolkit-dsh-adapted` or `.ai-toolkit-shared-adapted` | Re-rendered or removed | Treated as a user-owned directory and left alone |
| `dsh` key in `~/.softspark/ai-toolkit/state.json` | Dropped on the next write | Kept and ignored |

Projects that ran `ai-toolkit update` on any release from 5.0.0 to 5.3.5 are already converged and see none of this. Codex-only projects are unaffected.

## Cleaning up a project that still carries DSH files

Easiest: before upgrading, run `ai-toolkit update` once on 5.3.5. It migrates every registered project.

After upgrading, do it by hand in the project:

1. In `.agents/skills/`, find the directories that contain `.ai-toolkit-dsh-adapted` or `.ai-toolkit-shared-adapted`. Each holds a generated `SKILL.md`, that marker and symlinks into the toolkit. Delete a directory unless you added your own files to it.
2. Delete `.agents/.ai-toolkit-skill-owners`.
3. If the project uses Codex, run `ai-toolkit install --local --editors codex` to write a fresh surface. Passing `--editors` also replaces the stored editor list, which fixes a registry entry that still lists `dsh`.

## Removing an old DSH profile

Profiles set up by `ai-toolkit dsh install` live under `$DSH_HOME` (default `~/.dsh`). The toolkit does not read, update or remove them. If you no longer want the SoftSpark packages there, remove them with DSH itself. For the default `web` profile:

```bash
dsh plugin --profile web remove @softspark/dsh-codex
dsh plugin --profile web remove @softspark/dsh-orchestrator
rm -rf "${DSH_HOME:-$HOME/.dsh}/.agent-presets/softspark-orchestrator"
```

Repeat the two `plugin remove` lines for any other profile name you installed. Stop running DSH sessions first.

Notes:

- The preset directory `softspark-orchestrator` was a copy of `@softspark/dsh-orchestrator/agent-presets/softspark-orchestrator`. Delete it only if you did not edit it and want it gone.
- `ai-toolkit dsh install` also set a pnpm override for `@anthropic-ai/claude-agent-sdk` (version `0.3.263`) under the `@deepseek-ai/dsh-subagent-claude-code` selector in the profile's `pnpm-workspace.yaml`. It is harmless to keep. Remove it by hand if you want the profile back to its DSH default.

## History

The design, qualification evidence and pins of the removed integration are kept for reference:

- [PATH: kb/history/completed/dsh-native-install-target-plan.md]
- [PATH: kb/history/completed/dsh-integration-plan-superseded.md]
- Earlier versions of this document are in git history under `kb/reference/dsh-compatibility.md`: the compatibility contract (v1.8.1, toolkit v4.39.0) and the retirement note (v2.0.0, toolkit v5.0.0).
