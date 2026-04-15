---
name: seo-validate
description: "Validate code against SEO best practices: W3C semantics, meta/OG tags, Schema.org, hreflang, Core Web Vitals (LCP/INP/CLS), resource hints, GEO, SPA/SSG/CSR crawlability, technical SEO, accessibility-for-SEO. Supports React/Next/Nuxt/Astro/Gatsby/SvelteKit/Remix/Angular/Vue/static HTML."
user-invocable: true
effort: medium
disable-model-invocation: true
context: fork
agent: seo-specialist
argument-hint: "[path] [--scope full|technical|content|performance|geo|rendering] [--severity high|warn|info] [--framework auto|next|nuxt|astro|gatsby|sveltekit|remix|angular|vue|react-spa|vite-spa|cra|static] [--rendering auto|csr|ssr|ssg|isr|hybrid] [--output markdown|json]"
allowed-tools: Read, Grep, Glob, Bash
---

# /seo-validate — SEO Validation Scanner

$ARGUMENTS

Scan a codebase for SEO issues using pattern-matching heuristics. Detects W3C/HTML violations, meta tag gaps, structured data problems, hreflang errors, Core Web Vitals risks (LCP/INP/CLS), resource-hint misuse, above-the-fold anti-patterns, GEO gaps, SPA/CSR/SSG crawlability problems, technical SEO misconfigurations, and accessibility-for-SEO issues. Read-only — never modifies files.

**Standards basis**: W3C HTML5 Recommendation, W3C WCAG 2.2, Schema.org vocabulary, IETF RFC 5646 (BCP 47 language tags) for hreflang, web.dev Core Web Vitals thresholds (LCP <2.5s, INP <200ms, CLS <0.1), Google Search Central crawlability guidelines, and emerging GEO (Generative Engine Optimization) practices.

## Usage

```
/seo-validate                                # Scan full project, auto-detect framework
/seo-validate src/                           # Scan specific path
/seo-validate --scope rendering              # Only SPA/CSR/SSG crawlability checks
/seo-validate --scope performance            # Only Core Web Vitals static signals
/seo-validate --scope geo                    # Only GEO (Generative Engine Optimization)
/seo-validate --severity high                # Filter to HIGH findings only
/seo-validate --framework next               # Force framework (skip auto-detection)
/seo-validate --rendering csr                # Force rendering-mode interpretation
/seo-validate --output json                  # Structured JSON output for CI integration
```

**Scopes:**
- `full` (default) — all 9 categories
- `technical` — HTML semantics, hreflang, CWV, rendering, technical SEO (categories 1, 4, 5, 7, 8)
- `content` — meta/OG, structured data, GEO, a11y-for-SEO (categories 2, 3, 6, 9)
- `performance` — only CWV static signals (category 5)
- `geo` — only GEO (category 6)
- `rendering` — only category 7 (SPA/CSR/SSG crawlability) — useful for migration audits

**Severity filtering:** `--severity high` shows only HIGH, `--severity warn` shows HIGH+WARN, `--severity info` shows all. Default: all.

## What This Command Does

1. **Detect framework and rendering mode** from `package.json`, config files, and entry HTML.
2. **Scan the codebase** using `Grep`/`Glob`/`Read` against framework-aware patterns for each category in scope.
3. **Interpret findings** with specific fix suggestions tied to the detected framework.
4. **Report** findings with file paths, line numbers, severity, confidence, and standards citations.

## Steps

### Step 1: Detect Framework & Rendering Mode

Run detection before scanning so category patterns can adapt. Detection order:

1. **Read `package.json`** (if present) and inspect `dependencies` + `devDependencies`:

| Deps contain | Framework | Default rendering |
|--------------|-----------|-------------------|
| `next` | `next` | hybrid (per-route) |
| `nuxt` | `nuxt` | ssr |
| `astro` | `astro` | ssg |
| `gatsby` | `gatsby` | ssg |
| `@sveltejs/kit` | `sveltekit` | hybrid |
| `@remix-run/*` | `remix` | ssr |
| `@angular/core` + `@angular/ssr` or `@nguniversal/*` | `angular` | ssr |
| `@angular/core` alone | `angular` | csr (flag as SPA) |
| `vue` + `nuxt` | see nuxt row | — |
| `vue` without `nuxt` | `vue` | csr (flag as SPA) |
| `react` + `vite` without Next/Remix | `vite-spa` | csr (flag as SPA) |
| `react-scripts` | `cra` | csr (flag as SPA) |
| no `package.json` OR no framework deps | `static` | static |

2. **Read config files** to refine:
   - `next.config.*` — check `output: 'export'` (forces SSG), `images`, i18n settings.
   - `nuxt.config.*` — check `ssr: false`, `generate` blocks (SSG export).
   - `astro.config.*` — check `output: 'server'|'static'|'hybrid'` and `prerender` directives.
   - `gatsby-config.*` — plugin list (`gatsby-plugin-react-helmet`, `gatsby-plugin-sitemap`).
   - `svelte.config.*` — adapter choice (`static`, `node`, `vercel`).
   - `vite.config.*` + `package.json` scripts — look for `vite-plugin-ssr`, `vite-plugin-prerender`.
   - `angular.json` — look for SSR builder config.

3. **Read entry HTML** (`public/index.html`, `index.html`, `app/layout.tsx`, `src/app.html`, etc.) to confirm whether meaningful content is prerendered or only a mount point (`<div id="root"></div>`).

4. **Override precedence**: `--framework` and `--rendering` flags override detection.

Report the detected framework and rendering mode in the Summary table.

### Step 2: Run Category Scans

For each category in `--scope`, apply the pattern set below using `Grep` (for regex across files) and `Read` (for config parsing / ordered checks). Patterns are framework-aware — use the framework detected in Step 1 to select the right rule set.

### Step 3: Interpret and Enrich

For each finding:

1. **Read the flagged file/lines** to confirm the match is real (not a comment, not a type-only reference).
2. **Add a specific fix** tied to the framework (e.g., "use `next/image` with `priority` prop" vs. "add `<link rel="preload" as="image">` to `<head>`").
3. **Mark confidence**: `definitive` for regex matches against known-bad patterns, `heuristic` for co-occurrence / absence checks.
4. **Skip false positives** when context shows the concern is addressed elsewhere (e.g., meta tags set in a layout file the route inherits from).

### Step 4: Report

Present findings sorted by severity (HIGH → WARN → INFO), then by file path.

---

## Scanner Reference

### Category 1: HTML Semantics & W3C

Scan HTML/JSX/Vue/Svelte/Astro templates for W3C HTML5 compliance.

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| `<html>` without `lang` attribute | HIGH | definitive | HTML5 §3.2.6 — `lang` required for SEO + a11y |
| Missing `<meta charset="utf-8">` in `<head>` | HIGH | definitive | HTML5 §4.2.5.5 — required first |
| Missing `<meta name="viewport">` | HIGH | definitive | Mobile-first indexing requires viewport |
| Multiple `<h1>` per page/route component | WARN | heuristic | One H1 per document is standard SEO practice |
| No `<h1>` in page component | WARN | heuristic | Every indexable page should have H1 |
| Heading level skip (h1 → h3) | WARN | heuristic | Document outline breaks assistive tech + crawlers |
| Missing landmarks (`<main>`, `<nav>`, `<header>`, `<footer>`) | WARN | heuristic | Semantic HTML aids both a11y and crawlers |
| Missing `<!DOCTYPE html>` | HIGH | definitive | Triggers quirks mode in older browsers |

See: [reference/w3c-guidelines.md](reference/w3c-guidelines.md)

---

### Category 2: Meta & Open Graph

Check `<head>` composition in entry HTML, framework metadata exports, and route-level metadata.

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| Missing `<title>` / framework title | HIGH | definitive | Required for SERP display |
| `<title>` >60 chars OR <10 chars | WARN | definitive | Recommended 50–60 char range |
| Missing `<meta name="description">` | HIGH | definitive | Required for SERP snippets |
| Description >160 chars OR <50 chars | WARN | definitive | Recommended 150–160 char range |
| Missing `<link rel="canonical">` on indexable pages | HIGH | definitive | Prevents duplicate-content dilution |
| `<meta name="robots" content="noindex">` on production route | WARN | heuristic | Confirm intentional — blocks indexing |
| Missing OG tags: `og:title`, `og:description`, `og:image`, `og:url`, `og:type` | WARN | definitive | Required for rich social cards |
| Missing Twitter Card (`twitter:card`) | WARN | definitive | Required for Twitter/X rich previews |
| OG image without absolute URL | WARN | definitive | OG spec requires absolute URLs |

**Framework adapters**:
- **Next.js App Router**: look for `export const metadata = { ... }` or `generateMetadata()` in `layout.tsx`/`page.tsx`.
- **Next.js Pages Router**: look for `<Head>` from `next/head`.
- **Nuxt**: look for `useHead()` / `definePageMeta({ title, ... })`.
- **Astro**: look for `<BaseHead>` component or direct `<meta>` in layout.
- **Gatsby**: look for `<Helmet>` from `react-helmet`.
- **SvelteKit**: look for `<svelte:head>` blocks.
- **SPAs (Vue/Vite/CRA/Angular)**: look for `react-helmet-async`, `vue-meta`, `@angular/platform-browser`'s `Meta`/`Title` services. Flag runtime-only meta as a rendering-crawlability issue (Category 7).

---

### Category 3: Structured Data / Schema.org

Scan for JSON-LD (`<script type="application/ld+json">`) presence and correctness on key page types.

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| No JSON-LD on article/blog route | WARN | heuristic | `Article` schema improves rich results |
| JSON-LD missing `@context` | HIGH | definitive | Must be `https://schema.org` |
| JSON-LD missing `@type` | HIGH | definitive | Type declaration is required |
| `Article` missing `headline` / `author` / `datePublished` | WARN | definitive | Required properties per schema.org |
| `FAQPage` missing `mainEntity` array | WARN | definitive | FAQ rich result needs Q&A pairs |
| `BreadcrumbList` missing `itemListElement` | WARN | definitive | Breadcrumb rich result needs list |
| `Organization` missing `name` / `url` / `logo` | WARN | definitive | Knowledge Graph signals |
| `Product` missing `name` / `offers` / `aggregateRating` | WARN | definitive | Product rich results |
| `LocalBusiness` missing `address` / `telephone` / `openingHours` | WARN | definitive | Local SEO signals |

See: [reference/schema-types.md](reference/schema-types.md) for required-property matrix.

---

### Category 4: Hreflang & i18n

Scan all locale variants for hreflang correctness.

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| Hreflang pair not bidirectional (A→B but not B→A) | HIGH | definitive | Google ignores unidirectional hreflang |
| Missing `hreflang="x-default"` | WARN | definitive | Fallback required for unmatched locales |
| Missing self-referencing hreflang tag | WARN | definitive | Each version must reference itself |
| Invalid BCP 47 code (e.g., `en_US` instead of `en-US`) | HIGH | definitive | RFC 5646 requires hyphen-separated subtags |
| Unknown language code (not ISO 639-1) | HIGH | definitive | Invalid language subtag |
| Unknown region code (not ISO 3166-1 alpha-2) | HIGH | definitive | Invalid region subtag |
| Hreflang points to URL returning canonical to different URL | WARN | heuristic | Canonical must match hreflang target |

---

### Category 5: Core Web Vitals (Static Signals)

Detect code patterns that cause CWV regressions. Covers LCP, INP, CLS, resource hints, and above-the-fold optimization.

#### 5a. LCP (Largest Contentful Paint, target <2.5s)

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| `<img>` without `width`/`height` attributes | HIGH | definitive | Causes CLS + delays LCP |
| Above-the-fold `<img>` without `fetchpriority="high"` (or framework equivalent) | HIGH | heuristic | LCP image must be prioritized |
| Above-the-fold `<img loading="lazy">` | HIGH | definitive | Actively harmful — delays LCP |
| `@font-face` without `font-display` | HIGH | definitive | Blocks text paint |
| Missing `<link rel="preload" as="image">` for known hero image | WARN | heuristic | Preload accelerates LCP |
| Missing `<link rel="preload" as="font" crossorigin>` for self-hosted webfonts | WARN | heuristic | Fonts are a common LCP blocker |
| Missing `<link rel="preconnect">` for 3rd-party font/image/CDN origins on critical path | WARN | heuristic | Saves ~100–300ms per origin |
| Render-blocking `<link rel="stylesheet">` without `media` split or critical-inline | WARN | heuristic | Blocks first paint |
| Responsive image: `<img>` >600px without `srcset`+`sizes` or `<picture>` | WARN | heuristic | Over-fetches on mobile |
| **Next.js**: `<img>` used instead of `next/image` in route component | WARN | definitive | Misses automatic optimization |
| **Next.js**: `next/image` without `priority` on detected LCP element | HIGH | heuristic | LCP will under-perform |
| **Nuxt**: `<img>` instead of `<NuxtImg>`/`<NuxtPicture>` | WARN | definitive | Misses auto-optimization |
| **Astro**: `<img>` instead of `<Image>` from `astro:assets` | WARN | definitive | Misses auto-optimization |
| **Gatsby**: `<img>` instead of `GatsbyImage` | WARN | definitive | Misses auto-optimization |

#### 5b. INP (Interaction to Next Paint, target <200ms)

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| `<script>` in `<head>` without `async`/`defer` | HIGH | definitive | Render-blocking |
| Third-party analytics/chat/ads without `async`/`defer` or framework lazy strategy | WARN | definitive | Blocks main thread |
| `document.write` usage | HIGH | definitive | Blocks parser; disabled by modern browsers |
| Heavy top-level `useEffect(() => {...}, [])` (many sync calls) | WARN | heuristic | Long tasks delay INP |
| Client bundle estimated >300KB gzipped gating interaction | WARN | heuristic | Excessive JS delays hydration + INP |
| **Next.js**: `<Script>` without `strategy` prop on non-critical scripts | WARN | definitive | Defaults to `afterInteractive` — often not optimal |
| Missing `fetchpriority="low"` on deferrable below-the-fold resources | INFO | heuristic | Helps browser prioritize LCP |

#### 5c. CLS (Cumulative Layout Shift, target <0.1)

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| Images without `width`/`height` or `aspect-ratio` CSS | HIGH | definitive | Primary CLS cause |
| Iframes (YouTube/maps/ads) without dimensions or aspect-ratio | HIGH | definitive | Embeds shift layout |
| Dynamically injected ads/embeds without reserved placeholder space | WARN | heuristic | Shifts layout on load |
| `@font-face` without `font-display: swap`/`optional` | WARN | definitive | FOIT/FOUT shifts |
| SSR hydration mismatch: `typeof window` branches rendering different content | WARN | heuristic | Hydration-triggered shift |
| Skeleton → content of different height | WARN | heuristic | Load-state shift |

#### 5d. Resource Hints & Route Prefetching

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| `<link rel="preload">` for non-critical resource | WARN | heuristic | Wastes bandwidth + contention |
| Next-route not prefetched when framework supports it (Next `<Link>`, Nuxt `<NuxtLink>`, SvelteKit `data-sveltekit-preload-data`) | INFO | heuristic | Hurts soft-navigation UX |
| External origin referenced in critical path without `<link rel="preconnect">` | WARN | definitive | Adds 100–300ms per origin |
| Less-critical external origin without `<link rel="dns-prefetch">` | INFO | heuristic | Lightweight fallback |
| ESM chunks on critical path without `<link rel="modulepreload">` | INFO | heuristic | Helps browser parse ahead |
| `<link rel="preload">` appears AFTER resource that uses it in document order | WARN | heuristic | Preload must come first to help |
| >6 `<link rel="preload">` directives on one page | WARN | heuristic | Over-hinting — browsers throttle |

#### 5e. Above-the-Fold Heuristic

"Above-the-fold" candidates (confidence: heuristic):
- First `<img>` / `<Image>` / `<NuxtImg>` / `<Image from 'astro:assets'>` / `GatsbyImage` inside a page/route component.
- First child of `<main>` or `<section>`.
- Components named `Hero`, `Banner`, `Masthead`, `Jumbotron`, `HeroSection`, `CoverImage`.
- Images inside `<header>` that appear before any scroll-margin content.

Rules for ATF elements:
- MUST have explicit `width` + `height`.
- MUST have high priority (`fetchpriority="high"` or `priority` prop).
- MUST NOT have `loading="lazy"`.
- SHOULD have a matching `<link rel="preload">` entry.

Rules for below-the-fold:
- SHOULD have `loading="lazy"` + `decoding="async"`.
- MAY have `fetchpriority="low"`.

See: [reference/core-web-vitals.md](reference/core-web-vitals.md)

---

### Category 6: GEO (Generative Engine Optimization)

Content structure for AI answer engines (ChatGPT, Perplexity, Google AI Overviews, Bing Copilot). **All findings here are severity `INFO`** — emerging practice, not penalty-causing.

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| No `FAQPage` schema on FAQ-style content | INFO | heuristic | Highly extractable by LLMs |
| No `speakable` schema on summary content | INFO | heuristic | Voice/audio answer engines |
| Long paragraphs (>400 words) without sub-headings | INFO | heuristic | Harder for LLMs to extract |
| Missing explicit citation/source markup (`<cite>`, author bylines) | INFO | heuristic | LLM answer engines prefer attributable sources |
| No `<q>` or quote schema on quoted content | INFO | heuristic | Aids AI extraction |
| No Q&A structure on how-to content | INFO | heuristic | LLMs favor structured Q&A |
| Heavy reliance on `<div>` over semantic HTML | INFO | heuristic | Semantic HTML improves AI parsing |
| Key facts hidden behind JS interactions (tabs, accordions) | INFO | heuristic | LLMs see initial DOM only |

See: [reference/geo-guidelines.md](reference/geo-guidelines.md)

---

### Category 7: Rendering Mode & SPA/CSR/SSG Crawlability ⭐

**The most critical category for JS apps.** A CSR-only app with no prerendering is effectively invisible to most crawlers.

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| Entry HTML contains only mount point (`<div id="root">` or `<div id="app">`) with no prerendered content, and no SSR/SSG configured | HIGH | definitive | Crawlers see empty page |
| Meta/title set only in JS runtime (react-helmet-async, vue-meta, `document.title = ...`) with no SSR/SSG fallback | HIGH | definitive | Public routes won't have crawlable meta |
| `HashRouter` / hash-based routing (`/#/about`) on public routes | HIGH | definitive | Google ignores fragments for indexing |
| CSR app without `<noscript>` fallback containing meaningful content | WARN | heuristic | Minimum no-JS signal for crawlers |
| **Next.js**: `'use client'` at top of every page/layout forcing CSR | WARN | heuristic | Defeats SSR/SSG benefits |
| **Next.js**: Content page missing `generateMetadata` / static `metadata` export | WARN | heuristic | No crawlable metadata |
| **Next.js**: `dynamic(..., { ssr: false })` wrapping LCP / above-the-fold content | HIGH | definitive | Blocks both SSR and LCP |
| **Nuxt**: `ssr: false` in config or route with public content | WARN | heuristic | Disables SSR intentionally |
| **Astro**: `client:only` on hero/content components | WARN | heuristic | Component not prerendered |
| **SvelteKit**: `export const ssr = false` on public route | WARN | heuristic | Disables SSR |
| **Gatsby**: route excluded from prerender (`gatsby-plugin-exclude`) | WARN | heuristic | Verify intent |
| **Angular SPA**: project uses `@angular/core` without `@angular/ssr` or `@nguniversal/*` | HIGH | definitive | Default Angular is CSR-only |
| **Vue SPA / React SPA / CRA / Vite-SPA**: no prerender plugin detected (no `vite-plugin-ssr`, `react-snap`, `prerender-spa-plugin`, `vite-plugin-prerender`) | HIGH | definitive | Content invisible to crawlers |
| `suppressHydrationWarning` overuse (>3 occurrences) | WARN | heuristic | Masks real hydration mismatches |
| `typeof window !== 'undefined'` / `isBrowser` checks in render paths | WARN | heuristic | Often signals hydration mismatch |
| Static `robots.txt` references dynamic routes that aren't prerendered | WARN | heuristic | Crawlers hit empty pages |
| `prerender.io` / `rendertron` / dynamic-rendering middleware detected | INFO | definitive | Legacy pattern — Google now prefers SSR/SSG |

See: [reference/spa-ssg-patterns.md](reference/spa-ssg-patterns.md)

---

### Category 8: Technical SEO

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| Missing `robots.txt` | HIGH | definitive | Blocks crawler directives + sitemap reference |
| `robots.txt` contains `Disallow: /` in production build | HIGH | definitive | Blocks entire site |
| Missing `sitemap.xml` / framework sitemap generator | HIGH | definitive | Slows discovery |
| `robots.txt` missing `Sitemap:` directive | WARN | definitive | Crawlers may not find sitemap |
| Canonical URLs inconsistent with actual deployed URLs | WARN | heuristic | Dilutes link equity |
| Canonical URL includes query params on parametrized pages (e.g., `?q=`, `?page=`, `?sort=`) | HIGH | heuristic | Canonical must point to clean base URL, not parametrized variant — else each query variant is a duplicate |
| Site has search feature (detected: `<input type="search">`, `<form action="/search">`, route `/search`, `?q=` / `?query=` / `?s=` / `?search=`) but `robots.txt` does NOT `Disallow` the search URL pattern | HIGH | heuristic | Parametrized search URLs create unlimited duplicate-content pages — crawl budget waste + index bloat |
| Site has faceted navigation (filters, sort params, pagination like `?filter=`, `?sort=`, `?page=`, `?color=`) without `robots.txt` Disallow rules OR parameter-handling via canonical | WARN | heuristic | Faceted URLs multiply indexable variants exponentially |
| Search result page (SRP) missing `<meta name="robots" content="noindex, follow">` | HIGH | heuristic | SRPs are thin/duplicate content per Google Search Essentials; indexing wastes crawl budget |
| Search result page missing self-referencing canonical OR canonical with dynamic query in it | WARN | heuristic | SRP should either canonical to clean `/search` or be noindexed entirely |
| Parametrized URLs (tracking: `utm_*`, `gclid`, `fbclid`, `ref=`) served without canonical to clean URL | HIGH | heuristic | Tracking params create duplicate URLs — canonical must strip them |
| Trailing-slash inconsistency (some pages `/about/`, some `/about`) | WARN | heuristic | Duplicate-content risk |
| HTTPS not enforced (hardcoded `http://` internal links) | WARN | definitive | Mixed-content + security |
| No 404 page / no custom `not-found` route | WARN | heuristic | Default 404s hurt UX |
| Meta `robots: noindex,nofollow` on indexable production routes | HIGH | heuristic | Blocks indexing — verify intent |

**Parameter-handling guidance**: Google deprecated the Search Console URL Parameters tool in April 2022. Today the only signals are:
1. **Canonical tags** — every parametrized variant must `<link rel="canonical">` to the clean base URL.
2. **`robots.txt` Disallow rules** — block crawlers from following parameter patterns entirely (`Disallow: /*?q=*`, `Disallow: /search?*`).
3. **`noindex` meta** — allow crawl (for link discovery) but prevent indexing on SRPs and thin faceted pages.

Choose ONE strategy per parameter type — mixing `Disallow` + `noindex` is contradictory (Disallow prevents crawler from ever seeing the noindex directive).

**Example `robots.txt` for a site with search**:
```
User-agent: *
Disallow: /search?*
Disallow: /*?q=*
Disallow: /*?query=*
Disallow: /*?s=*
Disallow: /*?utm_*
Disallow: /*?gclid=*
Disallow: /*?fbclid=*
Allow: /

Sitemap: https://example.com/sitemap.xml
```

**Example canonical on a parametrized page** (`/products?category=shoes&color=red&sort=price`):
```html
<link rel="canonical" href="https://example.com/products">
```

The canonical points to the clean page; the specific filter combination is a view, not a distinct URL.

---

### Category 9: Accessibility for SEO

Accessibility ↔ SEO overlap. WCAG compliance improves ranking signals.

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| `<img>` missing `alt` attribute | WARN | definitive | WCAG 1.1.1 + image SEO |
| `<img alt="">` on informational image | WARN | heuristic | Empty alt only for decorative |
| Icon-only `<button>` without `aria-label` | WARN | definitive | Screen readers + semantic crawlers |
| Form `<input>` without associated `<label>` | WARN | definitive | WCAG 3.3.2 |
| `<div>` used for interactive element (click handler on `<div>`) | WARN | heuristic | Should be `<button>` or `<a>` |
| Link text is "click here" / "read more" | WARN | heuristic | Anchor text is a ranking signal |
| `<a>` without `href` (fake link) | WARN | definitive | Not crawlable |

---

## Output Format

```markdown
## SEO Validation Report

### Summary
| Metric | Value |
|--------|-------|
| Scope | full / technical / content / performance / geo / rendering |
| Framework detected | next / nuxt / astro / gatsby / sveltekit / remix / angular / vue / react-spa / vite-spa / cra / static |
| Rendering mode | csr / ssr / ssg / isr / hybrid |
| Files scanned | N |
| Public routes found | N |
| Routes with prerendering | N of N |
| Findings: HIGH | N |
| Findings: WARN | N |
| Findings: INFO | N |

### Findings

#### [HIGH] app/layout.tsx:12
Category: HTML Semantics & W3C
Confidence: definitive
Pattern: `<html>` element missing `lang` attribute
W3C Rule: HTML5 §3.2.6
Fix: Add `lang="en"` (or appropriate BCP 47 code) to the `<html>` element.
See: reference/w3c-guidelines.md#lang-attribute

#### [HIGH] components/HomeHero.tsx:24
Category: Core Web Vitals (LCP)
Confidence: definitive
Pattern: Above-the-fold `<img>` with `loading="lazy"`
Rule: LCP anti-pattern — lazy loading the LCP element delays it
Fix: Remove `loading="lazy"`, add `fetchpriority="high"`. For Next.js use `<Image priority />`.
See: reference/core-web-vitals.md#above-the-fold

#### [HIGH] src/App.tsx:1
Category: Rendering Mode & SPA Crawlability
Confidence: definitive
Pattern: CSR-only React app (Vite) with no prerender plugin
Rule: Content-site SPAs without SSR/SSG are invisible to most crawlers
Fix: Add `vite-plugin-ssr` or migrate to Next.js/Remix; OR add `react-snap` for build-time prerender.
See: reference/spa-ssg-patterns.md#react-spa-migration
```

**Confidence values**:
- `definitive` — regex match against a known-bad pattern with high precision.
- `heuristic` — co-occurrence / absence / ordering / above-the-fold inference — may be false positive.

**Exit codes** (when `--output json`):
- `0` — no HIGH findings.
- `1` — one or more HIGH findings.

## Rules

- **Read-only**: Never modify any files. Report findings only.
- **Framework-aware**: Always detect framework first; apply the correct rule set.
- **Standards citation**: Every HIGH/WARN finding must cite a W3C/Schema.org/RFC/web.dev reference.
- **Skip non-source files**: Binary files, lock files (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`), vendored directories (`node_modules/`, `vendor/`, `.git/`, `dist/`, `build/`, `out/`, `.next/`, `.nuxt/`, `.svelte-kit/`, `public/build/`).
- **No false confidence**: Label heuristic findings clearly; above-the-fold detection is always heuristic.
- **GEO is INFO-only**: Never flag GEO findings as HIGH/WARN — it is emerging practice.
- **SPA HIGH bar**: Only flag Category 7 HIGH when the app is clearly a content site (has public routes with meaningful content). Auth-gated apps (dashboards, admin panels) should stay at WARN/INFO since SEO is not a concern.
- **Noscript is not a substitute for SSR/SSG**: `<noscript>` catches only the "no-JS" case, not the "crawler without JS execution" case — don't upgrade a CSR HIGH to WARN just because noscript exists.
- **No auto-fix in v1**: Fixing SEO issues requires design/content decisions beyond pattern matching.

## Reference Documents

- [reference/w3c-guidelines.md](reference/w3c-guidelines.md) — HTML5 semantic requirements, meta tag specs, language tag rules.
- [reference/core-web-vitals.md](reference/core-web-vitals.md) — LCP/INP/CLS thresholds, resource hints, above-the-fold heuristic, per-framework image components.
- [reference/geo-guidelines.md](reference/geo-guidelines.md) — GEO principles, `speakable` schema, citation/source markup, AI-extractable content structure.
- [reference/schema-types.md](reference/schema-types.md) — Schema.org JSON-LD templates (Article, FAQ, BreadcrumbList, Organization, Product, LocalBusiness) with required properties.
- [reference/spa-ssg-patterns.md](reference/spa-ssg-patterns.md) — Rendering-mode decision tree, SPA pitfalls, per-framework detection patterns, prerendering strategies.
