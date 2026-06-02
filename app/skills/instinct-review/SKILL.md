---
name: instinct-review
description: "Reviews/promotes/removes instincts from `.claude/instincts/*.md`. Triggers: instinct review, curate instincts, manage instincts, promote instinct."
effort: low
user-invocable: true
argument-hint: "[--list | --promote <id> | --remove <id> | --clear]"
allowed-tools: Bash, Read, Write, Glob
---

# /instinct-review - Manage Learned Instincts

$ARGUMENTS

## What This Does

Manages the instinct system: project-local behavioral notes that Claude loads at the start of a session.

Instincts are markdown files in `.claude/instincts/`, loaded at session start by `session-start.sh` whenever any exist (set `AI_TOOLKIT_HOOK_QUIET=1` to suppress).

## Commands

### List all instincts
```
/instinct-review --list
```
Shows all instincts with confidence scores and source sessions.

### Review and curate
```
/instinct-review
```
Interactive review: shows each instinct and asks promote/remove/keep.

### Promote instinct (always apply)
```
/instinct-review --promote <filename>
```

### Remove instinct
```
/instinct-review --remove <filename>
```

### Clear all instincts
```
/instinct-review --clear
```

## How Instincts Work

1. **Authoring**: Instinct files are written by hand — one markdown file per pattern in `.claude/instincts/`. There is no automatic session-end extractor today (see [When NOT to Use](#when-not-to-use)).
2. **Storage**: `.claude/instincts/<pattern-name>.md`, each carrying a confidence score (see format below).
3. **Loading**: At session start, `session-start.sh` loads every instinct file into context whenever any exist. No instincts on disk means nothing is loaded; set `AI_TOOLKIT_HOOK_QUIET=1` to suppress.
4. **Curation**: Use `/instinct-review` to list, promote, remove, or clear them.

## Instinct Format

```markdown
# Pattern: [pattern name]
Confidence: 0.85
Sessions: 3
Last seen: 2026-03-25

[Description of the pattern or preference]
```

## Steps

1. Run `ls .claude/instincts/ 2>/dev/null || echo "No instincts yet"`
2. For each instinct file, read it and display confidence/summary
3. Based on `$ARGUMENTS`:
   - `--list`: display table of all instincts
   - `--promote <id>`: set confidence to 1.0, add "pinned" tag
   - `--remove <id>`: delete the file
   - `--clear`: delete all files in `.claude/instincts/`
   - no args: interactive review of each instinct
4. Report summary of changes made

## Rules

- **MUST** list instincts with their source (session ID or date) so the user can judge provenance — anonymous instincts cannot be curated
- **MUST** confirm before `--clear` — this action is irreversible without a backup
- **NEVER** invent or edit instinct content — this skill curates existing files, it does not generate new ones
- **NEVER** promote an instinct with confidence < 0.7 without explicit user approval — low-confidence patterns are often one-off noise
- **CRITICAL**: the user owns the instinct list. Propose changes in interactive mode; apply silently only for explicit `--promote`, `--remove`, `--clear` flags.
- **MANDATORY**: after any destructive operation, print the deleted or modified filenames so the user has an audit trail

## Gotchas

- Instincts live in **project-local** `.claude/instincts/`, not in `~/.softspark/ai-toolkit/`. Running this skill in a different project sees a different set — do not treat the list as global state.
- Every instinct file loads into session context by default (whenever the directory is non-empty), so each one costs startup tokens. This is why curation matters — prune aggressively and keep the set small.
- Promoted instincts (confidence = 1.0) load into every session's context, costing tokens. Too many pinned instincts bloat startup. Keep ≤10 pinned.
- Instinct files are plain markdown following the format above. If you accumulate many, a `--clear` and re-author is often cleaner than migrating stale notes after a major toolkit bump.
- The filename (`<pattern-name>.md`) is the identity used by `--promote` and `--remove`. Renaming files manually breaks those flags until the user reopens the review UI.

## When NOT to Use

- To **auto-extract** instincts from a session — not implemented. No Stop hook writes instinct files; author them by hand (or via a future extraction tool). This skill curates existing files, it does not generate them.
- To search past session memory — use `/mem-search`
- To edit global toolkit memory files — those live in `~/.claude/projects/*/memory/` and are managed by the auto-memory system, not this skill
- To stop instincts from loading — delete the files with `--clear`, or set `AI_TOOLKIT_HOOK_QUIET=1` to suppress all session-start output. There is no extraction process to disable.
