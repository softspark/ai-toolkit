---
title: "Ecosystem sync review, 2026-09-23"
category: planning
service: ai-toolkit
tags: [ecosystem, compatibility, codex, copilot, claude]
version: "1.0.0"
created: "2026-09-23"
last_updated: "2026-09-23"
description: "Source-backed editor compatibility review, implementation plan and verification evidence."
---

# Ecosystem sync, 2026-09-23

## Scope and plan

Requested priority: Codex, GitHub Copilot, Claude Code and Claude app. Review
the remaining registry targets too, using the [ecosystem sync SOP](../procedures/sop-ecosystem-sync.md).

1. Compare the registry and generators with current official documentation.
2. Classify confirmed differences using SOP classes A through F.
3. Fix emitted contracts, preserve user configuration and compatibility,
   and add behavior tests with affected documentation.
4. Regenerate artifacts and refresh only successfully fetched snapshots.
5. Run strict validation, skill audit, Python checks, the complete Bats suite
   and the online doctor. Record failures without substituting offline checks.

Success means supported output matches the reviewed contracts, regression
tests pass, every target has a documented disposition, and unavailable
upstream sources remain explicitly unverified.

## Pre-mortem

- Landing-page drift can miss schema changes: read actual feature references.
- Similar hook names can hide incompatible payloads: test native event inputs
  and decisions independently for each client.
- Preview features can be mistaken for required migrations: retain stable
  compatibility and record optional features as class C.
- Bot protection can prevent a complete online gate: preserve last-known-good
  snapshots and report the source failure.
- Regeneration can overwrite user-owned content: inspect the final diff and
  test merge preservation; do not update installed user configurations.

## Initial doctor evidence

The online doctor checked 14 targets: 3 clean, 10 with drift and 1 fetch error.
Most changes were content-hash-only. Structural observations: Windsurf's
`SKILL.md` marker appeared, Augment's `Notification` marker appeared, and local
version probes changed to Claude Code 2.1.280 and Codex CLI 0.155.1.
Claude app's documentation returned HTTP 429. A local version probe is not
evidence of the latest upstream release.

## Findings and verification

The review compares emitted contracts with feature references, rather than
treating a clean landing-page hash as proof of compatibility. Class B also
includes corrections where toolkit behavior diverged from a currently
documented contract; it does not imply the vendor changed that contract today.

| Target | SOP class | Disposition | Official sources |
|--------|-----------|-------------|------------------|
| claude-code | B/F | Accept model-switch hook events and current MCP input schema; correct skill metadata and recognize account-synced plugins. | [1](https://code.claude.com/docs/en/hooks), [2](https://code.claude.com/docs/en/skills), [3](https://code.claude.com/docs/en/plugins-reference) |
| claude-app | F | Account plugins sync to Claude Code terminal sessions from 2.1.273. Manual app export/upload remains necessary. Initial doctor fetch returned HTTP 429; preserve last-known-good snapshot on fetch errors. | [1](https://support.claude.com/en/articles/13837440-use-plugins-in-claude), [2](https://code.claude.com/docs/en/plugins-reference#plugins-synced-from-claude-ai) |
| dsh | A/C | Reviewed the pinned release; keep explicit-preview selection and separately qualified package pins. No automatic migration to other prereleases. | [1](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.1.2-rc.1) |
| cursor | B | Permission hooks must return valid JSON on success. Emit permission:allow for all six permission events, retaining destructive-command denials. | [1](https://cursor.com/docs/hooks) |
| windsurf | A/C/D | Native Devin and compatibility skill locations remain supported. Workflows are deprecated in favor of skills; preserve compatible workflow output with a deprecation notice. Plugin marketplace and optional skill permission grants are not adopted. | [1](https://docs.devin.ai/cli/extensibility/skills/overview), [2](https://docs.devin.ai/cli/extensibility/hooks/lifecycle-hooks), [3](https://docs.devin.ai/desktop/changelog) |
| github-copilot | B/F | Preserve skill invocation controls; enforce custom-agent character limit; normalize VS Code hook payloads and decisions separately from CLI/cloud. | [1](https://docs.github.com/en/copilot/reference/hooks-reference), [2](https://code.visualstudio.com/docs/agent-customization/hooks), [3](https://code.visualstudio.com/docs/agent-customization/agent-skills) |
| gemini-cli | A/C | Current hook reference still documents the existing eleven-event lifecycle. No Stop event or implicit migration to a different runtime. Optional extensions remain not adopted. | [1](https://geminicli.com/docs/hooks/) |
| cline | A/C | Refresh customization sources; native skills and SDK/CLI-only plugins retain their separate scopes. .clineignore deprecation does not affect toolkit output, which does not generate that file. The upstream repository confirms the executable-hook input/output schema, but still labels TaskComplete and PreCompact as coming soon; emitted files do not prove runtime event availability. | [1](https://docs.cline.bot/customization/skills), [2](https://docs.cline.bot/customization/plugins), [3](https://docs.cline.bot/resources/deprecations), [4](https://github.com/cline/cline/blob/main/.clinerules/hooks/README.md) |
| roo-code | A | Zoo custom-mode schema remains compatible with current .roomodes output. Keep Roo compatibility paths and distinguish frozen Roo docs from the successor. | [1](https://docs.zoocode.dev/features/custom-modes) |
| aider | A | Configuration options still support read conventions and existing generated switches. No required output migration found in the options reference. | [1](https://aider.chat/docs/config/options.html) |
| augment | A/C | Notification remains listed in the common event enum without a dedicated handler contract; do not wire a speculative event. Existing hook configuration remains supported. | [1](https://docs.augmentcode.com/cli/hooks) |
| google-antigravity | A | Official hook reference still specifies the existing five native events and camelCase payloads. Refresh snapshot and clarify that current docs can be read through the web index. | [1](https://antigravity.google/docs/hooks) |
| codex-cli | B/F | Add portable root plugin.json while retaining the Codex compatibility manifest. Accept Interrupt and mcp_tool configuration, wildcard matchers and current Stop continuation semantics; track native MCP searches. | [1](https://developers.openai.com/plugins/build/plugins), [2](https://learn.chatgpt.com/docs/hooks) |
| opencode | A/C | Stable skill discovery and tool/session plugin events remain supported. Keep stable generator; no speculative v2 API migration. | [1](https://opencode.ai/docs/plugins/), [2](https://opencode.ai/docs/skills/) |

### Compatibility boundaries

- No default model, tool grants or installed user configuration were changed.
- Codex retains its compatibility manifest alongside portable packaging and
  preserves user-authored MCP hooks and ignored matchers.
- Synced Claude plugins have no install record. Cache discovery is only a
  potential collision signal; the doctor does not disable required org plugins.
- Devin still receives compatibility workflows. Their deprecation has no
  verified removal deadline; this review adds an explicit generation notice.
  Native skill directories already exist, so no destructive conversion or
  duplicate skill catalog is introduced.
- Cline's upstream repository documents the executable-hook schema, while
  `TaskComplete` and `PreCompact` still carry coming-soon labels in that reference.
  Existing files are retained; their presence is not a runtime-availability claim.
- No paid editor sessions or user-account operations were exercised. Tests
  run generated artifacts and native payload fixtures in temporary directories.

### Verification evidence

- `npm run generate:all`: passed.
- `python3 scripts/ecosystem_doctor.py --update --format text`: all 14 fetched;
  initial Claude app HTTP 429 cleared before snapshot refresh.
- `python3 scripts/ecosystem_doctor.py --check --format text`: exit 0; no
  structural drift or fetch errors. Claude app and Gemini had only content-hash
  churn, which the SOP explicitly excludes from the structural gate.
- `pytest tests/python`: 436 passed.
- `npm run lint:py`: passed with the repository E/F rule set.
- `shellcheck --severity=warning app/hooks/*.sh app/plugins/*/hooks/*.sh`: passed.
- `python3 scripts/audit_skills.py --ci`: passed, no high or warning findings.
- `python3 scripts/validate.py --strict`: passed, no errors or warnings.
- Temporary-environment `python -m mypy`: passed for all 10 modules in the
  repository's strict allowlist.
- Python syntax compilation for all shipped scripts: passed.
- Initial full Bats run: 2052 passed, 2 failed. The failures were a stale
  11-event Codex assertion and sandbox refusal to bind the fixture HTTP server.
  The injection test now covers all 12 events and preservation of an existing
  Interrupt handler; all 45 injection tests passed after that change. Both
  prepare-test-env tests passed with localhost access. The final complete
  `npm test` run with that permission passed all 2054 tests, exit 0.
  Its log is `/private/tmp/ai-toolkit-ecosystem-bats-20260923-verified.log`;
  the initial failure log is retained alongside it without the `-verified` suffix.
- Independent cross-review covered the primary integrations and Cursor.
  Findings about ignored Codex matchers, ambiguous Copilot PascalCase inputs
  and missing Cursor denial regressions were corrected before the final run.
- Final diff review found no orphaned references to replaced constants and
  no stale 11-event Codex assertions. No editor version was installed or upgraded.

System `python3` lacks pytest/mypy and the existing mypy launcher references a
removed interpreter. Pytest ran through its installed launcher; a temporary
Python 3.12 environment with `requirements-dev.txt` is used for typechecking.
