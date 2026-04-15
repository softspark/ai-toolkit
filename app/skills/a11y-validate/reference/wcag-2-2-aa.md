# WCAG 2.2 New Success Criteria Reference

Reference for `a11y-validate --standard wcag-2.2-aa`. Covers ONLY the 9 new success criteria added in WCAG 2.2 (not in 2.1). For the 50 inherited criteria, see [wcag-2-1-aa.md](wcag-2-1-aa.md).

Source: W3C WCAG 2.2 Recommendation, 5 October 2023.

Note: WCAG 2.2 removes SC 4.1.1 Parsing (Level A) -- modern parsers handle malformed markup; the criterion is obsolete.

## Legend

- **Heuristic** -- static detection possible with false-positive/negative risk.
- **Runtime** -- requires rendering, interaction, or AT testing.

---

## Level A

### 2.4.11 Focus Not Obscured (Minimum) -- **Runtime**

When a component receives keyboard focus, it must not be entirely hidden by author-created content (sticky headers, cookie banners, chat widgets).

**Failures:** `position: fixed/sticky` elements with high `z-index` covering focused items. Cookie banners without `scroll-into-view` logic. Chat widgets overlapping tab-order elements.

```html
<!-- FAIL: focused link hidden behind sticky header -->
<header style="position: sticky; top: 0; z-index: 1000; height: 80px;">...</header>
<main><a href="/about">About</a></main>
```

**Grep:** `position:\s*(fixed|sticky)` | `z-index:\s*[0-9]{3,}`

**Frameworks:** React/Next -- add `scroll-padding-top` on `<html>` to offset sticky headers. Vue/Nuxt -- same for `<Teleport>` portals. Angular -- verify `CDK Overlay` does not obscure focus.

---

### 3.2.6 Consistent Help -- **Heuristic**

Help mechanisms (contact info, chat, FAQ) must appear in the same relative order across all pages in a set.

**Failures:** Help link in header on some pages, footer on others. Chat widget present on landing but absent on checkout.

```html
<!-- FAIL: Page A has help in header, Page B only in footer -->
<header><a href="/support">Help</a></header>  <!-- Page A -->
<footer><a href="/support">Help</a></footer>  <!-- Page B -->
```

**Grep:** `href=["'][^"']*(help|support|contact|faq)` | `(help|support|contact|chat|assistance)`

**Frameworks:** Place help links in shared layout -- `layout.tsx` (Next App Router), `layouts/default.vue` (Nuxt), shared `AppComponent` (Angular).

---

### 3.3.7 Redundant Entry -- **Heuristic**

Data previously entered in the same process must be auto-populated or selectable. Exceptions: security re-entry, expired/deleted data.

**Failures:** Multi-step form re-asking email without pre-fill. Billing address blank with no "same as shipping" checkbox.

```tsx
// FAIL: Step 3 re-asks email without persisting from Step 1
function Step3() {
  const [email, setEmail] = useState(''); // should pre-fill
  return <input value={email} onChange={e => setEmail(e.target.value)} />;
}
```

**Grep:** `(step|wizard|multi.?step|checkout)` | `(name|email|phone|address).*input`

**Frameworks:** React -- `useFormContext` (RHF) or Formik context across steps. Vue -- Pinia store. Angular -- shared `FormGroup` across stepper.

---

### 3.3.8 Accessible Authentication (Minimum) -- **Heuristic**

No cognitive function test for auth unless: (a) alternative exists, (b) mechanism helps complete it (paste, password manager), or (c) test uses object/personal-content recognition (allowed at Minimum, not Enhanced).

**Failures:** CAPTCHA with no non-cognitive alternative. Password field blocking paste or missing `autocomplete`. OTP input preventing paste.

```html
<!-- FAIL: blocks password manager -->
<input type="password" onpaste="return false">
<!-- FAIL: missing autocomplete -->
<input type="password" name="pwd">
<!-- PASS -->
<input type="password" name="pwd" autocomplete="current-password">
```

**Grep:** `onpaste.*preventDefault|onpaste.*return\s*false` | `captcha|recaptcha|hcaptcha` | `type=["']password["'](?!.*autocomplete)`

**Frameworks:** React uses `autoComplete="current-password"` (camelCase). Vue -- `autocomplete="current-password"`, no `@paste.prevent`. Angular -- `[attr.autocomplete]="'current-password'"`.

---

## Level AA

### 2.4.12 Focus Not Obscured (Enhanced) -- **Runtime**

No part of a focused component may be hidden by author-created content. Stricter than 2.4.11 -- even partial overlap fails.

**Failures:** Same as 2.4.11 but partial coverage also fails. Sticky sidebar partially covering a focused input. Bottom nav overlapping lower portion of a button.

```css
/* Fix: offset fixed elements with scroll-padding */
html { scroll-padding-bottom: 80px; scroll-padding-top: 100px; }
```

**Grep:** `position:\s*(fixed|sticky)` | `scroll-padding` | `scroll-margin`

**Frameworks:** All -- use `scroll-padding-top`/`scroll-padding-bottom` on scroll container. Tab through all interactive elements to verify.

---

### 2.4.13 Focus Appearance -- **Heuristic**

Focus indicator must have: (a) area >= perimeter x 2 CSS pixels (roughly a 2px outline), (b) >= 3:1 contrast between focused and unfocused states.

**Failures:** 1px dotted outline. Focus ring color close to background. `box-shadow`-only focus with low opacity.

```css
/* FAIL */ :focus-visible { outline: 1px dotted #ccc; }
/* FAIL */ :focus-visible { outline: 2px solid #e0e0e0; } /* ~1.1:1 on white */
/* PASS */ :focus-visible { outline: 2px solid #0056b3; outline-offset: 2px; }
```

**Grep:** `:focus-visible|:focus\b` | `outline:\s*(1px|0\.5px|thin|dotted|none|0)` | `box-shadow.*:focus`

**Frameworks:** React -- `@react-aria/focus` provides compliant rings; Shadcn `ring-2 ring-ring` needs contrast audit. Vue -- audit Vuetify/PrimeVue focus styles against theme. Angular -- Material `FocusMonitor` handles detection but verify visual indicator. Tailwind -- `focus-visible:ring-2 focus-visible:ring-offset-2` with high-contrast color.

---

### 2.5.7 Dragging Movements -- **Heuristic**

Drag functionality must have a single-pointer non-drag alternative (unless dragging is essential).

**Failures:** Drag-only reorder list without move buttons. Custom slider without keyboard steps. Kanban with drag-only cards.

```tsx
// FAIL: drag-only, no button alternative
<DndContext onDragEnd={handleDragEnd}>
  <SortableContext items={items}>
    {items.map(item => <SortableItem key={item.id} {...item} />)}
  </SortableContext>
</DndContext>

// PASS: add move buttons per item
<button onClick={() => moveUp(id)} aria-label="Move up">^</button>
<button onClick={() => moveDown(id)} aria-label="Move down">v</button>
```

**Grep:** `draggable|onDrag|DndContext|useDrag|useDrop` | `react-beautiful-dnd|@dnd-kit|react-dnd|vuedraggable|cdkDrag|SortableJS`

**Frameworks:** React -- `@dnd-kit` supports `KeyboardSensor`; ensure it is registered. Vue -- `vuedraggable` lacks keyboard reorder; add move buttons. Angular -- `cdk/drag-drop` has keyboard support; verify active.

---

### 2.5.8 Target Size (Minimum) -- **Heuristic**

Interactive targets must be >= 24x24 CSS pixels, unless spacing compensates, target is inline, or size is essential.

**Failures:** 16x16 icon buttons without padding. Close (`x`) buttons with tiny tap targets. Dense table action icons.

```css
/* FAIL */ .icon-btn { width: 16px; height: 16px; padding: 0; }
/* PASS */ .icon-btn { width: 24px; height: 24px; }
/* PASS */ .icon-btn { width: 16px; height: 16px; padding: 4px; } /* 24x24 total */
```

**Grep:** `(width|height|min-width|min-height):\s*(1[0-9]|2[0-3])px` | `(w-[1-5]|h-[1-5])\b` | `padding:\s*0[;\s]`

**Frameworks:** React -- Shadcn `size="icon"` is 36x36 (safe); custom icons need `min-w-6 min-h-6`. Vue -- Vuetify `v-btn icon` is 40x40 (safe). Angular -- `mat-icon-button` is 40x40 (safe). Tailwind minimum: `min-w-6 min-h-6` (24px); prefer `min-w-11 min-h-11` (44px) for touch.

---

## Level AAA

### 3.3.9 Accessible Authentication (Enhanced) -- **Heuristic**

Same as 3.3.8 but stricter: no cognitive test at all, including object recognition and personal content recognition. Only paste support, password manager autofill, or non-cognitive methods (WebAuthn, passkeys, magic links) qualify.

**Failures:** "Select all traffic lights" CAPTCHA (passes 3.3.8, fails 3.3.9). "Which is your profile photo?" (same). Any image/puzzle verification without fully non-cognitive alternative.

```html
<!-- FAIL at AAA --> <div class="g-recaptcha" data-sitekey="..."></div>
<!-- PASS --> <div class="g-recaptcha" data-sitekey="..." data-size="invisible"></div>
<!-- PASS --> <button onclick="navigator.credentials.get({publicKey: opts})">Passkey</button>
```

**Grep:** `recaptcha|hcaptcha|captcha|turnstile` | `data-size=["']invisible["']` | `navigator\.credentials\.(get|create)` | `WebAuthn|passkey`

**Frameworks:** All -- prefer WebAuthn/passkeys, magic links, or invisible CAPTCHA (reCAPTCHA v3, Turnstile managed). At AAA, even "select all buses" fails.

---

## Detection Coverage Summary

| Criterion | Level | Detection |
|-----------|-------|-----------|
| 2.4.11 Focus Not Obscured (Min) | A | Runtime |
| 2.4.12 Focus Not Obscured (Enhanced) | AA | Runtime |
| 2.4.13 Focus Appearance | AA | Heuristic |
| 2.5.7 Dragging Movements | AA | Heuristic |
| 2.5.8 Target Size (Minimum) | AA | Heuristic |
| 3.2.6 Consistent Help | A | Heuristic |
| 3.3.7 Redundant Entry | A | Heuristic |
| 3.3.8 Accessible Auth (Min) | AA | Heuristic |
| 3.3.9 Accessible Auth (Enhanced) | AAA | Heuristic |

- **0 statically detectable** -- no criterion is definitively matchable without context
- **7 heuristically detectable** -- the skill can flag likely violations
- **2 runtime-only** -- focus obscuring requires rendering to verify

---

## References

- WCAG 2.2 Recommendation: https://www.w3.org/TR/WCAG22/
- What's New in WCAG 2.2: https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
- Understanding WCAG 2.2: https://www.w3.org/WAI/WCAG22/Understanding/
- WCAG 2.2 Quick Reference: https://www.w3.org/WAI/WCAG22/quickref/
- Techniques for WCAG 2.2: https://www.w3.org/WAI/WCAG22/Techniques/
