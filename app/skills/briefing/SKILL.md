---
name: briefing
description: "Generate an executive daily briefing that aggregates reports from all agents into a short, decision-focused summary. Use when the user asks for a status update across the whole system — not for one-agent activity reports."
effort: medium
disable-model-invocation: true
agent: chief-of-staff
context: fork
allowed-tools: Read, Grep, Glob
---

# Briefing Command

Triggers the Chief of Staff to generate an executive summary.

## Usage

```bash
/briefing [period]
# Example: /briefing today
# Example: /briefing week
/briefing --tokens [--since 7d|24h|30m]
# Reports real session token usage from Claude Code JSONL.
```

## Protocol
1. **Collect**: Gather logs from `kb/learnings/`, `maintenance/` logs, and recent runs.
2. **Synthesize**: Group by category (Ops, Strategy, Actions).
3. **Filter**: Remove low-priority success logs.
4. **Present**: Render the Daily Brief.

## Example

```
## Daily Brief — 2026-04-23

### Ops
- night-watch: 3 dep updates shipped, 1 rolled back (breaking change in `x-pkg@2.0`)
- health: all green except `mailpit` (degraded, non-critical)

### Strategy
- predict: new PR #42 overlaps with in-flight refactor in `/src/auth`

### Actions needed
- Review rollback from night-watch (ETA: 5 min)
- Decide on `x-pkg` pin strategy (open question on GitHub #41)
```

## Rules

- **MUST** stay under 200 words unless the user explicitly asks for more detail
- **MUST** lead with decision-relevant facts, not chronology — "what should I act on" before "what happened"
- **NEVER** invent agent activity — report only what the logs show; absence of logs means "no data", not "nothing happened"
- **CRITICAL**: separate Ops (what ran) from Strategy (what was decided) from Actions (what needs a human) — mixing them defeats the brief
- **MANDATORY**: when no material activity exists for a category, omit the category heading instead of writing "none"

## Gotchas

- `kb/learnings/` often mixes drafts with completed entries. Filter by frontmatter `status: final` or by filename convention before aggregating.
- `maintenance/` branch logs from `/night-watch` use a different format (Shift Report markdown) than agent run logs. Do not concatenate blindly — parse each source separately and normalize.
- "Recent runs" without an explicit time bound defaults to **everything** on some log backends. Always pass `--since` or a date filter, or you will read a week into yesterday's memory.
- Successful runs outnumber interesting runs by an order of magnitude. Aggressively filter green/noop entries — they are the signal's noise floor.

## Token Receipts

The `--tokens` flag reports real token usage parsed from Claude Code session JSONL — not estimates. Useful for:

- Verifying `output-mode: concise` actually reduces tokens vs default sessions
- Spotting expensive runs before they show up on the bill
- Capturing a baseline before changing prompts or skills

Underlying script: `scripts/session_token_stats.py`.

```bash
# Aggregate current session
python3 scripts/session_token_stats.py --json

# Statusline-friendly one-line output
python3 scripts/session_token_stats.py --statusline

# Trend vs baseline
python3 scripts/session_token_stats.py --statusline --baseline ~/.softspark/ai-toolkit/baseline.json
```

### Status line (installed by default in v3.2.0+)

`ai-toolkit install` wires `~/.claude/settings.json` to `app/hooks/ai-toolkit-statusline.sh`. The hook reads native Claude Code statusLine stdin (no session JSONL parsing) and renders one line:

```
➜ <dir> git:(branch) ✗ ████░░░░░░ 43%  ↑6.5k ↓252k effort:xhigh <model>
```

Segments left to right:

- `➜ <dir>` — current directory basename
- `git:(branch) ✗` — git branch + dirty marker
- 10-cell **progress bar** for context-window usage. Color tiers: green `<70%`, orange `70–89%`, red `≥90%`
- `↑in ↓out` — token arrows. Green up = input (upload), red down = output (download). Both cumulative across the session.
- `effort:level` — Claude Code effort level (low / medium / high / xhigh)
- model name

Custom statusLine entries you set yourself (without the `_source: ai-toolkit` tag) are preserved untouched on install.

Opt-outs (no reinstall required):

- `AI_TOOLKIT_STATUSLINE_DISABLE=1` — silence the line entirely
- `AI_TOOLKIT_STATUSLINE_NO_TOKENS=1` — hide token arrows segment
- `AI_TOOLKIT_STATUSLINE_NO_GIT=1` — hide git segment
- `AI_TOOLKIT_STATUSLINE_NO_EFFORT=1` — hide effort level segment
- `AI_TOOLKIT_STATUSLINE_NO_COLOR=1` — disable ANSI colors
- `AI_TOOLKIT_STATUSLINE_SHOW_COST=1` — append Claude Code's reported cost (`cost.total_cost_usd`)
- `AI_TOOLKIT_STATUSLINE_DUMP=1` — write received stdin to `/tmp/cc-statusline-input.json` (debug)

### Save a baseline

```bash
python3 scripts/session_token_stats.py --json | jq '.totals' > ~/.softspark/ai-toolkit/baseline.json
export AI_TOOLKIT_STATUSLINE_BASELINE=~/.softspark/ai-toolkit/baseline.json
```

The statusline then renders trend arrows (↑ / ↓) against that baseline.

## When NOT to Use

- For a specific production incident — use `/workflow incident-response`
- For one-agent activity detail — read that agent's logs directly (`kb/learnings/<agent>/`)
- For planning future work — use `/plan` or `/prd-to-plan`
- For a technical system-up/down status — use `/health`
- When no agents have produced logs in the window — say so and stop; do not pad
