# GEO — Generative Engine Optimization

Reference for `seo-validate` Category 6. Structuring content so AI answer engines (ChatGPT, Perplexity, Google AI Overviews, Bing Copilot, Claude, Google AI Mode) can extract, cite, and quote it accurately.

GEO patterns have measurable impact on AI citation probability. **Category 6 findings are `WARN` (chunk size, author quality, freshness) or `INFO` (hedging, frameworks, contrast, bio)** — guidance based on citation research, not penalty-causing.

See [ai-pipeline.md](ai-pipeline.md) for Google's 4-stage pipeline and 7 ranking signals. See [content-citability.md](content-citability.md) for chunk anatomy, semantic triples, and hedging patterns.

## Core Principles

1. **Structure over prose.** LLMs extract facts from structured blocks (headings, lists, tables, Q&A, schema) much better than from long paragraphs.
2. **Be citable.** Provide explicit sources, authors, dates, and facts that can be quoted verbatim.
3. **Answer the question.** Lead with the answer, then elaborate. "Inverted pyramid" journalism works for LLMs too.
4. **Semantic HTML over div soup.** AI parsers rely on semantic structure just like screen readers.
5. **Don't hide content behind JS.** Crawler-level LLM ingestion sees initial DOM; hidden tabs/accordions lose their content in extraction.

---

## Content Structure Patterns

### Lead with the answer

LLMs often extract the first 1–2 sentences after a heading as the "answer" to the question that heading implies.

```html
<!-- Good -->
<h2>How long does shipping take?</h2>
<p>Standard shipping takes 3–5 business days in the US and 7–14 days internationally. Express options are 1–2 and 3–7 days respectively.</p>
<p>Orders placed before 2pm ET ship same-day. Delivery dates are confirmed at checkout based on your address.</p>

<!-- Bad (LLM extracts "we care about fast delivery" as the "answer") -->
<h2>How long does shipping take?</h2>
<p>At ExampleCo we care deeply about fast delivery, which is why we've invested in our logistics network...</p>
<p>(Buried eventually: 3–5 business days standard.)</p>
```

### Explicit Q&A blocks

Q&A structure is the single highest-signal pattern for LLM extraction:

```html
<section class="faq">
  <h2>Frequently Asked Questions</h2>
  <div>
    <h3>What is X?</h3>
    <p>X is ...</p>
  </div>
  <div>
    <h3>How much does X cost?</h3>
    <p>X costs $... per ...</p>
  </div>
</section>
```

Pair with `FAQPage` JSON-LD (see [schema-types.md](schema-types.md)).

### Tables for comparative data

Plans, pricing, specs, feature matrices:

```html
<table>
  <caption>Plan comparison</caption>
  <thead>
    <tr><th>Feature</th><th>Free</th><th>Pro</th><th>Enterprise</th></tr>
  </thead>
  <tbody>
    <tr><th scope="row">Users</th><td>1</td><td>10</td><td>Unlimited</td></tr>
    <tr><th scope="row">Storage</th><td>5GB</td><td>100GB</td><td>Unlimited</td></tr>
  </tbody>
</table>
```

LLMs excel at extracting tabular data but struggle when the same info is written as prose.

### Lists for steps

Use `<ol>` for ordered steps, `<ul>` for unordered sets:

```html
<h2>How to reset your password</h2>
<ol>
  <li>Go to the login page.</li>
  <li>Click "Forgot password".</li>
  <li>Enter your email. A reset link arrives within 2 minutes.</li>
  <li>Click the link and choose a new password.</li>
</ol>
```

Pair with `HowTo` schema for critical procedures.

### Definition lists for glossaries

```html
<dl>
  <dt>LCP</dt>
  <dd>Largest Contentful Paint — time to render the largest visible element. Target: under 2.5 seconds.</dd>

  <dt>INP</dt>
  <dd>Interaction to Next Paint — longest interaction latency in a session. Target: under 200ms.</dd>
</dl>
```

---

## Attribution & Citations

LLM answer engines (especially Perplexity, Google AI Overviews, Bing Copilot) prefer citable sources.

### Author bylines

```html
<article>
  <h1>Article title</h1>
  <p class="byline">
    By <a rel="author" href="/authors/jane-doe">Jane Doe</a>,
    <time datetime="2026-04-09">April 9, 2026</time>
  </p>
  <p>...</p>
</article>
```

Pair with `Article` schema including `author` and `datePublished`.

### Inline citations

```html
<p>
  Google's Core Web Vitals include LCP, INP, and CLS
  <cite><a href="https://web.dev/vitals/">web.dev/vitals</a></cite>.
</p>

<p>
  According to the 2024 State of JS report, React adoption
  is at 76%<sup><a href="#ref-1">[1]</a></sup>.
</p>
```

### Quotes

Use `<blockquote>` with `cite` attribute, or `<q>` for inline:

```html
<blockquote cite="https://example.com/source">
  <p>Direct quote here.</p>
  <footer>— <cite>Source Author, Source Publication</cite></footer>
</blockquote>

<p>As Crockford put it, <q cite="https://example.com">JavaScript is the world's most misunderstood language</q>.</p>
```

---

## speakable Schema

Marks portions of a page suited for audio/voice answer engines (Google Assistant, Alexa, Siri).

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "speakable": {
    "@type": "SpeakableSpecification",
    "cssSelector": [".article-summary", "h1"]
  }
}
</script>
```

- `cssSelector`: CSS selectors for speakable content.
- `xpath`: XPath selectors (alternative).

Best for: news article summaries, FAQ answers, definitions.

---

## JS-Gated Content Anti-Patterns

LLM crawlers typically ingest the initial DOM. Content revealed by clicks/hovers/scrolls may not be captured.

### Avoid for critical content

```jsx
// Bad — key FAQ answers hidden
<Accordion>
  <AccordionItem title="What does X cost?">
    <p>X costs $...</p>  {/* Hidden until clicked */}
  </AccordionItem>
</Accordion>

// Good — content visible by default, collapsed via CSS (still in DOM)
<details>
  <summary>What does X cost?</summary>
  <p>X costs $...</p>  {/* In DOM always — <details> is semantic */}
</details>
```

The native `<details>`/`<summary>` element is a rare exception — content is in the DOM, just visually collapsed.

### Tabs

Similar issue. If tab content is only rendered when active, hidden tabs are lost:

```jsx
// Bad — only active tab rendered
{activeTab === 'pricing' && <PricingContent />}

// Better — all rendered, hidden via CSS
<div hidden={activeTab !== 'pricing'}>
  <PricingContent />
</div>
```

---

## Per-Framework Notes

### Next.js / Remix / SvelteKit / Astro / Gatsby (SSR/SSG)

These render content server-side. GEO concerns are mostly about content structure, not rendering mode.

### SPAs without SSR (Vue, React CRA, Vite-SPA, Angular without Universal)

These don't render content for crawlers at all. **Category 7 (rendering) supersedes GEO** — fix the SPA crawlability first; GEO is moot if nothing is visible.

---

## Chunk Architecture

Google's retrieval stage (Stage 2 of the pipeline — see [ai-pipeline.md](ai-pipeline.md)) splits content into chunks of ≤500 tokens (~375 words). AI does not read your article — it extracts one chunk and uses it as the answer. If the answer is distributed across multiple sections or buried after a long preamble, AI cannot assemble it.

**The 375-word rule:** Each H2 section should stay within ~375 words. If a section runs longer, add an H3 — each H3 becomes its own independent chunk candidate.

### Anatomy of a citable chunk

```
H2: [Question or keyword-rich heading]
│
├── Direct answer — 2–3 sentences. Fact first. No preamble.
│
├── Elaboration — data, context, nuance. 3–5 sentences.
│
├── Visual element — list, table, or code block.
│
└── TL;DR (optional) — 1-sentence summary for long sections.
```

### Before / after

**Before (unchunkable):**
```
H2: Choosing the Right Mattress

When you're looking for a new mattress, there are many factors to consider.
The market offers a wide variety of options, and it can be overwhelming...
[70 words of preamble]
Eventually, firmness is one of the most important factors...
```
*AI extracts the preamble as the "answer" — zero information.*

**After (chunk-optimised):**
```
H2: How to Choose Mattress Firmness by Body Weight

Match firmness to your weight: under 70 kg → H1–H2; 70–90 kg → H3; over 90 kg → H4.
Higher body weight needs firmer support to maintain spinal alignment.

| Weight    | Firmness  |
|-----------|-----------|
| < 70 kg   | H1–H2     |
| 70–90 kg  | H3        |
| > 90 kg   | H4        |
```
*AI extracts the first two sentences. Table is precision bonus.*

---

## Semantic Triples vs Marketing Prose

AI answer engines parse content as Subject → Predicate → Object triples. Marketing prose requires inference; triples require none — lower hallucination risk, higher citation frequency.

| Style | Example | AI extractable? |
|---|---|---|
| Marketing prose | "Our exceptional collection will enchant you with its elegance." | No — zero extractable facts |
| Semantic triples | "Firmness: H3. Dimensions: 160×200 cm. Ideal for: side sleepers, 70–90 kg. Not for: stomach sleepers." | Yes — 4 distinct facts |

Each triple answers a different AI sub-query. Six triples on a product page = six citation opportunities.

---

## Opinionated Content

AI skips hedged claims. "This may be a good choice for many people" cannot be used as an answer to "which mattress should I buy?" Google's Jetstream signal explicitly rewards declarative, opinionated content.

**Hedging to eliminate → replacement:**

| Hedging | Replacement |
|---|---|
| "may be a good choice" | "We recommend X for Y" |
| "worth considering" | "Our top pick for Z is X" |
| "for many people" | "for side sleepers weighing 70–90 kg" |
| "it depends" | "It depends on your weight: under 70 kg → H2, over 90 kg → H4" |

**Rule:** Every guide and product page must take a position. Recommendation + named persona + justification = citable.

---

## The 13-Week Freshness Rule

50% of top AI-cited content was published or updated within the last 13 weeks (Blyskall, 40M AI Overviews results). After 13 weeks without a visible update, citation probability drops.

**Both signals required:**
1. `dateModified` in JSON-LD — machine-readable freshness signal.
2. Visible "Updated: [date]" near the byline — AI engines parse visible text; users trust visible dates.

JSON-LD alone is insufficient.

**Refresh strategy:**

| Action | Interval |
|---|---|
| Full content review + update | Every 12 weeks for top pillar pages |
| Date + minor fact refresh | Every 13 weeks for cluster articles |
| Add new FAQ or data point | On new data availability for product pages |

---

## Checklist (Category 6 findings)

- [ ] Each H2 section is ≤375 words; sections exceeding this have an H3 sub-heading.
- [ ] First paragraph under each heading is ≤60 words before a concrete fact or recommendation.
- [ ] No hedging language ("may be", "worth considering", "for many") in recommendation contexts.
- [ ] At least one decision framework ("if X → choose Y") per guide or category page.
- [ ] At least one explicit contrast ("X vs Y", "unlike X") per comparison page.
- [ ] At least one negative definition ("not recommended for…") per product or category page.
- [ ] Author block: real name (not "Admin"), ≥30-word bio, `Person` schema with `sameAs`.
- [ ] `dateModified` in JSON-LD AND visible "Updated: [date]" text present.
- [ ] FAQ-style content uses `FAQPage` schema.
- [ ] Summary content uses `speakable` schema.
- [ ] Citations use `<cite>` and author bylines.
- [ ] Quoted content uses `<blockquote>`/`<q>` with `cite` attr.
- [ ] How-to content uses `<ol>` + `HowTo` schema.
- [ ] Comparative data uses `<table>` with proper headers.
- [ ] Glossary content uses `<dl>`/`<dt>`/`<dd>`.
- [ ] Semantic HTML (`<article>`, `<section>`, `<main>`) used over `<div>`.
- [ ] Critical content is NOT hidden behind tabs/accordions (except native `<details>`).

---

## References

- Princeton/Georgia Tech GEO paper (Aggarwal et al., 2023): https://arxiv.org/abs/2311.09735
- Schema.org speakable: https://schema.org/speakable
- Schema.org FAQPage: https://schema.org/FAQPage
- Schema.org HowTo: https://schema.org/HowTo
- Google Search Central (structured data guidelines): https://developers.google.com/search/docs/appearance/structured-data
