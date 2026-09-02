---
name: design-engineering
description: "UI craftsmanship: animation rules, easing, micro-interactions, state polish. Triggers: animation, transition, ease-out, motion, micro-interaction, hover, loading state, UI polish."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Design Engineering Skill

Based on Emil Kowalski's design engineering philosophy — UI polish, component craftsmanship, and the compound value of invisible details.

## Core Principles

- **Taste is trainable.** Develops through studying exceptional work, reverse-engineering animations, and intentional practice.
- **Invisible details create love.** Most UI refinements users never consciously register — but combined they produce something stunning.
- **Beauty differentiates.** When functionality is table stakes, aesthetic excellence becomes genuine leverage.

## Anti-Slop Visual & Structural Checklist

Defaults that signal machine-generated UI ("AI slop"). Each is a falsifiable rule to uphold:

- **Avoid** full-bleed saturated gradient backgrounds (purple-to-pink/blue hero washes) and gradient headlines (`background-clip: text`). Use solid ink or warm neutral tinting.
- **Avoid** emoji as load-bearing decoration (emoji as icons, bullet markers, or section badges). Use a real icon set (Lucide/Phosphor/Heroicons) or typographic hierarchy.
- **Avoid** the 3-equal-column card grid with icon-above-heading tiles, nested cards-in-cards, or cards with thick coloured left-edge side stripes.
- **Avoid** hand-drawn fake imagery in SVG (synthetic "photos", invented logos, faux screenshots). Use a real asset or an honest labeled placeholder.
- **Avoid** fake re-drawn UI chrome (mock browser bars with traffic-light dots, mock IDE title bars, faux phone frames). Let content stand cleanly or use real screenshots in a `<figure>`.
- **Avoid** default-attractor sameness (Hero → 3 features → CTA → footer). Pick intentional macrostructures and vary heading placement, column rhythm, and divider language.
- **Avoid** the overused default font stack (Inter/Roboto on system-ui with no pairing). Apply the **2+1 rule** (display + body + at most 1 outlier face in <=2 slots).
- **Avoid** italic headers: headings and display type are always roman (`font-style: normal`). Never use single-word italic emphasis inside a headline.

## Pre-Emit Self-Critique (Six Axes)

Before marking any UI output complete, score it 1–5 on these six axes (score <3 on any axis triggers a revision pass):

| # | Axis | Assessment |
|---|---|---|
| **P** | **Philosophy** | Clear position and intent ("why"), not just arbitrary decoration |
| **H** | **Hierarchy** | Clear primary / secondary / tertiary weight distinguishable in 2 seconds |
| **E** | **Execution** | Exact rule weights, contrast ratios, focus rings, zero layout shifts |
| **S** | **Specificity** | Tailored specifically to this brief, not a generic interchangeable template |
| **R** | **Restraint** | Removed anything unearned (decorative bloat, redundant cards, excess padding) |
| **V** | **Variety** | Structurally distinct from previous layouts in the project (not just a color swap) |

## The 8 Interactive States Discipline

Every interactive element (button, input, select, card, tab, switch) must explicitly handle all 8 states in code. Styling only default + hover is an immediate defect:

| State | Trigger | Required Treatment |
|---|---|---|
| **1. Default** | At rest | Clean base styling, defined token bindings |
| **2. Hover** | Pointer over (`@media (hover: hover)`) | Subtle background shift (4–6%) or 1px translate, no layout jump |
| **3. Focus** | Keyboard navigation | Visible `:focus-visible` ring (2px solid, 1–2px offset), instant appearance |
| **4. Active** | Pressed | Pressed-in feel: slight darken, `transform: translateY(1px)` or `scale(0.98)` |
| **5. Disabled** | Inactive (`disabled`, `aria-disabled`) | 3 channels: `opacity: 0.55`, `cursor: not-allowed`, muted token color |
| **6. Loading** | Async in-flight (`data-state="loading"`) | Inline spinner replacing icon/badge, label preserved, submit disabled |
| **7. Error** | Validation failure (`aria-invalid="true"`) | Distinct error token border/message, helper text replaced, error icon |
| **8. Success** | Operation completed (`data-state="success"`) | Quiet confirmation: subtle green/accent indicator or checkmark, auto-dismiss |

## Input Fields & Zero Layout Shift

Input fields, textareas, and selects are where almost-right UIs break:

- **Constant border width (1px everywhere)**: Never change `border-width` between default, hover, focus, error, or disabled states. State changes go to `background-color`, `outline`, `box-shadow`, or `border-color`.
- **Reserved transparent outline**: Initialize with `outline: 2px solid transparent; outline-offset: 1px;` so activating `:focus-visible` never shifts layout or thrashes paint.
- **Matched component heights**: Input height MUST equal adjacent button height (base floor 44px for touch targets).
- **Reserved helper-text slot**: Allocate `min-height: 1lh` for helper/error text so appearing validation messages do not push downstream page content.

## Responsive Non-Negotiables

Verify every layout at **320px, 375px, 414px, and 768px**:

- **No horizontal scroll**: Apply `overflow-x: clip` (never `hidden`) on **both** `html` and `body`.
- **Single-line clickable affordances**: Buttons, primary nav links, footer links, and CTAs must never wrap to two lines. Shorten label or reflow parent container.
- **Image grid tracks**: Always use `minmax(0, 1fr)` instead of bare `1fr` to prevent image intrinsic dimensions from blowing out the grid.
- **Header wrapping**: Display headers must include `overflow-wrap: anywhere; min-width: 0;`.

## Locked Tokens Discipline

- All colors and typography must bind to declared tokens (`var(--color-accent)`, `var(--font-display)`).
- Never improvise inline hex / rgb / OKLCH values in components mid-build.
- Keep accent footprint under **~5%** of viewport area (accent is for focal emphasis, not surface fill).
- Tint neutral surfaces toward the primary anchor hue (minimum 0.005 chroma in OKLCH) — avoid flat `#000` / `#fff`.

## Minimum-Scale Floors

Accessibility-grounded hard thresholds. Going below these is a defect, not a style choice:

| Context | Floor | Basis |
|---|---|---|
| Slide / presentation body text | ~24px | Readable from the back of a room |
| Print body text | ~12pt | Legible at arm's length on paper |
| Mobile touch targets | 44px × 44px | Apple HIG minimum tappable size |

Treat these as the lower bound, not the target. Captions and footnotes may approach the floor; primary content should sit comfortably above it.

## Context-First & Pre-Flight Discipline

High-fidelity work MUST be rooted in real context before any pixels are produced:

- **Run Pre-Flight Scan**: Inspect existing `design.md`, package font stacks, palette tokens (`:root`, Tailwind `@theme`), motion libraries (`framer-motion`, `motion`, `gsap`), and spacing scale.
- **Preserve existing design systems**: Never overwrite established tokens or typography unless explicitly asked.
- **Lift exact values**: Copy real token variable names and spacing classes straight from source. Do NOT reconstruct token values from memory.

## Question-Budget Gate

Calibrate questions to how bounded the ask is, then proceed:

- **Rich context + bounded ask** → ask nothing, build. Example: "match this card to the existing dashboard" with the repo in hand.
- **Open ask** → ask before building. Example: "prototype my onboarding" needs goals, target audience, and which dimension to diverge on (UX flow vs. visual treatment vs. copy). Resolve those three, then start.

## Explore Many Variations

For exploratory or open work, produce **3+ atomic variations** across distinct axes, never three tweaks of one idea:

- Vary on different dimensions: layout, color, type treatment, interaction model.
- Deliberately mix safe matches with at least one novel direction — do not converge early.
- Order them basic → advanced so the reviewer can scan the gradient (the "Design It Twice" premise extended past two).

## Match Existing Vocabulary

When editing a live UI, conform to it instead of imposing a new style:

- Reverse-engineer the palette, interactive states (hover/active/disabled), motion timing, and shadow/card/density treatment.
- Match the copy tone too — terse product UI and chatty marketing copy are different vocabularies.
- A change that introduces a foreign style is a regression even when it looks good in isolation.

## No-Filler Content

- **Every element earns its place.** No dummy stats, decorative sections, or lorem blocks added just to fill space. If a block has no purpose, cut it.
- **Honest placeholder beats a bad fake.** A labeled placeholder ("[product screenshot]") is better than an invented icon or hand-drawn fake image. Do NOT fabricate assets — ask for the real ones.

## Animation Decision Framework

### Frequency determines approach

| Usage Pattern | Strategy |
|---|---|
| 100+ daily | No animation |
| Tens daily | Drastically reduce |
| Occasional | Standard animation |
| Rare/first-time | Add delight |

**Never animate keyboard-initiated actions** — they repeat hundreds of times daily, making animation feel sluggish.

### Purpose validation

Every animation requires justification: spatial consistency, state indication, explanation, user feedback, or preventing jarring transitions. "It looks cool" alone disqualifies frequent interactions.

### Easing rules

| Direction | Easing | Why |
|---|---|---|
| Entering elements | `ease-out` | Immediate feedback |
| On-screen movement | `ease-in-out` | Natural acceleration |
| Hover/color changes | `ease` | Smooth transition |
| Constant motion | `linear` | No acceleration |

**Critical:** Abandon default CSS easings. Use custom curves:

```css
/* Punchy entrance */
transition-timing-function: cubic-bezier(0.23, 1, 0.32, 1);
```

**Never use `ease-in`** — it delays initial movement exactly when attention peaks, making interfaces feel sluggish.

### Duration guidelines

| Element | Timing |
|---|---|
| Button press | 100-160ms |
| Tooltips, small popovers | 125-200ms |
| Dropdowns, selects | 150-250ms |
| Modals, drawers | 200-500ms |

UI animations should stay **under 300ms**. Speed perception matters as much as actual speed.

## Component Patterns

### Buttons must respond

```css
button:active {
  transform: scale(0.97);
}
```

Tactile feedback confirming interface responsiveness.

### Never scale from zero

```css
/* Bad */
.enter { transform: scale(0); opacity: 0; }

/* Good — natural entrance */
.enter { transform: scale(0.95); opacity: 0; }
```

Real-world objects don't vanish and reappear. Start from `scale(0.95)`.

### Popovers scale from triggers

```css
.popover {
  transform-origin: var(--radix-popover-content-transform-origin);
}
```

Exception: modals keep centered origin (viewport-anchored, not trigger-anchored).

### Tooltip optimization

Initial tooltip includes delay; subsequent hovers skip both delay and animation via `[data-instant]` attribute — perceived speed without defeating accidental activation prevention.

## Advanced Animation Techniques

For advanced transform mastery, 3D orbits, and clip-path animation recipes (tabs, hold-to-delete, image reveals, sliders), see [reference/animation-recipes.md](reference/animation-recipes.md).

## Performance Rules

### GPU acceleration

Only animate `transform` and `opacity` — these skip layout and paint. Animating `padding`, `margin`, `height`, `width` triggers full rendering pipeline.

### CSS variables caveat

Changing parent CSS variables recalculates styles on all children. Update `transform` directly on elements instead.

### Framer Motion gotcha

Shorthand properties (`x`, `y`, `scale`) use main-thread `requestAnimationFrame`, not GPU:

```tsx
// Bad — main thread
<motion.div animate={{ x: 100 }} />

// Good — GPU accelerated
<motion.div animate={{ transform: "translateX(100px)" }} />
```

### CSS beats JavaScript

CSS animations run off-thread and remain smooth during page loads. Framer Motion drops frames when browser is busy. Use CSS for predetermined animations; JavaScript for dynamic, interruptible ones.

## Accessibility

### Reduced motion

Keep opacity and color transitions (aid comprehension). Remove movement and position animations:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Touch hover protection

```css
@media (hover: hover) and (pointer: fine) {
  .card:hover {
    transform: translateY(-2px);
  }
}
```

Touch triggers false hover positives — always gate hover animations.

## Building Loved Components

For component craftsmanship principles (developer experience, defaults, edge cases, asymmetric timing), see [reference/component-craft.md](reference/component-craft.md).

## Review Checklist

| Issue | Resolution |
|---|---|
| `transition: all` | Specify properties: `transition: transform 200ms ease-out` |
| `scale(0)` entries | Start `scale(0.95)` with `opacity: 0` |
| `ease-in` on UI | Switch to `ease-out` or custom curve |
| Popover `transform-origin: center` | Use trigger-aware CSS variable |
| Animation on keyboard actions | Remove entirely |
| Duration > 300ms UI | Reduce to 150-250ms |
| Hover without media query | Add `@media (hover: hover) and (pointer: fine)` |
| Keyframes on rapid triggers | Use CSS transitions |
| Framer `x`/`y` under load | Use `transform: "translateX()"` |
| Identical enter/exit speed | Make exit faster (e.g., 2s enter, 200ms exit) |
| Simultaneous element appearance | Stagger 30-80ms between items |

## Two-Stage Verification Handoff

Visual work ships through two passes, mirroring the toolkit's verification-before-completion and subagent two-stage review ethos:

1. **Cheap self-check.** Load the rendered result yourself, eyeball it, and fix the obvious breaks (broken layout, wrong token, console errors) before handing off. Never claim done on output you have not opened.
2. **Independent verifier pass.** A separate reviewer (or fresh subagent) does the deeper check — visual fidelity against source, layout under different widths, console clean. On pass it stays silent; it surfaces ONLY on failure, with the specific defect.

## Anti-Patterns

- `transition: all` — animates unintended properties, hurts performance
- `ease-in` on UI elements — delays feedback when attention peaks
- Animating `height`/`width`/`margin` — triggers layout recalculation
- Same duration for enter and exit — exits should be faster
- Hover effects without `@media (hover: hover)` — breaks touch devices
- Framer Motion shorthands under load — drops frames on main thread

## Rules

- **MUST** specify exact properties in `transition` (`transition: transform 200ms ease-out`) — never `transition: all`
- **MUST** use `ease-out` (or a custom curve) on UI appearances; `ease-in` delays feedback at the moment the user's attention peaks
- **NEVER** animate `height`, `width`, `margin`, or `top/left` — animate `transform` and `opacity` only
- **CRITICAL**: exit is faster than enter. A 2s linear enter (hold-to-delete) needs a 200ms ease-out exit
- **MANDATORY**: any animation longer than 300ms for UI feedback needs an explicit justification
- **MUST** implement all 8 interactive states (default, hover, focus-visible, active, disabled, loading, error, success) for every interactive element
- **MUST** keep `border-width: 1px` constant across all input states (default/hover/focus/error/disabled) with a reserved transparent outline to guarantee zero layout shift
- **MUST** apply `overflow-x: clip` on both `html` and `body` to eliminate horizontal viewport scrolling on mobile (320px–768px)
- **MUST** ensure clickable affordance text (buttons, nav links, CTAs) remains single-line across all viewports
- **MUST** keep all display headings roman (`font-style: normal`) — never use single-word italic emphasis inside headlines
- **MUST** adhere to the 2+1 typography rule (max 3 families, outlier face used in at most 2 slots)
- **MUST** lock all colors to named CSS variable tokens — never improvise inline hex/rgb/OKLCH values mid-render
- **MUST** lift exact values (hex, spacing, font stack, radii) from real source — never reconstruct tokens from memory
- **MUST** keep mobile touch targets at 44px+ minimum floor
- **NEVER** ship slop defaults (purple/blue gradient hero washes, gradient text headlines, emoji as icons, cards-in-cards, side-stripe cards, centered-everything 100vh heroes)
- **NEVER** add filler (dummy stats, fake testimonials, invented logos, lorem) — use honest labeled placeholders
- **MUST** run pre-emit self-critique scoring (P/H/E/S/R/V) before completing UI implementation

## Gotchas

For compositor edge cases, Framer Motion GPU optimizations, and reduced-motion gotchas, see [reference/animation-recipes.md](reference/animation-recipes.md).

## When NOT to Load

- For **accessibility** beyond motion (contrast, focus, ARIA) — use `/a11y-validate`
- For component-library architecture (Radix, Headless UI, ShadCN) — use `/frontend-specialist` agent
- For **information architecture** and user flows — use `/ux-designer` agent
- For generic CSS patterns without motion — this skill is motion-specific
- For **brand voice** / content tone — use `/brand-voice`

