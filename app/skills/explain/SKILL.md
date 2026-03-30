---
name: explain
description: "Explain code, architecture, or concepts with diagrams"
user-invocable: true
effort: medium
argument-hint: "[file or module path]"
agent: code-archaeologist
context: fork
allowed-tools: Read, Grep, Glob
---

# Explain

$ARGUMENTS

Generates visual architecture explanations.

## Output Format

### 1. High-Level Role
"This module handles [Responsibility]. It interacts with [Dependencies]."

### 2. Dependency Graph (Mermaid)
Generate a graph showing imports/exports.
```mermaid
graph TD
    A[AuthService] -->|uses| B[UserRepo]
    A -->|validates| C[Schema]
    D[Controller] -->|calls| A
```

### 3. Key Flows (Sequence)
If logical flows are detected:
```mermaid
sequenceDiagram
    User->>Controller: Login
    Controller->>Service: Validate
    Service->>DB: Check Creds
    DB-->>Service: Result
    Service-->>Controller: Token
```

## Protocol
1. **Scan**: Read file contents to identify classes and functions.
2. **Link**: Identify imports to find collaborators.
3. **Visualize**: Generate standard Mermaid syntax.

## Automated Dependency Graph

Run the bundled script to extract imports and generate a Mermaid diagram:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/dependency-graph.py src/auth.py
```
