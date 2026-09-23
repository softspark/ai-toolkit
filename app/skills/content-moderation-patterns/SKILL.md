---
name: content-moderation-patterns
description: "Content moderation with Claude: pre-filter vs LLM-classify, categories, thresholds, HITL. Triggers: moderation, safety filter, policy enforcement, content classifier."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Content Moderation Patterns

Apply a versioned product policy with deterministic checks, a structured
classifier, and a review path. Select the model using labeled workload results.
No model family has a universal accuracy or cost advantage for moderation.

## Architecture

```text
input → size/format checks → policy checks → structured classifier → decision
                                                              ├─ allow
                                                              ├─ reject
                                                              └─ human review
```

Treat submitted text as data, including any instructions it contains. Keep the
classification policy in the system message. Request a short policy-grounded
reason, not hidden reasoning.

## Deterministic checks

Use configured size limits and exact parsed hostname checks for URL policies.
A prefix regex can mistakenly accept `allowed.example.attacker.test`.

```python
from urllib.parse import urlsplit


def is_allowed_url(value, allowed_hosts):
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.username is None
        and parsed.password is None
        and host is not None
        and host.casefold() in allowed_hosts
        and port in (None, 443)
    )
```

This checks an already-extracted URL against normalized exact hostnames. It is
not a general URL extractor or an SSRF defense. Evaluate false positives from
keyword filters instead of assuming a fixed percentage of input should be blocked.

## Structured classifier

Use native `output_config.format`. Supply the selected model, policy and output
budget from application configuration. The following taxonomy is an example;
change its enum and routing thresholds together to match the product policy.

```python
import json

MODERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "categories": {"type": "array", "items": {
            "type": "string", "enum": ["clean", "needs_review", "spam", "harassment"],
        }},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["categories", "confidence", "reason"],
    "additionalProperties": False,
}


def classify(client, model, policy, text, max_tokens):
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=policy,
        output_config={"format": {"type": "json_schema", "schema": MODERATION_SCHEMA}},
        messages=[{"role": "user", "content": text}],
    )
    if response.stop_reason != "end_turn":
        raise ValueError(f"Classification incomplete: {response.stop_reason}")
    blocks = [block.text for block in response.content if block.type == "text"]
    if len(blocks) != 1:
        raise ValueError("Expected one classification")
    return json.loads(blocks[0])
```

Apply local validation before routing. Refusal, truncation, invalid JSON or an
API failure produces a review/error outcome, never an implicit allow.
See `json-mode-patterns` for schema limitations and response checks.

A repeated `system` string is not automatically cached. If policy size and reuse
justify it, explicitly configure caching as in `prompt-caching-patterns`.
Do not generate heartbeat traffic to keep a cache warm.

## Categories and decision routing

Define categories and blocking behavior in the product policy. Keep `clean`
exclusive: a result containing both `clean` and a violation is inconsistent.
Use `needs_review` for uncertainty. Thresholds come from calibration and policy,
not the model's claim that its confidence is reliable.

```python
import math


def route(classification, block_thresholds, allow_threshold):
    if not isinstance(classification, dict) or set(classification) != {"categories", "confidence", "reason"}:
        return "human_review"
    if not isinstance(classification["reason"], str):
        return "human_review"
    confidence = classification.get("confidence")
    categories = classification.get("categories")
    if (type(confidence) not in (int, float)
            or not 0 <= confidence <= 1 or not math.isfinite(confidence)):
        return "human_review"
    if not isinstance(categories, list) or not categories or not all(isinstance(c, str) for c in categories):
        return "human_review"
    categories = {category.casefold() for category in categories}
    if categories - (set(block_thresholds) | {"clean", "needs_review"}):
        return "human_review"
    if "needs_review" in categories or ("clean" in categories and len(categories) != 1):
        return "human_review"
    if categories == {"clean"}:
        return "pass" if confidence >= allow_threshold else "human_review"
    if any(confidence >= block_thresholds[category] for category in categories):
        return "reject"
    return "human_review"
```

Validate configuration thresholds as finite numbers in [0, 1] at startup.
The example's category thresholds are policy-specific; it does not decide
which categories your product must reject.

## Evaluation and review

Use held-out labeled examples covering language, context, quoted material, benign
mentions and adversarial inputs. Track precision, recall, appeal outcomes and
per-category error cost. Neither false positives nor false negatives are always
cheaper; the product policy determines that trade-off.

Send ambiguous cases to human review. Store decision metadata, policy/model
versions and the minimum evidence needed for review under the application's
retention and access controls. Do not indiscriminately log raw sensitive input.

Refresh evaluations when the policy, model or input distribution changes.
Run an offline comparison before deploying a new route or threshold.

## Sources and related skills

Reviewed 2026-09-23:
- [Content moderation](https://platform.claude.com/docs/en/about-claude/use-case-guides/content-moderation)
- [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

Use `security-patterns` for application input security, `model-routing-patterns`
for model evaluation and `prompt-caching-patterns` for policy caching.
