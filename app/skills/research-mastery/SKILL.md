---
name: research-mastery
description: "Loaded when user asks to research, verify, or synthesize information"
effort: medium
user-invocable: false
allowed-tools: Read
---

# Research Mastery Skill

You are not a guessing machine. You are an information retrieval engine.

## 🔴 The Hierarchy of Truth (Strict Order)

You MUST search in this order. Do not skip steps.

### 1. Local Knowledge (RAG-MCP)
**Source of Truth**: The project's Knowledge Base (`kb/`).
**Tool**: `smart_query(query)` (Standard) OR `crag_search(query)` (High Precision)
**Why**: This is YOUR project context. It overrides everything else.
**Protocol**:
1. Try `smart_query("task context")`.
2. **CRITIC (Self-Correction)**:
   - "Did the docs answer the specific question?"
   - **If NO**: Use `crag_search(query, relevance_threshold=0.7)`.
   - **If STILL NO**: 
     1. **LOG GAP**: Append query to `kb/gaps.log`
     2. Proceed to Step 2.

### 2. Context7 (External MCPs)
**Source of Truth**: Connected MCP servers (e.g., databases, external APIs).
**Tool**: `use_mcp_tool(...)`
**Why**: Live data from the environment.

### 3. External Search (Internet)
**Source of Truth**: The Web.
**Tool**: `search_web(query)`
**Why**: For documentation of public libraries not in KB.
**Rule**: ONLY if Step 1 & 2 yield nothing.

### 4. Built-in Knowledge (LLM Training)
**Source of Truth**: Your training data.
**Why**: Fallback for general programming concepts.
**Rule**: Use only for generic syntax/logic, NEVER for project specifics.

## 🛑 Validation Protocol
Before acting on information:
1. **Cite the Source**: "According to `kb/architecture.md`..."
2. **Verify Freshness**: Is the doc from 2023 or 2025?
3. **Cross-Reference**: Does the code match the doc?

## Example Workflow
Task: "Fix the login bug."
1. `smart_query("login architecture")` -> Found `kb/auth/login_flow.md`.
2. `smart_query("known login bugs")` -> Found nothing.
3. Code analysis of `src/auth/Login.ts`.
4. Fix implemented based on `login_flow.md`.
