---
name: json-mode-patterns
description: "Loaded when user needs structured JSON output from Claude. Covers tool-use-as-JSON-mode, schema design, parsing, partial recovery, and validation."
effort: medium
user-invocable: false
allowed-tools: Read
---

# JSON Mode Patterns

Claude does not have a dedicated `response_format: json` parameter like some other APIs. The idiomatic way to get guaranteed JSON is **tool use with a forced function call**. This skill documents that pattern plus fallbacks.

## Preferred Pattern: Tool-as-Schema

Define a tool whose input schema IS the JSON shape you want, then force the model to call it.

```python
tools = [{
    "name": "record_analysis",
    "description": "Return the analysis as structured data",
    "input_schema": {
        "type": "object",
        "properties": {
            "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "themes": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["sentiment", "confidence", "themes"]
    }
}]

response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=1024,
    tools=tools,
    tool_choice={"type": "tool", "name": "record_analysis"},
    messages=[{"role": "user", "content": text_to_analyze}]
)

# The structured result is in response.content
for block in response.content:
    if block.type == "tool_use" and block.name == "record_analysis":
        result = block.input  # already a Python dict, schema-validated
        break
```

Why this wins:
- Schema is enforced at the API level
- No regex or parsing from model text
- Enums, min/max, required fields actually constrain the output

## Fallback: Prompted JSON + Strict Parse

When tool use is unavailable (some SDKs/proxies strip it):

```python
response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=1024,
    system="You return ONLY valid JSON. No prose, no markdown fences.",
    messages=[{
        "role": "user",
        "content": f"Extract as JSON matching this schema: {schema_str}\n\nInput: {text}"
    }]
)

import json
try:
    result = json.loads(response.content[0].text)
except json.JSONDecodeError:
    # Claude sometimes wraps in ```json ... ```
    result = json.loads(strip_markdown_fence(response.content[0].text))
```

Add a regex fallback that extracts the first `{...}` block if the model added a preface.

## Schema Design Rules

- **Favor enums** over free-form strings when values are known
- **Mark required fields** aggressively — default-optional produces flaky output
- **Use arrays of objects**, not parallel arrays (`[{name, value}]` over `{names: [], values: []}`)
- **Shallow beats nested** — 2 levels of nesting max unless necessary
- **Document each field** in the tool's `description` as well as the schema

## Partial Output Recovery

Model hits `max_tokens` mid-JSON. Strategies:

1. **Increase `max_tokens`** if the schema is genuinely large (most common cause).
2. **Split the schema** — generate one field per call, merge.
3. **Use streaming** and close unclosed braces if stop reason is `max_tokens`.

```python
if response.stop_reason == "max_tokens":
    # Either retry with higher budget or gracefully degrade
    raise IncompleteOutputError(...)
```

## Validation After Parse

Even with tool schema enforcement, business rules aren't enforced by JSON Schema. Add a Pydantic/Zod layer:

```python
from pydantic import BaseModel, Field

class Analysis(BaseModel):
    sentiment: Literal["positive", "neutral", "negative"]
    confidence: float = Field(ge=0, le=1)
    themes: list[str] = Field(min_length=1, max_length=10)

parsed = Analysis(**result)  # raises on violation
```

## Gotchas

- **Tool call tokens count toward output budget** — a huge schema eats max_tokens fast
- **`stop_reason == "tool_use"`** is success, not an error
- **Streaming with tool use** requires handling `content_block_delta` events with `input_json_delta` deltas
- **Model picks a different tool** than you expected if `tool_choice` is `"auto"` — always force the specific tool for JSON mode

## Related

- `claude-api` skill — Anthropic SDK essentials
- Anthropic docs: https://docs.claude.com/en/docs/build-with-claude/structured-outputs
