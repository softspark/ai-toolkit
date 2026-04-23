---
title: "SOP: Ecosystem Sync"
category: procedures
service: ai-toolkit
tags: [sop, ecosystem, editors, generators, drift-detection, sync]
version: "1.0.0"
created: "2026-04-23"
last_updated: "2026-04-23"
description: "Quarterly (or event-triggered) sync procedure that detects documentation and capability drift in supported tools (Claude Code + 11 editors), analyses our generators and skills for missing features, and walks through the migration + generator-update workflow."
---

# SOP: Ecosystem Sync

Keeps ai-toolkit aligned with the tools it integrates with. When an editor adds a new hook lifecycle, makes a feature globally available, changes a config path, or deprecates a flag, this SOP surfaces it before it surprises users.

**When to run:**
- **Every quarter** as a baseline health check (calendar reminder)
- **Before every minor release** of ai-toolkit (Phase 0 of release prep)
- **Whenever an editor ships a major version** (subscribe to their changelogs)
- **On demand** if a user reports "feature X exists but toolkit doesn't support it"

**Time:** 30 minutes for drift review + variable for any generator updates

---

## Quick Reference

```bash
# Full check (all 12 tools, online)
python3 scripts/ecosystem_doctor.py --format text

# Single tool
python3 scripts/ecosystem_doctor.py --tool cursor --format text

# First-ever run — baseline the snapshot
python3 scripts/ecosystem_doctor.py --update > /dev/null

# CI / gating mode
python3 scripts/ecosystem_doctor.py --check

# Offline (no network) — validates our side only
python3 scripts/ecosystem_doctor.py --offline --format text
```

---

## Inputs

| File | Purpose |
|------|---------|
| `scripts/ecosystem_tools.json` | Authoritative registry: 12 tools with doc URLs, config paths, our generators, capability markers |
| `benchmarks/ecosystem-doctor-snapshot.json` | Last-seen state (headings, content hash, markers, version) — updated via `--update` |
| `scripts/ecosystem_doctor.py` | Drift detector |
| `kb/reference/supported-tools-registry.md` | Human-readable view of the registry |

---

## Phase 1: Run the Doctor

```bash
python3 scripts/ecosystem_doctor.py --format text > /tmp/eco-report.txt
cat /tmp/eco-report.txt
```

The report classifies every tool into:

- **Clean** — doc page, headings, and markers match the last snapshot; no action
- **Drift** — something changed upstream. Each drift entry has a `kind`:
  - `headings_added` — the doc grew new sections (new features? reorg?)
  - `headings_removed` — a section disappeared (deprecation? renaming?)
  - `marker_flips` — an expected capability marker appeared (`+`) or vanished (`-`)
  - `content_changed_no_heading_delta` — prose edits, reorder, minor rewrites, OR HTML churn (timestamps, ads, CSRF nonces). Reported but **not** treated as drift by `--check` — too noisy on dynamic pages.
  - `version_changed` — the CLI version bumped (for tools that expose `--version`)
- **Errored** — couldn't fetch docs (timeout, 404, auth wall). Doctor does not overwrite
  the snapshot for errored tools; the last-known-good state persists.

---

## Phase 2: Classify Each Drift

For every drifting tool, read its docs URL and classify the change into exactly one bucket:

| Drift class | What it means | Action owner |
|-------------|---------------|--------------|
| **A. Cosmetic reword** | Prose edited, same feature set | Update snapshot (`--update`), no code change |
| **B. New feature — we should integrate** | New hook event, new config key, new CLI flag, new rule surface | Update the relevant generator in `scripts/generate_<tool>_*.py`; extend `app/skills/*` or `app/agents/*` if the feature maps onto our skills; document in `kb/reference/supported-tools-registry.md` |
| **C. New feature — not our concern** | Enterprise SSO, billing, proprietary UI-only features | Note in registry `capability_markers` as "not adopted"; update snapshot |
| **D. Deprecation** | Flag or path removed / renamed | Open migration issue; coordinate with `ai-toolkit install` and generator output; add deprecation warning to CLAUDE.md rules if user-facing |
| **E. Feature promoted to default** | Was behind a flag, now global | Remove the flag from generator output; simplify our installer |
| **F. Global availability** | Was editor-only, now also available via CLI / hooks / settings.json | Map new config surface; may require a new generator or extending an existing one |

Write one line per drift in `/tmp/eco-report.txt` with its class. Example:

```
cursor: headings_added [AGENTS.md support] -> class B (integrate: extend generate_cursor_mdc.py)
aider:  version_changed 0.70 -> 0.72          -> class A (cosmetic, --update)
windsurf: marker_flips +Cascade               -> class B (already supported, verify snapshot)
```

---

## Phase 3: Execute Changes

### For class B (new feature — integrate)

1. Read the tool's docs section that introduced the feature. Note the exact config key / hook name / file path.
2. Open the relevant generator (`scripts/generate_<tool>_*.py`) and add output for the new surface.
3. If the feature is a **hook event**, also update:
   - `app/hooks.json` (if Claude-Code-native)
   - `app/skills/hook-creator/SKILL.md` — add the event to the Supported Hook Events table
   - `scripts/inject_hook_cli.py` — if the hook target path differs
4. If the feature is a **skill/agent schema extension**:
   - Update `app/skills/skill-creator/SKILL.md` and `app/skills/command-creator/SKILL.md` templates
   - Update `scripts/validate.py` field allowlists
   - Update `kb/reference/agent-skills-spec.md` (if the change is an upstream spec change)
5. Add a bats test under `tests/test_<tool>.bats` covering the new output.
6. Regenerate artifacts: `npm run generate:all`.

### For class D (deprecation)

1. Open a migration issue in GitHub with "class: deprecation" and a link to the upstream changelog.
2. In the generator, mark the deprecated output path as emitting a comment: `# DEPRECATED: <link>, removed in <version>`.
3. If deprecation affects `ai-toolkit install --local --editors <tool>`, add a doctor check that warns when a user's repo still contains the deprecated file.

### For class E / F (feature promotion)

1. Simplify the generator to emit the new-default form; keep a fallback comment for users on older tool versions.
2. Update `kb/reference/supported-tools-registry.md` config-paths column.

### For class A / C (no code change)

1. Run `python3 scripts/ecosystem_doctor.py --update --tool <id>` to refresh that tool's snapshot.

---

## Phase 4: Update the Registry

If new capability markers, config paths, or doc URLs emerged during Phase 3, edit `scripts/ecosystem_tools.json`:

```bash
${EDITOR:-nvim} scripts/ecosystem_tools.json
```

Fields to consider updating:
- `urls.docs` — if the vendor moved their docs
- `urls.release_notes` — if the changelog location changed
- `config_paths` — if new files now ship in our install output
- `our_generators` — if a new generator was added
- `capability_markers` — if a new feature was adopted
- `version_probe.command` — if the CLI binary was renamed

After editing, increment `last_updated` in the registry and save the snapshot:

```bash
python3 scripts/ecosystem_doctor.py --update
```

---

## Phase 5: Validate

```bash
python3 scripts/validate.py --strict
python3 scripts/audit_skills.py --ci
python3 scripts/ecosystem_doctor.py --check              # exits 0 after --update
npm test
```

All four must pass before committing generator / registry changes.

---

## Phase 6: Commit

Use a structured commit per change class:

```bash
git add scripts/ecosystem_tools.json benchmarks/ecosystem-doctor-snapshot.json
git add scripts/generate_<tool>_*.py                  # if class B/D/E/F
git add app/skills/<skill>/SKILL.md                   # if templates touched
git add kb/reference/supported-tools-registry.md
git commit -m "chore(ecosystem): sync <tool> — <brief summary>"
```

Recommended commit messages by class:

| Class | Template |
|-------|----------|
| A | `chore(ecosystem): refresh <tool> snapshot (cosmetic docs update)` |
| B | `feat(<tool>): add support for <feature>` |
| C | `chore(ecosystem): note <tool> <feature> as not-adopted` |
| D | `feat(<tool>): deprecation warning for <old-path>` |
| E | `refactor(<tool>): remove flag for <feature> (now default)` |
| F | `feat(<tool>): add <new-surface> generator` |

---

## Gotchas

- **First run has no baseline.** On a machine where `benchmarks/ecosystem-doctor-snapshot.json` does not exist, every tool shows as clean (no prior state to diff against). Run `--update` once to seed, then run again to see real drift.
- **Documentation sites use client-side rendering.** Aider, opencode, and Antigravity serve most content via JavaScript. `urllib` fetches the bare HTML skeleton — the doctor only sees a few headings. Combine the automated check with a manual visit to the docs on these tools.
- **Release notes pages change structure more often than docs.** Cursor and Windsurf refactor their changelog layouts periodically; a heading delta from a changelog page is often a presentation change, not a feature change. Classify as A when in doubt.
- **Version probes require the CLI to be installed locally.** `gemini --version`, `aider --version`, etc. are skipped silently when the binary isn't on `$PATH`. The snapshot therefore omits version drift for tools you haven't installed — that is intentional, not a bug.
- **GitHub release pages have anti-scraping.** `github.com/<org>/<repo>/releases` works via `urllib` but rate-limits aggressively. If the doctor errors on repeated runs, wait 10 minutes or manually review the release page.
- **Marker list is intentionally small.** Capability markers are a "did we adopt this?" checklist, not a feature coverage map. Adding every sub-feature bloats the JSON and produces noisy flips — keep markers at the top-level-capability tier.
- **`--check` only gates on structural drift.** Heading/marker/version changes and fetch errors exit `1`. Pure content-hash differences (`content_changed_no_heading_delta`) exit `0` — otherwise dynamic pages with timestamps or rotating ads would page you every run. If you want the strictest possible gate, grep for `Content changed` in the text report instead.

---

## Scheduling

Recommended cadence:

| Trigger | Action |
|---------|--------|
| Every Monday morning | `python3 scripts/ecosystem_doctor.py --format text` — scan during coffee |
| Before a minor release | Full sync + clean snapshot before tagging |
| After any drift report | Act within 1 week or record explicit "ignore, low priority" in the commit message |
| New tool added to the registry | Baseline with `--update --tool <id>` |
| Tool removed from support | Delete its entry from the registry AND from the snapshot JSON |

An optional GitHub Action can run `--check` weekly and open an issue on drift. Template:

```yaml
# .github/workflows/ecosystem-doctor.yml  (proposed, not yet committed)
on:
  schedule:
    - cron: '0 9 * * 1'        # Mondays 09:00 UTC
  workflow_dispatch: {}
jobs:
  doctor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python3 scripts/ecosystem_doctor.py --format text | tee /tmp/doctor.txt
      - run: python3 scripts/ecosystem_doctor.py --check
```

---

## When NOT to Use

- For **runtime** user support (user hit a bug with an editor) — use `/debug` or `/triage-issue`
- For **picking** an editor to add — that is a product decision, not a sync; use `/architecture-decision`
- For **one-off** testing of a specific tool's install flow — use the release-verification SOP
- For **scaling up** the supported-tools list — add the new tool to the registry, then run the SOP to baseline it

---

## Related Documentation

- [Supported Tools Registry](../reference/supported-tools-registry.md) — human-readable per-tool breakdown
- [MCP Editor Compatibility](../reference/mcp-editor-compatibility.md) — MCP-specific adapter table
- [Maintenance SOP](maintenance-sop.md) — general toolkit upkeep
- [Release Preparation SOP](release-preparation-sop.md) — run the doctor before tagging
