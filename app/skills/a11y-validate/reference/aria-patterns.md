# ARIA 1.2 Authoring Patterns Reference

Reference for `a11y-validate` Category 7. ARIA roles, states, properties, common anti-patterns, and framework-specific helpers.

Source: WAI-ARIA 1.2 W3C Recommendation (June 2023), ARIA Authoring Practices Guide (APG).

## First Rule of ARIA

**Don't use ARIA if native HTML does the job.** Every `role="button"` on a `<div>` is a sign of a missing `<button>`. Native elements come with keyboard handling, focus management, accessibility-tree exposure, and OS-level AT integration for free.

ARIA is for:
- Widgets native HTML doesn't provide (tablist, tree, combobox with rich popup).
- Dynamic states (`aria-expanded`, `aria-busy`, `aria-invalid`).
- Supplementing native semantics (`aria-label`, `aria-describedby`).
- Live regions for async updates (`aria-live`, `role="status"`).

## Landmark Roles

Semantic HTML5 elements have implicit landmark roles — use them first:

| HTML | Implicit role | Usage |
|------|--------------|-------|
| `<header>` | `banner` (when top-level child of body) | Site header |
| `<nav>` | `navigation` | Navigation regions |
| `<main>` | `main` | Primary content (exactly one per page) |
| `<aside>` | `complementary` | Sidebar, related content |
| `<footer>` | `contentinfo` (when top-level child of body) | Site footer |
| `<section>` with `aria-label` | `region` | Named section |
| `<form>` with `aria-label` | `form` | Named form region |
| `<search>` (HTML 2024) | `search` | Search region |

For pre-HTML5 codebases: `<div role="banner">`, `<div role="navigation">`, `<div role="main">`, etc. Flag these as UPGRADE opportunities.

## Widget Roles

| Role | Requires | Notes |
|------|---------|-------|
| `button` | Keyboard activation (Enter + Space), focus | Prefer `<button>` |
| `checkbox` | `aria-checked`, keyboard activation | Prefer `<input type="checkbox">` |
| `radio` + `radiogroup` | `aria-checked`, arrow-key navigation | Prefer `<input type="radio">` |
| `combobox` | `aria-expanded`, `aria-controls`, `aria-activedescendant`, arrow keys | Rich autocomplete; no native equivalent |
| `listbox` + `option` | `aria-selected`, arrow keys | Prefer `<select>` for simple cases |
| `menu` + `menuitem` | Arrow keys, Escape, focus trap | Application menus; NOT nav links |
| `tab` + `tablist` + `tabpanel` | `aria-selected`, `aria-controls`, arrow keys | Tabs |
| `tree` + `treeitem` | Arrow keys, `aria-expanded`, `aria-level` | File tree, org tree |
| `grid` + `gridcell` + `row` | Arrow keys | Interactive data grid |
| `dialog` / `alertdialog` | `aria-modal="true"`, focus trap, Escape | Prefer `<dialog>` (HTML5) |
| `tooltip` | Hovered/focused trigger | Not focusable itself |
| `progressbar` | `aria-valuenow`, `aria-valuemin`, `aria-valuemax` | Prefer `<progress>` |
| `slider` | `aria-valuenow`, arrow keys | Prefer `<input type="range">` |
| `switch` | `aria-checked` | Toggle (no native equivalent) |

## States and Properties

### Widget states (dynamic)

- `aria-checked` — checkbox/radio/switch state
- `aria-selected` — option/tab/cell selected
- `aria-expanded` — disclosure/combobox open
- `aria-pressed` — toggle button pressed
- `aria-disabled` — disabled (prefer native `disabled` where possible)
- `aria-hidden` — removed from AT tree (DO NOT use on focusable elements)
- `aria-invalid` — form input invalid
- `aria-busy` — content loading
- `aria-current` — current item in a set (page, step, date, location, time, true)

### Widget properties (static)

- `aria-label` — accessible name (overrides visible text)
- `aria-labelledby` — accessible name from other element(s) by ID
- `aria-describedby` — accessible description by ID
- `aria-controls` — element controlled by this (e.g., tab → tabpanel)
- `aria-owns` — parent/child in accessibility tree (rarely needed)
- `aria-haspopup` — indicates popup type: menu / listbox / tree / grid / dialog
- `aria-level` — heading/tree depth (integer)
- `aria-setsize` / `aria-posinset` — position in a set

### Live region properties

- `aria-live` — polite / assertive / off
- `aria-atomic` — read whole region or just changes
- `aria-relevant` — additions / removals / text / all (limited browser support)

Roles with implicit `aria-live`:
- `role="alert"` — `aria-live="assertive"` + `aria-atomic="true"`
- `role="status"` — `aria-live="polite"` + `aria-atomic="true"`
- `role="log"` — `aria-live="polite"`
- `role="timer"` — `aria-live="off"` (implicit)
- `role="marquee"` — `aria-live="off"` (implicit)

## Common Anti-Patterns (flagged by Category 7)

### 1. Redundant ARIA

```html
<!-- Bad: role duplicates native semantics -->
<button role="button">Submit</button>
<a href="/x" role="link">Link</a>
<h1 role="heading" aria-level="1">Title</h1>
<nav role="navigation">...</nav>
<main role="main">...</main>

<!-- Good -->
<button>Submit</button>
<a href="/x">Link</a>
<h1>Title</h1>
<nav>...</nav>
<main>...</main>
```

### 2. Conflicting roles

```html
<!-- Bad -->
<button role="link">Go to page</button>
<a role="button" href="javascript:void(0)" onclick="...">Click</a>

<!-- Good — match role to behavior -->
<a href="/x">Go to page</a>
<button onclick="...">Click</button>
```

### 3. `aria-hidden` on focusable element

```html
<!-- Bad — keyboard user tabs into invisible content -->
<button aria-hidden="true">Skip</button>

<!-- Good — use inert (HTML 2024) or remove from DOM -->
<div inert>
  <button>Skip</button>
</div>
```

### 4. `tabindex="-1"` on native interactive

```html
<!-- Bad — removes from tab order for no reason -->
<button tabindex="-1">Submit</button>

<!-- Good: only use tabindex=-1 on elements you focus programmatically (modal root, error summary) -->
<div role="dialog" tabindex="-1" aria-modal="true" ref={modalRef}>
  ...
</div>
```

### 5. Missing `aria-label` for icon buttons

```html
<!-- Bad — screen reader announces "button" with no name -->
<button><svg aria-hidden="true"><!-- icon --></svg></button>

<!-- Good -->
<button aria-label="Close dialog"><svg aria-hidden="true">...</svg></button>
```

### 6. Broken `aria-labelledby` / `aria-describedby` references

```html
<!-- Bad — no element with id="hint" exists -->
<input aria-describedby="hint">

<!-- Good -->
<input aria-describedby="email-hint">
<span id="email-hint">We'll never share your email.</span>
```

### 7. `role="presentation"` on interactive

```html
<!-- Bad — strips button semantics -->
<button role="presentation">Submit</button>

<!-- Good — role=presentation only on purely visual containers -->
<div role="presentation">
  <img src="decorative.jpg" alt="">
</div>
```

## WAI-ARIA Authoring Practices Guide (APG) Widgets

The APG provides ready-made keyboard and ARIA patterns for common widgets:

- **Accordion**: https://www.w3.org/WAI/ARIA/apg/patterns/accordion/
- **Alert**: https://www.w3.org/WAI/ARIA/apg/patterns/alert/
- **Alert and Message Dialogs**: https://www.w3.org/WAI/ARIA/apg/patterns/alertdialog/
- **Breadcrumb**: https://www.w3.org/WAI/ARIA/apg/patterns/breadcrumb/
- **Button**: https://www.w3.org/WAI/ARIA/apg/patterns/button/
- **Carousel**: https://www.w3.org/WAI/ARIA/apg/patterns/carousel/
- **Checkbox**: https://www.w3.org/WAI/ARIA/apg/patterns/checkbox/
- **Combobox**: https://www.w3.org/WAI/ARIA/apg/patterns/combobox/
- **Dialog (modal)**: https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/
- **Disclosure (Show/Hide)**: https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/
- **Feed**: https://www.w3.org/WAI/ARIA/apg/patterns/feed/
- **Grid**: https://www.w3.org/WAI/ARIA/apg/patterns/grid/
- **Landmarks**: https://www.w3.org/WAI/ARIA/apg/patterns/landmarks/
- **Link**: https://www.w3.org/WAI/ARIA/apg/patterns/link/
- **Listbox**: https://www.w3.org/WAI/ARIA/apg/patterns/listbox/
- **Menu / Menubar**: https://www.w3.org/WAI/ARIA/apg/patterns/menubar/
- **Menu Button**: https://www.w3.org/WAI/ARIA/apg/patterns/menubutton/
- **Radio Group**: https://www.w3.org/WAI/ARIA/apg/patterns/radio/
- **Slider**: https://www.w3.org/WAI/ARIA/apg/patterns/slider/
- **Slider (Multi-thumb)**: https://www.w3.org/WAI/ARIA/apg/patterns/slider-multithumb/
- **Spinbutton**: https://www.w3.org/WAI/ARIA/apg/patterns/spinbutton/
- **Switch**: https://www.w3.org/WAI/ARIA/apg/patterns/switch/
- **Tabs**: https://www.w3.org/WAI/ARIA/apg/patterns/tabs/
- **Toolbar**: https://www.w3.org/WAI/ARIA/apg/patterns/toolbar/
- **Tooltip**: https://www.w3.org/WAI/ARIA/apg/patterns/tooltip/
- **Tree View**: https://www.w3.org/WAI/ARIA/apg/patterns/treeview/
- **Treegrid**: https://www.w3.org/WAI/ARIA/apg/patterns/treegrid/
- **Window Splitter**: https://www.w3.org/WAI/ARIA/apg/patterns/windowsplitter/

## Framework-Specific A11y Helpers

Use these libraries instead of hand-rolling ARIA:

### React

- **React Aria** (Adobe): https://react-spectrum.adobe.com/react-aria/ — unstyled hooks with correct ARIA + keyboard.
- **Radix UI**: https://www.radix-ui.com/ — primitives with built-in a11y.
- **Reach UI** (deprecated but functional): https://reach.tech/
- **Headless UI** (Tailwind): https://headlessui.com/
- **ARIA Kit**: https://ariakit.org/
- `eslint-plugin-jsx-a11y` — lint a11y violations in JSX.

### Angular

- **Angular CDK a11y**: https://material.angular.io/cdk/a11y/ — `FocusTrap`, `LiveAnnouncer`, `FocusMonitor`, `ListKeyManager`.
- `@angular-eslint/eslint-plugin-template` — includes a11y rules.

### Vue

- **@headlessui/vue** — same as React version.
- **Vue a11y plugins**: `vue-accessibility`, `vuelidate-a11y`.
- `eslint-plugin-vuejs-accessibility`.

### Svelte / SvelteKit

- Svelte has **built-in a11y warnings** in `.svelte` templates (`a11y-missing-attribute`, etc.).
- `eslint-plugin-svelte` with `--rules 'svelte/a11y-*'`.

### Astro

- `@astrojs/check` — type + a11y checks for `.astro` files.

### Mobile

- **React Native**: `AccessibilityInfo` API, `accessibilityLabel`, `accessibilityRole`, `accessibilityState` props.
- **Flutter**: `Semantics()` widget, `MergeSemantics`, `ExcludeSemantics`, `semanticLabel` on most widgets.

See [mobile-eaa.md](mobile-eaa.md) for mobile-specific patterns.

## References

- WAI-ARIA 1.2 (W3C Recommendation): https://www.w3.org/TR/wai-aria-1.2/
- ARIA Authoring Practices Guide: https://www.w3.org/WAI/ARIA/apg/
- ARIA in HTML (how ARIA interacts with HTML): https://www.w3.org/TR/html-aria/
- Using ARIA (W3C): https://www.w3.org/TR/using-aria/
- MDN ARIA reference: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA
