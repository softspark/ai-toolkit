---
name: json-mode-patterns
description: "Structured JSON output from Claude: native JSON schemas, strict tools, local validation, refusal and truncation handling. Triggers: JSON mode, structured output, schema validation, JSON parsing."
effort: medium
user-invocable: false
allowed-tools: Read
---

# JSON Mode Patterns

Use native JSON outputs through `output_config.format` for a structured response.
Use `strict: true` on a tool when its arguments need constrained decoding.
Forcing a tool call alone does not guarantee schema compliance.

## Native JSON response

This example uses the current Messages API shape. The caller supplies the approved
model and output budget. Numeric limits are checked locally because raw structured
output schemas do not support `minimum` and `maximum`.

```python
import json
import math

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
        "confidence": {"type": "number"},
        "themes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["sentiment", "confidence", "themes"],
    "additionalProperties": False,
}


def validate_analysis(result):
    if not isinstance(result, dict) or set(result) != set(ANALYSIS_SCHEMA["required"]):
        raise ValueError("Unexpected analysis fields")
    sentiment = result["sentiment"]
    if not isinstance(sentiment, str) or sentiment.casefold() not in {"positive", "neutral", "negative"}:
        raise ValueError("Unknown sentiment")
    confidence = result["confidence"]
    if (type(confidence) not in (int, float)
            or not 0 <= confidence <= 1 or not math.isfinite(confidence)):
        raise ValueError("Confidence must be finite and between zero and one")
    themes = result["themes"]
    if not isinstance(themes, list) or not 1 <= len(themes) <= 10 or not all(isinstance(t, str) for t in themes):
        raise ValueError("Expected one to ten theme strings")
    return {**result, "sentiment": sentiment.casefold()}


def analyze(client, model, text, max_tokens):
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": text}],
        output_config={"format": {"type": "json_schema", "schema": ANALYSIS_SCHEMA}},
    )
    if response.stop_reason != "end_turn":
        raise ValueError(f"Analysis incomplete: {response.stop_reason}")
    blocks = [block.text for block in response.content if block.type == "text"]
    if len(blocks) != 1:
        raise ValueError("Expected one structured response")
    return validate_analysis(json.loads(blocks[0]))
```

Treat the returned confidence as an uncalibrated score until evaluated on labeled
data. Schema compliance does not establish factual correctness.

## Strict tool arguments

For a real tool, put `"strict": True` beside `name` and `input_schema`.
Require `additionalProperties: False` on each object and validate business rules
before executing any side effect. Check the expected tool name, content block type
and `stop_reason == "tool_use"`.

Forced `tool_choice` has thinking-mode restrictions. Verify the selected model's
tool-choice contract before combining it with adaptive or extended thinking;
do not silently disable thinking or change models to force a function call.

## Failure handling

- Check `refusal` and `max_tokens` before parsing. Neither is a successful structured result.
- Retry only within the caller's approved attempt and token limits. Never increase a spending limit automatically.
- Do not close truncated braces or extract the first regex-matched object and treat it as valid.
- If a proxy lacks native structured outputs, parse the entire response and validate it locally; failure is an explicit error or review item.
- For streaming, wait for completion and the final stop reason before validating assembled text.

## Schema and SDK details

Raw schemas support a subset of JSON Schema. Numeric ranges, string length bounds,
recursive schemas and most array-length constraints are unsupported. Apply these
locally or use `client.messages.parse(output_format=YourPydanticModel)`, whose SDK
helper translates the schema and validates the original model afterward.

The SDK helper's `output_format` argument is not the raw Messages API field:
`messages.create` uses `output_config.format`. No structured-output beta header
is required. Check enum casing locally; avoid labels differing only by case.

## Sources and related skills

Reviewed 2026-09-23:
- [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Strict tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use)

Use `content-moderation-patterns` for decision routing and
`model-routing-patterns` for choosing among approved models.
