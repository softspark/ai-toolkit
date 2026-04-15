# WCAG 2.1 Level A + AA Reference

Reference for `a11y-validate`. All 50 WCAG 2.1 Level A + AA success criteria, with a detection-pattern matrix (which are statically detectable vs. runtime-only).

Source: W3C Web Content Accessibility Guidelines (WCAG) 2.1 Recommendation, 5 June 2018 (most recent maintenance: October 2023).

## Legend

- **Static** — detectable via source-code pattern matching (this skill's wheelhouse).
- **Heuristic** — static detection possible but with false-positive/negative risk.
- **Runtime** — requires rendering, interaction, or AT testing; beyond static analysis.
- **Authoring** — depends on content choices, not code patterns.

---

## Principle 1: Perceivable

### Guideline 1.1 — Text Alternatives

#### 1.1.1 Non-text Content (Level A) — **Static**
Images, form inputs, and non-text UI components must have text alternatives. Detection: `<img>` without `alt`, icon fonts without `aria-label`, `<svg>` without `<title>`/`aria-label`, form inputs without label, decorative images with non-empty alt.

### Guideline 1.2 — Time-based Media

#### 1.2.1 Audio-only and Video-only (Prerecorded) (Level A) — **Static**
Detection: `<audio>` without transcript; `<video>` without audio track requires captions.

#### 1.2.2 Captions (Prerecorded) (Level A) — **Static**
Detection: `<video>` without `<track kind="captions">`. **EAA legal risk.**

#### 1.2.3 Audio Description or Media Alternative (Prerecorded) (Level A) — **Static**
Detection: `<video>` without `<track kind="descriptions">` and no linked transcript.

#### 1.2.4 Captions (Live) (Level AA) — **Runtime**
Live caption quality can't be verified statically. Flag live-media patterns (WebRTC, YouTube Live embeds) for manual review.

#### 1.2.5 Audio Description (Prerecorded) (Level AA) — **Static**
Detection: Same as 1.2.3 but at AA level.

### Guideline 1.3 — Adaptable

#### 1.3.1 Info and Relationships (Level A) — **Static**
Detection: `<div>` used where semantic element appropriate; heading skip; missing landmarks; tables without `<th>`/`<caption>`.

#### 1.3.2 Meaningful Sequence (Level A) — **Heuristic**
CSS `order` / `flex-direction: row-reverse` that disconnects visual from DOM order. Hard to verify without rendering.

#### 1.3.3 Sensory Characteristics (Level A) — **Authoring**
Instructions like "click the button on the right" — content-driven.

#### 1.3.4 Orientation (Level AA) — **Static**
Detection: CSS `@media (orientation: portrait)` / `landscape` with content visibility rules that lock orientation.

#### 1.3.5 Identify Input Purpose (Level AA) — **Static**
Detection: `<input type="email/tel/name/cc-*/bday-*/street-*">` without `autocomplete` matching WCAG input-purpose taxonomy.

### Guideline 1.4 — Distinguishable

#### 1.4.1 Use of Color (Level A) — **Heuristic**
Detection: color-only signalling (links distinguished only by `color`, errors only by red, etc.).

#### 1.4.2 Audio Control (Level A) — **Static**
Detection: `<audio autoplay>` or `<video autoplay>` without `muted` AND without pause control.

#### 1.4.3 Contrast (Minimum) (Level AA) — **Heuristic**
Detection: hardcoded color pairs in CSS with computed contrast <4.5:1 (normal) or <3:1 (large text, 18pt+/14pt bold+). Runtime cascade may change this — flag as heuristic.

#### 1.4.4 Resize Text (Level AA) — **Static**
Detection: `<meta name="viewport">` with `user-scalable=no` or `maximum-scale=1`. Also flag `font-size` in `px` where rem/em would adapt better (INFO only).

#### 1.4.5 Images of Text (Level AA) — **Heuristic**
Detection: `<img>` with `alt` containing a full sentence — likely text rendered as image.

#### 1.4.10 Reflow (Level AA) — **Runtime**
Content must reflow at 320 CSS pixels width / 256 CSS pixels height without horizontal scroll. Requires rendering.

#### 1.4.11 Non-text Contrast (Level AA) — **Heuristic**
Detection: button/input border colors, focus indicator colors vs. adjacent colors — hardcoded combinations with <3:1 contrast.

#### 1.4.12 Text Spacing (Level AA) — **Runtime**
Content must adapt when users override line-height, letter-spacing, word-spacing, paragraph-spacing. Requires rendering.

#### 1.4.13 Content on Hover or Focus (Level AA) — **Runtime**
Tooltips/popovers must be dismissible, hoverable, persistent. Requires interaction testing.

---

## Principle 2: Operable

### Guideline 2.1 — Keyboard Accessible

#### 2.1.1 Keyboard (Level A) — **Heuristic**
Detection: `onClick` on `<div>`/`<span>` without role+tabindex+keydown; native `<button>` converted via CSS to link (acceptable) but custom `<a role="button">` without tabindex/key handlers (not acceptable).

#### 2.1.2 No Keyboard Trap (Level A) — **Heuristic**
Detection: `event.preventDefault()` in keydown within modal/dialog without Escape handling.

#### 2.1.4 Character Key Shortcuts (Level A) — **Heuristic**
Detection: global keydown listener on single-character keys without modifier. Should be disableable or only active on focus.

### Guideline 2.2 — Enough Time

#### 2.2.1 Timing Adjustable (Level A) — **Runtime**
Session timeouts, auto-refresh — requires behavioral testing.

#### 2.2.2 Pause, Stop, Hide (Level A) — **Static**
Detection: `<marquee>` / `<blink>` (deprecated); CSS `animation: ... infinite` on non-interactive element without pause control; auto-sliding carousel without pause button.

### Guideline 2.3 — Seizures and Physical Reactions

#### 2.3.1 Three Flashes or Below Threshold (Level A) — **Runtime**
Requires visual analysis.

### Guideline 2.4 — Navigable

#### 2.4.1 Bypass Blocks (Level A) — **Static**
Detection: No skip link (`<a href="#main">`) and no landmark `<main>`.

#### 2.4.2 Page Titled (Level A) — **Static**
Detection: `<title>` missing, empty, or duplicated across routes.

#### 2.4.3 Focus Order (Level A) — **Static**
Detection: `tabindex` value >0.

#### 2.4.4 Link Purpose (In Context) (Level A) — **Heuristic**
Detection: link text "click here", "read more", "here" without surrounding descriptive context.

#### 2.4.5 Multiple Ways (Level AA) — **Static**
Detection: Sitemap / search / navigation absence across project.

#### 2.4.6 Headings and Labels (Level AA) — **Static**
Detection: Empty `<h1>`, empty `<label>`, generic "Input" labels.

#### 2.4.7 Focus Visible (Level AA) — **Static**
Detection: `outline: none` / `outline: 0` on focusable selector without `:focus-visible` replacement.

### Guideline 2.5 — Input Modalities

#### 2.5.1 Pointer Gestures (Level A) — **Heuristic**
Detection: Multi-touch / path-based gestures (swipe, pinch) without single-pointer alternative.

#### 2.5.2 Pointer Cancellation (Level A) — **Heuristic**
Detection: `onMouseDown` triggering action without `onMouseUp` confirmation (up-event cancellation).

#### 2.5.3 Label in Name (Level A) — **Heuristic**
Detection: `<button aria-label="Close">✕</button>` where visible text ("Close") doesn't appear in accessible name. Also: button visible text "Submit" with `aria-label="Save"` — mismatched.

#### 2.5.4 Motion Actuation (Level A) — **Heuristic**
Detection: `devicemotion` / `deviceorientation` handlers without alternative UI control.

---

## Principle 3: Understandable

### Guideline 3.1 — Readable

#### 3.1.1 Language of Page (Level A) — **Static**
Detection: `<html>` missing `lang` attribute.

#### 3.1.2 Language of Parts (Level AA) — **Heuristic**
Detection: Foreign-language content without `<span lang="...">` wrapper.

### Guideline 3.2 — Predictable

#### 3.2.1 On Focus (Level A) — **Heuristic**
Detection: `onFocus` handler that changes context (navigation, submit, modal open).

#### 3.2.2 On Input (Level A) — **Heuristic**
Detection: `<form>` submitted on `onChange` of single input; `window.location` changed in `onChange` handler.

#### 3.2.3 Consistent Navigation (Level AA) — **Heuristic**
Detection: Navigation component with route-dependent render (different nav on different pages).

#### 3.2.4 Consistent Identification (Level AA) — **Heuristic**
Detection: Same UI element with different ARIA labels / icons across pages.

### Guideline 3.3 — Input Assistance

#### 3.3.1 Error Identification (Level A) — **Heuristic**
Detection: Error display without `aria-describedby` link from input.

#### 3.3.2 Labels or Instructions (Level A) — **Static**
Detection: `<input>` without label.

#### 3.3.3 Error Suggestion (Level AA) — **Authoring**
Content-driven: does the error message tell the user what's wrong and how to fix it?

#### 3.3.4 Error Prevention (Legal, Financial, Data) (Level AA) — **Heuristic**
Detection: Payment / delete / purchase form without confirmation step / review-before-submit.

---

## Principle 4: Robust

### Guideline 4.1 — Compatible

#### 4.1.1 Parsing (Level A, removed in WCAG 2.2) — **Static**
Detection: Malformed HTML, duplicate IDs, unclosed tags. Modern browsers tolerate most parse errors; WCAG 2.2 removes this criterion.

#### 4.1.2 Name, Role, Value (Level A) — **Static**
Detection: `<div onClick>` without role; custom widgets without ARIA state; `aria-labelledby` pointing to non-existent ID.

#### 4.1.3 Status Messages (Level AA) — **Heuristic**
Detection: Toast / async error display without `role="status"` / `role="alert"` / `aria-live`.

---

## WCAG 2.2 AA Additions (enable with `--standard wcag-2.2-aa`)

### 2.4.11 Focus Not Obscured (Minimum) (Level AA) — **Runtime**
Focused element must not be entirely hidden by author-created content (sticky headers, cookie banners).

### 2.5.7 Dragging Movements (Level AA) — **Heuristic**
Detection: drag-and-drop UI without keyboard alternative (buttons to reorder).

### 2.5.8 Target Size (Minimum) (Level AA) — **Heuristic**
Detection: interactive target <24×24 CSS pixels in source CSS.

### 3.2.6 Consistent Help (Level A) — **Heuristic**
Detection: Help / contact / support link not consistently placed across pages.

### 3.3.7 Redundant Entry (Level A) — **Heuristic**
Detection: Multi-step form asking for same data (email, name, address) twice without autofill.

### 3.3.8 Accessible Authentication (Minimum) (Level AA) — **Heuristic**
Detection: CAPTCHAs (reCAPTCHA v2 checkbox, image-based CAPTCHAs) without non-cognitive alternative; passwords without `autocomplete="current-password"` / `autocomplete="new-password"`.

---

## EN 301 549 Additional Requirements (enable with `--standard en-301-549` or `eaa`)

EN 301 549 v3.2.1 aligns with WCAG 2.1 AA but adds:

- **Chapter 5: Generic requirements** — user preferences, biometric alternatives, privacy of personal information.
- **Chapter 6: ICT with two-way voice communication** — real-time text, captions for calls.
- **Chapter 7: ICT with video capabilities** — captions for recorded video.
- **Chapter 9: Web** — full WCAG 2.1 AA.
- **Chapter 10: Non-web documents** — WCAG for PDFs.
- **Chapter 11: Software** — WCAG-equivalent for native apps. **Critical for EAA mobile scope.**
- **Chapter 12: Documentation and support services** — accessibility information published.
- **Chapter 13: ICT providing relay / emergency services**.

### Chapter 11.x (Software / Mobile)

Corresponds to WCAG criteria applied to mobile/native apps:

| Clause | Maps to WCAG | Description |
|--------|--------------|-------------|
| 11.1.1.1 | 1.1.1 | Non-text content in software |
| 11.1.3.1 | 1.3.1 | Info and relationships in software |
| 11.2.1.1 | 2.1.1 | Keyboard alternatives in software |
| 11.4.1.1 | 4.1.1 | Parsing in software (native UI tree correctness) |
| 11.4.1.2 | 4.1.2 | Name, role, value in software |

For React Native / Flutter, this means: every interactive widget needs an accessible name, role, state exposed to the platform accessibility API (iOS UIAccessibility / Android AccessibilityNodeInfo).

See [mobile-eaa.md](mobile-eaa.md) for implementation patterns.

---

## Detection Coverage Summary

Of 50 WCAG 2.1 Level A + AA criteria:
- **~20 statically detectable** (this skill's definitive findings)
- **~15 heuristically detectable** (confidence: heuristic)
- **~10 runtime-only** (needs rendering/interaction)
- **~5 authoring-only** (content decisions, not code)

For complete coverage, pair `/a11y-validate` with:
- **axe-core** (via Playwright / Cypress / Jest)
- **Lighthouse accessibility audit**
- **pa11y CLI**
- **NVDA / JAWS / VoiceOver / TalkBack manual testing**
- **User research with disabled participants**

---

## References

- WCAG 2.1: https://www.w3.org/TR/WCAG21/
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- EN 301 549 v3.2.1: https://www.etsi.org/deliver/etsi_en/301500_301599/301549/03.02.01_60/en_301549v030201p.pdf
- WCAG Quick Reference: https://www.w3.org/WAI/WCAG21/quickref/
- Understanding WCAG: https://www.w3.org/WAI/WCAG21/Understanding/
- Techniques for WCAG: https://www.w3.org/WAI/WCAG21/Techniques/
