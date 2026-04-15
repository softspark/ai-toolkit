# SPA / SSR / SSG / CSR / ISR Patterns

Reference for `seo-validate` Category 7. How to detect rendering mode, identify SPA pitfalls, and flag crawlability issues per framework.

## Rendering Mode Decision Tree

```
Is content server-rendered before the client gets it?
├── YES (server returns meaningful HTML)
│   ├── At request time?   → SSR (Server-Side Rendering)
│   ├── At build time?     → SSG (Static Site Generation)
│   └── Cached + revalidated periodically? → ISR (Incremental Static Regeneration)
└── NO (server returns a shell; client renders)
    └── CSR (Client-Side Rendering) / SPA — CRAWLABILITY RISK
```

For SEO:
- **SSG / SSR / ISR**: safe — crawlers see content immediately.
- **CSR / SPA**: risky — most crawlers see an empty shell.
- **Hybrid** (SSR/SSG for public routes, CSR for dashboards): check each route type.

---

## Why CSR SPAs Fail SEO

Modern crawlers (Googlebot) can execute JS, but:

1. **Other engines lag**: Bing, DuckDuckGo, Yandex, Baidu have limited/no JS execution.
2. **LLM answer engines** (ChatGPT, Perplexity, Bing Copilot) typically ingest raw HTML — they don't wait for hydration.
3. **Social scrapers** (Facebook, LinkedIn, Slack, Twitter/X) don't execute JS — OG tags in `<head>` must be present at initial response, not injected by React.
4. **Googlebot delays JS rendering** — two-wave indexing can delay discovery by days/weeks.
5. **Hash routes (`/#/about`)** are fragments — not indexed as separate URLs.
6. **Unique per-route meta is impossible without SSR/SSG/prerender** — the static `index.html` has the same `<title>` and `<meta description>` for every route.

**Bottom line**: a CSR-only SPA with public marketing content is effectively invisible to half the SEO ecosystem. This is a HIGH-severity finding.

---

## Framework Detection Patterns

### Next.js

Detection: `next` in `package.json` deps.

Config: `next.config.js` / `next.config.mjs` / `next.config.ts`.

Rendering per route (App Router, Next.js 13+):
- Static by default (SSG).
- `export const dynamic = 'force-dynamic'` → SSR.
- `export const revalidate = 60` → ISR.
- `'use client'` at top of component → component runs client-side, but page can still be SSR/SSG.
- `dynamic(() => import(...), { ssr: false })` → that specific component is CSR only.

Flags:
- `next.config.*` with `output: 'export'` → forced SSG. Dynamic features (API routes, ISR, middleware) won't work.
- Page file with `'use client'` at top: page still pre-renders but becomes a client component boundary.
- `dynamic(..., { ssr: false })` wrapping LCP element → HIGH severity.

Per-route metadata:
- App Router: `export const metadata = { ... }` or `export async function generateMetadata() { ... }`.
- Pages Router: `<Head>` from `next/head`.

### Nuxt

Detection: `nuxt` in `package.json` deps.

Config: `nuxt.config.ts`.

Rendering:
- Default: SSR.
- `ssr: false` → SPA mode (dangerous for SEO).
- `nitro.prerender.routes: [...]` → SSG routes.
- `nuxt generate` command → full SSG export.

Per-route metadata:
- `useHead({ title: ..., meta: [...] })` composable.
- `definePageMeta({ ... })`.

### Astro

Detection: `astro` in `package.json` deps.

Config: `astro.config.mjs`.

Rendering:
- `output: 'static'` (default) → SSG.
- `output: 'server'` → SSR (with adapter like `@astrojs/node`, `@astrojs/vercel`).
- `output: 'hybrid'` → mostly static, opt-in SSR per page.

Component-level:
- `client:load` / `client:idle` / `client:visible` → islands hydrate on client, but initial HTML is rendered.
- `client:only="react"` → component is CSR only. Flag when on hero/above-the-fold content.

Per-page metadata: direct `<meta>` tags in layout or frontmatter.

### Gatsby

Detection: `gatsby` in `package.json` deps.

Config: `gatsby-config.js`.

Rendering: SSG by default. `gatsby build` creates static HTML per page.

Modern Gatsby (4+) supports SSR (`getServerData`) and DSG (Deferred Static Generation).

Per-page metadata:
- `react-helmet` or `gatsby-plugin-react-helmet`.
- Gatsby Head API: `export const Head = () => (<><title>...</title></>)`.

### SvelteKit

Detection: `@sveltejs/kit` in `package.json` deps.

Config: `svelte.config.js`.

Rendering per route:
- `export const ssr = true` (default) — SSR.
- `export const ssr = false` — CSR only.
- `export const prerender = true` — SSG for that route.
- `export const prerender = 'auto'` — prerender unless dynamic data.

Adapter determines deployment:
- `@sveltejs/adapter-static` → pure SSG.
- `@sveltejs/adapter-node` → Node server, SSR.
- `@sveltejs/adapter-vercel` / `@sveltejs/adapter-cloudflare` → serverless.

Per-route metadata: `<svelte:head>` block.

### Remix

Detection: `@remix-run/*` in `package.json` deps.

Rendering: SSR by default. Loader functions run server-side, deliver HTML.

Per-route metadata: `export const meta: MetaFunction = () => [...]`.

No built-in SSG — always SSR.

### Angular

Detection: `@angular/core` in `package.json` deps.

Rendering:
- Default: CSR only → HIGH-severity for content sites.
- With `@angular/ssr` (Angular 17+) or `@nguniversal/*` (older): SSR.

Check `angular.json` for `ssr` builder config.

Per-page metadata: inject `Meta` and `Title` services from `@angular/platform-browser`.

### Vue (non-Nuxt SPA)

Detection: `vue` in deps without `nuxt`.

Rendering: CSR unless using:
- Vite SSR (`vite-plugin-ssr` → now `vike`).
- Vue Storefront or similar custom SSR.
- `@vue/server-renderer` explicitly.

Default Vue SPA from `create-vue` / `@vue/cli` is CSR-only → HIGH severity for content sites.

### React SPA (Vite)

Detection: `react` + `vite` in deps, no `next`, no `@remix-run/*`.

Rendering: CSR only unless:
- `vike` (formerly vite-plugin-ssr) → SSR.
- `vite-plugin-prerender` / `@preact/preset-vite` with prerender option → build-time prerender.
- `@tanstack/router` with SSR plugin.

Default Vite + React is CSR → HIGH severity for content sites.

### Create React App (CRA)

Detection: `react-scripts` in deps.

Rendering: CSR only.

Mitigations (rare — CRA is deprecated):
- `react-snap` plugin → build-time prerender crawl.

Default CRA is CSR → HIGH severity. Also: recommend migrating to Next.js / Remix / Vite+Vike.

---

## Detection Signals

### Entry HTML inspection

Read `public/index.html`, `index.html`, `src/app.html`, or framework entry:

**Empty mount point (SPA signal)**:
```html
<body>
  <div id="root"></div>
  <script src="/main.js"></script>
</body>
```

**Prerendered content (SSG/SSR signal)**:
```html
<body>
  <div id="root">
    <main>
      <h1>Actual content here</h1>
      ...
    </main>
  </div>
  <script src="/main.js"></script>
</body>
```

Rule of thumb: if `<div id="root">` / `<div id="app">` / `<div id="__next">` contains only whitespace or tiny loader markup, it's a SPA shell — flag.

### Runtime-only meta detection

Look for:
- `react-helmet-async` usage without `HelmetProvider` in SSR server entry.
- `vue-meta` / `@vueuse/head` without SSR plugin.
- Direct `document.title = ...` / `document.querySelector('meta[name=description]').content = ...` writes.

If meta is only set at runtime, it won't be in the initial response → crawlers miss it.

### HashRouter detection

```jsx
// React Router HashRouter
import { HashRouter } from 'react-router-dom';
<HashRouter>...</HashRouter>

// Vue Router hash mode
createRouter({ history: createWebHashHistory(), ... })
```

Hash routes like `/#/about` are fragments — Google does NOT index them as separate URLs.

Always use `BrowserRouter` / `createWebHistory()` for public routes.

### Hydration mismatch signals

```jsx
// Red flag: different output based on environment
function Component() {
  if (typeof window !== 'undefined') {
    return <ClientVariant />;
  }
  return <ServerVariant />;
}

// Red flag: overuse of suppressHydrationWarning
<div suppressHydrationWarning>
  {Math.random()}  {/* Masking a real bug */}
</div>
```

The skill flags `>3` occurrences of `suppressHydrationWarning` in the codebase as a heuristic WARN.

---

## Prerendering Strategies for SPAs

When migration to Next.js / Remix isn't feasible, SPA prerendering is the fallback:

### react-snap (CRA, Vite-React)

Runs a headless browser against the SPA at build time, snapshots the DOM per route, writes static HTML.

```json
// package.json
{
  "scripts": {
    "postbuild": "react-snap"
  },
  "reactSnap": {
    "source": "build",
    "include": ["/", "/about", "/pricing"]
  }
}
```

Works for: static content sites. Breaks on: dynamic/authenticated routes.

### vite-plugin-prerender

Same approach for Vite projects.

### vike (formerly vite-plugin-ssr)

Full SSR for Vite projects. More invasive than prerender plugins but more capable.

### prerender-spa-plugin (Webpack)

Older Webpack-based solution for Vue/React SPAs.

### Dynamic rendering (legacy — Google deprecated)

`prerender.io`, `rendertron`: intercept requests from crawler user agents, serve prerendered HTML.

Google's recommendation as of 2024: use SSR/SSG instead. Dynamic rendering is a fallback, not a solution — detected as INFO severity, not HIGH.

---

## Quick Detection Reference (for seo-validate Category 7)

| Check | Signal | Severity |
|-------|--------|----------|
| `public/index.html` mount div empty | CSR confirmed | HIGH (if content site) |
| `package.json` has `react-scripts` + no `react-snap` | CRA SPA no prerender | HIGH |
| `react` + `vite` + no `vike`/`vite-plugin-ssr`/prerender | Vite SPA no prerender | HIGH |
| `@angular/core` + no `@angular/ssr` + no `@nguniversal/*` | Angular SPA no SSR | HIGH |
| `vue` + no `nuxt` + no SSR plugin | Vue SPA no SSR | HIGH |
| `HashRouter` or `createWebHashHistory` on public route | Hash routing | HIGH |
| `dynamic(..., { ssr: false })` on hero component | LCP blocked + CSR | HIGH |
| `ssr: false` in `nuxt.config` | Nuxt SPA mode | WARN |
| `export const ssr = false` in SvelteKit route | Route is CSR | WARN |
| `client:only` on Astro hero component | Component is CSR | WARN |
| `'use client'` at top of Next.js page with no server-side logic | Forced CSR boundary | WARN |
| `react-helmet-async` without `HelmetProvider` in server entry | Meta only client-side | HIGH |
| `document.title = ...` in component code | Runtime-only title | HIGH |
| `suppressHydrationWarning` ≥4 occurrences | Likely masked mismatch | WARN |
| `prerender.io` / `rendertron` config | Legacy dynamic rendering | INFO |

---

## When to NOT Flag

Not every SPA needs SEO. The skill should NOT flag rendering-mode HIGH for:

- Auth-gated dashboards, admin panels (no public routes to index).
- Internal tools, intranet apps.
- Mobile app backends with no web UI.
- Electron/desktop apps.

Heuristic: if no public routes exist (check `robots.txt`, presence of marketing pages, landing page in a layout), downgrade SPA findings to INFO.

For mixed cases (Next.js app with marketing routes + dashboard routes), flag per-route: marketing routes should be SSG/SSR; dashboard can be CSR-heavy.

---

## References

- Google Search Central on JavaScript SEO: https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- web.dev rendering patterns: https://web.dev/rendering-on-the-web/
- Next.js rendering: https://nextjs.org/docs/app/building-your-application/rendering
- Nuxt rendering: https://nuxt.com/docs/guide/concepts/rendering
- Astro rendering: https://docs.astro.build/en/guides/rendering/
- Gatsby rendering: https://www.gatsbyjs.com/docs/conceptual/rendering-options/
- SvelteKit rendering: https://kit.svelte.dev/docs/page-options
- Angular SSR: https://angular.dev/guide/ssr
- vike (vite-plugin-ssr): https://vike.dev/
- react-snap: https://github.com/stereobooster/react-snap
