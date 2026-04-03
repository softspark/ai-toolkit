---
name: rag-patterns
description: "Loaded when user asks about RAG systems, embeddings, or vector search"
effort: medium
user-invocable: false
allowed-tools: Read
---

# RAG Patterns Skill

## Core Patterns

### 1. Hybrid Search
Combine dense (vector) and sparse (BM25) retrieval with RRF fusion:

```python
# RAG-MCP hybrid search
result = await hybrid_search_kb(
    query="rate limiting configuration",
    service="nginx",
    limit=10
)
```

### 2. Corrective RAG (CRAG)
Self-correcting retrieval with relevance validation:

```python
result = await crag_search(
    query="fuzzy query",
    relevance_threshold=0.4,
    max_retries=2
)

# Or via smart_query
result = await smart_query(query="...", use_crag=True)
```

### 3. HyDE (Hypothetical Document Embeddings)
Generate hypothetical answers for better retrieval on conceptual queries:

```python
result = await smart_query(
    query="conceptual question about design patterns",
    use_hyde=True
)
```

### 4. Multi-hop Retrieval
Complex queries requiring multiple retrieval steps:

```python
result = await multi_hop_search(
    query="Compare nginx with varnish for Magento cache",
    max_hops=3
)

# Or via smart_query
result = await smart_query(query="compare A vs B", use_multi_hop=True)
```

---

## Indexing Best Practices

| Aspect | Recommendation |
|--------|----------------|
| Chunk size | 512-1024 tokens |
| Overlap | 10-20% of chunk |
| Structure | Preserve headers, sections |
| Metadata | Include title, path, date, category, tags |
| Frontmatter | YAML with standardized fields |

### Frontmatter Template
```yaml
---
title: "Document Title"
service: {project-name}
category: reference|howto|procedures|troubleshooting|decisions|best-practices
tags: [tag1, tag2, tag3]
last_updated: "YYYY-MM-DD"
---
```

---

## MCP Tools Reference (v5.5.0)

| Tool | Use Case | Speed |
|------|----------|-------|
| `smart_query` ⭐ | Default for 90% of queries | 2-4s |
| `hybrid_search_kb` | Raw vector + text search | <1s |
| `get_document` | Full document content | <1s |
| `crag_search` | Vague/fuzzy queries | 1-3s |
| `multi_hop_search` | Complex reasoning | 20-30s |

### Tool Selection Guide

```python
# Default - auto-routing
smart_query("specific technical question")

# Vague query - self-correcting
crag_search("jak to skonfigurować")

# Complex comparison
multi_hop_search("nginx vs varnish performance comparison")

# Known document
get_document(path="kb/reference/architecture.md")
```

---

## Quality Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Faithfulness | Answer based on context | >70% |
| Relevancy | Answer addresses question | >70% |
| Context Precision | Found context is accurate | >60% |
| Latency (p95) | Response time | <2s |
| Precision@k | Relevant results in top-k | >80% |

---

## Retrieval Optimization

### Reranking
```python
# Retrieve more, rerank to top-k
initial_results = await hybrid_search_kb(query, limit=20)
reranked = rerank_results(initial_results, query)
final_results = reranked[:5]
```

### Context Window Management
- Place critical info at start/end (serial position effect)
- Summarize long documents before insertion
- Use tiered context: critical → supporting → background

### Query Enhancement
- Query expansion with synonyms
- Query decomposition for complex questions
- Entity extraction for filtering

---

## Anti-Patterns

❌ **Don't**:
- Skip reranking for final results
- Use very large chunks (>2000 tokens)
- Ignore metadata in retrieval
- Trust LLM output without citation
- Use `latest` for model versions

✅ **Do**:
- Use top-k=20 → rerank → top-5
- Chunk semantically (by section)
- Enrich metadata at indexing time
- Require source attribution in answers
- Pin model versions for reproducibility

---

## RAG System Implementation

### Key Files (Typical Structure)
```
scripts/
├── search_core.py           # Core search
├── query_enhancements.py    # HyDE, query expansion
├── corrective_rag.py        # CRAG
├── multi_hop.py             # Multi-hop
├── unified_indexer.py       # Indexing
└── rag_evaluator.py         # Evaluation
```

### Running RAG Commands

**Direct execution:**
```bash
# Index KB
make index

# Evaluate RAG
python scripts/evaluate_rag.py

# Detect gaps
python scripts/knowledge_gaps.py --detect
```

**Docker execution (if containerized):**
```bash
# Index KB
docker exec {app-container} make index

# Evaluate RAG
docker exec {api-container} python3 scripts/evaluate_rag.py

# Detect gaps
docker exec {api-container} python3 scripts/knowledge_gaps.py --detect
```
