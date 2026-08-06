---
name: a11y-validate
description: "Accessibility validator: WCAG 2.1 AA, EN 301 549, EAA. Triggers: a11y, accessibility, WCAG, EAA, ARIA, contrast, keyboard, screen reader."
user-invocable: true
effort: medium
disable-model-invocation: true
context: fork
agent: frontend-specialist
argument-hint: "[path] [--scope full|keyboard|contrast|forms|media|aria|motion|mobile|docs] [--standard wcag-2.1-aa|wcag-2.2-aa|en-301-549|eaa] [--severity high|warn|info] [--framework auto|react|next|nuxt|astro|gatsby|sveltekit|remix|angular|vue|react-native|flutter|static] [--output markdown|json]"
allowed-tools: Read, Grep, Glob, Bash
---

# /a11y-validate — Accessibility & EAA Compliance Scanner

$ARGUMENTS

Scan a codebase for accessibility issues using pattern-matching heuristics. Detects violations of **WCAG 2.1 Level AA**, **EN 301 549** (the EU harmonized accessibility standard), and the **European Accessibility Act** (Directive (EU) 2019/882, "EAA", in force since 28 June 2025). Read-only — never modifies files.

Complements `/seo-validate` (which only covers SEO-a11y overlap shallowly). Use this skill when the concern is legal accessibility compliance, not search engine ranking.

**Standards basis**:
- **WCAG 2.1** Level A + AA — W3C Recommendation 2018 (updated 2023).
- **WCAG 2.2** Level AA (opt-in via `--standard wcag-2.2-aa`) — adds 2.4.11 focus not obscured, 2.5.8 target size minimum, 3.2.6 consistent help, 3.3.7 redundant entry, 3.3.8 accessible authentication.
- **EN 301 549 v3.2.1** — EU harmonized standard; aligned with WCAG 2.1 AA plus additional chapters for mobile, hardware, ICT procurement, authoring tools, and functional-performance statements.
- **EAA / Directive (EU) 2019/882** — legal framework requiring EN 301 549 conformance for consumer-facing digital products and services in EU markets. Deadline: **28 June 2025**. Requires accessibility statements per member-state templates.

## Usage

```
/a11y-validate                                # Scan full project, auto-detect framework
/a11y-validate src/                           # Scan specific path
/a11y-validate --scope keyboard               # Only keyboard + focus checks
/a11y-validate --scope media                  # Only captions/transcripts/autoplay
/a11y-validate --scope docs                   # Only EAA accessibility-statement check
/a11y-validate --scope mobile                 # Only React Native + Flutter patterns
/a11y-validate --standard eaa                 # Activate EAA documentation category
/a11y-validate --standard wcag-2.2-aa         # Add WCAG 2.2 criteria
/a11y-validate --severity high                # Filter to HIGH findings
/a11y-validate --framework react-native       # Force framework
/a11y-validate --output json                  # Structured JSON for CI integration
```

**Scopes:**
- `full` (default) — all 8 categories
- `keyboard` — Category 3 only
- `contrast` — Category 4 only
- `forms` — Category 5 only
- `media` — Category 6 only
- `aria` — Category 7 only
- `motion` — Category 8 motion subsection
- `mobile` — Category 8 mobile subsection (React Native / Flutter)
- `docs` — Category 8 EAA documentation subsection (fast "are we legally exposed?" scan)

**Standards:**
- `wcag-2.1-aa` (default) — 50 Level A + AA success criteria.
- `wcag-2.2-aa` — adds 2.4.11, 2.5.8, 3.2.6, 3.3.7, 3.3.8.
- `en-301-549` — wcag-2.1-aa + mobile chapter + functional-performance statements.
- `eaa` — en-301-549 + accessibility-statement documentation requirement (activates Category 8 docs).

**Severity filtering:** `--severity high` shows only HIGH, `--severity warn` shows HIGH+WARN, `--severity info` shows all. Default: all.

## What This Command Does

1. **Detect framework** from `package.json`, `pubspec.yaml`, and entry HTML.
2. **Run the scanner script** for a deterministic baseline over 13 WCAG success criteria.
3. **Extend the scan by hand** using `Grep` / `Glob` / `Read` against framework-aware patterns for everything the script does not cover.
4. **Interpret findings** with specific fixes tied to the detected framework.
5. **Report** findings sorted by severity with WCAG / EN 301 549 citations.

## Steps

### Step 1: Detect Framework

Run detection before scanning. Same logic as `/seo-validate` plus mobile entries:

| Deps / files contain | Framework | Notes |
|---|---|---|
| `next` | `next` | App Router uses `metadata` export |
| `nuxt` | `nuxt` | `useHead()` / `definePageMeta` |
| `astro` | `astro` | islands model; `client:only` affects a11y |
| `gatsby` | `gatsby` | Head API + react-helmet |
| `@sveltejs/kit` | `sveltekit` | `<svelte:head>` |
| `@remix-run/*` | `remix` | `MetaFunction` |
| `@angular/core` | `angular` | CDK `a11y` module expected |
| `vue` (no nuxt) | `vue` | a11y plugins optional |
| `react` + `vite` (no next/remix) | `react-spa` | — |
| `react-scripts` | `cra` | — |
| `react-native` | `react-native` | mobile — AccessibilityInfo API |
| `pubspec.yaml` with Flutter SDK | `flutter` | mobile — `Semantics()` widget |
| no framework deps | `static` | raw HTML |

Also detect a11y libraries: `@react-aria/*`, `@reach/*`, `@angular/cdk/a11y`, `vue-a11y`, `svelte-a11y`, `react-axe`, `axe-core`. Their presence is INFO.

### Step 2: Run the Scanner Script

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/a11y-scanner.py [path] [--severity high|warn|info|all] [--output json|text]
```

Deterministic regex checks over 13 WCAG success criteria — images, headings,
language, forms, keyboard, focus, colour contrast, media, ARIA and target size.
No framework awareness and no heuristics: what it reports is real, what it misses
is Step 3's job. Exit code is non-zero when HIGH findings exist.

### Step 3: Extend the Scan by Hand

Read [reference/scanner-categories.md](reference/scanner-categories.md) in full,
then work every category in `--scope` with `Grep` + `Read`, skipping only the
success criteria Step 2 already reported. Patterns adapt to the detected framework.

The coverage table under [Scanner Reference](#scanner-reference) says which criteria
Step 2 handles per category. Everything else in the category is yours.

### Step 4: Interpret and Enrich

For each finding:
1. **Read the flagged file/lines** to confirm the match.
2. **Add a framework-specific fix** (e.g., "use `@react-aria/button`" vs "add `aria-label`").
3. **Mark confidence** — `definitive` for regex matches, `heuristic` for co-occurrence / absence / target-size estimation.
4. **Skip false positives** when context shows the concern is addressed (e.g., aria-label set via intl translation key).

### Step 5: Report

Present findings sorted by severity (HIGH → WARN → INFO), then file path.
State which findings came from the script and which from the manual pass — a reader
needs to know how much of the result is deterministic.

---

## Scanner Reference

`scripts/a11y-scanner.py` gives a deterministic baseline over 13 WCAG success
criteria. Everything else in each category is a manual pass, and the full pattern
tables for it live in
[reference/scanner-categories.md](reference/scanner-categories.md).

| # | Category | Covered by the script | Manual pass |
|---|----------|----------------------|-------------|
| 1 | Semantic Structure & Landmarks | 1.3.1, 3.1.1 | rest of the category |
| 2 | Text Alternatives & Non-Text Content | 1.1.1 | rest of the category |
| 3 | Keyboard & Focus | 2.1.1, 2.4.3, 2.4.7 | rest of the category |
| 4 | Color, Contrast & Visual Cues | 1.4.3 | rest of the category |
| 5 | Forms, Labels & Errors | 3.3.2 | rest of the category |
| 6 | Media (Audio, Video, Embeds) | 1.2.1, 1.2.2, 1.4.2 | rest of the category |
| 7 | ARIA, Live Regions & Dynamic Content | 4.1.2 | rest of the category |
| 8 | Motion, Target Size, Mobile & EAA Docs | 2.5.8 | rest of the category |

The script never covers a whole category. Treat its output as the floor, not the
result: a run that reports only script findings has skipped most of WCAG 2.1 AA.

## Output Format

```markdown
## Accessibility Validation Report

### Summary
| Metric | Value |
|--------|-------|
| Standard | wcag-2.1-aa / wcag-2.2-aa / en-301-549 / eaa |
| Scope | full / keyboard / contrast / forms / media / aria / motion / mobile / docs |
| Framework detected | next / nuxt / astro / ... / react-native / flutter / static |
| Files scanned | N |
| Public routes scanned | N |
| Accessibility statement | found / not-found |
| Findings: HIGH | N |
| Findings: WARN | N |
| Findings: INFO | N |

### Findings

#### [HIGH] src/components/VideoPlayer.tsx:42
Category: Media
Confidence: definitive
Pattern: `<video>` without `<track kind="captions">`
WCAG: 1.2.2 (Captions — Prerecorded, Level AA)
EAA: Article 4 (product/service accessibility requirements)
Fix: Add `<track kind="captions" src="/captions/en.vtt" srclang="en" label="English" default>`. If captions are unavailable, provide a transcript link.
See: reference/wcag-2-1-aa.md#guideline-12-time-based-media

#### [HIGH] public/index.html:8
Category: Viewport & Zoom
Confidence: definitive
Pattern: `<meta name="viewport" content="..., user-scalable=no">`
WCAG: 1.4.4 (Resize Text, Level AA)
Fix: Remove `user-scalable=no` and `maximum-scale=1` from the viewport meta — users must be able to zoom to 200%.
See: reference/wcag-2-1-aa.md#144-resize-text

#### [HIGH] src/routes.tsx:15
Category: EAA Accessibility Documentation
Confidence: heuristic
Pattern: No `/accessibility` / `/accessibility-statement` route detected; footer contains no a11y link
Standard: EAA Article 14 (mandatory accessibility statement)
Fix: Publish an accessibility statement conforming to your member-state template. Link it from the footer of every public page. See reference/eaa-compliance.md for template structure.
```

**Confidence values**:
- `definitive` — regex match against a known-bad pattern.
- `heuristic` — co-occurrence, absence, ordering, or derived inference (target size from CSS, contrast from hardcoded colors, ATF detection).

**Exit codes** (when `--output json`):
- `0` — no HIGH findings.
- `1` — one or more HIGH findings.

## Out of Scope (Static Analysis Cannot Detect)

The skill explicitly does NOT verify the following — pair with runtime tools:

- **Actual contrast ratios** under runtime CSS cascade, theme switching, custom properties (use `axe-core`, Lighthouse, or manual tooling).
- **Zoom / reflow behavior** at 200% / 400% (WCAG 1.4.10, 1.4.4) — requires rendering.
- **Screen reader announcement order and quality** (NVDA, JAWS, VoiceOver, TalkBack).
- **Cognitive accessibility** (WCAG 3.x is mostly process/content-driven, not pattern-matchable).
- **Actual keyboard trap behavior** — requires interaction.
- **Pronunciation / lang switches** at runtime.
- **Real-time caption accuracy**.
- **Usability / comprehension** — requires user studies.

For these, use: `axe-core`, `pa11y`, Lighthouse accessibility audit, manual assistive-tech testing, and user research with disabled participants.

## Rules

- **Read-only**: Never modify any files.
- **Framework-aware**: Detect framework first; apply correct pattern set.
- **Standards citation**: Every HIGH/WARN finding cites a WCAG success criterion (e.g., "1.3.1") or EN 301 549 clause.
- **Skip non-source files**: Binary files, lock files, vendored directories (`node_modules/`, `vendor/`, `dist/`, `build/`, `.next/`, `.nuxt/`, `.svelte-kit/`, `ios/Pods/`, `android/build/`, `.dart_tool/`).
- **No false confidence**: Label heuristic findings clearly. Color contrast and target size are ALWAYS heuristic in static analysis.
- **EAA docs category is LEGAL risk**: Missing accessibility statement when `--standard eaa` is selected is HIGH — this is a regulatory finding, not a code-quality suggestion.
- **No auto-fix**: A11y fixes often require design/content decisions that exceed pattern matching.
- **Don't flag missing ARIA when native semantics suffice**: Prefer native HTML elements; flag redundant ARIA, not absence when the native element is already there.

## Gotchas

- `scripts/a11y-scanner.py` exits **1 when it finds HIGH findings**, which is success for this skill, not failure. A wrapper that treats non-zero as an error will report a clean scan on the codebase with the most problems.
- The script covers 13 success criteria; `reference/wcag-2-1-aa.md` documents ~50. Reporting only script output looks like a full WCAG 2.1 AA pass and is not one — Step 3 is where most of the standard actually gets checked.
- Colour contrast is computed from **hardcoded hex values in source**. A theme built on CSS custom properties, `oklch()`, or a design-token pipeline yields no matches at all, and "no contrast findings" then means "nothing was measurable", not "contrast is fine".
- `alt=""` is correct for decorative images and wrong for meaningful ones. The scanner cannot see which is which — it flags missing `alt`, not useless `alt`, so a codebase that blanket-added `alt=""` scans clean while being less accessible than one that omitted the attribute.
- React Native and Flutter have no DOM. Categories written around HTML elements (landmarks, heading order, `lang`) do not transfer; use `reference/mobile-eaa.md` instead of reporting the whole category as passing.
- `--standard eaa` findings are **legal** risk with a June 2025 deadline, not code-quality suggestions. Downgrading a missing accessibility statement to WARN because it "isn't a code problem" misreports regulatory exposure.

## When NOT to Use

- To prove WCAG conformance for an audit or a VPAT — this is static analysis; conformance needs assistive-tech testing with disabled participants.
- To check contrast in a themed or token-driven design system — run `axe-core` or Lighthouse against the rendered page instead.
- For a runtime-only concern (focus traps, screen-reader announcement order, zoom reflow at 200%/400%) — see [Out of Scope](#out-of-scope-static-analysis-cannot-detect).
- For the a11y subset that affects search ranking — use `/seo-validate`, category 9.
- To fix what was found — this skill is read-only by contract; fixes usually need design and content decisions.

## Reference Documents

- [reference/wcag-2-1-aa.md](reference/wcag-2-1-aa.md) — All 50 Level A + AA success criteria with detection status (statically detectable vs runtime-only).
- [reference/wcag-2-2-aa.md](reference/wcag-2-2-aa.md) — 9 new WCAG 2.2 success criteria (2.4.11, 2.4.12, 2.4.13, 2.5.7, 2.5.8, 3.2.6, 3.3.7, 3.3.8, 3.3.9) with failure patterns, grep patterns, and framework notes.
- [reference/eaa-compliance.md](reference/eaa-compliance.md) — EU Directive 2019/882 articles, EN 301 549 v3.2.1 mapping, 28 June 2025 timeline, member-state transposition deltas, accessibility-statement templates.
- [reference/aria-patterns.md](reference/aria-patterns.md) — ARIA 1.2 Authoring Practices: landmarks, roles, states/properties, common anti-patterns, framework-specific helpers (`@react-aria`, `@angular/cdk/a11y`).
- [reference/mobile-eaa.md](reference/mobile-eaa.md) — EN 301 549 mobile chapter + React Native `AccessibilityInfo` / Flutter `Semantics()` patterns.

## Related Skills

- `/seo-validate` — SEO scanner; Category 9 covers a11y-for-SEO overlap only. For deep a11y compliance use `/a11y-validate`.
- `/cve-scan` — dependency vulnerability scanner.
- `/hipaa-validate` — HIPAA compliance scanner (similar pattern).
