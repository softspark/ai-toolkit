---
title: "Licensing"
category: reference
service: ai-toolkit
tags: [licence, apache-2.0, spdx, notice, attribution, headers, mit]
version: "1.0.0"
created: "2026-07-27"
last_updated: "2026-07-27"
description: "ai-toolkit is Apache-2.0 from v4.20.0. What that obliges a redistributor to do, why NOTICE is the point, the SPDX header convention and which files deliberately do not get one, how MIT-era contributions are handled, and the CI gate that enforces all of it."
---

# Licensing

ai-toolkit is licensed under the **Apache License 2.0** from v4.20.0. Releases up
to and including v4.20.0 were published under MIT and remain available under MIT.
The change applies going forward and revokes nothing already granted.

Canonical files: [`LICENSE`](../../LICENSE) (verbatim Apache-2.0 text) and
[`NOTICE`](../../NOTICE) (attribution).

## Why Apache-2.0, given MIT already required attribution

This is the part most often got wrong. MIT already says:

> The above copyright notice and this permission notice shall be included in all
> copies or substantial portions of the Software.

So attribution was never the new thing. What Apache-2.0 adds:

| Mechanism | MIT | Apache-2.0 |
|---|---|---|
| Copyright notice must be preserved | yes | yes |
| **`NOTICE` contents must travel into redistributions** (§4d) | — | **yes** |
| **Modified files must carry a notice saying they changed** (§4b) | — | **yes** |
| Express patent grant, terminated by patent litigation (§3) | — | yes |
| No rights to the licensor's names or marks (§6) | — | yes |

**`NOTICE` is the reason for the change.** It is the only mechanism in a
permissive licence that forces a redistributor to reproduce your attribution —
project name, copyright, source URL — somewhere their users can see it. Without
it, MIT and Apache-2.0 are close to equivalent in practice.

Consequence for packaging: `NOTICE` is listed in `package.json` `files`. A NOTICE
that does not reach the consumer cannot satisfy §4(d), so that entry is a
licensing requirement, not housekeeping, and is asserted in CI.

## What a fork owes

Fork it, modify it, ship it commercially. Three obligations:

1. **Carry the `NOTICE`** into your distribution (§4d).
2. **Say which files you changed** (§4b).
3. **Do not use the "ai-toolkit" or "SoftSpark" names or marks** as if endorsed (§6).

## Source header convention

Short SPDX form, three lines, always **after** the shebang — an interpreter
directive must stay on line 1 — and after a Python `coding:` line if present:

```bash
#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# guard-path.sh — the file's own description continues here.
```

`//` for JavaScript. SPDX was chosen over the 13-line Apache APPENDIX boilerplate
because it is machine-readable — licence scanners, GitHub and SBOM tooling parse
it — and because 13 lines on top of every source file buries the description that a
reader of a hook actually needs.

### Which files get a header

| Included | Count |
|---|---:|
| `scripts/**/*.py` | 109 |
| `tests/*.bats` | 77 |
| `app/hooks/*.sh` | 32 |
| `app/skills/**/*.py`, `**/*.js` | 27 |
| `app/plugins/**/*.sh`, `**/*.py` | 6 |
| `bin/*.js`, `benchmarks/**/*.py` | 2 |
| **total** | **253** |

These are a snapshot, not a contract — the CI gate checks that *every* matching
file has a header, so the count moves with the codebase and nothing needs
updating here when it does.

### Which files deliberately do not, and why

**No markdown file carries a header.** Not `app/skills/*/SKILL.md`, not
`app/agents/*.md`, not `app/rules/`, not `kb/`. Two reasons, both concrete:

1. **Frontmatter.** Skill and agent files open with parsed YAML. A header above
   it breaks parsing; a header below it is invisible where it matters.
2. **Token cost.** Skill and agent descriptions load into the system prompt of
   every session — measured at 5,051 and 2,750 tokens respectively. A four-line
   header across 108 skills and 45 agents would be a permanent per-session cost,
   billed on every conversation forever, for a notice Apache only *recommends*.
   `LICENSE` and `NOTICE` carry the full terms; the headers are a convenience.

This exclusion is asserted in CI, so a well-meant sweep of the header script over
`app/skills/` fails the build rather than silently taxing every session.

## MIT-era contributions

Contributions made while the project was MIT-licensed remain the copyright of
their authors and were received under MIT terms. Three contributors other than
the maintainer appear in the history.

MIT explicitly permits sublicensing, so those contributions are redistributed
here under Apache-2.0 **with the original MIT notice preserved verbatim** in
`NOTICE`, which is what MIT requires. This is standard practice for an MIT to
Apache-2.0 move and needs no contributor sign-off. A "clean" Apache-2.0 with no
MIT remnant would need each contributor's agreement.

*This is a description of what the project does, not legal advice.*

## Enforcement

`tests/test_licensing.bats`, seven assertions, run by `npm test` in CI:

- every shipped source file carries an SPDX header
- headers name Apache-2.0 and nothing else
- **no** markdown file carries a header
- `LICENSE` is the complete Apache 2.0 text, appendix included
- `NOTICE` carries attribution, the source URL, §4(d) and the MIT-era notice
- `LICENSE` and `NOTICE` both appear in `package.json` `files`
- every manifest declaring a licence declares Apache-2.0

It is a test rather than a checklist line on purpose. This project has two
same-day postmortems about SOPs that existed and were skipped; CI does not skip.
[Release Preparation](../procedures/sop-release.md) Phase 5c runs the
same gate before tagging so a failure surfaces before the tag, not after.

## If the licence ever changes again

Do not hand-type the licence text and do not paste a rendered copy — a
markdown-formatted licence is not the licence. Take it verbatim from a published
source, cross-verify against a second independent copy, and only then write
`LICENSE`. That is how the Apache-2.0 text in this repository was installed.

## Related

- [`LICENSE`](../../LICENSE), [`NOTICE`](../../NOTICE)
- [Release Preparation SOP](../procedures/sop-release.md) — Phase 5c
- [Distribution Model](distribution-model.md) — what ships and where
