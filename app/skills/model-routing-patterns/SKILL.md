---
name: model-routing-patterns
description: "Capability-aware model routing for Codex, Copilot, Claude and provider APIs. Triggers: model routing, model selection, reasoning effort, approved fallback, cost, escalation."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Model Routing Patterns

Choose routes from measured quality, latency and cost under the user's approved
model and spending policy. An explicit model choice overrides automatic routing.
This skill never authorizes a model-tier, permission or budget change.

Apply the same policy across Codex, Copilot and Claude: retain the model selected
by the native client. Provider API IDs, editor picker labels and agent aliases
are separate namespaces; do not translate between them by resemblance. For a
cross-provider application route, validate capabilities and availability on each
provider, and obtain authorization before transferring data or changing spend.
The project inventory is `kb/reference/model-compatibility.md`.

## Reviewed model reference (2026-09-23)

| Model | Claude API ID | API effort default |
|-------|---------------|--------------------|
| Claude Opus 5.5 | `claude-opus-5-5` | `medium` |
| Claude Fable 5.1 | `claude-fable-5-1` | `high` |
| Claude Sonnet 5 | `claude-sonnet-5` | `high` |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | Effort unsupported |

These are dated identifiers, not a runtime upgrade policy. Check the provider's
model availability and current [pricing](https://platform.claude.com/docs/en/about-claude/pricing)
before estimating costs. Do not encode universal cost ratios or declare a model
best for every workload. Preserve a user-specified older model while supported;
surface retirement or availability problems explicitly.

## Effort and caching

Opus 5.5, Fable 5.1 and Sonnet 5 support `low`, `medium`, `high`, `xhigh`, and
`max`. Effort is a behavior control, not a hard spending cap. Opus 5.5 and Fable
5.1 use always-on adaptive thinking; a small output limit can truncate the answer.

Changing top-level `output_config.effort` invalidates message cache blocks, with
model-dependent effects on earlier caches. Supported per-message effort changes
can preserve the prefix. Do not assume effort tuning is cache-neutral.

Keep the configured agent/skill effort. An approved application experiment may
compare effort settings, recording total thinking/output usage and completion
quality at the same task budget.

## Pattern 1: explicit task routing

Use application configuration reviewed for the workload. Labels such as
"classification" or "architecture" are evaluation slices, not proof that one
family is sufficient or necessary.

```python
def choose_model(task, routes, allowed_models, explicit_model=None):
    candidate = explicit_model if explicit_model is not None else routes.get(task)
    if candidate is None or candidate not in allowed_models:
        raise ValueError("No approved model for this request")
    return candidate
```

Start with the selected model. Add a separate classification call only when
measured routing savings exceed its latency and token cost.

## Pattern 2: validation-based escalation

Evaluate a result with task-specific checks: schema validation, failing tests,
retrieval evidence, or human labels. A model's self-reported confidence is not a
calibrated probability. Do not pass hidden reasoning between models; pass the
problem, relevant evidence, and a short failure summary.

Escalate only along an approved route with a bounded attempt count. If no
approved route remains, report failure or send the item for human review.

## Pattern 3: delegation within configured roles

A planner can split independent tasks between workers when the task and client
permit it. Use each agent's configured model and tools. Do not rewrite frontmatter
or force a cheaper worker because a generic diagram suggests it.

Compare end-to-end quality and cost, including planning, handoffs and synthesis.
More agents do not inherently save tokens.

## Pattern 4: resilience fallback

Retry transient failures within the existing retry policy before considering a
different model. The official SDK may already retry requests; avoid multiplying
its retries with another unbounded loop.

A fallback must preserve the user's model requirement, context limits, structured
output support and tool permissions. If changing models is not authorized, stop
with the original model's error. Record every actual fallback and its reason.

## Measuring

Track model ID, effort, policy version, attempts, latency, cache reads/writes and
total billable tokens. Evaluate quality per task type and language using held-out
examples. Set acceptance criteria before changing the route; do not use fixed
confidence thresholds, traffic percentages or cost multipliers as universal rules.

## Sources and related skills

Reviewed 2026-09-23:
- [Claude model overview](https://platform.claude.com/docs/en/models/overview)
- [Effort](https://platform.claude.com/docs/en/build-with-claude/effort)
- [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

Use `prompt-caching-patterns` for cache design and `json-mode-patterns` for
structured results. Use the `llm-ops-engineer` agent for application routing.
