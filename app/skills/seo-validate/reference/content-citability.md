# Content Citability Patterns

Reference for `seo-validate` Category 6 (GEO). Covers the structural and linguistic patterns that maximise AI citation probability. Companion to [geo-guidelines.md](geo-guidelines.md) and [ai-pipeline.md](ai-pipeline.md).

Source: Piotr Smargol, Indygo Agency — SEO Copywriting 2026.

---

## 1. Chunk Architecture

### The 500-token boundary

Google's retrieval stage splits content into chunks of **maximum 500 tokens (~375 words)**. AI does not summarise your article — it extracts one chunk and uses it as the answer. If the answer to a question is distributed across multiple sections or buried after a long preamble, AI cannot assemble it.

**Rules:**
- Each H2 section should stay within ~375 words.
- If a section exceeds this, split with an H3 sub-heading — each H3 becomes its own chunk candidate.
- Never put the answer at the end of a section after a long setup.

### Anatomy of a citable chunk

Every section should follow this structure:

```
H2: [Question or keyword-rich title]
│
├── Direct answer — 2–3 sentences. No preamble. The fact first.
│
├── Elaboration — data, context, nuance. 3–5 sentences.
│
├── Visual element — list, table, or code block.
│
└── TL;DR (optional, for long sections) — 1-sentence summary.
```

### Before / after examples

**Before (unchunkable):**
```
H2: Choosing the Right Mattress

When you're looking for a new mattress, there are many factors to consider.
The market offers a wide variety of options, and it can be overwhelming to
navigate. Let's explore the key aspects you should think about before making
a purchase decision, because getting this right is important for your sleep
quality and long-term health. After all, we spend a third of our lives in bed.

Eventually, firmness is one of the most important factors. For people under
70 kg, a softer H1–H2 rating works well.
```
*Problem: answer buried after 80-word preamble; AI extracts the preamble as the "answer".*

**After (chunk-optimised):**
```
H2: How to Choose Mattress Firmness by Body Weight

Match firmness to your weight: under 70 kg → H1 or H2; 70–90 kg → H3;
over 90 kg → H4. Higher body weight needs firmer support to maintain
spinal alignment.

| Weight | Recommended firmness |
|--------|----------------------|
| < 70 kg | H1–H2 (soft–medium) |
| 70–90 kg | H3 (medium-firm) |
| > 90 kg | H4 (firm) |

**TL;DR:** Firmness = body weight ÷ 10, rounded up to the nearest H-rating.
```
*Result: AI extracts the first two sentences as the answer; table is bonus precision.*

---

## 2. Semantic Triples

### What they are

A semantic triple is the simplest factual statement AI can parse without inference or guessing:

```
Subject → Predicate → Object
```

LLMs are trained on structured knowledge graphs built from triples. Content written as triples is extracted with high confidence and low hallucination risk.

### Triple structure

| Component | Role | Example |
|---|---|---|
| Subject | What/who is described | "Premium Mattress" |
| Predicate | Property or relationship | "has firmness rating" |
| Object | Value or target | "H3" |

Assembled: "The Premium Mattress has a firmness rating of H3."

### Stacking triples

One product/topic should generate multiple triples covering all queryable properties:

```
Product X → has firmness → H3
Product X → measures → 160 × 200 cm
Product X → has height → 22 cm
Product X → is ideal for → side sleepers weighing 70–90 kg
Product X → is not recommended for → stomach sleepers
Product X → pairs with → slatted base with max 5 cm gap
```

Each triple answers a different AI sub-query. Six triples = six citation opportunities.

### Marketing prose vs semantic triples

| Style | Example | AI extractable? |
|---|---|---|
| Marketing prose | "Our exceptional collection will enchant you with its elegance and superior comfort." | No — zero extractable facts |
| Semantic triples | "Firmness: H3. Dimensions: 160×200 cm. Height: 22 cm. Ideal for side sleepers, 70–90 kg. Not recommended for stomach sleepers." | Yes — 5 distinct facts |

**Rule:** Every product description, category page, and guide should contain a minimum of three semantic triples in the opening paragraph or a specification table.

### Grep patterns

```
# Detect marketing filler (high prose density, low factual density)
Pattern: \b(exceptional|extraordinary|unique|enchant|fascinate|remarkable|unparalleled|outstanding)\b
Files: *.html, *.md, *.tsx, *.jsx, *.vue, *.svelte, *.astro
Flag: marketing superlative without associated factual triple
```

---

## 3. Opinionated Content vs Hedging Language

### Why AI skips hedged claims

AI answer engines extract concrete statements to synthesise answers. A hedged claim ("this might be a good choice for many people") cannot be used as a direct answer to "which mattress should I buy?" AI silently passes over it.

**Google's Jetstream signal explicitly rewards** opinionated, declarative content over neutral, hedged content.

### Hedging patterns to eliminate

| Hedging phrase | Why it fails | Replacement |
|---|---|---|
| "may be a good choice" | Cannot be cited as a recommendation | "We recommend X for Y" |
| "might work well for" | Conditional — AI skips | "Works best for" |
| "worth considering" | No stance | "Our top pick for Z is X" |
| "for many people" | Undefined persona | "for side sleepers weighing 70–90 kg" |
| "could be ideal" | Speculative | "Is ideal for" |
| "one option is" | Non-committal | "Choose X if you need Y" |
| "it depends" (without resolution) | No extractable answer | "It depends on your weight: under 70 kg → H2, over 90 kg → H4" |

### Opinionated writing rules

1. **Take a position.** "We recommend X for Y" over "X is worth considering."
2. **Name the persona.** "Ideal for side sleepers weighing 70–90 kg" over "suitable for most users."
3. **Justify the claim.** AI cites "best for back pain because H3 stabilises the lumbar spine" — not "best for back pain" alone.
4. **Use first-person plural for brand voice.** "We tested X and found…" establishes E-E-A-T Experience signal.

### Grep patterns for hedging detection

```
# High-priority hedging (recommendation context)
Pattern: \b(may be|might be|could be|worth considering|for many|for most people|it depends)\b
Files: *.html, *.md, *.tsx, *.jsx, *.vue, *.astro
Context: within 50 words of product name, category heading, or recommendation heading
Severity: INFO
```

---

## 4. Decision Frameworks

### Why they dominate AI citations

"If X → choose Y" is the most frequently cited construction in AI Search. It directly answers the user's decision-making intent, requires no interpretation, and maps cleanly to Query Fan Out sub-queries ("which X for Y?").

### Formats

**Conditional (if/then):**
```
If you sleep on your side → choose H2–H3 firmness.
If you share a bed with a partner of significantly different weight → choose a split mattress.
If you have chronic lower back pain → choose H3 with lumbar zone reinforcement.
```

**Use-case mapping:**
```
For home office video calls → prioritise battery life and weight under 1.5 kg.
For graphic design work → prioritise display colour gamut (>95% DCI-P3).
For travel → prioritise weight and keyboard quality for extended typing.
```

**Elimination framework (negative definition):**
```
NOT for: stomach sleepers, children under 12, anyone over 100 kg.
```

### Placement

Decision frameworks belong:
- In H2 "How to Choose" or "Which X for You" sections.
- In product/category opening paragraphs (chunk position 1).
- In FAQ answers (each answer = one framework).
- In comparison tables (column "Best for:").

### Grep patterns

```
# Detect absence of decision framework in guide/category pages
Detect: (?i)<h[2-3][^>]*>(how to choose|which .* for|guide to|best .* for)
Then check: (?i)\bif\b.{1,50}\b(choose|select|pick|go with|opt for)\b  OR  (?i)\bfor .{3,30}\b(choose|recommend|ideal|best)\b
Flag if: guide heading found, no decision framework pattern within 500 words
Severity: INFO
```

---

## 5. Contrast Patterns (Jetstream Signal)

Contrasts and comparisons are a direct Jetstream (cross-attention) signal. Content with explicit "X vs Y" structures is over-represented in AI answers for comparative queries.

### Contrast constructions

| Construction | Example |
|---|---|
| `X vs Y` heading | "Foam vs Latex Mattress: Which is Better?" |
| "Unlike X, Y…" | "Unlike foam, latex responds instantly to movement." |
| "In contrast to X…" | "In contrast to bonnell springs, pocket springs isolate motion." |
| "X is better than Y for Z" | "Latex is better than foam for hot sleepers because it has open-cell structure." |
| "Compared to X, Y offers…" | "Compared to H2 firmness, H3 provides 40% more lumbar support." |
| Comparison table | Explicit columns for two or more options |

### When to use contrasts

- Every product category page should contain at least one "Category A vs Category B" section or table.
- Blog guides should compare at least two options before making a recommendation.
- Product descriptions should contrast with the alternative ("unlike [competitor type], this product…").

### Grep patterns

```
# Detect comparative content missing contrast constructions
Detect: (?i)\b(vs|versus|compare|comparison|difference between|X or Y)\b  in headings/titles
Then check: (?i)(unlike|in contrast|compared to|better than|vs|versus)  in body text
Then check: <table  present in the content
Flag if: comparative heading found, no contrast language AND no comparison table
Severity: INFO
```

---

## 6. Negative Definitions

Defining who/what a product is NOT for is a high-value signal for two reasons:

1. **AI exclusion queries:** "which mattress is not for stomach sleepers" — only content with explicit negative definitions answers this.
2. **Targeting precision:** Narrow persona definition increases citation probability for the right audience query.

### Patterns

```
Not recommended for: stomach sleepers, children under 12, bodyweight over 120 kg.
Not suitable for: use on adjustable bases without rigid slat support.
Avoid if: you prefer a cloud-soft feel — this mattress is designed for firm support.
This product is not designed for: outdoor use, temperatures below 5°C.
```

### Placement

- Product descriptions: one "Not recommended for:" block near the persona definition.
- Category pages: "Who this category is NOT for" subsection.
- FAQ: "Is X right for me?" answer should include negative persona.

### Grep patterns

```
# Check product/category pages for negative definition
Detect: (?i)(not recommended for|not suitable for|avoid if|not designed for|not ideal for)
Flag if: product or category page (detected by Product schema or URL pattern) has no negative definition
Severity: INFO
```

---

## 7. Justified Superlatives

Superlatives without justification are ignored by AI ("best mattress" is marketing noise). Superlatives with evidence are cited.

### Formula

```
[Superlative claim] + [specific reason] + [evidence or data]
```

### Examples

| Bad (ignored) | Good (citable) |
|---|---|
| "The best mattress for back pain" | "The best mattress for back pain because H3 firmness maintains neutral lumbar alignment — validated by our customer data showing 78% pain reduction after 30 days." |
| "Most durable laptop battery" | "Longest real-world battery life in the under-1.5 kg category — 14.2 hours in our standardised office test." |
| "Premium quality" | "Premium build: aluminium chassis, ISO military-grade drop rating (MIL-STD-810H), 3-year warranty." |

### Rule

Every superlative must be followed within the same sentence by "because", "with", "achieving", or a colon introducing a specific measurement.

---

## 8. The 13-Week Freshness Threshold

Research shows 50% of top AI-cited content was published or updated within the last 13 weeks (Blyskall, 40M AI Overviews results). After 13 weeks without a visible update, citation probability drops.

### Freshness strategy

| Action | Frequency | Priority pages |
|---|---|---|
| Full content review and update | Every 12 weeks | Top-traffic pillar pages |
| Date + minor fact refresh | Every 13 weeks | High-competition cluster articles |
| Add new FAQ or data point | On new data availability | Product pages, comparison guides |
| Update `dateModified` in JSON-LD AND visible text | On every meaningful change | All indexable pages |

### Visible freshness signals

Both are required:
1. JSON-LD `dateModified` field.
2. Visible "Updated: [date]" or "Last reviewed: [date]" text near the article byline.

JSON-LD alone is insufficient — AI engines parse visible text; users trust visible dates.

---

## 9. Author E-E-A-T (Experience Signal)

Google's most important E-E-A-T shift in 2025 was elevating **Experience** — content from someone who actually used the product, visited the place, or performed the task. This signal is impossible for pure AI generation to replicate.

### Author requirements for citability

| Requirement | Implementation | AI signal |
|---|---|---|
| Real name (not "Admin" or "Team") | `<span class="author">Jane Doe</span>` + `Person` schema | Identity trust |
| Role/credentials in bio | ≥30 words of bio near author name | Expertise signal |
| `Person` schema with `sameAs` | LinkedIn, GitHub, ORCID, or personal site URL | Authoritativeness |
| First-person experience language | "I tested…", "In our lab…", "After 6 months of use…" | Experience signal |
| Date visible to user | "Published [date] · Updated [date]" | Freshness + trust |

### Author schema

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "author": {
    "@type": "Person",
    "name": "Jane Doe",
    "jobTitle": "Senior Product Tester",
    "sameAs": [
      "https://linkedin.com/in/janedoe",
      "https://github.com/janedoe"
    ]
  },
  "datePublished": "2026-03-01",
  "dateModified": "2026-04-20"
}
```

---

## References

- Blyskall study — 40M AI Overviews, backlinks vs content structure signals
- Smargol, P. (2026). SEO Copywriting 2026. Indygo Agency. https://indygo.agency
- Aggarwal et al. (2023). GEO: Generative Engine Optimization. Princeton/Georgia Tech. https://arxiv.org/abs/2311.09735
- Google E-E-A-T: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- See also: [ai-pipeline.md](ai-pipeline.md), [geo-guidelines.md](geo-guidelines.md), [geo-aeo-patterns.md](geo-aeo-patterns.md)
