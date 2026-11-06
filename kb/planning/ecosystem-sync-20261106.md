---
title: "Ecosystem sync: 2026-11-06"
category: planning
service: ai-toolkit
tags: [ecosystem, editors, compatibility, hooks, migration]
version: "1.0.0"
created: "2026-11-06"
last_updated: "2026-11-06"
description: "Dated review of all 13 supported tools, adopted hook fixes, stable release channels and OpenCode V2 migration."
---

# Ecosystem sync: 2026-11-06

Executed under [SOP: Ecosystem Sync](../procedures/sop-ecosystem-sync.md).
The initial doctor scan found 10 changed targets, 3 unchanged targets and no
fetch errors. Feature references were reviewed even where landing pages were
unchanged. Each tool's exact sources and dispositions are recorded in
`scripts/ecosystem_tools.json` and the [supported-tools registry](../reference/supported-tools-registry.md).

## Scope and acceptance

Update the supported integration contracts, preserve user-owned configuration,
regenerate derived artifacts, refresh the reviewed snapshot and pass the full
local quality gates. Exercise installation and update in a disposable container
with its own user and home. This task does not publish a release or install
editor binaries into the operator's active environment.

Primary risks were mistaking preview documentation for a stable contract,
dropping user hooks during migration, and accepting tests built around an API
the real runtime does not implement. Version-qualified sources, independent
review, ownership fixtures and real hook subprocess tests address those risks.

## Release review

| Target | Reviewed release | Disposition |
|--------|------------------|-------------|
| Claude Code | 2.1.318 | A/B/C: `onFailure: block` for three existing safety guards; migrate tagged and untagged entries without taking foreign ownership. npm `stable` is 2.1.311; local 2.1.319 belongs to `next`. |
| Claude app | Dated product/plugin documentation | A/C: exported ZIP remains compatible. Hosted Cowork runtime version and live enforcement are not independently verified. |
| Cursor | IDE/Agents Window 3.27 | A/C: current hook/agent contracts match generated output; hosted-app deployment is a separate optional surface. |
| Devin Desktop / Windsurf | 3.11.238 | A/B/C: restore native JSON context from prompt/edit hooks. Both native and legacy rule directories load; dual emission is compatibility output. |
| GitHub Copilot | CLI 1.0.106 | A/C: existing hooks, skills and agents remain compatible. CLI release does not identify every IDE/cloud release. |
| Gemini CLI | 0.67.0 | A/B/C: wrap text-only advisory output as native JSON and retain `prompt_response` in session summaries. Nightly-only events are not adopted. |
| Cline | 4.1.26 | A/C/D: emitted contracts unchanged. Extension TaskComplete/PreCompact availability caveat remains; official repository used when docs returned navigation only. |
| Zoo / Roo Code | 3.94.0 | A/C: JSON `.roomodes` and existing rule paths remain supported. |
| aider | 0.86.2 | A: package metadata and source tag establish the release; GitHub latest-release and HISTORY lag it. |
| Auggie / Augment | 0.37.0 | A/C: pin stable `/cli/v0/` references. Unversioned docs describe 1.x prerelease with changed tools and permissions. |
| Antigravity | App 2.29.0; CLI 1.5.1 | A/C/D: shared global skills path is canonical; legacy CLI paths remain supported. Workflow migration stays under issue #34. |
| Codex | 0.167.0 | A/B/C: preserve user PreModelRequest/PostModelRequest diagnostics during refresh. No default diagnostic handlers or model overrides are added. |
| OpenCode | V2 2.2.5; V1 line 1.19.5 | A/B/C/D: migrate to the documented dual `id/setup/server` export. V1 compatibility requires 1.18.29+. Track migration in issue #44. |

Source disagreements are recorded rather than resolved by local version probes:
OpenCode's `@opencode/cli` publishes V2 while `opencode-ai` and GitHub's
latest-release endpoint identify V1. Auggie's unversioned docs describe a
prerelease. Claude's npm `latest`, conservative `stable` and `next` tags differ.

## Adopted behavior

- Claude Code 2.1.295+ blocks protected actions if the destructive-command,
  home-path or configuration guard cannot start, crashes or times out. Advisory
  hooks retain their behavior. Foreign `_source` ownership survives migration.
- Codex accepts the two diagnostic model-request events without emitting them.
  They cannot block requests or modify context. Hook trust remains required;
  local/plugin command hooks are not supported with cloud orchestration.
- Devin context-only commands emit native event-labelled JSON; guard verdicts
  and blocking exit codes remain intact.
- Gemini wraps advisory text in `systemMessage` or SessionStart context. Its
  native completion response becomes the session summary when the Claude field
  is absent. Blocking handlers keep their native output and status.
- OpenCode V1/V2 share a real subprocess transport with argument-separated
  script paths and JSON stdin. Policy denial and infrastructure failures reject
  tool execution. V2 lifecycle subscriptions are location-scoped and disposed.
  Doctor identifies obsolete managed exports; user plugins remain preserved.
  Global/project IDs are distinct, while one advisory executor per
  directory/workspace avoids ordinary duplicate side effects and supports unload
  takeover. Safety guards execute in every layer; advisory deduplication is best
  effort during reload, and stream failures release ownership to the survivor.

The V1 review found that the old Bun shell wrapper used a nonexistent
`stdin.write` API, so a mocked test had hidden missing guard execution. The
replacement uses `node:child_process.spawn` in both supported runtimes. Runtime
regressions cover missing scripts, crashes, signals, timeouts and denial.

Native OpenCode 2.2.5 smoke testing also found a global/project plugin-ID
collision. Distinct scoped IDs fix loading; both copies report `active` after
asynchronous activation. The one-shot list command can return before activation,
so the verification queries a running server after warm-up. It performs no model
inference and the owned server is stopped afterward.

Migration: [OpenCode issue #44](https://github.com/softspark/ai-toolkit/issues/44).
The previous [Antigravity workflow issue #34](https://github.com/softspark/ai-toolkit/issues/34)
remains the authority for removing legacy workflow output; this sync does not
delete user workflows.

## Models and prompt guidance

Rechecked OpenAI and Claude model families, effort, structured-output and cache
contracts against their official references. Existing defaults remain; no
active model, tool permission or budget is changed. This is a compatibility
review, not a live quality/cost evaluation. See
[model compatibility](../reference/model-compatibility.md).

## Verification

Final verification passed:

- 2037 Bats tests, no failures or skips; 1036 Python tests.
- Strict validation: 44 agents, 116 skills, zero errors or warnings.
- Skill audit: zero HIGH or WARN findings. Ruff, mypy (21 files), Python syntax,
  ShellCheck for hooks/plugin hooks and diff checks passed.
- Regenerated artifacts and refreshed the ecosystem snapshot. Online `--check`
  passed with no structural drift or fetch failures; three dynamic pages changed
  content hashes without heading changes, which the SOP classifies as cosmetic.
- Packed candidate installed with all editors and the full profile in a
  disposable Node 22 / Python 3.11 container under its own OS user. Reinstall
  preserved the hashes of the selected global/project settings and plugin files.
- Installed `doctor` reported zero errors. Its one warning was the container's
  absent optional Bats runner; the full source suite ran on the host.
- Claude Code 2.1.318 accepted the exported plugin through native strict
  validation. Codex 0.167.0 and OpenCode 2.2.5 versions were recorded separately.
- A fresh owned OpenCode 2.2.5 server loaded both scoped toolkit plugins as
  `active` after warm-up. The runner withheld transient authentication output
  and stopped the server. No model inference was used.

Review independently checked guard preservation, migration ownership, native
payloads, V1/V2 process execution, lifecycle isolation and unload/error handling.
The initial full run exposed two obsolete V1-only generator assertions and an
unstaged new KB file. Those causes were corrected; the final full run above
passed after the runtime collision and guard hardening fixes.

Local evidence uses the `/private/tmp/eco-20261106-` prefix: `bats-verified.log`,
`pytest-final-source.log`, `validate-final.log`, `audit.log`, `check.json`,
`smoke-final.log`, `native-final.log`, and the copied smoke evidence directory.
The operator's live editor installation and account settings were not modified.
