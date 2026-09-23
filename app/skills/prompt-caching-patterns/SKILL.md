---
name: prompt-caching-patterns
description: "Anthropic API prompt caching: TTL, breakpoints, stacking, invalidation, hit rate. Triggers: prompt caching, cache_control, cache breakpoint, cache TTL, hit rate."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Prompt Caching Patterns

Cache repeated prefixes when reuse offsets write costs. Cache eligibility and
pricing depend on the model and platform; a short system prompt is not cached
merely because it repeats.

## Dated cache reference (2026-09-23)

| Model | Minimum eligible prefix | Cache read / base input price |
|-------|-------------------------|-------------------------------|
| Claude Opus 5.5 | 512 tokens | 5% |
| Claude Fable 5.1 | 512 tokens | 2.5% |
| Claude Sonnet 5 | 1024 tokens | 10% |
| Claude Haiku 4.5 | 4096 tokens | 10% |

For the Claude API, a five-minute write costs 1.25 times base input and a one-hour
write costs 2 times base input. Recheck
[current pricing](https://platform.claude.com/docs/en/about-claude/pricing)
before budgeting; provider-specific billing and model availability can differ.

## Prefix design

Cache order is `tools → system → messages`, regardless of the order of request
keys. An explicit breakpoint includes the marked block and everything before it.
Keep dynamic material after the stable prefix.

```text
[ tool definitions              ] breakpoint 1
[ reusable system instructions  ] breakpoint 2
[ reference documents           ] breakpoint 3
[ stable conversation prefix    ] breakpoint 4
[ current variable content      ]
```

There are at most four breakpoints. Top-level automatic `cache_control` moves a
breakpoint to the last eligible block and consumes one slot. Explicit markers
give control over a static prefix.

## Explicit caching example

The caller supplies the approved model, text and output limit. Marking a prefix
below its model's minimum silently produces no cache entry.

```python
def cached_answer(client, model, policy, document, question, max_tokens):
    return client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{
            "type": "text",
            "text": policy,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": document,
                 "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": question},
            ],
        }],
    )
```

Use `{"type": "ephemeral", "ttl": "1h"}` for an approved one-hour write. When mixing
TTLs, put longer-lived breakpoints before shorter-lived ones. Do not send paid
heartbeat requests simply to keep an unused prefix warm.

## Invalidation

Changing tools invalidates subsequent system and message prefixes; changing the
system invalidates subsequent messages. Top-level effort changes invalidate
message cache blocks and can affect earlier blocks depending on the model.
Supported per-message effort updates preserve earlier prefixes. Changing the
model is not a promise of cross-model cache reuse.

A static string passed as `system` alone does not enable caching: configure
`cache_control` at the request or content-block level. Keep tool definitions,
document serialization and stable instructions deterministic.

## Measuring reuse

Include writes when calculating the fraction of input served from cache.

```python
def cache_read_fraction(usage):
    read = usage.cache_read_input_tokens or 0
    written = usage.cache_creation_input_tokens or 0
    uncached = usage.input_tokens or 0
    total = read + written + uncached
    return read / total if total else 0.0
```

Record write/read counts and actual costs across cold and warm requests. Choose a
target from observed reuse; a single universal hit-rate threshold is misleading.
Both cache counters remaining zero can indicate an ineligible prefix.

## When not to cache

Skip cache writes when no prefix will be reused before expiry or when measured
cost exceeds uncached requests. Do not pad prompts with irrelevant content merely
to reach a minimum. A one-hour TTL may fit intermittent reuse better than five
minutes, within the approved cost policy.

## Sources and related skills

Reviewed 2026-09-23:
- [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Pricing](https://platform.claude.com/docs/en/about-claude/pricing)

Use `model-routing-patterns` for route evaluation and `llm-ops-engineer` for
application operations.
