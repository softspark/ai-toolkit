---
name: rag-patterns
description: "RAG architecture: embeddings, chunking strategies, hybrid search (BM25 + vector), reranking, CRAG/self-correcting, multi-hop reasoning, evaluation metrics. Triggers: RAG, embedding, vector search, pgvector, Qdrant, Pinecone, Weaviate, chunking, reranker, retrieval, hybrid search, semantic search, knowledge base, cosine similarity. Load when building or tuning RAG systems."
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

## Rules

- **MUST** chunk by document structure (headers, lists, code fences), not by fixed byte/token count — structure-aware chunking recovers 20-40% of retrieval quality on technical docs
- **MUST** always use **hybrid search** (BM25 + vector) for keyword-heavy queries — pure vector search misses exact identifiers (function names, config keys)
- **NEVER** trust a single embedding model on multilingual corpora; pair with a bilingual model or translate queries at the edge
- **NEVER** index without content-hash change detection — full rebuilds on every change waste embedding budget and corrupt orphan tracking
- **CRITICAL**: every response includes verifiable citations (source path + exact chunk). A RAG answer without traceable sources is a hallucination wearing a badge.
- **MANDATORY**: evaluate with a golden dataset (faithfulness, relevancy, context precision) before promoting any pipeline change to production

## Gotchas

- Top-k cosine similarity is **not** relevance — semantically close chunks may be topically wrong. Always compare hybrid vs pure-vector scores on a held-out set before committing to one.
- Default embedding models (e.g., `text-embedding-ada-002`) underperform on long technical docs (>8k tokens). For long-form content consider chunking before embedding, not embedding then slicing.
- Chunk overlap (10-20%) helps narrative text but duplicates storage and token cost. Code and structured tables do not benefit from overlap — disable per content type.
- Cross-encoder rerankers (e.g., `bge-reranker`) add 100-300ms per query. For real-time UX, rerank only the top-20 candidates, not the top-100.
- RAG failure modes are structural (retrieval, routing, chunking), not prompt-level. Before "tuning the prompt", check retrieval metrics — a prompt fix on top of broken retrieval is theater.
- Query rewriting (HyDE, hypothetical doc generation) improves some queries and degrades others. A/B test before enabling globally; a blanket "always rewrite" often regresses simple lookups.

## When NOT to Load

- For **executing** a reindex — use `/index` (task skill)
- For measuring RAG quality — use `/evaluate` (task skill)
- For chunking documentation strategy without an index — this skill assumes you already have a vector store; use `/architecture-decision` for pipeline choice
- For MCP-specific retrieval via `smart_query()` — the tool is already built; reach for this skill only when tuning the underlying index
- For prompt engineering alone without retrieval concerns — use `/prompt-caching-patterns` or the relevant language skill
