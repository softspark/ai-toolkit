# Animation Recipes & Advanced Techniques

Supplementary reference for `design-engineering` skill covering transform techniques, clip-path animations, and advanced interaction recipes.

## Transform Mastery

### Percentage Translations
```css
/* Moves by own height — perfect for toasts, drawers */
transform: translateY(100%);
```
No hardcoded pixel values needed.

### Scale Affects Children
Unlike `width`/`height`, `scale()` proportionally scales content, icons, and text. Intentional feature, not a bug.

### 3D Transforms
```css
.orbit {
  transform-style: preserve-3d;
}
```
Enables orbit animations and coin flips without JavaScript.

---

## Clip-Path Animation

`clip-path: inset(top right bottom left)` creates rectangular clipping regions:

### Tab Color Transitions
Stack tab lists, clip the active copy, animate clip-path on change for seamless color shifting.

### Hold-to-Delete
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

### Image Reveals
```css
.reveal {
  clip-path: inset(0 0 100% 0); /* hidden */
}
.reveal.visible {
  clip-path: inset(0 0 0 0); /* revealed */
}
```

### Comparison Sliders
Overlay images, clip top one by adjusting right inset based on drag position.

---

## Gotchas & Performance Edge Cases

- `transform: translateX(-50%)` on an element that will animate `opacity` triggers a paint on every frame because the browser cannot composite the layer. Add `will-change: transform, opacity` during animation only.
- Framer Motion's `x={100}` prop falls back to the main thread under load. Use `style={{ transform: "translateX(100px)" }}` for guaranteed GPU compositor path.
- `@media (prefers-reduced-motion: reduce)` is widely supported but often forgotten; include reduced-motion overrides for every non-trivial animation.
- Chrome's Performance tab samples animations at 1kHz — sub-millisecond jank is invisible. Prefer `performance.mark` and `measure` with explicit timestamps.
- CSS keyframe animations re-trigger on every class toggle; transitions are cheaper and smoother on rapidly-updating state (drag, hover).
