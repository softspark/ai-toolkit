<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu) -->

# Decisions

Why things are the way they are. One entry per decision that a future reader would
otherwise have to reverse-engineer from a diff.

`CHANGELOG.md` says what shipped. This says why, and what was rejected.

---

## The surface manifest, not the prose, is the contract (2026-08-05)

`BACKWARD_COMPATIBILITY.md` shipped first and enforced nothing. This repository's
own `CLAUDE.md` already says why that is not good enough:

> "Any rule that must be enforced at a fixed lifecycle point belongs in
> `app/hooks.json` + `app/hooks/*.sh` with tests. `CLAUDE.md` guidance is context,
> not enforcement."

By that standard the document was the weak form: rename `/review` and every gate
stayed green. `scripts/surface_manifest.py` plus the committed `app/surface.json`
turn the list into a test over 275 entries — skills, agents, frontmatter fields,
CLI commands, hook scripts and events, KB categories, plugin packs.

The check is one-directional on purpose:

- **removal fails** — someone pinned the version that had it
- **addition passes** — a surface nobody has installed has no users to break

Additions passing silently is what keeps the check from becoming a tax. Adding a
skill does not turn the build red, so nobody learns to reach for `--update` as a
reflex.

**The manifest is deliberately not auto-regenerated.** If `generate:all` rewrote
it, deleting a skill would delete its manifest entry in the same breath and the
check would detect nothing — a green build proving only that the evidence was
destroyed. `--update` is a release-time step in
`kb/procedures/sop-release.md`: run it, read the diff, and every line
removed owes an entry here.

**Rejected:** wiring the check into a git hook. It belongs in `npm test`, where a
failure is visible and reviewable, not at commit time where the first instinct is
`--no-verify`.

---

## README badges are generated (2026-08-05)

Three badges — agents, skills, tests — were hand-maintained and validated by
`validate.py`. Every change that added a test broke `--strict` until someone
edited a number. That fired **three times in a single session**, each costing a
diagnosis cycle, and it also cascaded: a stale badge failed `validate.py`, which
failed the `setup_file` of a bats suite that shells out to it, producing four
failures with one cause.

`scripts/sync_badges.py` derives the counts exactly as `validate.py` does and
rewrites them. It runs last inside `npm run generate:all`, which `prepublishOnly`
executes before `validate.py --strict`, so the numbers are correct by the time
anything checks them. `--check` reports drift without writing, for CI.

The counting rules are duplicated between the two scripts, which is a real cost.
The alternative — validate.py rewriting files during validation — is worse: a
validator with side effects cannot be trusted to report what it found.

---

## `/brainstorm` — a planning skill allowed to say no (2026-08-05)

Every planning skill here produced an artifact. `/write-a-prd` produces a PRD,
`/prd-to-plan` a plan, `/prd-to-issues` issues, `/plan` phases, `/council` a
recommendation, `/grill-me` a critique of something already proposed. A grep over
all 108 skills for any variant of "not worth building" returned nothing. A
planning pipeline with no path to "no" is a yes-machine, and that was the gap.

Two mechanisms carry it:

- **The zero option is one of the three required alternatives**, priced with its
  own costs — what stays broken, who absorbs it today, what the codebase carries
  forever once the thing exists.
- **A separate challenger agent attacks the conclusion** before any routing. Not
  self-review in the same context, which reproduces the same blind spots and
  reports that everything holds. It is instructed to assume the conclusion is
  wrong and find where, and to treat a first pass that breaks nothing as evidence
  the attack was shallow rather than that the idea is sound.

Six exit ramps, of which ramp 1 is "nothing worth building — stop", with the rule
that no deliverable may be invented to justify the conversation.

**This may still be ceremony, and the skill says so.** Its own Gotchas carry the
kill switch: the challenger roughly doubles the cost of a planning session, and
that is only worth paying if ramp 1 or ramp 6 sometimes wins. If every run routes
to `/write-a-prd`, the skill has become theatre and should stop being used. A
skill that cannot describe the conditions under which it is worthless is a skill
nobody will ever retire.

---

## Why a compatibility contract exists (2026-08-05)

`BACKWARD_COMPATIBILITY.md` was written at v4.21.0 — after 106 published versions,
not before the first. That is late, and the reason it got written is worth
recording: the question "does anyone but the author use this?" was treated as
unanswerable and used to defer the work. It was answerable in one HTTP request.
The npm registry reported 3,909 downloads over 30 days with traffic on 29 of them.

The lesson generalises past this document: an assumption that blocks work and can
be checked should be checked, not carried.

---

## Skill body budget and the ratchet (2026-08-05)

`scripts/validate.py` now errors above 20,000 bytes of skill body and warns above
18,000, measured after the frontmatter block.

The thresholds are deliberately loose. A 12,000-byte budget was the target and is
still the floor the ratchet walks toward, but adopting it in one step would have
produced 19 warnings and — because `prepublishOnly` runs `validate.py --strict` —
a package that could not be published. Thresholds that block the release get
raised back, and then they mean nothing. So the budget entered at a level nothing
violated, and `kb/procedures/sop-release.md` owns lowering it.

Two rules were written into the SOP rather than left as a source comment, because
a comment saying "lower this each release" is a comment nobody reads:

- never lower a threshold in the same change that something violates it
- never raise one to green a red build

`validate.py` prints the current headroom on every run for the same reason.

**Rejected:** an allowlist of known-oversized skills. It would have shipped the
budget a day earlier and become permanent, which is the usual fate of a
"temporary" exemption list.

---

## The split gate is a tool, not a CI step (2026-08-05)

`scripts/check_split.py` proves that moving content from a `SKILL.md` body into
`reference/` lost nothing: fenced code lines survive (gate A), removed prose is
traceable (gate B), always-loaded sections stayed in the body (gate C), and the
frontmatter description is byte-identical (gate D).

It is run by hand during a split and is not wired into `npm test`, because it
needs a pre-split reference to compare against and there is nothing to compare on
an ordinary commit.

Gate B warns instead of failing. Prose legitimately gets reworded into pointers
during a split, so a binary gate there would be either noise or a lie; the unmatched
lines are printed and a human judges them. `--strict` promotes them for CI use.
Code is different: it is the risk surface, it must survive literally, and gate A is
hard.

The gate earned itself on first use. Splitting `hipaa-validate` demoted a
`### BAA Verification Checklist` heading that sits *inside* a fenced example of the
skill's own output; gate A caught it as one lost code line. Nothing else in the
pipeline would have.

**Gate E closed that gap the same day.** A split invalidates every
`(reference/x.md)` path that moves down a directory, and `validate.py` only checks
links in `SKILL.md` — so a broken pointer inside `reference/` ships silently. That
cost 19 hand-fixed links across three skills before the gate existed, and one of
them (`phi-identifiers.md`) was found only by walking every target manually.

Gate E resolves every relative link in the body and in each `reference/*.md`
against the directory of the file that holds it. Two exclusions, both structural
rather than heuristic:

- links inside fenced blocks are examples, not pointers
- links inside inline code spans are literal text — a WCAG grep pattern such as
  `` `type=["']password["'](?!.*autocomplete)` `` reads as a link to a naive matcher,
  and that was the single false positive in the first pass over all 108 skills

After the exclusions: 86 links checked tree-wide, zero false positives. Verified
against the historical bug by reintroducing it — the gate fails with
`BROKEN: scanner-categories.md -> reference/phi-identifiers.md`.

A tree-wide regression test (`every shipped skill has resolvable relative links`)
runs the same check on every skill in `npm test`, so a broken link cannot enter
outside a refactor either.

---

## Four-tier review severity, shared by skill and agent (2026-08-05)

`/review` and the `code-reviewer` agent now both report `blocker` / `major` /
`minor` / `nit` with a mechanical verdict rule: any blocker requests changes, any
unwaived major requests changes, only minor and nit approve.

They previously disagreed. The skill's output format asked for
`Critical/Major/Minor/Nit` while the agent it delegates to — `agent: code-reviewer`,
`context: fork` — reported `CRITICAL/HIGH/MEDIUM/LOW/INFO`. The agent wins at
runtime, so the skill never received the format it specified.

Severity and confidence were also explicitly separated: severity is impact,
confidence is certainty, and a low-confidence finding is reported at the tier its
evidence supports rather than promoted to blocker on suspicion.

The same change added the rule that a review collects every failing signal — merge
conflict, red CI, lint — records each as a blocker, and then reviews the change in
full anyway. A run that stops at the first red signal spends its cycle repeating
what the tracker already displayed.

---

## Validator scripts are wired into the skills that ship them (2026-08-05)

`a11y-validate` and `seo-validate` shipped working scanner scripts —
`a11y-scanner.py` (643 lines) and `seo-scanner.py` (553 lines) — that no step in
either `SKILL.md` invoked. Both told the model to grep the pattern tables by hand.

Both now run their script for a deterministic baseline, then take an explicit
manual pass over what the script does not reach. The body carries a coverage table
naming, per category, which part is which:

| Skill | Script coverage | Fully manual |
|---|---|---|
| `a11y-validate` | 10 checks, 13 of ~50 documented WCAG success criteria | none — every category partially covered |
| `seo-validate` | 9 checks across 8 of 10 categories | category 7 (Rendering & Crawlability), category 10 (Topical Authority) |

The table is measured, not asserted, so it can be re-derived when either script
changes. Stating coverage honestly matters more than stating it favourably: a skill
that implies full coverage and delivers 13 criteria is worse than one that says
which 13.

This was a behaviour change, taken deliberately in place of a pure refactor,
because splitting these two skills without it would have moved their working
material out of reach of the step that needs it.

---

## v4.20.0 — nine plugin packs removed (2026-07-27)

`csharp-pack`, `java-pack`, `kotlin-pack`, `ruby-pack`, `rust-pack`, `swift-pack`,
`frontend-pack`, `research-pack`, `security-pack`.

Every one declared only skills and agents that already ship in the core install,
so `plugin install` reported `(0 file items)` and wrote nothing to disk. Eight of
the nine owned nothing but a `README.md`. Measured on both runtimes across all
three profiles.

No capability was lost — `rust-patterns`, `java-patterns`, `security-patterns`,
`research-mastery` and the rest are core skills and always were. `frontend-pack`
was the one partial exception: on codex it copied core's `post-tool-use.sh` under a
pack-prefixed name, which is a generic hook with a domain label rather than
frontend functionality.

The break is narrow but real: `plugin install <name>` for those nine strings now
fails. The CHANGELOG entry documents it in full, which is the standard
`BACKWARD_COMPATIBILITY.md` now asks for.

---

## KB taxonomy is one list of eight categories (2026-07-28)

`decisions` and `runbooks` were added to `VALID_KB_CATEGORIES`, bringing it to
eight. They had been missing while the kb-migration SOP told people to create those
directories, so a correctly filed ADR failed validation. That part is a fix, not a
break.

Two new errors landed with it, and those are stricter than before:

- a document carrying both `section` and `category` with different values is
  rejected. `section` is a legacy alias, not a second axis; a document with two
  values gets indexed twice and found once, invisibly to its author.
- a document filed under a directory that *is* a category name must declare that
  category. Scoped on purpose: `kb/history/completed/` is a lifecycle location, not
  a type, and a finished plan is still a `planning` document.

The taxonomy lives in two files — `scripts/validate.py` rejects typos,
`app/skills/documentation-standards/SKILL.md` is what authors read. They are one
list in two places and a change belongs in both, in the same commit.
