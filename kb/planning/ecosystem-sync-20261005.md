---
title: "Ecosystem review for ai-toolkit 5.2.0"
category: planning
service: ai-toolkit
tags: [release, ecosystem, compatibility, editors, models]
version: "1.0.0"
created: "2026-10-05"
last_updated: "2026-10-05"
description: "Online review of thirteen integrations, upstream CLI releases and model contracts before ai-toolkit 5.2.0."
---

# Ecosystem review for 5.2.0

Release Phase 0 follows [the ecosystem SOP](../procedures/sop-ecosystem-sync.md).
The first online doctor run checked all 13 registry targets: **3 clean, 10 with
drift, zero fetch errors**. Structural differences were the Devin landing page
and installed CLI versions. Other reported differences were content hashes with
unchanged headings. Feature references were reviewed separately; a landing-page
hash alone does not verify hooks, skills, agents or plugin contracts.

## Dispositions

Each finding has one class. Multiple classes in a row describe separate findings.
Class A means compatible documentation/navigation churn; C means an optional
surface not adopted; D records a deprecation already handled by the toolkit.
No new mandatory generator migration, default promotion (E), or global surface
migration (F) was identified in this review.

| Integration | Classes | Evidence and disposition |
|-------------|---------|--------------------------|
| Claude Code | A, C | Local version advanced from 2.1.287 to 2.1.289. [Release 2.1.289](https://github.com/anthropics/claude-code/releases/tag/v2.1.289) fixes permission handling and plugin validation; optional mod teammate APIs are not adopted. [Command hooks](https://code.claude.com/docs/en/hooks), [skills](https://code.claude.com/docs/en/skills), [agent effort](https://code.claude.com/docs/en/sub-agents) and [plugin manifests](https://code.claude.com/docs/en/plugins-reference) remain compatible. |
| Claude Chat/Cowork | A, C | Content-only landing-page change. [Plugin distribution](https://support.claude.com/en/articles/13837440-use-plugins-in-claude) retains the existing export surface. Organization publishing and additional app UI capabilities do not require generated configuration. |
| Cursor | A, C | Content-only change. [Hooks](https://cursor.com/docs/hooks) retain project/user JSON configuration and native event names; [subagents](https://cursor.com/docs/subagents) retain native configuration. Optional workspace startup/plugin discovery is not generated. Cloud hook limitations do not expand local installation guarantees. |
| Windsurf/Devin | A | The landing page replaced onboarding headings with a video introduction. [Official Markdown](https://docs.devin.ai/desktop.md) confirms the presentation change. [Lifecycle hooks](https://docs.devin.ai/cli/extensibility/hooks/lifecycle-hooks) remain supported, and [skills](https://docs.devin.ai/cli/extensibility/skills/overview) explicitly retain `.windsurf/skills/` alongside `.devin/skills/`. |
| GitHub Copilot | A, C, D | [Command hooks](https://docs.github.com/en/copilot/reference/hooks-reference) remain supported; optional alternate handler surfaces are not adopted. [Agent configuration](https://docs.github.com/en/copilot/reference/custom-agents-configuration) retires `infer` in favor of invocation controls; the generator already uses `user-invocable` and `disable-model-invocation` and emits no `infer`. |
| Gemini CLI | A | Content-only change. [Native hooks](https://geminicli.com/docs/hooks/) retain `AfterAgent` as the completion event; this is not a Claude-style `Stop` event. |
| Cline | A, C | Content-only change. [Skills](https://docs.cline.bot/customization/skills) retain `.clinerules/skills/` compatibility alongside recommended `.cline/skills/`. [Plugin packaging](https://docs.cline.bot/customization/plugins) is an optional distribution surface; no migration of existing generated skills is required. |
| Roo/Zoo | A | Doctor clean. [Zoo custom modes](https://docs.zoocode.dev/features/custom-modes) explicitly retain JSON `.roomodes`; new UI YAML defaults do not deprecate existing JSON output. |
| Aider | A | Doctor clean. [Options reference](https://aider.chat/docs/config/options.html) continues documenting the configuration, read/conventions and lint/test surfaces used by the generators. |
| Augment | A | Content-only change. [Hooks](https://docs.augmentcode.com/cli/hooks) and [subagents](https://docs.augmentcode.com/cli/subagents) remain compatible with the 5.1.0 repair: native allowlist only, no overriding `disabled_tools`. No additional permission expansion is adopted. |
| Antigravity | A, D | Doctor clean, but the [workflow retirement on 2026-11-01](https://antigravity.google/docs/migration/workflows-to-skills/) remains relevant. Existing same-named skill migration and marked legacy output handle it. [Native hooks](https://antigravity.google/docs/hooks) remain compatible. Legacy removal remains tracked in [issue #34](https://github.com/softspark/ai-toolkit/issues/34). |
| Codex | A, C | Local CLI advanced from 0.159.3 to [0.160.0](https://github.com/openai/codex/releases/tag/rust-v0.160.0). UI, Guardian, reconnect and sandbox fixes require no generated-config migration. [Hooks](https://learn.chatgpt.com/docs/hooks) still execute `command`/`mcp_tool`, while `prompt`/`agent` handlers are parsed but skipped. [Skills](https://learn.chatgpt.com/docs/build-skills), [agents](https://learn.chatgpt.com/docs/agent-configuration/subagents) and the [supported compatibility plugin manifest](https://developers.openai.com/plugins/build/plugins) remain valid; portable root manifests do not force an existing export migration. |
| OpenCode | A, D | Content-only change. [Plugin events](https://opencode.ai/docs/plugins/) retain the stable JS contract. [Agent `tools`](https://opencode.ai/docs/agents/) is deprecated in favor of `permission`; our agent generator already omits that deprecated field. No speculative plugin-version migration. |

## Model and prompt review

Reviewed the native model/effort frontmatter inventory, model-routing guidance,
JSON-output examples and cache examples against current provider references.
The dated [model compatibility reference](../reference/model-compatibility.md)
remains the basis for separating client selection from API request parameters.

The current [OpenAI migration guide](https://developers.openai.com/api/docs/guides/latest-model)
adds `gpt-6.1-sol`. Like Astra, it rejects `none` effort and requires Responses
for tool calling. That does not change the documented behavior of `gpt-6-sol`
or authorize replacing configured models. This is class C availability metadata:
preserve all approved models, effort levels, tools and budgets. The
[Codex catalog](https://learn.chatgpt.com/docs/models) still scopes GPT-5.5
retirement on 2026-10-14 to ChatGPT sign-in rather than the OpenAI API.

[Claude model IDs and effort defaults](https://platform.claude.com/docs/en/models/overview)
remain consistent with the dated routing table. The
[effort reference](https://platform.claude.com/docs/en/build-with-claude/effort),
[structured-output schema](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
and [prompt-cache reference](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
retain the request contracts used by the reviewed examples. Cache eligibility
and cost remain model-dependent; historical Sonnet 5 examples are not silently
rewritten into Sonnet 5.5 requests. [Copilot availability](https://docs.github.com/en/copilot/reference/ai-models/supported-models)
remains account/client-dependent; generated agents continue inheriting selection.

## Validation and limits

The reviewed Claude CLI version for isolated release smoke tests is **2.1.289**.
This is backed by its official release page, separately from the doctor's local
version probe. Codex **0.160.0** was also checked against its tagged release notes.

The snapshot was refreshed after the above dispositions. Validation passed:

- Online `ecosystem_doctor.py --check --format text`: exit 0, 13 targets,
  11 clean and two content-only hash changes (Claude app and Gemini), zero
  structural drift or fetch errors. Dynamic hashes are non-gating per the SOP.
- Offline `ecosystem_doctor.py --offline --check --format text`: 13 clean.
- `validate.py --strict`: zero errors or warnings, including 76 KB documents.
- `audit_skills.py --ci`: zero high/warning findings, 14 informational notices.
- Diff and whitespace review completed for the snapshot and this report.

Full test suites and cross-platform release gates belong to the release
coordinator; this document does not claim they have completed.

The browser could not render the Devin desktop landing page; its official
Markdown endpoint was fetched successfully, and the online doctor fetched the
HTML successfully. No other source-access error blocked these dispositions.
The review establishes documented compatibility, not live execution in all
thirteen clients, account model availability, model quality or paid API results.
