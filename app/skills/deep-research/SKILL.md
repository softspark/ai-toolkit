---
name: deep-research
description: "Multi-source web research methodology: retrieve-vs-answer gate, complexity-scaled search budget, query craft, primary-source preference, source-conflict skepticism, adversarial verification, attribution-without-reproduction. Triggers: deep research, multi-source, web research, synthesize sources, cross-reference, fact synthesis, source verification."
user-invocable: false
allowed-tools: Read
---

# Deep Research

This is the web / multi-source counterpart to `research-mastery`. That skill is KB-first: it answers from the project's own knowledge base and only reaches outward when the KB comes up empty. This one governs what happens once you are already out on the open web pulling from many independent sources and have to weave them into one trustworthy answer. It is a method, not a fetcher — it does not retrieve anything by itself. You supply the search and fetch tools (built-in `WebSearch` / `WebFetch`, or the runtime `deep-research` command); this skill tells you how to spend them and how hard to doubt what comes back.

## Retrieve-vs-Answer Gate

Run this gate before you spend a single search:

1. **Is the answer already in the KB or your own context?** Then this is not a deep-research job — hand it to `research-mastery` (which checks RAG-MCP first) or just answer.
2. **Is it one stable fact** with a single obvious authority (a constant, a published spec value, a definition that does not move)? One targeted lookup, confirm, done. Do not open a research campaign.
3. **Does it need several independent sources reconciled, or is it contested, recent, or moving?** That is the case this skill exists for. Continue.

Skipping this gate is the most common failure: people fan out ten searches on a question that one source already settled, or worse, answer a contested question from memory because it "felt known."

## Scale Effort to Complexity

Match the search budget to the question. Burning twenty searches on a lookup wastes turns; doing two searches on a contested synthesis ships a half-checked claim.

| Question shape | Plan first? | Rough search budget |
|----------------|-------------|---------------------|
| Single stable fact, clear authority | no | 1, maybe a second to confirm |
| Compare a few known options / current state of one topic | light | a handful, broaden then narrow |
| Contested, multi-faceted, or "what is the latest on…" | yes — write the plan | many, with follow-ups as conflicts surface |

For anything in the bottom two rows, write a short research plan first: name the sub-questions, the kind of source that would answer each, and what "done" looks like. The plan is for you; keep it tight. Then let conflict drive the count — if sources disagree, you have not searched enough yet.

## Query Craft

- **Broaden, then narrow.** Open with a short, plain query to map the landscape; tighten with specific terms once you see what vocabulary the good sources actually use. Long kitchen-sink queries on the first try usually return noise.
- **Use the real current date.** Anchor "recent", "latest", "current" to today's actual date — never to your training cutoff. For 2026-06-15, "latest" means 2026, not 2024. A query that silently assumes an old year is a wrong query.
- **Vary the angle on a stubborn question.** If one phrasing returns thin or repetitive results, change the wording, the framing, or the assumed source type rather than re-running near-identical strings.

## Source Preference and Skepticism

- **Prefer primary and original sources.** Go to the spec, the paper, the official docs, the filing, the dataset, the person who actually said it — not a blog summarizing a blog summarizing it. Each hop away from the origin adds a chance for drift.
- **A surprising-but-sourced result is usually real.** If a credible primary source says something counterintuitive, treat it as true and report it. Do not soften or discard a well-attributed fact just because it clashes with your prior.
- **The exception: low-trust topic zones.** On SEO-spam-saturated queries, conspiracy-adjacent claims, and topics with genuinely no expert consensus, raise the bar instead of lowering it. Here a surprising claim needs strong independent corroboration before you repeat it, and "many pages say it" is not corroboration when those pages copy each other.
- **Conflict means search more.** When two solid sources disagree, that is a signal to run additional searches and find a tie-breaker or the underlying primary source — not to average them, pick the one you like, or paper over the disagreement.

## Adversarial Verification

Before you emit any synthesized claim, run this self-check. Each gate has a fix; do not just notice the problem.

| Self-check gate | If yes, do this |
|-----------------|-----------------|
| Am I mirroring one source's exact phrasing or structure? | Re-state it in your own words from the facts, not the prose. |
| Could my output stand in for reading the original — same length, same order, same examples? | Cut it back. Summarize and point to the source; do not reproduce it. |
| Have I already leaned on this one source for several claims? | Find an independent source, or flag the answer as single-sourced. |
| Is each claim independently corroborated, or is one shaky source carrying the conclusion? | Corroborate it, drop it, or label it as unconfirmed. |

For **high-stakes claims** — anything affecting money, health, legal exposure, security posture, or an irreversible decision — do not stop at one source. Confirm with a second, independent source or a different angle of approach before you state it as fact.

## Citation Discipline

- **Paraphrase by default, and attribute to a named source.** "Per the FY2025 10-K…", "the RFC's section on retries states…". The reader should always know who is behind a claim.
- **Reserve verbatim quotes for genuinely distinctive phrasing** — a definition, a legal clause, an exact figure where the wording itself matters. Keep quotes short and clearly marked. Do not quote at length to fill space.
- **Keep any single source's paraphrased footprint small.** No one source's material should dominate your output, and the output as a whole must never substitute for reading the originals. You are pointing readers to the sources, not republishing them.
- **NEVER invent an attribution.** If you are not sure a source actually said something, leave the claim out. A fabricated citation is worse than a missing one — it launders a guess as a fact.
- **Empty retrieval is a real result.** If a search returns nothing usable, say "not found in available sources" and cite nothing. Do not backfill from memory and dress it up as retrieved.

## Example

**Task:** "What is the current recommended approach for X, and has it changed recently?"

1. **Gate.** Not in KB, contested, has a "recently" — this is a deep-research job. Write a 3-line plan: (a) current recommendation, (b) what it replaced, (c) when/why it changed.
2. **Broaden.** Plain query anchored to the real date ("X recommended approach 2026"). Map who the authoritative voices are.
3. **Narrow to primary sources.** Open the official docs / spec / changelog rather than roundup posts. Pull the version and date where the guidance changed.
4. **Conflict surfaces.** One source still recommends the old approach. Run more searches; find the changelog entry that supersedes it. The disagreement was stale-vs-current, not a genuine split — note that.
5. **Adversarial pass.** Re-check each gate: paraphrase in own words (not mirroring the docs' structure), confirm the change claim against a second independent source since it drives the answer, confirm no single source carries everything.
6. **Synthesize with attribution.** "The official docs as of <date> recommend …; this replaced … per the <date> changelog." Short, sourced, original phrasing, none of it a stand-in for the docs themselves.

## Rules

- **MUST** pass the retrieve-vs-answer gate before searching — KB-answerable or single-fact questions do not start a research campaign.
- **MUST** scale the search budget to question complexity and write a plan for contested or multi-faceted questions.
- **MUST** anchor every "latest / current / recent" query to the real current date, never the training cutoff.
- **MUST** prefer primary and original sources over second-hand summaries.
- **MUST** run more searches when credible sources conflict — never average, cherry-pick, or hide the disagreement.
- **MUST** run the adversarial self-check before emitting a synthesized claim, and apply the corrective action when a gate trips.
- **MUST** verify high-stakes claims (money, health, legal, security, irreversible) against an independent second source or angle.
- **NEVER** fabricate an attribution; if unsure a source said it, omit the claim.
- **NEVER** let one source's paraphrased footprint dominate, and never let the output substitute for reading the originals.
- **CRITICAL**: on empty retrieval, declare "not found in available sources" and cite nothing — do not backfill from memory.
- **Authorized security work is in scope.** For sanctioned defensive analysis, CTF, vulnerability research, or pentest engagements, research and report on attack techniques, CVEs, exploit mechanics, and adversary tradecraft normally — the skepticism rules raise source quality, they do not gate legitimate security topics.

## When NOT to Use

- For a **single stable fact** already in the project KB or answerable in one lookup — use `research-mastery` (KB-first hierarchy) instead, or just answer.
- For **library / framework / API documentation** — query `context7` (or `research-mastery`'s MCP tier) for current docs rather than fanning out on the open web.
- When you need a tool that **actually fetches** — this skill is methodology only. Pair it with `WebSearch` / `WebFetch` or the runtime `deep-research` command; it retrieves nothing on its own.
