---
name: evaluate
description: "Evaluate skill quality and RAG retrieval accuracy"
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
