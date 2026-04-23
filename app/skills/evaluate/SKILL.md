---
name: evaluate
description: "Evaluate RAG retrieval accuracy and LLM-as-a-judge quality metrics (faithfulness, relevancy, context precision) against a golden dataset. Use when the user asks to measure RAG quality or detect knowledge gaps — not for evaluating generic LLM outputs."
effort: medium
disable-model-invocation: true
argument-hint: "[--threshold N]"
allowed-tools: Bash, Read
---

# RAG Evaluation

Evaluate RAG quality using LLM-as-a-Judge methodology.

## Usage

```
/evaluate [--threshold 0.7]
```

## Execution

### Direct Execution (recommended for most projects)
```bash
# Run RAG evaluation
python3 scripts/evaluate_rag.py

# With custom thresholds
python3 scripts/evaluate_rag.py \
  --faithfulness 0.7 \
  --relevancy 0.7 \
  --context 0.6

# Detect knowledge gaps
python3 scripts/knowledge_gaps.py --detect

# Generate gap report
python3 scripts/knowledge_gaps.py --report
```

### Docker Execution (containerized projects)
```bash
# Replace {api-container} with your API server container name
docker exec {api-container} python3 scripts/evaluate_rag.py

# With custom thresholds
docker exec {api-container} python3 scripts/evaluate_rag.py \
  --faithfulness 0.7 \
  --relevancy 0.7 \
  --context 0.6

# Detect knowledge gaps
docker exec {api-container} python3 scripts/knowledge_gaps.py --detect

# Generate gap report
docker exec {api-container} python3 scripts/knowledge_gaps.py --report
```

## Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Faithfulness** | Is answer based on context? | >70% |
| **Relevancy** | Does answer address question? | >70% |
| **Context Precision** | Is found context accurate? | >60% |

## Evaluation Process

1. **Generate test queries** from golden dataset
2. **Execute RAG pipeline** for each query
3. **LLM judges** each response on metrics
4. **Report** aggregate scores

## Golden Dataset

Located at: `scripts/golden_dataset.json` (or project-specific path)

```json
{
  "queries": [
    {
      "query": "How to configure rate limiting?",
      "expected_topics": ["nginx", "rate-limiting"],
      "expected_sources": ["kb/nginx/howto/rate-limiting.md"]
    }
  ]
}
```

## Output Example

```
RAG Evaluation Results
======================
Total Queries: 50
Average Faithfulness: 0.82
Average Relevancy: 0.78
Average Context Precision: 0.71

Quality: GOOD

Failed Queries (faithfulness < 0.7):
- Query: "How to backup PostgreSQL?"
  Score: 0.45
  Issue: No relevant documents found
```

## Knowledge Gaps

After evaluation, check for gaps:

```bash
# Direct execution
python3 scripts/knowledge_gaps.py --detect

# Docker execution
docker exec {api-container} python3 scripts/knowledge_gaps.py --detect
```

Output:
```
Knowledge Gaps Detected:
1. PostgreSQL backup procedures (5 failed queries)
2. Redis caching configuration (3 failed queries)
3. Ollama model selection (2 failed queries)
```

## Quality Gates

- [ ] Faithfulness >70%
- [ ] Relevancy >70%
- [ ] Context Precision >60%
- [ ] No critical knowledge gaps

## Rules

- **MUST** use a golden dataset — never evaluate on synthetic queries only
- **NEVER** report a score without listing the failed queries alongside it
- **CRITICAL**: if the golden dataset is missing, stop and ask the user to provide one
- **MANDATORY**: thresholds come from project config, not hardcoded defaults, when available

## Gotchas

- LLM-as-a-judge scores are **non-deterministic**; a single run fluctuates by ±10 points even with `temperature=0`. Always report the average and stddev over ≥3 runs, not a one-shot number.
- The default threshold trio (0.7 / 0.7 / 0.6) was calibrated on English KBs. Multilingual corpora (Polish + English in the same index) score systematically 5-15 points lower — recalibrate per language, or split the golden dataset by language.
- Golden datasets **drift**: when the KB is reindexed or documents are renamed, `expected_sources` may point at moved or deleted paths. A sudden drop in `context_precision` across unrelated queries usually means dataset rot, not RAG regression — validate the dataset paths first.
- Judges often reward verbose answers as "more faithful" because there is more text to ground. Tune the judge prompt to penalize padding, or cap answer length in the generator before evaluation.

## When NOT to Use

- For auditing skill quality (the 5-criteria check) — that lives in `scripts/evaluate_skills.py`
- For general-purpose LLM output scoring without a KB — use `/review` or a tailored prompt
- For unit tests or code correctness — use `/test`
- For continuous evaluation without a golden dataset — build the dataset first
