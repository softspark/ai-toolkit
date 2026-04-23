---
name: index
description: "Reindex the knowledge base for semantic search via the configured vector store (e.g., Qdrant). Use only when the user explicitly asks to reindex — never trigger speculative rebuilds."
effort: low
disable-model-invocation: true
argument-hint: "[path or scope]"
allowed-tools: Bash
---

# Knowledge Base Indexing

$ARGUMENTS

Reindex the knowledge base for semantic search.

> **Prerequisite**: This command requires a vector store (e.g., Qdrant) and an indexing pipeline configured for your project. If not configured, this command provides guidance on setup.

## Usage

```
/index              # Incremental index (detect changes)
/index --full       # Full rebuild
```

## Execution

### Direct Execution
```bash
# Incremental index (auto-detects changes)
make index

# Full rebuild
make index-full
```

### Docker Execution
```bash
docker exec {app-container} make index
docker exec {app-container} make index-full
```

## Change Detection

The indexer uses content hashing to detect changes:

| Scenario | Action |
|----------|--------|
| New document | Index |
| Changed content | Reindex |
| No changes | Skip |
| Deleted document | Remove from index |

## Frontmatter Validation

Before indexing, ensure all KB documents have valid frontmatter:

```yaml
---
title: "Document Title"
service: {service-name}
category: reference|howto|procedures|troubleshooting|decisions|best-practices
tags: [tag1, tag2]
last_updated: "YYYY-MM-DD"
---
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Index not updating | Check file timestamps, run full rebuild |
| Missing documents | Verify frontmatter is valid |
| Slow indexing | Check embedding service performance |
| No vector store | Set up Qdrant or compatible vector DB |

## Rules

- **MUST** require explicit user permission before running `make index` or `make index-full` — never self-trigger
- **NEVER** trigger a full rebuild to "clean up" unless the user asked for it
- **CRITICAL**: validate KB frontmatter before indexing — abort on invalid documents rather than indexing a broken state
- **MANDATORY**: respect change-detection hashes; do not force reindexing of unchanged documents

## Gotchas

- Content-hash change detection keys on the file's content AND path. A **moved** document (same content, new path) looks new to the indexer — both the old path vector and the new one will exist until a full rebuild. Plan a full rebuild after mass reorganizations.
- Deleting a document on disk does not automatically remove its vectors from Qdrant; the indexer emits tombstones only if run with a directory scan. Without `--delete-missing`, orphan vectors stay for weeks.
- Embedding providers rate-limit by requests-per-minute AND by tokens-per-minute. A reindex of 1000+ docs hits the token cap first and stalls silently — watch for 429s in the indexer log before concluding "slow indexing".
- `make index-full` truncates the collection before re-embedding; if the embedding job crashes mid-way, the collection is left partially populated with no query-time indicator of the gap.

## When NOT to Use

- For searching the KB — use `/search` or call `smart_query()` via the rag-mcp tool
- For fixing indexing bugs — use `/debug` on the indexer pipeline
- To evaluate RAG quality after reindexing — use `/evaluate`
- When no vector store is configured — document the gap, do not invent one
