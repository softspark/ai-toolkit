# Core Web Vitals Reference

Reference for `seo-validate` Category 5. Static-analysis patterns that cause LCP/INP/CLS regressions, plus resource hint guidance and above-the-fold heuristics.

Source: web.dev Core Web Vitals, HTML Living Standard `<link>` rel types, W3C Resource Hints, per-framework image component documentation.

## Thresholds

| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| LCP (Largest Contentful Paint) | <2.5s | 2.5–4.0s | >4.0s |
| INP (Interaction to Next Paint) | <200ms | 200–500ms | >500ms |
| CLS (Cumulative Layout Shift) | <0.1 | 0.1–0.25 | >0.25 |

75th-percentile mobile values count for ranking. The skill can't measure these at runtime — it flags code patterns known to cause regressions.

---

## LCP (Largest Contentful Paint)

The LCP element is typically the hero image or H1 text in the first viewport. Goal: render it as fast as possible.

### Image dimensions

Every `<img>` and `<video>` must declare `width` and `height` (or `aspect-ratio` CSS). Missing dimensions cause:
- CLS as the image loads.
- LCP delay (browser can't reserve space / estimate priority).

```html
<!-- Good -->
<img src="hero.jpg" width="1200" height="630" alt="...">

<!-- Bad (CLS + LCP) -->
<img src="hero.jpg" alt="...">
```

### fetchpriority

`fetchpriority="high"` on the LCP image tells the browser to fetch it before other resources. Introduced in Chrome 101 (May 2022).

```html
<img src="hero.jpg" width="1200" height="630" fetchpriority="high" alt="...">
```

`fetchpriority="low"` on below-the-fold images frees bandwidth for critical resources.

### loading="lazy" on LCP = BAD

`loading="lazy"` delays the image load until it's near the viewport. Applied to the LCP element, this is a HIGH-severity anti-pattern.

Only apply `loading="lazy"` to images **below the fold**.

```html
<!-- Bad: LCP element marked lazy -->
<img src="hero.jpg" loading="lazy" alt="Hero">

<!-- Good: LCP element eager + high priority -->
<img src="hero.jpg" fetchpriority="high" alt="Hero">

<!-- Good: below-the-fold image lazy -->
<img src="testimonial.jpg" loading="lazy" decoding="async" alt="Jane, happy customer">
```

### decoding="async"

Signals that image decoding can happen off the main thread. Apply to non-critical images.

```html
<img src="sidebar.jpg" loading="lazy" decoding="async" alt="...">
```

Don't apply `decoding="async"` to the LCP image — it can delay paint. Use `decoding="sync"` or omit.

### Preloading the LCP image

When the LCP image URL is known at build time (hero background, article cover), preload it:

```html
<link rel="preload" as="image" href="/images/hero.jpg"
      imagesrcset="/images/hero-640.jpg 640w, /images/hero-1280.jpg 1280w"
      imagesizes="100vw">
```

### Font loading

Fonts frequently gate LCP when text is the LCP element.

```css
/* Good: text renders in fallback, swaps when webfont loads */
@font-face {
  font-family: 'Inter';
  src: url('/fonts/inter.woff2') format('woff2');
  font-display: swap;  /* or 'optional' for aggressive LCP optimization */
}

/* Bad: FOIT (Flash of Invisible Text) blocks paint */
@font-face {
  font-family: 'Inter';
  src: url('/fonts/inter.woff2') format('woff2');
  /* font-display defaults to 'auto', which most browsers treat as 'block' = FOIT */
}
```

Preload webfonts used above the fold:

```html
<link rel="preload" as="font" type="font/woff2"
      href="/fonts/inter-var.woff2" crossorigin>
```

The `crossorigin` attribute is required even for same-origin fonts — fonts are always fetched with CORS.

### Responsive images

Images wider than ~600px should use `srcset` + `sizes` or `<picture>`:

```html
<img
  src="hero-1280.jpg"
  srcset="hero-640.jpg 640w, hero-1280.jpg 1280w, hero-2560.jpg 2560w"
  sizes="(max-width: 768px) 100vw, 50vw"
  width="1280" height="720" alt="...">
```

Over-fetching a 2560px image to a 375px mobile viewport wastes bytes and delays LCP.

---

## INP (Interaction to Next Paint)

Replaces FID (First Input Delay) as the CWV interaction metric in March 2024. Measures longest interaction latency across the session.

### Render-blocking scripts

Scripts in `<head>` without `async` or `defer` block parsing:

```html
<!-- Bad: blocks parser + CSSOM -->
<script src="/analytics.js"></script>

<!-- Good: doesn't block parser, runs after parse but before DOMContentLoaded -->
<script defer src="/app.js"></script>

<!-- Good: downloads in parallel, runs ASAP (order not guaranteed) -->
<script async src="/analytics.js"></script>
```

### Third-party scripts

Analytics, chat widgets, ads, A/B test SDKs commonly cause INP regressions.

Patterns to flag:
- `<script src="https://www.googletagmanager.com/...">` without `async`
- Intercom, Drift, HubSpot widgets loaded synchronously
- Ads via direct `<script>` (most use `async` by default, verify)

Next.js `<Script>` component with strategy:
```jsx
<Script src="https://analytics.example.com" strategy="lazyOnload" />
```

Strategies:
- `beforeInteractive` — blocks hydration, rarely needed.
- `afterInteractive` (default) — loads after hydration.
- `lazyOnload` — loads during idle time. Best for analytics/chat.
- `worker` — runs in Web Worker (Partytown). Experimental.

### document.write

Always HIGH. Modern browsers disable `document.write` for scripts loaded over 2G-like networks. Never use.

### Hydration cost

Heavy synchronous work during hydration blocks INP. Red flags:

```jsx
useEffect(() => {
  // Large sync block — splits Long Tasks
  heavyComputation();
  anotherHeavyFunction();
  yetAnotherOne();
}, []);
```

Mitigation: `requestIdleCallback`, `scheduler.postTask`, or split across effects.

### Bundle size

Bundles >300KB gzipped gating interaction = INP risk. Check:
- Imports of entire lodash / moment / date-fns (use tree-shaking or day.js)
- Icon libraries imported wholesale (import only what's used)
- PDF/charting libraries loaded eagerly (dynamic import)

---

## CLS (Cumulative Layout Shift)

### Image/video/iframe dimensions

Covered above — always set `width`/`height` or `aspect-ratio`.

### Iframes

YouTube embeds, maps, Twitter embeds cause CLS without reserved space:

```html
<!-- Bad -->
<iframe src="https://www.youtube.com/embed/..."></iframe>

<!-- Good: fixed container -->
<div style="aspect-ratio: 16/9;">
  <iframe src="..." width="100%" height="100%"></iframe>
</div>
```

### Dynamic content

Ads, embeds, and "related content" widgets injected after paint cause CLS. Reserve space with CSS:

```css
.ad-slot {
  min-height: 250px;  /* Or aspect-ratio tied to ad size */
}
```

### Font swap shifts

`font-display: swap` causes a visible shift when the webfont loads (FOUT — Flash of Unstyled Text). Minimize by:
- Using system-ui fonts as fallback with matching metrics (`size-adjust`, `ascent-override`).
- Using `font-display: optional` (accepts missing-font in exchange for zero shift).

### Hydration mismatches

Server renders one thing, client renders another — content "flashes" or "jumps":

```jsx
// Bad — hydration mismatch potential
function Component() {
  if (typeof window !== 'undefined') {
    return <ClientOnlyContent />;
  }
  return <ServerContent />;
}

// Good — use useEffect with loading state
function Component() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted ? <ClientOnlyContent /> : <Skeleton />;
}
```

---

## Resource Hints

HTML Living Standard + W3C Resource Hints. Hints are suggestions — browsers can ignore them.

### preload

High-priority fetch for critical, known resources.

```html
<link rel="preload" as="image" href="/hero.jpg">
<link rel="preload" as="font" type="font/woff2" href="/fonts/inter.woff2" crossorigin>
<link rel="preload" as="style" href="/critical.css">
<link rel="preload" as="script" href="/critical.js">
```

Rules:
- Must include `as` attribute matching the resource type.
- Must appear BEFORE the resource uses it in document order.
- Don't over-use — >6 preloads starts to hurt.
- Preloaded resource not used within a few seconds → browser console warning.

### prefetch

Low-priority fetch for probable-next-navigation resources.

```html
<link rel="prefetch" href="/next-page.js">
```

Framework-integrated prefetching:
- Next.js `<Link>` auto-prefetches visible links in production.
- Nuxt `<NuxtLink>` with `prefetch` prop.
- SvelteKit: `data-sveltekit-preload-data="hover"` or `"tap"`.
- Remix: `<Link prefetch="intent">`.

### preconnect

Establishes early connection (DNS + TCP + TLS) to a 3rd-party origin.

```html
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://www.google-analytics.com">
```

Use for critical 3rd-party origins: font hosts, CDNs, analytics. Overuse contends with critical-path connections — limit to 3–4.

### dns-prefetch

Lightweight DNS-only resolution. Use for less-critical origins or as fallback for browsers without preconnect support.

```html
<link rel="dns-prefetch" href="https://some-analytics.example.com">
```

### modulepreload

Preload ESM modules on the critical path (bypasses discovery cost for import graphs).

```html
<link rel="modulepreload" href="/build/chunk-main.js">
```

Build tools can generate these automatically (Vite, esbuild, Rollup plugins).

### Ordering

Preload/preconnect MUST appear before the resource that uses them — typically at the top of `<head>`, right after charset/viewport.

```html
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="...">

  <!-- Resource hints first -->
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="preload" as="image" href="/hero.jpg" fetchpriority="high">
  <link rel="preload" as="font" type="font/woff2" href="/fonts/inter.woff2" crossorigin>

  <!-- Then the resource (stylesheets) -->
  <link rel="stylesheet" href="/styles.css">

  <!-- Metadata -->
  <title>...</title>
  <meta name="description" content="...">
</head>
```

### Anti-patterns

- Preloading non-critical resources (every icon, every font weight).
- Preload without `as` attribute — browser issues warning, may not prioritize.
- Multiple `preload`s for images that aren't the LCP element.
- Preload after stylesheets/scripts that already request the resource.

---

## Above-the-Fold Heuristics

True "above-the-fold" detection requires rendering. In static analysis, treat these as ATF candidates:

1. **First `<img>` / `<Image>` / `<NuxtImg>` / `<GatsbyImage>` / `<Image from 'astro:assets'>`** in a route/page component.
2. **First child of `<main>`**, `<section>`, or `<header>`.
3. **Components named** `Hero`, `HeroSection`, `Banner`, `Masthead`, `Jumbotron`, `CoverImage`, `SplashImage`, `HeaderImage`.
4. **`<Image>` with `priority` prop** (Next.js) — developer has already declared ATF intent.

For ATF elements, required:
- `width` + `height` declared.
- `fetchpriority="high"` (or framework `priority` equivalent).
- NO `loading="lazy"`.
- Matching `<link rel="preload">` if URL known at build.

For below-the-fold images, recommended:
- `loading="lazy"`.
- `decoding="async"`.
- `fetchpriority="low"` (optional).

---

## Framework-Specific Image Components

### Next.js — `next/image`

```jsx
import Image from 'next/image';

// LCP image
<Image src="/hero.jpg" alt="..." width={1200} height={630} priority />

// Below fold
<Image src="/thumb.jpg" alt="..." width={400} height={300} loading="lazy" />
```

Benefits: automatic WebP/AVIF, responsive srcset, lazy by default, supports `fill` + `sizes`.

Flags:
- `<img>` used instead of `<Image>` in route components → WARN (unless explicit raw HTML is needed).
- `<Image>` without `priority` on LCP element → HIGH.
- `<Image>` without `sizes` when using `fill` → WARN.

### Nuxt — `<NuxtImg>` / `<NuxtPicture>`

```vue
<NuxtImg src="/hero.jpg" width="1200" height="630" preload />
<NuxtImg src="/thumb.jpg" width="400" height="300" loading="lazy" />
```

Requires `@nuxt/image` module.

### Astro — `<Image>` from `astro:assets`

```astro
---
import { Image } from 'astro:assets';
import hero from '../assets/hero.jpg';
---
<Image src={hero} alt="..." width={1200} height={630} loading="eager" />
```

### Gatsby — `GatsbyImage`

```jsx
import { GatsbyImage, getImage } from 'gatsby-plugin-image';

const image = getImage(data.file);
<GatsbyImage image={image} alt="..." loading="eager" />
```

### SvelteKit — `@sveltejs/enhanced-img`

```svelte
<script>
  import heroImg from '$lib/images/hero.jpg?enhanced';
</script>
<enhanced:img src={heroImg} alt="..." />
```

---

## References

- web.dev LCP: https://web.dev/lcp/
- web.dev INP: https://web.dev/inp/
- web.dev CLS: https://web.dev/cls/
- Resource Hints: https://www.w3.org/TR/resource-hints/
- HTML Living Standard `<link>` rel: https://html.spec.whatwg.org/multipage/links.html#linkTypes
- fetchpriority: https://web.dev/fetch-priority/
- font-display: https://developer.mozilla.org/en-US/docs/Web/CSS/@font-face/font-display
- Next.js Image: https://nextjs.org/docs/app/api-reference/components/image
- Nuxt Image: https://image.nuxt.com/
- Astro Image: https://docs.astro.build/en/guides/images/
- Gatsby Image: https://www.gatsbyjs.com/docs/reference/built-in-components/gatsby-plugin-image/
