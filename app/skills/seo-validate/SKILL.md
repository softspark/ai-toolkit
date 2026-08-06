---
name: seo-validate
description: "SEO validator: meta/OG, Schema.org, hreflang, Core Web Vitals, crawlability. Triggers: SEO, meta tags, Schema.org, hreflang, LCP, INP, CLS, Core Web Vitals, sitemap, crawlability."
user-invocable: true
effort: medium
disable-model-invocation: true
context: fork
agent: seo-specialist
argument-hint: "[path] [--scope full|technical|content|performance|geo|rendering|topical] [--severity high|warn|info] [--framework auto|next|nuxt|astro|gatsby|sveltekit|remix|angular|vue|react-spa|vite-spa|cra|static] [--rendering auto|csr|ssr|ssg|isr|hybrid] [--output markdown|json]"
allowed-tools: Read, Grep, Glob, Bash
---

# /seo-validate — SEO Validation Scanner

$ARGUMENTS

Scan a codebase for SEO issues using pattern-matching heuristics. Detects W3C/HTML violations, meta tag gaps, structured data problems, hreflang errors, Core Web Vitals risks (LCP/INP/CLS), resource-hint misuse, above-the-fold anti-patterns, GEO gaps (chunk architecture, hedging language, decision frameworks, semantic triples, freshness), topical authority gaps (pillar/cluster structure, orphan pages, cannibalization), SPA/CSR/SSG crawlability problems, technical SEO misconfigurations, and accessibility-for-SEO issues. Read-only — never modifies files.

**Standards basis**: W3C HTML5 Recommendation, W3C WCAG 2.2, Schema.org vocabulary, IETF RFC 5646 (BCP 47 language tags) for hreflang, web.dev Core Web Vitals thresholds (LCP <2.5s, INP <200ms, CLS <0.1), Google Search Central crawlability guidelines, and emerging GEO (Generative Engine Optimization) practices.

## Usage

```
/seo-validate                                # Scan full project, auto-detect framework
/seo-validate src/                           # Scan specific path
/seo-validate --scope rendering              # Only SPA/CSR/SSG crawlability checks
/seo-validate --scope performance            # Only Core Web Vitals static signals
/seo-validate --scope geo                    # Only GEO (Generative Engine Optimization)
/seo-validate --scope topical               # Only topical authority and cluster architecture
/seo-validate --severity high                # Filter to HIGH findings only
/seo-validate --framework next               # Force framework (skip auto-detection)
/seo-validate --rendering csr                # Force rendering-mode interpretation
/seo-validate --output json                  # Structured JSON output for CI integration
```

**Scopes:**
- `full` (default) — all 10 categories
- `technical` — HTML semantics, hreflang, CWV, rendering, technical SEO (categories 1, 4, 5, 7, 8)
- `content` — meta/OG, structured data, GEO, a11y-for-SEO (categories 2, 3, 6, 9)
- `performance` — only CWV static signals (category 5)
- `geo` — only GEO / citability checks (category 6)
- `rendering` — only category 7 (SPA/CSR/SSG crawlability) — useful for migration audits
- `topical` — only topical authority and cluster architecture (category 10)

**Severity filtering:** `--severity high` shows only HIGH, `--severity warn` shows HIGH+WARN, `--severity info` shows all. Default: all.

## What This Command Does

1. **Detect framework and rendering mode** from `package.json`, config files, and entry HTML.
2. **Run the scanner script** for a deterministic baseline over 8 of the 10 categories.
3. **Extend the scan by hand** using `Grep`/`Glob`/`Read` against framework-aware patterns for everything the script does not cover.
4. **Interpret findings** with specific fix suggestions tied to the detected framework.
5. **Report** findings with file paths, line numbers, severity, confidence, and standards citations.

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

### Step 2: Run the Scanner Script

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/seo-scanner.py [path] [--output json|text]
```

Deterministic checks over meta tags, heading order, image `alt`, JSON-LD, hreflang,
`robots.txt`, sitemap, Core Web Vitals signals and `llms.txt`. No framework
awareness — it reads files, not build config. Categories 7 and 10 are not touched.

### Step 3: Extend the Scan by Hand

Read [reference/scanner-categories.md](reference/scanner-categories.md) in full,
then work every category in `--scope` with `Grep` (regex across files) and `Read`
(config parsing / ordered checks), skipping only what Step 2 already reported.
Patterns are framework-aware — use the framework detected in Step 1 to select the
right rule set.

Categories 7 (Rendering Mode & Crawlability) and 10 (Topical Authority) get no help
from the script. Run them in full or say in the report that you did not.

### Step 4: Interpret and Enrich

For each finding:

1. **Read the flagged file/lines** to confirm the match is real (not a comment, not a type-only reference).
2. **Add a specific fix** tied to the framework (e.g., "use `next/image` with `priority` prop" vs. "add `<link rel="preload" as="image">` to `<head>`").
3. **Mark confidence**: `definitive` for regex matches against known-bad patterns, `heuristic` for co-occurrence / absence checks.
4. **Skip false positives** when context shows the concern is addressed elsewhere (e.g., meta tags set in a layout file the route inherits from).

### Step 5: Report

Present findings sorted by severity (HIGH → WARN → INFO), then by file path.
State which findings came from the script and which from the manual pass, and name
any category you did not complete.

---

## Scanner Reference

`scripts/seo-scanner.py` gives a deterministic baseline over 8 of the 10 categories.
The full pattern tables, per-framework rules and standards citations live in
[reference/scanner-categories.md](reference/scanner-categories.md).

| # | Category | Covered by the script | Manual pass |
|---|----------|----------------------|-------------|
| 1 | HTML Semantics & W3C | heading order | rest of the category |
| 2 | Meta & Open Graph | title, description, OG/Twitter tags | rest of the category |
| 3 | Structured Data / Schema.org | JSON-LD presence and shape | rest of the category |
| 4 | Hreflang & i18n | hreflang pairs, x-default | rest of the category |
| 5 | Core Web Vitals (static signals) | LCP/CLS/INP signal patterns | rest of the category |
| 6 | GEO (Generative Engine Optimization) | `llms.txt` presence | rest of the category |
| 7 | Rendering Mode & SPA/CSR/SSG Crawlability | **nothing** | the whole category |
| 8 | Technical SEO | `robots.txt`, sitemap | rest of the category |
| 9 | Accessibility for SEO | image `alt` | rest of the category |
| 10 | Topical Authority & Cluster Architecture | **nothing** | the whole category |

Categories 7 and 10 have no script coverage at all — they are entirely manual, and
skipping them is the most likely way this skill under-reports.

## Output Format

```markdown
## SEO Validation Report

### Summary
| Metric | Value |
|--------|-------|
| Scope | full / technical / content / performance / geo / rendering / topical |
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
- **GEO severity**: Category 6 findings may be WARN (chunk size, author quality, freshness) or INFO (hedging, frameworks, contrast, bio) — see table. Never raise GEO findings to HIGH.
- **SPA HIGH bar**: Only flag Category 7 HIGH when the app is clearly a content site (has public routes with meaningful content). Auth-gated apps (dashboards, admin panels) should stay at WARN/INFO since SEO is not a concern.
- **Noscript is not a substitute for SSR/SSG**: `<noscript>` catches only the "no-JS" case, not the "crawler without JS execution" case — don't upgrade a CSR HIGH to WARN just because noscript exists.
- **No auto-fix in v1**: Fixing SEO issues requires design/content decisions beyond pattern matching.

## Gotchas

- `scripts/seo-scanner.py` reads **files, not build output**. A Next.js `metadata` export, a `useHead()` call, or a `<svelte:head>` block produces correct tags at runtime that the scanner cannot see, so "missing meta description" on a framework project is a claim about the source, not about the page.
- Categories **7 (Rendering & Crawlability)** and **10 (Topical Authority)** get zero script coverage. They are also the two that most often carry the real problem, because a CSR-only app can pass every other category while being invisible to crawlers. Skipping Step 3 for these silently converts the worst finding into no finding.
- `robots.txt` and `sitemap.xml` are checked **at the project root**. Frameworks that generate them at build time (`next-sitemap`, `@astrojs/sitemap`, `gatsby-plugin-sitemap`) leave nothing on disk, so absence is not evidence — check the config and the plugin list before reporting it.
- Hreflang correctness needs **both directions**. A page declaring `hreflang="de"` is only valid if the German page declares the reverse; a one-file scan sees half the pair and cannot conclude.
- Core Web Vitals here are **static signals only** — missing `width`/`height`, unbounded images, render-blocking patterns. Real LCP/CLS/INP come from field data (CrUX, RUM). Reporting a passing CWV category is out of this skill's reach.
- Category 6 (GEO) is genuinely young. Its "signals" track how generative engines behaved recently, not a ratified standard, so its findings stay WARN/INFO by rule — raising one to HIGH asserts more certainty than the field supports.

## When NOT to Use

- On an auth-gated app — dashboards and admin panels have no crawler audience, and every category-7 finding will be noise.
- To measure Core Web Vitals — use PageSpeed Insights, CrUX, or your RUM; this skill sees source patterns, not field metrics.
- To verify tags a framework generates at build time — build the site and scan the output, or read the framework config instead.
- For accessibility beyond the SEO overlap — use `/a11y-validate`; category 9 here is deliberately shallow.
- To rewrite content for topical authority — this skill is read-only and reports gaps; the writing is a separate job.

## Reference Documents

- [reference/w3c-guidelines.md](reference/w3c-guidelines.md) — HTML5 semantic requirements, meta tag specs, language tag rules.
- [reference/core-web-vitals.md](reference/core-web-vitals.md) — LCP/INP/CLS thresholds, resource hints, above-the-fold heuristic, per-framework image components.
- [reference/geo-guidelines.md](reference/geo-guidelines.md) — GEO principles, `speakable` schema, citation/source markup, AI-extractable content structure, chunk anatomy, 13-week freshness strategy.
- [reference/geo-aeo-patterns.md](reference/geo-aeo-patterns.md) — AEO (Answer Engine Optimization): `FAQPage`/`HowTo`/`QAPage` schema, `llms.txt`, AI bot `robots.txt` directives, E-E-A-T signals, automated grep patterns for Category 6.
- [reference/content-citability.md](reference/content-citability.md) — Chunk architecture, semantic triples, opinionated vs hedging language, decision frameworks, contrast patterns, negative definitions, justified superlatives, grep patterns.
- [reference/ai-pipeline.md](reference/ai-pipeline.md) — Google's 4-stage AI pipeline (Prepare/Retrieve/Signal/Serve), 7 ranking signals (Gecko, Jetstream, PCTR, Freshness, BM25, Base, Boost/Bury), Query Fan Out, probabilistic ranking, format routing.
- [reference/schema-types.md](reference/schema-types.md) — Schema.org JSON-LD templates (Article, FAQ, BreadcrumbList, Organization, Product, LocalBusiness) with required properties.
- [reference/spa-ssg-patterns.md](reference/spa-ssg-patterns.md) — Rendering-mode decision tree, SPA pitfalls, per-framework detection patterns, prerendering strategies.
