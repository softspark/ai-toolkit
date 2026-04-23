---
name: content-moderation-patterns
description: "Loaded when user builds content moderation, safety filters, or policy enforcement with Claude. Covers pre-filter vs LLM-classify, category design, confidence thresholds, and human-in-the-loop."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Content Moderation Patterns

Two-stage pattern that balances cost, latency, and quality: cheap deterministic filters first, then LLM classification only on survivors.

## Architecture

```
[ input ]
   │
   ▼
[ pre-filter ]  ── (regex, allow/block lists, length check) ──► reject early
   │
   ▼
[ LLM classifier ]  ── (Haiku, structured output) ──► categories + confidence
   │
   ▼
[ decision router ]
   ├── high confidence + policy violation → reject
   ├── high confidence + clean → pass
   └── low confidence or edge categories → human review queue
```

## Pre-filter Stage (cheap)

Catch the obvious cases before paying an LLM call:

```python
BANNED_PATTERNS = [
    re.compile(r"\b(banned_term_1|banned_term_2)\b", re.I),
    re.compile(r"\bhttps?://(?!allowed-domain\.com)", re.I),  # external links
]

def pre_filter(text: str) -> tuple[bool, str]:
    if len(text) > 10_000:
        return False, "too_long"
    for pat in BANNED_PATTERNS:
        if pat.search(text):
            return False, f"banned_pattern:{pat.pattern}"
    return True, "pass"
```

Roughly 40-70% of spammy input should die here. Log counts by rule so you can tune.

## LLM Classifier Stage (Haiku)

Use the smallest capable model. Haiku is usually right for moderation.

```python
CATEGORIES = ["harassment", "self_harm", "spam", "off_topic", "pii", "clean"]

def classify(text: str) -> dict:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        tools=[{
            "name": "moderate",
            "description": "Classify content against policy",
            "input_schema": {
                "type": "object",
                "properties": {
                    "categories": {
                        "type": "array",
                        "items": {"type": "string", "enum": CATEGORIES}
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "reasoning": {"type": "string", "maxLength": 200}
                },
                "required": ["categories", "confidence", "reasoning"]
            }
        }],
        tool_choice={"type": "tool", "name": "moderate"},
        system=POLICY_DESCRIPTION,  # cached — stable across requests
        messages=[{"role": "user", "content": text}]
    )
    return extract_tool_result(response)
```

**Cache the policy description** — it's the same on every call. See `prompt-caching-patterns`.

## Category Design

- **Start with 5-8 categories**, not 50. Fewer = higher per-category accuracy.
- **One `clean` category** — easier than trying to define "not bad"
- **No overlapping categories** — `harassment` and `hate_speech` should be merged or clearly separated by specific criteria in the policy doc
- **`unclear` / `needs_review` category** — gives the model a graceful escape hatch instead of forcing a wrong label

## Threshold Router

```python
def route(classification: dict) -> str:
    conf = classification["confidence"]
    cats = set(classification["categories"])

    if "clean" in cats and conf > 0.8:
        return "pass"
    if cats & BLOCK_CATEGORIES and conf > 0.85:
        return "reject"
    if cats & BLOCK_CATEGORIES:
        return "human_review"
    return "human_review"  # default to review on ambiguity
```

Thresholds belong in config, not code — they change as you learn.

## Human-in-the-Loop

- All `human_review` cases go to a queue with the model's reasoning
- Human decisions flow back into a dataset used to evaluate new model versions
- Track disagreement rate between human and model — rising disagreement signals policy drift

## Evaluation Loop

Build a golden set of ~500 examples per category with ground truth. Track:
- **Precision per category** (of what we flagged, how much was truly bad)
- **Recall per category** (of truly bad, how much we caught)
- **False-positive cost** per category — harassment FP is cheap, "clean FP" (wrongly blocking good content) is expensive

## Anti-patterns

| Anti-pattern | Why it bites | Fix |
|--------------|--------------|-----|
| One huge prompt asking "is this okay?" | Unstable answers, no tracking | Structured categories + confidence |
| Using Opus for moderation | 10x cost, no accuracy gain for this task | Haiku is fine |
| Hiding policy in user message | Policy gets mixed with input | Policy in system prompt, cached |
| Binary block/allow only | No signal for edge cases | Add review queue |
| No audit trail | Can't improve | Log every decision with full classification |

## Related

- `security-patterns` — input validation at system boundaries
- `prompt-caching-patterns` — cache the policy doc
- `model-routing-patterns` — when to escalate from Haiku to Sonnet
- Anthropic docs: https://docs.claude.com/en/docs/about-claude/use-case-guides/content-moderation

## Rules

- **MUST** pre-filter the obvious cases (regex, deny-lists, length caps) before sending to an LLM — LLM moderation on a 500MB comment is unusable
- **MUST** return a structured JSON classification (category, confidence, reason), not a prose verdict — prose breaks audit trails
- **NEVER** ship a moderation pipeline without a human-in-the-loop escalation path for ambiguous cases
- **NEVER** hide the policy in the user message; the policy belongs in the cached system prompt so it is versioned and auditable
- **CRITICAL**: log every decision (input, category, confidence, model, policy version, timestamp) — moderation without an audit trail cannot be improved or appealed
- **MANDATORY**: calibrate confidence thresholds per category; harassment FP is cheap, clean-content FP is expensive

## Gotchas

- False positives on clean content are **much more expensive** than false negatives on borderline content, in user-trust terms. Optimize for recall on hard-fail categories (CSAM, doxing) but precision on soft-fail categories (spam, rudeness).
- Haiku is sufficient for most moderation classification; using Opus inflates cost 10× with no measurable accuracy gain on this task. Reach for Opus only for edge cases that Haiku consistently misclassifies.
- Prompt caching on the policy doc only hits when the cache window is still warm (5 minutes). Bursty traffic with long quiet periods loses the cache every window — amortize by keeping a heartbeat call.
- Structured JSON output via tool-use is more reliable than free-form JSON in the response — parse errors happen ~1-3% of the time with free-form, near zero with tool-use schemas.
- The golden test set drifts. Policy changes, new attack patterns, and new product surfaces all invalidate old examples. Refresh quarterly or after any policy update.

## When NOT to Load

- For **structured JSON output** design in general — use `/json-mode-patterns`
- For **security** input validation (SQLi, XSS) — use `/security-patterns`
- For caching the policy doc mechanics — use `/prompt-caching-patterns`
- For picking the model tier (Haiku vs Sonnet vs Opus) — use `/model-routing-patterns`
- For moderation of voice/audio content — this skill covers text; audio adds a transcription failure mode not covered here
