# Google AI Pipeline

Reference for `seo-validate` — understanding how Google processes content for AI Search. Informs Category 6 (GEO) and Category 10 (Topical Authority) findings.

Source: Piotr Smargol, Indygo Agency — SEO Copywriting 2026.

---

## 1. The Four-Stage Pipeline

Every query in Google AI Search (AI Overviews, AI Mode, and classical SERPs) passes through the same pipeline. The presentation layer differs; the engine is the same.

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Stage 1: PREPARE                               │
│  NLU — synonym mapping — intent classification  │
│  Query Fan Out (synthetic sub-queries)          │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Stage 2: RETRIEVE                              │
│  Content divided into chunks (≤500 tokens)      │
│  Layout parsed — embeddings computed (Gecko)    │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Stage 3: SIGNAL                                │
│  7 ranking signals applied per chunk candidate  │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Stage 4: SERVE                                 │
│  Gemini 2.5 Flash generates the final answer    │
│  Inline source citations added                  │
└─────────────────────────────────────────────────┘
```

**Key implication for copywriters:** AI does not read your article — it extracts a chunk and pastes it as an answer. Each section must be a self-contained answer unit. If the answer is scattered across the article, AI cannot assemble it.

---

## 2. The Seven Ranking Signals

Google applies seven signals to decide which chunk from which source appears in the answer.

### Signal 1 — Base Ranking
Classical relevance algorithm (PageRank descendants). SEO fundamentals still matter. High-authority domains get a floor advantage, but content structure can compensate.

**Copywriter implication:** Standard on-page SEO (title, H1, internal linking) remains the foundation.

---

### Signal 2 — Gecko Score (Semantic Embedding Similarity)
Gecko is Google's embedding model. It measures how semantically close your chunk is to the user's query — not keyword overlap, but meaning overlap. A chunk about "mattress firmness" will score well for "which mattress is best for back pain" even without that exact phrase.

**Copywriter implication:** Cover the topic from multiple angles and personas. Topical depth beats keyword density. A single cluster of related articles scores higher than one over-optimised page.

---

### Signal 3 — Jetstream (Cross-Attention)
Jetstream is the model's ability to understand context, contrasts, negations, and comparisons within a chunk. It specifically rewards:

- `X vs Y` comparisons
- Negations: "not recommended for…", "avoid if…", "unlike X…"
- Conditional statements: "best for…", "ideal for…", "if X, choose Y"
- Contrast phrases: "in contrast to X, Y does…", "unlike foam, latex…"

**Copywriter implication:** These constructions are not just reader-friendly — they are a direct Jetstream signal. Content with explicit comparisons and decision frameworks is over-represented in AI citations.

---

### Signal 4 — BM25 (Keyword Matching)
The classic TF-IDF/BM25 algorithm is still active. Exact keyword matches in headings and early paragraphs contribute. Not dominant, but present.

**Copywriter implication:** Include the primary keyword in H2 headings and in the first sentence of each section. Do not keyword-stuff — BM25 has diminishing returns and Gecko penalises unnatural density.

---

### Signal 5 — PCTR (Predicted Click-Through Rate)
Google estimates how likely users are to click your result based on historical CTR patterns for that title format, topic, and position. High PCTR boosts a chunk's probability of being included in the AI answer.

**Copywriter implication:** Title and meta description quality directly affects AI citation probability — not just traditional click traffic. Use benefit-led titles. Avoid clickbait (Google's AI pipeline detects and suppresses it). Brand at the end of the title.

---

### Signal 6 — Freshness
Content age is weighted by topic type:

| Topic type | Freshness weight |
|---|---|
| Breaking news | Dominant — stale content is excluded |
| Technology / AI / tools | High — 13-week threshold observed |
| Evergreen how-to | Moderate — update signals matter |
| Historical / definitions | Low — accuracy over recency |

**The 13-week rule:** Research across top AI-cited content shows 50% of cited results were published or updated within the last 13 weeks. Evergreen pages that are not refreshed drop out of AI citation pools gradually.

**Copywriter implication:** Add visible `dateModified` to all indexable pages. Refresh key articles before the 13-week threshold. Use "Updated: [date]" visible to users, not just in JSON-LD.

---

### Signal 7 — Boost/Bury Rules
Manual editorial adjustments applied by Google. Certain sources are systematically boosted (e.g., Reddit, YouTube, Wikipedia, government and academic domains). Certain patterns are buried (AI-generated content without human editing, thin content, pages without authors).

**Copywriter implication:** Named authors with bylines and bios protect content from Bury Rules. Generic AI-generated text without editorial review is actively suppressed.

---

## 3. Query Fan Out

When a user submits a query, the AI does not search only for that query. It generates dozens of synthetic sub-queries internally and retrieves candidate chunks for each.

```
User query: "which laptop for remote work"
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
  "best laptops remote work 2026"    "lightweight laptop long battery"
           │                         │
           ▼                         ▼
  "MacBook vs ThinkPad remote"    "quiet fan laptop home office"
           │                         │
           ▼                         ▼
  "budget laptop for Zoom"        "laptop under 1000 remote work"
           │
           ▼
  "best keyboard laptop coding"
  … (50+ more sub-queries)
```

### The 95% problem

**95% of these sub-queries have zero Monthly Search Volume** in Semrush, Ahrefs, Senuto, or any keyword tool. Classical keyword research shows only 5% of the actual retrieval surface.

**Copywriter implication:**
- Stop optimising for a single phrase per page.
- Cover the topic from multiple persona angles: beginner vs expert, budget vs premium, use case A vs use case B.
- Answer implicit sub-questions within the same article using H2/H3 sections.
- Cluster architecture (pillar + cluster articles) is the structural response to Query Fan Out.

---

## 4. Probabilistic Ranking

In classical SEO, "position 1" was deterministic — the same for every user. In AI Search, ranking is probabilistic: two users sending the identical query can receive different answers.

AI personalises based on:
- Search history and session context
- Location and language
- Inferred demographic profile
- Device type
- Stochastic variation in model generation

**Implication:** There is no single position to win. There is a **probability of being cited**. Maximise that probability by:
1. Covering the topic from multiple perspectives (different personas, contexts, formats).
2. Being present in multiple chunk positions within a long article (each H2 is a citation candidate).
3. Publishing cluster articles that address sub-queries individually.
4. Maintaining freshness so your chunk stays in the retrieval pool.

---

## 5. Format Routing

The AI routes queries to content formats. If your format does not match the query type, you lose — even with superior content.

| Query pattern | Optimal content format | Schema signal |
|---|---|---|
| `how to X` | Numbered step-by-step tutorial | `HowTo` |
| `X vs Y` | Side-by-side comparison table | `Article` + table markup |
| `show me X` | Visual: image gallery or video | Image alt + video schema |
| `latest / best X in [year]` | Freshly updated article with date | `Article` + `dateModified` |
| `reviews of X` / `what do people think of X` | UGC aggregation or forum discussion | `Review`, `AggregateRating` |
| `what is X` | Definition paragraph + entity context | `Article` with entity-first opening |
| `X for [persona]` | Persona-targeted guide | `Article` + `FAQPage` |
| `is X worth it` | Opinionated recommendation with evidence | `Article` with author + data |

**Copywriter implication:** Before writing, determine the dominant query pattern for the page's topic. Structure the page to match that format. Mismatched format = invisible to AI routing.

---

## 6. The Two-Audience Reality

| Audience | Wins with | Metric |
|---|---|---|
| Fast AI (simple information queries) | Structured chunks, direct answers, semantic triples | AI citation probability |
| Human readers (purchase decisions, complex topics) | Narrative, trust signals, social proof, UGC | Engagement, conversion |

**Strategy:** Pages must serve both simultaneously. Chunk-optimised structure aids AI extraction without harming human readability — they are the same discipline (clear headings, direct answers, no filler).

---

## References

- Google Search Central — How Google Search works: https://developers.google.com/search/docs/fundamentals/how-search-works
- Google Gecko embedding model: https://research.google/pubs/gecko-versatile-text-embeddings-distilled-from-large-language-models/
- Blyskall study — 40M AI Overviews results, backlink vs content signals: referenced in SEO Copywriting 2026 (Smargol, Indygo Agency)
- Senuto topical authority study — 212K phrases, 7,200 semantic groups
- Google AI Mode announcement (March 2025): https://blog.google/products/search/google-ai-mode-search/
