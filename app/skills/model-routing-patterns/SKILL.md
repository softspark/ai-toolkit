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

<!-- CLAUDE_CODE_ONLY_START -->
## Claude Code: available executors and supervised routing

Apply this section only in Claude Code. Other clients use their native agents
and keep their configured models and reasoning effort. Never call the Claude
Codex plugin from Codex, Antigravity or another client.

Check availability before choosing an executor. The Codex route requires all
three: the `codex@openai-codex` plugin is installed, effectively enabled for the
current project, and `codex:codex-rescue` is callable through the current Agent
tool. The toolkit SessionStart hint checks local metadata only; it does not
prove runtime availability, authentication, model access or security access.
An existing cache directory alone is insufficient. If the hint is absent,
verify those conditions from the client's plugin status and agent catalog.

When unavailable or disabled, use installed native agents with their configured
models and effort. Do not install or enable a plugin, force a Codex command,
or change the current session's model to satisfy this policy. If delegation
itself is unavailable, do the authorized work in the current session and report
that limitation. Explicit user model choices always take precedence.

The toolkit's Claude defaults use these roles when available:

| Work | Executor |
|------|----------|
| Planning, coordination and acceptance | Native orchestrator, Opus `high` |
| Bounded implementation, tests and routine fixes | Native implementation agent, Sonnet `high`, or the available Codex plugin |
| Security work | Prefer Codex `gpt-6-astra`, `xhigh`; otherwise the installed native security agent and its configured model |
| Hard debugging | Available Codex at `xhigh`, or the native debugger, Opus `xhigh` |

Use Codex proactively for substantial independent implementation or diagnosis;
do not require a failure first, and keep trivial edits with the current executor.
Retain the native domain role, file ownership and review criteria when selecting
the Codex executor. If Astra is unavailable, report that and use the configured
native security agent. Do not silently select a different Codex model.

Dispatch with `Agent(subagent_type="codex:codex-rescue", prompt="--fresh ...")`.
Include the task, working directory, owned paths, relevant evidence, acceptance
criteria and verification commands. Pass `--model gpt-6-astra --effort xhigh`
for the security route, and `--effort xhigh` for hard debugging. Ordinary coding
keeps the configured Codex model and effort unless the user chose otherwise.
These flags control the Codex worker, not the Sonnet forwarding wrapper.
Do not use the retired Spark alias or substitute a plugin command for the agent.

Request read-only work explicitly for audits or diagnosis; write access is
appropriate only for an authorized implementation task. Codex's sandbox and
approval restrictions still apply. Permission or authentication failures return
to the supervisor; they do not authorize bypasses or a new account/provider.
Selecting Astra does not load a security package or confer Trusted Access.
Use an existing security package only when it is available in the delegated
runtime and within the user's task; report which workflow actually ran.

The supervisor owns lifecycle and verification. A background job identifier is
not completion: collect the final result using the plugin's documented status
and result controls, keyed to that job. Resume only the identified prior task;
use a fresh task for independent work. Empty output, failed startup and partial
results are failures to resolve, not successful delegation. Do not redispatch
failed writes until their partial changes have been inspected. Verify the diff,
tests and required review before acceptance, then finish or cancel owned work.
The forwarding wrapper must only forward; do not ask it to inspect or monitor.

When creating agents, keep native Claude model fields valid. Codex is a separate
executor, not a Claude `model:` value or an automatic Claude Team member. Reuse
the installed plugin instead of generating another wrapper or editing its cache.
<!-- CLAUDE_CODE_ONLY_END -->

## Reviewed model reference (2026-10-08)

| Model | Claude API ID | API effort default |
|-------|---------------|--------------------|
| Claude Opus 5.5 | `claude-opus-5-5` | `medium` |
| Claude Fable 5.1 | `claude-fable-5-1` | `high` |
| Claude Sonnet 5.5 | `claude-sonnet-5-5` | `high` |
| Claude Haiku 5.5 | `claude-haiku-5-5` | `medium` |

Codex (account and client availability decide): `gpt-6-astra` is the most
capable model; `gpt-6.1-sol` is the recommended
model for complex coding and agentic work and replaces `gpt-6-sol`; `gpt-6-luna`
fits focused, repeatable tasks. GPT-5.5 leaves Codex with ChatGPT sign-in on
2026-10-14. Sol 6.1 accepts `low` to `max` effort but not `none` or `minimal`.

These are dated identifiers, not a runtime upgrade policy. Check the provider's
model availability and current [pricing](https://platform.claude.com/docs/en/about-claude/pricing)
before estimating costs. Do not encode universal cost ratios or declare a model
best for every workload. Preserve a user-specified older model while supported;
surface retirement or availability problems explicitly.

## Effort and caching

Opus 5.5, Fable 5.1, Sonnet 5.5 and Haiku 5.5 support `low`, `medium`, `high`,
`xhigh`, and `max`. Effort is a behavior control, not a hard spending cap. Opus 5.5 and Fable
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

Reviewed 2026-10-08:
- [Claude model overview](https://platform.claude.com/docs/en/models/overview)
- [Effort](https://platform.claude.com/docs/en/build-with-claude/effort)
- [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Sonnet 5.5 prompting](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5)
- [Codex models](https://learn.chatgpt.com/docs/models)
- [Astra model](https://developers.openai.com/api/docs/models/gpt-6-astra)
- [Latest OpenAI model guide](https://developers.openai.com/api/docs/guides/latest-model)
- [Models and Trusted Access](https://learn.chatgpt.com/docs/cyber-safety)

Use `prompt-caching-patterns` for cache design and `json-mode-patterns` for
structured results. Use the `llm-ops-engineer` agent for application routing.
