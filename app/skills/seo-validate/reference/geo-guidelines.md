# GEO — Generative Engine Optimization

Reference for `seo-validate` Category 6. Structuring content so AI answer engines (ChatGPT, Perplexity, Google AI Overviews, Bing Copilot, Claude) can extract, cite, and quote it accurately.

GEO is emerging practice, not a ranking algorithm with known penalties. **All findings in Category 6 are severity `INFO`** — guidance, not enforcement.

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

## Checklist (Category 6 findings)

- [ ] FAQ-style content uses `FAQPage` schema.
- [ ] Summary content uses `speakable` schema.
- [ ] Paragraphs >400 words are broken up with sub-headings.
- [ ] Citations use `<cite>` and author bylines.
- [ ] Quoted content uses `<blockquote>`/`<q>` with `cite` attr.
- [ ] How-to content uses `<ol>` + `HowTo` schema.
- [ ] Comparative data uses `<table>` with proper headers.
- [ ] Glossary content uses `<dl>`/`<dt>`/`<dd>`.
- [ ] Semantic HTML (`<article>`, `<section>`, `<main>`, `<nav>`, `<aside>`) is used over `<div>`.
- [ ] Critical content is NOT hidden behind tabs/accordions (except native `<details>`).

---

## References

- Princeton/Georgia Tech GEO paper (Aggarwal et al., 2023): https://arxiv.org/abs/2311.09735
- Schema.org speakable: https://schema.org/speakable
- Schema.org FAQPage: https://schema.org/FAQPage
- Schema.org HowTo: https://schema.org/HowTo
- Google Search Central (structured data guidelines): https://developers.google.com/search/docs/appearance/structured-data
