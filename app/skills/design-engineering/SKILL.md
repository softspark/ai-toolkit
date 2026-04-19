---
name: design-engineering
description: "UI craftsmanship (Emil Kowalski school): animation frequency rules, easing curves, micro-interactions, state polish, invisible-details philosophy. Triggers: animation, transition, ease-out, ease-in-out, motion, micro-interaction, hover state, loading state, UI polish, design detail, spring curve, delightful UX. Load when building or reviewing interactive UI."
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

## Anti-Patterns

- `transition: all` — animates unintended properties, hurts performance
- `ease-in` on UI elements — delays feedback when attention peaks
- Animating `height`/`width`/`margin` — triggers layout recalculation
- Same duration for enter and exit — exits should be faster
- Hover effects without `@media (hover: hover)` — breaks touch devices
- Framer Motion shorthands under load — drops frames on main thread
