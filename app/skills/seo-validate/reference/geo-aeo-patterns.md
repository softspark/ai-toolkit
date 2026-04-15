# AEO — Answer Engine Optimization

Reference for `seo-validate` Category 6 (GEO/AEO). Companion to [geo-guidelines.md](geo-guidelines.md). Focuses on optimizing content to appear in AI-generated answers — not just ranked pages.

All AEO findings are severity `INFO` — emerging practice, no known penalties.

---

## 1. What is AEO

Traditional SEO ranks pages. AEO targets AI-synthesized answers that cite or paraphrase your content without requiring a click.

**Key answer engines:**

| Engine | Mechanism |
|--------|-----------|
| Google AI Overviews | Retrieval-augmented summarization over organic index |
| Bing Copilot | GPT-4 grounded on Bing index; inline citations |
| Perplexity | Real-time retrieval + LLM synthesis; explicit source cards |
| ChatGPT Search | OpenAI web retrieval; used in ChatGPT Plus |

**Difference from classic SEO:** AI engines do not rank pages against each other — they extract the most useful fragment. A page ranked #8 with a direct-answer paragraph can beat #1 in AI responses.

---

## 2. Content Structure for AI Consumption

### Direct-answer paragraphs (first-sentence-answer pattern)

AI engines extract the first 1–3 sentences after a heading as the answer to the implied question. Put the fact first.

```html
<!-- Good -->
<h2>What is a canonical URL?</h2>
<p>A canonical URL is the preferred page version search engines should index when near-duplicates exist. Specify it with <code>&lt;link rel="canonical" href="..."&gt;</code> in <code>&lt;head&gt;</code>.</p>

<!-- Bad: answer buried after filler -->
<h2>What is a canonical URL?</h2>
<p>When building websites, you often encounter situations where multiple URLs serve similar content...</p>
```

### FAQ schema with concise Q&A pairs

`FAQPage` is the highest-precision signal. Each `acceptedAnswer` is extracted as a direct response to its `name` question. Pair with matching visible HTML.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [{
    "@type": "Question",
    "name": "How do I add a canonical tag in Next.js?",
    "acceptedAnswer": {
      "@type": "Answer",
      "text": "In App Router: export const metadata = { alternates: { canonical: 'https://example.com/page' } }. In Pages Router: use <Head><link rel=\"canonical\" href=\"...\" /></Head>."
    }
  }]
}
```

Rules: question text = natural-language query; answer = self-contained under 300 chars for voice engines.

### HowTo schema with numbered steps

```json
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "How to configure robots.txt for a Next.js site",
  "step": [
    { "@type": "HowToStep", "position": 1, "name": "Create the file", "text": "Add robots.txt to public/." },
    { "@type": "HowToStep", "position": 2, "name": "Add directives", "text": "Set User-agent, Disallow, Allow, and Sitemap URL." }
  ]
}
```

Match with a visible `<ol>` — never schema without HTML steps.

### QAPage schema for single-question articles

Use `QAPage` for knowledge-base and support docs structured around one primary question. Include `author` + `answerCount` fields.

### Entity-first writing

Define the subject before explaining it. AI engines build knowledge-graph connections from entity definitions.

```html
<!-- Good: entity defined first -->
<h2>Core Web Vitals</h2>
<p>Core Web Vitals are three Google-defined UX metrics: LCP, INP, and CLS. They are used as ranking signals in Google Search since 2021.</p>
```

---

## 3. Technical Signals

### llms.txt / llms-full.txt

The `llms.txt` convention (analogous to `robots.txt` for AI agents) lets agents discover curated content. Serve at domain root.

```
# /llms.txt
> ExampleCo builds developer tooling for SEO automation.

## Docs
- [API Reference](https://example.com/docs/api/llms.txt): Full API docs
- [Getting Started](https://example.com/docs/start/llms.txt): Setup guide
```

`llms-full.txt` = concatenated full-text for one-shot context loading.

### robots.txt AI bot directives

Known AI crawler `User-agent` strings:

| Bot | Owner | Purpose |
|-----|-------|---------|
| `GPTBot` | OpenAI | ChatGPT training + search |
| `OAI-SearchBot` | OpenAI | ChatGPT Search real-time retrieval |
| `ClaudeBot` | Anthropic | Claude training |
| `anthropic-ai` | Anthropic | Claude real-time retrieval |
| `PerplexityBot` | Perplexity | Real-time answer grounding |
| `Google-Extended` | Google | Gemini training (NOT AI Overviews) |
| `Googlebot` | Google | Organic + AI Overviews |

Blocking `Googlebot` blocks AI Overviews. Block `Google-Extended` to opt out of Gemini training only.

```
User-agent: GPTBot
Allow: /docs/
Disallow: /

User-agent: Google-Extended
Disallow: /

Sitemap: https://example.com/sitemap.xml
```

### Sitemap with lastmod

Include `<lastmod>` reflecting actual content change dates — not today's build date. AI engines prefer recently-updated sources.

### Clean HTML semantics

AI parsers rely on heading hierarchy. Rules:
- One `<h1>` per page — becomes the answer title in AI responses.
- `<h2>` maps to extractable sub-questions.
- Never skip heading levels.
- Use `<article>`, `<section>`, `<main>` over `<div>` wrappers.

---

## 4. Content Quality Signals

### E-E-A-T

| Signal | Implementation |
|--------|---------------|
| Experience | First-person case studies, original screenshots, tested procedures |
| Expertise | Author byline + `Person` schema with `sameAs` links (LinkedIn, GitHub) |
| Authoritativeness | `Organization` schema with `sameAs` to Wikidata/Crunchbase |
| Trustworthiness | HTTPS, `dateModified` on articles, correction notices |

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "How to Optimize robots.txt for AI Crawlers",
  "author": {
    "@type": "Person",
    "name": "Jane Doe",
    "sameAs": ["https://github.com/janedoe", "https://linkedin.com/in/janedoe"]
  },
  "datePublished": "2026-03-01",
  "dateModified": "2026-04-10"
}
```

### Citation-worthy content

- Statistics with sources: "76% of developers use React (State of JS 2024)" — not "most developers."
- Dated claims: include year on every statistic.
- Expert quotes in `<blockquote cite="...">` with named speaker.
- Outbound links to primary sources (w3.org, ietf.org, schema.org, developers.google.com, developer.mozilla.org, arxiv.org) — AI engines treat authoritative outbound links as a credibility signal.

---

## 5. Grep Patterns for Automated Detection

All patterns below yield `INFO` + `heuristic` findings.

### Missing FAQ schema on FAQ-like content

```
Detect: (?i)(frequently asked questions|faq|common questions)  in *.html,*.tsx,*.jsx,*.vue,*.svelte,*.astro
Then check: "FAQPage"  in same file or its layout
Flag if: FAQ heading found, no FAQPage schema present
```

### Missing llms.txt

```
Glob: llms.txt  in public/, static/, site root
Flag if: not found
```

### robots.txt missing AI bot directives

```
File: robots.txt
Pattern: GPTBot|ClaudeBot|PerplexityBot|Google-Extended|OAI-SearchBot|anthropic-ai
Flag if: robots.txt exists but no AI-specific User-agent rules found
```

### How-to headings without HowTo schema

```
Detect: (?i)<h[2-3][^>]*>how (to|do|can|should)\s  in *.html,*.tsx,*.jsx,*.vue,*.svelte,*.astro
Then check: "HowTo"  in same file or layout
Flag if: how-to heading found, no HowTo schema present
```

### Missing author/date metadata on articles

```
Detect: (?i)<article|"@type"\s*:\s*"Article"  in *.html,*.tsx,*.jsx,*.vue,*.svelte,*.astro
Then check: datePublished|rel="author"|<time datetime
Flag if: article detected, neither datePublished in JSON-LD nor <time datetime> in HTML
```

---

## Checklist (Category 6 AEO additions)

- [ ] `llms.txt` present at domain root.
- [ ] `robots.txt` has explicit AI bot directives.
- [ ] Sitemap `<lastmod>` reflects actual content change dates.
- [ ] FAQ content uses `FAQPage` schema with self-contained answers.
- [ ] How-to content uses `HowTo` schema with `step` array + visible `<ol>`.
- [ ] Single-question pages use `QAPage` schema.
- [ ] Articles have `datePublished` + `dateModified` in JSON-LD.
- [ ] Author bylines use `Person` schema with `sameAs` links.
- [ ] Statistics include inline source citations with year.
- [ ] `<h2>` headings phrased as natural-language questions where applicable.
- [ ] Entity terms defined on first use.

---

## References

- llmstxt.org spec: https://llmstxt.org
- OpenAI GPTBot docs: https://platform.openai.com/docs/gptbot
- Google-Extended opt-out: https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers
- Google E-E-A-T guidance: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- Schema.org FAQPage: https://schema.org/FAQPage
- Schema.org HowTo: https://schema.org/HowTo
- Schema.org QAPage: https://schema.org/QAPage
- Schema.org Article: https://schema.org/Article
- Princeton/Georgia Tech GEO paper (Aggarwal et al., 2023): https://arxiv.org/abs/2311.09735
