# Component Craft & Design Principles

Supplementary reference for `design-engineering` skill covering principles for loved UI components and microinteraction cohesion.

## Building Loved Components

Five core principles (inspired by Sonner):

1. **Developer experience first** — minimal setup friction, insert once, use globally
2. **Excellent defaults** — ship beautifully configured out-of-box
3. **Identity through naming** — a memorable name resonates
4. **Invisible edge cases** — pause timers when hidden, handle pointer capture during drag
5. **Transitions over keyframes** — rapid additions cause keyframe restart from zero; transitions retarget smoothly

---

## Personality & Cohesion

Animation personality should match component identity:
- **Playful components**: Can use slightly softer curves or playful timing.
- **Professional tools & dashboards**: Stay crisp, deterministic, and fast (150–200ms).

---

## Asymmetric Timing

- **Deliberate user actions**: Stay controlled/slow (e.g., 2s linear for hold-to-delete).
- **System feedback / release**: Snaps fast (e.g., 200ms ease-out).
