---
title: "Model compatibility refresh, 2026-09-23"
category: planning
service: ai-toolkit
tags: [models, skills, agents, compatibility, prompting]
version: "1.0.0"
created: "2026-09-23"
last_updated: "2026-09-23"
description: "Source-backed review and validation plan for current-model skill and agent guidance."
---

# Model compatibility refresh

## Objective and scope

Adapt active skills, agent instructions and client adapters to current model
contracts. Prioritize Codex/OpenAI, GitHub Copilot and Claude. Keep historical
release records intact and preserve explicit user model choices and permissions.

## Plan

1. Inventory active model IDs, pricing assumptions, effort controls and prompt
   guidance; compare them with official sources dated at review time.
2. Correct Claude API skills and provider-specific output/cache assumptions.
3. Correct OpenAI examples, prompting and cost handling in agent instructions.
4. Adapt runtime model directives for Codex/Copilot without confusing API
   examples with instructions to select a session model.
5. Align orchestration guidance and authoring templates; document client/API
   boundaries in the shared model compatibility reference.
6. Regenerate artifacts, review independent findings and run validation, audits,
   meaningful example/adapter regressions and the full project suites.

## Success criteria

- Active guidance uses verified current contracts or explicit configured model
  inputs, rather than claiming that one model or effort level fits every client.
- Examples handle incomplete/refused/malformed outputs and pricing units safely.
- Translated agents preserve the client's selected model; API code examples
  retain their provider meaning and resource references still resolve.
- Tests establish generated-output behavior and pure example logic without
  contacting paid model APIs or altering installed user configurations.
- Final evidence distinguishes contract validation from live model-quality evals.

## Pre-mortem

- API identifiers can differ from UI names and client availability: verify each
  surface separately and preserve the existing selection when unsupported.
- A sweeping replacement can corrupt API examples or historical records: use
  narrow adapters and an explicit inventory, with preservation regressions.
- Prices and aliases drift: date snapshots, link primary sources and require
  configured rates for calculations rather than silently estimating zero.
- More effort or a more expensive model can worsen cost without helping quality:
  retain approved tiers and require measured evidence for routing changes.
- Passing schema tests is not evidence of model quality: record live-evaluation
  status explicitly instead of claiming unmeasured improvements.

## Evidence

The active catalog and generator mappings were searched for model IDs, model-tier
orders, prices, effort, cache assumptions and reasoning instructions. Historical
CHANGELOG entries and preservation-test literals intentionally retain older IDs.
The dated source matrix is [Model Compatibility](../reference/model-compatibility.md).

| Surface | Change |
|---------|--------|
| Claude API skills | Current model reference, model-specific effort/cache behavior, closed structured-output schemas and local semantic checks |
| LLM operations agent | Actual Responses SDK call, bounded approved fallback, scoped cache identity and configured per-million-token rates |
| AI/prompt agents | Capability-based selection and verifiable results instead of blanket chain-of-thought or model-name recommendations |
| Orchestration and creators | Preserve configured models and budgets; new agent templates inherit; consensus uses evidence rather than confidence alone |
| Codex/Copilot adapters | Rewrite imperative Claude tier orders in prompt text, preserve API examples and code literals, leave native metadata-only mentions intact |
| Secondary surfaces | Current shared Claude API map, removal of unused OpenCode model read, corrected Microsoft Copilot model assumption |
| Maintenance | Model/prompt review is now explicit in ecosystem sync; catalog docs link the shared reference |

## Review findings resolved

- Metadata containing a model name no longer forces a native skill wrapper.
- API fences, repeated backticks and multiline inline literals remain unchanged.
- A numbered list following a tier name is not consumed as a model version.
- Oversized integer confidence values reach validation/review rather than raising
  an unhandled floating-point overflow.
- New Python fixtures have SPDX attribution; streaming is described as latency
  behavior rather than inherent token-cost reduction.

## Verification

- Related Codex/native-skill/Copilot suites: 107 passed.
- Claude API pattern fixtures: 6 passed, including invalid output and URL cases.
- Full Python suite: 456 passed.
- Strict mypy allowlist, repository Ruff rules, ShellCheck, source compilation,
  skill audit, skill evaluation and protected public-surface check: passed.
- Artifact regeneration: passed with the required write permission for generated
  `.agents` outputs. Existing skill/agent catalog counts and permissions remain.
- Full Bats suite: 2068 passed, exit 0; log retained at
  `/private/tmp/ai-toolkit-model-refresh-bats.log`.
- Final strict validation: passed with zero errors and warnings.

No paid provider calls or live multi-model quality/cost benchmarks were run.
These checks establish documented contract compatibility and deterministic
behavior, not measured model-quality improvements. This work is included in the
4.39.0 release candidate; publication follows the release SOP.
