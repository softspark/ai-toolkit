# W3C HTML Guidelines (SEO-Relevant Subset)

Reference for `seo-validate` Category 1 (HTML Semantics & W3C) and Category 2 (Meta & Open Graph).

Sources: W3C HTML Living Standard (HTML5), WCAG 2.2, IETF RFC 5646 (BCP 47), Open Graph Protocol, Twitter Card spec.

## Document Structure

### DOCTYPE

HTML5 §8.1.1 — the document MUST begin with `<!DOCTYPE html>` (case-insensitive). Missing doctype triggers quirks mode in older browsers and breaks modern CSS behavior — effectively a HIGH-severity issue.

```html
<!DOCTYPE html>
<html lang="en">
  <head>...</head>
  <body>...</body>
</html>
```

### lang attribute

HTML5 §3.2.6 — the `<html>` element SHOULD have a `lang` attribute using a BCP 47 language tag.

- Required for screen reader pronunciation (WCAG 3.1.1).
- Signals primary language to search engines.
- Feeds into hreflang correctness checks.

Valid examples:
- `lang="en"` — English (generic)
- `lang="en-US"` — English (United States)
- `lang="pl"` — Polish
- `lang="zh-Hant"` — Chinese (Traditional)

Invalid examples (flag these):
- `lang="en_US"` — underscore, not hyphen
- `lang="english"` — not an ISO code
- `lang="EN"` — case irrelevant per RFC but inconsistent; prefer lowercase

### charset

HTML5 §4.2.5.5 — `<meta charset="utf-8">` MUST appear in `<head>` as early as possible, within the first 1024 bytes. UTF-8 is the only accepted encoding for new content.

```html
<head>
  <meta charset="utf-8">
  <!-- other meta tags follow -->
</head>
```

### viewport

Not formally W3C but required for mobile-first indexing:

```html
<meta name="viewport" content="width=device-width, initial-scale=1">
```

Missing viewport = mobile rendering breaks = Google ranks the page lower.

## Document Outline

### Heading hierarchy

HTML5 §4.3.6 defines heading semantics. Current best practice:

- **Exactly one `<h1>`** per page/route component.
- **Sequential levels**: `h1` → `h2` → `h3`, never skip (e.g., `h1` → `h3`).
- **Semantic, not decorative**: heading level should reflect content hierarchy, not visual size. Use CSS for styling.

### Landmarks

HTML5 §4.3 + ARIA Landmarks. Every page should have at minimum:

- `<header>` — site/page header
- `<nav>` — primary navigation
- `<main>` — main content (exactly one per page)
- `<footer>` — site/page footer

Optionally: `<aside>`, `<section>` (requires accessible name), `<article>`.

Using `<div>` for these is a WARN — semantic HTML aids both screen readers and AI/LLM parsers.

## Meta Tags

### Title

HTML5 §4.2.2. Required element inside `<head>`.

- Recommended length: **50–60 characters** including brand/separator. Google truncates at ~600 pixels (~50–60 chars).
- Unique per page.
- Format: `Primary Keyword - Brand` or `Primary Keyword | Secondary | Brand`.
- Avoid keyword stuffing.

```html
<title>SEO Audit Tool - Free Analyzer | ExampleCo</title>
```

### Description

HTML `<meta name="description">`.

- Recommended length: **150–160 characters**. Google truncates at ~155 chars (mobile narrower).
- Unique per page.
- Include primary keyword naturally.
- Write as a SERP call-to-action.

```html
<meta name="description" content="Free SEO audit tool. Instantly analyze your site's title tags, meta descriptions, and Core Web Vitals. Fix issues before Google indexes them.">
```

### Canonical

HTML5 §4.2.4 + Google Search Central canonicalization.

- Required on indexable pages.
- Must be an absolute URL.
- Self-referencing canonical on canonical version.
- Points to preferred version when multiple URLs return the same content (tracking params, pagination, sort orders).

```html
<link rel="canonical" href="https://example.com/blog/post-slug">
```

#### Canonical + URL parameters

Query parameters create duplicate URLs unless handled explicitly. After Google deprecated the Search Console URL Parameters tool (April 2022), the only remaining signals are `rel="canonical"`, `robots.txt`, and `<meta name="robots">`.

**Tracking parameters** (`utm_source`, `utm_medium`, `utm_campaign`, `gclid`, `fbclid`, `msclkid`, `ref`):

Every variant must canonical to the clean URL:

```html
<!-- User lands on: https://example.com/page?utm_source=newsletter&utm_campaign=apr26 -->
<link rel="canonical" href="https://example.com/page">
```

**Faceted navigation** (filters, sort, pagination on category/product listing pages):

```html
<!-- URL: /products?category=shoes&color=red&sort=price-asc&page=2 -->
<!-- Strategy A: canonical to clean base, let Google dedup -->
<link rel="canonical" href="https://example.com/products">

<!-- Strategy B: canonical to first page + rel=prev/next (deprecated as signal but still used by some engines) -->
<link rel="canonical" href="https://example.com/products?category=shoes">
```

For facet combinations that are NOT genuinely different content (e.g., `?sort=name` vs `?sort=price`), always canonical to the clean URL. For facets that ARE different content (e.g., `/products?category=shoes` is a distinct shoe listing), the facet URL itself is canonical.

**Search result pages (SRPs)**:

Internal search results are thin, user-specific content. Google's Search Essentials explicitly lists SRPs as content to keep out of the index.

Two valid strategies:

```html
<!-- Strategy A: noindex, allow crawl (discovers outbound links) -->
<meta name="robots" content="noindex, follow">
<link rel="canonical" href="https://example.com/search">
```

```
# Strategy B: robots.txt Disallow — blocks crawl entirely
User-agent: *
Disallow: /search?*
Disallow: /*?q=*
```

Never combine Disallow + noindex — a disallowed URL will never be fetched, so the noindex directive is never read.

**Pagination**:

Modern Google treats paginated content as individual URLs. Each page self-canonicals:

```html
<!-- /blog?page=2 -->
<link rel="canonical" href="https://example.com/blog?page=2">
```

`rel="prev"` and `rel="next"` are deprecated as a Google signal (2019) but remain valid HTML and are used by other engines/accessibility tools.

### Robots

Controls indexing and following per-page.

```html
<!-- Indexable, links followed (default — usually omitted) -->
<meta name="robots" content="index, follow">

<!-- Block indexing (confirm intent!) -->
<meta name="robots" content="noindex, nofollow">

<!-- Common production mistake: leftover from dev -->
<meta name="robots" content="noindex">
```

`noindex` on production routes is a HIGH-severity finding unless explicitly intentional (admin pages, thank-you pages, search-results pages).

## Open Graph Protocol

`https://ogp.me/` — used by Facebook, LinkedIn, Slack, Discord, Teams, WhatsApp.

Required for rich social cards:

```html
<meta property="og:title" content="Page Title">
<meta property="og:description" content="Page description">
<meta property="og:image" content="https://example.com/og-image.jpg">  <!-- ABSOLUTE URL -->
<meta property="og:url" content="https://example.com/page">
<meta property="og:type" content="article">  <!-- or website, product, profile -->
<meta property="og:site_name" content="ExampleCo">
```

Image specs:
- Recommended: 1200×630 px (1.91:1 aspect ratio).
- Maximum: 8 MB.
- JPEG or PNG. WebP has limited platform support for OG.

Relative URLs for `og:image` are a definitive WARN — many scrapers don't resolve them.

## Twitter Card

```html
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@example">
<meta name="twitter:creator" content="@author">
<meta name="twitter:title" content="Page Title">
<meta name="twitter:description" content="Page description">
<meta name="twitter:image" content="https://example.com/twitter-image.jpg">
```

When OG tags are present, Twitter falls back to them for most fields — but `twitter:card` is still required.

## hreflang

RFC 5646 (BCP 47) language tags + ISO 3166-1 alpha-2 region codes.

### Format

```
<language-subtag>[-<region-subtag>]
```

Valid:
- `en`, `en-US`, `en-GB`, `pl`, `pt-BR`, `zh-Hant`, `sr-Cyrl`

Invalid:
- `en_US` (underscore)
- `EN-us` (case inconsistent — prefer lowercase language, uppercase region)
- `english` (not a code)
- `uk` is **Ukrainian**, not "UK English" (common confusion — `en-GB` is correct for British English)

### Implementation

Every locale version MUST include hreflang for every other locale, including itself, plus `x-default`:

```html
<link rel="alternate" hreflang="en-US" href="https://example.com/en-us/page">
<link rel="alternate" hreflang="en-GB" href="https://example.com/en-gb/page">
<link rel="alternate" hreflang="pl"    href="https://example.com/pl/page">
<link rel="alternate" hreflang="x-default" href="https://example.com/en-us/page">
```

### Bidirectionality

If page A links to page B via hreflang, page B MUST link back to page A. Broken bidirectionality is ignored by Google — a HIGH-severity issue.

### x-default

Fallback for users whose language doesn't match any listed locale. Usually points to the default/main version (often English).

## Validation

The W3C provides an online validator: https://validator.w3.org/ — but the `seo-validate` skill targets static source analysis, not rendered HTML validation.

For runtime validation, use:
- `html-validate` (npm)
- `htmlhint`
- Built-in linters in Next.js, Nuxt, Astro

## References

- HTML Living Standard: https://html.spec.whatwg.org/
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- BCP 47 (RFC 5646): https://datatracker.ietf.org/doc/html/rfc5646
- ISO 3166-1: https://www.iso.org/iso-3166-country-codes.html
- Open Graph Protocol: https://ogp.me/
- Google Search Central (title/description/canonical): https://developers.google.com/search/docs
