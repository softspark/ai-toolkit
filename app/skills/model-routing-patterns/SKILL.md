---
name: model-routing-patterns
description: "Loaded when user builds multi-model pipelines (Haiku/Sonnet/Opus). Covers cost-optimized routing, escalation, sub-agent delegation, and fallback chains."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Model Routing Patterns

Three Claude tiers. Using Opus for everything is 10-40x more expensive than it needs to be. Using Haiku for everything loses accuracy on hard tasks. The craft is routing.

## Model Characteristics (2026)

| Model | Latency | Cost (rel.) | Strengths | When |
|-------|---------|-------------|-----------|------|
| Haiku 4.5 | Fastest | 1x | Classification, extraction, simple tools, moderation | Bulk processing, triage, labels |
| Sonnet 4.6 | Medium | 3-5x | General coding, reasoning, most agent tasks | Default workhorse |
| Opus 4.7 | Slowest | 15-30x | Complex reasoning, orchestration, architecture, large context | Hard, rare, high-stakes |

Ratios are approximate and shift between releases. Re-check pricing before committing a production path.

## Pattern 1 — Complexity Router (pre-classify)

Cheap model classifies the request, then routes to the right tier:

```python
def route(user_message: str) -> str:
    complexity = classify_with_haiku(user_message)  # returns: simple | medium | hard
    return {"simple": "haiku", "medium": "sonnet", "hard": "opus"}[complexity]
```

Good when ~60% of traffic is simple. Overhead: one Haiku call per request (~100 tokens).

## Pattern 2 — Confidence-Based Escalation

Try the cheap model first, escalate only when it hesitates:

```python
def solve(problem: str):
    haiku = call_haiku(problem)
    if haiku.confidence > 0.85:
        return haiku.answer
    sonnet = call_sonnet(problem + haiku.reasoning)
    if sonnet.confidence > 0.8:
        return sonnet.answer
    return call_opus(problem)
```

Haiku must be prompted to output confidence (e.g. via tool-use structured output — see `json-mode-patterns`). Pure self-reported confidence is noisy; combine with a heuristic (output length, tool calls, hedging words).

## Pattern 3 — Sub-agent Delegation (Opus orchestrates, Haiku workers)

Orchestrator reasons about the plan, workers execute atomic steps:

```
Opus (planner)
  ├── Haiku (extract_dates_from_doc_1)
  ├── Haiku (extract_dates_from_doc_2)
  ├── Haiku (extract_dates_from_doc_3)
  └── Opus (synthesize all extractions into timeline)
```

Real example: `/orchestrate` in ai-toolkit runs Opus as planner, subagents (model per agent's frontmatter) as workers. See `app/agents/*.md` — each agent sets `model:` explicitly.

## Pattern 4 — Fallback Chain (resilience, not cost)

When primary is rate-limited or errors, degrade gracefully:

```python
def call_with_fallback(messages):
    for model in ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"]:
        try:
            return client.messages.create(model=model, messages=messages, ...)
        except (RateLimitError, OverloadedError):
            continue
    raise AllModelsExhausted()
```

Useful in production, not for cost optimization — you lose quality on fallback.

## Pattern 5 — Task-Specific Routing

Skip generic complexity scoring when you know the task type:

| Task | Route |
|------|-------|
| Commit message from diff | Haiku |
| Summarize 5-10 lines | Haiku |
| Classify intent | Haiku |
| Fix a failing test | Sonnet |
| Write new feature | Sonnet |
| Code review, architecture decision | Opus |
| Multi-agent orchestration | Opus |
| Complex debugging across systems | Opus |

Encode this as a map in code, not a prompt.

## Anti-patterns

| Anti-pattern | Consequence | Fix |
|--------------|-------------|-----|
| Opus for everything | 10-40x bill | Start with Sonnet, measure, demote |
| Haiku for code review | Misses subtle bugs | Sonnet minimum for code quality |
| Router overhead > savings | Haiku classifier eats the margin | Skip router if >80% of traffic is one tier |
| Different prompts per tier | Maintenance nightmare | Same prompt, just swap model |
| No telemetry | Can't optimize | Log model + tokens + cost per request |

## Measuring

Track per-route:
- Cost per request
- Latency p50/p95
- Quality score (human-labeled or auto-evaluated)
- Escalation rate (how often you fell back to a bigger model)

Target: move the Pareto curve — cheaper at equal quality OR better at equal cost.

## Related

- `llm-ops-engineer` agent — production routing strategy
- `prompt-caching-patterns` — stack caching on top of routing
- `json-mode-patterns` — structured confidence from Haiku
- Anthropic cookbook: https://github.com/anthropics/claude-cookbooks — see "sub-agents" notebook
