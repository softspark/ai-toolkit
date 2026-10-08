---
title: "Model compatibility for skills and agents"
category: reference
service: ai-toolkit
tags: [models, skills, agents, codex, copilot, claude, effort]
version: "1.2.0"
created: "2026-09-23"
last_updated: "2026-10-08"
description: "Dated model snapshot and rules separating runtime selection, API parameters and prompt guidance."
---

# Model compatibility for skills and agents

Reviewed 2026-10-08. These are documentation snapshots, not a guarantee that a
model is enabled on a particular account. Check the active client's picker and
policy before selecting a model. Preserve a user's explicit choice; do not
replace a tiered workflow with a single flagship model.

## Runtime selection and API examples are different surfaces

| Surface | Selection contract | Toolkit behavior |
|---------|--------------------|------------------|
| Claude Code | Named models and `opus`/`sonnet`/`haiku` aliases; resolution depends on provider and configuration | Existing agent tiers remain aliases; skill and agent frontmatter are Claude-specific unless an adapter explicitly maps them |
| Codex | Client model picker/configuration and native custom-agent configuration | Generated agents omit model overrides, preserving the host's selection; Claude skill `effort` is not a Codex reasoning setting |
| Copilot | Account/client model availability, picker and supported custom-agent configuration | Generated agents omit provider-specific model defaults; Claude aliases are not portable Copilot model IDs |
| API examples | Explicit provider model ID plus that model's endpoint and capability contract | Receive configured models, budgets and rates; application fallback must use an approved compatible set |

Claude aliases do not imply the same concrete model on every provider. The
current Claude Code reference maps Anthropic API `opus` to Opus 5.5, `sonnet`
to Sonnet 5.5 and `haiku` to Haiku 5.5, while other providers can resolve
differently. Sonnet 5.5 requires Claude Code 2.1.284 or later and Haiku 5.5
requires 2.1.293 or later. See
[Claude Code model configuration](https://code.claude.com/docs/en/model-config).

## Reviewed model families

| Provider/surface | Current examples at review time | Important boundary |
|------------------|---------------------------------|--------------------|
| OpenAI API | `gpt-6-astra`, `gpt-6.1-sol`, `gpt-6-luna` (`gpt-6-sol` still listed) | Use Responses for reasoning with tools; Astra and Sol 6.1 reject `none` (Sol 6.1 also `minimal`; use `low`), while GPT-6 Sol/Luna allow it |
| Codex | `gpt-6.1-sol` recommended for complex coding, `gpt-6-astra` most capable, `gpt-6-luna` for focused tasks, according to account/client availability | Start from the selected/default effort; higher reasoning and orchestration modes are explicit choices |
| Claude API | `claude-opus-5-5`, `claude-fable-5-1`, `claude-sonnet-5-5`, `claude-haiku-5-5` | Opus 5.5 and Haiku 5.5 default to medium effort, Fable/Sonnet to high; all four support `low` to `max` |
| GitHub Copilot | Offers models from multiple providers, including current GPT-6 and Claude families | Plan, organization policy and client determine the actual list; utility models are not selectable session models |

Sources: [OpenAI latest model guide](https://developers.openai.com/api/docs/guides/latest-model),
[Codex models](https://learn.chatgpt.com/docs/models),
[Claude models](https://platform.claude.com/docs/en/models/overview),
[Claude effort](https://platform.claude.com/docs/en/build-with-claude/effort),
[Copilot availability](https://docs.github.com/en/copilot/reference/ai-models/supported-models).

Retirement is also surface-specific. At this review date, Codex with ChatGPT
sign-in has retired GPT-5.4/mini and announces GPT-5.5 retirement for 2026-10-14.
That notice does not retire those models from the OpenAI API or establish
Copilot availability. Check the relevant account/client instead of applying
one product's retirement list globally. See the Codex models reference above.

## Effort, caching and prompting

Sonnet 5.5 API migrations are not model-name substitutions: forced `tool_choice`
values `any` and `tool` are rejected, and thinking-block handling changed.
Existing examples targeting Sonnet 5 remain examples for that model until their
full request/response contract is migrated.
[Migration guide](https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide).

- Preserve effective effort when supported. An API's `reasoning.effort`,
  Claude's `output_config.effort`, and an editor's reasoning control are not
  interchangeable schemas. Do not forward unsupported sampling parameters to
  reasoning requests.
- Changing effort does not universally preserve cache. Use the provider's
  documented per-message update mechanism where supported; re-check cache
  invalidation rules for ordinary request-level changes.
- Ask for a concrete result, constraints, evidence and acceptance criteria.
  Avoid blanket requests to expose chain-of-thought, unsupported universal
  performance claims, or unconditional maximum effort for every reviewer.
- A failed task is a signal to inspect context and evidence. Escalate to another
  model only within an approved routing policy; uncertainty scores alone do not
  establish which output is correct.

## Conditional Claude-to-Codex delegation

The Claude orchestrator and authoring/workflow skills apply
`model-routing-patterns`. The native defaults are Opus `high` for coordination,
Sonnet `high` for bounded implementation and tests, and Opus `xhigh` for hard
debugging. The plugin route is optional and requires an installed, effectively
enabled `codex@openai-codex` plus a callable `codex:codex-rescue` in the current
Claude session. A cache directory or SessionStart hint alone is not enough.

When the plugin is missing, disabled or unavailable, use installed native agents
with their configured models and effort. Never install/enable a plugin, change
the current model or force a cross-provider call merely to satisfy routing.
Explicit task-level model choices take precedence.

When available, Codex can own an implementation task before Claude gets stuck.
Security prefers `--model gpt-6-astra --effort xhigh`; hard debugging uses
`--effort xhigh` or the native debugger. Normal Codex implementation retains its
configured model and effort. The forwarding wrapper's Claude model is separate.
An unavailable Astra route is reported and falls back to the existing native
security agent, without silently substituting another Codex model.

The supervisor supplies working directory, owned paths, acceptance criteria and
checks; it collects final results, reviews changes and validates tests. A job ID,
empty output or a partial result is not completion. Security package loading and
account access are separate from selecting Astra. Existing permissions remain.

Claude-only instruction blocks are omitted from generated native agents,
commands and materialized skills for other clients. Marker-only skills preserve
their native frontmatter and resources. Clients that read canonical skills via
catalogue pointers must ignore the explicitly scoped blocks. Codex and other
hosts use native delegation; they never delegate back to the Claude plugin.

## Cost and validation

Keep pricing outside executable prompt examples. Resolve current rates for the
actual model and account, use explicit per-million-token units, and record input,
cached input and output usage where the API reports them. Unknown rates must be
reported rather than treated as free usage. API dollar rates do not describe
Copilot credits or subscription plan usage.

Contract tests cover emitted metadata, resource preservation, fake-client
request shapes and deterministic parsing/calculation behavior. They do not
measure the quality, latency or actual token spend of every model. Live evals
require representative tasks, available models and an explicitly bounded budget.

See [review plan and evidence](../planning/model-compatibility-refresh-20260923.md).
