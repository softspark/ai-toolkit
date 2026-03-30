---
name: index
description: "Index codebase into the knowledge base"
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
