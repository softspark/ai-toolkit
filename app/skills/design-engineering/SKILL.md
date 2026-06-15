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

## Anti-Slop Visual Checklist

Defaults that signal machine-generated UI. Each is a falsifiable thing to avoid:

- **Avoid** full-bleed saturated gradient backgrounds (purple-to-pink hero washes). A flat surface or a near-flat tonal shift reads as intentional; a loud gradient reads as a template.
- **Avoid** emoji as load-bearing decoration — emoji standing in for icons, bullet markers, or section badges. Use a real icon set or typographic hierarchy instead.
- **Avoid** the rounded-card-with-left-accent-border cliche repeated across every block. If three sections share that exact treatment, vary the layout or drop the accent.
- **Avoid** hand-drawn fake imagery in SVG (synthetic "photos", invented logos, faux screenshots). Use a real asset or an honest labeled placeholder.
- **Avoid** the overused default font stack (Inter/Roboto on system-ui for everything with no scale or weight intent). Pick type with a reason and lift the actual stack from source when one exists.

## Minimum-Scale Floors

Accessibility-grounded hard thresholds. Going below these is a defect, not a style choice:

| Context | Floor | Basis |
|---|---|---|
| Slide / presentation body text | ~24px | Readable from the back of a room |
| Print body text | ~12pt | Legible at arm's length on paper |
| Mobile touch targets | 44px × 44px | Apple HIG minimum tappable size |

Treat these as the lower bound, not the target. Captions and footnotes may approach the floor; primary content should sit comfortably above it.

## Context-First Discipline

High-fidelity work MUST be rooted in real context before any pixels are produced. This mirrors the toolkit's verify-don't-recall ethos:

- **Read the source first.** Inspect the codebase, design tokens, UI kit, and screenshots that already exist before generating anything.
- **Lift exact values.** Copy real hex codes, the spacing scale, the font stack, and radii straight from source. Do NOT reconstruct token values from memory — recalled values drift.
- **Mock from scratch only as a last resort.** Building a screen with no reference is the fallback when no codebase, kit, or screenshot exists, not the default.

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

## Transform Mastery

### Percentage translations

```css
/* Moves by own height — perfect for toasts, drawers */
transform: translateY(100%);
```

No hardcoded pixel values needed.

### Scale affects children

Unlike `width`/`height`, `scale()` proportionally scales content, icons, and text. Intentional feature, not a bug.

### 3D transforms

```css
.orbit {
  transform-style: preserve-3d;
}
```

Enables orbit animations and coin flips without JavaScript.

## Clip-path Animation

`clip-path: inset(top right bottom left)` creates rectangular clipping regions:

### Tab color transitions

Stack tab lists, clip the active copy, animate clip-path on change for seamless color shifting.

### Hold-to-delete

```css
.delete-overlay {
  clip-path: inset(0 100% 0 0);
  transition: clip-path 200ms ease-out; /* fast snap-back on release */
}
.delete-button:active .delete-overlay {
  clip-path: inset(0 0 0 0);
  transition: clip-path 2s linear; /* slow fill while holding */
}
```

### Image reveals

```css
.reveal {
  clip-path: inset(0 0 100% 0); /* hidden */
}
.reveal.visible {
  clip-path: inset(0 0 0 0); /* revealed */
}
```

### Comparison sliders

Overlay images, clip top one by adjusting right inset based on drag position.

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

Five principles (from Sonner, 13M+ weekly downloads):

1. **Developer experience first** — minimal setup friction, insert once, use globally
2. **Excellent defaults** — ship beautifully configured out-of-box
3. **Identity through naming** — a memorable name resonates
4. **Invisible edge cases** — pause timers when hidden, handle pointer capture during drag
5. **Transitions over keyframes** — rapid additions cause keyframe restart from zero; transitions retarget smoothly

### Cohesion

Animation personality should match component identity. Playful components can bounce; professional dashboards stay crisp.

### Asymmetric timing

Deliberate actions stay slow (2s linear for hold-to-delete), system responses snap fast (200ms ease-out for release).

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
- **NEVER** animate `height`, `width`, `margin`, or `top/left` — animate `transform` and `opacity` only. Layout-triggering properties drop frames under load.
- **NEVER** add motion for decorative reasons alone — every animation must serve meaning (status change, spatial relationship, progress)
- **CRITICAL**: exit is faster than enter. A 2s linear enter (hold-to-delete) needs a 200ms ease-out exit. Symmetrical durations feel sluggish.
- **MANDATORY**: any animation longer than 300ms for UI feedback needs an explicit justification — the user perceives >300ms as "laggy", not "smooth"
- **MUST** lift exact values (hex, spacing, font stack, radii) from the real codebase, tokens, UI kit, or screenshots before high-fidelity work — never reconstruct token values from memory; mock from scratch only when no source exists
- **MUST** keep slide body text at ~24px+, print at ~12pt+, and mobile touch targets at 44px+ — these are accessibility floors, not preferences
- **NEVER** ship the slop defaults — saturated full-bleed gradients, emoji as decoration, repeated rounded-card-with-accent-border, hand-drawn fake imagery in SVG, or the unconsidered default font stack
- **NEVER** add filler (dummy stats, decorative sections, lorem) to fill space, and never fabricate assets — an honest labeled placeholder beats an invented icon or fake image; ask for the real one
- **MUST** match the existing UI's vocabulary (palette, states, motion, shadow/density, copy tone) when editing a live surface instead of imposing a new style
- **MUST** ask about goals, audience, and which dimension to diverge on (UX vs. visuals vs. copy) before building an open-ended ask; skip questions only when context is rich and the ask is bounded
- **CARVE-OUT**: a sanctioned design audit, accessibility-failure demonstration, or authorized red-team mockup may deliberately reproduce a slop pattern or sub-floor scale to illustrate the defect — label it as such; the bans above target shipped UI, not sanctioned analysis
- **SHOULD** produce 3+ atomic variations across distinct axes (layout, color, type, interaction), ordered basic → advanced, for any exploratory or open design ask

## Gotchas

- `transform: translateX(-50%)` on an element that will animate `opacity` triggers a paint on every frame because the browser cannot composite the layer. Add `will-change: transform, opacity` to hint the compositor — but only during the animation, not permanently (it consumes GPU memory).
- Framer Motion's `x={100}` prop is a shortcut for `transform: translateX(100px)`, but under load it falls back to the main thread. Use the longhand `style={{ transform: "translateX(100px)" }}` for guaranteed compositor path.
- `@media (prefers-reduced-motion: reduce)` is widely supported but often forgotten. Users with vestibular disorders or pointer-device sensitivity will notice; include a reduced-motion override for every non-trivial animation.
- Chrome's Performance tab samples animations, but the sampling rate is 1kHz — sub-millisecond jank is invisible. For micro-animations, prefer `performance.mark` and `measure` with explicit timestamps.
- CSS keyframe animations re-trigger on every class toggle. On rapidly-updating state (drag, hover), transitions are cheaper and smoother; keyframes are for one-shot entries/exits.

## When NOT to Load

- For **accessibility** beyond motion (contrast, focus, ARIA) — use `/a11y-validate`
- For component-library architecture (Radix, Headless UI, ShadCN) — use `/frontend-specialist` agent
- For **information architecture** and user flows — use `/ux-designer` agent
- For generic CSS patterns without motion — this skill is motion-specific
- For **brand voice** / content tone — use `/brand-voice`
