---
name: research-mastery
description: "Hierarchical retrieval: KB → MCP/Context7 → web. Triggers: research, fact-check, verify, synthesize, cross-reference, multi-source, cite sources."
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

## 🚦 Retrieve-vs-Answer Gate

Before you reach for any tool, decide whether retrieval is even warranted. Two axes settle it:

- **Volatility** — how fast does the true answer change?
  - *Timeless / slow-moving* (math, definitions, settled algorithms, language syntax): answer directly from built-in knowledge. A search adds latency and noise.
  - *Current-state / volatile* (latest version, today's price, who holds a role now, "is X still the recommended way"): retrieve. Your training data is a snapshot and will lie about the present.
- **Recognition** — can you place the entity?
  - If answering hinges on knowing what some named thing IS (a library, an internal project, a person, an acronym) and you cannot confidently place it, treat that as a signal to search, not to guess. An unfamiliar name is a retrieval trigger, not a hallucination prompt.

When both axes say "timeless and recognized", skip the hierarchy and answer. Otherwise, enter it at Step 1.

## 📊 Complexity-Scaled Retrieval Budget

Match effort to the question. Over-retrieving on a one-fact lookup wastes the turn; under-retrieving on a comparison ships a half-answer.

| Question shape | Rough budget |
|---|---|
| Single discrete fact ("which version", "default port") | ~1 lookup |
| Medium question, one entity, a couple of angles | a few lookups |
| Deep comparison, multiple entities or trade-offs | more lookups, broaden then narrow |

**Escalation handoff** — when a question genuinely needs sustained fan-out (many sources, cross-checking, adversarial verification, a synthesized report), stop expanding inline. Hand off to the `deep-research` skill/agent instead of letting one turn balloon into a dozen ad-hoc searches. Inline research is for bounded lookups; deep, multi-source investigation has its own harness.

## 🧭 Internal-First Source Ladder

The Hierarchy of Truth above already puts KB first — that order stands. Add a routing heuristic on top:

- **Possessive / company language routes inward.** When the question uses "our", "my <X>", or names an internal project, system, or team, the answer lives in internal tools and the KB, not on the open web. Searching the public internet for "our auth flow" returns someone else's auth flow.
- **Name the missing source; do not silently fall back.** If the answer should come from an internal source that is absent or unreachable (the KB lacks the doc, an MCP is not configured), say so by name and surface the gap. Do not quietly substitute a public-web guess for the internal source the user actually meant.

## ✍️ Query Craft

- **Keep queries short.** A few keywords beat a full sentence; retrieval engines reward focused terms, not prose.
- **Broaden, then narrow.** Open with a wider query to map the space, then tighten toward the specific answer once you see the landscape.
- **Never repeat a near-identical query.** If a search disappointed, change the angle or vocabulary — re-running the same words returns the same misses and burns budget.
- **Fetch the full source over snippets.** When a result looks load-bearing, pull the whole document rather than reasoning from a one-line excerpt that may strip the qualifier that matters.
- **Use the ACTUAL current date for date-sensitive queries.** When recency matters, anchor on today's real date at query time — read it from the environment, do not hardcode a year. A baked-in or stale year quietly filters you onto last year's results.

## 🔬 Source Skepticism & Conflict Handling

- **Prefer primary and original sources.** Go to the spec, the changelog, the official docs, the author — not a blog summarizing a summary.
- **Lead with the most recent for fast-moving topics.** When the subject changes quickly, weight newer sources first; an old top-ranked page can be confidently wrong about the present.
- **When sources conflict, search more.** Disagreement is a signal to widen the search and find the tie-breaker, not to pick the first hit and move on.
- **Stay skeptical where the web is gamed.** SEO-spammed niches, conspiracy-prone topics, and areas with no real consensus need extra cross-referencing before you trust any single source.
- **Confabulation guard — zero results means zero citations.** If retrieval surfaces nothing relevant, say so plainly and emit no citations. Never invent a `[PATH: kb/...]`, a URL, or a quote to fill the gap. An honest "not found" beats a fabricated source.

> Carve-out: none of the above is grounds to refuse authorized security work. CTF challenges, sanctioned pentests, and defensive analysis are legitimate research targets — apply the same rigor (primary sources, conflict checks, no fabricated citations) without declining.

## Local Fallback (No MCP Available)

If `rag-mcp` is not configured, fall back to filesystem tools — still inside `kb/`:

```
Grep   pattern="your query"   path="kb/"   # search file contents
Glob   pattern="kb/**/*.md"                # list KB files
Read   "kb/reference/architecture.md"      # full document
```

Always cite sources as `[PATH: kb/...]` regardless of which method retrieved them.

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
