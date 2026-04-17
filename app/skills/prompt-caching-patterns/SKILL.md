---
name: prompt-caching-patterns
description: "Loaded when user builds with Anthropic API and needs to cut cost or latency via prompt caching. Covers TTL, cache breakpoints, stacking, invalidation, and measuring hit rate."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Prompt Caching Patterns

Anthropic's prompt caching cuts input-token cost by ~90% on cached prefixes and reduces latency. Worth learning because one mistake (putting a dynamic value before a stable prefix) disables the whole cache.

## Cache Mechanics

- **TTL**: default 5 minutes; `ttl: "1h"` for 1-hour cache (higher base cost but longer-lived).
- **Minimum size**: 1024 tokens per cache block for Sonnet/Opus, 2048 for Haiku.
- **Max breakpoints**: 4 per request.
- **Order matters**: everything BEFORE a `cache_control` block is part of that cache key. Dynamic content AFTER the cached block doesn't break the cache.

## Anatomy of a Cached Request

```python
from anthropic import Anthropic

client = Anthropic()
response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": LONG_SYSTEM_PROMPT,  # stable across requests
            "cache_control": {"type": "ephemeral"}
        }
    ],
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": LARGE_DOCUMENT_CONTEXT,
                 "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": user_question}  # dynamic
            ]
        }
    ]
)
```

## Layering Pattern (4 breakpoints)

```
[ system prompt              ] ← breakpoint 1 (most stable)
[ tool definitions           ] ← breakpoint 2
[ long reference docs        ] ← breakpoint 3
[ conversation history up to turn N ] ← breakpoint 4
[ current user message       ] ← not cached (dynamic)
```

Put the MOST stable content earliest. A change to breakpoint 2 invalidates 3 and 4.

## Anti-patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Timestamp in system prompt | Every request is unique | Remove timestamp, or put it AFTER the cache block |
| User name inserted into cached text | Cache misses per user | Inject user name AFTER the cache block |
| Reordering tool definitions across requests | Cache invalidated | Sort tools deterministically |
| Retrying with exponential jitter that changes prompt | Cache miss on retry | Keep the exact same prefix on retries |
| Caching <1024 tokens | Silently uncached | Merge with adjacent content or drop the breakpoint |

## Measuring Hit Rate

Response includes:
```python
response.usage.cache_creation_input_tokens  # written this request
response.usage.cache_read_input_tokens      # read from cache (billed ~10%)
response.usage.input_tokens                 # not cached
```

Target ratio for a well-tuned loop: `cache_read / (cache_read + input) > 0.7`. Below that, you're leaving money on the table.

## When NOT to Cache

- One-shot calls (cost of writing cache > savings)
- Prompts under ~1500 tokens
- Content that changes every request (user input, current weather, live data)
- Hot path with <1 request per 5 min (cache expires unused)

## TypeScript SDK

```typescript
const response = await anthropic.messages.create({
  model: "claude-opus-4-7",
  max_tokens: 1024,
  system: [
    { type: "text", text: LONG_SYSTEM, cache_control: { type: "ephemeral" } }
  ],
  messages: [
    {
      role: "user",
      content: [
        { type: "text", text: LARGE_CONTEXT, cache_control: { type: "ephemeral" } },
        { type: "text", text: userQuestion }
      ]
    }
  ]
});
```

## Related

- `claude-api` skill — full Anthropic SDK patterns
- `llm-ops-engineer` agent — production caching strategy
- Anthropic docs: https://docs.claude.com/en/docs/build-with-claude/prompt-caching
