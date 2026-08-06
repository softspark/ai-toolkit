# Accessibility Scanner Categories

### Category 1: Semantic Structure & Landmarks

WCAG 1.3.1 (Info and Relationships), 2.4.1 (Bypass Blocks), 2.4.6 (Headings and Labels), 3.1.1 (Language of Page), 3.1.2 (Language of Parts).

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| `<html>` missing `lang` attribute | HIGH | definitive | WCAG 3.1.1 |
| Mixed-language content without `<span lang="...">` wrapper (heuristic: non-Latin characters in otherwise-Latin content) | WARN | heuristic | WCAG 3.1.2 |
| Page/route component with >1 `<h1>` | WARN | heuristic | WCAG 1.3.1 |
| Heading level skip (h1 → h3 without h2) | WARN | heuristic | WCAG 1.3.1 |
| No landmark roles / semantic elements (`<main>`, `<nav>`, `<header>`, `<footer>`) | WARN | heuristic | WCAG 1.3.1, 2.4.1 |
| `role="presentation"` / `role="none"` on semantic element | WARN | definitive | Strips meaning; misuse of ARIA |
| Multiple `<main>` per page | HIGH | definitive | WCAG 1.3.1 — only one `<main>` allowed |

### Category 2: Text Alternatives & Non-Text Content

WCAG 1.1.1 (Non-text Content).

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| `<img>` without `alt` attribute | HIGH | definitive | WCAG 1.1.1 — required even if empty |
| `<img alt="">` on informational image (heuristic: image inside `<article>`, `<figure>`, or with adjacent caption) | WARN | heuristic | Empty alt only for decorative |
| `<img alt="image">` / `<img alt="photo">` / `<img alt="picture">` (redundant/meaningless) | WARN | definitive | Alt should describe content |
| `<svg>` without `<title>` + `role="img"` + `aria-label`, used in interactive context | WARN | heuristic | Inline SVG needs alternative |
| Icon font (`<i class="fa-...">`, `<span class="material-icons">`) without `aria-label` or text alternative | WARN | definitive | WCAG 1.1.1 |
| `<img>` used for text content (heuristic: `alt` contains a full sentence like "Click here to...") | WARN | heuristic | WCAG 1.4.5 Images of Text |
| Complex image (`<img>` with `src` matching `chart|graph|diagram|infographic`) without long description (`aria-describedby` or `longdesc` or linked description) | WARN | heuristic | WCAG 1.1.1 for complex content |

### Category 3: Keyboard & Focus

WCAG 2.1.1 (Keyboard), 2.1.2 (No Keyboard Trap), 2.4.3 (Focus Order), 2.4.7 (Focus Visible).

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| `tabindex` value >0 (positive) | HIGH | definitive | WCAG 2.4.3 — breaks natural tab order |
| `tabindex="-1"` on natively interactive element (`<button>`, `<a href>`, `<input>`, etc.) | WARN | definitive | Removes from tab order |
| `outline: none` or `outline: 0` on focusable selector without `:focus-visible` replacement | HIGH | definitive | WCAG 2.4.7 |
| `onClick` / `onKeyDown` handler on `<div>` / `<span>` without `role="button"` + `tabindex="0"` + keydown handler for Enter/Space | HIGH | heuristic | WCAG 2.1.1 — not keyboard-accessible |
| No skip link (`<a href="#main">`, `<a href="#content">`) on page with navigation | WARN | heuristic | WCAG 2.4.1 Bypass Blocks |
| Potential keyboard trap: `event.preventDefault()` / `event.stopPropagation()` in keydown handler on modal/dialog without Escape handling | WARN | heuristic | WCAG 2.1.2 |
| Custom dropdown / combobox without `aria-expanded` + `aria-haspopup` + keyboard handlers | WARN | heuristic | WAI-ARIA Authoring Practices |
| `autofocus` on page load on non-critical input (distracts keyboard users, moves focus unexpectedly) | WARN | definitive | Confuses assistive tech |
| `contenteditable="true"` without `aria-label` / `aria-labelledby` | WARN | definitive | WCAG 4.1.2 |

### Category 4: Color, Contrast & Visual Cues

WCAG 1.4.1 (Use of Color), 1.4.3 (Contrast Minimum), 1.4.11 (Non-text Contrast).

**Static analysis limitation**: actual contrast ratios depend on the CSS cascade, custom properties, theme switching, and background images. The skill flags patterns where contrast is AT RISK; pair with runtime tools (axe-core, Lighthouse) for definitive measurement.

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| Hardcoded foreground+background color pairs in CSS where computed contrast is <4.5:1 (normal) or <3:1 (large text) | WARN | heuristic | WCAG 1.4.3 — verify at runtime |
| Link inside body text without underline/border AND only `color` distinguishing it | WARN | heuristic | WCAG 1.4.1 — color-only signalling |
| Error/required field indicated only by red color (no icon, text, or shape) | WARN | heuristic | WCAG 1.4.1 |
| Required form field marked only with `*` character without `aria-required="true"` + text explanation | WARN | definitive | WCAG 1.4.1 + 3.3.2 |
| CSS uses `color: red`/`color: green` as sole signal (success vs error) | WARN | heuristic | WCAG 1.4.1 |
| Focus indicator with <3:1 contrast against background (heuristic from color values) | WARN | heuristic | WCAG 1.4.11 |
| Button/input border color with <3:1 contrast against adjacent color | WARN | heuristic | WCAG 1.4.11 |
| CSS `text-shadow`/`opacity` on body text reducing effective contrast | INFO | heuristic | May affect 1.4.3 |

### Category 5: Forms, Labels & Errors

WCAG 1.3.5 (Identify Input Purpose), 3.3.1 (Error Identification), 3.3.2 (Labels or Instructions), 3.3.3 (Error Suggestion), 4.1.2 (Name, Role, Value).

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| `<input>` / `<select>` / `<textarea>` without `<label for="...">` AND without `aria-label` / `aria-labelledby` | HIGH | heuristic | WCAG 3.3.2, 4.1.2 |
| `<label>` without `for` attribute (implicit association only works if input is a child) | WARN | definitive | WCAG 3.3.2 |
| `<input type="email"/tel/name/password/address">` without `autocomplete` attribute | WARN | definitive | WCAG 1.3.5 |
| Missing `autocomplete="one-time-code"` on OTP input with `inputmode="numeric"` | INFO | definitive | Improves user experience |
| Radio / checkbox group without `<fieldset>` + `<legend>` | WARN | heuristic | WCAG 1.3.1 |
| Error messages displayed visually but not linked via `aria-describedby` to the input | WARN | heuristic | WCAG 3.3.1 |
| `required` attribute without accompanying `aria-required="true"` (belt-and-suspenders for assistive tech consistency) | INFO | definitive | WCAG 4.1.2 (modern SR handle `required` but legacy may not) |
| Error uses `role="alert"` without being updated dynamically (static alert on page load) | INFO | heuristic | WCAG 4.1.3 |
| Placeholder used as label (no visible label, only `placeholder`) | WARN | heuristic | WCAG 3.3.2 — placeholder disappears on focus |
| `<input type="email">` without `inputmode="email"` (mobile UX) | INFO | definitive | EN 301 549 mobile |

### Category 6: Media (Audio, Video, Embeds)

WCAG 1.2.1–1.2.5 (Captions, audio description, sign language), 1.4.2 (Audio Control).

**EAA is specifically strict about media** — video without captions is a common legal-risk finding.

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| `<video>` without `<track kind="captions">` child (or `<track kind="subtitles">` for foreign-language) | HIGH | definitive | WCAG 1.2.2 — EAA legal risk |
| `<video>` without transcript link or `<track kind="descriptions">` | WARN | heuristic | WCAG 1.2.3 / 1.2.5 |
| `<audio>` without transcript link or `<track kind="captions">` | HIGH | definitive | WCAG 1.2.1 |
| `<video autoplay>` without `muted` | HIGH | definitive | WCAG 1.4.2 — auto-playing audio |
| `<video autoplay loop>` running >5 seconds without pause control | WARN | heuristic | WCAG 1.4.2, 2.2.2 |
| YouTube/Vimeo embed URL without `cc_load_policy=1` or equivalent CC parameter | INFO | definitive | Platform-dependent captioning |
| YouTube embed via `<iframe src="https://www.youtube.com/embed/...">` without accessibility enhancements | INFO | definitive | Note: platform controls most a11y |
| Live media without real-time caption indication | WARN | heuristic | WCAG 1.2.4 |
| Background video (hero section) without pause button in DOM | WARN | heuristic | WCAG 2.2.2 |

### Category 7: ARIA, Live Regions & Dynamic Content

WCAG 4.1.2 (Name, Role, Value), 4.1.3 (Status Messages).

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| `aria-hidden="true"` on focusable element | HIGH | definitive | Creates orphaned focus — serious a11y bug |
| `role="button"` on native `<button>` (redundant ARIA) | WARN | definitive | ARIA Authoring: avoid redundant roles |
| `role="link"` on `<a href>` / `role="heading"` on `<h1–h6>` (redundant ARIA) | WARN | definitive | Same |
| Conflicting roles (`<button role="link">`, `<a role="button">`) | WARN | definitive | WAI-ARIA — wrong role |
| Custom toggle (disclosure, menu, accordion) without `aria-expanded` + `aria-controls` | WARN | heuristic | WAI-ARIA |
| `aria-labelledby` referencing non-existent ID | HIGH | heuristic | Broken reference |
| `aria-describedby` referencing non-existent ID | HIGH | heuristic | Broken reference |
| `aria-live` region without `role="status"` / `role="alert"` AND async updates in component (heuristic) | WARN | heuristic | WCAG 4.1.3 |
| Toast/notification component without `role="status"` or `role="alert"` | WARN | heuristic | WCAG 4.1.3 |
| Modal / dialog without `role="dialog"` + `aria-modal="true"` + focus trap | WARN | heuristic | WAI-ARIA Authoring Practices |
| Tabs without proper roles (`role="tablist"` + `role="tab"` + `role="tabpanel"`) | WARN | heuristic | WAI-ARIA Authoring Practices |

### Category 8: Motion, Target Size, Mobile & EAA Docs

#### 8a. Motion & Animation

WCAG 2.2.2 (Pause, Stop, Hide), 2.3.3 (Animation from Interactions — AAA but EAA-recommended).

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| CSS animation / transition / transform without matching `@media (prefers-reduced-motion: reduce)` override | WARN | heuristic | WCAG 2.3.3 |
| JS animation library (GSAP, framer-motion, anime.js) without `matchMedia('(prefers-reduced-motion: reduce)')` check | WARN | heuristic | WCAG 2.3.3 |
| Parallax scrolling without opt-out | WARN | heuristic | WCAG 2.3.3 |
| Infinite animation (CSS `animation: name infinite`) on content element without pause control | WARN | heuristic | WCAG 2.2.2 |
| `<marquee>` / `<blink>` (deprecated) | HIGH | definitive | WCAG 2.2.2 |

#### 8b. Target Size (WCAG 2.2 Minimum AA 2.5.8 + EN 301 549)

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| Interactive target with declared size <24×24 px (heuristic from CSS: `width`/`height`/`padding` on buttons/links/inputs) | WARN | heuristic | WCAG 2.2 2.5.8 / EN 301 549 |
| Touch-target spacing <8 px between adjacent interactive elements | INFO | heuristic | Best practice |

#### 8c. Viewport & Zoom

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| `<meta name="viewport">` containing `user-scalable=no` / `user-scalable=0` | HIGH | definitive | WCAG 1.4.4 — blocks zoom |
| `<meta name="viewport">` with `maximum-scale=1` / `maximum-scale=1.0` | HIGH | definitive | WCAG 1.4.4 |
| Content rendered via `<img>` for text (text-as-image) | WARN | heuristic | WCAG 1.4.5 |

#### 8d. Mobile (React Native + Flutter)

EN 301 549 mobile chapter. Critical for EAA scope since consumer apps are in-scope.

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| **React Native**: `<TouchableOpacity>` / `<TouchableHighlight>` / `<Pressable>` without `accessibilityLabel` | HIGH | definitive | EN 301 549 mobile |
| **React Native**: `<Image>` without `accessibilityLabel` or `accessible={false}` | WARN | heuristic | EN 301 549 |
| **React Native**: Missing `accessibilityRole` on custom components that behave as buttons/links | WARN | heuristic | EN 301 549 |
| **React Native**: `Alert.alert` for error flow without `AccessibilityInfo.announceForAccessibility` fallback | INFO | heuristic | — |
| **Flutter**: Interactive widget (`GestureDetector`, `InkWell`, `TextButton`, `IconButton`) without `Semantics()` wrapper or `semanticLabel` parameter | HIGH | definitive | EN 301 549 mobile |
| **Flutter**: `Image()` / `Image.asset()` / `Image.network()` without `semanticLabel` (or `excludeFromSemantics: true` for decorative) | WARN | definitive | EN 301 549 |
| **Flutter**: Missing `ExcludeSemantics` / `MergeSemantics` where child semantics conflict | INFO | heuristic | Semantics tree cleanup |

#### 8e. EAA Accessibility Documentation

**Activated by `--standard eaa`.** EAA Article 14 + member-state transpositions require consumer-facing services to publish an accessibility statement. Missing statement = HIGH legal finding.

| Pattern | Severity | Confidence | Description |
|---------|----------|------------|-------------|
| No route at any of: `/accessibility`, `/accessibility-statement`, `/a11y`, `/dostepnosc` (PL), `/barrierefreiheit` (DE), `/declaration-accessibilite` (FR), `/declaración-accesibilidad` (ES), `/dichiarazione-accessibilita` (IT), `/toegankelijkheidsverklaring` (NL) | HIGH | heuristic | EAA Article 14 |
| Footer / sitemap lacks link to accessibility statement | HIGH | heuristic | EAA visibility requirement |
| Accessibility statement present but missing required elements: (a) conformance level (WCAG/EN 301 549), (b) list of non-conformant content, (c) feedback mechanism, (d) enforcement procedure link | WARN | heuristic | Member-state template requirement |
| No contact mechanism (email / form) for accessibility feedback referenced in statement | WARN | heuristic | EAA Article 14 |
| `robots.txt` disallows `/accessibility*` path (accidentally blocks statement from crawlers + assistive tech) | WARN | definitive | Discoverability |

See: [eaa-compliance.md](eaa-compliance.md) for directive text, member-state deadlines, statement templates.

---
